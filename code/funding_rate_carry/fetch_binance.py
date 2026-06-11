"""Pull Binance USDT-margined BTC perp funding-rate history and spot daily closes.

Binance returns funding rates in pages of 1000 (~330 days at 3 fundings/day).
We paginate backwards from now until we have ~3 years.

Outputs:
  data/funding_btcusdt.csv   8-hourly funding rates with mark price
  data/spot_btcusdt.csv      1-day spot closes (used as the spot leg's PnL)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data"
OUT.mkdir(parents=True, exist_ok=True)

FUTURES = "https://fapi.binance.com/fapi/v1/fundingRate"
SPOT_KLINES = "https://api.binance.com/api/v3/klines"
SYMBOL = "BTCUSDT"


def fetch_funding(end_ms: int, days: int = 1100) -> pd.DataFrame:
    """Walk FORWARD from (end_ms - days) until we run out of data.

    Binance's funding endpoint returns the EARLIEST <= 1000 rates after
    startTime (oldest-first ordering), so we step startTime forward by
    the newest fundingTime returned on each page.
    """
    start_ms = end_ms - days * 24 * 3600 * 1000
    rows: list[dict] = []
    cursor = start_ms
    while True:
        params = {
            "symbol": SYMBOL,
            "startTime": cursor,
            "limit": 1000,
        }
        r = requests.get(FUTURES, params=params, timeout=30)
        r.raise_for_status()
        page = r.json()
        if not page:
            break
        rows.extend(page)
        newest = max(p["fundingTime"] for p in page)
        if newest >= end_ms or len(page) < 1000:
            break
        cursor = newest + 1
        time.sleep(0.10)
    df = pd.DataFrame(rows).drop_duplicates(subset=["fundingTime"]).sort_values("fundingTime")
    df["funding_time"] = pd.to_datetime(df["fundingTime"], unit="ms", utc=True)
    df["funding_rate"] = pd.to_numeric(df["fundingRate"], errors="coerce")
    df["mark_price"] = pd.to_numeric(df.get("markPrice", float("nan")), errors="coerce")
    df = df.dropna(subset=["funding_rate"]).copy()
    return df[["funding_time", "funding_rate", "mark_price"]].reset_index(drop=True)


def fetch_spot(end_ms: int, days: int = 1100) -> pd.DataFrame:
    """Walk forward through daily klines."""
    rows: list[list] = []
    start_ms = end_ms - days * 24 * 3600 * 1000
    cursor = start_ms
    while True:
        params = {
            "symbol": SYMBOL,
            "interval": "1d",
            "startTime": cursor,
            "limit": 1000,
        }
        r = requests.get(SPOT_KLINES, params=params, timeout=30)
        r.raise_for_status()
        page = r.json()
        if not page:
            break
        rows.extend(page)
        newest = max(row[0] for row in page)
        if newest >= end_ms or len(page) < 1000:
            break
        cursor = newest + 1
        time.sleep(0.10)
    # Klines: [open_time, open, high, low, close, volume, close_time, ...]
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ]).drop_duplicates(subset=["open_time"]).sort_values("open_time")
    df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.date
    df["close"] = df["close"].astype(float)
    return df[["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


def main() -> None:
    now_ms = int(time.time() * 1000)
    print("fetching funding…")
    fund = fetch_funding(now_ms, days=1100)
    fund.to_csv(OUT / "funding_btcusdt.csv", index=False)
    print(f"  {len(fund):,} funding observations  "
          f"({fund['funding_time'].min()} -> {fund['funding_time'].max()})")
    print(f"  mean: {fund['funding_rate'].mean()*1e4:.2f} bps per 8h   "
          f"std: {fund['funding_rate'].std()*1e4:.2f} bps")

    print()
    print("fetching spot daily…")
    spot = fetch_spot(now_ms, days=1100)
    spot.to_csv(OUT / "spot_btcusdt.csv", index=False)
    print(f"  {len(spot):,} daily bars  "
          f"({spot['date'].min()} -> {spot['date'].max()})")


if __name__ == "__main__":
    sys.exit(main())
