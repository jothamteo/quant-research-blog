"""Composite a styled Hyperliquid trading terminal screen onto the laptop
in the capybara cover illustration.

Renders a dark-green HL-branded terminal (matching actual HL UI colours) with
a candlestick crash sequence, then perspective-warps it onto the laptop screen quad.
The logo wordmark is extracted from the PNG (dark pixels → white) so it reads
cleanly on the dark background instead of pasting a screenshot with background intact.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).resolve().parent / "assets"
BASE = ASSETS / "hyperliquid-risk-engine_base.png"
COVER = ROOT / "static" / "covers" / "hyperliquid-risk-engine.png"
LOGO = ASSETS / "hyperliquid_logo.png"

# Monitor screen quad in 1200x630 cover coords: TL, TR, BR, BL
QUAD = [(90, 70), (296, 76), (294, 230), (88, 236)]

# ── Hyperliquid brand colours ─────────────────────────────────────────────────
BG_DARK   = (10,  28, 18)      # terminal background
BG_HEADER = (14,  42, 26)      # header bar
GRID_COL  = (20,  52, 34)      # subtle grid
UP_COL    = (45, 200, 112)     # green candle  (HL green)
DN_COL    = (220,  60,  50)    # red candle
TEXT_COL  = (180, 235, 200)    # axis / price labels

# ── Panel dimensions (internal resolution before warp) ───────────────────────
CW, CH = 700, 500
HEADER_H = 72

# ── 1. Build the trading terminal panel ──────────────────────────────────────
panel = Image.new("RGB", (CW, CH), BG_DARK)
d = ImageDraw.Draw(panel)

# Header bar
d.rectangle([0, 0, CW, HEADER_H], fill=BG_HEADER)

# Hyperliquid wordmark: extract dark pixels from logo PNG → render as white
logo_src = Image.open(LOGO).convert("RGBA")
logo_arr = np.array(logo_src, dtype=np.int32)
# Dark pixels = text (sum RGB < 180); mint background ~(163,240,211) sums ~614
is_text = (logo_arr[:, :, 0] + logo_arr[:, :, 1] + logo_arr[:, :, 2]) < 200
# Build white RGBA mask
white_logo_arr = np.zeros((logo_src.height, logo_src.width, 4), dtype=np.uint8)
white_logo_arr[is_text] = [230, 255, 238, 230]
white_logo_img = Image.fromarray(white_logo_arr, mode="RGBA")

# Resize to fit header
lw = int(CW * 0.50)
lh = int(lw * white_logo_img.height / white_logo_img.width)
white_logo_img = white_logo_img.resize((lw, lh), Image.LANCZOS)
logo_y = (HEADER_H - lh) // 2
panel_rgba = panel.convert("RGBA")
panel_rgba.alpha_composite(white_logo_img, (16, max(logo_y, 4)))
panel = panel_rgba.convert("RGB")
d = ImageDraw.Draw(panel)

# Thin separator line under header
d.line([(0, HEADER_H), (CW, HEADER_H)], fill=GRID_COL, width=1)

# Small "BTC-USD" ticker label
d.text((CW - 120, 26), "BTC-USD", fill=TEXT_COL)

# ── 2. Candlestick chart ──────────────────────────────────────────────────────
plot_top  = HEADER_H + 18
plot_bot  = CH - 28
plot_left = 28
plot_right = CW - 28

# Price series: drift up gently then roll over, then massive crash candle
prices = [300]
drift = [3, 5, -2, 6, 4, -3, 7, 2, -5, 4, -4, -7, -9]
for s in drift:
    prices.append(prices[-1] + s * 3)

crash_open  = prices[-1]
crash_close = crash_open - 140          # dramatic drop

all_prices = prices + [crash_close, crash_open - 155]  # include wicks
lo = min(all_prices) - 18
hi = max(all_prices) + 18

def py(v: float) -> float:
    return plot_bot - (v - lo) / (hi - lo) * (plot_bot - plot_top)

n_candles = len(prices)            # 14 regular + 1 crash = 15 total
total_slots = n_candles + 1
bw = (plot_right - plot_left) / (total_slots + 1)
body_w = bw * 0.52

# Subtle grid lines
for gy in np.linspace(plot_top, plot_bot, 6):
    d.line([(plot_left, gy), (plot_right, gy)], fill=GRID_COL, width=1)
for gx in np.linspace(plot_left, plot_right, 8):
    d.line([(gx, plot_top), (gx, plot_bot)], fill=GRID_COL, width=1)

# Regular candles
for i in range(1, n_candles):
    o, c = prices[i - 1], prices[i]
    cx = plot_left + bw * i
    col = UP_COL if c >= o else DN_COL
    wk_hi = max(o, c) + abs(c - o) * 0.55 + 5
    wk_lo = min(o, c) - abs(c - o) * 0.55 - 5
    d.line([(cx, py(wk_hi)), (cx, py(wk_lo))], fill=col, width=2)
    yt, yb = sorted([py(o), py(c)])
    d.rectangle([cx - body_w / 2, yt, cx + body_w / 2, max(yb, yt + 3)], fill=col)

# Crash candle — long red body, long lower wick
cx_crash = plot_left + bw * n_candles
d.line([(cx_crash, py(crash_open + 8)), (cx_crash, py(crash_close - 60))],
       fill=DN_COL, width=3)
d.rectangle([cx_crash - body_w / 2 - 2, py(crash_open),
             cx_crash + body_w / 2 + 2, py(crash_close)], fill=DN_COL)

# Red down-arrow beside crash candle
ax = cx_crash + bw * 0.65
ay = py((crash_open + crash_close) / 2)
d.polygon([(ax, ay + 36), (ax - 14, ay), (ax + 14, ay)], fill=DN_COL)
d.rectangle([ax - 5, ay - 28, ax + 5, ay], fill=DN_COL)

# ── 3. Perspective-warp panel onto laptop screen quad ─────────────────────────
def perspective_coeffs(output_pts, input_pts):
    """PIL PERSPECTIVE coefficients: output pixel → input pixel mapping."""
    M = []
    for (ox, oy), (ix, iy) in zip(output_pts, input_pts):
        M.append([ox, oy, 1, 0, 0, 0, -ix * ox, -ix * oy])
        M.append([0, 0, 0, ox, oy, 1, -iy * ox, -iy * oy])
    A = np.array(M, dtype=float)
    B = np.array(input_pts, dtype=float).reshape(8)
    return np.linalg.solve(A, B)

cover = Image.open(BASE).convert("RGBA")
W, H = cover.size
src_corners = [(0, 0), (CW, 0), (CW, CH), (0, CH)]
coeffs = perspective_coeffs(QUAD, src_corners)

panel_rgba = panel.convert("RGBA")
warped = panel_rgba.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC,
                               fillcolor=(0, 0, 0, 0))

# 93% opacity so it sits on the illustrated screen naturally
alpha = warped.split()[3].point(lambda a: int(a * 0.93))
warped.putalpha(alpha)
cover.alpha_composite(warped)
cover.convert("RGB").save(COVER)
print("wrote", COVER)
