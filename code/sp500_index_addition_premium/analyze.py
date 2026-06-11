"""Aggregate event-study results and produce the charts used in the blog post.

Outputs:
  data/by_period.csv         summary table: events grouped into eras
  data/avg_ar_path.csv       average abnormal-return path across all events,
                             by [pre-2010] and [post-2010]
  charts/car_by_period.png   bar chart: mean CAR by era with 95% CI
  charts/ar_path.png         line chart: avg AR around the event by era
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "data" / "event_study_results.csv"
CHARTS = ROOT / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)


def era(year: int) -> str:
    if year <  2005: return "2000-2004"
    if year <  2010: return "2005-2009"
    if year <  2015: return "2010-2014"
    if year <  2020: return "2015-2019"
    return "2020-2022"


def main() -> None:
    if not RESULTS.exists():
        sys.exit("Run event_study.py first.")
    df = pd.read_csv(RESULTS, parse_dates=["effective_date"])
    df = df.dropna(subset=["car_0_5"]).copy()

    # Filter out events with implausible single-day abnormal returns (>50%),
    # which are almost always artefacts of a corporate action (split, ticker
    # change, M&A) not properly handled by the price adjustment.
    ar_cols_init = [c for c in df.columns if c.startswith("ar_")]
    bad = (df[ar_cols_init].abs() > 0.50).any(axis=1)
    if bad.sum() > 0:
        print(f"NOTE: dropping {bad.sum()} event(s) with |AR| > 50% on some day "
              f"(corporate-action artefacts): {df.loc[bad, 'ticker'].tolist()}")
    df = df[~bad].reset_index(drop=True)

    df["era"] = df["year"].apply(era)

    # ---- Era summary table -----------------------------------------------
    car_cols = ["car_-5_-1", "car_-5_0", "car_0_1", "car_0_5", "car_0_10", "car_0_20"]
    rows = []
    for era_label, grp in df.groupby("era"):
        row = {"era": era_label, "n": len(grp)}
        for c in car_cols:
            v = grp[c].dropna()
            row[f"{c}_mean_bps"] = v.mean() * 1e4
            row[f"{c}_se_bps"]   = v.std(ddof=1) / np.sqrt(len(v)) * 1e4
        rows.append(row)
    summary = pd.DataFrame(rows).sort_values("era").reset_index(drop=True)
    summary.to_csv(ROOT / "data" / "by_period.csv", index=False)
    print("by-era summary (CAR in basis points, +/- 1 standard error):")
    cols_to_show = ["era", "n",
                    "car_-5_0_mean_bps", "car_-5_0_se_bps",
                    "car_0_5_mean_bps",  "car_0_5_se_bps",
                    "car_0_20_mean_bps", "car_0_20_se_bps"]
    print(summary[cols_to_show].round(1).to_string(index=False))
    print()

    # Pre vs post 2010
    pre  = df[df["year"] <  2010]
    post = df[df["year"] >= 2010]
    print(f"Pre-2010  : n={len(pre):3d}  mean CAR[-5,0] = {pre['car_-5_0'].mean()*1e4:+.1f} bps   "
          f"mean CAR[0,5] = {pre['car_0_5'].mean()*1e4:+.1f} bps")
    print(f"Post-2010 : n={len(post):3d}  mean CAR[-5,0] = {post['car_-5_0'].mean()*1e4:+.1f} bps   "
          f"mean CAR[0,5] = {post['car_0_5'].mean()*1e4:+.1f} bps")
    print()

    # Welch t-test on the difference
    from scipy import stats
    for col in ["car_-5_0", "car_0_5", "car_0_20"]:
        a = pre[col].dropna().values
        b = post[col].dropna().values
        t, p = stats.ttest_ind(a, b, equal_var=False)
        print(f"  {col:10s}  pre - post = {(a.mean()-b.mean())*1e4:+.1f} bps   "
              f"t = {t:+.2f}   p = {p:.3f}")
    print()

    # ---- Headline chart: CAR[-5, 0] (the run-up) by era -----------------
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    eras = summary["era"]
    means = summary["car_-5_0_mean_bps"]
    se = summary["car_-5_0_se_bps"]
    colors = ["#1f77b4" if e < "2010" else "#d62728" for e in eras]
    ax.bar(eras, means, yerr=1.96 * se, color=colors, capsize=4, alpha=0.85)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("mean cumulative abnormal return\nover [-5, 0] trading days (bps)")
    ax.set_title("S&P 500 index-addition run-up has evaporated\n"
                 "(Brown-Warner market-model CAR in the 5 days leading to inclusion)")
    for i, (m, n) in enumerate(zip(means, summary["n"])):
        ax.text(i, m + (40 if m >= 0 else -40), f"n={n}", ha="center", fontsize=10)
    ax.text(0.99, 0.02,
            "blue = pre-2010   |   red = post-2010\nerror bars: 95% CI on the mean",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
            color="#555")
    fig.tight_layout()
    fig.savefig(CHARTS / "car_runup_by_era.png", dpi=140)
    print(f"saved {CHARTS / 'car_runup_by_era.png'}")

    # ---- Cumulative AR path across the event window ---------------------
    ar_cols_sorted = sorted([c for c in df.columns if c.startswith("ar_")],
                            key=lambda c: int(c.replace("ar_", "")))
    days_full = [int(c.replace("ar_", "")) for c in ar_cols_sorted]
    pre_path = df[df["year"] <  2010][ar_cols_sorted].mean().cumsum() * 1e4
    post_path = df[df["year"] >= 2010][ar_cols_sorted].mean().cumsum() * 1e4

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(days_full, pre_path.values, marker="o", label=f"pre-2010 (n={len(pre)})",
            color="#1f77b4", markersize=4)
    ax.plot(days_full, post_path.values, marker="o", label=f"post-2010 (n={len(post)})",
            color="#d62728", markersize=4)
    ax.axvline(0, color="k", lw=0.5, linestyle="--", alpha=0.5)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("trading days relative to effective date (0 = inclusion)")
    ax.set_ylabel("cumulative abnormal return (bps)")
    ax.set_title("Cumulative abnormal return around S&P 500 inclusion")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS / "car_path.png", dpi=140)
    print(f"saved {CHARTS / 'car_path.png'}")

    # ---- Average AR path -------------------------------------------------
    ar_cols = [c for c in df.columns if c.startswith("ar_")]
    ar_pre = df[df["year"] <  2010][ar_cols].mean()
    ar_post = df[df["year"] >= 2010][ar_cols].mean()
    days = [int(c.replace("ar_", "")) for c in ar_cols]
    ar_path = pd.DataFrame({"day": days,
                            "pre_2010_bps":  (ar_pre.values * 1e4).round(2),
                            "post_2010_bps": (ar_post.values * 1e4).round(2)})
    ar_path.to_csv(ROOT / "data" / "avg_ar_path.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(days, ar_pre.values * 1e4, marker="o", label=f"pre-2010 (n={len(pre)})", color="#1f77b4")
    ax.plot(days, ar_post.values * 1e4, marker="o", label=f"post-2010 (n={len(post)})", color="#d62728")
    ax.axvline(0, color="k", lw=0.5, linestyle="--", alpha=0.5)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("trading days relative to effective date (0 = inclusion)")
    ax.set_ylabel("mean abnormal return (bps)")
    ax.set_title("Average abnormal-return path around S&P 500 inclusion")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS / "ar_path.png", dpi=140)
    print(f"saved {CHARTS / 'ar_path.png'}")


if __name__ == "__main__":
    main()
