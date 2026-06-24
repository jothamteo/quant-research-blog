"""Market making and transient impact for an FX dealer — a lean reproduction.

Reproduces the *mechanism* in Barzykin, "Market Making and Transient Impact in
Spot FX" (arXiv:2601.13421): a dealer warehouses inventory from client flow and
hedges it in the interbank market, where its own hedging trades carry **transient**
market impact — a price displacement that decays at a resilience rate rho.

The single knob rho nests both Almgren-Chriss limits:
    rho -> 0     impact never heals   -> purely *permanent* impact
    rho -> inf   impact heals at once  -> purely *temporary* (instantaneous) impact
Real spot FX lives in between, which is exactly the interesting regime.

We avoid the full optimal-control machinery and instead make the trade-off
explicit and robust. The dealer hedges a position Q at a constant rate over a
horizon tau. Transient impact is the exponential propagator
    J(t) = eta * integral_0^t exp(-rho (t-s)) v(s) ds.
Costs of the hedge:
    impact cost   = integral v(t) J(t) dt          (favours SLOW: let impact decay)
    risk cost     = gamma * integral q(t)^2 dt      (favours FAST: don't warehouse risk)
The dealer picks the horizon tau that minimises the sum. That single 1-D trade-off
is the paper's subject: risk management vs impact resilience.

`python simulate.py` writes three charts and prints a small table.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
CHARTS = HERE.parents[1] / "static" / "charts" / "fx-transient-impact"
CHARTS.mkdir(parents=True, exist_ok=True)

BL, OR, GR, RED, PUR = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728", "#6a4c93"

ETA = 1.0          # transient-impact loading
Q0 = 1.0           # inventory to hedge (normalised)
DT = 0.002         # integration step


def hedge_paths(tau: float, rho: float, eta: float = ETA, q0: float = Q0, dt: float = DT):
    """Constant-rate hedge of q0 over [0, tau]; integrate the propagator past it.

    Returns (t, v, q, J): time grid, hedge rate, inventory, price displacement.
    The grid runs to ~ tau + 6/rho so the impact fully relaxes. The step is
    refined for short horizons so the integral stays accurate.
    """
    dt = min(dt, tau / 300.0)                        # adaptive: >=300 steps within tau
    t_end = tau + 6.0 / max(rho, 0.2)
    n = int(t_end / dt)
    t = np.arange(n) * dt
    v = np.where(t < tau, q0 / tau, 0.0)            # constant hedge rate, then stop
    q = np.clip(q0 - np.cumsum(v) * dt, 0.0, None)  # inventory drawn down to 0
    # exponential-propagator impact: J_{k} = (1-rho dt) J_{k-1} + eta v_k dt
    J = np.empty(n)
    j = 0.0
    decay = 1.0 - rho * dt
    for k in range(n):
        j = decay * j + eta * v[k] * dt
        J[k] = j
    return t, v, q, J


def hedge_cost(tau: float, rho: float, gamma: float, eta: float = ETA):
    """Total cost of hedging q0 over horizon tau: impact + inventory risk."""
    t, v, q, J = hedge_paths(tau, rho, eta)
    dt = t[1] - t[0]                                # the adaptive step actually used
    impact = float(np.sum(v * J) * dt)              # integral v(t) J(t) dt
    risk = float(gamma * np.sum(q * q) * dt)        # gamma integral q^2 dt
    return impact, risk, impact + risk


def optimal_tau(rho: float, gamma: float, taus=None):
    if taus is None:
        taus = np.geomspace(0.02, 8.0, 200)
    costs = np.array([hedge_cost(tau, rho, gamma)[2] for tau in taus])
    i = int(np.argmin(costs))
    return float(taus[i]), float(costs[i])


# ---------------------------------------------------------------------------
def fig_signature():
    """Fig 1 — the transient signature: a hedge pushes the interbank price up, which
    then mean-reverts once hedging stops. Same schedule, three resiliences."""
    fig, ax = plt.subplots(figsize=(9, 5))
    tau = 1.0
    for rho, c, lab in [(0.5, OR, "rho = 0.5  (near-permanent: high, slow to revert)"),
                        (1.5, GR, "rho = 1.5  (intermediate)"),
                        (8.0, BL, "rho = 8.0  (fast healing: small, quick to revert)")]:
        t, v, q, J = hedge_paths(tau, rho)
        ax.plot(t, J, color=c, lw=2, label=lab)
    ax.axvline(tau, color="#888", lw=0.9, ls="--")
    ax.text(tau + 0.1, ax.get_ylim()[1] * 0.96, "hedge ends", fontsize=9, color="#666", va="top")
    ax.axhline(0, color="#444", lw=0.7)
    ax.set_xlim(0, 12)
    ax.set_title("Interbank price displacement from a hedge  (jump, then revert)")
    ax.set_xlabel("time"); ax.set_ylabel("price displacement  J")
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout(); fig.savefig(CHARTS / "transient_signature.png", dpi=140)
    plt.close(fig)


def fig_cost_vs_speed():
    """Fig 2 — the U-shaped hedging cost: impact (favours slow) vs risk (favours
    fast). The minimum is the optimal hedge horizon. Shown for three resiliences."""
    taus = np.geomspace(0.03, 6.0, 220)
    gamma = 0.5
    fig, ax = plt.subplots(figsize=(9, 5))
    for rho, c, lab in [(0.5, OR, "rho = 0.5  (near-permanent)"),
                        (1.5, GR, "rho = 1.5  (intermediate)"),
                        (8.0, BL, "rho = 8.0  (fast healing)")]:
        costs = np.array([hedge_cost(tau, rho, gamma)[2] for tau in taus])
        ax.plot(taus, costs, color=c, lw=2, label=lab)
        i = int(np.argmin(costs))
        ax.scatter([taus[i]], [costs[i]], color=c, s=45, zorder=5)
    ax.set_xscale("log")
    ax.set_title("Total hedging cost vs hedge horizon  (dot = optimum)")
    ax.set_xlabel("hedge horizon  tau  (log) — slower hedging to the right")
    ax.set_ylabel("impact cost + inventory risk")
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout(); fig.savefig(CHARTS / "cost_vs_speed.png", dpi=140)
    plt.close(fig)


def fig_optimal_surface():
    """Fig 3 — the interplay: optimal hedge horizon tau* as a function of impact
    resilience rho, at three levels of inventory-risk aversion gamma."""
    rhos = np.geomspace(0.15, 30, 40)
    fig, ax = plt.subplots(figsize=(9, 5))
    for gamma, c, lab in [(0.1, BL, "gamma = 0.1 (risk-tolerant)"),
                          (0.5, GR, "gamma = 0.5"),
                          (2.0, RED, "gamma = 2.0 (risk-averse)")]:
        taus = np.array([optimal_tau(r, gamma)[0] for r in rhos])
        ax.plot(rhos, taus, color=c, lw=2, marker="o", ms=3, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_title("Optimal hedge horizon  tau*  vs impact resilience")
    ax.set_xlabel("impact resilience  rho  (log)  —  permanent  <—  —>  temporary")
    ax.set_ylabel("optimal hedge horizon  tau*  (log)")
    ax.legend(fontsize=9, frameon=False)
    fig.tight_layout(); fig.savefig(CHARTS / "optimal_horizon.png", dpi=140)
    plt.close(fig)


def summary():
    print("rho     gamma   tau*    cost")
    for rho in [0.2, 0.5, 1.5, 5.0, 20.0]:
        for gamma in [0.1, 0.5, 2.0]:
            tau, cost = optimal_tau(rho, gamma)
            print(f"{rho:5.2f}   {gamma:4.1f}   {tau:5.3f}  {cost:7.4f}")


if __name__ == "__main__":
    fig_signature()
    fig_cost_vs_speed()
    fig_optimal_surface()
    summary()
    print("charts ->", CHARTS)
