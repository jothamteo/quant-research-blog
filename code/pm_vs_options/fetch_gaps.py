"""Match Polymarket BTC threshold digitals to the option-implied binary from
Deribit, live. Runs on a host with clean egress to both (the EU VPS).

For each 'Bitcoin above ___ on June D' Polymarket event, and the Deribit option
expiry on the same calendar day, we:
  - read each strike's Polymarket Yes price;
  - build the risk-neutral binary P(BTC > K) from Deribit calls as the digital
    value  P(S_T > K) = -dC/dK  (finite differences across the strike grid;
    undiscounted, r~=0 over days);
  - record the gap = Polymarket Yes - Deribit-implied probability.

Output: rows.json with (date, dte_days, strike, spot, pm_yes, opt_prob, gap_pp).
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime, timezone

import numpy as np

UA = {"User-Agent": "Mozilla/5.0 pm-opt/1.0"}
GAMMA = "https://gamma-api.polymarket.com"
DERIBIT = "https://www.deribit.com/api/v2/public/"
DATES = [22, 23, 24, 25, 26]  # June 2026 daily expiries present on both venues


def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))


def pm_event(day):
    d = get(f"{GAMMA}/events?slug=bitcoin-above-on-june-{day}-2026")
    if not d:
        return None, {}
    e = d[0]
    end = e.get("endDate")
    out = {}
    for m in e.get("markets", []):
        lab = m.get("groupItemTitle") or ""
        k = re.sub(r"[,$\s]", "", lab)
        try:
            pr = json.loads(m.get("outcomePrices") or "[]")
        except json.JSONDecodeError:
            pr = []
        if pr and re.match(r"^\d+$", k):
            out[int(k)] = float(pr[0])
    return end, out


def deribit_digitals(day):
    idx = get(DERIBIT + "get_index_price?index_name=btc_usd")["result"]["index_price"]
    inst = get(DERIBIT + "get_instruments?currency=BTC&kind=option&expired=false")["result"]
    tok = f"{day}JUN26"
    calls = sorted([i for i in inst if i["option_type"] == "call"
                    and i["instrument_name"].split("-")[1] == tok],
                   key=lambda i: i["strike"])
    Ks, Cs = [], []
    for i in calls:
        t = get(DERIBIT + f"ticker?instrument_name={i['instrument_name']}")["result"]
        m = t.get("mark_price")
        if m is not None:
            Ks.append(i["strike"]); Cs.append(m * idx)
        time.sleep(0.03)
    Ks, Cs = np.array(Ks, float), np.array(Cs, float)
    dig = np.clip(-np.gradient(Cs, Ks), 0, 1) if len(Ks) > 2 else None
    return idx, Ks, dig


def main():
    now = datetime.now(timezone.utc)
    rows = []
    for day in DATES:
        end, pm = pm_event(day)
        if not pm:
            print(f"June {day}: no PM event"); continue
        idx, Ks, dig = deribit_digitals(day)
        if dig is None:
            print(f"June {day}: no Deribit expiry"); continue
        exp = datetime(2026, 6, day, 8, 0, tzinfo=timezone.utc)  # Deribit 08:00Z
        dte = (exp - now).total_seconds() / 86400
        for K in sorted(pm):
            if K < Ks.min() or K > Ks.max():
                continue
            opt = float(np.interp(K, Ks, dig))
            rows.append({"date": f"2026-06-{day:02d}", "dte_days": round(dte, 2),
                         "strike": K, "spot": round(idx), "pm_yes": pm[K],
                         "opt_prob": round(opt, 4), "gap_pp": round((pm[K] - opt) * 100, 2)})
        print(f"June {day}: {len([r for r in rows if r['date'].endswith(f'{day:02d}')])} strikes matched")
    out = {"fetched_at_utc": now.isoformat(), "rows": rows}
    with open("rows.json", "w") as f:
        json.dump(out, f, indent=2)
    gaps = [r["gap_pp"] for r in rows]
    print(f"\nTOTAL {len(rows)} obs | mean gap {np.mean(gaps):+.2f}pp | "
          f"mean|gap| {np.mean(np.abs(gaps)):.2f}pp")


if __name__ == "__main__":
    main()
