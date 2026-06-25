---
title: "A market maker doesn't get to choose its quoting rule — eight axioms force it"
date: 2026-06-24
draft: false
math: true
tags: ["market-making", "market-microstructure", "adverse-selection", "inventory-risk", "glosten-milgrom", "reproducible-research"]
summary: "Every market maker thinks it is choosing how to skew its quotes and how wide to set them. A recent paper (Feys, arXiv:2606.09454) proves it isn't: under eight natural axioms and six assumptions on inventory cost, there is exactly one admissible quoting rule, up to three parameters. The mid is forced linear in inventory; the spread is forced to split additively into an inventory piece and an adverse-selection piece; and the three parameters each fall out of a separate, decoupled moment of the observable quotes. I reproduce that forced shape in ~190 lines of numpy, and chase the corollary that actually belongs on a dashboard — a sharp phase transition where the market stops working entirely once toxic flow crosses a threshold."
cover:
  image: "/quant-research-blog/covers/axiomatic-market-making.png"
  alt: "axiomatic-market-making"
  relative: false
---

Ask a market maker how it quotes and you'll hear a list of *choices*: we skew the
mid against inventory, we widen when it's volatile, we pad the spread when flow
looks toxic. It sounds like a design space — a hundred knobs, a house style, an edge
in how you turn them. A new paper by Frank Feys,
[*Axiomatic Market Making*](https://arxiv.org/abs/2606.09454) (arXiv:2606.09454),
makes a quietly deflating claim: **there is no design space.** Write down eight
properties any reasonable quoting rule should have, add six mild assumptions about
how holding inventory costs you, and the rule is *forced* — pinned to a single
three-parameter family. Everything that feels like a choice is either one of those
three numbers or a violation of an axiom.

That's a strong statement, so it's worth seeing what survives the squeeze. I rebuilt
the *shape* the axioms force — not the 66-page uniqueness proof, but the canonical
[Avellaneda–Stoikov](https://www.math.nyu.edu/~avellane/HighFrequencyTrading.pdf) /
Glosten–Milgrom maker whose form the theorem pins down — and looked at the three
things a desk actually trades on. Everything below is reproducible from the
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/axiomatic_market_making):
plain numpy, no proprietary data.

## The mid is forced linear in inventory

The first thing the axioms kill is any cleverness in how you skew. The mid-quote —
the centre of your bid and ask — must be **linear in inventory**:

$$
\text{mid}(q) = \mu - \kappa\, q .
$$

You hold fair value $\mu$ when flat, and you shade the whole quote down by a constant
$\kappa$ for every unit of inventory you're long (and up when short), to coax the
next trade toward flattening you. No convexity, no regime-dependent curvature — a
straight line, slope $-\kappa$.

![inventory skew](/quant-research-blog/charts/axiomatic-market-making/inventory_skew.png)

Most makers already skew roughly like this because the Avellaneda–Stoikov
reservation price does. The paper's contribution isn't the formula — it's the word
*forced*. Linear skew isn't a convenient first-order approximation you could improve
on with a fancier model; it's the **only** skew consistent with the axioms. And
$\kappa$ is the first of the three free parameters. Crucially it's read straight off
one observable moment: regress your realised mid against your inventory and the slope
*is* $\kappa$. Nothing else in the rule touches that moment.

## The spread is forced to split into two independent pieces

The second result is the one I find genuinely useful. The half-spread $\delta$ —
how far your bid and ask sit from the mid — is forced to **decompose additively**:

$$
\delta = \underbrace{s_{\text{inv}}}_{\text{inventory / rebalancing}} \; + \; \underbrace{s_{\text{adv}}}_{\text{adverse selection}} .
$$

Two costs, added, not blended. $s_{\text{inv}}$ is what you charge to carry and
rebalance inventory; it's there even in a perfectly benign market. $s_{\text{adv}}$
is the [Glosten–Milgrom](https://www.sciencedirect.com/science/article/abs/pii/0304405X85900443)
tax: the premium you must charge because some fraction $\phi$ of your counterparties
know something you don't, and you lose to them on average. It scales with that
informed fraction and with volatility, $s_{\text{adv}} = \alpha\,\phi\,\sigma$.

![spread decomposition](/quant-research-blog/charts/axiomatic-market-making/spread_decomposition.png)

The payoff is in *how the two pieces sit in the data*. The inventory piece is the
intercept — the spread that survives as $\phi \to 0$. The adverse-selection piece is
the slope in $\phi$ (and in $\sigma$). They live in different moments of the
observable quoting rule, which is what the paper means by the three identifications
being **mutually decoupled**: you can estimate $s_{\text{inv}}$ from the benign-flow
intercept and the adverse-selection loading from the toxicity slope *separately*,
without a joint fit where one contaminates the other. For anyone who has tried to
disentangle "we're wide because inventory is heavy" from "we're wide because flow is
toxic" on a live book, a clean separation result is worth more than it sounds.

## The corollary that belongs on a dashboard: the freeze

The structural corollary is where this stops being elegant and starts being
operational. A competitive maker can't dodge adverse selection by quoting wider —
competition forces the spread *up to* break-even, where what you earn on uninformed
flow just covers what you bleed to informed flow. That break-even half-spread is
exactly the additive form from the last figure:

$$
\delta_{\text{be}}(\phi) = s_{\text{inv}} + \phi\,A, \qquad A = \beta\,\sigma \;\;(\text{the adverse move}).
$$

But uninformed traders aren't infinitely patient. They have a reservation
half-spread $\delta_{\max}$ — a transaction-cost budget past which they simply don't
trade. The market functions only while the spread you're *forced* to quote stays
under that ceiling. The instant $\delta_{\text{be}}(\phi)$ breaches $\delta_{\max}$,
uninformed flow leaves, you're alone in a room full of people who know more than you,
and the only rational quote is no quote. The market **freezes** — at a sharp critical
informed fraction

$$
\phi^{\ast} = \frac{\delta_{\max} - s_{\text{inv}}}{A} .
$$

![phase transition](/quant-research-blog/charts/axiomatic-market-making/phase_transition.png)

With the parameters in the code, $\phi^{\ast} = 0.375$. The right panel is the part that
matters: captured liquidity doesn't gently fade as flow gets more toxic — it falls,
then **cuts to zero discontinuously** at $\phi^{\ast}$. There's a functioning regime and a
frozen regime and almost nothing in between. That's the "sharp phase transition" the
paper proves separates the two, reproduced as a mechanism: not a model artefact but
the generic consequence of a forced break-even spread walking into a finite
tolerance.

## Why I care: this is a market-making kill-switch with a number on it

I run market-making bots — on Polymarket, and on Hyperliquid's HIP-4 venues. The
forced-form result is reassuring in a boring, load-bearing way: the parameterisation
I'd reach for anyway — linear inventory skew, a spread split into an inventory floor
plus an adverse-selection markup — isn't one modelling taste among many. It's the
*only* one consistent with the axioms, and its three parameters calibrate
independently from separate moments. That's permission to stop second-guessing the
functional form and spend the effort on estimating $\kappa$, $s_{\text{inv}}$ and the
adverse-selection loading cleanly.

The freeze is the part I'll actually wire up. $\phi$ — the informed-trader fraction —
is not abstract: it's toxicity, and toxicity is measurable. The standard estimator is
[VPIN](https://www.cmu.edu/tepper/faculty-and-research/assets/docs/vpin.pdf), and — in
a satisfying coincidence — the
[Polymarket-v1 dataset paper](https://arxiv.org/abs/2606.04217) from the *same*
research scan that surfaced this one finds that True VPIN is a strong predictor of
calibration degradation on Polymarket's order book. Put the two together and you get
a concrete rule rather than a vibe:

- Estimate $\phi$ live from order-flow toxicity (VPIN on volume buckets).
- Estimate your own $\phi^{\ast} = (\delta_{\max} - s_{\text{inv}})/A$ from the book — the
  tolerance, the inventory floor, the adverse move are all observable.
- When estimated $\phi$ approaches $\phi^{\ast}$, **pull quotes before the freeze, not
  after the bleed.** The transition is sharp, so there's no reward for lingering near
  it — the marginal liquidity you capture collapses while the adverse selection
  doesn't.

Most MM blow-ups I've seen aren't a slow grind; they're a maker that kept quoting
into flow that had already gone toxic, on the hope it would mean-revert. The axiomatic
picture says that hope is mispriced: past $\phi^{\ast}$ there is no spread that works, so
the correct action isn't "widen and pray," it's "stand down." Having a *number* for
where that line is — derived, not eyeballed — is the difference between a kill-switch
and a post-mortem.

*Code and charts: [`code/axiomatic_market_making`](https://github.com/jothamteo/quant-research-blog/tree/main/code/axiomatic_market_making). Paper: Feys, "Axiomatic Market Making," [arXiv:2606.09454](https://arxiv.org/abs/2606.09454). The reproduction here is the canonical Avellaneda–Stoikov / Glosten–Milgrom maker whose functional form the axioms pin down — it illustrates the mechanism, not the paper's uniqueness proof.*
