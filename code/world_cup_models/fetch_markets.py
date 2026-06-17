"""Fetch a live snapshot of World Cup market prices from Polymarket and Hyperliquid.

Two venues, two market types:
  - Polymarket  "World Cup Winner"  champion market (one YES/NO per team)
  - Polymarket  per-match moneyline (Home / Draw / Away) for a given match-day
  - Hyperliquid HIP-4 champion outcome markets (one YES/NO per team)

Hyperliquid has *no* per-match markets, so the per-match comparison is model-vs-Polymarket
only; the champion comparison is the full three-way.

NOTE on networking: Polymarket's gamma API is unreachable from some ISPs (incl. the
author's), so this script is designed to run from a host with clean egress (an EU VPS).
Hyperliquid is reachable anywhere. Output is a single timestamped JSON the analysis and the
website both read — never edited by hand.

Usage:  python fetch_markets.py --match-days 2026-06-17 2026-06-18
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GAMMA = "https://gamma-api.polymarket.com"
HL_INFO = "https://api.hyperliquid.xyz/info"
DATA = Path(__file__).resolve().parent / "data"


_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 wc-models/1.0"


def _get(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _post(url: str, body: dict, timeout: int = 25):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": _UA},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def fetch_pm_champion() -> list[dict]:
    """Polymarket 'World Cup Winner' event -> [{team, yes_price}]."""
    ev = _get(f"{GAMMA}/events?slug=world-cup-winner")[0]
    out = []
    for m in ev.get("markets", []):
        try:
            prices = json.loads(m.get("outcomePrices") or "[]")
        except json.JSONDecodeError:
            prices = []
        team = m.get("groupItemTitle") or m.get("question")
        if prices and team:
            out.append({"team": team, "yes_price": float(prices[0])})
    return out


def fetch_pm_matches(slugs: list[str]) -> list[dict]:
    """Polymarket per-match events -> [{title, slug, outcomes:[{name, price}]}]."""
    out = []
    for slug in slugs:
        try:
            data = _get(f"{GAMMA}/events?slug={slug}")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {slug}: {e}", file=sys.stderr)
            continue
        if not data:
            continue
        ev = data[0]
        # A 3-way match event holds three YES/NO markets, one per outcome
        # (Home win / Draw / Away win). The market's groupItemTitle names the leg,
        # and its YES price is that outcome's implied probability.
        legs = []
        for m in ev.get("markets", []):
            try:
                names = json.loads(m.get("outcomes") or "[]")
                prices = json.loads(m.get("outcomePrices") or "[]")
            except json.JSONDecodeError:
                continue
            label = m.get("groupItemTitle") or m.get("question")
            yes_price = None
            for n, p in zip(names, prices):
                if str(n).strip().lower() == "yes":
                    yes_price = float(p)
            if label and yes_price is not None:
                legs.append({"label": label, "prob": yes_price})
        out.append({"title": ev.get("title"), "slug": slug, "outcomes": legs})
        time.sleep(0.3)
    return out


def fetch_hl_champion() -> list[dict]:
    """Hyperliquid HIP-4 champion outcomes -> [{team, mid}] using the YES-side mid."""
    meta = _post(HL_INFO, {"type": "outcomeMeta"})
    wc = {
        o["outcome"]: o["name"]
        for o in meta["outcomes"]
        if "World Cup champion" in o.get("description", "")
    }
    mids = _post(HL_INFO, {"type": "allMids"})
    out = []
    for idx, name in wc.items():
        coin = "#" + str(10 * idx)  # encoding = 10*outcome + side; side 0 = YES
        if coin in mids:
            out.append({"team": name, "mid": float(mids[coin])})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-days", nargs="*", default=["2026-06-17", "2026-06-18"])
    args = ap.parse_args()

    # Polymarket match slugs follow fifwc-<home3>-<away3>-<date>; discover them from the
    # FIFA World Cup tag rather than guessing the abbreviations.
    print("Discovering Polymarket match slugs from the FIFA World Cup tag ...")
    match_slugs = []
    events = _get(f"{GAMMA}/events?closed=false&limit=200&tag_id=102232")
    for ev in events:
        slug = ev.get("slug") or ""
        if slug.startswith("fifwc-") and any(slug.endswith(d) for d in args.match_days):
            match_slugs.append(slug)
    print(f"  found {len(match_slugs)} match markets for {args.match_days}")

    snap = {
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "match_days": args.match_days,
        "pm_champion": fetch_pm_champion(),
        "pm_matches": fetch_pm_matches(match_slugs),
        "hl_champion": fetch_hl_champion(),
    }
    DATA.mkdir(parents=True, exist_ok=True)
    stamp = snap["fetched_at_utc"].replace(":", "").replace("-", "")[:15]
    path = DATA / f"market_snapshot_{stamp}.json"
    path.write_text(json.dumps(snap, indent=2))
    latest = DATA / "market_snapshot_latest.json"
    latest.write_text(json.dumps(snap, indent=2))
    print(
        f"saved {path.name}: "
        f"{len(snap['pm_champion'])} PM champ, "
        f"{len(snap['pm_matches'])} PM matches, "
        f"{len(snap['hl_champion'])} HL champ"
    )


if __name__ == "__main__":
    main()
