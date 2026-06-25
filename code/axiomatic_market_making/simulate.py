"""Axiomatic market making — a lean reproduction of the mechanism.

Reproduces the *shape* forced by the axioms in Feys, "Axiomatic Market Making"
(arXiv:2606.09454): eight natural axioms plus six environmental assumptions on the
maker's inventory cost pin down a UNIQUE three-parameter quoting rule. Two features
of that forced form are the ones a practitioner actually trades on:

    1. the mid-quote is *linear in inventory*          mid(q) = mu - kappa * q
    2. the half-spread *decomposes additively* into     delta  = s_inv + s_adv
       an inventory piece and an adverse-selection piece,

and the three parameters (kappa, s_inv, the adverse-selection loading) are each
identified from a *distinct, decoupled* moment of the observable quoting rule — you
can estimate one without contaminating the others.

A structural corollary is the headline for anyone running a real book: a sharp
*phase transition* separates a functioning regime from a frozen one. Past a critical
informed-trader fraction phi*, no admissible quote is profitable and the maker
rationally withdraws — the market freezes.

This script does NOT redo the paper's 66-page uniqueness proof. It builds the
canonical Avellaneda-Stoikov / Glosten-Milgrom maker whose *form* the axioms force,
and shows the three things above concretely. `python simulate.py` writes three
charts and prints the critical phi*.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CHARTS = HERE.parents[1] / "static" / "charts" / "axiomatic-market-making"
CHARTS.mkdir(parents=True, exist_ok=True)

BL, OR, GR, RED, PUR, GREY = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728", "#6a4c93", "#888888"

MU = 100.0          # fair mid (belief)
SIGMA = 1.0         # per-trade adverse-move / volatility scale
KAPPA = 0.08        # inventory-skew slope  (mid moves -kappa per unit inventory)
S_INV = 0.10        # inventory half-spread component (the phi -> 0 intercept)
ALPHA = 0.90        # adverse-selection loading: s_adv = alpha * phi * sigma


# ---------------------------------------------------------------------------
# The forced functional form
# ---------------------------------------------------------------------------
def mid_quote(q: np.ndarray, mu: float = MU, kappa: float = KAPPA) -> np.ndarray:
    """Axiom-forced mid: linear in inventory. Slope -kappa is one of the 3 params."""
    return mu - kappa * q


def half_spread(phi: float, sigma: float = SIGMA, s_inv: float = S_INV,
                alpha: float = ALPHA) -> tuple[float, float]:
    """Axiom-forced additive decomposition: delta = s_inv + s_adv.

    s_inv  — inventory/rebalancing component, independent of the informed fraction.
    s_adv  — adverse-selection component, linear in informed fraction phi and in
             volatility sigma (the Glosten-Milgrom loss the maker must price in).
    Returned separately so the decomposition is explicit.
    """
    s_adv = alpha * phi * sigma
    return s_inv, s_adv


# ---------------------------------------------------------------------------
# The phase transition: functioning vs frozen
# ---------------------------------------------------------------------------
# A competitive maker cannot escape adverse selection by widening: in
# Glosten-Milgrom equilibrium the spread is forced *up to* break-even, where the
# spread earned on uninformed flow just covers the loss to informed flow. That
# break-even half-spread is exactly the additive form from Fig 2,
#
#     delta_be(phi)  =  s_inv  +  phi * A ,         A = beta * sigma  (adverse move)
#
# Uninformed traders, however, have a finite tolerance: they will not pay more than
# a reservation half-spread DMAX. The market *functions* only while the spread the
# maker is forced to quote stays within that tolerance. Past the critical informed
# fraction
#
#     phi*  =  (DMAX - s_inv) / A ,
#
# the forced spread exceeds DMAX, uninformed flow leaves, the maker is left facing
# only informed traders, and quoting stops. The market *freezes* — a sharp
# transition, not a gentle widening.
BETA = 1.20         # adverse move A = BETA * sigma
DMAX = 0.55         # uninformed reservation half-spread (tolerance)
KF = 0.30           # Avellaneda-Stoikov uninformed fill-decay scale


def breakeven_spread(phi: float | np.ndarray, sigma: float = SIGMA,
                     s_inv: float = S_INV, beta: float = BETA):
    """Forced competitive break-even half-spread:  s_inv + phi * (beta*sigma)."""
    return s_inv + phi * beta * sigma


def traded_volume(phi: float | np.ndarray, sigma: float = SIGMA, s_inv: float = S_INV,
                  beta: float = BETA, dmax: float = DMAX, kf: float = KF, lam0: float = 1.0):
    """Uninformed volume the maker actually captures. Avellaneda-Stoikov fill
    intensity exp(-delta/kf) on the (1-phi) uninformed mass *while* the forced
    spread is tolerated; identically zero once delta_be > dmax (frozen)."""
    phi = np.asarray(phi, dtype=float)
    delta = breakeven_spread(phi, sigma, s_inv, beta)
    vol = (1.0 - phi) * lam0 * np.exp(-delta / kf)
    return np.where(delta <= dmax, vol, 0.0)


def critical_phi(sigma: float = SIGMA, s_inv: float = S_INV, beta: float = BETA,
                 dmax: float = DMAX) -> float:
    """Informed fraction at which the forced spread hits the uninformed tolerance."""
    return float((dmax - s_inv) / (beta * sigma))


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig_inventory_skew():
    """Fig 1 — the mid-quote is forced linear in inventory. Bid/ask ride a fixed
    half-spread around a mid that skews down as the maker gets longer."""
    q = np.linspace(-10, 10, 400)
    mid = mid_quote(q)
    s_inv, s_adv = half_spread(phi=0.2)
    delta = s_inv + s_adv
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(q, mid, color=BL, lw=2.2, label="mid  =  mu - kappa * q  (axiom-forced)")
    ax.plot(q, mid + delta, color=GR, lw=1.4, ls="--", label="ask  =  mid + delta")
    ax.plot(q, mid - delta, color=OR, lw=1.4, ls="--", label="bid  =  mid - delta")
    ax.fill_between(q, mid - delta, mid + delta, color=BL, alpha=0.06)
    ax.axhline(MU, color=GREY, lw=0.7, ls=":")
    ax.text(-9.6, MU + 0.05, "fair value mu", fontsize=9, color="#666")
    ax.annotate("skew slope = -kappa", xy=(6, mid_quote(6)), xytext=(2.0, MU - 0.95),
                fontsize=9, color="#444",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
    ax.set_title("Quote vs inventory — the mid is forced linear (skew = -kappa)")
    ax.set_xlabel("inventory  q   (long to the right)")
    ax.set_ylabel("price")
    ax.legend(fontsize=9, frameon=False, loc="upper right")
    fig.tight_layout(); fig.savefig(CHARTS / "inventory_skew.png", dpi=140)
    plt.close(fig)


def fig_spread_decomposition():
    """Fig 2 — the half-spread decomposes additively. The inventory piece is the
    phi -> 0 intercept; the adverse-selection piece is the slope in phi. The two
    parameters live in different moments, so they identify independently."""
    phis = np.linspace(0.0, 1.0, 200)
    fig, ax = plt.subplots(figsize=(9, 5))
    for sigma, c in [(1.0, BL), (1.6, RED)]:
        s_inv = np.full_like(phis, S_INV)
        s_adv = ALPHA * phis * sigma
        ax.fill_between(phis, 0, s_inv, color=GR, alpha=0.25 if sigma == 1.0 else 0.0)
        ax.plot(phis, s_inv + s_adv, color=c, lw=2.2,
                label=f"delta(phi)  at sigma = {sigma:g}")
    ax.axhline(S_INV, color=GR, lw=1.6)
    ax.text(0.02, S_INV + 0.02, "s_inv  (inventory piece — the phi=0 intercept)",
            fontsize=9, color=GR)
    ax.annotate("s_adv = alpha * phi * sigma\n(adverse-selection piece — the slope)",
                xy=(0.72, ALPHA * 0.72 + S_INV), xytext=(0.30, 0.95),
                fontsize=9, color="#444",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.9))
    ax.set_title("Half-spread decomposes additively:  delta  =  s_inv  +  s_adv")
    ax.set_xlabel("informed-trader fraction  phi")
    ax.set_ylabel("half-spread  delta")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1.6)
    ax.legend(fontsize=9, frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(CHARTS / "spread_decomposition.png", dpi=140)
    plt.close(fig)


def fig_phase_transition():
    """Fig 3 — the headline. The forced break-even half-spread climbs linearly in
    the informed fraction; the captured (uninformed) volume erodes with it and then
    cuts to zero the instant the spread breaches the uninformed tolerance. Past phi*
    the market is frozen — a sharp transition, not a gentle fade."""
    phis = np.linspace(0.0, 0.6, 600)
    delta = breakeven_spread(phis)
    vol = traded_volume(phis)
    phi_c = critical_phi()

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 4.6))

    # left: the forced spread walking into the tolerance ceiling
    axL.plot(phis, delta, color=BL, lw=2.4, label="forced spread  delta_be = s_inv + phi*A")
    axL.axhline(DMAX, color=PUR, lw=1.6, ls="--", label=f"uninformed tolerance  DMAX = {DMAX:g}")
    axL.axvline(phi_c, color=RED, lw=1.3, ls=":")
    axL.axvspan(phi_c, 0.6, color=RED, alpha=0.07)
    axL.scatter([phi_c], [DMAX], color=RED, s=45, zorder=5)
    axL.text(phi_c + 0.008, DMAX * 0.30, f"phi* = {phi_c:.3f}", fontsize=10, color=RED)
    axL.set_title("Forced spread hits the tolerance wall")
    axL.set_xlabel("informed-trader fraction  phi  (toxicity)")
    axL.set_ylabel("half-spread  delta")
    axL.set_xlim(0, 0.6); axL.set_ylim(0, 0.9)
    axL.legend(fontsize=8.5, frameon=False, loc="upper left")

    # right: realised liquidity collapses discontinuously at phi*
    axR.plot(phis, vol, color=GR, lw=2.4)
    axR.axvline(phi_c, color=RED, lw=1.3, ls=":")
    axR.axvspan(phi_c, 0.6, color=RED, alpha=0.07)
    axR.text(phi_c - 0.014, max(vol) * 0.55, "functioning", fontsize=10,
             color=GR, ha="right")
    axR.text(phi_c + 0.014, max(vol) * 0.55, "frozen", fontsize=10, color=RED)
    axR.set_title("Captured liquidity — sharp cutoff, not a fade")
    axR.set_xlabel("informed-trader fraction  phi  (toxicity)")
    axR.set_ylabel("uninformed volume captured")
    axR.set_xlim(0, 0.6); axR.set_ylim(0, max(vol) * 1.15)

    fig.tight_layout(); fig.savefig(CHARTS / "phase_transition.png", dpi=140)
    plt.close(fig)
    return phi_c


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fig_inventory_skew()
    fig_spread_decomposition()
    phi_c = fig_phase_transition()
    print("three forced parameters:")
    print(f"  kappa (inventory skew slope) = {KAPPA}")
    print(f"  s_inv (inventory half-spread)= {S_INV}")
    print(f"  alpha (adverse-sel loading)  = {ALPHA}")
    print(f"critical informed fraction phi* (freeze) = {phi_c:.3f}")
    print("charts ->", CHARTS)
