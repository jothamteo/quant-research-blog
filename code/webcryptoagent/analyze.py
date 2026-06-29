"""WebCryptoAgent, reality-checked against the tape it traded.

WebCryptoAgent (arXiv:2601.04687) fuses web text, social sentiment and OHLCV into
an hourly "strategic" trading decision, guarded by a fast second-level risk model.
It is evaluated on BTCUSDT and ETHUSDT over 2025-01-05 → 2026-01-05 with ~122
strategic decision points, and reports *relative* gains in stability, spurious-
activity and tail-risk versus baselines.

This script does not reproduce the agent (its code/metrics are pending release).
It does the two things a reader actually needs to size the claim, both from the
real price path the agent traded against:

  1. The benchmark. What did buy-and-hold BTC and ETH do over the *exact* window?
     If the benchmark lost money, "reduced activity / better tail-risk" is the
     trivially winning behaviour, and the bar is "did it beat sitting in cash / a
     flat book", not "did it beat a bull market".

  2. The luck floor. With only N=122 decisions in the year, how wide is the
     distribution of outcomes from *random* decisions on the same tape, and how
     large an annualized Sharpe must a strategy post before it is statistically
     distinguishable from luck? (Closed form: the standard error on an annualized
     Sharpe estimated from N decisions is ~ sqrt((1 + 0.5*SR^2)/N) on the
     per-decision Sharpe, which annualizes to ~1.0 at N=122 — so a Sharpe near 1
     is ~1 sigma from zero.)

Outputs: printed metrics (every number in the post) + three charts under
static/charts/webcryptoagent/. Pure numpy/pandas/matplotlib; data via fetch_data.py.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHARTS = HERE.parents[1] / "static" / "charts" / "webcryptoagent"
CHARTS.mkdir(parents=True, exist_ok=True)

N_DECISIONS = 122          # the paper's strategic-decision count over the window
HOURS_PER_YEAR = 24 * 365
ANN = np.sqrt(HOURS_PER_YEAR)
RNG = np.random.default_rng(7)

# muted house palette
BTC_C, ETH_C = "#e0922f", "#5b7fb0"
ACC, GREY = "#c0473b", "#444444"


def load(fname: str) -> pd.Series:
    df = pd.read_csv(DATA / fname, parse_dates=["time"]).set_index("time")
    return df["close"].astype(float)


def buy_and_hold(px: pd.Series) -> dict:
    r = np.log(px).diff().dropna().values          # hourly log returns
    total = px.iloc[-1] / px.iloc[0] - 1
    vol_ann = r.std(ddof=1) * ANN
    sharpe = r.mean() / r.std(ddof=1) * ANN
    # max drawdown on the price path
    peak = np.maximum.accumulate(px.values)
    mdd = ((px.values - peak) / peak).min()
    return dict(total=total, vol_ann=vol_ann, sharpe=sharpe, mdd=mdd, r=r)


def decision_log_returns(px: pd.Series, n: int) -> np.ndarray:
    """Log return of the asset between n evenly-spaced decision points."""
    idx = np.linspace(0, len(px) - 1, n + 1).round().astype(int)
    p = px.values[idx]
    return np.log(p[1:] / p[:-1])


def monte_carlo(seg: np.ndarray, policy: str, sims: int = 50_000):
    """Random agent over the decision-spaced returns `seg`.

    policy 'long_flat'   : each decision independently long (1) or flat (0), 50/50
    policy 'long_flat_short': position in {-1,0,1} uniformly
    Returns arrays of terminal simple return and annualized Sharpe per sim.
    """
    n = len(seg)
    if policy == "long_flat":
        pos = RNG.integers(0, 2, size=(sims, n))            # 0 or 1
    else:
        pos = RNG.integers(-1, 2, size=(sims, n))           # -1,0,1
    pnl = pos * seg                                         # log-return contribution
    term = np.exp(pnl.sum(axis=1)) - 1.0                    # compounded terminal return
    mu = pnl.mean(axis=1)
    sd = pnl.std(axis=1, ddof=1)
    sd[sd == 0] = np.nan
    sharpe = mu / sd * np.sqrt(n)                           # annualized (n decisions/yr)
    return term, sharpe


def sharpe_se_years(sr_ann: float, years: float) -> float:
    """Lo (2002) SE of an *annualized* Sharpe estimated from `years` of data.

    SE(SR_ann) ~ sqrt((1 + 0.5*SR_ann^2) / T_years). The key fact: it depends on
    calendar time, not on how finely you chop the year into decisions — slicing one
    year into 122 vs 2000 decisions does not shrink it. At T=1yr it is ~1.0.
    """
    return np.sqrt((1 + 0.5 * sr_ann ** 2) / years)


def min_detectable_sharpe(years: float) -> float:
    """Smallest annualized Sharpe that clears 2 SE of the SR=0 null: 2/sqrt(T)."""
    return 2.0 / np.sqrt(years)


def main():
    btc, eth = load("btc_1h.csv"), load("eth_1h.csv")
    print(f"window {btc.index[0].date()} -> {btc.index[-1].date()}  "
          f"({len(btc)} hourly bars)\n")

    print("=== Buy-and-hold benchmark over the exact eval window ===")
    bh = {}
    for name, px in [("BTC", btc), ("ETH", eth)]:
        m = buy_and_hold(px)
        bh[name] = m
        print(f"  {name}: total {m['total']*100:+6.1f}%   ann.vol {m['vol_ann']*100:5.1f}%   "
              f"Sharpe {m['sharpe']:+5.2f}   maxDD {m['mdd']*100:6.1f}%")
    # equal-weight BT C/ETH buy & hold
    ew = 0.5 * (btc / btc.iloc[0]) + 0.5 * (eth / eth.iloc[0])
    ew_total = ew.iloc[-1] - 1
    print(f"  50/50 BTC+ETH buy&hold total {ew_total*100:+.1f}%\n")

    print(f"=== Luck floor at N={N_DECISIONS} decisions (random agents on the real tape) ===")
    mc = {}
    for name, px in [("BTC", btc), ("ETH", eth)]:
        seg = decision_log_returns(px, N_DECISIONS)
        term_lf, sh_lf = monte_carlo(seg, "long_flat")
        term_lfs, sh_lfs = monte_carlo(seg, "long_flat_short")
        mc[name] = (seg, term_lf, sh_lf, term_lfs, sh_lfs)
        p5, p95 = np.nanpercentile(term_lfs, [5, 95]) * 100
        print(f"  {name} long/flat/short: terminal return  mean {np.nanmean(term_lfs)*100:+5.1f}%  "
              f"std {np.nanstd(term_lfs)*100:4.1f}%  [5%,95%]=[{p5:+.1f}%, {p95:+.1f}%]")
        print(f"  {name} long/flat/short: annualized Sharpe std from luck alone = "
              f"{np.nanstd(sh_lfs):.2f}")
    se = sharpe_se_years(0.0, 1.0)
    print(f"\n  Closed-form SE on annualized Sharpe from 1 year of data: ~{se:.2f}")
    print(f"  (matches the Monte-Carlo luck std above; set by calendar time, not decision count)")
    print(f"  -> Sharpe must exceed ~{min_detectable_sharpe(1.0):.1f} (2 SE) to clear luck at 95% confidence.")
    # years to detect a true Sharpe of 1.0 at the 2-SE bar?
    target = 1.0
    yrs_needed = next(y for y in np.arange(1.0, 30.0, 0.5)
                      if min_detectable_sharpe(y) <= target)
    print(f"  -> to call a true Sharpe of {target:.1f} 'real' you need ~{yrs_needed:.0f} years "
          f"of out-of-sample tape, not 1.\n")

    # ---- Chart 1: the regime the agent was tested in -------------------------
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(btc.index, btc / btc.iloc[0] * 100, color=BTC_C, lw=1.6,
            label=f"BTC buy&hold  ({bh['BTC']['total']*100:+.1f}%)")
    ax.plot(eth.index, eth / eth.iloc[0] * 100, color=ETH_C, lw=1.6,
            label=f"ETH buy&hold  ({bh['ETH']['total']*100:+.1f}%)")
    ax.axhline(100, color=GREY, lw=0.9, ls="--")
    ax.set_title("The tape WebCryptoAgent was graded on (2025-01-05 → 2026-01-05)")
    ax.set_ylabel("normalized price (start = 100)")
    ax.legend(frameon=False, loc="lower left")
    ax.margins(x=0.01)
    fig.tight_layout(); fig.savefig(CHARTS / "regime.png", dpi=150); plt.close(fig)

    # ---- Chart 2: luck distribution on BTC -----------------------------------
    seg, term_lf, sh_lf, term_lfs, sh_lfs = mc["BTC"]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.hist(term_lfs * 100, bins=80, color=ETH_C, alpha=0.85,
            label=f"random long/flat/short, {N_DECISIONS} decisions")
    ax.axvline(bh["BTC"]["total"] * 100, color=BTC_C, lw=2.2,
               label=f"BTC buy&hold ({bh['BTC']['total']*100:+.1f}%)")
    ax.axvline(0, color=GREY, lw=1.2, ls="--", label="flat / cash (0%)")
    ax.set_title(f"How wide is luck? {N_DECISIONS} random decisions on the real BTC tape")
    ax.set_xlabel("terminal return over the year (%)")
    ax.set_ylabel("simulations")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(CHARTS / "luck.png", dpi=150); plt.close(fig)

    # ---- Chart 3: the detectability bar vs years of data ---------------------
    yrs = np.logspace(np.log10(0.5), np.log10(12), 120)
    bar = min_detectable_sharpe(yrs)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(yrs, bar, color=ACC, lw=2.0)
    ax.axvline(1.0, color=GREY, lw=1.2, ls="--")
    ax.annotate(f"1 year (this paper)\nneed Sharpe > {min_detectable_sharpe(1.0):.1f}",
                xy=(1.0, min_detectable_sharpe(1.0)), xytext=(1.4, 1.9),
                color=GREY, arrowprops=dict(arrowstyle="->", color=GREY))
    ax.axhline(1.0, color=ETH_C, lw=1.0, ls=":")
    ax.annotate("a 'real' Sharpe of 1.0\nneeds ~4 years to prove",
                xy=(4.0, 1.0), xytext=(4.4, 1.35), color=ETH_C)
    ax.set_xscale("log")
    ax.set_title("Smallest annualized Sharpe distinguishable from luck (95%) vs years of data")
    ax.set_xlabel("years of out-of-sample tape (log scale)")
    ax.set_ylabel("Sharpe needed to clear 2 standard errors")
    fig.tight_layout(); fig.savefig(CHARTS / "power.png", dpi=150); plt.close(fig)

    print("wrote", CHARTS / "regime.png")
    print("wrote", CHARTS / "luck.png")
    print("wrote", CHARTS / "power.png")


if __name__ == "__main__":
    main()
