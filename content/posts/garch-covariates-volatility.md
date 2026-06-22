---
title: "Beyond the résumé: do extra signals actually improve a volatility forecast?"
date: 2026-06-22
draft: false
math: true
tags: ["volatility", "garch", "forecasting", "equities", "reproducible-research"]
summary: "A GARCH model forecasts tomorrow's volatility from price history alone — the résumé. A recent paper argues you should add 'interview' signals like the VIX and realized vol. I tested that on 22 years of S&P 500 data: bolting the VIX onto GARCH barely helps (+0.3%), but a model built directly on realized volatility beats GARCH by 9.5% out-of-sample. The lesson isn't 'add covariates' — it's which signal, used how."
---

When a firm hires an analyst, the résumé is the starting point — grades, degrees,
prior roles. But nobody hires on the résumé alone. The interview, the references,
how they think on their feet: those signals, the ones that never make the page,
are usually what separate "looks great" from "actually good."

Volatility forecasting has the same shape. The workhorse model, **GARCH**, predicts
tomorrow's variance from the résumé only — yesterday's squared return and its own
past variance:

$$
\sigma_t^2 = \omega + \alpha\, r_{t-1}^2 + \beta\, \sigma_{t-1}^2
$$

A recent paper — *Deep Learning Enhanced Volatility Modeling with Covariates* (the
RECH-X model of Nguyen, Nguyen & Tran) — makes the natural argument: traders don't forecast risk from
returns alone — they watch the **VIX**, realized volatility, macro signals — so a
model should too. RECH-X wires a neural network and a pile of covariates into a
GARCH backbone and reports better forecasts.

I wanted the *economically* interesting part of that claim, stripped of the deep
learning: **does looking beyond returns actually help — and if so, which signal, and
how much?** So I ran the clean version on 22 years of S&P 500 data (2004–2026),
with transparent, hand-rolled models and nothing exotic. Everything's reproducible
from the
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/garch_covariates).

## The horse race

Four models, all forecasting daily variance one step ahead, fit on 2004–2017 and
judged **out-of-sample on 2018–2026** (2,127 trading days):

- **GARCH(1,1)** — the résumé-only baseline.
- **GARCH-X (VIX)** — GARCH plus yesterday's VIX (as an implied-variance term).
- **GARCH-X (realized vol)** — GARCH plus a Garman-Klass realized-variance estimate.
- **HAR-RV** — Corsi's model built *entirely* on realized volatility (a blend of
  yesterday's, last week's, and last month's), no returns-based GARCH at all.

I score them with **QLIKE**, the standard proper loss for variance forecasts
(lower is better), against a Garman-Klass realized-variance proxy.

![QLIKE bars](/quant-research-blog/charts/garch-covariates/qlike_bars.png)

| Model | OOS QLIKE | vs GARCH |
|---|:--:|:--:|
| GARCH(1,1) | 0.537 | — |
| GARCH-X (VIX) | 0.536 | **+0.3%** |
| GARCH-X (realized vol) | 0.535 | +0.5% |
| **HAR-RV** | **0.486** | **+9.5%** |

## The result, and the twist

The headline answer is "yes, extra signals help" — but **where** the help comes from
is the whole story, and it's not where you'd guess.

**Bolting the VIX onto GARCH does almost nothing — +0.3%.** That surprises people:
the VIX is *the* volatility signal, the market's own forecast. Why doesn't it move
the needle? Because GARCH already knows most of what the VIX knows. The VIX is, to a
first approximation, recent realized vol plus a risk premium — and GARCH is built
from recent squared returns. Hand a model information it already has and you get a
rounding error. The same goes for tacking realized vol on as a side term: +0.5%.

**But rebuild the model *around* realized volatility — HAR-RV — and it beats GARCH
by 9.5%.** Same family of information, radically different payoff. The lesson isn't
"add covariates to GARCH." It's that **realized volatility is the signal that
matters, and the way to use it is as the backbone of the model, not a garnish.**
GARCH infers volatility indirectly from the *sign-blind square* of one daily return;
HAR uses a direct, lower-noise measurement of how much the market actually moved.
Direct measurement beats inference.

![vol forecasts](/quant-research-blog/charts/garch-covariates/vol_forecasts.png)

You can see it in the forecasts: GARCH and the VIX-augmented version track each
other almost exactly, both reacting a beat *after* volatility moves; a realized-vol
model turns faster because it's reading the move directly rather than waiting for a
big squared return to feed through the recursion.

## What this says about the paper

It supports RECH-X's thesis — *information beyond returns improves volatility
forecasts* — but sharpens it. Most of the achievable gain here comes from **using
realized volatility well**, which a plain linear HAR already captures. The
incremental covariates (VIX, and in the paper oil/gold/FX) and the neural-network
nonlinearity are fighting over the *residual* after realized vol has done the heavy
lifting. That's worth knowing before you reach for an RNN: check what a transparent
HAR gives you first, because it may already be most of the win — at a fraction of
the complexity and with none of the interpretability lost.

## The bottom line

- **Looking beyond returns does help** — confirmed out-of-sample on the S&P 500.
- But **adding the VIX to GARCH is nearly free of value (+0.3%)**: it's information
  GARCH effectively already has.
- The real win — **+9.5%** — comes from **building on realized volatility directly**
  (HAR), i.e. choosing a better backbone, not adding a garnish.
- Before the deep-learning version, run the boring linear one: a HAR benchmark is
  the honest bar any fancy volatility model has to clear.

## Limitations (the honest list)

- **Daily-data realized-vol proxy.** I use Garman-Klass from OHLC, not intraday
  5-minute realized variance; the true-RV target is noisy, which compresses all the
  QLIKE differences (the *ranking* is robust, the exact percentages aren't).
- **Hand-rolled Gaussian QMLE GARCH**, not the paper's Bayesian/Sequential-Monte-Carlo
  estimation, and **no RNN** — by design; this isolates the value of the *covariates*,
  not the model class.
- **One index, one split** (S&P 500, train ≤2017). A multi-market panel — as in the
  paper — would test whether the VIX's redundancy holds everywhere (it likely
  weakens for markets where the local implied-vol index carries info U.S. returns
  don't).
- **Single covariate at a time.** I didn't test combinations or let HAR also take the
  VIX; the point here is the decomposition, not the kitchen sink.
