"""Pull resolved binary markets from Manifold Markets.

Manifold's /v0/markets endpoint paginates via the `before` cursor (the id of
the oldest market in the previous page). We fetch pages of 500 until we have
enough resolved BINARY markets, then write to data/resolved_markets.csv.

Limitations:
- This uses the LATEST snapshot probability on each market — i.e. the closing
  probability. A more honest test would use the probability at some fixed
  lead time (e.g. 7 days before resolution) for each market, which requires
  bet-history pulls. See `fetch_bets.py` for that step.
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

API = "https://api.manifold.markets/v0/markets"
PAGE = 500
TARGET = 5000  # resolved binary markets we want


def main() -> None:
    rows: list[dict] = []
    before: str | None = None
    n_pages = 0
    while True:
        params = {"limit": PAGE}
        if before is not None:
            params["before"] = before
        r = requests.get(API, params=params, timeout=30)
        r.raise_for_status()
        page = r.json()
        if not page:
            break
        n_pages += 1
        before = page[-1]["id"]
        for m in page:
            if m.get("outcomeType") != "BINARY":
                continue
            if not m.get("isResolved"):
                continue
            res = m.get("resolution")
            if res not in ("YES", "NO"):
                # MKT / CANCEL / etc. — don't include in calibration
                continue
            rows.append({
                "id": m["id"],
                "question": m.get("question", "")[:200],
                "resolution": res,
                "y_obs": 1 if res == "YES" else 0,
                "p_close": m.get("probability"),
                "close_time_ms": m.get("closeTime"),
                "resolution_time_ms": m.get("resolutionTime"),
                "created_time_ms": m.get("createdTime"),
                "volume": m.get("volume"),
                "n_bettors": m.get("uniqueBettorCount"),
            })
        if n_pages % 5 == 0:
            print(f"  pages={n_pages:3d}  resolved-binary so far: {len(rows):,}")
        if len(rows) >= TARGET:
            break
        time.sleep(0.10)   # be polite

    df = pd.DataFrame(rows)
    out_path = OUT / "resolved_markets.csv"
    df.to_csv(out_path, index=False)
    print()
    print(f"wrote {len(df):,} markets to {out_path.relative_to(ROOT)}")
    print(f"by resolution:")
    print(df["resolution"].value_counts().to_string())
    print()
    print("p_close (closing-time probability) distribution:")
    print(df["p_close"].describe().round(3).to_string())


if __name__ == "__main__":
    sys.exit(main())
