"""Illustrative schematic diagrams for the Deribit dealer-positioning post.

These are *teaching schematics*, not snapshots of live data — they show the
reader what shape to look for on the live dashboard and how to read it. Clearly
labelled as illustrative so nothing here is mistaken for a real market reading.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[2] / "static" / "charts" / "deribit-dealer-positioning"
OUT.mkdir(parents=True, exist_ok=True)


def gex_reading() -> None:
    """Aggregate dealer GEX vs spot, with the zero-gamma flip and the two
    regimes you'd trade differently."""
    spot = np.linspace(0.85, 1.15, 400)        # spot relative to a reference of 1.0
    flip = 0.985                                # illustrative zero-gamma flip
    # Standard shape: NEGATIVE below the flip (short gamma), POSITIVE above
    # (long gamma). Odd function around the flip, with a hump on each side.
    gex = 30.0 * (spot - flip) * np.exp(-((spot - flip) ** 2) / 0.012)
    ymax = float(np.max(np.abs(gex)))

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ax.axhline(0, color="#444", lw=0.8)
    ax.axvline(flip, color="#d62728", lw=1.4, linestyle="--")
    ax.plot(spot, gex, color="#1f77b4", lw=2.2)

    # Shade the two regimes
    ax.fill_between(spot, gex, 0, where=(spot >= flip), color="#2a9d8f", alpha=0.15)
    ax.fill_between(spot, gex, 0, where=(spot < flip), color="#e76f51", alpha=0.15)

    ax.set_ylim(-1.5 * ymax, 1.5 * ymax)
    ax.annotate("zero-gamma flip", xy=(flip, 0), xytext=(flip + 0.005, 1.25 * ymax),
                fontsize=10, color="#d62728")
    ax.text(1.07, 0.7 * ymax,
            "ABOVE flip\ndealers long gamma\n→ they SELL rallies, BUY dips\n→ vol suppressed, ranges hold",
            fontsize=9.5, color="#1d6f63", ha="center",
            bbox=dict(boxstyle="round", fc="#eafaf6", ec="#2a9d8f"))
    ax.text(0.905, -0.75 * ymax,
            "BELOW flip\ndealers short gamma\n→ they BUY rallies, SELL dips\n→ moves amplified, trends extend",
            fontsize=9.5, color="#9c3b27", ha="center",
            bbox=dict(boxstyle="round", fc="#fdeee9", ec="#e76f51"))

    ax.set_xlabel("spot (relative to reference = 1.00)")
    ax.set_ylabel("aggregate dealer gamma exposure  (\$ per 1% move)")
    ax.set_title("Reading the GEX chart: the spot level where dealer hedging\n"
                 "flips from dampening to amplifying  (illustrative schematic)")
    ax.set_yticks([])
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "gex_reading.png", dpi=140)
    print(f"saved {OUT / 'gex_reading.png'}")


def skew_reading() -> None:
    """An IV smile with the 25-delta put/call and ATM marked, and the
    risk-reversal / butterfly read annotated."""
    k = np.linspace(-0.6, 0.6, 400)            # log-moneyness
    # A put-skewed smile (puts richer than calls), typical "crash fear" shape.
    iv = 0.55 + 0.9 * (k - 0.05) ** 2 - 0.35 * (k - 0.05)
    k_p, k_c = -0.28, 0.28                      # ~25-delta points (illustrative)
    iv_p = 0.55 + 0.9 * (k_p - 0.05) ** 2 - 0.35 * (k_p - 0.05)
    iv_c = 0.55 + 0.9 * (k_c - 0.05) ** 2 - 0.35 * (k_c - 0.05)
    iv_atm = 0.55 + 0.9 * (0 - 0.05) ** 2 - 0.35 * (0 - 0.05)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(k, iv, color="#1f77b4", lw=2.2, label="fitted SVI smile")
    ax.axvline(0, color="#888", lw=0.8, linestyle=":")
    for kk, vv, lab, col in [(k_p, iv_p, "25Δ put", "#e76f51"),
                             (0, iv_atm, "ATM", "#444"),
                             (k_c, iv_c, "25Δ call", "#2a9d8f")]:
        ax.scatter([kk], [vv], s=60, color=col, zorder=5)
        ax.annotate(lab, xy=(kk, vv), xytext=(kk, vv + 0.045), ha="center",
                    fontsize=10, color=col)

    # Risk-reversal annotation (put IV vs call IV)
    ax.annotate("", xy=(k_p, iv_p), xytext=(k_c, iv_c),
                arrowprops=dict(arrowstyle="<->", color="#9467bd", lw=1.3))
    ax.text(0.0, (iv_p + iv_c) / 2 + 0.02,
            "Risk-reversal (RR) = call IV − put IV\nputs richer → market paying up for downside",
            fontsize=9.5, color="#6a4a9c", ha="center",
            bbox=dict(boxstyle="round", fc="#f3eefb", ec="#9467bd"))

    # Butterfly annotation (wings vs ATM)
    ax.annotate("Butterfly (BF) = wing avg − ATM\nhigher → market paying up for big moves either way",
                xy=(k_c, iv_c), xytext=(0.18, iv_atm - 0.16),
                fontsize=9.5, color="#1d6f63", ha="center",
                bbox=dict(boxstyle="round", fc="#eafaf6", ec="#2a9d8f"),
                arrowprops=dict(arrowstyle="->", color="#2a9d8f"))

    ax.set_xlabel("log-moneyness  $k = \\ln(K / F)$   (puts ← 0 → calls)")
    ax.set_ylabel("implied volatility")
    ax.set_title("Reading the skew: risk-reversal is directional positioning,\n"
                 "butterfly is the price of tails  (illustrative schematic)")
    ax.legend(loc="upper center")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUT / "skew_reading.png", dpi=140)
    print(f"saved {OUT / 'skew_reading.png'}")


if __name__ == "__main__":
    gex_reading()
    skew_reading()
