"""Fetch daily prices for each S&P 500 addition event window.

For each (ticker, effective_date) we need:
  - 150 trading days BEFORE the event (estimation + event-window lead)
  - 40 trading days AFTER  the event (event-window tail)
We pull from Yahoo Finance via yfinance. Failures (delisted, ticker renamed,
no data) are recorded so the post can honestly report the drop count.

Run as a script. Writes one parquet per event under data/prices/.
"""

from __future__ import annotations

import time
import sys
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")  # noisy urllib3 OpenSSL warning on Apple Python

ROOT = Path(__file__).resolve().parent
EVENTS = ROOT / "data" / "wiki_changes_raw.csv"
PRICE_DIR = ROOT / "data" / "prices"
PRICE_DIR.mkdir(parents=True, exist_ok=True)
META = ROOT / "data" / "fetch_meta.csv"

START_YEAR = 2000
END_YEAR = 2022      # avoid events whose post-window isn't fully observable
LOOKBACK_DAYS = 220  # generous to cover non-trading days
LOOKAHEAD_DAYS = 65


def main() -> None:
    events = pd.read_csv(EVENTS, parse_dates=["date"])
    events = events.rename(columns={"date": "effective_date", "added_ticker": "ticker"})
    events = events[
        (events["effective_date"].dt.year >= START_YEAR)
        & (events["effective_date"].dt.year <= END_YEAR)
    ].reset_index(drop=True)

    # Pull the S&P 500 benchmark once for the full range
    bench_start = events["effective_date"].min() - pd.Timedelta(days=LOOKBACK_DAYS + 10)
    bench_end   = events["effective_date"].max() + pd.Timedelta(days=LOOKAHEAD_DAYS + 10)
    print(f"benchmark window: {bench_start.date()} -> {bench_end.date()}")
    bench = yf.download("^GSPC", start=bench_start, end=bench_end, auto_adjust=True,
                        progress=False)
    if bench.empty:
        sys.exit("Failed to fetch ^GSPC benchmark.")
    bench.columns = [c[0] if isinstance(c, tuple) else c for c in bench.columns]
    bench[["Close"]].to_parquet(ROOT / "data" / "sp500_close.parquet")
    print(f"saved benchmark: {len(bench):,} trading days")

    meta_rows = []
    for i, row in events.iterrows():
        ticker = str(row["ticker"]).strip()
        eff = row["effective_date"]
        out_path = PRICE_DIR / f"{ticker}_{eff.date().isoformat()}.parquet"
        if out_path.exists():
            meta_rows.append({"ticker": ticker, "effective_date": eff,
                              "status": "cached", "n_obs": -1})
            continue

        start = eff - pd.Timedelta(days=LOOKBACK_DAYS)
        end   = eff + pd.Timedelta(days=LOOKAHEAD_DAYS)
        try:
            df = yf.download(ticker, start=start, end=end, auto_adjust=True,
                             progress=False, threads=False)
        except Exception as e:
            meta_rows.append({"ticker": ticker, "effective_date": eff,
                              "status": f"error:{type(e).__name__}", "n_obs": 0})
            continue

        if df.empty:
            meta_rows.append({"ticker": ticker, "effective_date": eff,
                              "status": "empty", "n_obs": 0})
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df[["Close"]].to_parquet(out_path)
        meta_rows.append({"ticker": ticker, "effective_date": eff,
                          "status": "ok", "n_obs": len(df)})

        if (i + 1) % 25 == 0:
            print(f"  fetched {i+1}/{len(events)}")
            pd.DataFrame(meta_rows).to_csv(META, index=False)
        time.sleep(0.05)  # be polite to Yahoo

    meta = pd.DataFrame(meta_rows)
    meta.to_csv(META, index=False)
    print()
    print("done.")
    print(meta["status"].apply(lambda s: s.split(":")[0]).value_counts().to_string())


if __name__ == "__main__":
    main()
