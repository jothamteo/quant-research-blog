---
title: "An FX dealer's real problem isn't the spread — it's hedging without leaving a mark"
date: 2026-06-24
draft: false
math: true
tags: ["market-making", "fx", "market-impact", "optimal-execution", "inventory-risk", "reproducible-research"]
summary: "A spot-FX dealer earns the spread, then has to get rid of the inventory it just bought — by hedging in the interbank market, where its own trades move the price. A recent note (Barzykin, arXiv:2601.13421) points out that this impact is neither instantaneous nor permanent but transient: the price jumps when you hedge, then heals. I reproduce the mechanism with a transient-impact propagator and show the whole dealer problem reduces to one trade-off — let impact decay (hedge slowly) versus dump inventory risk (hedge fast). The optimal hedge speed is hump-shaped in how fast the market heals, and that has a direct read-across to hedging large fills on Polymarket."
cover:
  image: "/quant-research-blog/covers/fx-transient-impact.png"
  alt: "fx-transient-impact"
  relative: false
---

A market maker's pitch sounds like free money: quote a bid and an ask, buy at one,
sell at the other, pocket the difference, repeat. In spot FX that picture is a
fiction, and the reason is the part nobody puts on the slide. When a client lifts
your offer, you are now **short EUR you didn't want**. The spread you earned is a
few tenths of a basis point. The position you're now holding can move many times
that against you before you find the other side. The dealer's actual job isn't
quoting — it's **getting flat again without the act of getting flat costing more
than the spread you just earned.**

You get flat by hedging in the interbank market. And there's the catch that a
recent eight-page note by Alexander Barzykin
([arXiv:2601.13421](https://arxiv.org/abs/2601.13421)) puts its finger on: **your
hedge moves the price.** Sell EUR to flatten and you push EUR down — partly into
your own fill. The standard way to model that, going back to Almgren–Chriss, splits
impact into two pieces: an *instantaneous* cost you pay on the spot and a
*permanent* shift that stays forever. Barzykin's point is that neither is what
actually happens. Real impact is **transient**: the price jumps when you trade and
then **mean-reverts** as the market heals. Instantaneous and permanent are just the
two limiting cases of one dial — how fast the healing happens.

I wanted to see the mechanism for myself rather than take the abstract's word for
it, so I rebuilt the core trade-off from scratch. Everything here is reproducible
from the
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/fx_transient_impact)
— it's a transient-impact propagator and a one-line cost, no proprietary data and
no heavy optimal-control machinery.

## One dial instead of two impact terms

Model the price displacement your own hedging creates as a decaying memory of your
recent trades. If you hedge at rate $v(t)$ (units per unit time), the extra price
displacement is

$$
J(t) = \eta \int_0^t e^{-\rho\,(t-s)}\, v(s)\,\mathrm{d}s .
$$

Every trade kicks the price by $\eta$ and that kick **decays at rate $\rho$** — the
*resilience* of the market. That single parameter contains both Almgren–Chriss
limits:

- $\rho \to \infty$ — the kick heals instantly. Impact is **purely temporary**: it
  exists only while you're trading, exactly the instantaneous-cost term.
- $\rho \to 0$ — the kick never heals. Impact is **permanent**: every hedge leaves a
  scar that the next one trades into.

Spot FX is neither. It's somewhere in the middle, and *where* in the middle turns
out to decide how a dealer should behave.

Here's the signature, the thing the propagator buys you that a static cost can't
show. Hedge a unit of inventory down at a constant rate over one time unit, then
stop, and watch the price displacement:

![transient signature](/quant-research-blog/charts/fx-transient-impact/transient_signature.png)

The price ramps up while you hedge, peaks the moment you stop, then **reverts back to
zero**. That's the whole idea. And notice the two regimes are qualitatively
different, not just rescaled: when the market is slow to heal (orange) the
displacement is **large and lingers** — you've genuinely moved the market and it
stays moved for a while. When it heals fast (blue) the displacement is **small and
gone almost immediately** — you barely left a footprint. Same trade, same size; the
only thing that changed is $\rho$.

## The dealer's whole problem is one trade-off

Strip the dealer down and there are exactly two forces pulling on how fast to hedge,
and they pull in opposite directions.

**Impact says hedge slowly.** The cost of your impact is what you pay trading into
your own displacement, $\int v(t)\,J(t)\,\mathrm{d}t$. Spread a hedge out and each
child order has time to let the previous one's kick decay before adding its own — so
the displacement never piles up, and the bill is smaller. Patience is cheap
execution.

**Inventory risk says hedge fast.** Every moment you're still holding the position,
the market can move against it. Penalise that warehoused risk the usual quadratic
way, $\gamma \int q(t)^2\,\mathrm{d}t$, and the message is blunt: the position is a
liability, get rid of it.

The dealer just picks the hedge horizon $\tau$ that minimises the sum. Plot total
cost against horizon and you get a clean U — too fast and impact crushes you, too
slow and risk does:

![cost vs speed](/quant-research-blog/charts/fx-transient-impact/cost_vs_speed.png)

The bottom of each U is the optimal hedge speed, and look where it sits. When the
market heals fast (blue) the whole cost curve is *lower* — impact is cheap, so the
optimum drifts toward patient hedging and the floor is deep. When the market is slow
to heal (orange) impact is unavoidable and roughly speed-independent, so there's
nothing to gain by waiting and the optimum jams up against *fast*. The resilience of
the market reaches in and moves where you want to be.

## The punchline: optimal hedge speed is hump-shaped in resilience

Sweep $\rho$ across the whole range — permanent on the left, temporary on the right
— and trace the optimal hedge horizon $\tau^\*$ for three levels of risk aversion:

![optimal horizon](/quant-research-blog/charts/fx-transient-impact/optimal_horizon.png)

This is the result worth sitting with, because the naive intuition ("transient
impact heals, so always hedge slower") is wrong at *both* ends:

- **Permanent impact (far left): hedge immediately.** When the kick never heals,
  going slow buys you nothing — the impact bill is the same however you slice it, so
  the only thing that still matters is inventory risk, and that screams *get flat
  now*. Every curve is pinned to the floor.
- **Very transient impact (far right): hedge fairly fast again.** When the market
  heals almost instantly, impact is so cheap it barely constrains you, and risk
  pulls the horizon back in. You don't *need* to be patient.
- **In between: maximum patience.** Patience only pays when impact is real enough to
  hurt *and* transient enough to reward waiting. That's the hump — and it's exactly
  where spot FX lives.

Risk aversion (the red/green/blue ladder) slides the whole thing: the more you fear
inventory, the further right you have to go — the more transient the market has to
be — before you'll allow yourself to slow down at all. A risk-averse dealer in a
sticky market just dumps.

This is the "interplay between risk management and impact resilience" the paper is
actually about, made concrete. The spread was never the interesting variable. The
interesting variable is **how fast the market forgets what you just did**, and how
much you're willing to bleed in inventory risk while it does.

## Why I care: this is the Polymarket large-fill problem

This isn't an FX-desk curiosity for me — it's the same shape as a problem I keep
hitting on prediction markets. When one of my Polymarket bots gets a large fill, or
wants to unwind a position into a thin book, the order book behaves *exactly* like
the propagator above: a big print walks the book, the price gaps, and then —
crucially — it **partially heals** as resting liquidity refills the levels you ate.
That heal is transient impact, and its rate $\rho$ is just "how fast does this book
refill."

The read-across is direct:

- **Don't model book impact as permanent.** If you assume your fill permanently
  re-rates the market, you'll either panic-unwind into your own footprint or sit on
  risk you didn't need to. The truth is in between, and the post above is how you'd
  estimate where.
- **The right unwind speed is a measurable property of the book, not a constant.**
  $\rho$ — the refill rate — is estimable from how quickly depth returns after large
  prints. Feed it into the same U-curve and you get an unwind horizon instead of a
  guess.
- **Thin, slow-to-refill books are the permanent-impact corner: get flat fast.**
  Deep, fast-refilling books are the transient corner: you can afford to work the
  order. Same chart, different venue.

The honest caveat: I've reproduced the *mechanism*, not the paper's full
optimal-control solution — Barzykin solves the dealer's stochastic control problem
properly; I've reduced it to a transparent one-parameter hedge-horizon trade-off so
the moving parts are visible. The qualitative conclusions — transient signature,
U-shaped cost, hump-shaped optimal speed — are robust to that simplification. The
exact numbers are not the point; the *shape* is, and the shape is what tells you how
to hedge a fill. Next step on my side is to actually estimate $\rho$ from
Polymarket book-refill data and see where my markets sit on that hump.

*Code and charts: [`code/fx_transient_impact`](https://github.com/jothamteo/quant-research-blog/tree/main/code/fx_transient_impact). Paper: Barzykin, "Market Making and Transient Impact in Spot FX," [arXiv:2601.13421](https://arxiv.org/abs/2601.13421).*
