"""Fetch S&P 500 historical add/drop events from Wikipedia.

Wikipedia maintains a 'Selected changes to the list of S&P 500 Components'
table in https://en.wikipedia.org/wiki/List_of_S%26P_500_companies. We parse
it and emit a CSV of (effective_date, added_ticker, removed_ticker, reason).
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(parents=True, exist_ok=True)

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
UA = {"User-Agent": "quant-research-blog/0.1 (educational; +https://github.com/jothamteo)"}


def fetch() -> pd.DataFrame:
    r = requests.get(URL, headers=UA, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    # The 'changes' table is the second main wikitable; it has a multi-row header
    # with 'Date', 'Added' (Ticker, Security), 'Removed' (Ticker, Security), 'Reason'.
    changes = tables[1]
    # Flatten the MultiIndex columns
    changes.columns = ["_".join([str(c) for c in col]).strip("_") for col in changes.columns]
    return changes


def normalise(changes: pd.DataFrame) -> pd.DataFrame:
    """Pick the columns we need and parse dates."""
    # Try several historical column names — Wikipedia has churned this schema
    candidates = {
        "date": ["Effective Date_Effective Date", "Date_Date", "Date"],
        "added_ticker": ["Added_Ticker", "Added", "Ticker_Added"],
        "removed_ticker": ["Removed_Ticker", "Removed", "Ticker_Removed"],
        "reason": ["Reason_Reason", "Reason"],
    }

    cols = {}
    for key, options in candidates.items():
        for opt in options:
            if opt in changes.columns:
                cols[key] = opt
                break
        else:
            raise RuntimeError(
                f"Could not find column for {key}. Have: {list(changes.columns)}"
            )

    out = changes.rename(columns={v: k for k, v in cols.items()})[
        list(cols.keys())
    ].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date", "added_ticker"]).reset_index(drop=True)
    # Drop placeholder rows where the ticker looks empty
    out = out[out["added_ticker"].astype(str).str.match(r"^[A-Z\.\-]{1,6}$")]
    return out.reset_index(drop=True)


def main() -> None:
    raw = fetch()
    changes = normalise(raw)
    out_path = OUT / "wiki_changes_raw.csv"
    changes.to_csv(out_path, index=False)
    print(f"wrote {len(changes):,} rows to {out_path.relative_to(Path(__file__).resolve().parent)}")
    print()
    print("By year (counts of additions):")
    print(changes.assign(year=changes["date"].dt.year).groupby("year").size().tail(20).to_string())


if __name__ == "__main__":
    sys.exit(main())
