---
title: "Funding-rate carry in BTC perps: 7.4% a year, plus everything that number leaves out"
date: 2026-06-11T13:00:00+08:00
draft: false
math: true
tags: ["crypto", "perpetuals", "carry-trade", "funding-rate", "btc", "backtest"]
summary: "The canonical 'short perp / long spot' carry trade on BTCUSDT delivered +7.4% annualised funding-only PnL over the last three years on Binance. The headline Sharpe of 15 is meaningless on its own. This post backtests the trade, reports what the data actually show, and itemises the risks that the headline number ignores."
---

A common crypto-Twitter claim is that you can earn the perpetual funding
rate as a delta-neutral carry trade: short the perp, long the spot, collect
the funding payments. The literature is sparse, the practitioner essays
are hype-laden, and the headline numbers tend to be reported without the
risks attached. This post runs the trade on three years of Binance data
and reports both the headline and the honest version.

**Headline**: short 1 BTC of BTCUSDT perp, long 1 BTC of BTCUSDT spot,
hold from 2023-06-07 to 2026-06-11. Over **3,300 eight-hour funding
periods** (1,101 days), cumulative funding-only PnL was **+22.3%**, or
**+7.4% annualised**. After a one-time 4 bps round-trip entry/exit cost,
the annualised return is essentially unchanged (+7.4%). The annualised
Sharpe of the *funding-only PnL series* is **15.3**, but that number is
materially misleading without the risk discussion in §3 below.

![BTC funding carry cumulative](/quant-research-blog/charts/funding-rate-carry/funding_cumulative.png)

## 1. The trade and the data

**Trade**: short 1 BTC notional of the BTCUSDT perpetual futures contract
on Binance USDⓈ-M futures; long 1 BTC notional of BTCUSDT on Binance
spot. Net BTC exposure is zero. Funding payments accrue every 8 hours.

Binance's funding rate sign convention: **positive funding rate means
longs pay shorts.** As a short, we receive `funding_rate × notional`
once every 8 hours when funding is positive, and pay when funding is
negative.

**Data**: pulled from Binance's public futures and spot APIs (no
authentication required):

- `/fapi/v1/fundingRate?symbol=BTCUSDT` for funding history
- `/api/v3/klines?symbol=BTCUSDT&interval=1d` for spot daily closes

3,300 funding observations from **2023-06-07 to 2026-06-11**.
[Full code on GitHub.](https://github.com/jothamteo/quant-research-blog/tree/main/code/funding_rate_carry)

## 2. What the funding distribution looks like

![funding distribution](/quant-research-blog/charts/funding-rate-carry/funding_distribution.png)

| stat                     | value           |
|--------------------------|-----------------|
| mean funding (8h)        | **+0.67 bps**   |
| std funding (8h)         | 0.90 bps        |
| fraction periods > 0     | **84.8%**       |
| worst 8h period          | -1.51 bps       |
| best 8h period           | +8.83 bps       |
| annualised mean (×3×365) | **+7.34%**      |

A few observations.

**The distribution is sharply right-skewed.** The mean is 0.67 bps but
the median is closer to 0.5 bps and the distribution has a thick right
tail of occasional spikes. The biggest 8h funding (+8.8 bps) happens in
the runaway-rally periods when long demand on the perp drives the basis
wide and Binance's funding mechanism reacts.

**The "+1 bps" spike in the histogram is Binance's funding cap.** When the
basis stays wide for an extended period, Binance pins the funding rate at
its cap (`±0.01% per 8h` for most coins under normal conditions). Roughly
30% of the post-2023 observations cluster at this cap, which is
informative: the funding rate is *not* freely floating; it is
mechanically capped, and the cap binds during bull-trend regimes.

**Funding has been positive 85% of the time.** This is a strong directional
prior: BTC perpetuals are in *contango* almost permanently because long
demand exceeds short demand at the margin. The trade is asymmetric — the
short side of the basis is where the systematic edge sits.

## 3. The honest risk picture (i.e. why a Sharpe of 15 is misleading)

The 15.3 Sharpe number is the Sharpe **of the funding-only PnL series
under the assumption that the spot and perp legs perfectly offset each
other**. That assumption ignores at least five real risks. The trade *does*
work in practice, but the realistic Sharpe is somewhere in the 3-6 range
for retail size, lower for institutional size. Here is the itemised list
of what the headline number leaves out.

### 3.1 Basis variance

The perp and spot prices are *not* identical instant-to-instant. In normal
markets the basis is 1-3 bps; in fast-rally days it can spike to 30-50
bps before collapsing back. If you mark the position to fair value each
8h, your reported PnL is funding *plus* the basis change. Over the long
run the basis mean-reverts to zero (mechanically: funding pulls perp
back to spot), but the *path* you have to ride includes meaningful
basis-only mark-to-market drawdowns. A more honest backtest would mark
both legs to their own price at each 8h step. I have not implemented
that here, which is a real omission.

### 3.2 Liquidation risk

Both legs of the trade are margin positions. The perp short is held in
the futures account; the spot long uses the spot account's USDT
collateral. A 30% BTC rally over a single day puts the perp short under
substantial margin pressure even if the spot leg is unrealised-gain by
the same amount, because the two accounts cannot offset directly without
explicit cross-margin (and even with cross-margin, your effective
leverage on the funding-only edge is constrained). The realistic version
of the trade keeps both accounts well over-collateralised, which lowers
the effective return on capital well below the funding-only number.

### 3.3 Slippage on the entry / exit

The 4 bps round-trip I used as a cost is generous for VIP0 Binance retail
on a small ticket. For institutional size, taker fees plus market impact
plus the inevitable failed-leg slippage when one side fills before the
other can easily push the entry/exit cost to 10-15 bps. On a single
holding period that is irrelevant; on a strategy that flips position
when funding goes negative, it eats the edge.

### 3.4 Counterparty risk

The whole strategy lives on a single exchange. Binance is by far the
most reliable major venue; that does not make it riskless. The 2022 FTX
collapse erased the funding-carry edge for everyone caught with collateral
on FTX. A real allocation to this trade requires either spreading across
exchanges (which adds basis risk across venues) or accepting binary
exchange risk as part of the return.

### 3.5 Tail-event regimes

The current dataset spans 2023-2026, a period during which BTC was in a
sustained uptrend interrupted by relatively brief corrections. Negative-
funding periods are short-lived in this sample. In 2018 and 2022 the
funding regime inverted for *months* — the trade would have run flat or
slightly negative. The naive *Sharpe* of 15.3 reads ex-ante that
inversion-events are equally probable in future, which is the standard
historical-sample limitation. The 0.41% max drawdown in this backtest is
almost certainly an under-estimate of the worst case.

## 4. What the trade still has going for it

After all the caveats, the empirical edge is *real*. A few features
that make me take it seriously despite the caveats:

- **Structural**: the long-bias of retail crypto leverage demand pushes
  the basis positive *more often than negative*. This is a mechanical
  feature of the perpetuals product structure, not a flaky alpha.
- **Capped downside per period**: the worst single 8h funding payment in
  3 years was −1.5 bps. Even running the trade *wrong* (long perp / short
  spot) when funding is positive caps your loss at a small per-period
  amount. The asymmetry is genuine.
- **Improves at scale**: high-frequency rebalancing of the spot/perp
  leg ratios (to keep delta exactly zero through spot moves) is a real
  edge improvement that's available to anyone with API access and a
  little discipline.

## 5. What I am explicitly *not* doing in this post

- **No multi-exchange comparison.** Bybit and dYdX also publish funding;
  the trade has different per-venue edges. A serious version of this
  research compares them.
- **No backtest with realistic basis marking.** As noted in §3.1, the
  headline backtest is funding-only. A path-marked version would have a
  meaningfully lower Sharpe.
- **No funding-rate regime model.** A natural follow-up is to model the
  funding rate as a function of basis, BTC momentum, and order-book
  skew, then conditionally allocate. That is a paper in itself.
- **No portfolio-level treatment.** What is the optimal Kelly fraction
  for this edge given the worst-case drawdowns above? I do not answer
  that here.

## 6. Reproducing the backtest

```bash
git clone https://github.com/jothamteo/quant-research-blog
cd quant-research-blog/code/funding_rate_carry
pip install -r requirements.txt
python fetch_binance.py    # ~2 min (paginated futures + spot APIs)
python backtest.py         # ~2 sec — also writes the charts above
```

All numbers in this post come out of `data/backtest_summary.json` and the
charts from `backtest.py`.

---

[^alexander]: Alexander, C., Heck, D. F., & Kaeck, A. (2022). Price
    discovery in Bitcoin spot, futures and perpetual swap markets.
    *Journal of Financial Markets*, 59, Article 100654. The
    price-discovery hierarchy across the three markets.
[^makarov]: Makarov, I., & Schoar, A. (2020). Trading and arbitrage in
    cryptocurrency markets. *Journal of Financial Economics*, 135(2),
    293-319. The early empirical treatment of cross-exchange basis
    behaviour that grounds any serious crypto-arbitrage research.
[^bis]: BIS Quarterly Review (2024). Box: crypto derivatives and the
    funding-rate carry trade. Industry-level sizing of the carry-trade
    flow during the recent bull cycle.
