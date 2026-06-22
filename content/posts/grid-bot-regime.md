---
title: "When does a grid bot actually make money? It's a short-trend bet in disguise"
date: 2026-06-22
draft: false
math: true
tags: ["market-making", "grid-trading", "crypto", "mean-reversion", "backtest", "reproducible-research"]
summary: "Grid and market-making bots promise to 'profit from volatility.' I backtested one on 40,000 hours of BTC and bucketed every week by its trend strength. The truth: a grid bot is short the trend. It wins ~70% of weeks, but its return is a near-perfect inverted-cubic in trend strength — small grind in calm markets, brutal losses in strong ones — exactly the shape a recent statistical-mechanics paper predicts."
cover:
  image: "/quant-research-blog/covers/grid-bot-regime.png"
  alt: "grid-bot-regime"
  relative: false
---

Every grid-bot advert shows the same picture: a price sawtoothing up and down, and
a tidy little stack of profit harvested from each wiggle. "Make money from
volatility," it says. "Set it and forget it." It looks like a money printer that
only needs the market to *move*.

It is not a money printer, and "volatility" is the wrong word. A grid bot is a
**bet that trends mean-revert** — and when a trend refuses to revert, it hands back
weeks of grind in a few sessions. I wanted to put a number on *when* it works, so I
backtested one on **40,000 hours of Bitcoin** (Nov 2021 – Jun 2026) and sorted every
week by the one thing that actually decides its fate: trend strength. Everything is
reproducible from the
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/grid_bot_regime).

## A grid bot, stripped to its essence

Strip away the dashboard and a grid bot follows one rule: **buy as price falls, sell
as it rises.** It holds inventory that leans *against* the move — long after a drop,
short after a rally. In the fine-grid limit that's just a linear "fade" rule:

$$
I(p) = \text{clip}\!\left(-\alpha\,\frac{p-\text{centre}}{\text{centre}\cdot\text{band}},\; -\alpha,\; +\alpha\right)
$$

— maximally long at the bottom of its band, maximally short at the top, flat in the
middle. Its profit each step is simply *inventory × the next price move*, minus a
cost every time it trades:

$$
\text{PnL}_t = I_t\,(p_{t+1}-p_t)\;-\;\text{fees}
$$

Look at that and the whole character of the strategy falls out. If price oscillates
around the centre, the bot is long into dips and short into rallies and **pockets the
wiggle**. If price *trends*, the inventory pins to the band edge and the bot sits
there **losing on every further step in the same direction**. It's short the trend,
full stop.

I deploy a fresh grid every week (±10% band, 1bp per trade), and then ask the only
interesting question: how did each week's profit depend on that week's *regime*?

## The result: an inverted cubic in trend strength

Here is every one of 238 weeks — grid return against the week's trend strength
(signed, normalised by how much the price wiggled):

![return vs trend](/quant-research-blog/charts/grid-bot-regime/ret_vs_trend.png)

That shape is the entire post. The grid earns its best return — about **+2.4% on
deployed capital** — when trend strength is near zero (a choppy, going-nowhere
week). As the trend strengthens in *either* direction the return rolls over and
goes sharply negative, down past −15% in the most violent trends. It is a short
straddle drawn in trend-space.

It's worth pausing on *why that curve is a cubic*. The recent Schmidhuber
["trends, volatility & critical phenomena"](https://arxiv.org/abs/2606.20145) paper
models expected returns as a **cubic polynomial of trend strength** — mild trends
tend to persist, but extreme trends snap back. A grid bot is the mirror image of
that bet: it is *long* mean reversion, so its payoff inherits the same cubic shape,
flipped. The red fit is that cubic. We didn't impose it; BTC drew it.

## Bucketed: it wins most weeks and still goes nowhere

Sort the 238 weeks into trend-strength quartiles:

| Regime (trend strength) | Mean grid return / week |
|---|:--:|
| **Calm** (lowest) | **+2.14%** |
| Mild | +1.67% |
| Trending | +0.42% |
| **Strong** (highest) | **−4.16%** |

![return by regime](/quant-research-blog/charts/grid-bot-regime/ret_by_regime.png)

The grid is profitable in **69.7% of weeks** — it wins small, constantly, which is
exactly why the equity curve *feels* so reassuring and why the adverts look so good.
But the mean weekly return is essentially **zero**: the one-in-four "strong trend"
weeks, at −4.2% apiece, claw back the entire grind from the other three quarters.
This is the same brutal arithmetic as *selling* volatility — win often, lose big —
just expressed through inventory instead of options.

Two illustrative weeks make it visceral — a calm one the grid milks, and a trending
one that runs it over:

![two weeks](/quant-research-blog/charts/grid-bot-regime/two_weeks.png)

## The "grids love volatility" myth

Here's the part that catches people out. Surely a grid bot *wants* volatility — more
wiggle, more harvest? Bucket by realized vol instead of trend:

- Low vol +0.26% · Mid +0.07% · High +0.16% · **Extreme −0.45%**

The correlation of weekly return with volatility is only **−0.16** — weak and, if
anything, *negative* — versus **−0.78** with trend strength. Volatility barely
matters once you know the trend; what kills the grid is *directional* vol. And
that's not a coincidence: the same Schmidhuber paper shows **volatility rises in
strong trends** (especially down-trends). So the high-vol weeks the grid supposedly
craves are disproportionately the trending weeks that bury it. The bot doesn't want
volatility — it wants *chop*, and the market cruelly serves up the most vol exactly
when it's trending hardest.

## So when does it make money — and can you use that?

The honest answer: **a grid bot makes money in range-bound markets and only there.**
Its edge isn't a clever spacing or a magic setting — it's a regime bet you're making
whether you realise it or not. Which means the entire game is *regime selection*:
run it when the market is chopping, switch it off when a trend is underway.

That sounds easy and isn't — calling trends in real time is its own hard problem
(the Schmidhuber result says mild trends *persist*, so "it's trended a lot, it must
revert" is a good way to get run over). But it reframes what you should actually
work on:

- **Don't tune the grid; tune the on/off switch.** A trend filter (turn the grid
  off when |trend strength| is high) matters far more than spacing or band width.
- **Cap the inventory and respect it.** The −4% weeks become −20%+ weeks the moment
  you let the ladder keep adding into a trend on leverage. The bounded loss above
  *assumes* you stop at the band edge.
- **Judge it on the bad weeks, not the win rate.** 70% of weeks green is the
  seductive, meaningless number; the strong-trend tail is the whole P&L story.

## The bottom line

- A grid / market-making bot is **short the trend** — a mechanical mean-reversion
  bet, not a volatility harvester.
- On BTC its weekly return is a clean **inverted cubic in trend strength**: ~+2% in
  calm weeks, **−4%+ in strong trends**, averaging to roughly nothing.
- It **wins ~70% of weeks and still makes no money**, because the trend weeks pay
  for everything — the same win-small-lose-big shape as selling options.
- "Grids love volatility" is a myth: trend strength drives the P&L (−0.78), vol
  barely does (−0.16), and high vol tends to *arrive with* the trends that kill it.

## Limitations (the honest list)

- **Idealised grid.** I use the continuous linear-fade limit, not a discrete ladder
  with real queue position; fills are taken on hourly closes with a flat 1bp cost.
  This captures the *economics* (inventory leans against price; you pay turnover),
  not exact execution.
- **Inventory is capped at the band edge.** A real grid that keeps adding past its
  band — or runs on leverage — bleeds far more in trends, and can be liquidated; the
  bounded losses here are the *optimistic* case.
- **One asset, one configuration.** BTC, ±10% band, weekly redeploy. Wider bands
  bleed slower but capture less; the qualitative shape is robust, the exact numbers
  are not.
- **No borrow/funding cost** on the short side of the neutral grid, and no
  bid-ask beyond the 1bp fee — both flatter the calm-week returns.
- **Regime is measured in-sample.** Knowing a week was "calm" *after* the fact is
  easy; the hard, unsolved part — trading on it — is exactly the trend filter above.
