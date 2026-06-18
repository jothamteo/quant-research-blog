"""Mark to Model — light/editorial variant (cream paper, black Didot).
Outputs *_light.png so it can be compared against the dark versions."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle

OUTDIR = Path(__file__).resolve().parents[2] / "static" / "brand"
DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
fm.fontManager.addfont(DIDOT)
SERIF = fm.FontProperties(fname=DIDOT)

PAPER = "#EDE7D8"     # warm cream
INK = "#15120D"       # near-black, warm
MUTE = "#6E6757"


def _paper_bg(ax, w, h):
    """Flat cream with a whisper of edge vignette for an editorial feel."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    xx /= w; yy /= h
    d = np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2)
    shade = np.clip(1 - (d / 0.95) ** 2.4 * 0.10, 0.9, 1)  # subtle
    base = np.array([237, 231, 216]) / 255.0
    img = base[None, None] * shade[..., None]
    ax.imshow(np.clip(img, 0, 1), extent=[0, 1, 0, 1], origin="lower", zorder=0)


def _tracked(s):
    return " ".join(list(s))


def header():
    W, H = 1500, 500
    fig = plt.figure(figsize=(15, 5), dpi=100); fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    _paper_bg(ax, W, H)
    # thin editorial keyline frame
    ax.add_patch(Rectangle((0.022, 0.06), 0.956, 0.88, fill=False, ec=INK, lw=1.1, alpha=0.5))
    ax.text(0.5, 0.585, "MARK TO MODEL", color=INK, fontproperties=SERIF,
            fontsize=86, ha="center", va="center")
    ax.plot([0.355, 0.645], [0.40, 0.40], color=INK, lw=1.0, alpha=0.5)
    ax.text(0.5, 0.325, _tracked("REPRODUCIBLE  QUANT  RESEARCH"), color=MUTE,
            fontproperties=SERIF, fontsize=15.5, ha="center", va="center")
    fig.savefig(OUTDIR / "header_light.png", facecolor=PAPER, dpi=100); plt.close(fig)
    print("header_light.png")


def avatar():
    W = H = 1000
    fig = plt.figure(figsize=(10, 10), dpi=100); fig.patch.set_facecolor(PAPER)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    _paper_bg(ax, W, H)
    ax.text(0.5, 0.55, "M2M", color=INK, fontproperties=SERIF, fontsize=210,
            ha="center", va="center")
    ax.plot([0.34, 0.66], [0.345, 0.345], color=INK, lw=1.1, alpha=0.5)
    ax.text(0.5, 0.285, _tracked("MARK TO MODEL"), color=MUTE, fontproperties=SERIF,
            fontsize=17, ha="center", va="center")
    fig.savefig(OUTDIR / "avatar_light.png", facecolor=PAPER, dpi=100); plt.close(fig)
    print("avatar_light.png")


if __name__ == "__main__":
    header(); avatar()
    print(f"-> {OUTDIR}")
