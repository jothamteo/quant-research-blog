"""Brand assets for 'Marked to Madness': X avatar + header banner.

Concept: 'marked to market -> marked to madness'. A price line that is calm and
orderly, then erupts into volatility. Editorial ink + vermilion palette, terminal
/ ledger feel. No gradients, no glossy orbs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

OUTDIR = Path(__file__).resolve().parents[2] / "static" / "brand"
OUTDIR.mkdir(parents=True, exist_ok=True)

INK = "#0C0E12"
CREAM = "#ECE6D6"
VERM = "#FF4D2E"
MUTE = "#7E839A"
GRID = "#1B1F2A"

MONO = font_manager.FontProperties(family="DejaVu Sans Mono", weight="bold")
MONO_R = font_manager.FontProperties(family="DejaVu Sans Mono")


def _vol_line(x, calm_frac=0.42, seed=7):
    """A series that is low-vol then erupts. Returns y in [-1,1]-ish."""
    rng = np.random.default_rng(seed)
    n = len(x)
    cut = int(n * calm_frac)
    y = np.zeros(n)
    # calm: tiny drift + small noise
    y[:cut] = 0.12 * np.sin(np.linspace(0, 3, cut)) + rng.normal(0, 0.03, cut)
    # madness: rising-amplitude jagged spikes
    amp = np.linspace(0.15, 1.0, n - cut)
    y[cut:] = amp * rng.normal(0, 1.0, n - cut)
    y[cut:] = np.clip(y[cut:], -1.05, 1.15)
    return y, cut


def avatar():
    fig = plt.figure(figsize=(10, 10), dpi=100)
    fig.patch.set_facecolor(INK)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(INK); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    # An 'M' drawn as a market line: 4 strokes, with volatility jitter overlaid.
    pts = np.array([[0.16, 0.30], [0.34, 0.74], [0.50, 0.46], [0.66, 0.74], [0.84, 0.30]])
    # densify and add rising jitter toward the right so it reads as a chart
    xs, ys = [], []
    rng = np.random.default_rng(3)
    for i in range(len(pts) - 1):
        seg = np.linspace(0, 1, 22)
        x = pts[i, 0] + seg * (pts[i + 1, 0] - pts[i, 0])
        y = pts[i, 1] + seg * (pts[i + 1, 1] - pts[i, 1])
        jit = 0.018 * rng.normal(0, 1, len(seg)) * (x - 0.16) / 0.68
        xs += list(x); ys += list(y + jit)
    ax.plot(xs, ys, color=VERM, lw=15, solid_capstyle="round", solid_joinstyle="round")
    # baseline tick row (ledger)
    ax.plot([0.13, 0.87], [0.205, 0.205], color=GRID, lw=4)
    for xt in np.linspace(0.16, 0.84, 9):
        ax.plot([xt, xt], [0.19, 0.22], color=MUTE, lw=2)
    # wordmark chip
    ax.text(0.5, 0.115, "M2M", color=CREAM, fontproperties=MONO, fontsize=46,
            ha="center", va="center")
    fig.savefig(OUTDIR / "avatar.png", facecolor=INK, dpi=100)
    plt.close(fig)
    print("avatar.png 1000x1000")


def header():
    fig = plt.figure(figsize=(15, 5), dpi=100)
    fig.patch.set_facecolor(INK)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(INK); ax.axis("off")
    ax.set_xlim(0, 1500); ax.set_ylim(0, 500)

    # the calm->madness price line across the whole banner
    x = np.linspace(60, 1455, 600)
    y, cut = _vol_line(np.linspace(0, 1, 600), calm_frac=0.50, seed=11)
    yy = 215 + y * 118
    ax.plot(x[:cut], yy[:cut], color=MUTE, lw=2.4)
    ax.plot(x[cut:], yy[cut:], color=VERM, lw=2.6)
    ax.axhline(215, color=GRID, lw=1.4, xmin=0.03, xmax=0.97)
    # the moment it breaks
    ax.axvline(x[cut], color=GRID, lw=1.2, ymin=0.16, ymax=0.74)

    # wordmark: calm part cream, madness part vermilion
    ax.text(70, 350, "MARKED TO ", color=CREAM, fontproperties=MONO, fontsize=44,
            ha="left", va="center")
    ax.text(70 + 535, 350, "MADNESS", color=VERM, fontproperties=MONO, fontsize=44,
            ha="left", va="center")
    # taglines: confined to the calm left zone, lifted clear of the avatar overlap
    ax.text(72, 292, "reproducible quant research · code-backed, rerun it yourself",
            color=CREAM, fontproperties=MONO_R, fontsize=14.5, ha="left", va="center",
            alpha=0.9)
    ax.text(72, 258, "MSc Quant Finance · prediction markets · crypto · options",
            color=MUTE, fontproperties=MONO_R, fontsize=13, ha="left", va="center")
    fig.savefig(OUTDIR / "header.png", facecolor=INK, dpi=100)
    plt.close(fig)
    print("header.png 1500x500")


if __name__ == "__main__":
    avatar()
    header()
    print(f"-> {OUTDIR}")
