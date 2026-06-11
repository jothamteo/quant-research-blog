"""Brown-Warner market-model event study.

For each (ticker, effective_date) with sufficient price history:
  1. Compute daily log returns for both the stock and S&P 500.
  2. Estimation window: trading days [-120, -20] relative to event.
  3. Fit OLS: r_stock = alpha + beta * r_market + e
  4. Event window: trading days [-10, +20].
     Abnormal return AR_t = r_stock_t - (alpha_hat + beta_hat * r_market_t).
     Cumulative abnormal return CAR_{[a,b]} = sum_{t=a..b} AR_t.
  5. Standardise CAR_{[a,b]} by sqrt((b-a+1)) * sigma_hat (Brown-Warner SCAR_i).

Outputs a CSV with one row per event:
  ticker, effective_date, year, n_obs_est, sigma_hat, beta_hat, alpha_hat,
  ar_t-5, ..., ar_t+10, car_{-5,-1}, car_{0,1}, car_{-5,0}, car_{0,5},
  car_{0,10}, car_{0,20}, scar_{-5,0}, scar_{0,5}.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
PRICE_DIR = ROOT / "data" / "prices"
BENCH = ROOT / "data" / "sp500_close.parquet"

EST_START, EST_END = -120, -21    # trading-day offsets relative to event
EVT_START, EVT_END = -10, 20

CAR_WINDOWS = {
    "car_-5_-1": (-5, -1),    # pre-event run-up
    "car_0_1":   ( 0,  1),    # immediate
    "car_-5_0":  (-5,  0),    # announcement-to-effective approx
    "car_0_5":   ( 0,  5),    # first-week
    "car_0_10":  ( 0, 10),
    "car_0_20":  ( 0, 20),
}


def _to_trading_index(df: pd.DataFrame, event_date: pd.Timestamp) -> pd.DataFrame:
    """Reindex prices to trading-day offsets relative to event_date.

    Finds the closest trading day on/after the event, then labels offsets
    -N, -N+1, ..., 0, 1, ..., M for the available rows.
    """
    df = df.sort_index().copy()
    # Find first trading day >= event_date
    cand = df.index.searchsorted(event_date)
    if cand >= len(df):
        return pd.DataFrame()
    t0 = df.index[cand]
    offsets = np.arange(len(df)) - cand
    df = df.assign(offset=offsets).reset_index().rename(columns={"index": "date"})
    df = df.set_index("offset")
    return df


def _event_returns(ticker_path: Path, bench: pd.DataFrame, event_date: pd.Timestamp):
    """Returns (stock_ret, mkt_ret) Series indexed by trading-day offset."""
    px = pd.read_parquet(ticker_path)
    px = px.rename(columns={"Close": "px"})
    # Align with bench on dates
    aligned = px.join(bench.rename(columns={"Close": "mkt"}), how="inner")
    if len(aligned) < 80:
        return None, None
    aligned["r_stock"] = np.log(aligned["px"] / aligned["px"].shift(1))
    aligned["r_mkt"]   = np.log(aligned["mkt"] / aligned["mkt"].shift(1))
    aligned = aligned.dropna()
    aligned = _to_trading_index(aligned, event_date)
    return aligned["r_stock"], aligned["r_mkt"]


def run_one(ticker_path: Path, bench: pd.DataFrame, event_date: pd.Timestamp):
    r_stock, r_mkt = _event_returns(ticker_path, bench, event_date)
    if r_stock is None or r_mkt is None:
        return None

    est = (r_stock.index >= EST_START) & (r_stock.index <= EST_END)
    if est.sum() < 60:
        return None
    rs_est = r_stock[est]
    rm_est = r_mkt[est]

    # OLS market-model regression
    X = np.column_stack([np.ones(len(rm_est)), rm_est.values])
    y = rs_est.values
    beta_hat, *_ = np.linalg.lstsq(X, y, rcond=None)
    alpha, beta = float(beta_hat[0]), float(beta_hat[1])
    resid = y - X @ beta_hat
    sigma = float(resid.std(ddof=2))   # 2 estimated params

    evt = (r_stock.index >= EVT_START) & (r_stock.index <= EVT_END)
    rs_evt = r_stock[evt]
    rm_evt = r_mkt[evt]
    ar = rs_evt - (alpha + beta * rm_evt)

    row = {
        "n_obs_est": int(est.sum()),
        "alpha": alpha, "beta": beta, "sigma_resid": sigma,
    }
    for t in range(EVT_START, EVT_END + 1):
        row[f"ar_{t}"] = float(ar.loc[t]) if t in ar.index else np.nan
    for name, (a, b) in CAR_WINDOWS.items():
        if a in ar.index and b in ar.index:
            row[name] = float(ar.loc[a:b].sum())
        else:
            row[name] = np.nan
    return row


def main() -> None:
    if not BENCH.exists():
        sys.exit("Run fetch_prices.py first to produce sp500_close.parquet.")
    bench = pd.read_parquet(BENCH)

    meta = pd.read_csv(ROOT / "data" / "fetch_meta.csv", parse_dates=["effective_date"])
    rows = []
    skipped = 0
    for _, m in meta.iterrows():
        if str(m.get("status", "")).split(":")[0] != "ok":
            continue
        path = PRICE_DIR / f"{m['ticker']}_{m['effective_date'].date().isoformat()}.parquet"
        if not path.exists():
            continue
        res = run_one(path, bench, pd.to_datetime(m["effective_date"]))
        if res is None:
            skipped += 1
            continue
        res.update({
            "ticker": m["ticker"],
            "effective_date": pd.to_datetime(m["effective_date"]),
            "year": pd.to_datetime(m["effective_date"]).year,
        })
        rows.append(res)

    out = pd.DataFrame(rows)
    out_path = ROOT / "data" / "event_study_results.csv"
    out.to_csv(out_path, index=False)
    print(f"wrote {len(out):,} events to {out_path.relative_to(ROOT)}")
    print(f"skipped {skipped} (insufficient window)")
    if len(out):
        print()
        print("by-decade summary (mean CAR over the [0, 5] window):")
        out["decade"] = (out["year"] // 10) * 10
        print(out.groupby("decade")["car_0_5"].agg(["count", "mean", "std"]).round(4))


if __name__ == "__main__":
    main()
