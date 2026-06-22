---
title: "Two venues, one bet: do Polymarket and Deribit agree on Bitcoin's odds?"
date: 2026-06-22
draft: false
math: true
tags: ["prediction-markets", "options", "crypto", "deribit", "polymarket", "market-microstructure", "reproducible-research"]
summary: "Polymarket sells you a contract that pays $1 if Bitcoin is above some price on some date. The options market prices the exact same bet — you just have to dig it out of the call curve. A new paper finds the two disagree by 5–11 percentage points. I rebuilt the test on live data: at the short, liquid end the venues agree to ~1.6pp, but Polymarket is systematically rich in the long-shot tails — the same tilt the paper documents, scaled down by maturity."
cover:
  image: "/quant-research-blog/covers/polymarket-vs-option-implied-btc.png"
  alt: "polymarket-vs-option-implied-btc"
  relative: false
---

Picture two bookmakers on the same street taking bets on one question: *will
Bitcoin be above \$66,000 on Friday?* One writes the odds on a chalkboard out
front. The other never quotes that bet directly — but he's quoting a whole ladder
of related bets, and if you're willing to do a little arithmetic you can back out
exactly what *he* thinks the odds are. Now you can stand between them and ask the
only question that matters: **do they agree?**

That's not a metaphor — it's a live arbitrage check, and a
[new paper](https://arxiv.org/abs/2606.19517) just ran it at scale. The first
bookmaker is **Polymarket**, which lists contracts that pay \$1 if BTC is above a
strike on a date. The second is the **options market** (Binance in the paper;
**Deribit** here), which prices the identical payoff implicitly. The paper finds
they *don't* agree: a persistent **5.6–6.3 percentage-point** gap on Binance
(11pp on Deribit), with Polymarket richer, mean-reverting on a ~4-hour half-life.
I wanted to see it with my own eyes, on live prices. Everything below is
reproducible from the
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/pm_vs_options);
prices are a snapshot from **22 June 2026**.

## The trick: an option chain already contains the digital

Here's the bit of arithmetic that makes the two venues comparable. A Polymarket
"BTC above \$K" contract is a **digital** (or binary) option: it pays \$1 if
$S_T > K$, nothing otherwise. Its fair value is simply the risk-neutral
probability $\;\mathbb{P}(S_T > K)$.

The options market doesn't list that digital — but it lists ordinary calls at a
ladder of strikes, and the digital is hiding in the *slope* of the call curve:

$$
\mathbb{P}(S_T > K)\;=\;-\,e^{rT}\,\frac{\partial C}{\partial K}\;\approx\;-\frac{\partial C}{\partial K}
$$

(the discount factor $e^{rT}$ is ~1 over a few days). Intuitively: a call struck
at \$K and one struck just above at \$K+\Delta differ in price by exactly the
chance Bitcoin lands in between — so the **negative slope of the call curve is the
probability of finishing above the strike.** Take Deribit's calls, difference them
across adjacent strikes, and you have the option market's answer to the very same
question Polymarket is quoting. No model, no implied-vol assumptions — just the
prices.

## A worked example: "BTC above K on 26 June"

Polymarket lists eleven strikes for that day. I took each one's Yes price and, for
every strike, computed Deribit's implied probability from the 26 Jun call curve
(spot was ~\$63.9k). Side by side:

| Strike | Polymarket Yes | Deribit-implied | Gap |
|-------:|:-------------:|:--------------:|:---:|
| \$56k | 99.4% | 97.7% | **+1.7** |
| \$60k | 92.5% | 91.0% | +1.5 |
| \$62k | 76.5% | 78.9% | −2.4 |
| \$64k (ATM) | 50.5% | 54.0% | **−3.5** |
| \$66k | 23.5% | 22.4% | +1.1 |
| \$68k | 7.5% | 5.1% | **+2.4** |
| \$70k | 2.2% | 1.0% | +1.3 |

![June 26 curves](/quant-research-blog/charts/pm-vs-options/june26_curves.png)

Eyeball the two curves and they sit almost on top of each other — which is itself
worth noting. But look closer at the *pattern* of the gaps: around the money
(\$62–64k) Polymarket is a touch **cheap**; out in the long-shot tails (\$68k+) it's
**rich**. Hold that thought.

## Pooling five days: small gap, familiar tilt

One day could be a fluke, so I pooled every strike across **June 22–26** — 43
matched Polymarket/Deribit observations. The result:

- **Mean gap: +0.81pp** (Polymarket richer), mean absolute gap **1.58pp**.
- Polymarket is the richer side **74% of the time** (naive $t \approx 2.5$ — though
  these observations are autocorrelated, so a HAC/clustered standard error would
  widen that meaningfully; call it "real but not overwhelming").

So at this short, liquid horizon the two venues agree to within a couple of points
— *much* tighter than the paper's 5–11pp. That's not a contradiction; it's the
maturity story. But the *shape* is the giveaway:

![gap vs probability](/quant-research-blog/charts/pm-vs-options/gap_vs_prob.png)

Bucket the gap by Deribit's implied probability:

| Implied probability | Mean gap |
|---|:--:|
| Low (< 25%) — long shots | **+1.7pp** |
| Middle (25–75%) | +0.4pp |
| High (> 75%) — near-certain | +0.0pp |

**Polymarket is systematically rich in the long shots and bang-on for the
near-certain bets.** That is exactly the direction the paper documents — the wedge
"largest at low option-implied probabilities" — and the standard reading is
*speculative demand*: punters on a prediction market overpay for cheap-looking
lottery tickets ("BTC to \$70k by Friday for 2 cents!"), while the options market,
priced by hedgers and arbitrageurs, doesn't. We're seeing the same fingerprint at
one-week maturity that the paper sees, larger, at one month.

## So why is *our* gap small and theirs big?

Two reasons, and both are the honest limitation of a live reproduction:

1. **Maturity.** The paper's headline gaps come from *monthly* contracts; our clean
   live comparison is *daily/weekly*. A bet resolving tomorrow gives arbitrageurs
   almost no risk to warehouse, so they crush the gap; a bet resolving in a month
   carries inventory risk and accumulates speculative demand, so the wedge widens.
   The paper finds precisely this — the gap grows with maturity.
2. **Polymarket doesn't list long-dated *European* BTC thresholds.** Its long-dated
   BTC markets ("will Bitcoin *reach* \$200k by Dec 31?") are **one-touch barriers**,
   not "above on the date" digitals — a different payoff that doesn't line up with a
   vanilla option-implied binary. So the clean apples-to-apples comparison is, today,
   necessarily short-dated. That's a real constraint on the live test, not a flaw in
   the paper.

## Can you actually trade the gap?

A +0.8pp average edge at one-week maturity does not survive a serious accounting:

- **De-vigging.** I used Polymarket mid prices and Deribit mark prices. Cross the
  real bid-ask on both legs and a 1–2pp gap is mostly gone.
- **Timing mismatch.** Polymarket's "on June 26" resolves at **16:00 UTC**; Deribit's
  26 Jun options expire at **08:00 UTC** — eight hours apart. Part of any small gap is
  just that extra half-day of optionality, not a true mispricing.
- **Execution.** You'd need both legs wired (USDC on Polygon for one, a Deribit
  account for the other) and the discipline to hold to resolution.

The paper's own verdict is the honest one: a delta-hedged arbitrage proxy stays
*marginally* profitable after conservative costs, "with marginal statistical
precision." Translation: it's a real, persistent wedge — evidence that two venues
pricing identical payoffs don't fully agree — but it is not a fat free lunch,
least of all at the short maturities you can cleanly access.

## The bottom line

- The option chain already contains Polymarket's bet — it's the slope of the call
  curve — so you can check the two venues against each other with nothing but
  prices.
- Live, at one-week maturity, **they agree to ~1.6pp**, with Polymarket carrying a
  small, systematic richness **concentrated in the long-shot tails** — the same
  fingerprint the paper finds at larger scale.
- The big 5–11pp wedges live at **longer maturities**, which Polymarket only offers
  as one-touch markets — so the clean version of this trade is a
  longer-dated game than a retail screen makes it look.

## Limitations (the honest list)

- **Snapshot, not a time series.** I can't measure the paper's ~4-hour mean-reversion
  half-life from one reading; that needs continuous collection (a good follow-up —
  the VPS that pulls this could log it hourly).
- **Resolution-time mismatch** (16:00 vs 08:00 UTC) and **de-vig** (mids/marks, not
  executable bid-ask) both flatter the gap's tradeability.
- **Digital via finite differences** of Deribit marks across a discrete strike grid;
  a smoother fit (or a proper call-spread bound) would tighten the tails where
  marks get noisy (note the −0.0% at \$74k — a discretisation artefact, floored at 0).
- **Near-dated only**, for the structural reason above.
