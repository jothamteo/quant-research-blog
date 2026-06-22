"""Does looking beyond past returns improve a volatility forecast?

GARCH forecasts tomorrow's variance from yesterday's squared return and its own
past variance — the 'resume' (price history alone). We test whether adding
'interview' signals — the VIX and a realized-volatility measure — genuinely
improves out-of-sample forecasts, and which covariate earns its keep. This is the
economically interesting core of the RECH-X paper (arXiv: Nguyen, Nguyen & Tran),
reproduced with transparent, hand-rolled models — no RNN, no Bayesian SMC.

Models (all forecast the daily variance sigma^2_t using info up to t-1):
  GARCH(1,1):  s2 = w + a*r2_{t-1} + b*s2_{t-1}
  GARCH-X:     + g * X_{t-1}        with X = VIX-implied daily variance, or realized var
  HAR-RV:      Corsi (1d/1w/1m) regression on log realized variance
Scored out-of-sample by QLIKE against a Garman-Klass realized-variance proxy.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CHARTS = HERE.parents[1] / "static" / "charts" / "garch-covariates"
TRAIN_END = "2017-12-31"


def load():
    import yfinance as yf
    g = yf.download("^GSPC ^VIX", start="2004-01-01", auto_adjust=False, progress=False)
    df = pd.DataFrame(index=g.index)
    o, h, l, c = (g[k]["^GSPC"] for k in ["Open", "High", "Low", "Close"])
    df["ret"] = np.log(c).diff()
    # Garman-Klass daily variance (a low-noise realized-variance proxy from OHLC)
    df["gk"] = 0.5 * np.log(h / l) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2
    df["gk"] = df["gk"].clip(lower=1e-8)
    df["vix_var"] = (g["Close"]["^VIX"] / 100.0) ** 2 / 252.0  # VIX -> daily variance
    df = df.dropna()
    DATA.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA / "spx_vix.csv")
    return df


def garch_filter(params, r2, x=None):
    """Recursively build the conditional-variance path."""
    if x is None:
        w, a, b = params; g = 0.0; x = np.zeros_like(r2)
    else:
        w, a, b, g = params
    n = len(r2); s2 = np.empty(n); s2[0] = r2.mean()
    for t in range(1, n):
        s2[t] = w + a * r2[t - 1] + b * s2[t - 1] + g * x[t - 1]
        if s2[t] <= 0:
            s2[t] = 1e-10
    return s2


def fit_garch(r, x=None):
    r2 = r ** 2
    has_x = x is not None

    def nll(p):
        s2 = garch_filter(p, r2, x if has_x else None)
        return 0.5 * np.sum(np.log(s2) + r2 / s2)

    v = r2.mean()
    if has_x:
        p0 = [v * 0.1, 0.08, 0.88, 0.01]
        bnds = [(1e-12, None), (0, 1), (0, 1), (0, None)]
    else:
        p0 = [v * 0.1, 0.08, 0.90]
        bnds = [(1e-12, None), (0, 1), (0, 1)]
    res = minimize(nll, p0, method="L-BFGS-B", bounds=bnds)
    return res.x


def qlike(s2_pred, rv):
    z = rv / s2_pred
    return np.mean(z - np.log(z) - 1)


def fit_har(logrv_train, idx_train):
    """Corsi HAR on log realized variance: 1d, 1w(5), 1m(22) averages."""
    def feats(series):
        d = series.shift(1)
        w = series.rolling(5).mean().shift(1)
        m = series.rolling(22).mean().shift(1)
        return pd.concat([d, w, m], axis=1)
    X = feats(logrv_train); X.columns = ["d", "w", "m"]
    XY = pd.concat([X, logrv_train.rename("y")], axis=1).dropna()
    A = np.c_[np.ones(len(XY)), XY[["d", "w", "m"]].to_numpy()]
    coef, *_ = np.linalg.lstsq(A, XY["y"].to_numpy(), rcond=None)
    return coef


def main():
    df = load()
    r = df["ret"].to_numpy()
    gk = df["gk"].to_numpy()
    vixv = df["vix_var"].to_numpy()
    dates = df.index
    test_mask = dates > TRAIN_END
    tr = ~test_mask
    print(f"{len(df)} days; train {tr.sum()} (≤{TRAIN_END}), test {test_mask.sum()}")

    models = {}
    # GARCH(1,1)
    p = fit_garch(r[tr]); s2 = garch_filter(p, r ** 2); models["GARCH"] = (p, s2)
    # GARCH-X(VIX)
    pv = fit_garch(r[tr], vixv[tr]); s2v = garch_filter(pv, r ** 2, vixv); models["GARCH-X (VIX)"] = (pv, s2v)
    # GARCH-X(RV)
    pr = fit_garch(r[tr], gk[tr]); s2r = garch_filter(pr, r ** 2, gk); models["GARCH-X (realized vol)"] = (pr, s2r)

    # HAR-RV on log GK
    logrv = pd.Series(np.log(gk), index=dates)
    coef = fit_har(logrv[tr], dates[tr])
    d = logrv.shift(1); w = logrv.rolling(5).mean().shift(1); m = logrv.rolling(22).mean().shift(1)
    har_log = coef[0] + coef[1] * d + coef[2] * w + coef[3] * m
    har_s2 = np.exp(har_log.to_numpy())

    # OOS QLIKE vs GK
    rows = {}
    for name, (_, s2m) in models.items():
        rows[name] = qlike(s2m[test_mask], gk[test_mask])
    valid = test_mask & np.isfinite(har_s2)
    rows["HAR-RV"] = qlike(har_s2[valid], gk[valid])

    base = rows["GARCH"]
    summary = {"train_end": TRAIN_END, "n_test": int(test_mask.sum()),
               "qlike": {k: round(float(v), 4) for k, v in rows.items()},
               "improvement_vs_garch_pct": {k: round(float((base - v) / base * 100), 1)
                                            for k, v in rows.items()},
               "garchx_vix_gamma": round(float(pv[3]), 6),
               "garchx_rv_gamma": round(float(pr[3]), 6)}
    print(json.dumps(summary, indent=2))
    (DATA / "results.json").write_text(json.dumps(summary, indent=2))
    _charts(df, models, har_s2, test_mask, rows, summary)


def _charts(df, models, har_s2, test_mask, rows, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    CHARTS.mkdir(parents=True, exist_ok=True)
    BL, OR, GR, GY = "#1f77b4", "#e76f51", "#2a9d8f", "#888"
    ann = np.sqrt(252) * 100  # daily var -> annualized vol %

    dates = df.index
    gk = df["gk"].to_numpy()
    # 1) realized vol vs two forecasts over a recent slice
    sl = (dates >= "2024-06-01")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(dates[sl], np.sqrt(gk[sl]) * ann, color=GY, lw=1, label="realized vol (Garman-Klass)")
    ax.plot(dates[sl], np.sqrt(models["GARCH"][1][sl]) * ann, color=BL, lw=1.4, label="GARCH forecast")
    ax.plot(dates[sl], np.sqrt(models["GARCH-X (VIX)"][1][sl]) * ann, color=OR, lw=1.4, label="GARCH-X (VIX) forecast")
    ax.set_ylabel("annualized vol (%)"); ax.set_title("S&P 500 volatility: realized vs forecasts (out-of-sample)")
    ax.legend(fontsize=9); ax.grid(alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "vol_forecasts.png", dpi=140); plt.close(fig)

    # 2) OOS QLIKE bar (lower = better) + improvement labels
    names = ["GARCH", "GARCH-X (VIX)", "GARCH-X (realized vol)", "HAR-RV"]
    vals = [rows[n] for n in names]
    imp = summary["improvement_vs_garch_pct"]
    fig, ax = plt.subplots(figsize=(9, 5))
    cols = [GY] + [GR if rows[n] < rows["GARCH"] else OR for n in names[1:]]
    ax.bar(range(len(names)), vals, color=cols)
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, fontsize=9, rotation=12)
    ax.set_ylabel("out-of-sample QLIKE  (lower = better)")
    ax.set_title("Do extra signals improve the forecast?\nS&P 500, out-of-sample 2018–2026")
    for i, n in enumerate(names):
        if n != "GARCH":
            ax.text(i, vals[i], f"{imp[n]:+.1f}%", ha="center", va="bottom", fontsize=9)
    lo = min(vals); ax.set_ylim(lo * 0.97, max(vals) * 1.01)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout(); fig.savefig(CHARTS / "qlike_bars.png", dpi=140); plt.close(fig)
    print(f"charts -> {CHARTS}")


if __name__ == "__main__":
    main()
