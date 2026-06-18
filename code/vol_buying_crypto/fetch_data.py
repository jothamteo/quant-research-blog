"""Pull the inputs for the crypto vol-buying study.

  - Deribit DVOL (BTC implied-vol index) daily history, paged back as far as the
    public API allows.
  - BTC daily closes (Binance vision mirror, reachable where api.binance.com is
    geo-blocked) to compute realized volatility.

Saved as CSVs the analysis reads. Nothing here is editable by hand.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 vol-study/1.0"}
DERIBIT = "https://www.deribit.com/api/v2/public/"


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def fetch_dvol():
    """Page get_volatility_index_data backwards (API caps ~1000 rows/call)."""
    now = int(time.time() * 1000)
    day = 24 * 3600 * 1000
    rows = {}
    end = now
    for _ in range(8):  # up to ~8000 days if available
        start = end - 900 * day
        d = _get(
            f"{DERIBIT}get_volatility_index_data?currency=BTC"
            f"&start_timestamp={start}&end_timestamp={end}&resolution=1D"
        )
        data = d.get("result", {}).get("data", [])
        if not data:
            break
        for ts, o, h, l, c in data:
            rows[ts] = c
        oldest = min(r[0] for r in data)
        if oldest <= start + day:  # didn't fill the window -> reached the start
            end = oldest - day
        else:
            break
        time.sleep(0.25)
    items = sorted(rows.items())
    out = DATA / "dvol_btc.csv"
    with out.open("w") as f:
        f.write("date,dvol\n")
        for ts, c in items:
            ds = time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
            f.write(f"{ds},{c}\n")
    print(f"DVOL: {len(items)} days -> {items[0][0] and time.strftime('%Y-%m-%d', time.gmtime(items[0][0]/1000))} .. "
          f"{time.strftime('%Y-%m-%d', time.gmtime(items[-1][0]/1000))}")


def fetch_btc_daily():
    """BTC daily closes from the Binance vision mirror (works from SG)."""
    base = "https://data-api.binance.vision/api/v3/klines"
    out_rows = []
    end = int(time.time() * 1000)
    for _ in range(6):
        url = f"{base}?symbol=BTCUSDT&interval=1d&limit=1000&endTime={end}"
        kl = _get(url)
        if not kl:
            break
        for k in kl:
            out_rows.append((k[0], float(k[4])))  # openTime, close
        end = kl[0][0] - 1
        if len(kl) < 1000:
            break
        time.sleep(0.25)
    rows = sorted(set(out_rows))
    out = DATA / "btc_daily.csv"
    with out.open("w") as f:
        f.write("date,close\n")
        for ts, c in rows:
            ds = time.strftime("%Y-%m-%d", time.gmtime(ts / 1000))
            f.write(f"{ds},{c}\n")
    print(f"BTC daily: {len(rows)} days")


if __name__ == "__main__":
    fetch_dvol()
    fetch_btc_daily()
