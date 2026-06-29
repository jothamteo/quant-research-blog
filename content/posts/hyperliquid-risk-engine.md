---
title: "Decompiling Hyperliquid's risk engine: who gets force-closed when the exchange is short — and how not to be them"
date: 2026-06-27
draft: false
math: true
tags: ["market-microstructure", "perpetuals", "hyperliquid", "risk", "auto-deleveraging", "cross-exchange-arbitrage", "reproducible-research"]
summary: "Ottersec reverse-engineered Hyperliquid's closed-source Rust risk engine and recovered the exact rule that decides which winners get force-closed when the exchange takes on bad debt. I verify their reconstructed ADL ranking formula against Hyperliquid's own published docs and the 11 Oct 2025 cascade — it checks out — then build a reproducible numpy model of the queue. The punchline is a tradeable one: ADL is a deterministic, public-state tax on being both levered and right, and you can compute your own place in the firing line. With the actionable read for winners, the 'be ADL-senior' play, and the cross-exchange hedge against being clipped at a stale mark."
cover:
  image: "/quant-research-blog/covers/hyperliquid-risk-engine.png"
  alt: "hyperliquid-risk-engine"
  relative: false
---

The security firm Ottersec just published something unusual: they pointed a fleet of
AI agents at Hyperliquid's *closed-source* `hl-node` binary — a 51 MB stripped Rust
executable — and reverse-engineered the exchange's risk engine from the machine code
up ([osec.io, 22 Jun 2026](https://osec.io/blog/2026-06-22-hyperliquid-risk-engine/)).
Most of the writeup is a tour de force of decompilation tooling. But buried in it is
one object that every Hyperliquid trader should care about more than any candlestick:
**the exact formula that decides whose winning position gets force-closed when the
exchange is left holding a loss.**

This post does three things, all reproducible from
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/hyperliquid_risk_engine)
(plain numpy, no external data): I explain the mechanism from first principles, I
*verify* Ottersec's reconstructed formula against Hyperliquid's own documentation and
on-chain history, and then — the part I actually care about — I work out what a desk
can do with it. Because this rule isn't a black box once you have it. It's
deterministic, it runs on public state, and it systematically taxes a very specific
kind of trader. Knowing which kind is an edge.

## Foundation: why a perp exchange ever has to claw back a winner

On a perpetual-futures venue, the market is zero-sum across traders: every dollar a
winner is up, a loser is down. Normally that's fine — when a loser's margin runs
out, the engine **liquidates** them into the order book, and the winner gets paid out
of the proceeds. For an isolated position, that trigger fires (per the reconstructed
code) around

$$
\text{liq\_equity} = \frac{|\text{notional}|}{2 \cdot \text{leverage}},
$$

i.e. when your equity falls to roughly half your maintenance requirement.

The trouble is a fast move into a thin book. If price gaps and the book can't absorb
the liquidation, the loser's account goes *negative* — they owe more than they have.
That gap is **bad debt**, and someone has to eat it or the exchange is insolvent.
Hyperliquid's defenses stack up in order: first the **HLP** (the protocol's
market-making vault) and the **insurance fund** absorb the hole. Only when *those* are
exhausted does the engine reach for its last resort — **auto-deleveraging (ADL)**:
it reaches across the trade and force-closes *winning* positions on the other side,
at the previous mark price, to cover the debt. Hyperliquid's design promise is that a
user with no open position never socialises anyone's loss. The flip side is that if
you're winning, you are the insurance fund of last resort.

This is rare — the first platform-wide cross-margin ADL didn't fire until **11 October
2025**, more than two years after launch, when a market-wide cascade force-closed
profitable positions across tens of thousands of accounts. Rare, but when it hits, it
hits the same people every time. Who?

## The rule, recovered — and verified

Ottersec's decompilation recovers a single sort key. Each candidate position on the
winning side gets a score

$$
\text{score}_i \;=\; \underbrace{\frac{|\text{notional}_i|}{\text{account\_value}_i}}_{\text{effective leverage}}
\;\times\;
\underbrace{\frac{\max(\text{pnl}_i,\,0)}{\text{entry\_notional}_i}}_{\text{profit ratio}},
$$

with both factors floored at $10^{-8}$ so neither can zero out the product, and
**positions are closed in descending score**: highest first. In plain English — the
engine fires the trader who is *most levered* and *most in profit* before anyone else.

Is this real, or an artifact of reading tea leaves in a stripped binary? I cross-checked
it three ways, and it holds:

1. **Hyperliquid's own docs.** Their published ADL page states the ordering index is
   $(\text{mark}/\text{entry}) \times (\text{notional}/\text{account\_value})$, ranking
   counterparties by "unrealized pnl and leverage used." For a long, $\text{mark}/\text{entry}
   = 1 + \text{pnl}/\text{entry\_notional}$, so that index is a monotone transform of
   Ottersec's score — **the same ordering.** The reconstruction matches the official rule.
2. **Observed behaviour.** The 11 Oct 2025 ADL is documented as closing "the highest
   profit and leverage" counterparties first — exactly what the formula predicts.
3. **What it is *not*.** The infamous March 2025 JELLY episode was *not* this mechanism
   — that was a manual validator intervention that delisted the token and settled
   positions at an administratively-chosen price. Different beast. ADL is the automatic,
   code-path backstop described here. Keeping those two straight matters.

So the mechanism is verified fact. Ottersec's *editorial* on top of it — that the rule
is "antifair" versus alternatives like Percolator — is a defensible design argument, not
a fact, and I'll treat it as such below.

## What the rule does to a crowd

Let me make the abstract concrete. I simulate 600 winning longs after a +12% run, with
realistic dispersion in leverage (most clustered low, a tail maxing near 20×), account
size (a few whales, a long retail tail), and profit ratio (everyone entered at a
different time). Then I inflict a severe cascade — bad debt equal to 30% of open winning
notional, in the spirit of the October event — and let the engine walk its queue.

![who ADL closes](/quant-research-blog/charts/hyperliquid-risk-engine/adl_queue.png)

The casualties (red) are not random. They live in the upper-right corner: high leverage
*and* high profit. The survivors (grey) fill the rest of the plane. In this run, **100%
of the high-leverage, high-profit corner (≥10× and ≥6% profit) got force-closed, while
0% of the conservative corner (≤3× leverage) was touched** — even the conservative
traders who were *more* in profit. Leverage, not being right, is what puts you in the
chair.

That asymmetry is the whole of Ottersec's "antifairness" complaint, and it's easy to
quantify. Take each trader's haircut as a share of their own equity, $h_i = x_i / w_i$,
and measure the inequality of the $h_i$ across winners with a Gini coefficient. Compare
the queue against the leverage-indifferent alternative — a Percolator-style rule that
just trims everyone's withdrawal capacity by the same fraction of equity:

![who carries the bad debt](/quant-research-blog/charts/hyperliquid-risk-engine/fairness.png)

The pro-rata rule sits on the equality diagonal (**Gini = 0.00** by construction — pain
shared flat). Hyperliquid's queue hugs the floor and then spikes: **about 87% of winners
pay nothing, and the top ~13% absorb the entire loss (Gini = 0.89).** That's the
trilemma Ottersec frames — a queue reaches solvency *fast* (close the biggest, riskiest
positions and you cover the hole in the fewest closures) but distributes the pain
*unequally*; a flat rule is fair but slower and touches everyone. Neither is "correct";
they're different points on a solvency–fairness–speed frontier. Hyperliquid picked the
fast corner.

## The part that's actually tradeable

Here's where I diverge from a security writeup. "Antifair" is a complaint. To a desk,
**a deterministic rule on public state is not a complaint — it's a signal.** Three uses:

**1. For winners: the seniority knob.** Your ADL score is *your own choice* on one axis.
Hold the same directional bet, the same entry, the same conviction — and vary only how
much margin you post. More margin → lower effective leverage → lower score → further
back in the queue. The model makes this precise:

![the seniority knob](/quant-research-blog/charts/hyperliquid-risk-engine/seniority.png)

The same winning position taken at 3× sits around the 35th percentile of the queue; at
10× it's past the 85th; above ~10× in this cascade it crosses a hard kill-line where the
axe reaches you with near-certainty. **De-levering from 10× to 3× on a winning trade
roughly halves your place in the firing line without changing your view at all.** ADL is,
precisely, a tax on being levered *and* right — and you control the leverage term in real
time. The discipline writes itself: as a position runs into deep profit on the crowded
side, *scale leverage down as PnL scales up*. You keep the directional exposure; you shed
the queue priority.

**2. Be ADL-senior on purpose.** Flip it around. ADL force-closes your levered
competitors *at the previous mark* — flushing them out of a winning trade right as it's
working. If you're holding the same side at low leverage, you don't just survive the
cascade; you inherit the continuation they were forced to abandon. Running deliberately
low effective leverage on a crowded, one-sided trade is a way to be *senior* to the
leveraged crowd: same thesis, but you're the one still in the position when the engine
clears the deck.

**3. Monitor your own rank, and beat the engine to it.** The queue is recomputed from
public state on a roughly 3-second cadence. That means you can compute *your own ADL
percentile* live, the same way the engine does, from your leverage and profit ratio
relative to the visible book. If you're drifting toward the front during a stressed
session, you can deleverage *yourself* — at the real market, on your terms — before the
engine deleverages you at a stale mark on its terms. Self-liquidation at a good price
beats forced liquidation at a bad one. Two leading indicators feed the same dashboard:
HLP equity and insurance-fund depth (ADL can't fire until both are drained), and the
**`only_isolated` / `strict_isolated`** asset flags Ottersec found — names like HYPE,
ZRO and JELLY that can trigger ADL on their *own* shortfall regardless of the
system-wide picture. Carrying size in those names is carrying idiosyncratic ADL risk;
price it in.

## The cross-exchange angle: getting clipped at a stale mark

The detail that opens an arbitrage is *price*: ADL closes you at the **previous mark
price**, not by sweeping the book. In a fast move, the previous mark *lags* the true
price. So a winning long that gets ADL'd is closed at a number below where the asset
actually is — the trader eats a "clip" of roughly

$$
\text{clip} \;\approx\; (\,p_\text{true} - p_\text{prev\_mark}\,)\times \text{closed size},
$$

the upside between the stale mark and reality, surrendered involuntarily. That's a
*quantifiable, predictable* cost, and predictable forced flow is the raw material of
cross-venue arbitrage:

- **Pre-hedge the flatten.** If you're long the crowded side on Hyperliquid and you can
  see HLP/insurance buffers thinning during a violent move, carry an *offsetting* leg on
  Binance or Bybit sized to your ADL-exposed notional. When Hyperliquid force-flattens
  your winner, your off-venue leg leaves you at your target net exposure instead of
  knocked flat at a stale price — you've converted an involuntary clip into a controlled,
  hedged exit.
- **Fade the mechanical dislocation.** A platform-wide ADL is a wave of *same-direction*
  forced closes hitting one venue's mark while the other venues print the real price. The
  basis between Hyperliquid's mark and the off-exchange spot/perp during the cascade is a
  mechanical, non-informational dislocation — exactly the kind a cross-exchange maker
  wants to provide liquidity into and collect as it reconverges.
- **Anticipate, don't chase.** Because the trigger stack (HLP drained → insurance drained
  → ADL) and the victim ordering (top of the leverage×profit queue) are both knowable
  ahead of time, the cascade is one of the rare crypto events you can *position before*
  rather than react to. The edge is in the seconds between "the buffers are gone" and "the
  queue fires."

## Why I care

I run market-making and liquidation bots on on-chain venues, and the recurring lesson is
the same one this writeup hands you for free: **on a venue, the rules of the risk engine
are part of the market, not the plumbing under it.** Hyperliquid's ADL queue is a
deterministic function of leverage and profit, computable by anyone, firing on a
published schedule. Treated as a hazard it's just a reason to be scared of perps. Treated
as what it is — a known, public, exploitable rule — it's a leverage limit you set on
yourself, a seniority play against the crowd, and a cross-exchange hedge you can arm
*before* the cascade instead of after. The work Ottersec did to pull it out of a stripped
binary is the hard part. Using it is the fun part.

*Code and charts: [`code/hyperliquid_risk_engine`](https://github.com/jothamteo/quant-research-blog/tree/main/code/hyperliquid_risk_engine). Source article: Ottersec, ["Auto Reverse-Engineering Hyperliquid's Risk Engine"](https://osec.io/blog/2026-06-22-hyperliquid-risk-engine/), 22 Jun 2026. The simulation here illustrates the mechanism — the verified ranking score, the resulting haircut concentration, and the seniority knob — on a synthetic cohort; it is not a reproduction of Ottersec's binary recovery, nor of Percolator's formal model, and the dollar figures are illustrative, not Hyperliquid's live book.*
