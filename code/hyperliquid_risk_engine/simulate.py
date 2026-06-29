"""Hyperliquid's ADL queue, reconstructed — who pays when the exchange is short.

Background. On a perpetual-futures venue, every dollar of profit a winner holds is
a dollar a loser owes. When a loser's account goes negative faster than it can be
liquidated into the book, the exchange is left holding *bad debt*. Hyperliquid's
final backstop is **auto-deleveraging (ADL)**: it force-closes winning positions on
the opposite side, at the previous mark price, to cover the hole — so a solvent user
with no position never socialises a loss, but a winner can be cut off mid-trade.

The order in which winners get cut is the whole story. Ottersec reverse-engineered
the closed-source `hl-node` risk engine (https://osec.io/blog/2026-06-22-hyperliquid-risk-engine/)
and recovered the ranking score. It matches Hyperliquid's *own* published formula
for ADL ordering, the sort index

    (mark_price / entry_price) * (notional_position / account_value)

which the decompiled code computes as

    score_i = (abs_notional_i / account_value_i) * (max(pnl_i, 0) / entry_notional_i)
            = effective_leverage_i        *  profit_ratio_i

with both factors floored at 1e-8. Positions are closed in *descending* score: the
most leveraged, most profitable winners go first. (mark/entry = 1 + pnl/entry for a
long, so the two expressions induce the same ordering.)

This script does three things, pure numpy, no external data:

  1. fig_adl_queue   — a synthetic cohort of winners on the crowded side; show which
                       ones ADL closes to cover a shortfall. The casualties cluster
                       in the high-leverage / high-profit corner. That is the
                       "antifairness" Ottersec names: being *more right* and *more
                       levered* moves you to the front of the firing line.
  2. fig_fairness    — Lorenz curve + Gini of the haircut distribution, HL's
                       score-ranked queue vs a leverage-indifferent pro-rata rule
                       (the Percolator-style alternative). Pro-rata spreads the pain
                       flat (Gini -> 0); the queue concentrates it.
  3. fig_seniority   — the trader-actionable knob. Hold the *same* directional bet
                       and the *same* entry; vary only how much margin you post
                       (your leverage). Your ADL score, and the chance you get
                       force-closed, fall steeply as you de-lever. You can buy your
                       way down the queue.

`python simulate.py` writes the three charts and prints the headline numbers.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CHARTS = HERE.parents[1] / "static" / "charts" / "hyperliquid-risk-engine"
CHARTS.mkdir(parents=True, exist_ok=True)

BL, OR, GR, RED, PUR, GREY = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728", "#6a4c93", "#888888"

RNG = np.random.default_rng(11)


# ---------------------------------------------------------------------------
# The ADL ranking score, exactly as reconstructed.
# ---------------------------------------------------------------------------
def adl_score(notional: np.ndarray, account_value: np.ndarray,
              pnl: np.ndarray, entry_notional: np.ndarray) -> np.ndarray:
    """Hyperliquid's ADL sort index. Higher = closed earlier.

    effective_leverage = |notional| / account_value   (how big the bet is vs equity)
    profit_ratio       = max(pnl, 0) / entry_notional  (how well the bet has done)
    Both floored at 1e-8 so a zero factor can't cancel the product, matching the
    decompiled clamp.
    """
    eff_lev = np.maximum(np.abs(notional) / account_value, 1e-8)
    profit_ratio = np.maximum(np.maximum(pnl, 0.0) / entry_notional, 1e-8)
    return eff_lev * profit_ratio


# ---------------------------------------------------------------------------
# Build a synthetic cohort of winners on the crowded side of a fast move.
# Losers on the other side have blown through margin, leaving bad debt D that
# the insurance fund / HLP can't absorb, so ADL must close winners to cover it.
# ---------------------------------------------------------------------------
def make_cohort(n: int = 600):
    """Each winner is a long that's now in profit after a +g move."""
    g = 0.12  # the crowd's side rallied 12%

    # Account equity: lognormal, a few whales and a long tail of retail.
    account_value = np.exp(RNG.normal(np.log(5_000), 1.1, n))      # USDC

    # Chosen leverage: most people cluster low/mid, a tail max out near 20x.
    leverage = np.clip(RNG.gamma(2.2, 2.4, n), 1.0, 20.0)

    notional = leverage * account_value                            # |position| in USDC

    # Each entered at a different time, so each carries a different profit ratio
    # in [0, g]. Entry notional backs out from current notional and the run-up.
    profit_ratio = RNG.uniform(0.0, g, n)
    entry_notional = notional / (1.0 + profit_ratio)
    pnl = notional - entry_notional                                # unrealised, > 0

    return dict(account_value=account_value, leverage=leverage, notional=notional,
                entry_notional=entry_notional, pnl=pnl, profit_ratio=profit_ratio)


def run_adl(c: dict, bad_debt: float):
    """Close winners in descending score until `bad_debt` of notional is covered.
    Returns the closed-notional burden per winner (the marginal name is partially
    closed). Closing at mark transfers the loser's hole onto these positions."""
    score = adl_score(c["notional"], c["account_value"], c["pnl"], c["entry_notional"])
    order = np.argsort(-score)                       # highest score first
    burden = np.zeros_like(c["notional"])
    remaining = bad_debt
    for i in order:
        if remaining <= 0:
            break
        take = min(c["notional"][i], remaining)      # close up to the whole position
        burden[i] = take
        remaining -= take
    return burden, score


def run_prorata(c: dict, bad_debt: float):
    """Leverage-indifferent alternative: every winner gives up the same fraction of
    their *equity*. This is the spirit of Percolator — reduce everyone's withdrawal
    capacity proportionally rather than queue-and-close the riskiest. Because the
    haircut metric is h_i = x_i / w_i, charging proportional to equity makes every
    h_i identical, i.e. Gini -> 0 by construction. (Charging pro-rata of *notional*
    instead is still far flatter than the queue, but not perfectly equal, because
    leverage varies — see the post.)"""
    frac = bad_debt / c["account_value"].sum()
    return frac * c["account_value"]


def gini(x: np.ndarray) -> float:
    """Gini coefficient of a non-negative vector. 0 = perfectly equal."""
    x = np.sort(np.asarray(x, float))
    n = x.size
    if x.sum() == 0:
        return 0.0
    cum = np.cumsum(x)
    return (n + 1 - 2 * np.sum(cum) / cum[-1]) / n


def lorenz(x: np.ndarray):
    """Lorenz curve points (population share, burden share), sorted ascending."""
    x = np.sort(np.asarray(x, float))
    cum = np.insert(np.cumsum(x), 0, 0.0)
    pop = np.linspace(0, 1, x.size + 1)
    return pop, cum / cum[-1]


# ---------------------------------------------------------------------------
# Figure 1 — who ADL closes.
# ---------------------------------------------------------------------------
def fig_adl_queue(c: dict, bad_debt: float):
    burden, score = run_adl(c, bad_debt)
    closed = burden > 0
    frac_closed = burden / c["notional"]             # 0..1, how much of the position went

    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    # survivors
    ax.scatter(c["leverage"][~closed], 100 * c["profit_ratio"][~closed],
               s=14, color=GREY, alpha=0.45, label="kept (survived the queue)")
    # casualties, colour by fraction closed
    sc = ax.scatter(c["leverage"][closed], 100 * c["profit_ratio"][closed],
                    c=frac_closed[closed], cmap="autumn_r", s=34, edgecolor="k",
                    linewidth=0.3, vmin=0, vmax=1, label="force-closed by ADL")
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("fraction of position force-closed")

    ax.set_xlabel("effective leverage  (|notional| / account value)")
    ax.set_ylabel("profit ratio  (unrealised PnL / entry notional, %)")
    ax.set_title("Hyperliquid ADL: the most levered, most profitable winners go first")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(CHARTS / "adl_queue.png", dpi=140)
    plt.close(fig)

    pct = 100 * closed.mean()
    notional_share_closed = 100 * c["notional"][closed].sum() / c["notional"].sum()
    return closed, pct, notional_share_closed


# ---------------------------------------------------------------------------
# Figure 2 — fairness: queue vs pro-rata.
# ---------------------------------------------------------------------------
def fig_fairness(c: dict, bad_debt: float):
    burden_hl, _ = run_adl(c, bad_debt)
    burden_pr = run_prorata(c, bad_debt)

    # Haircut as a share of the trader's own equity, h_i = x_i / w_i (Ottersec's
    # definition). Gini over h_i measures how unequally the pain lands.
    h_hl = burden_hl / c["account_value"]
    h_pr = burden_pr / c["account_value"]
    g_hl, g_pr = gini(h_hl), gini(h_pr)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for h, col, lab, gg in [(h_hl, OR, "Hyperliquid score-ranked queue", g_hl),
                            (h_pr, GR, "leverage-indifferent pro-rata", g_pr)]:
        pop, cum = lorenz(h)
        ax.plot(100 * pop, 100 * cum, color=col, lw=2.4,
                label=f"{lab}  (Gini = {gg:.2f})")
    ax.plot([0, 100], [0, 100], color=GREY, lw=1.0, ls="--", label="perfect equality")
    ax.set_xlabel("share of winning traders (poorest-hit → hardest-hit, %)")
    ax.set_ylabel("share of total haircut borne (%)")
    ax.set_title("Who carries the bad debt: a queue concentrates, pro-rata spreads")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(CHARTS / "fairness.png", dpi=140)
    plt.close(fig)
    return g_hl, g_pr


# ---------------------------------------------------------------------------
# Figure 3 — the seniority knob: de-lever to drop down the queue.
# ---------------------------------------------------------------------------
def fig_seniority(c: dict, bad_debt: float):
    """Hold one fixed directional bet (same entry notional, same profit ratio as the
    median winner) and vary only the margin you post -> your leverage. Plot your ADL
    score percentile and your expected force-closed fraction vs leverage. Lower
    leverage = lower score = further back in the queue = more of your winner survives."""
    base_score = adl_score(c["notional"], c["account_value"], c["pnl"], c["entry_notional"])
    burden_hl, _ = run_adl(c, bad_debt)
    closed_frac_cohort = burden_hl / c["notional"]

    # A representative winning bet: median entry notional and median profit ratio.
    entry_n = np.median(c["entry_notional"])
    pr = np.median(c["profit_ratio"])
    cur_notional = entry_n * (1.0 + pr)
    cur_pnl = cur_notional - entry_n

    levs = np.linspace(1.0, 20.0, 60)
    my_acct = cur_notional / levs                      # post more margin -> lower leverage
    my_score = adl_score(np.full_like(levs, cur_notional), my_acct,
                         np.full_like(levs, cur_pnl), np.full_like(levs, entry_n))

    # Percentile of my score within the live cohort queue (higher = closer to front).
    pctile = np.array([100 * (base_score < s).mean() for s in my_score])

    # Expected force-closed fraction: map my score-rank to the cohort's realised
    # closed-fraction-vs-rank profile (a clean read of "how deep does the axe reach").
    order = np.argsort(-base_score)
    ranked_closed = closed_frac_cohort[order]
    cohort_pctile = 100 * (1 - np.arange(len(order)) / len(order))  # front = high pctile
    exp_closed = np.interp(pctile, cohort_pctile[::-1], ranked_closed[::-1])

    fig, ax1 = plt.subplots(figsize=(7.4, 5.2))
    ax1.plot(levs, pctile, color=BL, lw=2.4)
    ax1.set_xlabel("your chosen leverage on the same winning bet")
    ax1.set_ylabel("ADL queue percentile  (100 = first to be closed)", color=BL)
    ax1.tick_params(axis="y", labelcolor=BL)
    ax1.grid(alpha=0.15)

    ax2 = ax1.twinx()
    ax2.plot(levs, 100 * exp_closed, color=RED, lw=2.4, ls="--")
    ax2.set_ylabel("expected % of the position ADL force-closes", color=RED)
    ax2.tick_params(axis="y", labelcolor=RED)

    ax1.set_title("The seniority knob: de-lever and you fall to the back of the queue")
    fig.tight_layout()
    fig.savefig(CHARTS / "seniority.png", dpi=140)
    plt.close(fig)
    return levs, pctile, exp_closed


def main():
    c = make_cohort()
    total_notional = c["notional"].sum()
    # Bad debt sized so ADL has to reach ~30% of open winning notional — a severe
    # cascade in the spirit of the 11 Oct 2025 event, where ADL force-closed tens of
    # thousands of profitable positions across the platform.
    bad_debt = 0.30 * total_notional

    closed, pct_closed, notional_share = fig_adl_queue(c, bad_debt)
    g_hl, g_pr = fig_fairness(c, bad_debt)
    levs, pctile, exp_closed = fig_seniority(c, bad_debt)

    # Headline numbers used in the post.
    score = adl_score(c["notional"], c["account_value"], c["pnl"], c["entry_notional"])
    hi_corner = (c["leverage"] >= 10) & (c["profit_ratio"] >= 0.06)
    lo_corner = (c["leverage"] <= 3)
    hit_rate_hi = 100 * closed[hi_corner].mean()
    hit_rate_lo = 100 * closed[lo_corner].mean()

    # Highest leverage at which expected force-closed fraction is still below 5%
    # (the crossover, since exp_closed rises with leverage).
    below = exp_closed < 0.05
    safe_lev = levs[below].max() if below.any() else float("nan")

    print("=" * 64)
    print(f"Cohort: {len(c['leverage'])} winning longs, total notional "
          f"${total_notional/1e6:.1f}M, bad debt to cover ${bad_debt/1e6:.1f}M "
          f"({100*bad_debt/total_notional:.0f}% of notional)")
    print(f"Winners force-closed (by count):      {pct_closed:.1f}%")
    print(f"Winners force-closed (by notional):   {notional_share:.1f}%")
    print(f"Hit rate, high-lev high-profit corner (>=10x, >=6%): {hit_rate_hi:.0f}%")
    print(f"Hit rate, low-leverage corner (<=3x):                {hit_rate_lo:.0f}%")
    print(f"Gini of haircut — Hyperliquid queue:  {g_hl:.2f}")
    print(f"Gini of haircut — pro-rata:           {g_pr:.2f}")
    print(f"De-lever below ~{safe_lev:.1f}x and expected force-closed share < 5%")
    print("Charts ->", CHARTS)
    print("=" * 64)


if __name__ == "__main__":
    main()
