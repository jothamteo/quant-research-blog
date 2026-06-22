---
title: "A practical guide to event studies: the linear algebra and statistics behind the market model"
date: 2026-06-11T11:00:00+08:00
draft: false
math: true
tags: ["methodology", "event-study", "linear-algebra", "statistics", "explainer"]
summary: "The Brown-Warner market model is the workhorse of event-study research, but it is often presented as a recipe rather than as a piece of statistics. This post walks through the linear algebra and the statistics behind it — from the per-event OLS to the cumulative-abnormal-return test statistic — and uses a worked synthetic example to show the methodology recovering a planted effect."
cover:
  image: "/quant-research-blog/covers/event-study-methodology.png"
  alt: "event-study-methodology"
  relative: false
---

A marketing manager runs a big campaign in March. Sales jump 10%. Did the
campaign work? You can't answer from that number alone — March was also the start
of spring, a competitor had a stockout, and the whole category was up anyway. To
give the campaign credit you need a baseline: what would sales have done *without*
it? The campaign's real effect is the part of the jump your baseline can't
explain.

That question — how much of a move is genuinely due to the event, versus what
would have happened regardless — is the entire problem an **event study** solves.
In finance the "event" is an earnings surprise, an index addition, a rating
change; the "sales jump" is the stock's return around it; and the baseline is how
the stock normally moves with the market. Get the baseline right and you can put
a number, and a confidence interval, on the event's true effect.

In an earlier [post](/quant-research-blog/posts/sp500-index-addition-premium/) I
leaned on this machinery to ask whether the S&P 500 index-addition premium has
disappeared — but I took the method on trust. This post opens the box. By the
end you'll know exactly what you're claiming when you report a cumulative
abnormal return ("CAR") with a *t*-statistic: what hypothesis it tests, what it
assumes, and where those assumptions bite. We finish with a worked example where
the method recovers a planted +50 basis-point effect out of pure noise — the
cleanest way to prove a recipe actually works.

## 1. The market model in matrix form

Pick an event date for stock $i$ and let $\tau = 0$ be the event day in
event-time. Pick an *estimation window* $\tau \in [T_1, T_2]$ — typically
something like $[-120, -21]$ trading days before the event. Let
$N = T_2 - T_1 + 1$ be the number of days in the estimation window. The
market model says that over the estimation window,

$$
\mathbf{r}_i = \mathbf{X} \boldsymbol{\beta}_i + \boldsymbol{\varepsilon}_i,
$$

where

$$
\mathbf{r}_i \in \mathbb{R}^N \;\; \text{(stock returns)}, \qquad
\mathbf{X} = \begin{bmatrix} 1 & r_{m,T_1} \\ 1 & r_{m,T_1+1} \\ \vdots & \vdots \\ 1 & r_{m,T_2} \end{bmatrix} \in \mathbb{R}^{N \times 2},
$$

$\boldsymbol{\beta}_i = (\alpha_i, \beta_i)^\top$ is the per-stock intercept
and market beta, and $\boldsymbol{\varepsilon}_i$ is the residual — the part
of stock $i$'s return that the broad market cannot explain.

The classical OLS assumptions are:

- $\mathbb{E}[\boldsymbol{\varepsilon}_i \mid \mathbf{X}] = \mathbf{0}$
- $\mathrm{Var}(\boldsymbol{\varepsilon}_i \mid \mathbf{X}) = \sigma_i^2 \mathbf{I}_N$
  (homoskedastic, no autocorrelation in residuals over the estimation window)
- $\boldsymbol{\varepsilon}_i \mid \mathbf{X} \sim \mathcal{N}(\mathbf{0}, \sigma_i^2 \mathbf{I}_N)$
  (Gaussian residuals — for the finite-sample *t*-distribution result)

These assumptions are the load-bearing ones for everything below. They are
not exactly true. They are approximately fine for daily returns over a
100-day window if you stay away from event days for the *other* stock's
events, which is why event-study windows are kept short and estimation
windows are kept clear of the event.

### 1.1 The OLS estimator

The minimiser of the sum of squared residuals
$\lVert \mathbf{r}_i - \mathbf{X} \boldsymbol{\beta}_i \rVert^2$ is the
standard normal-equations solution:

$$
\hat{\boldsymbol{\beta}}_i = (\mathbf{X}^\top \mathbf{X})^{-1} \mathbf{X}^\top \mathbf{r}_i.
$$

The conditional variance of the estimator, under the OLS assumptions
above, is

$$
\mathrm{Var}(\hat{\boldsymbol{\beta}}_i \mid \mathbf{X}) = \sigma_i^2 (\mathbf{X}^\top \mathbf{X})^{-1}.
$$

We estimate $\sigma_i^2$ with the usual unbiased residual variance, using
$N - 2$ degrees of freedom because we estimated two parameters
($\hat\alpha_i, \hat\beta_i$):

$$
\hat\sigma_i^2 = \frac{1}{N - 2} \sum_{\tau = T_1}^{T_2} \big(r_{i,\tau} - \hat\alpha_i - \hat\beta_i \, r_{m,\tau}\big)^2.
$$

This is *all* the linear algebra you need for the per-event regression.
The rest is bookkeeping for what happens in the **event window**.

## 2. Abnormal returns in the event window

Now switch from estimation window to event window. Let
$\tau \in [\tau_1, \tau_2]$ — say $[-10, +20]$. The market-model **abnormal
return** for stock $i$ on event-day $\tau$ is

$$
\widehat{\mathrm{AR}}_{i,\tau} = r_{i,\tau} - \hat\alpha_i - \hat\beta_i \, r_{m,\tau}.
$$

Read in English: it is the part of the stock's event-window return that
the broad market does *not* explain, with the relationship between stock
and market calibrated on a clean pre-event window.

### 2.1 Variance of an abnormal return

This is the step that students of the methodology most often skip. The
naive variance of $\widehat{\mathrm{AR}}_{i,\tau}$ is $\sigma_i^2$ — but
that ignores that we used estimated $\hat\alpha_i, \hat\beta_i$ rather
than the truth. Plugging in the OLS estimator gives the exact conditional
variance:

$$
\mathrm{Var}\big(\widehat{\mathrm{AR}}_{i,\tau} \mid \mathbf{X}, r_{m,\tau}\big) = \sigma_i^2 \cdot \left[ 1 + \mathbf{x}_\tau^\top (\mathbf{X}^\top \mathbf{X})^{-1} \mathbf{x}_\tau \right],
$$

where $\mathbf{x}_\tau = (1, r_{m,\tau})^\top$. For a 100-day estimation
window and typical daily market returns, the bracket is very close to 1
— usually $1.01$ to $1.03$. In a low-effort study you can ignore it; in a
careful study you should compute it.

### 2.2 The cumulative abnormal return

The CAR over event-window sub-window $[a, b]$ is

$$
\widehat{\mathrm{CAR}}_{i,[a,b]} = \sum_{\tau = a}^{b} \widehat{\mathrm{AR}}_{i,\tau}.
$$

If we *additionally* assume that the event-window residuals
$\varepsilon_{i,\tau}$ are **independent across $\tau$** — which is roughly
true if you are using daily returns and there is no microstructure
contamination — then the variance of the CAR is the sum of the
variances:

$$
\mathrm{Var}\big(\widehat{\mathrm{CAR}}_{i,[a,b]}\big) \approx L \cdot \sigma_i^2 \cdot \overline{c},
$$

with $L = b - a + 1$ and $\overline{c}$ the average of the brackets from
§2.1 over the window. In practice $\overline{c} \approx 1$ for any
reasonable estimation window length and the variance is well-approximated
by $L \sigma_i^2$.

## 3. The test statistic

We want to test the null

$$
H_0: \mathbb{E}\big[\widehat{\mathrm{CAR}}_{i,[a,b]}\big] = 0.
$$

The standardised statistic — what Brown and Warner call the **SCAR** — is

$$
\mathrm{SCAR}_i = \frac{\widehat{\mathrm{CAR}}_{i,[a,b]}}{\sqrt{L} \cdot \hat\sigma_i}.
$$

Under the null and the assumptions in §1, $\mathrm{SCAR}_i$ is distributed
as a Student-*t* with $N - 2$ degrees of freedom. With $N = 100$ this is
indistinguishable from a standard normal at the relevant tail (the 95%
two-sided critical values are 1.984 vs 1.96).

### 3.1 Cross-sectional aggregation

In practice we have *many* events and we want a *portfolio-level*
statement: across all $M$ events, is the average CAR significantly
different from zero? Under the assumption that the per-event CARs are
**independent of each other** (i.e. the events are sufficiently
non-overlapping in calendar time) the cross-sectional test is the
straightforward one:

$$
t = \frac{\overline{\widehat{\mathrm{CAR}}}}{S_{\widehat{\mathrm{CAR}}} / \sqrt{M}},
$$

where the average and standard deviation are taken across events. For
large $M$ this is asymptotically normal. The S&P 500 index-addition study
in the earlier post used this form with $M = 22$ pre-2010 vs $M = 182$
post-2010 events.

This **does** break down when events cluster in time — for instance, if
you study reactions to Fed rate decisions, every event happens on a day
when the rest of the cross-section is *also* reacting to the same
information. The Boehmer-Musumeci-Poulsen (1991) correction[^bmp1991] is
the standard fix; it deflates the test statistic by the cross-sectional
standard deviation of the *event-day* abnormal returns, capturing the
event-induced variance increase.

## 4. Worked example — recovering a planted effect

Enough theory. Let's check the methodology actually does what it claims to
do by simulating a known data-generating process and running the recipe.

```python
import numpy as np
import pandas as pd

rng = np.random.default_rng(0)

N_EST = 100          # estimation window length
EVT   = np.arange(-5, 11)
M     = 200          # number of events
TRUE_BETA = 1.2
TRUE_SIGMA = 0.012   # ~1.2% daily idiosyncratic vol
ABNORMAL_DAY = 0     # planted effect on event-day 0
TRUE_AR = 0.0050     # +50 bps

cars = []
for _ in range(M):
    r_m_est = rng.normal(0, 0.01, N_EST)
    eps_est = rng.normal(0, TRUE_SIGMA, N_EST)
    r_i_est = TRUE_BETA * r_m_est + eps_est

    # OLS market model
    X = np.column_stack([np.ones(N_EST), r_m_est])
    beta_hat, *_ = np.linalg.lstsq(X, r_i_est, rcond=None)
    alpha_hat, beta_hat_ = beta_hat
    resid = r_i_est - X @ beta_hat
    sigma_hat = resid.std(ddof=2)

    # Event window
    r_m_evt = rng.normal(0, 0.01, len(EVT))
    eps_evt = rng.normal(0, TRUE_SIGMA, len(EVT))
    r_i_evt = TRUE_BETA * r_m_evt + eps_evt
    # Plant the abnormal return on day 0
    r_i_evt[EVT == ABNORMAL_DAY] += TRUE_AR

    ar = r_i_evt - (alpha_hat + beta_hat_ * r_m_evt)
    cars.append({
        "car_0":   ar[EVT == 0].sum(),
        "car_0_3": ar[(EVT >= 0) & (EVT <= 3)].sum(),
    })

cars = pd.DataFrame(cars)
print(f"mean CAR on day 0:      {cars['car_0'].mean()*1e4:+.2f} bps "
      f"  (planted: {TRUE_AR*1e4:+.0f} bps)")
print(f"mean CAR over [0, +3]:  {cars['car_0_3'].mean()*1e4:+.2f} bps")
# Cross-sectional t-stat
import scipy.stats as st
t = cars['car_0'].mean() / (cars['car_0'].std(ddof=1) / np.sqrt(M))
print(f"cross-sectional t for day-0 CAR: {t:.2f}  "
      f"(two-sided p = {2*(1-st.norm.cdf(abs(t))):.4f})")
```

Running this (with `seed = 0` for reproducibility) gives

```
mean CAR on day 0:      +37.23 bps   (planted: +50 bps)
mean CAR over [0, +3]:  +42.84 bps
cross-sectional t for day-0 CAR: 4.66  (two-sided p = 0.0000)
```

The estimator recovers the planted effect at the right sign and order of
magnitude — it slightly under-estimates the headline $+50$ bps as $+37$
bps on this single seed. That is *not* a methodological flaw, it is sampling
variability: the standard error of a 200-event average with
$\hat\sigma_i \approx 1.2\%$ is roughly
$0.012 / \sqrt{200} \approx 0.085\%$, i.e. about 8 bps. The observed $-13$
bps deviation from the planted truth is well within $\pm 2$ standard errors.

The cross-sectional *t* of $4.66$ is comfortably above any conventional
threshold; the *p*-value is essentially zero. This is exactly what we should
see when there is a real, properly identified effect of $+50$ bps in $M = 200$
events.

What does the methodology look like when the effect is **zero**? Re-run
with `TRUE_AR = 0.0`:

```
mean CAR on day 0:      -12.77 bps   (planted: +0 bps)
mean CAR over [0, +3]:  -7.16 bps
cross-sectional t for day-0 CAR: -1.60  (two-sided p = 0.1104)
```

The null is correctly *not* rejected at the 5% level. The mean is $-13$ bps
— a coincidence of the single seed; under repeated experiments the
distribution of the day-0 CAR mean is centred on zero and has standard
error of $\approx 8$ bps. This is the most important sanity check: under
repeated experiments with no real effect, the test must reject only at
the 5% type-I rate. If your event-study code rejects *too often* under the
null, it is broken.

## 5. Common mistakes

A non-exhaustive list of the failure modes I've seen most often in
practice — and that are easy to introduce silently.

1. **Including the event window in the estimation window.** The event-day
   abnormal return *is* a residual; if you let it contribute to
   $\hat\sigma_i^2$, you make the test too conservative.

2. **Using arithmetic returns when you mean log returns (or vice versa)
   without saying.** For 1-day horizons it makes almost no difference; for
   the CAR over a 10-day window it can shift the mean by tens of basis
   points. Pick one and document it.

3. **Standardising by $\sigma_i^2$ rather than $L \cdot \sigma_i^2$.**
   Forgetting the $\sqrt{L}$ inflation in the denominator of $\mathrm{SCAR}$
   is the single most common arithmetic error.

4. **Using a market index that *includes* the stock you're studying.** If
   you're studying S&P 500 *deletions* and you use the S&P 500 itself as
   the benchmark, you've contaminated the regression — the deleted stock's
   own movement is in the market return on the estimation window. Use a
   sector-matched portfolio, an equal-weight index, or a benchmark with
   the studied stocks excluded.

5. **Clustered events without the BMP correction.** When 50 firms react to
   the *same* Fed meeting, the per-event CARs are correlated. Treating
   them as independent inflates your *t*-statistic by the square root of
   the within-cluster correlation factor. For non-clustered firm-specific
   events (earnings announcements on different days, index additions
   spread across the year) the naive *t* is fine.

6. **Event-induced variance change.** If the event itself increases
   short-term volatility — e.g. announcements, regulatory actions, M&A
   leaks — the event-window variance is larger than $\hat\sigma_i^2$ would
   predict, and your *t* is biased upward. This is exactly what BMP
   corrects for. Modern practice often skips it because the effect is
   usually mild and the correction reduces power; document the choice.

## 6. When *not* to use a market-model event study at all

The methodology assumes that **most** of the daily return variation comes
from a single factor — the market — and that the residual is small,
unbiased, and approximately Gaussian. That assumption fails for:

- **Small-cap or illiquid stocks** whose returns have only weak market
  beta and strong idiosyncratic non-Gaussian tails.
- **Cryptocurrency events**, where there is no clean "market" return and
  the residuals are heavy-tailed.
- **Multi-day reaction events** where the relevant CAR window is so long
  that other firm-specific news contaminates it.
- **Cases with factor-exposure shifts** triggered by the event itself
  (e.g. spin-offs, capital-structure changes) where $\hat\beta_i$
  estimated on the pre-event window no longer applies to the post-event
  data.

For those cases the right answer is a different methodology — matched
control portfolios, calendar-time portfolios, or panel regressions with
event-window indicators — *not* a more aggressive market-model event
study.

---

## TL;DR

- The market model is an OLS regression on a clean pre-event window.
- The abnormal return is the event-window residual implied by that
  regression.
- The CAR over a sub-window is just the sum of those residuals.
- The variance of the CAR is roughly $L \cdot \sigma_i^2$ (with a small
  bracket correction for the use of $\hat\beta_i$ rather than the truth).
- The standardised statistic is *t*-distributed under the null.
- The cross-sectional test averages CARs across non-overlapping events.
- BMP corrects for event-day variance inflation when events cluster.
- You can verify the recipe works by planting a known effect into
  simulated data — which is the cleanest sanity check there is.

---

[^bw1985]: Brown, S. J., & Warner, J. B. (1985). Using daily stock
    returns: the case of event studies. *Journal of Financial Economics*,
    14(1), 3-31.
[^bmp1991]: Boehmer, E., Musumeci, J., & Poulsen, A. B. (1991). Event-
    study methodology under conditions of event-induced variance.
    *Journal of Financial Economics*, 30(2), 253-272.
[^mackinlay]: MacKinlay, A. C. (1997). Event studies in economics and
    finance. *Journal of Economic Literature*, 35(1), 13-39. The
    methodology survey most often cited as the practitioner reference.
