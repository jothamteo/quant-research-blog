"""Beyond accuracy: why a more *accurate* LLM forecaster still need not *profit*.

A reproducible illustration of the central tension in "Beyond Accuracy: Can LLM
Forecasters Profit on Prediction Markets?" (OpenReview, 2026): frontier LLMs now
approach human forecasting *accuracy*, yet turning that into *profit* on a real
prediction market is a separate, much higher bar. Three forces open a wedge
between the two:

  1. you don't get paid for being accurate, you get paid for beating the *price*,
  2. the bid-ask spread taxes every trade, and
  3. the markets you most disagree with are adversely selected — disagreement is
     partly your own error, so realised edge < perceived edge.

The descriptive market structure quoted in the post is REAL — computed from a local
archive of 145,819 Polymarket markets (39,271 resolved binary; 30% resolved YES,
70% NO; median volume ~$5.8k). The accuracy->profit experiment here is a
self-contained Monte-Carlo of the mechanism — no LLM call, no look-ahead, fully
reproducible. `python simulate.py` writes three charts and prints the headline gap.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CHARTS = HERE.parents[1] / "static" / "charts" / "llm-forecaster-profit"
CHARTS.mkdir(parents=True, exist_ok=True)

BL, OR, GR, RED, PUR, GREY = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728", "#6a4c93", "#888888"

RNG = np.random.default_rng(7)
N = 80_000
BASE_A, BASE_B = 1.5, 3.5      # Beta(1.5,3.5): mean 0.30 -> matches real 30% YES base rate
SIGMA_M = 0.025                # the market is an *efficient* aggregator — hard to beat
TAU = 0.03                     # only trade on disagreement bigger than this
HALF_SPREAD = 0.025            # 2.5% each side ~ 5% round-trip (realistic for PMs)


# ---------------------------------------------------------------------------
# One synthetic universe of binary markets, calibrated to the real base rate.
# ---------------------------------------------------------------------------
q = RNG.beta(BASE_A, BASE_B, N)                       # true resolution probability
outcome = (RNG.random(N) < q).astype(float)           # realised 0/1
market = np.clip(q + RNG.normal(0, SIGMA_M, N), 0.01, 0.99)   # market price (efficient-ish)
z = RNG.normal(0, 1, N)                               # common LLM error direction


def llm_forecast(sigma_f: float) -> np.ndarray:
    """LLM probability estimate with skill set by its error scale sigma_f
    (smaller = better). Common random numbers across sigma_f for smooth curves."""
    return np.clip(q + sigma_f * z, 0.01, 0.99)


def brier(p: np.ndarray) -> float:
    return float(np.mean((p - outcome) ** 2))


def pnl_per_market(f: np.ndarray, h: float = HALF_SPREAD, tau: float = TAU):
    """Trade against the market when the LLM disagrees by more than tau; pay the
    half-spread h on entry. YES at ask m+h pays `outcome`; NO at ask (1-m)+h pays
    `1-outcome`. Returns mean P&L per market and the fraction of markets traded."""
    edge = f - market
    yes = edge > tau
    no = edge < -tau
    pnl = np.zeros(N)
    pnl[yes] = outcome[yes] - market[yes] - h
    pnl[no] = market[no] - outcome[no] - h
    return float(pnl.sum() / N), float((yes | no).mean()), pnl, (yes | no)


# ---------------------------------------------------------------------------
# Fig 1 — accuracy improves smoothly, profit has a cliff
# ---------------------------------------------------------------------------
def fig_accuracy_vs_profit():
    sig = np.linspace(0.12, 0.0, 160)                 # LLM error: poor -> perfect
    b_mkt = brier(market)
    brier_adv = np.array([b_mkt - brier(llm_forecast(s)) for s in sig])  # >0 = LLM more accurate
    pnl = np.array([pnl_per_market(llm_forecast(s))[0] for s in sig])

    fig, axL = plt.subplots(figsize=(9.2, 5))
    axR = axL.twinx()
    l1, = axL.plot(sig[::-1], brier_adv[::-1], color=BL, lw=2.4,
                   label="accuracy edge vs market  (Brier, left axis)")
    l2, = axR.plot(sig[::-1], pnl[::-1] * 100, color=OR, lw=2.4,
                   label="net P&L per market after spread  (right axis)")
    axL.axhline(0, color=BL, lw=0.8, ls=":")
    axR.axhline(0, color=OR, lw=0.8, ls=":")

    s_acc = sig[np.argmin(np.abs(brier_adv))]          # where LLM ties market on accuracy
    s_pnl = sig[np.argmin(np.abs(pnl))]                # where P&L finally reaches 0
    axL.axvline(s_acc, color=GREY, lw=0.9, ls="--")
    axL.text(s_acc + 0.004, brier_adv.max() * 0.92,
             "ties the market\non accuracy", fontsize=8.5, color=BL)
    # the whole region to the left (less skilled than the market) is underwater
    axR.annotate("P&L is negative across this whole region —\n"
                 "the LLM only stops losing once it is as\nprecise as the market itself",
                 xy=(0.06, pnl_per_market(llm_forecast(0.06))[0] * 100),
                 xytext=(0.066, pnl.min() * 100 * 0.62), fontsize=8.5, color=OR,
                 arrowprops=dict(arrowstyle="->", color=OR, lw=0.8))

    axL.set_title("Accuracy rises steadily; profit stays underwater until you match the market")
    axL.set_xlabel("LLM forecast error   (← more skilled)")
    axL.set_ylabel("Brier accuracy edge vs market", color=BL)
    axR.set_ylabel("net P&L per market  (cents)", color=OR)
    axL.set_xlim(0.12, 0.0)
    axL.legend(handles=[l1, l2], fontsize=9, frameon=False, loc="lower left")
    fig.tight_layout(); fig.savefig(CHARTS / "accuracy_vs_profit.png", dpi=140)
    plt.close(fig)
    return s_acc, s_pnl


# ---------------------------------------------------------------------------
# Fig 2 — the spread eats the edge
# ---------------------------------------------------------------------------
def fig_spread_hurdle():
    f = llm_forecast(0.015)                             # a genuinely market-beating LLM
    spreads = np.linspace(0.0, 0.06, 140)              # half-spread 0..6%
    pnl = np.array([pnl_per_market(f, h=h)[0] for h in spreads])
    fig, ax = plt.subplots(figsize=(9.2, 5))
    ax.plot(spreads * 200, pnl * 100, color=BL, lw=2.6)   # x in round-trip % (2*half)
    ax.fill_between(spreads * 200, 0, pnl * 100, where=(pnl > 0), color=GR, alpha=0.12)
    ax.fill_between(spreads * 200, 0, pnl * 100, where=(pnl <= 0), color=RED, alpha=0.10)
    ax.axhline(0, color=GREY, lw=0.8)
    zero = spreads[np.argmin(np.abs(pnl))] * 200
    ax.axvline(zero, color=RED, lw=1.1, ls=":")
    ax.text(zero + 0.15, pnl.max() * 100 * 0.5, f"breaks even at\n~{zero:.1f}% round-trip", fontsize=9, color=RED)
    ax.axvspan(2, 6, color=OR, alpha=0.06)
    ax.text(4.0, pnl.max() * 100 * 0.12, "typical PM spreads", fontsize=8.5, color=OR, ha="center")
    ax.set_title("A market-beating forecaster still loses once the spread is realistic")
    ax.set_xlabel("round-trip trading spread  (%)")
    ax.set_ylabel("net P&L per market  (cents)")
    ax.set_xlim(0, 12)
    fig.tight_layout(); fig.savefig(CHARTS / "spread_hurdle.png", dpi=140)
    plt.close(fig)
    return zero


# ---------------------------------------------------------------------------
# Fig 3 — disagreement is adversely selected
# ---------------------------------------------------------------------------
def fig_adverse_selection():
    f = llm_forecast(0.03)
    _, traded_frac, _, traded = pnl_per_market(f)
    # the LLM's *perceived* edge vs the *realised* edge, on the markets it trades
    edge = f - market
    side = np.sign(edge)
    perceived = np.abs(edge)[traded].mean()                       # how much it thinks it's right by
    # realised directional edge: did the outcome move its way vs the price it paid?
    realised_dir = np.where(side > 0, outcome - market, market - outcome)
    realised = realised_dir[traded].mean()
    # accuracy overall vs on the traded subset
    acc_all = 1 - brier(f)
    acc_traded = 1 - float(np.mean((f[traded] - outcome[traded]) ** 2))
    naive_always_no = 0.70                                        # real base rate anchor

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.6))
    axL.bar(["perceived\nedge", "realised\nedge"], [perceived * 100, realised * 100],
            color=[BL, RED], width=0.6)
    axL.set_title("On the markets it trades, edge shrinks")
    axL.set_ylabel("mean edge per trade  (cents)")
    for i, v in enumerate([perceived * 100, realised * 100]):
        axL.text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=10)

    axR.bar(["naive\n'always NO'", "LLM\n(all markets)", "LLM\n(its trades)"],
            [naive_always_no * 100, acc_all * 100, acc_traded * 100],
            color=[GREY, GR, OR], width=0.62)
    axR.set_ylim(50, 100)
    axR.axhline(naive_always_no * 100, color=GREY, lw=0.8, ls=":")
    axR.set_title("Accuracy is cheap; the traded subset is the hard part")
    axR.set_ylabel("accuracy  (%)")
    for i, v in enumerate([naive_always_no * 100, acc_all * 100, acc_traded * 100]):
        axR.text(i, v + 0.6, f"{v:.0f}%", ha="center", fontsize=10)

    fig.tight_layout(); fig.savefig(CHARTS / "adverse_selection.png", dpi=140)
    plt.close(fig)
    return perceived, realised, acc_all, acc_traded


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    s_acc, s_pnl = fig_accuracy_vs_profit()
    zero = fig_spread_hurdle()
    perceived, realised, acc_all, acc_traded = fig_adverse_selection()
    print(f"market Brier                         = {brier(market):.4f}")
    print(f"LLM error where it ties on accuracy   = {s_acc:.3f}")
    print(f"LLM error where it breaks even on P&L = {s_pnl:.3f}   (needs to be this much better)")
    print(f"break-even round-trip spread          = {zero:.1f}%")
    print(f"perceived vs realised edge per trade  = {perceived*100:.1f}c -> {realised*100:.1f}c")
    print(f"accuracy all={acc_all*100:.0f}%  traded={acc_traded*100:.0f}%  naive-NO=70%")
    print("charts ->", CHARTS)
