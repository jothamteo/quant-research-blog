"""On-brand cover images for blog posts — dark editorial, Didot title, one minimal
topic motif each. 1200x630, consistent with the Mark to Model avatar/header.
Writes to static/covers/<slug>.png; posts reference them via PaperMod `cover`.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

OUT = Path(__file__).resolve().parents[2] / "static" / "covers"
OUT.mkdir(parents=True, exist_ok=True)
DIDOT = "/System/Library/Fonts/Supplemental/Didot.ttc"
fm.fontManager.addfont(DIDOT)
SERIF = fm.FontProperties(fname=DIDOT)
MONO = fm.FontProperties(family="DejaVu Sans Mono")

INK = "#0E1320"; INK2 = "#161B2B"; CREAM = "#F2EEE4"; MUTE = "#8C93B8"
VERM = "#FF5A3C"; TEAL = "#1FC7B6"


def _bg(ax, w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(float); xx /= w; yy = 1 - yy / h
    d = np.sqrt(((xx - 0.62) * 1.1) ** 2 + (yy - 0.6) ** 2)
    s = np.clip(1 - d / 0.9, 0, 1) ** 1.7
    edge = np.array([14, 19, 32]) / 255.0; cen = np.array([28, 35, 52]) / 255.0
    img = edge[None, None] + (cen - edge)[None, None] * s[..., None]
    ax.imshow(np.clip(img, 0, 1), extent=[0, 1, 0, 1], origin="lower", zorder=0)


def cover(slug, kicker, title_lines, motif):
    W, H = 1200, 630
    fig = plt.figure(figsize=(12, 6.3), dpi=100); fig.patch.set_facecolor(INK)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    _bg(ax, W, H)
    # motif lives on the right half / background
    motif(ax)
    # kicker + title (left)
    ax.text(0.055, 0.86, "MARK TO MODEL", color=MUTE, fontproperties=MONO,
            fontsize=15, ha="left", va="center")
    ax.text(0.055, 0.80, kicker, color=TEAL, fontproperties=MONO, fontsize=12.5,
            ha="left", va="center")
    y = 0.60
    for ln in title_lines:
        ax.text(0.052, y, ln, color=CREAM, fontproperties=SERIF, fontsize=44,
                ha="left", va="center")
        y -= 0.135
    fig.savefig(OUT / f"{slug}.png", facecolor=INK, dpi=100); plt.close(fig)
    print(f"{slug}.png")


# ---- topic motifs (faint, right side) ----
def m_grid(ax):
    rng = np.random.default_rng(3); x = np.linspace(0.5, 0.97, 220)
    saw = 0.5 + 0.06 * np.sin(np.linspace(0, 38, 220)) + rng.normal(0, 0.01, 220)
    ax.plot(x, saw, color=VERM, lw=1.6, alpha=0.85)
    for yv in np.linspace(0.42, 0.58, 7):
        ax.plot([0.5, 0.97], [yv, yv], color=MUTE, lw=0.6, alpha=0.25)


def m_curve_up(ax):  # generic rising/❤ vol line
    x = np.linspace(0.5, 0.97, 200)
    y = 0.45 + 0.12 * (x - 0.5) / 0.47 + 0.03 * np.sin(np.linspace(0, 12, 200))
    ax.plot(x, y, color=TEAL, lw=2, alpha=0.85)


def m_smile(ax):  # vol smile
    k = np.linspace(-1, 1, 200); v = 0.5 + 0.13 * (k + 0.1) ** 2 - 0.05 * (k + 0.1)
    ax.plot(0.73 + 0.22 * k, v, color=VERM, lw=2, alpha=0.85)


def m_bars(ax):  # regime bars
    xs = np.linspace(0.54, 0.93, 6); hs = [0.10, 0.13, 0.08, -0.06, -0.12, 0.05]
    for x, h in zip(xs, hs):
        ax.add_patch(plt.Rectangle((x, 0.5), 0.045, h, color=TEAL if h > 0 else VERM, alpha=0.8))
    ax.plot([0.52, 0.95], [0.5, 0.5], color=MUTE, lw=0.8, alpha=0.5)


def m_scatter(ax):  # calibration / gap scatter
    rng = np.random.default_rng(7); x = rng.uniform(0.52, 0.95, 60); y = 0.5 + (x - 0.73) + rng.normal(0, 0.04, 60)
    ax.scatter(x, np.clip(y, 0.3, 0.72), s=12, color=TEAL, alpha=0.7)
    ax.plot([0.52, 0.95], [0.29, 0.72], color=MUTE, lw=0.8, ls="--", alpha=0.5)


if __name__ == "__main__":
    # sample only
    cover("grid-bot-regime", "market-making · mean reversion",
          ["When does a grid", "bot make money?"], m_grid)
