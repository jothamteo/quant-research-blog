---
title: "Reading dealer positioning on Deribit: GEX, SVI, and what the SqueezeMetrics sign assumption actually buys you"
date: 2026-06-11T11:30:00+08:00
draft: false
math: true
tags: ["options", "microstructure", "deribit", "gex", "svi", "btc"]
summary: "I built a browser-only Deribit BTC options dashboard that fits Gatheral SVI per expiry, computes dealer gamma exposure under the SqueezeMetrics canonical sign convention, and surfaces 25-delta risk-reversal, butterfly and max-pain. This is the post explaining what the dashboard is reading and where the dealer-positioning story actually holds up vs. where it is borrowed faith."
cover:
  image: "/quant-research-blog/covers/deribit-dealer-positioning.png"
  alt: "deribit-dealer-positioning"
  relative: false
---

Think about the thermostat in your house. When the room gets too warm it kicks
on the cooling; too cold, the heat. It pushes *against* whatever's happening, and
the result is a room that stays roughly stable. Now imagine someone reversed the
wiring — it cranks the heat when the room is already hot and blasts cold when
it's freezing. Same machine, opposite sign, and suddenly every little
fluctuation gets amplified into a swing.

Options dealers are a giant thermostat wired into the market. The banks and
market-makers who sell options have to constantly buy and sell the underlying to
stay hedged, and which way they're "wired" — quietly dampening the day's moves or
amplifying them — comes down to one number: their **gamma**. Reading that number
is the single most useful thing my browser-only Deribit BTC options dashboard
tries to do: [jothamteo.github.io/deribit-options-dashboard](https://jothamteo.github.io/deribit-options-dashboard/).

Under the hood it does what the standard equity-options tools do — fits a
[Gatheral SVI](https://www.researchgate.net/publication/267839486_A_parsimonious_arbitrage-free_implied_volatility_parameterization_with_application_to_the_valuation_of_volatility_derivatives)
volatility surface per expiry, computes dealer
[gamma exposure (GEX)](https://squeezemetrics.com/download/The_Implied_Order_Book_and_Gamma_Exposure.pdf)
across the book, and shows 25-delta risk-reversal, butterfly, and max-pain per
expiry — all recomputed locally from the Deribit public API every 30 seconds.
The [methodology doc](https://jothamteo.github.io/deribit-options-dashboard/docs/methodology.html)
is the *what*. This post is the *why*, and — more importantly — the
*how-much-should-you-trust-it*, because porting this idea from stocks to crypto
quietly breaks one of its load-bearing assumptions.

## What dealer GEX is actually measuring

Back to the thermostat. If you sell options to end-users, you are short option
gamma. To stay
delta-neutral as spot moves, you buy when spot rises and sell when spot
falls. Your *aggregate* gamma — the second derivative of your portfolio
value with respect to spot — determines how much rebalancing you do per
1% move in spot. **Negative aggregate gamma** means you rebalance in the
*same* direction as spot moves (buy high, sell low), which amplifies
intraday volatility — the reversed thermostat. **Positive aggregate gamma**
means you rebalance against the spot move, which dampens it — the thermostat
working as intended.

The dashboard's GEX number is the dollar-gamma per 1% spot move,
aggregated across every live option at every strike. The per-option
contribution is

$$
\text{GEX}_i = \Gamma_i \cdot \text{OI}_i \cdot \text{contractSize} \cdot S^2 \cdot 0.01 \cdot \epsilon_i,
$$

with $\Gamma_i$ the Black-Scholes gamma, $\text{OI}_i$ the open interest
in contracts, and $\epsilon_i \in \{+1, -1\}$ the **dealer-side sign**.
The $S^2 \cdot 0.01$ converts the gamma-per-share to dollar-gamma per 1%
spot move. The methodology document derives this in full and benchmarks
the BSM greeks against published Hull values.

The interesting part is $\epsilon_i$.

## The SqueezeMetrics sign assumption

The canonical assumption — the one made by every commercial GEX feed,
inherited from the [SqueezeMetrics (2017)](https://squeezemetrics.com/monitor/download)
paper that put GEX into practitioner vocabulary — is:

$$
\epsilon_i = +1 \;\text{for calls}, \qquad \epsilon_i = -1 \;\text{for puts}.
$$

The story behind this is that in equity index options *as a whole*,
end-users are systematically net buyers of puts (downside protection)
and net sellers of calls (covered-call overwriting). Dealers therefore
sit on the *opposite* side: net short puts, net long calls. Plugging
that into the gamma calculation gives the canonical $+\text{calls},
-\text{puts}$ rule.

When I read SqueezeMetrics' paper for the dashboard, I noticed something
worth being honest about: their sign assumption is **derived from S&P 500
dealer flow circa 2015-2017**. The Deribit BTC options book has none of
the same structural features:

- No insurance-buying base of pension funds and institutional asset
  owners. Crypto has no analogue of the put-buying-for-downside-
  protection demand that anchors the SPX assumption.
- The Deribit user mix is dominated by directional retail, prop trading
  firms, and crypto-native hedge funds. There is no "market-maker bank
  taking the structurally short-put position because their clients keep
  buying puts" pipeline.
- Calls are *more* in vogue than puts on Deribit for big stretches of
  any given bull run — covered-call selling is significant, but so is
  directional call buying.

I implemented the GEX calculation under the SqueezeMetrics sign because
that is what readers of GEX dashboards expect. But I surface the caveat
in the methodology doc and in the dashboard footer: **for Deribit, the
sign of dealer positioning is genuinely less certain than for SPX**.

What can we still take from the chart? Even if the sign is wrong, the
**absolute magnitude** of $|\Gamma_i \cdot \text{OI}_i|$ aggregated by
strike still tells you something useful: it identifies which strikes are
the largest gamma anchors in the book, where the dollar exposure to a 1%
spot move is concentrated. That much is sign-independent. The "zero-gamma
flip level" interpretation — the spot at which dealer hedging flips
from amplifying to dampening — is the thing that **does** depend on the
sign and therefore travels less well from SPX to Deribit.

The honest version of the chart in a portfolio piece is what I built:
implement the canonical sign, do the analytics correctly *given* that
sign, and put the limitation in front of the reader.

## How to actually read the GEX chart

So — caveats noted — what do you *do* with it? Open the GEX panel and the one
number to find is the **zero-gamma flip**: the spot level where aggregate dealer
gamma crosses from positive to negative.

![Reading the GEX chart](/quant-research-blog/charts/deribit-dealer-positioning/gex_reading.png)

Here's the read, and it's the whole reason the chart is worth looking at:

- **Spot trading *above* the flip** → dealers are net long gamma. To stay hedged
  they lean *against* the move: selling into rallies, buying dips. That's a
  stabilising, mean-reverting regime — ranges tend to hold, realised vol stays
  pinned. The practical lean: fading extremes and selling premium has the wind at
  its back; don't expect a clean trend day.
- **Spot trading *below* the flip** → dealers are net short gamma and hedge *with*
  the move: buying as it rises, selling as it falls. That's a destabilising,
  trend-amplifying regime — the same headline can produce a much bigger candle.
  The practical lean: respect breakouts, give trends room, and be wary of selling
  options into it.
- **The largest GEX bars by strike** mark the heaviest hedging anchors — the
  strikes around which dealer rebalancing concentrates. Those levels often act as
  near-term magnets or walls.

Two honesties keep this from being a money-printer. First, all of the above
*assumes the SqueezeMetrics sign holds* — and we just saw it's shakier on Deribit
than on the S&P. Treat the flip as a hypothesis to confirm against price action,
not gospel. Second, even where the sign is right, the magnitudes shift as the
book updates, so the flip level moves: it's a same-day read, not a set-and-forget
level. What I trust most here is the **distribution of gamma across strikes**
(where the anchors are) — that part is sign-independent.

## SVI: why it's the right object to fit

The other workhorse calculation in the dashboard is the
[Gatheral SVI](https://www.researchgate.net/publication/267839486_A_parsimonious_arbitrage-free_implied_volatility_parameterization_with_application_to_the_valuation_of_volatility_derivatives)
fit. For each expiry $T$, total implied variance $w(k) = \sigma^2_{\mathrm{IV}}(k) \cdot T$
as a function of log-moneyness $k = \ln(K / F)$ is fit as

$$
w(k) = a + b \big(\rho \cdot (k - m) + \sqrt{(k - m)^2 + \sigma^2}\big).
$$

Five parameters per expiry: $a$ (overall level), $b$ (wing slope), $\rho$
(asymmetry / put-vs-call skew), $m$ (centre), $\sigma$ (smoothness near
the centre).

Why bother fitting a curve instead of just connecting the market IVs with
straight lines? Because a *fitted* smile is one you can trust at the edges and
between the strikes. SVI's parameters can be constrained so the smile is
guaranteed arbitrage-free, its wings behave the way option theory says they
must,[^lee] and you get a clean ATM reading even when no listed strike sits
exactly at-the-money (common on Deribit). Naive interpolation gives none of
those guarantees and quietly produces garbage skew and butterfly numbers in the
wings. The [methodology doc](https://jothamteo.github.io/deribit-options-dashboard/docs/methodology.html)
has the full fit, the constraint penalties, and the test suite if you want to
audit it.

## How to read the skew for an edge

Here's the part I trust *more* than the GEX flip, because none of it depends on
guessing the dealer sign — it falls straight out of option prices. Once the smile
is fitted, two numbers summarise it, and both are live on the dashboard:

![Reading the skew](/quant-research-blog/charts/deribit-dealer-positioning/skew_reading.png)

- **25-delta risk-reversal (RR)** = the IV of the 25Δ call minus the 25Δ put. It's
  the market's *directional* lean priced in vol. Deeply negative RR (puts much
  richer than calls) means traders are paying up for downside protection — fear.
  Positive RR means they're chasing upside — euphoria. The *level* matters less
  than the *change*: a sharp swing in RR is positioning rotating, often ahead of
  spot. A read: when downside is already extremely bid, the marginal put is
  expensive insurance, and skew tends to mean-revert.
- **25-delta butterfly (BF)** = the average of the wing IVs minus the ATM IV — how
  much extra the market charges for *big moves in either direction*. A rich
  butterfly says the market is bracing for a fat tail; a flat one says it expects
  a quiet grind. If you think the coming move is smaller than the butterfly
  implies, the wings are where you'd sell; if larger, where you'd buy.
- **The ATM term structure** (ATM IV across expiries) tells you *when* the market
  expects the action. Upward-sloping (contango) is the calm default — near-dated
  vol cheap, longer-dated richer. When the front end spikes *above* the back
  (backwardation), the market is pricing an imminent event; that inversion is
  itself the signal.

Because all three come from the fitted prices rather than an assumed dealer
position, they're the readings I'd lean on hardest for an actual BTC options
trade.

## Two things it deliberately doesn't do

So you don't over-read it: the dashboard sets the risk-free rate to zero (there's
no canonical one in crypto — the cost of carry lives in the *forward* computed
from listed futures, which is cleaner than inventing a rate), and it makes **no
attempt to infer the true dealer position from flow**. Estimating who's really
short which strikes needs trade-level taker/maker data the public API doesn't
expose. So the GEX chart shows the *canonical-sign* picture and no more — reading
conviction into the sign is your call, not the dashboard's claim.

## Pragmatic reading guide

If you click around the live dashboard, here is what I take seriously and
what I take with caveat:

| Panel                                | Sign confidence | Magnitude confidence | Useful for                                  |
|---|---|---|---|
| Total GEX                            | medium          | high                 | gamma anchor strikes, flip-level *direction*|
| Zero-gamma flip level                | sign-dependent  | medium               | regime-change spot levels (if SqM sign holds)|
| SVI ATM IV term structure            | n/a             | high                 | clean cross-expiry comparison                |
| 25Δ risk-reversal                    | n/a             | high                 | put-call skew in IV space                    |
| 25Δ butterfly                        | n/a             | high                 | smile curvature in IV space                  |
| Max-pain by expiry                   | n/a             | medium               | shape of OI distribution; *not* a price target |

The "magnetism" interpretation of max-pain — that spot is drawn toward
the max-pain strike — is folklore, not derivation. The chart is still
informative because the *shape* of $\text{pain}(S^*)$ across candidate
strikes tells you where dealer / writer P&L is anchored, regardless of
whether spot actually pins.

## The bottom line

So, what does the SqueezeMetrics sign assumption actually buy you on Deribit? A
**direction-of-regime hypothesis** — a flip level and a long/short-gamma read
that's genuinely useful *if* the sign holds, and that you should treat as a
hypothesis to confirm against price, not a law. The parts that don't depend on
that assumption — where gamma is concentrated by strike, and the whole skew
complex (risk-reversal, butterfly, term structure) — are what I'd actually lean
on for a trade. Read in that order of trust, the dashboard earns its place: GEX
for the regime *story*, skew for the *signal*.

For the live dashboard:
[jothamteo.github.io/deribit-options-dashboard](https://jothamteo.github.io/deribit-options-dashboard/).
For the methodology:
[docs/methodology.html](https://jothamteo.github.io/deribit-options-dashboard/docs/methodology.html).
For the source:
[github.com/jothamteo/deribit-options-dashboard](https://github.com/jothamteo/deribit-options-dashboard).

---

[^lee]: Lee, R. (2004). The moment formula for implied volatility at
    extreme strikes. *Mathematical Finance*, 14(3), 469-480. The
    asymptotic slope result that pinned down what SVI-class
    parameterisations are *supposed* to look like in the wings.
