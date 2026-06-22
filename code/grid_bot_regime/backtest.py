"""When does a grid / market-making bot actually make money?

A grid bot fades moves: it buys as price falls and sells as it rises, holding
inventory that leans *against* the trend. In the fine-grid limit this is a linear
mean-reversion inventory rule:

    I(p) = clip( -alpha * (p - center) / (center * band),  -alpha, +alpha )

i.e. maximally long at the bottom of the band, maximally short at the top, flat at
the centre. Its step P&L is just inventory times the next price move,
    pnl_t = I_t * (p_{t+1} - p_t),
minus a turnover cost on every inventory change. That makes the grid an explicit
bet on mean reversion: it prints in choppy/range-bound markets and bleeds when a
trend runs the inventory to the band edge and keeps going.

We deploy a fresh grid each week on hourly BTC, then bucket every week's return by
its **trend strength** and **realized volatility** — the exact axes the
Schmidhuber 'trends, volatility & critical phenomena' paper uses to model returns
(cubic in trend) and vol (rises in strong trends).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHARTS = HERE.parents[1] / "static" / "charts" / "grid-bot-regime"

WINDOW = 168       # 1 week of hourly bars
BAND = 0.10        # grid spans +/-10% around the week's opening price
ALPHA = 1.0        # max units of inventory at the band edge (normalised)
FEE = 1e-4         # 1 bp per unit of notional turned over (maker-ish)
HOURS_PER_YEAR = 24 * 365


def load():
    df = pd.read_csv(DATA / "btc_1h.csv")
    df["ret"] = np.log(df.close).diff()
    return df


def run_window(close: np.ndarray):
    """Return dict of this window's grid economics + regime stats."""
    center = close[0]
    # target inventory at each bar (fade the move), capped at the band edge
    I = np.clip(-ALPHA * (close - center) / (center * BAND), -ALPHA, ALPHA)
    dp = np.diff(close)
    pnl = I[:-1] * dp                      # mark-to-market of holding I over each step
    turnover = np.abs(np.diff(I))          # units traded each bar
    cost = FEE * turnover * close[:-1]
    net = pnl.sum() - cost.sum()
    max_notional = ALPHA * center          # capital that backs the max inventory
    ret = net / max_notional               # return on deployed notional
    # regime descriptors
    logret = np.diff(np.log(close))
    vol_ann = float(np.std(logret) * np.sqrt(HOURS_PER_YEAR)) if len(logret) > 1 else np.nan
    drift = close[-1] / close[0] - 1.0
    # trend strength = normalised drift (signed): total move per unit of wiggle
    sigma_path = np.std(logret) * np.sqrt(len(logret)) if len(logret) > 1 else np.nan
    trend = float(np.log(close[-1] / close[0]) / sigma_path) if sigma_path else np.nan
    return {"ret": float(ret), "net": float(net), "gross": float(pnl.sum()),
            "cost": float(cost.sum()), "vol_ann": vol_ann, "drift": float(drift),
            "trend": trend, "abs_trend": abs(trend)}


def main():
    df = load()
    close = df.close.to_numpy()
    n = len(close)
    rows = []
    for s in range(0, n - WINDOW, WINDOW):
        w = close[s:s + WINDOW]
        r = run_window(w)
        r["start_ts"] = int(df.ts.iloc[s])
        rows.append(r)
    res = pd.DataFrame(rows).dropna(subset=["trend", "vol_ann"])
    print(f"{len(res)} weekly grid deployments on hourly BTC")

    # headline
    summary = {
        "n_weeks": int(len(res)),
        "mean_week_ret_pct": round(float(res.ret.mean()) * 100, 3),
        "pct_weeks_positive": round(float((res.net > 0).mean()) * 100, 1),
        "fee_bps": FEE * 1e4, "band": BAND, "window_h": WINDOW,
    }
    # by trend-strength quartile
    res["trend_q"] = pd.qcut(res.abs_trend, 4, labels=["calm", "mild", "trending", "strong"])
    by_trend = res.groupby("trend_q", observed=True).ret.mean().mul(100).round(3).to_dict()
    # by vol quartile
    res["vol_q"] = pd.qcut(res.vol_ann, 4, labels=["low", "mid", "high", "extreme"])
    by_vol = res.groupby("vol_q", observed=True).ret.mean().mul(100).round(3).to_dict()
    summary["ret_by_trend_pct"] = by_trend
    summary["ret_by_vol_pct"] = by_vol
    # correlations
    summary["corr_ret_abs_trend"] = round(float(res.ret.corr(res.abs_trend)), 3)
    summary["corr_ret_vol"] = round(float(res.ret.corr(res.vol_ann)), 3)
    print(json.dumps(summary, indent=2))
    (DATA / "results.json").write_text(json.dumps(
        {"summary": summary, "rows": res.to_dict("records")}, indent=2, default=str))

    _charts(df, res, summary)


def _charts(df, res, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    CHARTS.mkdir(parents=True, exist_ok=True)
    BL, OR, GR, RED = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728"

    # 1) grid weekly return vs trend strength (the core result)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axhline(0, color="#444", lw=0.8)
    ax.scatter(res.trend, res.ret * 100, s=22, color=BL, alpha=0.55)
    # cubic fit (echoing the paper's cubic-in-trend return model)
    x = res.trend.to_numpy(); y = res.ret.to_numpy() * 100
    z = np.polyfit(x, y, 3); xs = np.linspace(x.min(), x.max(), 200)
    ax.plot(xs, np.polyval(z, xs), color=RED, lw=2, label="cubic fit (cf. Schmidhuber)")
    ax.set_xlabel("week trend strength  (signed normalised drift)")
    ax.set_ylabel("grid return that week (%)")
    ax.set_title("A grid bot is short the trend\nIt earns near zero trend, loses in strong trends")
    ax.legend(); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "ret_vs_trend.png", dpi=140); plt.close(fig)

    # 2) return by trend quartile + by vol quartile (bars)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    t = summary["ret_by_trend_pct"]
    axes[0].bar(list(t.keys()), list(t.values()),
                color=[GR if v > 0 else OR for v in t.values()])
    axes[0].axhline(0, color="#444", lw=0.8); axes[0].set_title("Grid return by trend strength")
    axes[0].set_ylabel("mean weekly return (%)"); axes[0].grid(axis="y", alpha=0.2)
    v = summary["ret_by_vol_pct"]
    axes[1].bar(list(v.keys()), list(v.values()),
                color=[GR if val > 0 else OR for val in v.values()])
    axes[1].axhline(0, color="#444", lw=0.8); axes[1].set_title("Grid return by volatility")
    axes[1].grid(axis="y", alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "ret_by_regime.png", dpi=140); plt.close(fig)

    # 3) two illustrative weeks: a calm one (profit) vs a trending one (loss)
    calm = res.loc[res[res.abs_trend < res.abs_trend.quantile(0.2)].ret.idxmax()]
    trend = res.loc[res[res.abs_trend > res.abs_trend.quantile(0.8)].ret.idxmin()]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, row, lab in [(axes[0], calm, "calm week → grid profits"),
                         (axes[1], trend, "trending week → grid bleeds")]:
        s = df.index[df.ts == row.start_ts][0]
        w = df.close.to_numpy()[s:s + WINDOW]
        ax.plot(range(len(w)), w, color=BL)
        ax.set_title(f"{lab}\n(grid return {row.ret*100:+.1f}%)", fontsize=11)
        ax.set_xlabel("hour"); ax.grid(alpha=0.2)
    axes[0].set_ylabel("BTC price ($)")
    fig.tight_layout(); fig.savefig(CHARTS / "two_weeks.png", dpi=140); plt.close(fig)
    print(f"charts -> {CHARTS}")


if __name__ == "__main__":
    main()
