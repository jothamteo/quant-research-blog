"""Cost of manipulating an AMM-based price oracle — a reproducible mechanism.

Builds up from the constant-product market maker (CPMM, the x*y=k curve that powers
Uniswap-style DEXs) to the question in Feys-style / arXiv:2606.03548, "Cost of
Manipulation in AMM-Based Oracles": if a lending protocol reads its price from a
CPMM, how much does it cost an attacker to push that price somewhere false — and
which oracle designs make the attack uneconomic?

Three figures, no external data, pure numpy:

  1. fig_cpmm_curve       — the x*y=k curve and why a swap moves the price; spot
                            price is the slope, and big trades pay slippage.
  2. fig_manip_cost       — cost to shove the oracle by a given % vs pool depth.
                            Manipulation cost scales linearly with pool liquidity.
  3. fig_twap_defense     — spot (flash-loanable, ~free) vs TWAP-over-N-blocks,
                            where arbitrage erodes the manipulated price every
                            block so the attacker re-pays slippage N times. Cost
                            crosses the attacker's extractable value -> defense.

`python simulate.py` writes the three charts and prints the headline numbers.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CHARTS = HERE.parents[1] / "static" / "charts" / "amm-oracle-manipulation"
CHARTS.mkdir(parents=True, exist_ok=True)

BL, OR, GR, RED, PUR, GREY = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728", "#6a4c93", "#888888"


# ---------------------------------------------------------------------------
# CPMM primitives.  Pool holds x tokens (the asset) and y units of numeraire
# (USDC).  Invariant k = x*y.  Spot price of the token in USDC is p = y / x.
# At a target price p the reserves are pinned:  x(p) = sqrt(k/p),  y(p) = sqrt(k p).
# A pool's USDC value at price p0 is  V = y + x*p0 = 2*sqrt(k*p0)  -> k = (V/2)^2 / p0.
# ---------------------------------------------------------------------------
def k_from_pool_value(V: float, p0: float) -> float:
    """Invariant k implied by a pool worth V (USDC) quoting price p0."""
    return (V / 2.0) ** 2 / p0


def reserves_at_price(k: float, p: float) -> tuple[float, float]:
    return np.sqrt(k / p), np.sqrt(k * p)


def manipulation_cost(V: float, p0: float, r: float, fee: float = 0.003) -> float:
    """Slippage cost (USDC) to push the spot price from p0 to r*p0 by buying the
    token through the curve. Cost = USDC paid in - fair value of tokens received
    at the *original* price p0, plus the swap fee on the trade. This is the
    impact the attacker eats to move the quote; it scales linearly with V."""
    k = k_from_pool_value(V, p0)
    p1 = r * p0
    x0, y0 = reserves_at_price(k, p0)
    x1, y1 = reserves_at_price(k, p1)
    dy_in = y1 - y0                 # USDC the attacker adds to the pool (pays)
    dx_out = x0 - x1               # tokens the attacker removes
    slippage = dy_in - dx_out * p0  # paid minus fair value at p0
    return slippage + dy_in * fee


# ---------------------------------------------------------------------------
def fig_cpmm_curve():
    """Fig 1 — the constant-product curve. Reserves live on x*y=k; the spot
    price is the (negative) slope y/x; a finite swap walks along the curve and
    the average fill is worse than the start price — that gap is slippage."""
    k = 1_000_000.0
    x = np.linspace(180, 5200, 400)
    y = k / x
    x0 = 1000.0; y0 = k / x0           # start: price p0 = 1.0
    # a buy of 400 tokens walks the reserve point left along the curve
    x1 = x0 - 400; y1 = k / x1
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x, y, color=BL, lw=2.4, label="x · y = k  (all valid reserve states)")
    ax.scatter([x0, x1], [y0, y1], color=[GR, RED], s=55, zorder=5)
    ax.annotate("start\nprice p0 = y/x = 1.00", xy=(x0, y0), xytext=(x0 + 350, y0 + 360),
                fontsize=9, color=GR, arrowprops=dict(arrowstyle="->", color="#888"))
    ax.annotate("after buying 400 tokens\nprice p1 = %.2f" % (y1 / x1),
                xy=(x1, y1), xytext=(x1 - 60, y1 + 520), fontsize=9, color=RED,
                arrowprops=dict(arrowstyle="->", color="#888"))
    ax.plot([x1, x1, x0], [y1, y0, y0], color=GREY, lw=0.8, ls=":")
    ax.fill_between([x1, x0], [y1, y0], [k / x1, k / x0], color=OR, alpha=0.0)
    ax.set_title("The constant-product curve: price is the slope, size is slippage")
    ax.set_xlabel("token reserve  x")
    ax.set_ylabel("numeraire reserve  y  (USDC)")
    ax.set_xlim(180, 5200); ax.set_ylim(0, 6000)
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    fig.tight_layout(); fig.savefig(CHARTS / "cpmm_curve.png", dpi=140)
    plt.close(fig)


def fig_manip_cost():
    """Fig 2 — cost to move the oracle. To push the quoted price up by a given
    %, the attacker buys through the curve and eats slippage. That cost is
    linear in pool depth: a 10x deeper pool is 10x more expensive to fool."""
    moves = np.linspace(0.0, 0.5, 200)          # fractional price move (0..+50%)
    fig, ax = plt.subplots(figsize=(9, 5))
    for V, c in [(250_000, GR), (1_000_000, BL), (5_000_000, PUR)]:
        cost = np.array([manipulation_cost(V, 1.0, 1 + m) for m in moves])
        ax.plot(moves * 100, cost / 1000, color=c, lw=2.2,
                label=f"pool depth = ${V/1e6:.2f}M")
    ax.set_title("Cost to push the oracle vs pool depth (CPMM, 0.3% fee)")
    ax.set_xlabel("oracle price distortion  (%)")
    ax.set_ylabel("attacker cost  ($000s)")
    ax.set_xlim(0, 50); ax.set_ylim(bottom=0)
    ax.legend(fontsize=9, frameon=False, loc="upper left", title="deeper pool = costlier")
    fig.tight_layout(); fig.savefig(CHARTS / "manip_cost.png", dpi=140)
    plt.close(fig)


def fig_twap_defense():
    """Fig 3 — why TWAP raises the cost. A spot oracle can be moved and read in
    one atomic (flash-loaned) block, so the only cost is fees — cheap. A TWAP
    over N blocks forces the attacker to *hold* the false price: each block,
    arbitrageurs trade the dislocation back toward truth, so the attacker must
    re-push and re-pay slippage. Cost grows ~linearly in N and eventually
    exceeds whatever they could extract downstream -> the attack dies."""
    V = 1_000_000.0
    target_move = 0.30                      # attacker wants +30% on the oracle
    per_block_repush = manipulation_cost(V, 1.0, 1 + target_move)  # re-pay each block
    N = np.arange(1, 51)
    # spot (N=1) is flash-loanable: manipulate + read + unwind in one atomic block,
    # so the only unavoidable cost is the round-trip swap fee — slippage is recovered.
    spot_cost = 2 * 0.003 * V * target_move
    # TWAP: arbitrage reverts the dislocation each block, so the attacker re-pays
    # the full push every block (a conservative, defender-favourable upper bound).
    twap_cost = per_block_repush * N
    extractable = np.full_like(N, 350_000.0, dtype=float)  # value attacker can steal downstream

    fig, ax = plt.subplots(figsize=(9.2, 5))
    ax.plot(N, twap_cost / 1000, color=BL, lw=2.4, label="TWAP over N blocks (must re-push each block)")
    ax.axhline(spot_cost / 1000, color=OR, lw=2.0, ls="--",
               label="spot oracle (flash-loanable, ~fees only)")
    ax.axhline(extractable[0] / 1000, color=RED, lw=1.6, ls=":",
               label="value extractable downstream")
    cross = np.argmax(twap_cost >= extractable)
    if twap_cost[cross] >= extractable[cross]:
        ax.axvline(N[cross], color=GREY, lw=0.8, ls=":")
        ax.scatter([N[cross]], [twap_cost[cross] / 1000], color=RED, s=45, zorder=5)
        ax.text(N[cross] + 0.4, extractable[0] / 1000 * 1.05,
                f"attack unprofitable\nfor N ≥ {N[cross]} blocks", fontsize=9, color=RED)
    ax.fill_between(N, spot_cost / 1000, twap_cost / 1000, color=BL, alpha=0.05)
    ax.set_title("Spot vs TWAP: averaging turns a flash-loan into a sustained, costly hold")
    ax.set_xlabel("TWAP window  N  (blocks)")
    ax.set_ylabel("attacker cost to hold +30% oracle  ($000s)")
    ax.set_xlim(1, 50); ax.set_ylim(bottom=0)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(CHARTS / "twap_defense.png", dpi=140)
    plt.close(fig)
    return spot_cost, per_block_repush, N[cross]


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fig_cpmm_curve()
    fig_manip_cost()
    spot, perblock, n_safe = fig_twap_defense()
    print(f"cost to push +10% on a $1M pool = ${manipulation_cost(1e6, 1.0, 1.10):,.0f}")
    print(f"cost to push +30% on a $1M pool = ${manipulation_cost(1e6, 1.0, 1.30):,.0f}")
    print(f"spot flash-loan cost (fees)      = ${spot:,.0f}")
    print(f"TWAP per-block re-push cost       = ${perblock:,.0f}")
    print(f"TWAP blocks to deter ($380k steal)= {n_safe}")
    print("charts ->", CHARTS)
