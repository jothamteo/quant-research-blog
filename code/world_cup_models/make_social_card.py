"""Generate a 1200x675 X/Twitter social card for the World Cup post.
Pulls the real model-vs-market numbers from results.json. WC-2026 palette."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE.parents[1] / "static" / "charts" / "world-cup-models" / "social_card.png"

# palette
NAVY = "#0A0E27"
NAVY2 = "#121734"
PINK = "#E6357A"
TEAL = "#19C3B2"
GOLD = "#FFC72C"
INK = "#F4F6FF"
MUTE = "#8C93B8"

res = json.load(open(DATA / "results.json"))
champ = {r["team"]: r for r in res["champion"]}
teams = ["France", "Spain", "Argentina", "England"]
model = [champ[t]["dc"] * 100 for t in teams]     # Dixon-Coles
market = [champ[t]["pm"] * 100 for t in teams]     # Polymarket de-vig

fig = plt.figure(figsize=(12, 6.75), dpi=100)
fig.patch.set_facecolor(NAVY)

# subtle top band
band = fig.add_axes([0, 0.93, 1, 0.07]); band.set_facecolor(NAVY2); band.axis("off")
band.text(0.035, 0.5, "MARKED TO MADNESS", color=GOLD, fontsize=15, fontweight="bold",
          va="center", ha="left", transform=band.transAxes, family="DejaVu Sans")
band.text(0.965, 0.5, "jothamteo.github.io/quant-research-blog", color=MUTE, fontsize=11,
          va="center", ha="right", transform=band.transAxes)

# headline
head = fig.add_axes([0, 0.55, 1, 0.36]); head.axis("off"); head.set_facecolor(NAVY)
head.text(0.035, 0.78, "Two models. Two markets.\nOne World Cup.", color=INK,
          fontsize=33, fontweight="bold", va="top", ha="left", linespacing=1.05,
          transform=head.transAxes)
head.text(0.035, 0.12, "Dixon-Coles + Elo, calibrated out-of-sample, vs live "
          "Polymarket & Hyperliquid odds.", color=TEAL, fontsize=14.5, va="bottom",
          ha="left", transform=head.transAxes)

# bar chart: model vs market for 4 teams
ax = fig.add_axes([0.11, 0.10, 0.50, 0.42]); ax.set_facecolor(NAVY)
for s in ax.spines.values():
    s.set_visible(False)
y = range(len(teams))
h = 0.38
ax.barh([i + h / 2 for i in y], model, h, color=PINK, label="My model")
ax.barh([i - h / 2 for i in y], market, h, color=GOLD, label="Market")
ax.set_yticks(list(y)); ax.set_yticklabels(teams[::-1] if False else teams,
                                           color=INK, fontsize=13)
ax.invert_yaxis()
ax.tick_params(axis="x", colors=MUTE, labelsize=10)
ax.tick_params(axis="y", length=0)
ax.set_xlim(0, max(max(model), max(market)) * 1.18)
for i in y:
    ax.text(model[i] + 0.4, i + h / 2, f"{model[i]:.0f}%", color=PINK, fontsize=11,
            va="center", fontweight="bold")
    ax.text(market[i] + 0.4, i - h / 2, f"{market[i]:.0f}%", color=GOLD, fontsize=11,
            va="center", fontweight="bold")
ax.set_xlabel("chance of winning the World Cup", color=MUTE, fontsize=10.5)
ax.legend(loc="lower right", frameon=False, labelcolor=INK, fontsize=11)
ax.set_title("Model vs market (champion)", color=INK, fontsize=13.5,
             fontweight="bold", loc="left", pad=8)

# right-hand callout: the France hook
call = fig.add_axes([0.64, 0.10, 0.32, 0.42]); call.axis("off"); call.set_facecolor(NAVY)
box = FancyBboxPatch((0.02, 0.04), 0.96, 0.92, boxstyle="round,pad=0.02,rounding_size=0.05",
                     transform=call.transAxes, facecolor=NAVY2, edgecolor=PINK, linewidth=2)
call.add_patch(box)
call.text(0.5, 0.82, "THE CALL", color=GOLD, fontsize=12, fontweight="bold", ha="center",
          transform=call.transAxes)
call.text(0.5, 0.60, "France", color=INK, fontsize=27, fontweight="bold", ha="center",
          transform=call.transAxes)
fr_dc = champ["France"]["dc"] * 100; fr_pm = champ["France"]["pm"] * 100
call.text(0.5, 0.42, f"market {fr_pm:.0f}%   ·   model {fr_dc:.0f}%", color=TEAL,
          fontsize=14.5, ha="center", transform=call.transAxes)
call.text(0.5, 0.20, "The favourite looks\nover-bet. Graded in July.", color=MUTE,
          fontsize=12.5, ha="center", va="center", linespacing=1.2,
          transform=call.transAxes)

fig.savefig(OUT, facecolor=NAVY, dpi=100)
print(f"saved {OUT}  ({OUT.stat().st_size // 1024} KB)")
