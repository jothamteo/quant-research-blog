# `funding_rate_carry/`

Reproducible BTCUSDT funding-rate carry backtest backing the blog post
**"Funding-rate carry in BTC perps: 7.4% a year, plus everything that
number leaves out"**.

## Run it

```bash
pip install -r requirements.txt
python fetch_binance.py    # ~2 min (paginated futures + spot APIs)
python backtest.py         # ~2 sec
```

## Inputs

- Binance USDⓈ-M futures funding-rate history for BTCUSDT
  (3,300 8-hour observations over 3 years)
- Binance spot daily klines for BTCUSDT (used for date alignment)

Both pulled from public APIs; no authentication required.

## Headline assumptions

- Strategy: short 1 BTC notional perp + long 1 BTC notional spot.
- Funding-only PnL — the spot and perp legs are assumed to offset
  exactly. This **ignores** basis variance, liquidation risk, and
  slippage. See the post's section §3 for the honest risk picture.
- One-time round-trip cost: 4 bps total (2 bps each side).

## Outputs

- `data/funding_btcusdt.csv` — 8-hourly funding rates
- `data/spot_btcusdt.csv` — daily spot OHLC (for time-axis alignment)
- `data/backtest_returns.csv` — daily aggregated PnL + cumulative
- `data/backtest_summary.json` — headline stats
- `charts/funding_cumulative.png` — cumulative funding capture
- `charts/funding_drawdown.png` — drawdown from running peak
- `charts/funding_distribution.png` — funding rate histogram

MIT license. Binance data is subject to their public API terms.
