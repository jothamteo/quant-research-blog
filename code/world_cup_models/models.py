"""Two transparent, reproducible football forecasting models, fit on real data.

  1. Dixon-Coles (1997): a bivariate-Poisson goals model with a low-score
     correlation correction and exponential time-decay weighting.
  2. Elo: a recursive rating updated match-by-match (World-Football-Elo style,
     with margin-of-victory and competition weighting), turned into 1X2
     probabilities through an ordered-logit fit on the realised results.

Both are fit on the public `martj42/international_results` dataset (every men's
international since 1872). Nothing here is hand-tuned to a market price.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

DATA = Path(__file__).resolve().parent / "data"

# Reference "today" for time-decay weighting. Set to the tournament's eve so the
# fit is identical whenever it is rerun (reproducibility over freshness).
AS_OF = pd.Timestamp("2026-06-11")

# Competition importance weights (used by both models).
COMP_WEIGHT = {
    "FIFA World Cup": 1.00,
    "FIFA World Cup qualification": 0.80,
    "UEFA Euro": 0.90,
    "UEFA Euro qualification": 0.70,
    "Copa AmÃ©rica": 0.90,
    "Copa America": 0.90,
    "African Cup of Nations": 0.80,
    "AFC Asian Cup": 0.80,
    "UEFA Nations League": 0.70,
    "Confederations Cup": 0.70,
    "Friendly": 0.40,
}
DEFAULT_COMP_WEIGHT = 0.60

# Canonical team names. The three data sources spell several teams differently;
# everything is mapped onto the names used in the results dataset.
NAME_CANON = {
    # Polymarket / Hyperliquid -> results.csv
    "Czechia": "Czech Republic",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "Congo DR": "DR Congo",
    "DR Congo": "DR Congo",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "USA": "United States",
    "United States": "United States",
    "Cape Verde": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "IR Iran": "Iran",
    "Iran": "Iran",
    "CÃ´te d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    "Turkiye": "Turkey",
    "TÃ¼rkiye": "Turkey",
    "Curacao": "Curaçao",
}


def canon(name: str) -> str:
    return NAME_CANON.get(name, name)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_results(since: str = "2014-01-01") -> pd.DataFrame:
    df = pd.read_csv(DATA / "results.csv", parse_dates=["date"])
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df = df[df.date >= pd.Timestamp(since)]
    df["home_team"] = df.home_team.map(canon)
    df["away_team"] = df.away_team.map(canon)
    df["home_score"] = df.home_score.astype(int)
    df["away_score"] = df.away_score.astype(int)
    df["comp_w"] = df.tournament.map(COMP_WEIGHT).fillna(DEFAULT_COMP_WEIGHT)
    df["neutral"] = df.neutral.astype(str).str.upper().eq("TRUE")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Dixon-Coles
# ---------------------------------------------------------------------------
@dataclass
class DixonColes:
    teams: list[str]
    attack: dict[str, float]
    defence: dict[str, float]
    home_adv: float
    rho: float

    def _lambdas(self, home: str, away: str, neutral: bool) -> tuple[float, float]:
        ha = 0.0 if neutral else self.home_adv
        lam = np.exp(ha + self.attack[home] - self.defence[away])      # home goals
        mu = np.exp(self.attack[away] - self.defence[home])            # away goals
        return lam, mu

    def score_matrix(self, home: str, away: str, neutral: bool, maxgoals: int = 10) -> np.ndarray:
        from math import factorial

        lam, mu = self._lambdas(home, away, neutral)
        h = np.arange(maxgoals + 1)
        fact = np.array([factorial(int(k)) for k in h], dtype=float)
        ph = np.exp(-lam) * lam**h / fact
        pa = np.exp(-mu) * mu**h / fact
        m = np.outer(ph, pa)
        # Dixon-Coles low-score dependence correction.
        tau = np.ones((2, 2))
        tau[0, 0] = 1 - lam * mu * self.rho
        tau[0, 1] = 1 + lam * self.rho
        tau[1, 0] = 1 + mu * self.rho
        tau[1, 1] = 1 - self.rho
        m[:2, :2] *= tau
        return m / m.sum()

    def match_probs(self, home: str, away: str, neutral: bool = True) -> dict[str, float]:
        m = self.score_matrix(home, away, neutral)
        return {
            "home": float(np.tril(m, -1).sum()),
            "draw": float(np.trace(m)),
            "away": float(np.triu(m, 1).sum()),
        }


def fit_dixon_coles(df: pd.DataFrame, teams: list[str], half_life_days: float = 900.0) -> DixonColes:
    """Fit Dixon-Coles by weighted maximum likelihood. Weights combine exponential
    time decay (recent matches matter more) with competition importance."""
    teams = sorted(set(teams))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)

    # Keep only matches where both teams are in the universe.
    d = df[df.home_team.isin(idx) & df.away_team.isin(idx)].copy()
    hi = d.home_team.map(idx).to_numpy()
    ai = d.away_team.map(idx).to_numpy()
    hs = d.home_score.to_numpy()
    as_ = d.away_score.to_numpy()
    neutral = d.neutral.to_numpy()

    age_days = (AS_OF - d.date).dt.days.to_numpy().astype(float)
    xi = np.log(2) / half_life_days
    w = np.exp(-xi * age_days) * d.comp_w.to_numpy()

    # log-factorial tables for the Poisson term (constant in params, kept for a real NLL).
    from scipy.special import gammaln

    lg_hs = gammaln(hs + 1)
    lg_as = gammaln(as_ + 1)

    def unpack(p):
        atk = p[:n]
        dfc = p[n:2 * n]
        ha = p[2 * n]
        rho = p[2 * n + 1]
        atk = atk - atk.mean()  # identifiability: mean attack = 0
        return atk, dfc, ha, rho

    def nll(p):
        atk, dfc, ha, rho = unpack(p)
        ha_eff = np.where(neutral, 0.0, ha)
        log_lam = ha_eff + atk[hi] - dfc[ai]
        log_mu = atk[ai] - dfc[hi]
        lam = np.exp(log_lam)
        mu = np.exp(log_mu)
        # Poisson log-likelihood for each side.
        ll = hs * log_lam - lam - lg_hs + as_ * log_mu - mu - lg_as
        # Dixon-Coles tau correction (only affects 0/1-goal cells).
        tau = np.ones_like(lam)
        m00 = (hs == 0) & (as_ == 0)
        m01 = (hs == 0) & (as_ == 1)
        m10 = (hs == 1) & (as_ == 0)
        m11 = (hs == 1) & (as_ == 1)
        tau = np.where(m00, 1 - lam * mu * rho, tau)
        tau = np.where(m01, 1 + lam * rho, tau)
        tau = np.where(m10, 1 + mu * rho, tau)
        tau = np.where(m11, 1 - rho, tau)
        tau = np.clip(tau, 1e-9, None)
        ll = ll + np.log(tau)
        return -np.sum(w * ll)

    p0 = np.concatenate([np.zeros(n), np.zeros(n), [0.25], [-0.05]])
    bounds = [(-3, 3)] * (2 * n) + [(-1, 1), (-0.2, 0.2)]
    res = minimize(nll, p0, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": 500, "maxfun": 100000})
    atk, dfc, ha, rho = unpack(res.x)
    return DixonColes(
        teams=teams,
        attack={t: float(atk[i]) for t, i in idx.items()},
        defence={t: float(dfc[i]) for t, i in idx.items()},
        home_adv=float(ha),
        rho=float(rho),
    )


# ---------------------------------------------------------------------------
# Elo
# ---------------------------------------------------------------------------
@dataclass
class Elo:
    rating: dict[str, float]
    home_adv: float
    # ordered-logit params mapping Elo diff -> 1X2: P(away) < c1 < draw < c2 < home
    slope: float
    c1: float
    c2: float

    def _logit_probs(self, diff: float) -> dict[str, float]:
        # diff = (home elo + home_adv) - away elo, on the 400-scale.
        z = self.slope * diff
        from math import exp

        F = lambda x: 1.0 / (1.0 + exp(-x))  # noqa: E731
        p_away = F(self.c1 - z)
        p_draw = F(self.c2 - z) - p_away
        p_home = 1.0 - F(self.c2 - z)
        return {"home": p_home, "draw": max(p_draw, 1e-9), "away": p_away}

    def match_probs(self, home: str, away: str, neutral: bool = True) -> dict[str, float]:
        ra = self.rating.get(home, 1500.0)
        rb = self.rating.get(away, 1500.0)
        ha = 0.0 if neutral else self.home_adv
        return self._logit_probs((ra + ha) - rb)


def fit_elo(df: pd.DataFrame, home_adv: float = 65.0, base_k: float = 40.0) -> Elo:
    """Run a World-Football-Elo-style pass over the full history, then fit the
    Elo-diff -> 1X2 mapping by ordered logit on the realised results."""
    rating: dict[str, float] = {}
    diffs, results = [], []  # collect pre-match Elo diff + outcome (0 away,1 draw,2 home)

    for r in df.sort_values("date").itertuples():
        ra = rating.get(r.home_team, 1500.0)
        rb = rating.get(r.away_team, 1500.0)
        ha = 0.0 if r.neutral else home_adv
        diff = (ra + ha) - rb

        if r.home_score > r.away_score:
            res, sa = 2, 1.0
        elif r.home_score == r.away_score:
            res, sa = 1, 0.5
        else:
            res, sa = 0, 0.0
        diffs.append(diff)
        results.append(res)

        # Expected score and margin-of-victory multiplier (World Football Elo).
        exp_a = 1.0 / (1.0 + 10 ** (-diff / 400.0))
        gd = abs(r.home_score - r.away_score)
        g = 1.0 if gd <= 1 else (1.5 if gd == 2 else (1 + 0.75 * (gd - 1) / (gd)))
        k = base_k * r.comp_w * g
        delta = k * (sa - exp_a)
        rating[r.home_team] = ra + delta
        rating[r.away_team] = rb - delta

    diffs = np.array(diffs)
    results = np.array(results)

    # Ordered logit MLE: latent z = slope*diff; cutpoints c1<c2.
    def nll(p):
        slope, c1, dc = p
        c2 = c1 + np.exp(dc)  # enforce c2 > c1
        z = slope * diffs
        from scipy.special import expit

        p_away = expit(c1 - z)
        p_draw = expit(c2 - z) - p_away
        p_home = 1 - expit(c2 - z)
        pr = np.where(results == 0, p_away, np.where(results == 1, p_draw, p_home))
        return -np.sum(np.log(np.clip(pr, 1e-12, None)))

    res = minimize(nll, np.array([0.004, -0.5, 0.0]), method="Nelder-Mead",
                   options={"maxiter": 5000, "xatol": 1e-6, "fatol": 1e-6})
    slope, c1, dc = res.x
    c2 = c1 + np.exp(dc)
    return Elo(rating=rating, home_adv=home_adv, slope=float(slope), c1=float(c1), c2=float(c2))
