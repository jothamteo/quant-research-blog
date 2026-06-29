"""Pull the inputs for the WebCryptoAgent reality-check.

WebCryptoAgent (arXiv:2601.04687) is evaluated on BTCUSDT and ETHUSDT over
2025-01-05 → 2026-01-05 on 15-minute bars, with ~122 strategic decision points.
To reconstruct the *benchmark* that evaluation has to beat — and to quantify how
much of any result is luck at N=122 — we only need the price path the agent
traded against. We pull hourly closes for both assets over the exact window.

Source: Binance public klines (api.binance.com; falls back to the
data.binance.vision mirror where the main host is geo-blocked). Saved as CSVs the
analysis reads. Nothing here is editable by hand.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 webcryptoagent-study/1.0"}

# The paper's evaluation window, to the day.
START = dt.datetime(2025, 1, 5, tzinfo=dt.timezone.utc)
END = dt.datetime(2026, 1, 5, tzinfo=dt.timezone.utc)
INTERVAL = "1h"
HOSTS = ["https://api.binance.com", "https://data-api.binance.vision"]


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def klines(symbol: str):
    """Page Binance klines (1000-row cap) across the window; return [(ts_ms, close)]."""
    start_ms = int(START.timestamp() * 1000)
    end_ms = int(END.timestamp() * 1000)
    out, cur = [], start_ms
    while cur < end_ms:
        path = (f"/api/v3/klines?symbol={symbol}&interval={INTERVAL}"
                f"&startTime={cur}&endTime={end_ms}&limit=1000")
        data = None
        for host in HOSTS:
            try:
                data = _get(host + path)
                break
            except Exception:
                continue
        if not data:
            break
        out += [(int(k[0]), float(k[4])) for k in data]
        cur = data[-1][0] + 1
        if len(data) < 1000:
            break
    return out


def save(symbol: str, fname: str):
    rows = klines(symbol)
    with open(DATA / fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "close"])
        for ts, close in rows:
            iso = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).isoformat()
            w.writerow([iso, close])
    print(f"{symbol}: {len(rows)} hourly bars -> {fname}")


if __name__ == "__main__":
    save("BTCUSDT", "btc_1h.csv")
    save("ETHUSDT", "eth_1h.csv")
