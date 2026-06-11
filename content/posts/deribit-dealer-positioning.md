---
title: "Reading dealer positioning on Deribit: GEX, SVI, and what the SqueezeMetrics sign assumption actually buys you"
date: 2026-06-13
draft: false
math: true
tags: ["options", "microstructure", "deribit", "gex", "svi", "btc"]
summary: "I built a browser-only Deribit BTC options dashboard that fits Gatheral SVI per expiry, computes dealer gamma exposure under the SqueezeMetrics canonical sign convention, and surfaces 25-delta risk-reversal, butterfly and max-pain. This is the post explaining what the dashboard is reading and where the dealer-positioning story actually holds up vs. where it is borrowed faith."
---

For the last few months I've been working on a small browser-only options
dashboard for Deribit BTC: [jothamteo.github.io/deribit-options-dashboard](https://jothamteo.github.io/deribit-options-dashboard/).
The dashboard does what the standard equity-options analytics tools do —
fits a [Gatheral SVI](https://www.researchgate.net/publication/267839486_A_parsimonious_arbitrage-free_implied_volatility_parameterization_with_application_to_the_valuation_of_volatility_derivatives)
volatility surface per expiry, computes dealer
[gamma exposure (GEX)](https://squeezemetrics.com/download/The_Implied_Order_Book_and_Gamma_Exposure.pdf)
across the book, shows the 25-delta risk-reversal and butterfly term
structures, and finds max-pain per expiry. Everything is recomputed
locally from the Deribit public API every 30 seconds. The full methodology
document is at [docs/methodology.html](https://jothamteo.github.io/deribit-options-dashboard/docs/methodology.html).

The methodology document is the *what*. This post is the *why* and,
more importantly, the *how-much-do-we-trust-it*. Two questions matter.

## What dealer GEX is actually measuring

If you sell options to end-users, you are short option gamma. To stay
delta-neutral as spot moves, you buy when spot rises and sell when spot
falls. Your *aggregate* gamma — the second derivative of your portfolio
value with respect to spot — determines how much rebalancing you do per
1% move in spot. **Negative aggregate gamma** means you rebalance in the
*same* direction as spot moves (buy high, sell low), which amplifies
intraday volatility. **Positive aggregate gamma** means you rebalance
against the spot move, which dampens it.

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

Why fit a parametric form at all rather than just linearly interpolating
the market IVs? Three reasons that are non-negotiable in practice.

1. **No-arbitrage constraints are explicit.** The SVI form is convex in
   $k$ when $b \ge 0$, $|\rho| < 1$, $\sigma > 0$, and
   $a + b\sigma\sqrt{1 - \rho^2} \ge 0$. As long as the optimiser respects
   those four constraints (the dashboard's optimiser uses a soft-penalty
   Nelder-Mead implementation that I wrote and tested) the fit is
   guaranteed to be a no-static-arbitrage smile. Linear-interpolation
   between market IVs is *not*.

2. **ATM IV is well-defined.** Deribit's listed strike grid doesn't
   always include the forward exactly, so the at-the-money mark is not
   always on a listed strike. Evaluating the SVI at $k = 0$ gives a
   smooth, parameter-consistent ATM IV for term-structure plots. Linear
   interpolation in IV between the two nearest strikes is asymptotically
   identical but loses the no-arbitrage guarantee.

3. **The wing behaviour is dictated by theory.** Lee's moment formula[^lee]
   constrains the asymptotic slope of total variance as $|k| \to \infty$.
   SVI naturally has the asymptotic form $w(k) \sim |k| \cdot b(1 \pm \rho)$,
   which is exactly what Lee predicts. Fits that don't have this
   asymptotic shape (e.g. cubic splines) extrapolate badly into deep OTM
   wings and produce spurious skew or butterfly numbers.

The methodology doc derives the fit, the constraint penalties, and the
seeding strategy in full and links to the test suite that benchmarks the
output against textbook examples.

## What the dashboard is *not* doing

Three things worth flagging explicitly because they are easy assumptions
to make if you've only used the dashboard from the outside.

1. **No risk-free rate.** $r$ and $q$ are both set to zero in the
   Black-Scholes calculation. The methodology doc explains why: there is
   no canonical crypto risk-free rate, perpetual funding is too noisy to
   use as a substitute, and the alternative — encoding the cost of carry
   into the *forward* curve computed from listed Deribit futures — is
   cleaner and more defensible than picking an arbitrary rate. The cost
   of carry shows up in $F$, where it belongs, not in $r$.

2. **No flow-decomposition.** The dashboard does not attempt to estimate
   dealer position from observed maker-quoting behaviour. Doing that
   credibly requires either trade-by-trade taker-vs-maker flag data (which
   Deribit's public API doesn't provide at strike granularity) or a
   structural model of market-maker inventory dynamics. Both are out of
   scope for a static portfolio piece. The GEX chart presents the
   *canonical-sign* dealer-positioning picture; reading anything more
   into it is the operator's call, not the dashboard's claim.

3. **No realised-volatility benchmark.** A natural addition would be a
   "realised vol vs implied vol" rolling time-series, which would put the
   SVI fit's ATM IV in context. I haven't added it because Deribit's
   public API has a 30-second rate budget that I'm using for the
   live-book pull; adding a 30-day spot history pull would change the
   request shape. It's on the list.

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

## Take-aways

- Browser-only options analytics on a public API is a perfectly viable
  portfolio-piece pattern: no backend cost, full reproducibility, and the
  methodology doc plus the test suite make the implementation auditable
  by anyone.
- The dashboard correctly implements the canonical SqueezeMetrics GEX
  sign. *Correctly* does not mean *for-Deribit-trustworthy* — it means
  *consistent with the published canonical assumption*, which is the
  honest baseline.
- The SVI fit is the more reliably useful object: skew and butterfly
  numbers are sign-independent, smile shape is invariant to my $r = 0$
  choice, and the no-arbitrage constraints are explicit.
- The biggest open improvement is empirical estimation of dealer
  positioning from Deribit's actual flow rather than borrowing the SPX
  sign. I haven't done it because it needs richer data than the public
  API exposes.

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
