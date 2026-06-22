"""Analyse the Polymarket-vs-Deribit binary gap and draw the post's charts."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHARTS = HERE.parents[1] / "static" / "charts" / "pm-vs-options"


def main():
    raw = json.load(open(DATA / "rows.json"))
    df = pd.DataFrame(raw["rows"])
    gaps = df.gap_pp.to_numpy()
    n = len(df)
    mean = gaps.mean()
    se = gaps.std(ddof=1) / np.sqrt(n)
    t = mean / se
    summary = {
        "fetched_at_utc": raw["fetched_at_utc"], "n": int(n),
        "mean_gap_pp": round(float(mean), 2),
        "mean_abs_gap_pp": round(float(np.abs(gaps).mean()), 2),
        "naive_t": round(float(t), 2),
        "pct_pm_rich": round(float((gaps > 0).mean() * 100), 1),
        "dates": sorted(df.date.unique().tolist()),
    }
    # cross-section: gap vs option-implied probability (paper: wedge largest at low prob)
    lo = df[df.opt_prob < 0.25]; hi = df[df.opt_prob > 0.75]; mid = df[(df.opt_prob >= 0.25) & (df.opt_prob <= 0.75)]
    summary["gap_low_prob"] = round(float(lo.gap_pp.mean()), 2) if len(lo) else None
    summary["gap_mid_prob"] = round(float(mid.gap_pp.mean()), 2) if len(mid) else None
    summary["gap_high_prob"] = round(float(hi.gap_pp.mean()), 2) if len(hi) else None
    print(json.dumps(summary, indent=2))
    (DATA / "results.json").write_text(json.dumps(
        {"summary": summary, "june26": df[df.date == "2026-06-26"].to_dict("records")}, indent=2))

    _charts(df, summary)


def _charts(df, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    CHARTS.mkdir(parents=True, exist_ok=True)
    BL, OR, GR = "#1f77b4", "#e76f51", "#2a9d8f"

    # 1) June 26: PM Yes vs Deribit-implied across strikes
    d = df[df.date == "2026-06-26"].sort_values("strike")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(d.strike / 1000, d.pm_yes * 100, "-o", color=OR, label="Polymarket Yes")
    ax.plot(d.strike / 1000, d.opt_prob * 100, "-s", color=BL, label="Deribit option-implied")
    ax.set_xlabel("strike ($000)"); ax.set_ylabel("P(BTC > strike) %")
    ax.set_title("Same bet, two venues: 'BTC above K on 26 Jun'\nPolymarket Yes vs Deribit-implied binary")
    ax.legend(); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "june26_curves.png", dpi=140); plt.close(fig)

    # 2) gap vs implied probability (cross-section)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axhline(0, color="#444", lw=0.8)
    ax.scatter(df.opt_prob * 100, df.gap_pp, s=34, color=BL, alpha=0.8)
    z = np.polyfit(df.opt_prob * 100, df.gap_pp, 1)
    xs = np.linspace(0, 100, 50)
    ax.plot(xs, np.polyval(z, xs), color=OR, lw=2, label=f"fit (slope {z[0]:+.3f}pp per %)")
    ax.set_xlabel("Deribit option-implied probability (%)")
    ax.set_ylabel("gap = Polymarket − Deribit (pp)")
    ax.set_title(f"Where's the wedge? Gap vs implied probability\n"
                 f"{summary['n']} obs, June 22–26 · mean {summary['mean_gap_pp']:+.2f}pp")
    ax.legend(); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "gap_vs_prob.png", dpi=140); plt.close(fig)
    print(f"charts -> {CHARTS}")


if __name__ == "__main__":
    main()
