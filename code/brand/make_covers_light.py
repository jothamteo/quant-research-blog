"""Light/warm/flat covers for every post — Sakana-spirit: soft cream background,
rounded pastel panel, friendly rounded font, a category pill, one flat motif.
1200x630, written to static/covers/<slug>.png."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse, Rectangle, RegularPolygon, Polygon, Arc
from matplotlib import font_manager as fm

OUT = Path(__file__).resolve().parents[2] / "static" / "covers"
OUT.mkdir(parents=True, exist_ok=True)
RND = fm.FontProperties(fname="/System/Library/Fonts/SFCompactRounded.ttf")

CREAM = "#F7F0E3"; INK = "#2C2723"; MUTE = "#9A9080"
CORAL = "#F4795B"; MINT = "#CFE8DD"; PEACH = "#FBDFC6"; SKY = "#CFE0EE"
LILAC = "#E4D8EF"; LEMON = "#F6E6AE"; TEAL = "#1FBFA9"; BLUE = "#5B9BD5"; MUST = "#E8B54B"
AR = 630 / 1200  # aspect: multiply x-radius to draw round circles


def dot(ax, x, y, r, fc, ec="white", lw=2):
    ax.add_patch(Ellipse((x, y), 2 * r * AR, 2 * r, fc=fc, ec=ec, lw=lw))


def cover(slug, tag, tag_color, title_lines, panel, motif):
    fig = plt.figure(figsize=(12, 6.3), dpi=100); fig.patch.set_facecolor(CREAM)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(Rectangle((0, 0), 1, 1, color=CREAM, zorder=0))
    ax.add_patch(FancyBboxPatch((0.55, 0.15), 0.40, 0.70,
                 boxstyle="round,pad=0,rounding_size=0.045", fc=panel, ec="none"))
    motif(ax)
    ax.add_patch(FancyBboxPatch((0.055, 0.78), 0.02 + 0.0135 * len(tag), 0.072,
                 boxstyle="round,pad=0.006,rounding_size=0.05", fc=tag_color, ec="none"))
    ax.text(0.065, 0.815, tag, color="white", fontproperties=RND, fontsize=12.5, ha="left", va="center")
    y = 0.605
    for ln in title_lines:
        ax.text(0.055, y, ln, color=INK, fontproperties=RND, fontsize=41, ha="left", va="center")
        y -= 0.12
    ax.text(0.057, y + 0.005, "marked to model  ·  reproducible quant research",
            color=MUTE, fontproperties=RND, fontsize=13.5, ha="left", va="top")
    fig.savefig(OUT / f"{slug}.png", facecolor=CREAM, dpi=100); plt.close(fig)
    print(slug)


# ---------- motifs (drawn inside the panel x:0.55-0.95, y:0.15-0.85) ----------
def _line(ax, xs, ys, c, lw=4):
    ax.plot(xs, ys, color=c, lw=lw, solid_capstyle="round", solid_joinstyle="round")

def m_saw(ax):
    x = np.linspace(0.60, 0.90, 120); _line(ax, x, 0.55 + 0.07 * np.sin(np.linspace(0, 22, 120)), CORAL)
    for cx, c in [(0.64, MUST), (0.71, BLUE), (0.78, CORAL)]: dot(ax, cx, 0.34, 0.028, c)
    ax.text(0.75, 0.70, "$", color=INK, fontproperties=RND, fontsize=30, ha="center", va="center")

def m_smile(ax):
    k = np.linspace(-1, 1, 120); _line(ax, 0.745 + 0.16 * k, 0.5 + 0.16 * (k + 0.15) ** 2 - 0.05 * (k + 0.15), CORAL)
    dot(ax, 0.62, 0.55, 0.022, BLUE); dot(ax, 0.745, 0.47, 0.022, MUST); dot(ax, 0.87, 0.58, 0.022, TEAL)

def m_umbrella(ax):
    th = np.linspace(0, np.pi, 60); cx, cy, r = 0.745, 0.55, 0.13
    ax.add_patch(plt.Polygon(np.c_[cx + r * np.cos(th) * AR, cy + r * np.sin(th)], color=CORAL))
    for a in np.linspace(0.05, 0.95, 5):
        xx = cx + r * np.cos(np.pi * a) * AR; ax.plot([xx, cx], [cy + r * np.sin(np.pi * a) - 0.003, cy], color="white", lw=1.5)
    ax.plot([cx, cx], [cy, 0.34], color=INK, lw=3); ax.plot([cx, cx + 0.03], [0.34, 0.36], color=INK, lw=3)

def m_event(ax):
    x = np.linspace(0.58, 0.92, 100); y = 0.45 + 0.02 * np.sin(np.linspace(0, 8, 100))
    y = np.where(x > 0.74, 0.45 + (x - 0.74) * 0.9, y); _line(ax, x, y, TEAL)
    ax.plot([0.74, 0.74], [0.30, 0.70], color=CORAL, lw=2, ls=(0, (2, 2))); dot(ax, 0.74, 0.45, 0.02, CORAL)

def m_bars(ax):
    for i, (h, c) in enumerate([(0.22, TEAL), (0.30, CORAL)]):
        ax.add_patch(FancyBboxPatch((0.63 + i * 0.13, 0.34), 0.08, h, boxstyle="round,pad=0,rounding_size=0.01", fc=c, ec="none"))
    dot(ax, 0.83, 0.42, 0.03, MUST); ax.text(0.83, 0.42, "$", color="white", fontproperties=RND, fontsize=18, ha="center", va="center")

def m_cone(ax):
    x = np.linspace(0.60, 0.90, 80); m = 0.55 + 0.0 * x; sd = 0.02 + (x - 0.60) * 0.6
    ax.fill_between(x, m - sd, m + sd, color=CORAL, alpha=0.25); _line(ax, x, m, CORAL, lw=3)

def m_reliab(ax):
    ax.plot([0.60, 0.90], [0.32, 0.78], color=MUTE, lw=2, ls=(0, (3, 3)))
    rng = np.random.default_rng(5); xs = np.linspace(0.62, 0.88, 7)
    for x in xs: dot(ax, x, 0.32 + (x - 0.60) * 1.53 + rng.normal(0, 0.015), 0.02, TEAL)

def m_twovenue(ax):
    ax.add_patch(FancyBboxPatch((0.59, 0.42), 0.10, 0.16, boxstyle="round,pad=0,rounding_size=0.02", fc=CORAL, ec="none"))
    ax.add_patch(FancyBboxPatch((0.81, 0.42), 0.10, 0.16, boxstyle="round,pad=0,rounding_size=0.02", fc=BLUE, ec="none"))
    ax.text(0.75, 0.50, "=", color=INK, fontproperties=RND, fontsize=34, ha="center", va="center")

def m_ladder(ax):
    for i in range(4):
        ax.add_patch(FancyBboxPatch((0.60 + i * 0.07, 0.32 + i * 0.07), 0.06, 0.05, boxstyle="round,pad=0,rounding_size=0.01", fc=[MUST, TEAL, BLUE, CORAL][i], ec="none"))
    ax.annotate("", xy=(0.90, 0.66), xytext=(0.60, 0.36), arrowprops=dict(arrowstyle="->", color=INK, lw=2))

def m_ball(ax):  # a flat trophy (World Cup)
    cx = 0.745
    ax.add_patch(Polygon([(cx - 0.075, 0.66), (cx + 0.075, 0.66), (cx + 0.05, 0.50), (cx - 0.05, 0.50)], fc=MUST, ec="none"))
    ax.add_patch(Ellipse((cx, 0.66), 0.15 * AR * 2 / 1, 0.045, fc=MUST, ec="white", lw=2))
    ax.add_patch(Arc((cx - 0.075, 0.61), 0.07, 0.12, theta1=70, theta2=290, color=MUST, lw=4))
    ax.add_patch(Arc((cx + 0.075, 0.61), 0.07, 0.12, theta1=250, theta2=110, color=MUST, lw=4))
    ax.add_patch(Rectangle((cx - 0.013, 0.44), 0.026, 0.07, fc=MUST, ec="none"))
    ax.add_patch(FancyBboxPatch((cx - 0.055, 0.395), 0.11, 0.04, boxstyle="round,pad=0,rounding_size=0.01", fc=MUST, ec="none"))
    ax.text(cx, 0.585, "★", color="white", fontproperties=RND, fontsize=22, ha="center", va="center")

def m_clean(ax):  # data cleaning: grid of cells, some highlighted + sparkle
    for r in range(3):
        for c in range(4):
            x = 0.60 + c * 0.072; y = 0.38 + r * 0.10
            fc = TEAL if (r + c) % 4 == 0 else "white"
            ax.add_patch(FancyBboxPatch((x, y), 0.058, 0.07, boxstyle="round,pad=0,rounding_size=0.008", fc=fc, ec=MUTE, lw=1))
    ax.text(0.90, 0.74, "*", color=MUST, fontproperties=RND, fontsize=34, ha="center", va="center")


COVERS = [
 ("ai-agents-financial-data-cleaning", "PRACTITIONER", TEAL, ["Using AI agents to", "clean financial data"], LILAC, m_clean),
 ("buying-cheap-vol-crypto", "VOLATILITY", CORAL, ["Buying cheap vol", "on crypto"], SKY, m_umbrella),
 ("deribit-dealer-positioning", "OPTIONS", BLUE, ["Reading dealer", "positioning on Deribit"], LEMON, m_smile),
 ("event-study-methodology", "METHODOLOGY", TEAL, ["A practical guide", "to event studies"], MINT, m_event),
 ("funding-rate-carry-btc", "CRYPTO · CARRY", MUST, ["Funding-rate carry", "in BTC perps"], PEACH, m_bars),
 ("garch-covariates-volatility", "VOLATILITY", CORAL, ["Do extra signals", "improve vol forecasts?"], MINT, m_cone),
 ("grid-bot-regime", "MARKET MAKING", CORAL, ["When does a grid", "bot make money?"], MINT, m_saw),
 ("polymarket-vs-option-implied-btc", "PREDICTION MARKETS", BLUE, ["Two venues,", "one bet"], PEACH, m_twovenue),
 ("prediction-market-calibration", "PREDICTION MARKETS", TEAL, ["Are prediction markets", "well-calibrated?"], SKY, m_reliab),
 ("sp500-index-addition-premium", "EQUITIES", BLUE, ["Has the index-addition", "premium disappeared?"], LEMON, m_ladder),
 ("world-cup-models-vs-markets", "SPORTS", TEAL, ["Two models, two markets,", "one World Cup"], MINT, m_ball),
]

if __name__ == "__main__":
    for args in COVERS:
        cover(*args)
    print(f"-> {OUT}  ({len(COVERS)} covers)")
