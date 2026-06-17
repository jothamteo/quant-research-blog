---
title: "Two models, two markets, one World Cup: where the prices disagree"
date: 2026-06-17
draft: false
math: true
tags: ["prediction-markets", "sports", "elo", "dixon-coles", "reproducible-research", "crypto"]
summary: "I fit two transparent football models — Dixon-Coles and Elo — checked that they're actually calibrated out-of-sample, then put them against two real-money prediction markets pricing the exact same bets: Polymarket and Hyperliquid's six-week-old HIP-4 World Cup markets. The interesting part isn't any single number, it's the disagreements — and an honest look at whether 'disagreement equals edge' actually holds."
---

Picture two betting kiosks on the same street. Same sport, same question — *who
wins the World Cup?* — and a price chalked up next to every country. You wander
between them and notice the boards don't quite agree: one has France a shade
shorter than the other, and one is quoting the whole field much tighter than its
neighbour. In your back pocket you have a third opinion — your own, built from
nothing but the results of every international played in the last decade.

That's the post. The two kiosks are real: **Polymarket** and **Hyperliquid's
HIP-4 outcome markets**, two crypto venues that both list a "will country X win
the 2026 World Cup" contract for nearly every team. The third opinion is two
football models I fit from scratch. The interesting bit isn't any single number —
it's the *gaps*: model vs market, market vs market, and the two models against
each other. And because "the model disagrees with the market" is the oldest trap
in quant finance, I'll spend real effort on the un-fun question: **do these gaps
actually mean anything, or is the market just right and my model blind?**

Everything below is reproducible from the
[code on GitHub](https://github.com/jothamteo/quant-research-blog/tree/main/code/world_cup_models).
Market prices are a snapshot pulled on **17 June 2026** (group-stage matchday 2);
they move.

## The two opinions I brought to the kiosks

Before you can call a price wrong, you need a view of your own. I built two, on
purpose, because they fail in different ways.

**Dixon-Coles** is the workhorse of football modelling. A team scores goals at
some average rate that depends on how good its attack is and how leaky the
opponent's defence is; model each side's goals as a Poisson draw, give the home
team a bump, and you can write down the probability of any exact scoreline. The
goal rates are

$$
\lambda = \exp(\eta + \alpha_{\text{home}} - \beta_{\text{away}}), \qquad
\mu = \exp(\alpha_{\text{away}} - \beta_{\text{home}})
$$

where $\alpha$ is attack strength, $\beta$ defensive strength, and $\eta$ the
home edge. **That Poisson attack/defence structure is the engine** — it's what
carries essentially all of the model's predictive power. Dixon and Coles's 1997
contribution was a small extra knob: independent Poisson slightly *under*-predicts
the very low scores teams actually draw, so they multiply the four lowest cells by
a correction $\tau$ governed by one parameter $\rho$. With my fitted $\rho =
-0.055 < 0$, that correction nudges **0-0 and 1-1 up, and 1-0 and 0-1 down**. It's
a genuine refinement, but a second-order one — don't let anyone (including me)
tell you the $\rho$ term is where the magic lives. I fit everything by weighted
maximum likelihood on internationals since 2014, with a ~2.5-year half-life and
competitive games weighted above friendlies. Out comes a home edge $\eta = 0.24$
(reasonable) and $\rho = -0.055$ (on the *low* side of the canonical DC estimate
of roughly $-0.13$, but the right sign).

**Elo** is the other classic and it ignores goals almost entirely. Each team
carries one rating; win and it rises, lose and it falls, scaled by the margin and
the match's importance. I ran it over the full history and fit the mapping from
rating gap to win/draw/loss probabilities on the data. Its top five on the eve of
the tournament:

| Elo rank | Team        | Rating |
|---------:|-------------|-------:|
| 1        | Spain       |  1960  |
| 2        | Argentina   |  1947  |
| 3        | France      |  1929  |
| 4        | England     |  1883  |
| 5        | Morocco     |  1879  |

To turn either model into "who wins the tournament," I simulate the whole thing
30,000 times: the real group fixtures, the real qualification rule (top two per
group plus the eight best third-placed teams — $\binom{12}{8}=495$ possible
third-place combinations, exactly as in FIFA's regulations), and the **exact**
published knockout bracket. At champion-level probabilities the Monte-Carlo
standard error is about $\sqrt{p(1-p)/N}\approx 0.2$–$0.4$ points, so the gaps
below are signal, not simulation noise.

## Do the models actually work? (The part most blog posts skip)

Here's the question a sharp reader asks before believing a single champion number:
*are these models even calibrated?* A model that says "70%" should win about 70%
of the time. So before comparing to any market, I held data back.

Train on every international through **2023**; test on the **2,487** internationals
played in **2024 through June 2026** that the models never saw. Dixon-Coles is fit
once on the training window; Elo is run online (each test match predicted from the
rating *before* it's played). I score both with the ranked probability score (RPS,
the proper score for ordered home/draw/away outcomes) and multiclass log-loss,
against two naive baselines.

| Model | RPS ↓ | Log-loss ↓ |
|-------|:-----:|:----------:|
| **Dixon-Coles** | **0.165** | **0.856** |
| Elo | 0.174 | 0.892 |
| Base-rate (train H/D/A frequencies) | 0.227 | 1.054 |
| Uniform (1/3, 1/3, 1/3) | 0.238 | 1.099 |

Both models comfortably beat the naive baselines out-of-sample, and Dixon-Coles
edges Elo. More telling is *where* they're right:

![calibration reliability](/quant-research-blog/charts/world-cup-models/calibration_reliability.png)

Dixon-Coles hugs the diagonal across the whole range — when it says 25%, 45%, 75%,
those things happen about that often. **Elo is well-calibrated in the middle but
over-confident on strong favourites**: in its top bucket it predicts ~85% and the
favourite wins ~78%. Hold that thought — it matters for France in a minute.

This is the honest foundation. It does **not** prove the model can beat a market.
It proves the model isn't junk, which is the price of admission for the rest of
the post.

## First, the immediate test: tonight's games

Each model's probability that the listed team wins, next to Polymarket's (margin
removed by simple normalization — more on that method below):

| Match | Dixon-Coles | Elo | Polymarket |
|-------|:-----------:|:---:|:----------:|
| Portugal vs DR Congo | 67% | 62% | **75%** |
| England vs Croatia | 51% | 55% | 57% |
| Ghana vs Panama | 40% | 17% | 41% |
| Colombia vs Uzbekistan¹ | 61% | 45% | 71% |
| Czechia vs South Africa | 50% | 38% | 54% |
| Switzerland vs Bosnia | 65% | 76% | 62% |
| Canada vs Qatar | 60% | 66% | **75%** |
| Mexico vs South Korea | 40% | 36% | 48% |

¹ shown from Colombia's side (the favourite). All for the named team to win in 90
minutes — which, importantly, is exactly how these match markets resolve.

![tonight home-win probabilities](/quant-research-blog/charts/world-cup-models/tonight_home_win.png)

On **England–Croatia** everyone agrees within six points — that's consensus, and
consensus means no edge. The gaps are on **Portugal–DR Congo** and
**Canada–Qatar**, where the market is 8–15 points more sold on the favourite than
either model. That's the market pricing things a results-only model can't see:
squad news, that Canada is effectively at home, that DR Congo's results flatter a
thin squad. Sometimes that soft information is real; sometimes it's a crowd
talking itself into a favourite. And note where the *models* split hardest —
Ghana–Panama, DC 40% vs Elo 17% — which is the two methods admitting they don't
know, and a cue to trust neither.

## Now the big one: who wins it all

Stack the model-implied champion probabilities against both markets:

![champion three-way](/quant-research-blog/charts/world-cup-models/champion_three_way.png)

| Team | Dixon-Coles | Elo | Polymarket | Hyperliquid |
|------|:-----------:|:---:|:----------:|:-----------:|
| France | 8% | 16% | **18%** | **17%** |
| Spain | 18% | 24% | 13% | 13% |
| Argentina | 19% | 21% | 10% | 10% |
| England | 12% | 6% | 10% | 9% |
| Portugal | 7% | 3% | 10% | 11% |
| Brazil | 9% | 3% | 7% | 6% |

The headline is **France**, and it's subtler than "model says market is wrong."
Both markets make France the clear favourite at ~18%. My **goal-based** model
(Dixon-Coles) has them at less than half that. But my **rating-based** model
(Elo) has France at 16% — basically agreeing with the market. So this is *not*
"both my models are cooler on France." It's that my two models flatly disagree
with *each other* about France, and that split is the story.

And it's not a coin-flip which to believe. Remember the calibration check: Elo is
the model that *over-rates strong favourites*, and France sits right in that
over-confident top bucket. The better-calibrated model (Dixon-Coles) is the one
screaming "over-bet." That doesn't make DC right — the market sees France's squad
depth, which my model is blind to — but it means the France disagreement has a
real, testable shape rather than being noise.

The cleaner signal is **Argentina and Spain**, where *both* models sit well above
both markets (Argentina ~19–21% model vs ~10% market). The reigning and European
champions have been winning, and by margins, and a results-driven model rewards
that more than the crowd does.

## The cross-venue bit: the same bet is "wider" at one kiosk

Here's the pure-microstructure observation, and the reason a crypto trader should
care. Both venues sell the *same contract*, so the mid prices of every team
winning should, in a frictionless market, sum to 100%. Summing the **mid price**
of every listed team:

- **Polymarket:** the field sums to **101.3%**.
- **Hyperliquid HIP-4:** the field sums to **106.8%**.

A quick but important clarification, because the bookmaker word "overround" is the
wrong lens here: *neither venue is a bookmaker*. Both are trader-driven order
books with no house taking a cut. So that 1.3% / 6.8% isn't a charged margin —
it's the slack left by **bid-ask spread and thin liquidity**. Polymarket's World
Cup book is deep and tight (1.3% is genuinely impressive — for comparison, a Vegas
sportsbook's 48-team outright-winner board routinely sums to *130–150%*; the right
peers for "this tight" are Betfair Exchange or Pinnacle, not Vegas). Hyperliquid's
HIP-4 market is **six weeks old and thin**, so its mids sit inside wide spreads and
the field over-sums. That's not "Hyperliquid charges 5× the margin" — it's "this
venue is new and illiquid," which is itself the useful signal: a wide, slow book is
exactly the surface a market-making or latency strategy would target.

![Polymarket vs Hyperliquid](/quant-research-blog/charts/world-cup-models/pm_vs_hl_scatter.png)

The scatter plots each team's Polymarket mid (x-axis) against its Hyperliquid mid
(y-axis). Most points sit a touch below the diagonal — consistent with HL's wider
book — but the gap isn't a uniform shift; spread loads unevenly across favourites
and longshots, and *that* uneven structure is where a real cross-venue trade would
live. Two housekeeping notes a careful reader will want: Polymarket lists ~50 teams
to Hyperliquid's 48 because PM leaves a couple of non-qualifiers (e.g. Italy, Peru)
on the board at ~$0; I restrict every comparison to the 48 teams actually in the
field. And I de-vig by **simple normalization** (divide by the sum), which is the
transparent choice but not the perfect one — it assumes margin is spread
proportionally, whereas the favourite-longshot effect loads more onto longshots, so
naive normalization mildly *understates* favourites (perhaps 1–3 points on France)
and overstates minnows. Shin or power-method de-vigging would correct this; I kept
it simple and I'm flagging the bias rather than hiding it.

## So can you actually trade these gaps?

Honest answer: **I can't prove it from this post, and neither can anyone — yet.**
The clean test would be a backtest of "when models and markets diverged, who moved
toward whom?" (closing-line value). But Polymarket's World Cup book and especially
Hyperliquid's HIP-4 markets are *weeks* old; there's no history of past tournaments
priced on these venues to backtest against. Anyone claiming a proven World Cup
prediction-market edge on Hyperliquid is fitting noise.

What I *can* do is be disciplined about it:

1. **Trust the consensus, scrutinise the lonely outlier.** When two models and two
   markets cluster (England–Croatia; the top of the board), there's nothing to do.
   Spend attention only where one of the four is far from the other three.
2. **Make one falsifiable call and mark it to market.** My goal model says France
   is over-bet (DC 8% vs market 18%); my rating model disagrees; the calibration
   evidence leans toward the goal model on favourites. So here's a concrete,
   checkable claim: **France is the tournament's most over-priced favourite, and
   its market price should drift down (or it should exit earlier than 18% implies).
   I'll mark this against the closing price in July.** That's how you find out if a
   gap was edge or blindness — not by asserting it in June.
3. **Size to your own disagreement.** The Dixon-Coles–Elo gap is a free uncertainty
   estimate. Ghana tonight, England and Brazil for the title — those are the bets
   where two reasonable methods can't agree, so the honest stake is small or zero.

This isn't an alpha claim. It's a calibrated disagreement detector plus one bet
I'm willing to be graded on.

## How it's built (and how to rerun it)

```bash
git clone https://github.com/jothamteo/quant-research-blog
cd quant-research-blog/code/world_cup_models
pip install -r requirements.txt
python fetch_markets.py        # live PM + HL snapshot (run from clean egress)
python calibrate.py            # out-of-sample RPS / log-loss / reliability
python run_all.py --sims 30000 # fit, simulate, write results + charts
```

- **Match data.** Every men's international since 1872 (`martj42/international_results`);
  fit on 2014-onward with time decay.
- **Models.** `models.py` — Dixon-Coles by weighted MLE, Elo with a data-fit
  rating→1X2 mapping. No parameter is tuned to a market price.
- **Tournament.** `tournament.py` + `bracket.py` — 30,000 Monte-Carlo runs over the
  real fixtures and FIFA's exact bracket.
- **Markets.** `fetch_markets.py` — Polymarket's `world-cup-winner` event and
  per-match books, plus Hyperliquid's HIP-4 champion outcomes, saved as a
  timestamped JSON.

## Limitations (the honest list)

- **No squads, no injuries, no form-beyond-results.** The models see scorelines,
  not team sheets — the most likely explanation for the France gap, and a real edge
  the market has over me.
- **No shrinkage on sparse teams.** Fitting across all internationals leaves
  minnows with few matches carrying high parameter variance, which propagates into
  the sims. A hierarchical/shrinkage prior on attack-defence is the standard fix;
  I haven't applied one. It barely touches the (near-zero) champion odds of small
  teams but does add noise to their group-stage upset probabilities.
- **De-vig is naive normalization** (favourite-longshot caveat above).
- **Neutral-venue assumption**, which understates the three hosts (USA, Canada,
  Mexico) playing at home.
- **Elo has no goal model**, so its group tie-breaks use rating, not goal
  difference — immaterial to champion numbers.
- **Carry/time value ignored.** These resolve ~a month out, so it's minor, but it's
  why a frictionless futures board can sum to just *under* 100%; Polymarket sitting
  at 101.3% rather than ~99.5% is mildly interesting on that score.
- **One snapshot.** Prices move; this is a photograph taken on 17 June 2026.

A live version that refreshes all of this against both venues' moving prices is
next. For now, the whole thing reruns in under a minute.
