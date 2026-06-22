---
title: "Buying cheap vol: does the insurance-buyer's trade work on crypto?"
date: 2026-06-18
draft: false
math: true
tags: ["options", "volatility", "crypto", "deribit", "market-microstructure", "reproducible-research"]
summary: "Selling options harvests the variance risk premium — until it blows up. The opposite trade, systematically *buying* cheap vol and selling the bounce, is harder to kill. I test it on 5 years of Deribit BTC implied vol, find the mean-reversion edge is real but subtler than it looks, and then ask the question that actually decides it: can you afford the spread? BTC on Deribit clears the bar; HYPE options on derive.xyz don't even have a quote."
cover:
  image: "/quant-research-blog/covers/buying-cheap-vol-crypto.png"
  alt: "buying-cheap-vol-crypto"
  relative: false
---

Think about who sells flood insurance. They collect a premium from everyone,
every year, and most years nothing happens — pure profit. Then one year the river
comes over the wall and they pay out everything they collected and then some. It's
a wonderful business right up until the day it isn't.

Selling options is the same business. Implied volatility — the price of the
insurance — sits *above* the volatility that actually shows up, almost all the
time. That gap is the **variance risk premium**, and harvesting it (selling
options, collecting the premium) is one of the most reliable edges in markets.
Until three bad sessions erase a year of it.

So here's the contrarian question: instead of *selling* the overpriced
insurance, can you make money *buying* it — but only when it's on sale? Be the
person who calmly buys flood cover in the dry season, when everyone's forgotten
the last flood and premiums are cheap, and sells it back when the clouds roll in.
That's the **buy-cheap-vol** trade, and this post tests whether it survives the
trip to crypto — specifically BTC options on **Deribit** and HYPE options on
**derive.xyz**. Every number is reproducible from the
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/vol_buying_crypto);
market data is a live snapshot from **18 June 2026**.[^credit]

## The method, in one rule

Buy volatility when it's *historically cheap*, and only then. The standard gauge
is **IV-rank** — where today's implied vol sits inside its own trailing one-year
range:

$$
\text{IV-rank} = 100 \times \frac{\text{IV}_{\text{today}} - \min_{1y}\text{IV}}
{\max_{1y}\text{IV} - \min_{1y}\text{IV}}
$$

When IV-rank is low, vol is near the bottom of its recent range. The rule: **enter
long vol only when IV-rank < 35.** The thesis is mean reversion — cheap vol tends
to climb back. The chart below is BTC's implied vol (Deribit's **DVOL** index)
over five years, with the "cheap" regime shaded.

![DVOL regime](/quant-research-blog/charts/vol-buying-crypto/dvol_regime.png)

As I write this, **BTC's IV-rank is 17.6 — squarely in buy territory** (DVOL ~42,
near the floor of its range). The signal is live. Which makes "does this actually
work?" more than academic.

## What the data says — and the part everyone gets wrong

Here's where most write-ups stop: "vol mean-reverts, so buy it cheap, easy." I
ran five years of DVOL to check, and the honest answer has two halves.

**Half one — the mean reversion is real.** Bucket every day by its IV-rank and
look at how DVOL moves over the *next* 30 days:

![mean reversion by IV-rank](/quant-research-blog/charts/vol-buying-crypto/meanrev_by_ivrank.png)

It's beautifully monotonic. When vol is cheap (IV-rank < 20), it drifts **up**
+2.5 points over the next month; when it's expensive (IV-rank > 65), it
collapses −17 points. Buying cheap vol does put the wind at your back. So far so
good.

**Half two — but the variance risk premium doesn't die just because vol is
cheap.** A long straddle held to expiry and delta-hedged earns, roughly,

$$
\text{P\&L} \;\propto\; \sigma_{\text{realized}}^2 - \sigma_{\text{implied}}^2
$$

— you win if *realized* vol comes in above the *implied* you paid. So I measured
exactly that: at every entry, the forward 30-day realized vol minus the implied
you'd have paid.

![edge by IV-rank](/quant-research-blog/charts/vol-buying-crypto/edge_by_ivrank.png)

Every bucket is **negative**. Even in the cheapest-vol regime, realized came in
**4.2 vol points below implied** on average, and beat implied only **38% of the
time**. Read that again: even when vol looks cheap, if you just buy the straddle
and hold it to expiry, *you still lose to the premium on average.* (It's "least
bad" when cheap and catastrophic when expensive — which is simply the mirror
image of why *selling* vol works.)

**So how can the trade make money?** Reconcile the two halves and the mechanism
falls out: you are **not** harvesting realized-beats-implied. You're harvesting
the **mean reversion of the implied vol itself** — buy when DVOL is at 42, sell
when it pops back to 50 on the next scare, and pocket the **vega**. You exit on
the bounce; you do *not* sit there hoping realized vol shows up to vindicate the
straddle. That's why a well-built version of this trade *barely trades* and exits
quickly — it's a timing trade on the price of insurance, not a bet that the flood
arrives. Miss that distinction and you'll hold too long and feed the premium right
back.

## The question that actually decides it: can you afford the spread?

A vega-timing edge of a few vol points is small. Small edges die on transaction
costs. The single most useful thing in the original write-up that inspired this
was the discipline of running *real* bid-ask spreads first — and watching most
candidates fail. On US ETFs, only the most liquid (SPY, IWM, TLT) survived;
spreads on the rest ate the whole edge.

So before believing a word of it for crypto, I pulled **live** Deribit BTC option
spreads across maturities, as a fraction of the option's premium:

![slippage curve](/quant-research-blog/charts/vol-buying-crypto/slippage_curve.png)

| Days to expiry | Round-trip spread / premium |
|---:|:--|
| ~1 day | 18.4% (forget it) |
| ~8 days | 4.7% |
| ~15 days | **1.7%** |
| ~22 days | **1.4%** |
| ~43 days | **1.9%** |

At the 2–6 week maturities you'd actually use for a mean-reversion trade, **BTC on
Deribit costs 1.4–1.9% of premium round-trip** — right in the band of Sam's
surviving US ETFs. Short-dated options are a slippage trap (18% on the 1-day), but
that's not where this trade lives. **Verdict: BTC options on Deribit clear the
cost bar.** The edge is small, but it's not eaten alive before it starts.

## HYPE on derive.xyz: the signal can be screaming and it won't matter

Now the frontier case. derive.xyz lists **748 HYPE options**, so on paper you can
run the same playbook on Hyperliquid's token. In practice I checked the order
books across the three nearest expiries:

| Expiry | Strikes with a two-sided quote |
|---|---|
| 19 Jun 2026 | **0 / 40** |
| 20 Jun 2026 | **0 / 40** |
| 21 Jun 2026 | **0 / 38** |

There is **no resting market** — not a wide one, *none*. The ATM HYPE option shows
bid 0 / ask 0. derive leans on request-for-quote market making, so a price exists
only if you ping for one, and on a token this young that quote will be wide and
shallow. It doesn't matter how cheap HYPE vol looks on the screen: this is the
flood insurer who'll sell you a policy *only* if you call, and only at his price.
You cannot systematically buy cheap vol on a book that isn't there. **Verdict: the
strategy is untradeable on derive HYPE today** — the exact slippage wall, at its
most extreme.

## The bottom line

- **The method is a vega mean-reversion trade, not a "buy a straddle and pray for
  a crash" trade.** Cheap vol reliably drifts up (the edge); realized still
  undershoots implied even when cheap (why you must exit on the bounce, not hold).
- **BTC on Deribit passes both tests:** the mean-reversion signal works, it's live
  right now (IV-rank 17.6), and 2–6 week spreads (1.4–1.9% of premium) are cheap
  enough to trade.
- **HYPE on derive fails the only test that matters in the end** — there's no
  two-sided market to lift, so the signal is academic.

It's the same lesson the ETF version taught, sharpened by crypto's liquidity
gradient: **the edge is in the vol, but whether you keep it is decided by the
spread.** A pristine signal on an empty book is worth exactly nothing.

## Limitations (the honest list)

- **No historical option chains.** Deribit's free API doesn't give deep history
  of full option prices, so I test the *signal* on five years of DVOL + realized
  vol, plus a *live* slippage snapshot — not a multi-year fill-by-fill straddle
  backtest. The mechanism is evidenced; the exact net P&L of a specific
  entry/exit rule is the next step (and needs paid chain data or forward
  collection).
- **DVOL is a 30-day ATM-ish index**, not the specific option you'd trade; skew
  and term structure will move the real numbers.
- **One snapshot of spreads.** Liquidity varies; the 1.4–1.9% is a daytime
  reading on 18 June 2026, not a guarantee.
- **Mean reversion is a regime, not a law.** A prolonged quiet market — vol cheap
  and *staying* cheap — is precisely where this trade bleeds, and five years
  (incl. only a couple of true low-vol stretches) can't fully price that risk.

[^credit]: The framing — systematic vol-buying gated on IV-rank, with brutal
    honesty about slippage killing most underlyings — follows a write-up by
    [@sam_sathiaraj19](https://medium.com/@sam.sambathkumar7/a-full-breakdown-of-building-a-systematic-vol-buying-strategy-f63aab543c8a)
    on US ETFs. The crypto extension, the DVOL analysis, and the
    realized-vs-implied decomposition here are my own.
