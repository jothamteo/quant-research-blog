"""Does buying cheap vol pay on BTC — and can you capture it after costs?

Signal (the method): go long vol when implied vol is historically cheap —
IV-rank below 35 on a trailing one-year window. The economic precondition for a
long-vol trade to make money is that *subsequent realized vol exceeds the implied
vol you paid* (a delta-hedged straddle's P&L is ~ proportional to RV^2 - IV^2).
So we test, on 5 years of Deribit DVOL: when vol is cheap, does it mean-revert up,
and does forward realized beat the implied you'd have paid?

Then the reality check the method lives or dies on: slippage. We snapshot live
Deribit BTC option spreads across maturities and derive.xyz HYPE option books.
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHARTS = HERE.parents[1] / "static" / "charts" / "vol-buying-crypto"
UA = {"User-Agent": "Mozilla/5.0 vol-study/1.0"}
DERIBIT = "https://www.deribit.com/api/v2/public/"
LYRA = "https://api.lyra.finance"

IVRANK_WIN = 365
RV_WIN = 30
SIGNAL = 35.0
ANN = np.sqrt(365)


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={**UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load():
    dv = pd.read_csv(DATA / "dvol_btc.csv", parse_dates=["date"]).set_index("date")
    px = pd.read_csv(DATA / "btc_daily.csv", parse_dates=["date"]).set_index("date")
    df = dv.join(px, how="inner")
    df["ret"] = np.log(df.close).diff()
    # realized vol (annualized), trailing and forward 30d
    df["rv"] = df.ret.rolling(RV_WIN).std() * ANN * 100
    df["rv_fwd"] = df.ret[::-1].rolling(RV_WIN).std()[::-1] * ANN * 100
    df["rv_fwd"] = df["rv_fwd"].shift(-1)  # strictly forward
    # IV rank on trailing 1y of DVOL
    lo = df.dvol.rolling(IVRANK_WIN).min()
    hi = df.dvol.rolling(IVRANK_WIN).max()
    df["ivrank"] = 100 * (df.dvol - lo) / (hi - lo)
    # forward 30d change in DVOL (mean-reversion test)
    df["dvol_fwd"] = df.dvol.shift(-RV_WIN)
    df["dvol_chg_fwd"] = df.dvol_fwd - df.dvol
    return df


def regime_table(df):
    d = df.dropna(subset=["ivrank", "rv_fwd", "dvol_chg_fwd"]).copy()
    d["edge"] = d.rv_fwd - d.dvol  # forward realized minus implied paid
    bins = [0, 20, 35, 50, 65, 80, 100]
    d["bucket"] = pd.cut(d.ivrank, bins, include_lowest=True)
    g = d.groupby("bucket", observed=True).agg(
        n=("edge", "size"),
        mean_edge=("edge", "mean"),
        pct_edge_pos=("edge", lambda x: (x > 0).mean() * 100),
        mean_dvol_chg=("dvol_chg_fwd", "mean"),
    ).reset_index()
    cheap = d[d.ivrank < SIGNAL]
    rest = d[d.ivrank >= SIGNAL]
    summary = {
        "n_total": int(len(d)),
        "n_cheap": int(len(cheap)),
        "cheap_frac": round(len(cheap) / len(d), 3),
        "cheap_mean_edge": round(cheap.edge.mean(), 2),
        "rest_mean_edge": round(rest.edge.mean(), 2),
        "cheap_pct_edge_pos": round((cheap.edge > 0).mean() * 100, 1),
        "rest_pct_edge_pos": round((rest.edge > 0).mean() * 100, 1),
        "cheap_mean_dvol_chg": round(cheap.dvol_chg_fwd.mean(), 2),
        "rest_mean_dvol_chg": round(rest.dvol_chg_fwd.mean(), 2),
        "current_ivrank": round(df.ivrank.dropna().iloc[-1], 1),
        "current_dvol": round(df.dvol.iloc[-1], 1),
    }
    return g, summary, d


def deribit_slippage():
    """ATM call spread/premium across maturities."""
    inst = _get(DERIBIT + "get_instruments?currency=BTC&kind=option&expired=false")["result"]
    idx = _get(DERIBIT + "get_index_price?index_name=btc_usd")["result"]["index_price"]
    now = time.time() * 1000
    by_exp = {}
    for i in inst:
        by_exp.setdefault(i["expiration_timestamp"], []).append(i)
    rows = []
    for exp in sorted(by_exp):
        dte = (exp - now) / (24 * 3600 * 1000)
        if dte < 0.3:
            continue
        calls = [i for i in by_exp[exp] if i["option_type"] == "call"]
        atm = min(calls, key=lambda i: abs(i["strike"] - idx))
        t = _get(DERIBIT + f"ticker?instrument_name={atm['instrument_name']}")["result"]
        bid, ask, mark = t.get("best_bid_price"), t.get("best_ask_price"), t.get("mark_price")
        if bid and ask and mark:
            spr_usd = (ask - bid) * idx
            prem_usd = mark * idx
            rows.append({"dte": round(dte, 1), "instrument": atm["instrument_name"],
                         "spread_usd": round(spr_usd, 1), "premium_usd": round(prem_usd, 1),
                         "spread_pct_prem": round(spr_usd / prem_usd * 100, 1)})
        time.sleep(0.1)
        if len(rows) >= 8:
            break
    return {"btc_index": round(idx), "rows": rows}


def derive_hype_liquidity():
    """How many HYPE option strikes actually carry a two-sided quote, by expiry."""
    r = _post(LYRA + "/public/get_instruments",
              {"currency": "HYPE", "instrument_type": "option", "expired": False})["result"]
    by_exp = {}
    for i in r:
        by_exp.setdefault(i["instrument_name"].split("-")[1], []).append(i["instrument_name"])
    out = []
    for exp in sorted(by_exp)[:3]:
        names = by_exp[exp]
        two_sided = 0
        for n in names[:40]:
            t = _post(LYRA + "/public/get_ticker", {"instrument_name": n}).get("result", {})
            b, a = t.get("best_bid_price"), t.get("best_ask_price")
            if b and a and float(b) > 0 and float(a) > 0:
                two_sided += 1
        out.append({"expiry": exp, "checked": min(len(names), 40), "two_sided_quotes": two_sided})
    return {"total_hype_options": len(r), "by_expiry": out}


def make_charts(df, regime, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    CHARTS.mkdir(parents=True, exist_ok=True)
    BL, OR, GR, RED = "#1f77b4", "#e76f51", "#2a9d8f", "#d62728"

    # 1) DVOL history with cheap-vol regime shaded
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(df.index, df.dvol, color=BL, lw=1.1)
    cheap = df.ivrank < SIGNAL
    ax.fill_between(df.index, df.dvol.min(), df.dvol.max(), where=cheap.fillna(False),
                    color=GR, alpha=0.15, label="IV-rank < 35 (vol cheap → buy signal)")
    ax.scatter([df.index[-1]], [df.dvol.iloc[-1]], color=RED, zorder=5,
               label=f"today: DVOL {summary['current_dvol']}, IV-rank {summary['current_ivrank']}%")
    ax.set_ylabel("DVOL (BTC 30d implied vol, %)")
    ax.set_title("BTC implied vol and the 'cheap vol' regime (Deribit DVOL, 2021–2026)")
    ax.legend(loc="upper right", fontsize=9); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "dvol_regime.png", dpi=140); plt.close(fig)

    # 2) the core result: forward (realized - implied) by IV-rank bucket
    labels = [str(b) for b in regime.bucket]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [GR if regime.mean_edge.iloc[i] > 0 else OR for i in range(len(labels))]
    ax.bar(x, regime.mean_edge, color=colors)
    ax.axhline(0, color="#444", lw=0.8)
    for i, v in enumerate(regime.mean_edge):
        ax.text(i, v + (0.4 if v >= 0 else -0.9), f"{v:+.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlabel("IV-rank bucket (left = vol historically cheap)")
    ax.set_ylabel("forward 30d realized − implied paid (vol pts)")
    ax.set_title("When BTC vol is cheap, realized tends to beat implied\n"
                 "(positive = a long-vol trade profits gross of costs)")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "edge_by_ivrank.png", dpi=140); plt.close(fig)

    # 3) the actual edge: forward change in DVOL by IV-rank bucket (mean reversion)
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [GR if regime.mean_dvol_chg.iloc[i] > 0 else OR for i in range(len(labels))]
    ax.bar(x, regime.mean_dvol_chg, color=colors)
    ax.axhline(0, color="#444", lw=0.8)
    for i, v in enumerate(regime.mean_dvol_chg):
        ax.text(i, v + (0.3 if v >= 0 else -0.8), f"{v:+.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
    ax.set_xlabel("IV-rank bucket (left = vol historically cheap)")
    ax.set_ylabel("forward 30d change in DVOL (vol pts)")
    ax.set_title("Vol mean-reverts: cheap vol drifts UP, expensive vol drifts DOWN\n"
                 "(this is the tailwind a long-vega 'buy cheap, sell the bounce' trade harvests)")
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "meanrev_by_ivrank.png", dpi=140); plt.close(fig)

    # 4) slippage curve: spread/premium vs DTE (built in main via results)
    print(f"charts -> {CHARTS}")


def make_slippage_chart(slip):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BL, GR = "#1f77b4", "#2a9d8f"
    rows = slip["rows"]
    dtes = [r["dte"] for r in rows]
    pct = [r["spread_pct_prem"] for r in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(dtes, pct, "-o", color=BL, label="BTC ATM (Deribit), live")
    ax.axhspan(1, 3, color=GR, alpha=0.15, label="Sam's survivors (SPY/IWM/TLT): ~1–3%")
    ax.set_xlabel("days to expiry"); ax.set_ylabel("round-trip spread / premium (%)")
    ax.set_title("Can you afford to trade it? BTC option slippage by maturity\n"
                 "(derive.xyz HYPE: no two-sided quotes at all — off the chart)")
    ax.legend(); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "slippage_curve.png", dpi=140); plt.close(fig)


def main():
    df = load()
    regime, summary, _ = regime_table(df)
    print("=== Regime table (by IV-rank bucket) ===")
    print(regime.to_string(index=False))
    print("\n=== Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("\nFetching live slippage ...")
    slip = deribit_slippage()
    print("Deribit ATM spread/premium by DTE:")
    for r in slip["rows"]:
        print(f"  {r['dte']:>5}d  {r['instrument']:<22} spread ${r['spread_usd']:>6} "
              f"prem ${r['premium_usd']:>7}  = {r['spread_pct_prem']}%")
    hype = derive_hype_liquidity()
    print(f"\nderive HYPE: {hype['total_hype_options']} options; two-sided quotes by expiry:")
    for e in hype["by_expiry"]:
        print(f"  {e['expiry']}: {e['two_sided_quotes']}/{e['checked']}")

    results = {
        "regime": regime.assign(bucket=regime.bucket.astype(str)).to_dict("records"),
        "summary": summary, "deribit_slippage": slip, "derive_hype": hype,
        "params": {"ivrank_window": IVRANK_WIN, "rv_window": RV_WIN, "signal": SIGNAL},
    }
    (DATA / "results.json").write_text(json.dumps(results, indent=2, default=str))
    make_charts(df, regime, summary)
    make_slippage_chart(slip)
    print(f"\nresults -> {DATA/'results.json'}")


if __name__ == "__main__":
    main()
