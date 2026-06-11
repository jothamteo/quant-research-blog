"""Calibration analysis of resolved Manifold prediction markets.

Inputs: data/resolved_markets.csv (from fetch_markets.py).
Outputs:
  data/calibration_bins.csv     binned reliability diagram (overall)
  data/calibration_by_volume.csv reliability diagram by volume tier
  data/scores.json              Brier + log scores vs baselines
  charts/reliability_overall.png   the reliability diagram
  charts/reliability_by_volume.png by-volume comparison
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scipy import stats

ROOT = Path(__file__).resolve().parent
INP = ROOT / "data" / "resolved_markets.csv"
CHARTS = ROOT / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

EPS = 1e-9


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    phat = k / n
    denom = 1 + z ** 2 / n
    centre = (phat + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2)) / denom
    return centre - half, centre + half


def reliability_bins(df: pd.DataFrame, n_bins: int = 10) -> pd.DataFrame:
    """Equal-width bins on [0, 1] for closing probability."""
    edges = np.linspace(0, 1, n_bins + 1)
    rows = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if i == n_bins - 1:
            mask = (df["p_close"] >= lo) & (df["p_close"] <= hi)
        else:
            mask = (df["p_close"] >= lo) & (df["p_close"] < hi)
        sub = df[mask]
        n = len(sub)
        k = int(sub["y_obs"].sum())
        rate = k / n if n else np.nan
        lo_ci, hi_ci = wilson_ci(k, n)
        rows.append({
            "bin_lo": lo, "bin_hi": hi,
            "mid": (lo + hi) / 2,
            "n": n,
            "k_yes": k,
            "mean_p": sub["p_close"].mean() if n else np.nan,
            "obs_rate": rate,
            "ci_lo": lo_ci, "ci_hi": hi_ci,
        })
    return pd.DataFrame(rows)


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def log_score(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, EPS, 1 - EPS)
    return float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def expected_calibration_error(df: pd.DataFrame, n_bins: int = 20) -> float:
    """Weighted L1 calibration error across equal-width bins."""
    edges = np.linspace(0, 1, n_bins + 1)
    out = 0.0
    n = len(df)
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if i == n_bins - 1:
            mask = (df["p_close"] >= lo) & (df["p_close"] <= hi)
        else:
            mask = (df["p_close"] >= lo) & (df["p_close"] < hi)
        if mask.sum() == 0:
            continue
        sub = df[mask]
        rate = sub["y_obs"].mean()
        mean_p = sub["p_close"].mean()
        out += (mask.sum() / n) * abs(mean_p - rate)
    return float(out)


def volume_tier(v: float) -> str:
    if pd.isna(v): return "unknown"
    if v < 100:    return "low (<M$100)"
    if v < 1000:   return "mid (M$100-1k)"
    return "high (>=M$1k)"


def main() -> None:
    if not INP.exists():
        sys.exit("Run fetch_markets.py first.")
    df = pd.read_csv(INP).dropna(subset=["p_close", "y_obs"]).reset_index(drop=True)
    p = df["p_close"].values
    y = df["y_obs"].values.astype(int)
    base = float(y.mean())
    n = len(df)
    print(f"n markets        : {n:,}")
    print(f"base rate (YES)  : {base:.3f}")
    print(f"mean p_close     : {p.mean():.3f}")
    print()

    # Overall calibration bins
    bins = reliability_bins(df, n_bins=10)
    bins.to_csv(ROOT / "data" / "calibration_bins.csv", index=False)
    print("reliability bins (10):")
    cols = ["bin_lo", "bin_hi", "n", "mean_p", "obs_rate", "ci_lo", "ci_hi"]
    print(bins[cols].round(3).to_string(index=False))
    print()

    # Scores vs baselines
    scores = {
        "n_markets": n,
        "base_rate_yes": base,
        "brier_market": brier(p, y),
        "brier_baseline_05": brier(np.full_like(y, 0.5, dtype=float), y),
        "brier_baseline_base": brier(np.full_like(y, base, dtype=float), y),
        "log_market": log_score(p, y),
        "log_baseline_05": log_score(np.full_like(y, 0.5, dtype=float), y),
        "log_baseline_base": log_score(np.full_like(y, base, dtype=float), y),
        "ece_market": expected_calibration_error(df, n_bins=20),
    }
    print("scores:")
    for k, v in scores.items():
        print(f"  {k:24s} {v:>8.4f}")
    with open(ROOT / "data" / "scores.json", "w") as f:
        json.dump(scores, f, indent=2)
    print()

    # By volume tier
    df["tier"] = df["volume"].apply(volume_tier)
    tier_rows = []
    print("by volume tier:")
    for tier, sub in df.groupby("tier"):
        if len(sub) < 50: continue
        t_p = sub["p_close"].values
        t_y = sub["y_obs"].values.astype(int)
        row = {
            "tier": tier,
            "n": len(sub),
            "base_rate": t_y.mean(),
            "brier": brier(t_p, t_y),
            "log": log_score(t_p, t_y),
            "ece": expected_calibration_error(sub, n_bins=10),
        }
        tier_rows.append(row)
        print(f"  {tier:18s} n={len(sub):4d}  brier={row['brier']:.4f}  "
              f"log={row['log']:.4f}  ece={row['ece']:.4f}")
    tier_df = pd.DataFrame(tier_rows)
    tier_df.to_csv(ROOT / "data" / "calibration_by_volume.csv", index=False)
    print()

    # ---- Reliability diagram (overall) -----------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 7),
                                   gridspec_kw={"height_ratios": [3, 1]},
                                   sharex=True)
    valid = bins["n"] > 0
    ax1.plot([0, 1], [0, 1], color="#888", linestyle="--", lw=1, label="perfect calibration")
    yerr_lo = bins.loc[valid, "obs_rate"] - bins.loc[valid, "ci_lo"]
    yerr_hi = bins.loc[valid, "ci_hi"] - bins.loc[valid, "obs_rate"]
    ax1.errorbar(bins.loc[valid, "mean_p"], bins.loc[valid, "obs_rate"],
                 yerr=[yerr_lo, yerr_hi],
                 fmt="o", color="#1f77b4", capsize=4, markersize=7,
                 label="Manifold (closing probability)")
    ax1.set_ylabel("observed YES frequency")
    ax1.set_title(f"Calibration of Manifold prediction markets at close "
                  f"(n = {n:,} resolved binary)")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.3)
    ax1.set_xlim(-0.02, 1.02); ax1.set_ylim(-0.02, 1.02)

    # Density of predictions
    ax2.hist(p, bins=np.linspace(0, 1, 21), color="#1f77b4", alpha=0.7, edgecolor="white")
    ax2.set_xlabel("closing probability")
    ax2.set_ylabel("count")
    ax2.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(CHARTS / "reliability_overall.png", dpi=140)
    print(f"saved {CHARTS / 'reliability_overall.png'}")

    # ---- Reliability diagram by volume tier -----------------------------
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot([0, 1], [0, 1], color="#888", linestyle="--", lw=1, label="perfect")
    colors = {"low (<M$100)": "#e76f51", "mid (M$100-1k)": "#f4a261", "high (>=M$1k)": "#2a9d8f"}
    for tier in ["low (<M$100)", "mid (M$100-1k)", "high (>=M$1k)"]:
        sub = df[df["tier"] == tier]
        if len(sub) < 50: continue
        b = reliability_bins(sub, n_bins=8)
        valid = b["n"] > 0
        ax.plot(b.loc[valid, "mean_p"], b.loc[valid, "obs_rate"],
                marker="o", label=f"{tier} (n={len(sub):,})",
                color=colors.get(tier, "#888"))
    ax.set_xlabel("closing probability")
    ax.set_ylabel("observed YES frequency")
    ax.set_title("Manifold calibration by market volume tier")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS / "reliability_by_volume.png", dpi=140)
    print(f"saved {CHARTS / 'reliability_by_volume.png'}")


if __name__ == "__main__":
    sys.exit(main())
