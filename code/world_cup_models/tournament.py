"""Monte-Carlo the 2026 World Cup from a fitted match model to get champion odds.

Group stage: real fixtures + real qualification rule (top two per group plus the
eight best third-placed teams). Knockout: the exact bracket FIFA published
(`bracket.py`). Dixon-Coles simulates full scorelines, so group tie-breaks use
real goal difference; Elo simulates 1X2 outcomes (group ties broken by Elo
rating, knockout draws resolved toward the stronger side).

The one modelled simplification is routing the eight third-placed teams to their
bracket slots: FIFA's Annex C fixes one of 495 combinations; we solve the
equivalent allowed-group assignment by backtracking. Both give a legal bracket;
the difference is immaterial to champion probabilities.
"""
from __future__ import annotations

import numpy as np

from bracket import R32_SLOTS, THIRD_SLOTS, bracket_pairs

MAXG = 10


# ---------------------------------------------------------------------------
# Dixon-Coles scoreline sampler (vectorised per ordered pair)
# ---------------------------------------------------------------------------
class DCSampler:
    def __init__(self, dc):
        self.dc = dc
        gh, ga = np.meshgrid(np.arange(MAXG + 1), np.arange(MAXG + 1), indexing="ij")
        self.gh = gh.ravel()
        self.ga = ga.ravel()
        self._cum: dict[tuple, np.ndarray] = {}

    def _cumulative(self, home, away, neutral):
        key = (home, away, neutral)
        c = self._cum.get(key)
        if c is None:
            m = self.dc.score_matrix(home, away, neutral, maxgoals=MAXG).ravel()
            c = np.cumsum(m / m.sum())
            self._cum[key] = c
        return c

    def sample_scores(self, home, away, n, rng, neutral=True):
        c = self._cumulative(home, away, neutral)
        idx = np.clip(np.searchsorted(c, rng.random(n)), 0, len(self.gh) - 1)
        return self.gh[idx], self.ga[idx]


# ---------------------------------------------------------------------------
# Third-place slot assignment (per sim, backtracking over allowed groups)
# ---------------------------------------------------------------------------
def assign_thirds(qualified_letters):
    slots = list(THIRD_SLOTS.items())
    assignment = {}

    def bt(i, remaining):
        if i == len(slots):
            return True
        slot_id, allowed = slots[i]
        for L in list(remaining):
            if L in allowed:
                assignment[slot_id] = L
                remaining.discard(L)
                if bt(i + 1, remaining):
                    return True
                remaining.add(L)
                assignment.pop(slot_id, None)
        return False

    return assignment if bt(0, set(qualified_letters)) else None


# ---------------------------------------------------------------------------
# Group stage, vectorised over n simulations
# ---------------------------------------------------------------------------
def _group_tables_dc(groups, sampler, n, rng):
    ranks, thirds = {}, {}
    for L, teams in groups.items():
        pts = np.zeros((n, 4)); gf = np.zeros((n, 4)); ga = np.zeros((n, 4))
        for i in range(4):
            for j in range(i + 1, 4):
                hs, as_ = sampler.sample_scores(teams[i], teams[j], n, rng)
                gf[:, i] += hs; ga[:, i] += as_; gf[:, j] += as_; ga[:, j] += hs
                pts[:, i] += np.where(hs > as_, 3, np.where(hs == as_, 1, 0))
                pts[:, j] += np.where(as_ > hs, 3, np.where(hs == as_, 1, 0))
        gd = gf - ga
        key = pts * 1e9 + gd * 1e5 + gf * 1e2 + rng.random((n, 4))
        order = np.argsort(-key, axis=1)
        ranks[L] = order
        rows = np.arange(n); ti = order[:, 2]
        thirds[L] = (pts[rows, ti], gd[rows, ti], gf[rows, ti])
    return ranks, thirds


def _group_tables_elo(groups, elo, n, rng):
    ranks, thirds = {}, {}
    for L, teams in groups.items():
        pts = np.zeros((n, 4))
        rating = np.array([elo.rating.get(t, 1500.0) for t in teams])
        for i in range(4):
            for j in range(i + 1, 4):
                p = elo.match_probs(teams[i], teams[j], neutral=True)
                u = rng.random(n)
                home_w = u < p["home"]
                draw = (u >= p["home"]) & (u < p["home"] + p["draw"])
                pts[:, i] += np.where(home_w, 3, np.where(draw, 1, 0))
                pts[:, j] += np.where(~home_w & ~draw, 3, np.where(draw, 1, 0))
        # tie-break by Elo rating (no goal model), then random
        key = pts * 1e6 + rating[None, :] + rng.random((n, 4)) * 1e-3
        order = np.argsort(-key, axis=1)
        ranks[L] = order
        rows = np.arange(n); ti = order[:, 2]
        thirds[L] = (pts[rows, ti], rating[ti], np.zeros(n))
    return ranks, thirds


def _best_eight_thirds(thirds, n, rng):
    letters = list(thirds.keys())
    score = np.zeros((n, len(letters)))
    for k, L in enumerate(letters):
        pts, b, c = thirds[L]
        score[:, k] = pts * 1e9 + b * 1e5 + c * 1e2
    score = score + rng.random(score.shape) * 1e-3
    top = np.argsort(-score, axis=1)[:, :8]
    return np.array(letters)[top]


# ---------------------------------------------------------------------------
# Knockout, looped per sim
# ---------------------------------------------------------------------------
def _play_bracket(r32_teams, winner_fn, rng):
    """r32_teams: list of 16 (home, away) tuples in bracket order.
    Returns (champion, [two finalists])."""
    teams = [winner_fn(h, a, rng) for h, a in r32_teams]   # -> 16 R16 entrants
    finalists = None
    while len(teams) > 1:
        pairs = bracket_pairs(teams)
        if len(pairs) == 1:
            finalists = [pairs[0][0], pairs[0][1]]
        teams = [winner_fn(h, a, rng) for h, a in pairs]
    return teams[0], finalists


def _resolver(groups, ranks, thirds_letters, s):
    winners = {L: groups[L][ranks[L][s, 0]] for L in groups}
    runners = {L: groups[L][ranks[L][s, 1]] for L in groups}
    thirds_by_group = {L: groups[L][ranks[L][s, 2]] for L in groups}
    qual = list(thirds_letters[s])
    slot_team = assign_thirds(qual) or {sid: qual[i] for i, sid in enumerate(THIRD_SLOTS)}

    def resolve(tok):
        kind, arg = tok
        if kind == "W":
            return winners[arg]
        if kind == "R":
            return runners[arg]
        return thirds_by_group[slot_team[arg]]

    return [(resolve(a), resolve(b)) for a, b in R32_SLOTS]


def run_dc(dc, groups, n=10000, seed=12345):
    rng = np.random.default_rng(seed)
    sampler = DCSampler(dc)
    ranks, thirds = _group_tables_dc(groups, sampler, n, rng)
    third_letters = _best_eight_thirds(thirds, n, rng)

    def winner_fn(home, away, rng):
        hs, as_ = sampler.sample_scores(home, away, 1, rng)
        if hs[0] != as_[0]:
            return home if hs[0] > as_[0] else away
        p = dc.match_probs(home, away, neutral=True)
        return home if rng.random() < p["home"] / (p["home"] + p["away"]) else away

    champ, final, semi = {}, {}, {}
    for s in range(n):
        r32 = _resolver(groups, ranks, third_letters, s)
        c, finalists = _play_bracket(r32, winner_fn, rng)
        champ[c] = champ.get(c, 0) + 1
        for t in finalists:
            final[t] = final.get(t, 0) + 1
    return _normalise(champ, n), _normalise(final, n)


def run_elo(elo, groups, n=10000, seed=12345):
    rng = np.random.default_rng(seed)
    ranks, thirds = _group_tables_elo(groups, elo, n, rng)
    third_letters = _best_eight_thirds(thirds, n, rng)

    def winner_fn(home, away, rng):
        p = elo.match_probs(home, away, neutral=True)
        ph = p["home"] / (p["home"] + p["away"])  # decisive split
        return home if rng.random() < ph else away

    champ, final = {}, {}
    for s in range(n):
        r32 = _resolver(groups, ranks, third_letters, s)
        c, finalists = _play_bracket(r32, winner_fn, rng)
        champ[c] = champ.get(c, 0) + 1
        for t in finalists:
            final[t] = final.get(t, 0) + 1
    return _normalise(champ, n), _normalise(final, n)


def _normalise(counts, n):
    return {k: v / n for k, v in sorted(counts.items(), key=lambda x: -x[1])}
