"""SpaceX joins the Russell 1000 — the mechanics of a forced-buying event.

A reproducible, illustrative model of the largest single index-inclusion flow on
record: SpaceX (NASDAQ: SPCX) enters the Russell 1000 / 3000 at the June 2026
reconstitution, forcing an estimated $22-27bn of price-insensitive index-fund
buying into one closing auction.

This script does NOT use proprietary data. It reproduces three *mechanisms*:

  1. fig_forced_demand   — how the forced dollar buy decomposes into
                           (index weight) x (passive AUM tracking the index),
                           with the publicly-reported $22-27bn band highlighted.
  2. fig_impact_concession — a square-root market-impact model for the price
                           concession the forced buyer pays at the close, as a
                           function of forced demand / ADV. That concession is
                           the liquidity provider's edge.
  3. fig_car_paths       — the textbook pre-2010 inclusion run-up vs the modern
                           fully-anticipated path (flat into the effective date,
                           concession + reversal at the close). Ties to the prior
                           S&P event study, which found the naive premium ~ 0.

All parameters are illustrative and labelled as such. `python simulate.py`
writes three charts and prints the headline numbers.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CHARTS = HERE.parents[1] / "static" / "charts" / "spacex-russell-etf-flow"
CHARTS.mkdir(parents=True, exist_ok=True)

BL, OR, GR, RED, PUR, GREY = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728", "#6a4c93", "#888888"

# Publicly-reported event facts (sourced in the post) -----------------------
FORCED_LOW, FORCED_HIGH = 22.0, 27.0   # $bn of forced index-fund buying (est.)


# ---------------------------------------------------------------------------
# Fig 1 — forced demand = index weight x tracking AUM
# ---------------------------------------------------------------------------
def fig_forced_demand():
    """The forced buy is mechanical: every dollar tracking the index must hold
    the new name at its index weight. forced_$ = weight x AUM. We don't know the
    exact float-adjusted weight, so we show the whole surface and mark where the
    reported $22-27bn band lands."""
    weight = np.linspace(0.002, 0.014, 300)          # SpaceX float-adj index weight
    aum = np.array([1.6, 2.0, 2.4])                   # $tn tracking Russell 1000 family
    fig, ax = plt.subplots(figsize=(9, 5))
    for a, c in zip(aum, (GR, BL, PUR)):
        forced = weight * a * 1000.0                  # -> $bn
        ax.plot(weight * 100, forced, color=c, lw=2.2,
                label=f"AUM tracking index = ${a:.1f}tn")
    ax.axhspan(FORCED_LOW, FORCED_HIGH, color=OR, alpha=0.15)
    ax.axhline(FORCED_LOW, color=OR, lw=1.0, ls="--")
    ax.axhline(FORCED_HIGH, color=OR, lw=1.0, ls="--")
    ax.text(0.21, (FORCED_LOW + FORCED_HIGH) / 2,
            "reported forced buy\n$22-27bn", fontsize=9, color=OR, va="center")
    ax.set_title("Forced index-fund demand  =  SpaceX index weight  x  tracking AUM")
    ax.set_xlabel("SpaceX float-adjusted weight in the index  (%)")
    ax.set_ylabel("forced one-day buy  ($bn)")
    ax.set_xlim(0.2, 1.4)
    ax.set_ylim(0, 35)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(CHARTS / "forced_demand.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 2 — the price concession the forced buyer pays (square-root impact)
# ---------------------------------------------------------------------------
# Square-root impact law: the *realised* concession on a forced parent order of
# size Q scales like sqrt(Q / ADV). We write it directly in basis points,
#   concession(bps) ≈ KAPPA * sqrt(Q / ADV),
# and calibrate KAPPA so the numbers sit in the empirically-observed range for
# index-rebalance concessions — tens of bps, consistent with Petajisto's
# 20-28bps/yr implicit cost cited in the companion S&P study. The forced buyer is
# price-insensitive, so it *pays* this concession; the desk on the other side
# *earns* it. That is the entire modern edge.
KAPPA = 35.0       # bps at Q = 1x ADV (illustrative, literature-calibrated)


def concession_bps(q_over_adv, kappa=KAPPA):
    return kappa * np.sqrt(np.maximum(q_over_adv, 0.0))


def fig_impact_concession():
    r = np.linspace(0.0, 1.5, 400)                 # forced demand as a fraction of ADV
    bps = concession_bps(r)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(r, bps, color=BL, lw=2.4)
    ax.fill_between(r, 0, bps, color=BL, alpha=0.06)
    # mark a plausible operating range for a liquid mega-IPO at reconstitution
    for rr, lab in [(0.25, "deep, liquid name"), (0.6, "base case"), (1.1, "thin close")]:
        ax.axvline(rr, color=GREY, lw=0.7, ls=":")
        ax.scatter([rr], [concession_bps(rr)], color=RED, s=35, zorder=5)
        ax.annotate(f"{lab}\n{concession_bps(rr):.0f} bps",
                    xy=(rr, concession_bps(rr)),
                    xytext=(rr + 0.03, concession_bps(rr) - 16),
                    fontsize=8.5, color="#444")
    ax.set_title("Closing-auction concession the forced buyer pays  "
                 "(square-root impact)")
    ax.set_xlabel("forced demand  /  average daily volume")
    ax.set_ylabel("price concession  (bps)")
    ax.set_xlim(0, 1.5); ax.set_ylim(0, concession_bps(1.5) * 1.15)
    ax.text(0.02, concession_bps(1.5) * 1.02,
            f"illustrative:  concession = {KAPPA:.0f}bps·√(Q/ADV)  "
            "(literature-calibrated, ~tens of bps)",
            fontsize=8.5, color=GREY)
    fig.tight_layout(); fig.savefig(CHARTS / "impact_concession.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Fig 3 — where the money is: run-up (gone) vs concession+reversal (the edge)
# ---------------------------------------------------------------------------
def fig_car_paths():
    """Stylised cumulative-abnormal-return paths around the effective date t=0.
    Pre-2010: a textbook run-up into inclusion that index funds overpay for.
    Modern: anticipated demand is arbitraged out before t=0, leaving only a
    closing-auction concession that mean-reverts over the following days. The
    modern edge is supplying that close, not buying the add."""
    t = np.arange(-10, 11)

    # textbook pre-2010 run-up (peaks just after the effective date)
    runup = 3.6 / (1 + np.exp(-0.7 * (t + 1)))           # ~360 bps logistic run-up
    runup = runup - runup[0]

    # modern: flat into t=0, a concession dip at the close, then reversion
    modern = np.zeros_like(t, dtype=float)
    modern[t == 0] = -0.32                                # forced-buy concession (~tens of bps)
    modern[t == 1] = -0.05
    modern[t >= 2] = 0.05                                 # partial reversion / mild drift

    fig, ax = plt.subplots(figsize=(9.2, 5))
    ax.axhline(0, color=GREY, lw=0.7)
    ax.axvline(0, color=RED, lw=1.1, ls=":")
    ax.text(0.15, 3.2, "effective date\n(recon close)", fontsize=8.5, color=RED)
    ax.plot(t, runup, color=OR, lw=2.4, marker="o", ms=3,
            label="pre-2010 textbook add  (index funds overpay)")
    ax.plot(t, modern, color=BL, lw=2.4, marker="o", ms=3,
            label="modern anticipated add  (premium arbitraged out)")
    ax.annotate("the edge today:\nbuy the concession\nat the close, fade the bounce",
                xy=(0, -0.32), xytext=(2.4, -1.7), fontsize=8.5, color=BL,
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
    ax.set_title("Cumulative abnormal return around index inclusion  (stylised)")
    ax.set_xlabel("trading days relative to effective date")
    ax.set_ylabel("cumulative abnormal return  (%)")
    ax.set_xlim(-10, 10)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(CHARTS / "car_paths.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fig_forced_demand()
    fig_impact_concession()
    fig_car_paths()
    print("forced buy (reported)        = $%.0f-%.0fbn" % (FORCED_LOW, FORCED_HIGH))
    print("concession @ 0.25x ADV       = %.0f bps" % concession_bps(0.25))
    print("concession @ 0.60x ADV       = %.0f bps" % concession_bps(0.60))
    print("concession @ 1.10x ADV       = %.0f bps" % concession_bps(1.10))
    print("charts ->", CHARTS)
