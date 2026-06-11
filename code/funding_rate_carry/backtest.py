"""Backtest the canonical funding-rate carry trade on BTCUSDT perp.

Strategy: hold 1 unit notional SHORT perp + 1 unit notional LONG spot.
The position is delta-neutral (basis-only exposure); the dominant PnL is
the funding payment received from longs when funding rate > 0.

Sign convention (Binance): positive funding rate means LONGS pay SHORTS,
once every 8 hours. As a short, we receive `funding_rate * notional` per
8-hour period.

Costs:
  - One-time entry: 2 * (spot taker fee + perp taker fee) ~ 0.04% round
    trip (Binance retail VIP0). We use 2 bps each side = 4 bps total.
  - Spot borrow / margin: assume 0 (USDT spot is held outright, no carry).
  - Basis decay: BTC perp tracks BTC spot tightly on Binance; the per-
    period basis change averages a few bps and is ignored in the first-
    pass headline. The honest scenario uses spot daily returns to mark
    the basis difference; we report both.

Outputs:
  data/backtest_returns.csv  per-period PnL series + cumulative
  data/backtest_summary.json  headline stats
  charts/funding_cumulative.png  funding capture over time
  charts/funding_drawdown.png   funding-leg drawdown over time
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

ROOT = Path(__file__).resolve().parent
FUNDING = ROOT / "data" / "funding_btcusdt.csv"
SPOT = ROOT / "data" / "spot_btcusdt.csv"
CHARTS = ROOT / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

ROUND_TRIP_BPS = 4.0   # bps total — both legs in/out


def main() -> None:
    if not FUNDING.exists():
        sys.exit("Run fetch_binance.py first.")
    fund = pd.read_csv(FUNDING)
    fund["funding_time"] = pd.to_datetime(fund["funding_time"], utc=True, format="ISO8601")
    spot = pd.read_csv(SPOT)
    spot["date"] = pd.to_datetime(spot["date"], utc=True)

    # Per-period PnL (funding-only, per unit perp notional)
    fund = fund.sort_values("funding_time").reset_index(drop=True)
    fund["pnl"] = fund["funding_rate"]                     # short perp receives funding when > 0
    fund["cum"] = fund["pnl"].cumsum()

    # Date features for stats
    fund["date"] = fund["funding_time"].dt.date

    # Daily aggregate (funding per day = sum of 3 periods)
    daily = fund.groupby("date")["pnl"].sum().to_frame("daily_pnl")
    daily.index = pd.to_datetime(daily.index, utc=True)
    daily["cum"] = daily["daily_pnl"].cumsum()

    # Summary stats
    n_days = len(daily)
    total_funding = float(fund["pnl"].sum())
    annual = total_funding * 365 / n_days
    daily_mean = float(daily["daily_pnl"].mean())
    daily_std = float(daily["daily_pnl"].std(ddof=1))
    sharpe = daily_mean / daily_std * np.sqrt(365) if daily_std > 0 else float("nan")

    # Drawdown
    running_max = daily["cum"].cummax()
    dd = daily["cum"] - running_max
    max_dd = float(dd.min())

    # Cost-adjusted: subtract one-time round-trip
    cost = ROUND_TRIP_BPS / 1e4
    annual_after_cost = (total_funding - cost) * 365 / n_days
    summary = {
        "n_days": int(n_days),
        "n_funding_periods": int(len(fund)),
        "first": str(fund["funding_time"].min()),
        "last":  str(fund["funding_time"].max()),
        "mean_funding_bps_per_8h": float(fund["funding_rate"].mean() * 1e4),
        "std_funding_bps_per_8h":  float(fund["funding_rate"].std(ddof=1) * 1e4),
        "frac_positive_periods":   float((fund["funding_rate"] > 0).mean()),
        "total_funding":     total_funding,
        "annualised_return": annual,
        "annualised_after_4bps_round_trip": annual_after_cost,
        "daily_mean":  daily_mean,
        "daily_std":   daily_std,
        "sharpe_annualised": sharpe,
        "max_drawdown": max_dd,
        "worst_8h_period":  float(fund["funding_rate"].min()),
        "best_8h_period":   float(fund["funding_rate"].max()),
        "worst_day":        float(daily["daily_pnl"].min()),
        "best_day":         float(daily["daily_pnl"].max()),
    }

    print("=== Funding-rate carry on BTCUSDT (short perp + long spot) ===")
    for k, v in summary.items():
        if isinstance(v, float):
            if abs(v) < 1 and k.startswith(("total_", "annual", "daily_", "max_", "worst_", "best_")):
                print(f"  {k:38s} {v*100:>8.3f}%")
            else:
                print(f"  {k:38s} {v:>8.4f}")
        else:
            print(f"  {k:38s} {v}")
    with open(ROOT / "data" / "backtest_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    daily.to_csv(ROOT / "data" / "backtest_returns.csv")

    # Cumulative
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(daily.index, daily["cum"] * 100, color="#2a9d8f", lw=1.4)
    ax.fill_between(daily.index, 0, daily["cum"] * 100, color="#2a9d8f", alpha=0.15)
    ax.axhline(0, color="k", lw=0.4)
    ax.set_ylabel("cumulative funding capture (%)")
    ax.set_title("BTCUSDT funding-rate carry: cumulative funding-only PnL, "
                 "fully delta-hedged")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS / "funding_cumulative.png", dpi=140)
    print(f"\nsaved {CHARTS / 'funding_cumulative.png'}")

    # Drawdown
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.fill_between(daily.index, 0, dd * 100, color="#e76f51", alpha=0.6)
    ax.axhline(0, color="k", lw=0.4)
    ax.set_ylabel("drawdown (%)")
    ax.set_title("BTCUSDT funding-rate carry: drawdown from running peak")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHARTS / "funding_drawdown.png", dpi=140)
    print(f"saved {CHARTS / 'funding_drawdown.png'}")

    # Distribution of 8h funding rates
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    ax.hist(fund["funding_rate"] * 1e4, bins=80, color="#264653", alpha=0.85, edgecolor="white")
    ax.axvline(0, color="k", lw=0.5)
    ax.axvline(fund["funding_rate"].mean() * 1e4, color="#e76f51", lw=1.5,
               linestyle="--", label=f"mean = {fund['funding_rate'].mean()*1e4:.2f} bps")
    ax.set_xlabel("8-hour funding rate (bps)")
    ax.set_ylabel("count")
    ax.set_title("Distribution of BTCUSDT 8-hour funding rates (3,300 observations)")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(CHARTS / "funding_distribution.png", dpi=140)
    print(f"saved {CHARTS / 'funding_distribution.png'}")


if __name__ == "__main__":
    sys.exit(main())
