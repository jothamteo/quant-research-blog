---
title: "Can LLM forecasters actually profit on prediction markets? Accuracy is the easy part"
date: 2026-06-26
draft: false
math: true
tags: ["prediction-markets", "llm", "forecasting", "market-microstructure", "reproducible-research"]
summary: "Frontier LLMs now forecast about as accurately as good humans — so the obvious next step is to point one at Polymarket and print money. A recent paper (Beyond Accuracy: Can LLM Forecasters Profit on Prediction Markets?) shows why that doesn't follow. Using a real archive of 145,819 Polymarket markets to set the stage, I reproduce the three forces that pry profit apart from accuracy: you're paid for beating the price not the truth, the spread taxes every trade, and the markets you most disagree with are adversely selected. Reproducible numpy."
cover:
  image: "/quant-research-blog/covers/llm-forecaster-profit.png"
  alt: "llm-forecaster-profit"
  relative: false
---

Here is the pitch you've heard a hundred times since LLMs got good at forecasting:
models now hit roughly human-expert accuracy on "will X happen?" questions, prediction
markets pay you for answering exactly those questions, so wire one to the other and
collect. A recent paper, *Beyond Accuracy: Can LLM Forecasters Profit on Prediction
Markets?* ([OpenReview](https://openreview.net/forum?id=TSA5kRUKZv)), takes that pitch
seriously and finds the obvious-looking step — accuracy → profit — is where it breaks.

I wanted to see the mechanism for myself, grounded in a real market. I have a local
archive of **145,819 Polymarket markets** (39,271 of them resolved binary Yes/No
questions). Everything qualitative below is reproducible from
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/llm_forecaster_profit);
the experiment is a self-contained Monte-Carlo, calibrated to that archive's real
structure.

## First, why "accuracy" is a trap

Start with one number from the real data. Of those 39,271 resolved binary markets,
**only 30% resolved YES** — 70% resolved NO. That makes sense once you read a few:
prediction markets are full of "Will [specific unlikely thing] happen by [date]?",
and most specific things don't.

That single fact wrecks accuracy as a metric. A forecaster that ignores every question
and robotically answers "NO, 0%" is **70% accurate** out of the gate. It knows nothing,
predicts nothing, and would beat a careless reading of many "our LLM was 68% accurate!"
headlines. Accuracy on a base-rate-skewed universe is nearly free, which is the first
clue that it can't be what separates a profitable bot from a broke one.

So let's measure the thing that actually matters — money — and watch it come apart from
accuracy.

## Force 1: you're paid for beating the price, not the truth

The market price already *is* a forecast — an aggregate of everyone who showed up with
an opinion and capital. To profit you don't have to be accurate in absolute terms; you
have to be *more accurate than the price*, in the right direction, on the markets you
actually trade. That's a completely different bar.

I simulate a universe of binary markets with the real 30/70 base rate. The market price
is an efficient-but-imperfect estimate of each market's true probability; the LLM is
another estimate whose skill I dial from "noisy" to "perfect." Then I plot two things as
the LLM gets smarter: its **accuracy edge over the market** (Brier), and its **net P&L**
after paying to trade.

![accuracy vs profit](/quant-research-blog/charts/llm-forecaster-profit/accuracy_vs_profit.png)

Accuracy improves smoothly and gracefully as the model sharpens. Profit does not. P&L
stays **underwater across the entire region** where the LLM is anything less precise than
the market itself, and only claws to zero right around the point where it finally *matches*
the market's own accuracy. Being a good forecaster in absolute terms — better than the
"always NO" baseline, better than most humans — lands you nowhere near profitability,
because the price you're trading against is already at least as good as you are.

## Force 2: the spread taxes every trade

The chart above already includes a trading cost, and it's doing a lot of work. Prediction
markets are not tight: crossing the bid-ask on Polymarket commonly costs a few cents
round-trip, which is enormous when the *entire* edge of a good forecast over the price is
itself a couple of cents.

Take a forecaster that genuinely beats the market — sharper than the price, real positive
edge before costs — and sweep only the spread:

![spread hurdle](/quant-research-blog/charts/llm-forecaster-profit/spread_hurdle.png)

At zero spread it makes money. By the time the round-trip cost reaches the range real
Polymarket books actually quote, the edge is gone and the P&L crosses into the red. The
forecaster didn't get worse; the *market got more expensive to access than the edge is
wide.* This is the quiet killer of most "my bot is well-calibrated" threads — calibration
is computed on paper, P&L is computed after the spread, and the spread routinely exceeds
the edge.

## Force 3: the markets you trade are adversely selected

The subtlest force, and the one that turns a thin edge into a negative one. You don't
trade every market — you trade the ones where you *most disagree* with the price. But
disagreement has two sources: cases where you genuinely know better, and cases where
*you're* the one who's wrong. By selecting the biggest disagreements, you scoop up both —
and the bigger your own error, the more of that pile is just you being confidently wrong.

So the edge you *think* you have going in is systematically larger than the edge you
*realise* coming out:

![adverse selection](/quant-research-blog/charts/llm-forecaster-profit/adverse_selection.png)

In the simulation, a forecaster that perceives a ~5-cent edge on the markets it picks
realises only about ~2 cents once outcomes land — better than half the apparent edge
evaporates, purely from selecting on disagreement. The right panel is the same point from
the accuracy side: the LLM's overall accuracy (82%) barely moves on the subset it chooses
to trade, even though those are exactly the markets where the price disagrees with it most
and is often disagreeing for a *reason*. The trades are the hard markets, not the easy
ones, and "82% accurate overall" tells you almost nothing about them.

## So — can they profit?

Sometimes, at the frontier, in the right markets, net of everything — which is a much more
demanding sentence than "the model is accurate." The paper's contribution is to hold those
apart cleanly, and the mechanism reproduces from three forces a desk already respects:

- **Accuracy is priced in.** You earn the *difference* between your forecast and the
  market's, and that difference is small precisely because prediction markets aggregate
  well. Absolute accuracy — the thing the benchmarks report — is the wrong number.
- **The spread is the hurdle rate.** On PMs it's often wider than the edge. The first
  question for any forecasting-bot pitch isn't "how accurate?" but "how wide is the book,
  and how much of it do you have to cross?"
- **Disagreement is adverse selection.** The markets you trade are the ones where you're
  most confident *and* most likely wrong. Realised edge < perceived edge, always; size and
  threshold accordingly, or the selection eats you.

None of this says LLM forecasters are useless — it says forecasting accuracy and trading
profit are different products, and the benchmark everyone quotes measures the first while
implying the second. The version I'd actually run leans the same way every result here
points: trade only where the edge clears the spread *with margin*, treat a high
disagreement as a yellow flag rather than a green light, and judge the model on realised
P&L net of the book — never on its Brier score.

*Code and charts: [`code/llm_forecaster_profit`](https://github.com/jothamteo/quant-research-blog/tree/main/code/llm_forecaster_profit). Paper: "Beyond Accuracy: Can LLM Forecasters Profit on Prediction Markets?" ([OpenReview](https://openreview.net/forum?id=TSA5kRUKZv)). The 145,819-market figures are real (a local Polymarket archive); the accuracy→profit experiment is a self-contained simulation of the mechanism — no live LLM calls and no look-ahead — calibrated to that archive's base rate, not a reproduction of the paper's measured returns.*
