"""Three clean avatar directions for 'Marked to Madness'. Premium/editorial,
no horror-red jagged lines. 1000x1000, designed to survive X's circle crop."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle
from matplotlib import font_manager

OUTDIR = Path(__file__).resolve().parents[2] / "static" / "brand"
OUTDIR.mkdir(parents=True, exist_ok=True)

INK = "#0E1320"
INK2 = "#171D2E"
CREAM = "#ECE6D6"
VERM = "#FF5A3C"
TEAL = "#1FC7B6"
MUTE = "#7E839A"

MONO = font_manager.FontProperties(family="DejaVu Sans Mono", weight="bold")
MONO_R = font_manager.FontProperties(family="DejaVu Sans Mono")


def _base():
    fig = plt.figure(figsize=(10, 10), dpi=100)
    fig.patch.set_facecolor(INK)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(INK); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    return fig, ax


def opt1_monogram():
    """Confident M2M monogram + a thin badge ring and a single up-tick rule."""
    fig, ax = _base()
    ax.add_patch(Circle((0.5, 0.5), 0.45, fill=False, ec=MUTE, lw=2.5, alpha=0.35))
    ax.text(0.5, 0.545, "M2M", color=CREAM, fontproperties=MONO, fontsize=150,
            ha="center", va="center")
    # subtle up-tick rule beneath
    ax.plot([0.30, 0.56], [0.345, 0.345], color=MUTE, lw=3, solid_capstyle="round")
    ax.plot([0.56, 0.70], [0.345, 0.40], color=VERM, lw=4, solid_capstyle="round")
    ax.text(0.5, 0.265, "MARKED TO MADNESS", color=MUTE, fontproperties=MONO_R,
            fontsize=17.5, ha="center", va="center")
    fig.savefig(OUTDIR / "avatar_1.png", facecolor=INK, dpi=100); plt.close(fig)


def opt2_candles():
    """A tidy row of candlesticks (calm -> one breakout) under the monogram."""
    fig, ax = _base()
    xs = [0.30, 0.41, 0.52, 0.63, 0.74]
    bodies = [(0.50, 0.60, CREAM), (0.47, 0.58, CREAM), (0.52, 0.64, TEAL),
              (0.40, 0.55, VERM), (0.58, 0.74, TEAL)]
    wicks = [(0.45, 0.66), (0.43, 0.63), (0.47, 0.70), (0.35, 0.60), (0.52, 0.80)]
    w = 0.052
    for x, (lo, hi, c), (wl, wh) in zip(xs, bodies, wicks):
        ax.plot([x, x], [wl, wh], color=c, lw=3, solid_capstyle="round")
        ax.add_patch(FancyBboxPatch((x - w / 2, lo), w, hi - lo,
                     boxstyle="round,pad=0,rounding_size=0.012", fc=c, ec="none"))
    ax.text(0.5, 0.30, "M2M", color=CREAM, fontproperties=MONO, fontsize=92,
            ha="center", va="center")
    fig.savefig(OUTDIR / "avatar_2.png", facecolor=INK, dpi=100); plt.close(fig)


def opt3_ticker():
    """A stock-ticker chip: $M2M with an up arrow. Playful, finance-native."""
    fig, ax = _base()
    chip = FancyBboxPatch((0.16, 0.37), 0.68, 0.26,
                          boxstyle="round,pad=0.01,rounding_size=0.06",
                          fc=INK2, ec=VERM, lw=3, transform=ax.transAxes)
    ax.add_patch(chip)
    ax.text(0.45, 0.502, "$M2M", color=CREAM, fontproperties=MONO, fontsize=78,
            ha="center", va="center")
    ax.text(0.745, 0.502, "▲", color=TEAL, fontsize=46, ha="center", va="center")
    ax.text(0.5, 0.285, "marked to madness", color=MUTE, fontproperties=MONO_R,
            fontsize=18, ha="center", va="center")
    fig.savefig(OUTDIR / "avatar_3.png", facecolor=INK, dpi=100); plt.close(fig)


if __name__ == "__main__":
    opt1_monogram(); opt2_candles(); opt3_ticker()
    print(f"-> {OUTDIR} : avatar_1.png avatar_2.png avatar_3.png")
