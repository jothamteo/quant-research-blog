---
title: "Has the S&P 500 index-addition premium disappeared? A reproducible event study"
date: 2026-06-11
draft: false
math: true
tags: ["event-study", "equities", "index-effects", "reproducible-research"]
summary: "The classic 'index-addition premium' — the run-up in a stock's price in the days before it joins the S&P 500 — has been documented for decades. I replicate it on 204 events from 2000-2022 using a Brown-Warner market-model event study, and find that it has compressed to essentially zero in the post-2010 era."
cover:
  image: "/quant-research-blog/covers/sp500-index-addition-premium.png"
  alt: "sp500-index-addition-premium"
  relative: false
---

Imagine you knew, a week in advance, that a buyer was about to walk into the
market — one who *had* to buy a particular stock, in size, regardless of price.
Not because they think it's cheap, but because a rule says they must. What would
you do?

You'd probably buy it first, and sell it to them when they show up.

That, in one sentence, is the **index-addition premium**. When S&P announces
that a stock is joining the S&P 500, every index fund tracking the index becomes
a forced buyer on the day the change takes effect — they have to hold the stock,
at whatever price the market sets. For years, the academic literature documented
exactly what you'd expect: the price ran up in the days *before* inclusion, and
the index funds paid that premium when they finally bought.[^petajisto] The
most-cited estimates put the run-up at **3-8%** in the 1990s and early
2000s.[^chen][^denis] That's a real, recurring cost paid by anyone who owns an
index fund.

So here's the honest question: **is it still there?** A pattern that obvious,
that well-documented, and that profitable to front-run is exactly the kind of
thing markets tend to compete away. Let's check.

I ran a standard Brown-Warner market-model event study[^brown_warner] on **204
S&P 500 additions between 2000 and 2022**, using only public data and free Python
tooling. The full code is on
[GitHub](https://github.com/jothamteo/quant-research-blog/tree/main/code/sp500_index_addition_premium)
— you can rerun every number in this post yourself.

**The short version.** The run-up over the 5 trading days ending on inclusion
averaged **+325 basis points before 2010** but **−21 basis points after 2010**.
That difference — 346 bps — is statistically significant (t = 3.02, p = 0.005).
The premium hasn't just shrunk. It's gone.

![CAR run-up by era](/quant-research-blog/charts/sp500-addition-premium/car_runup_by_era.png)

## How I measured it

The tricky part of a claim like "the stock ran up 3%" is the obvious follow-up:
*ran up compared to what?* Over any given week the whole market drifts around,
and a stock that happens to get added to the index might have been rising anyway.
So before we can say a move is *abnormal*, we need a baseline for what's normal.

That baseline is the **market model** — and despite the fancy name, the idea is
simple. On a normal day, a stock mostly just rides the broad market, plus a bit
of its own wiggle. If the S&P is up 1% and a particular stock tends to move about
1.2-for-1 with it, then "expected" is roughly +1.2% that day; anything beyond
that is the stock doing something of its own. Every stock has its own personal
relationship to the market — some amplify its moves, some barely budge — so the
first step is to *measure* that relationship for each one.

The way you measure it is a regression: fit the straight line that best relates
the stock's daily return to the S&P 500's daily return, using a clean window of
data from *before* the event — here, the trading days from $[t-120, t-21]$, i.e.
the four-ish months leading up to it but stopping well short of the action:

$$
r_{i,\tau} = \alpha_i + \beta_i \, r_{m,\tau} + \varepsilon_{i,\tau}, \quad \tau \in [-120, -21]
$$

In plain terms: this regression learns how the stock normally moves with the
market. Once we know that, the **abnormal return** on any day is just the part of
the stock's move the market *doesn't* explain — the bit that's specific to the
stock. I compute it across the event window $[-10, +20]$:

$$
\mathrm{AR}_{i,\tau} = r_{i,\tau} - \big(\hat\alpha_i + \hat\beta_i \, r_{m,\tau}\big)
$$

and **cumulative abnormal returns** over various sub-windows $[a, b]$:

$$
\mathrm{CAR}_{i,[a,b]} = \sum_{\tau = a}^{b} \mathrm{AR}_{i,\tau}
$$

Averaging $\mathrm{CAR}_{i,[a,b]}$ across the $N$ events in an era and taking the
standard error of the mean as $\hat\sigma / \sqrt{N}$ gives the per-era estimate
and confidence intervals. A Welch *t*-test compares the pre-2010 and post-2010
means. All log returns; no overlapping-event correction (the events are sparse
enough that this is a minor concern, and the per-event regressions are
independent by construction).

### Sample

- **Source.** Wikipedia's `List_of_S&P_500_companies` "Selected changes" table,
  parsed with `pandas.read_html`. Effective dates 2000-01-01 through 2022-12-31.
- **Prices.** Daily adjusted close from Yahoo Finance via `yfinance`.
- **Filters.** Events with `|AR| > 50%` on any single event-window day were
  dropped as corporate-action artefacts (1 event: CBE in 2011-11). Events with
  fewer than 60 valid estimation-window observations were dropped (26 events).
  Tickers that returned empty from Yahoo (delisted, renamed, M&A) were skipped
  (79 events). **Final sample: 204 events.**

By era (and the count is honest — pre-2010 is a small sample because S&P 500
membership was relatively stable in the early-2000s):

| era       | n   | CAR$_{[-5,0]}$ (bps) | std-err (bps) |
|-----------|----:|---------------------:|--------------:|
| 2000-2004 |   4 |              **+28** |          ±81  |
| 2005-2009 |  18 |             **+391** |         ±123  |
| 2010-2014 |  45 |              **−89** |          ±77  |
| 2015-2019 |  93 |              **−18** |          ±51  |
| 2020-2022 |  44 |              **+44** |         ±126  |

The 2005-2009 bar is large and statistically reliable; the post-2010 eras all
sit on top of zero.

## The cumulative path tells the whole story

Plotting the per-day average AR cumulatively from $t = -10$ to $t = +20$:

![cumulative AR path](/quant-research-blog/charts/sp500-addition-premium/car_path.png)

Pre-2010, the typical event built a clear run-up that peaked just after the
effective date — exactly the textbook shape. Post-2010, the path is essentially
flat through the effective date and drifts mildly negative afterwards. There is
nothing left to capture by the time index funds buy on $t=0$, because everyone
who was going to has already bought between announcement and effective.

## So why did it vanish?

The honest answer is that a free lunch this well-advertised was never going to
last. Three forces the literature keeps coming back to:

1. **Anticipated demand has been arbitraged out.** S&P announces additions
   typically 5-7 trading days before the effective date. That is more than
   enough time for arbitrageurs (and the index funds themselves, via
   pre-effective transition trades) to lift the stock to its new equilibrium
   price before the rebalance window starts. The very feature that *caused* the
   premium — predictable, mechanical buying — is also what makes the premium
   trivial to front-run.

2. **Passive AUM has grown enough that the effect saturates the float.** When
   the share of float that *must* trade on the effective date is large enough,
   the marginal buyer faces a steep supply curve and demands compensation in
   the form of lower entry prices. The supply elasticity of S&P 500 stocks has
   improved enormously alongside the growth of the ETF lending and short
   markets.

3. **Index-fund execution has become smarter.** Modern index funds and the ETF
   creation/redemption mechanism unwind the rebalance over several days, often
   using volume-weighted trades or in-kind exchanges that compress most of the
   price impact into a small concession around the effective-date close. This
   is well documented in the practitioner literature.

The Petajisto (2011) paper estimated the implicit cost of the premium to S&P
500 index funds at roughly **20-28 bps per year** during the height of the
effect. On the post-2010 evidence here, that drag has gone to essentially
zero — a small but real piece of good news for passive investors.

## Limitations

This is a clean illustration, not a definitive replication. Things that would
sharpen it:

- **Announcement vs. effective date.** I use the effective date because
  Wikipedia gives that. A true Petajisto-style study uses the announcement
  date, which is typically 4-7 trading days earlier. The CAR$_{[-5,0]}$ window
  largely captures the announcement-to-effective interval, but a precise
  announcement-date study would shift the run-up into a $[+1, +5]$ window
  measured from announcement.
- **Pre-2010 sample is small (n=22).** The classic Petajisto results lean on
  1990s data, which Wikipedia's changes table covers thinly. Extending the
  sample further back would tighten the pre-2010 confidence band.
- **No matched-control benchmarking.** I use the S&P 500 itself as the
  market-model factor. A sector-matched control (or a Carhart 4-factor model)
  would be more conservative. The headline result is robust enough that I
  doubt it would flip, but it's worth doing.
- **Effective-date deletions are not studied here.** Symmetric removals would
  also be informative — the classic premium has a mirror "deletion discount"
  that the literature has flagged.[^chen]

## Reproducing this

```bash
git clone https://github.com/jothamteo/quant-research-blog
cd quant-research-blog/code/sp500_index_addition_premium
pip install -r requirements.txt
python fetch_events.py     # ~5 sec
python fetch_prices.py     # ~5-10 min (yfinance, 311 tickers)
python event_study.py      # ~2 sec
python analyze.py          # ~2 sec — also writes the charts in this post
```

Every number in this post is reproducible from `data/event_study_results.csv`
and every chart from `analyze.py`.

---

[^petajisto]: Petajisto, A. (2011). The Index Premium and Its Hidden Cost for
    Index Funds. *Journal of Empirical Finance*, 18(2), 271-288.
[^chen]: Chen, H., Noronha, G., & Singal, V. (2004). The Price Response to S&P
    500 Index Additions and Deletions: Evidence of Asymmetry and a New
    Explanation. *Journal of Finance*, 59(4), 1901-1929.
[^denis]: Denis, D. K., McConnell, J. J., Ovtchinnikov, A. V., & Yu, Y. (2003).
    S&P 500 Index Additions and Earnings Expectations. *Journal of Finance*,
    58(5), 1821-1840.
[^brown_warner]: Brown, S. J., & Warner, J. B. (1985). Using Daily Stock
    Returns: The Case of Event Studies. *Journal of Financial Economics*,
    14(1), 3-31.
