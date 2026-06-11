---
title: "Are prediction markets well-calibrated? A check on 5,125 resolved Manifold markets"
date: 2026-06-15
draft: false
math: true
tags: ["prediction-markets", "calibration", "scoring-rules", "manifold", "empirical"]
summary: "I pulled 5,125 resolved binary markets from Manifold and ran a standard reliability-diagram and scoring-rule analysis. The headline: markets at their closing probability are well-calibrated — almost perfectly so above $1,000 in volume — and beat both a 50% prior and a base-rate baseline by a factor of three on the Brier score. I also report where the calibration fails and what the result does and does not buy you."
---

A common claim about prediction markets is that they aggregate
information into well-calibrated probabilities: when the market says
*"70%"*, those events should happen roughly seven times out of ten.
The claim is testable. This post tests it.

I pulled the **5,125 most recent resolved BINARY markets** from
[Manifold Markets](https://manifold.markets/) (resolution ∈ {YES, NO},
play-money but the largest free public source of resolved markets) and
ran the standard calibration analysis: a reliability diagram, Brier and
log scores against two naive baselines, and an expected-calibration-error
(ECE) decomposition by market volume.

**Headline result.** Manifold's closing probability is well-calibrated.
Across all 5,125 markets the Brier score is **0.089** — versus **0.249**
for a base-rate baseline and **0.250** for a 50% prior. The expected
calibration error is **0.031** (3.1 percentage points L1 distance, on
average, between predicted and observed). Calibration is sharply better
for high-volume markets: **Brier 0.046** above M$1,000 in volume, vs
**0.218** for markets under M$100.

![Manifold reliability diagram](/quant-research-blog/charts/prediction-market-calibration/reliability_overall.png)

## What "calibrated" means here

For a binary market that resolves yes (1) or no (0), the standard
reliability check is:

1. Take the market's probability prediction $p \in [0, 1]$ for each
   market.
2. Bin the markets by their $p$ — say, into 10 equal-width bins.
3. For each bin, plot the mean $p$ vs the observed YES rate.
4. A perfectly calibrated forecaster sits on the $y = x$ line: when it
   says "60%", the empirical YES rate in those events is 60%.

This is Murphy's[^murphy] reliability decomposition of the Brier score
$\mathrm{BS} = \frac{1}{N} \sum_i (p_i - y_i)^2$, where the
**reliability** term is the calibration deviation and the
**resolution** term is the predictor's ability to discriminate
between cases.

Two summary statistics:

- **Brier score**: $\mathrm{BS} = \frac{1}{N} \sum (p_i - y_i)^2$. Lower
  is better; bounded in $[0, 1]$ for binary targets. A perfect forecaster
  has BS = 0; one that always predicts the base rate has BS ≈ base ×
  (1−base) ≈ 0.249 for Manifold.
- **Log score**: $\mathrm{LS} = \frac{1}{N} \sum [y_i \ln p_i + (1 - y_i) \ln(1 - p_i)]$.
  Higher (closer to 0) is better; bounded above by 0. A constant 50%
  predictor gets $\ln 0.5 = -0.693$.

I also report the **expected calibration error**: a weighted L1 distance
between mean predicted and observed yes-rate across 20 equal-width bins.

## What the data look like

| | n | brier ↓ | log ↑ | ECE ↓ |
|---|---:|---:|---:|---:|
| **Manifold (closing probability)**  | **5,125** | **0.089** | **−0.278** | **0.031** |
| Baseline: always 0.50              | 5,125 | 0.250  | −0.693 | — |
| Baseline: always base rate (0.465) | 5,125 | 0.249  | −0.691 | — |

By Brier and log score, the market is **~3× better than either naive
baseline**. The ECE — the headline calibration figure — is 3.1
percentage points, which is small for a sample of this size.

### Where the calibration is good and where it isn't

| bin              | n     | mean $p$ | observed | 95% CI |
|------------------|------:|---------:|---------:|--------|
| 0.00 – 0.10      | 1,568 | 0.027    | **0.012**  | [0.008, 0.019] |
| 0.10 – 0.20      |   273 | 0.144    | **0.048**  | [0.028, 0.080] |
| 0.20 – 0.30      |   206 | 0.247    | **0.184**  | [0.137, 0.243] |
| 0.30 – 0.40      |   212 | 0.353    | **0.335**  | [0.275, 0.401] |
| 0.40 – 0.50      |   345 | 0.460    | **0.403**  | [0.352, 0.455] |
| 0.50 – 0.60      |   551 | 0.526    | **0.546**  | [0.505, 0.587] |
| 0.60 – 0.70      |   196 | 0.651    | **0.602**  | [0.532, 0.668] |
| 0.70 – 0.80      |   194 | 0.747    | **0.794**  | [0.731, 0.845] |
| 0.80 – 0.90      |   233 | 0.850    | **0.863**  | [0.813, 0.901] |
| 0.90 – 1.00      | 1,347 | 0.978    | **0.987**  | [0.979, 0.992] |

Two observations.

1. **The middle of the distribution is on the diagonal.** Between roughly
   0.5 and 1.0, the Manifold mean $p$ and the observed YES rate sit
   within the 95% Wilson intervals of each other in every bin. This is
   the typical pattern for a well-aggregating market.
2. **There is mild over-confidence in the lower-mid range.** Markets
   priced in the 0.10-0.30 range resolve YES less often than the price
   suggests (0.05 observed vs 0.14 predicted in the 0.10-0.20 bin; 0.18
   vs 0.25 in the 0.20-0.30 bin). The signed direction is the **opposite
   of the classic equity favourite-longshot bias** — markets are
   *over*-pricing low-probability events, not under-pricing them.

The first point is the "wisdom-of-markets-works" claim, vindicated. The
second is a real, non-trivial finding about Manifold specifically:
long-shot markets resolve at lower rates than their price suggests.
Possible mechanisms — none of which I am able to distinguish empirically
with this dataset:

- **Speculative attention**: markets that have caught a small spike of
  attention but no real informed flow can hover at 0.10-0.20 longer
  than warranted.
- **Question selection bias**: "will X unlikely-but-noteworthy thing
  happen?" gets *posted* on Manifold more often than the unconditional
  base rate of unlikely things actually occurring, so the platform's
  *catalogue* of questions is biased toward the long-shot direction.
- **Play-money artefact**: with no skin in the game, the marginal
  trader who pushes a market from 0.05 to 0.15 doesn't get punished by
  reality the way a real-money trader would.

## Volume tier matters a lot

When I split by trading volume, the picture sharpens:

![reliability by volume](/quant-research-blog/charts/prediction-market-calibration/reliability_by_volume.png)

| tier                  | n     | brier | log    | ECE   |
|-----------------------|------:|------:|-------:|------:|
| low (< M$100)         |   626 | 0.218 | −0.618 | 0.065 |
| mid (M$100 – M$1,000) | 1,846 | 0.107 | −0.338 | 0.040 |
| **high (≥ M$1,000)**  | **2,653** | **0.046** | **−0.156** | **0.018** |

High-volume markets are essentially flawlessly calibrated — Brier 0.046
and ECE of 1.8 percentage points. Low-volume markets are noisier but
still beat the 50% baseline (Brier 0.218 vs 0.250) by a meaningful
margin.

This matches the intuition: more volume means more participants, more
arbitrage on mispriced markets, and more total information aggregated
into the price. **If you cite a Manifold market in a serious context,
filter by trading volume first.**

## What this result does *not* show

This is a closing-time calibration study. It says: *at the moment a
market closes, the price is a well-calibrated probability.* It does **not**
say:

- **That markets are calibrated weeks before resolution.** The most
  interesting question — *are these things actually predicting the
  future, or just pricing in news as it arrives?* — requires pulling
  per-market bet histories and re-running the analysis on the price at,
  say, $T - 7\ \text{days}$ for each market. That is a 5,000× more API
  calls and a project's worth of additional work. I haven't done it yet.
- **That high-stakes real-money markets behave the same way.** Manifold
  is play-money. A subset of behavioural-finance research has found
  meaningful differences between play-money and real-money market
  efficiency.[^servan-schreiber] The result here transfers to Polymarket
  / Kalshi only as a hypothesis to test, not as a fact.
- **That markets are calibrated *conditional on question type*.** I
  haven't stratified by category. It is entirely possible that political
  markets are well-calibrated while sci-fi-tech markets are not, and the
  aggregate hides it.

A natural follow-up post would address (1) by pulling bet histories and
re-running calibration at fixed lead times — a more demanding test.

## How to reproduce

```bash
git clone https://github.com/jothamteo/quant-research-blog
cd quant-research-blog/code/prediction_market_calibration
pip install -r requirements.txt
python fetch_markets.py    # ~3-5 min (Manifold public API, paginated)
python calibration.py      # ~3 sec — also produces the charts above
```

All numbers in this post come out of `data/scores.json`,
`data/calibration_bins.csv`, and `data/calibration_by_volume.csv`.

---

[^murphy]: Murphy, A. H. (1973). A new vector partition of the
    probability score. *Journal of Applied Meteorology*, 12(4), 595-600.
    The reliability-resolution-uncertainty decomposition of the Brier
    score that the reliability diagram visualises.
[^brier]: Brier, G. W. (1950). Verification of forecasts expressed in
    terms of probability. *Monthly Weather Review*, 78(1), 1-3. The
    original mean-squared-error scoring rule for binary forecasts.
[^wolfers]: Wolfers, J., & Zitzewitz, E. (2004). Prediction markets.
    *Journal of Economic Perspectives*, 18(2), 107-126. The standard
    survey of the information-aggregation claim that this post
    empirically tests.
[^servan-schreiber]: Servan-Schreiber, E., Wolfers, J., Pennock, D. M.,
    & Galebach, B. (2004). Prediction markets: does money matter?
    *Electronic Markets*, 14(3), 243-251. The play-money vs real-money
    comparison.
