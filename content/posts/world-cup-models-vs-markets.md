---
title: "Two models, two markets, one World Cup: where the prices disagree"
date: 2026-06-17
draft: false
math: true
tags: ["prediction-markets", "sports", "elo", "dixon-coles", "reproducible-research", "crypto"]
summary: "I built two transparent football models — Dixon-Coles and Elo — and put them head-to-head against two real-money prediction markets pricing the exact same bets: Polymarket and Hyperliquid's HIP-4 World Cup champion markets. The models, the two venues, and each other disagree in ways that are genuinely tradeable — and the two markets quote the same contract at very different vig."
---

Picture two betting kiosks on the same street. Same sport, same question — *who
wins the World Cup?* — and a price chalked up next to every country. You wander
between them and notice something odd: the two boards don't quite agree. One has
France at roughly even-money-ish odds; the other a shade longer. One is selling
the whole board for almost exactly fair value; the other is quietly charging you
a fat margin on every ticket. And in your back pocket you have a third opinion —
your own, built from nothing but the results of every international match played
in the last decade.

That's the whole post. The two kiosks are real: **Polymarket** and
**Hyperliquid's HIP-4 outcome markets**, two crypto prediction venues that both
list a "will country X win the 2026 World Cup" contract for essentially every
team in the field. The third opinion is two football models I fit from scratch.
The interesting bit isn't any single number — it's the *gaps*: model vs market,
market vs market, and the two models against each other.

Everything below is computed from public data and live market snapshots, and
every number is reproducible from the
[code on GitHub](https://github.com/jothamteo/quant-research-blog/tree/main/code/world_cup_models).
Market prices were pulled on **17 June 2026** (group-stage matchday 2); they move,
so treat the exact figures as a snapshot, not gospel.

## The two opinions I brought to the kiosks

Before you can say a price is "wrong," you need a view of your own. I built two,
on purpose, because they fail in different ways.

**Dixon-Coles** is the workhorse of football modelling. The idea is almost
embarrassingly simple: a team scores goals at some average rate, and that rate
depends on how good its attack is and how leaky the opponent's defence is. Model
each team's goals as a Poisson draw, give the home side a bump, and you can write
down the probability of any exact scoreline. The one wrinkle Dixon and Coles added
in 1997 is a small correction for low-scoring games (0-0, 1-0, 1-1 happen a bit
more often than independent-Poisson says), which matters enormously in a sport
where a third of matches end with two goals or fewer. Concretely, the home and
away goal rates are

$$
\lambda = \exp(\eta + \alpha_{\text{home}} - \beta_{\text{away}}), \qquad
\mu = \exp(\alpha_{\text{away}} - \beta_{\text{home}})
$$

where $\alpha$ is a team's attack strength, $\beta$ its defensive strength, and
$\eta$ the home-field edge. I fit all of those by maximum likelihood on every
international since 2014, weighting recent matches more heavily (a ~2.5-year
half-life) and competitive matches more than friendlies. Out pops a home-field
edge of $\eta = 0.24$ and the tell-tale negative low-score correction
$\rho = -0.055$ — both bang in line with the literature.

**Elo** is the other classic, and it ignores goals almost entirely. Every team
carries a single rating; win and it ticks up, lose and it ticks down, and the
size of the move depends on the result, the margin, and how big a deal the match
was. It's the model behind chess rankings and most "power rankings" you've ever
seen. I ran it over the full history and then fit — again on the data, not by
hand — the mapping from rating gap to win/draw/loss probabilities. Its top of the
table on the eve of the tournament:

| Elo rank | Team        | Rating |
|---------:|-------------|-------:|
| 1        | Spain       |  1960  |
| 2        | Argentina   |  1947  |
| 3        | France      |  1929  |
| 4        | England     |  1883  |
| 5        | Morocco     |  1879  |

To turn either model into "who wins the tournament," I simulate the whole thing
30,000 times: the real group fixtures, the real qualification rule (top two per
group plus the eight best third-placed teams), and the **exact** knockout bracket
FIFA published, down to which third-place slot feeds which round-of-32 tie. Count
how often each team lifts the trophy, and you have a model-implied champion
probability you can stack right next to the market's.

## First, tonight's games

The group stage is still on, so the most immediate test is the next slate of
matches. Here's each model's probability that the listed team wins, next to
Polymarket's (with the bookmaker's margin stripped out):

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

¹ shown from Colombia's side (the favourite). All probabilities are for the named
team to win in 90 minutes.

![tonight home-win probabilities](/quant-research-blog/charts/world-cup-models/tonight_home_win.png)

A few things jump out. On **England–Croatia**, everyone agrees — two models and a
real-money market all land within six points of each other, which is about as
much consensus as you ever get. But look at **Portugal–DR Congo** and
**Canada–Qatar**: the market is a clear 8–15 points more confident in the
favourite than either model is. That's the market pricing in things a
results-only model can't see — squad news, that Canada is effectively playing at
home, that DR Congo's recent results flatter a thin squad. Sometimes that
soft information is real edge; sometimes it's a crowd talking itself into a
favourite. The models can't tell you which, but they can tell you *where to look*.

And notice where the two models split hardest: **Ghana–Panama**, Dixon-Coles 40%
vs Elo 17%. That gap is the models arguing about how to weight a handful of recent
Ghana results — exactly the kind of disagreement that should make you trust
*neither* number much and shrink your stake.

## Now the big one: who wins it all

Stack the model-implied champion probabilities against both markets and the
picture gets spicy.

![champion three-way](/quant-research-blog/charts/world-cup-models/champion_three_way.png)

| Team | Dixon-Coles | Elo | Polymarket | Hyperliquid |
|------|:-----------:|:---:|:----------:|:-----------:|
| France | 8% | 16% | **18%** | **17%** |
| Spain | 18% | 24% | 13% | 13% |
| Argentina | 19% | 21% | 10% | 10% |
| England | 12% | 6% | 10% | 9% |
| Portugal | 7% | 3% | 10% | 11% |
| Brazil | 9% | 3% | 7% | 6% |

The headline is **France**. Both markets make France the clear favourite at
~18%. Both of my models, working only from results on the pitch, are far cooler
— Dixon-Coles has them at *half* that. The market is paying up for France's
talent and pedigree in a way that recent scorelines alone don't justify. Either
the market knows something the data doesn't (very possible — squads aren't in my
model), or France is the tournament's most over-bet team. That's a real,
falsifiable disagreement, and it's the single biggest one on the board.

The mirror image is **Argentina and Spain**, where *both* models think the
markets are too low — Argentina at 10% on the market versus 19–21% on the models.
The reigning champion and the European champion have been quietly demolishing
opponents, and a results-driven model rewards that more than the market does.

It's worth pausing on what it means that the two *models* also disagree — England
at 12% (Dixon-Coles) versus 6% (Elo), Brazil 9% versus 3%. Dixon-Coles rewards
teams that win by margins and have soft group draws; Elo cares only about the
binary result and rates the very top tier as a clearer cut above. When your own
two methods are this far apart on a team, that's not a signal to trade — it's a
signal that the honest answer is "we don't really know," and the market's price
is probably as good as yours.

## The part most people miss: the same bet costs more at one kiosk

Here's the bit that's pure market microstructure, and the reason a crypto-native
trader should care. Both venues are selling the *same contract*. So add up the
price of every team winning — in a perfectly efficient, margin-free market that
sum would be exactly 100%. The excess is the **overround**, the house edge baked
into the board.

- **Polymarket:** the 50 listed teams sum to **101.3%** — a 1.3% overround.
- **Hyperliquid HIP-4:** the 48 listed teams sum to **106.8%** — a 6.8% overround.

![Polymarket vs Hyperliquid](/quant-research-blog/charts/world-cup-models/pm_vs_hl_scatter.png)

That is a *big* gap. Polymarket's World Cup book is priced about as tight as a
Vegas futures market; Hyperliquid's is carrying more than five times the margin.
In plain terms: if you're *buying* a team to win, Polymarket is the cheaper kiosk
almost across the board. If you're a market maker, Hyperliquid's wider book is
where the spread — and the inventory risk — lives. The scatter plot above puts
each team's two prices on the same axes; almost everything sits below the diagonal,
which is exactly what a fatter overround looks like team by team.

This is the same lesson as any cross-venue pricing exercise in crypto: before you
get excited about a "mispriced" outcome, check whether you're really seeing edge
or just paying a different venue's vig.

## How to actually use this

Three concrete reads, in rough order of how much I'd trust them:

1. **Trust the consensus, fade the lonely outlier.** When both models and both
   markets cluster (England–Croatia, the top of the champion board), there's no
   edge — move on. When *one* of the four is far from the other three, that's
   where to spend your attention. France being 10 points above the models while
   the two markets agree with each other tells you the disagreement is
   model-vs-market, not noise.

2. **Shop the overround before you shop the team.** A 1.3% vs 6.8% gap means your
   break-even bar is very different at the two venues. The same nominal "edge"
   against the Hyperliquid price has to clear five times more margin. For
   outright *buys*, default to the tighter book; the wider one is interesting
   mainly from the *making* side.

3. **Size down where your own models fight.** The Dixon-Coles vs Elo gap is a
   free, built-in uncertainty estimate. Ghana tonight, England and Brazil for the
   title — those are the bets where two reasonable methods can't agree, so the
   honest position size is small or zero.

None of this is a license to bet the mortgage. It's a framework for knowing
*which* of the hundreds of World Cup prices is even worth a second look.

## How it's built (and how to rerun it)

```bash
git clone https://github.com/jothamteo/quant-research-blog
cd quant-research-blog/code/world_cup_models
pip install -r requirements.txt
python fetch_markets.py        # live PM + HL snapshot (run from clean egress)
python run_all.py --sims 30000 # fit both models, simulate, write results + charts
```

- **Match data.** Every men's international since 1872, from the public
  `martj42/international_results` dataset; I fit on 2014-onward with time decay.
- **Models.** `models.py` — Dixon-Coles by weighted MLE, Elo with a data-fit
  rating→1X2 mapping. No parameter is tuned to a market price.
- **Tournament.** `tournament.py` + `bracket.py` — 30,000 Monte-Carlo runs over
  the real fixtures, real third-place rule, and FIFA's exact published bracket.
- **Markets.** `fetch_markets.py` — Polymarket's `world-cup-winner` event and
  per-match books, plus Hyperliquid's HIP-4 champion outcomes, saved as a
  timestamped JSON that the analysis and the (forthcoming) live comparison site
  both read.

## Limitations (the honest list)

- **No squads, no injuries, no form-beyond-results.** The models see scorelines,
  not team sheets. That's the most likely explanation for the France gap, and a
  genuine edge the market has over me.
- **Neutral-venue assumption.** I treat every World Cup match as neutral, which
  understates the three host nations (USA, Canada, Mexico) playing at home.
- **Elo has no goal model**, so its group-stage tie-breaks use rating rather than
  goal difference — a minor approximation that barely moves champion numbers.
- **Third-place routing.** FIFA's 495-row allocation table is reproduced by a
  constrained assignment; it yields a legal bracket but not necessarily FIFA's
  exact tie-break ordering. Immaterial to champion probabilities.
- **One snapshot.** Prices move. The disagreements above are a photograph taken
  on 17 June 2026, not a standing claim.

A live version that refreshes these comparisons against both venues' moving
prices is next. For now, the code reruns the whole thing in about half a minute.
