"""Mark to Model — cinematic Didone rebrand. Avatar + header.

Style brief (from reference): high-contrast 'Didone' display serif (Didot),
near-monochrome cream on a dark, spotlit, vignetted background. No mascot.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

OUTDIR = Path(__file__).resolve().parents[2] / "static" / "brand"
OUTDIR.mkdir(parents=True, exist_ok=True)

DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
fm.fontManager.addfont(DIDOT)
SERIF = fm.FontProperties(fname=DIDOT)              # regular
SERIF_B = fm.FontProperties(fname=DIDOT)            # (Didot.ttc face 0)

CREAM = "#F2EEE4"
MUTE = "#9AA0A6"
GOLD = "#C9A24B"


def _bg(ax, w, h, cx=0.5, cy=0.56):
    """Dark, spotlit, vignetted cinematic background as an RGB image."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    xx /= w; yy = 1 - yy / h
    d = np.sqrt(((xx - cx) * 1.15) ** 2 + (yy - cy) ** 2)
    s = np.clip(1 - d / 0.85, 0, 1) ** 1.7           # spotlight falloff
    edge = np.array([7, 10, 12]) / 255.0             # near-black, cool
    center = np.array([26, 33, 37]) / 255.0          # lifted charcoal-teal
    img = edge[None, None] + (center - edge)[None, None] * s[..., None]
    # gentle vignette in corners
    vig = np.clip(1 - (np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2) / 0.95) ** 2.2, 0.55, 1)
    img *= vig[..., None]
    ax.imshow(np.clip(img, 0, 1), extent=[0, 1, 0, 1], origin="lower", zorder=0)


def _tracked(s, gap=" "):
    return gap.join(list(s))


def header():
    W, H = 1500, 500
    fig = plt.figure(figsize=(15, 5), dpi=100); fig.patch.set_facecolor("#070A0C")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    _bg(ax, W, H)
    ax.text(0.5, 0.585, "MARK TO MODEL", color=CREAM, fontproperties=SERIF_B,
            fontsize=86, ha="center", va="center")
    # hairline rule
    ax.plot([0.355, 0.645], [0.40, 0.40], color=CREAM, lw=1.0, alpha=0.55)
    ax.text(0.5, 0.325, _tracked("REPRODUCIBLE  QUANT  RESEARCH"), color=MUTE,
            fontproperties=SERIF, fontsize=15.5, ha="center", va="center", alpha=0.9)
    fig.savefig(OUTDIR / "header.png", facecolor="#070A0C", dpi=100); plt.close(fig)
    print("header.png 1500x500")


def avatar():
    W = H = 1000
    fig = plt.figure(figsize=(10, 10), dpi=100); fig.patch.set_facecolor("#070A0C")
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    _bg(ax, W, H, cx=0.5, cy=0.54)
    ax.text(0.5, 0.55, "M2M", color=CREAM, fontproperties=SERIF_B, fontsize=210,
            ha="center", va="center")
    ax.plot([0.34, 0.66], [0.345, 0.345], color=CREAM, lw=1.1, alpha=0.5)
    ax.text(0.5, 0.285, _tracked("MARK TO MODEL"), color=MUTE, fontproperties=SERIF,
            fontsize=17, ha="center", va="center", alpha=0.9)
    fig.savefig(OUTDIR / "avatar.png", facecolor="#070A0C", dpi=100); plt.close(fig)
    print("avatar.png 1000x1000")


if __name__ == "__main__":
    header(); avatar()
    print(f"-> {OUTDIR}")
