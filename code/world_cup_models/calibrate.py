"""Out-of-sample calibration of the two models.

We can't backtest model-vs-market historically — Polymarket's World Cup book and
Hyperliquid's HIP-4 markets are weeks old, so there are no past closing lines to
mark against. What we *can* do, and must before claiming the models are worth
listening to, is check that their probabilities are calibrated out of sample.

Split: train on internationals up to 2023-12-31, test on 2024-01-01 .. 2026-06-10.
Dixon-Coles is fit once on the training window. Elo is run online (each test match
is predicted from the rating *before* it is played, then the rating updates), with
its rating->1X2 mapping fit on the training window only. We score both with:

  - RPS  (ranked probability score; the football-standard proper score for the
          ordered home/draw/away outcome — lower is better)
  - LogLoss (multiclass; lower is better)

against two naive baselines: a uniform 1/3-1/3-1/3 and the training-set base-rate.
A reliability diagram for the home-win probability shows where each model is
over- or under-confident.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

import models as M

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHARTS = HERE.parents[1] / "static" / "charts" / "world-cup-models"

TRAIN_END = pd.Timestamp("2023-12-31")
TEST_END = pd.Timestamp("2026-06-10")


def outcome_index(hs, as_):
    return 0 if hs > as_ else (1 if hs == as_ else 2)  # 0 home, 1 draw, 2 away


def rps(p, obs):
    """Ranked probability score for ordered categories [home, draw, away]."""
    cp = np.cumsum(p)
    co = np.cumsum(obs)
    return np.sum((cp[:-1] - co[:-1]) ** 2) / (len(p) - 1)


def logloss(p, idx):
    return -np.log(max(p[idx], 1e-12))


def main():
    df = M.load_results(since="2014-01-01")
    train = df[df.date <= TRAIN_END].copy()
    test = df[(df.date > TRAIN_END) & (df.date <= TEST_END)].copy()

    counts = pd.concat([train.home_team, train.away_team]).value_counts()
    universe = sorted(counts[counts >= 20].index)
    uset = set(universe)
    test = test[test.home_team.isin(uset) & test.away_team.isin(uset)].copy()
    print(f"train {len(train)} matches, test {len(test)} matches (both teams known)")

    # --- Dixon-Coles fit on train only ---
    dc = M.fit_dixon_coles(train, universe)

    # --- Elo online over train+test, predicting each test match before updating ---
    elo = M.fit_elo(train)  # ratings after train + mapping fit on train
    rating = dict(elo.rating)

    def elo_probs(home, away):
        diff = rating.get(home, 1500.0) - rating.get(away, 1500.0)  # neutral
        z = elo.slope * diff
        p_away = expit(elo.c1 - z)
        p_draw = expit(elo.c2 - z) - p_away
        p_home = 1 - expit(elo.c2 - z)
        return np.array([p_home, max(p_draw, 1e-9), p_away])

    base_rate = np.array([
        (train.home_score > train.away_score).mean(),
        (train.home_score == train.away_score).mean(),
        (train.home_score < train.away_score).mean(),
    ])
    base_rate = base_rate / base_rate.sum()
    uniform = np.array([1 / 3, 1 / 3, 1 / 3])

    scores = {m: {"rps": [], "ll": []} for m in ["dc", "elo", "base", "unif"]}
    rel = {"dc": [], "elo": []}  # (pred_home, realized_home) pairs

    for r in test.sort_values("date").itertuples():
        idx = outcome_index(r.home_score, r.away_score)
        obs = np.eye(3)[idx]
        neutral = bool(r.neutral)

        d = dc.match_probs(r.home_team, r.away_team, neutral=neutral)
        pdc = np.array([d["home"], d["draw"], d["away"]])
        pelo = elo_probs(r.home_team, r.away_team)
        if not neutral:  # add home edge for elo when not neutral
            diff = rating.get(r.home_team, 1500.0) + elo.home_adv - rating.get(r.away_team, 1500.0)
            z = elo.slope * diff
            pa = expit(elo.c1 - z); pd_ = expit(elo.c2 - z) - pa
            pelo = np.array([1 - expit(elo.c2 - z), max(pd_, 1e-9), pa])

        for m, p in [("dc", pdc), ("elo", pelo), ("base", base_rate), ("unif", uniform)]:
            p = p / p.sum()
            scores[m]["rps"].append(rps(p, obs))
            scores[m]["ll"].append(logloss(p, idx))
        rel["dc"].append((pdc[0] / pdc.sum(), 1 if idx == 0 else 0))
        rel["elo"].append((pelo[0] / pelo.sum(), 1 if idx == 0 else 0))

        # update Elo after the match (online)
        ra = rating.get(r.home_team, 1500.0); rb = rating.get(r.away_team, 1500.0)
        ha = 0.0 if r.neutral else elo.home_adv
        sa = 1.0 if idx == 0 else (0.5 if idx == 1 else 0.0)
        exp_a = 1.0 / (1.0 + 10 ** (-((ra + ha) - rb) / 400.0))
        gd = abs(r.home_score - r.away_score)
        g = 1.0 if gd <= 1 else (1.5 if gd == 2 else (1 + 0.75 * (gd - 1) / gd))
        k = 40.0 * r.comp_w * g
        delta = k * (sa - exp_a)
        rating[r.home_team] = ra + delta
        rating[r.away_team] = rb - delta

    summary = {m: {"rps": float(np.mean(s["rps"])), "logloss": float(np.mean(s["ll"]))}
               for m, s in scores.items()}
    summary["n_test"] = int(len(test))
    print("\n=== Out-of-sample (2024 - 2026.06) ===")
    print(f"{'model':6s} {'RPS':>8} {'LogLoss':>9}")
    for m in ["dc", "elo", "base", "unif"]:
        print(f"{m:6s} {summary[m]['rps']:8.4f} {summary[m]['logloss']:9.4f}")

    # reliability (home-win), 10 bins
    reliability = {}
    for m in ["dc", "elo"]:
        arr = np.array(rel[m])
        bins = np.linspace(0, 1, 11)
        which = np.clip(np.digitize(arr[:, 0], bins) - 1, 0, 9)
        pts = []
        for b in range(10):
            sel = which == b
            if sel.sum() >= 10:
                pts.append({"pred": float(arr[sel, 0].mean()),
                            "obs": float(arr[sel, 1].mean()), "n": int(sel.sum())})
        reliability[m] = pts

    out = {"summary": summary, "reliability": reliability,
           "train_end": str(TRAIN_END.date()), "test_end": str(TEST_END.date())}
    (DATA / "calibration.json").write_text(json.dumps(out, indent=2))
    print(f"\nsaved {DATA / 'calibration.json'}")

    _chart(reliability, summary)


def _chart(reliability, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    CHARTS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 6.6))
    ax.plot([0, 1], [0, 1], color="#888", ls="--", lw=1, label="perfect calibration")
    for m, col, lab in [("dc", "#1f77b4", "Dixon-Coles"), ("elo", "#2a9d8f", "Elo")]:
        pts = reliability[m]
        ax.plot([p["pred"] for p in pts], [p["obs"] for p in pts], "-o", color=col,
                label=f"{lab}  (RPS {summary[m]['rps']:.3f})")
    ax.set_xlabel("predicted P(home win), out-of-sample")
    ax.set_ylabel("observed frequency of home win")
    ax.set_title("Are the models calibrated? Reliability on held-out matches\n"
                 "(2024 - Jun 2026, internationals)")
    ax.legend(loc="upper left"); ax.grid(alpha=0.2)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(CHARTS / "calibration_reliability.png", dpi=140)
    print(f"chart -> {CHARTS / 'calibration_reliability.png'}")


if __name__ == "__main__":
    main()
