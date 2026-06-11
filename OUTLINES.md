# Phase 3 — outlines for the next five posts

This is the internal brief I'll write each post from. Per the spec: outline
only — do not write fully until the author picks which to develop next.

Each outline includes: angle, honest research question, data source, key
papers to engage with, and an effort estimate.

---

## Article 2 — "Reading dealer positioning on Deribit: GEX, SVI, and the SqueezeMetrics assumption"

**Angle.** The companion piece to my Deribit BTC options dashboard at
[jothamteo.github.io/deribit-options-dashboard](https://jothamteo.github.io/deribit-options-dashboard/).
The dashboard already does the work — fits Gatheral SVI per expiry, computes
dealer gamma exposure with SqueezeMetrics' canonical sign, surfaces 25Δ
risk-reversal + butterfly, max-pain by expiry. This post is the narrative
that goes with it: explaining *what* dealer positioning means, *why* GEX
matters for the spot path through dealer hedging, and *most importantly*
the limits of porting SqueezeMetrics' sign convention from SPX to Deribit
BTC.

**Honest research question.** Does the SqueezeMetrics canonical sign
(+calls, −puts) survive the move from SPX dealer flow to Deribit's user
mix (more prop, more directional retail, fewer market-making banks)? If
not, what would a *Deribit-honest* dealer positioning estimate look like —
and is the existing dashboard's GEX still useful as a *relative* signal
even when the sign is uncertain?

**Data source.** Live Deribit `get_book_summary_by_currency` feed (already
wired into the dashboard). One historical session snapshot to ground the
illustrative numbers in the post.

**Key papers / sources to engage with.**
1. SqueezeMetrics (2017). *The Implied Order Book and Gamma Exposure.* The
   source of the canonical SPX dealer-positioning assumption.
2. Gatheral, J. (2004). *A parsimonious arbitrage-free implied volatility
   parameterization.* The SVI form the dashboard fits.
3. Barbon, A., & Buraschi, A. (2021). *Gamma Fragility.* Pricing impact of
   dealer hedging on short-term spot volatility.
4. Brogaard, J., Han, J., & Won, P. (2024). *Dealer gamma exposure and stock
   market volatility.* The current academic treatment of GEX as a state
   variable.
5. Garleanu, N., Pedersen, L. H., & Poteshman, A. (2009). *Demand-Based
   Option Pricing.* Foundational paper on end-user demand → dealer
   positioning → IV shape.

**Effort.** Low. Dashboard exists, methodology doc exists. Post is mostly
the *write-up* of work already done, plus the honest GEX-sign limitations
section. **~1 day.**

---

## Article 3 — "What I learned using AI agents to clean financial data"

**Angle.** A practitioner essay, *not* a benchmark. Honest account of
where coding-agent and LLM tools sped up data work (boilerplate parsers,
schema profiling, anomaly *proposal*, fuzzy date parsing across messy
filings) and where they have to be kept on a tight leash (silent
hallucinations of column meanings, non-determinism that breaks
reproducibility, plausible-but-wrong fix proposals on noisy fields). The
point is *judgement about a new tool*, which is itself a quant signal —
"can this person hold a sharp idea about something they actually use".

**Honest research question.** Where in a quant data pipeline can a
non-deterministic agent be in the loop without compromising
reproducibility — and what does the operating discipline look like
(prompts, evals, human-confirm gates, deterministic re-runs)?

**Data source.** Personal: cleaning Compustat-like equity filings, futures
metadata, options chain corrections, perp funding-rate vendor feeds. Use
synthetic or anonymised examples in the post; no proprietary feeds.

**Key papers / sources to engage with.**
1. Anthropic (2026). *Building agents — claude.ai/docs/agents-best-practices.*
   The "agent ≠ chatbot" framing.
2. Liu, N. F. et al. (2023). *Lost in the middle: how language models use long
   contexts.* The failure mode that hits big-CSV inspection.
3. Cuadros, M. et al. (2024). *Faithful and Reproducible Data Cleaning with
   LLMs.* Recent academic attempt at deterministic LLM cleaning pipelines.
4. Sambasivan, N. et al. (2021). *"Everyone wants to do the model work, not the
   data work."* Google's classic on data cascades — the cost of upstream
   mistakes.

**Effort.** Low. No empirical study, just careful prose. **~0.5-1 day.**

---

## Article 4 — "A practical guide to event studies: the linear algebra and statistics behind the market model"

**Angle.** The methodology explainer that the index-addition premium post
(Post 1) leaves on the table. Walk through the Brown-Warner framework
properly: $\mathbf{X}^\top \mathbf{X}$ in matrix form, the per-event
regression, the standardisation that gets you a *t*-distributed test
statistic under the null, the choice of estimation window, the
cross-sectional aggregation when events overlap. Worked example with code
on a tiny synthetic dataset so the maths is unambiguously demonstrated.

**Honest research question.** *Not* an empirical question — this is a
teaching post. The "research question" is methodological: what *exactly*
is being assumed when you report a CAR with a *t*-statistic, and where do
those assumptions bite in practice?

**Data source.** Synthetic returns generated from a known data-generating
process so the reader can verify the methodology recovers the planted
effect. Then a small real-world re-application to a 5-event subset of the
S&P 500 sample from Post 1.

**Key papers / sources to engage with.**
1. Brown, S. J., & Warner, J. B. (1985). *Using daily stock returns: the
   case of event studies.* JFE. The canonical reference.
2. MacKinlay, A. C. (1997). *Event studies in economics and finance.*
   Journal of Economic Literature. The methodology survey.
3. Kothari, S. P., & Warner, J. B. (2007). *Econometrics of event studies.*
   In *Handbook of Empirical Corporate Finance*. The modern treatment.
4. Boehmer, E., Musumeci, J., & Poulsen, A. B. (1991). *Event-study
   methodology under conditions of event-induced variance.* The most
   commonly-cited robustness correction.

**Effort.** Low-medium. No data fetching; mostly clear writing and a
worked code example. **~1-1.5 days.**

---

## Article 5 — "Are prediction markets actually well-calibrated? An empirical check"

**Angle.** Honest empirical test of the "wisdom of markets" claim. Take
resolved prediction-market data, build a calibration plot (binned
predicted probability vs. observed frequency), report Brier scores and
log scores, compare against a few naive baselines (a uniform prior, last
year's base rate). Report the result honestly — including the categories
where the markets are *poorly* calibrated. This is the post that proves I
can hold a probabilistic question rigorously.

**Honest research question.** When a prediction market is trading at
$p$ per yes-share, what fraction of those events actually resolves yes?
Where does calibration break (tail probabilities, long-dated markets, low
volume)?

**Data source.** Public resolved markets from Polymarket and/or Kalshi.
Both expose historical resolved-market data via API; Polymarket also has
a graphql endpoint that includes final settlement. ~1000-2000 resolved
markets across several categories (elections, sports, macro) is a
respectable sample.

**Key papers / sources to engage with.**
1. Wolfers, J., & Zitzewitz, E. (2004). *Prediction markets.* The classic
   survey of their information-aggregation claim.
2. Brier, G. W. (1950). *Verification of forecasts expressed in terms of
   probability.* The original scoring rule.
3. Murphy, A. H. (1973). *A new vector partition of the probability score.*
   Resolution / reliability decomposition that the calibration plot
   visualises.
4. Augenblick, N., & Rabin, M. (2021). *Belief movement, uncertainty
   reduction, and rational updating.* Recent work on prediction-market
   over- and under-reaction.
5. Page, L., & Clemen, R. T. (2013). *Do prediction markets produce
   well-calibrated probability forecasts?* Empirical study with similar
   methodology — I would extend it to newer Polymarket/Kalshi data.

**Effort.** Medium. Data plumbing (API → resolved markets DataFrame) is
the main work; the actual calibration analysis is short. **~2-3 days.**

---

## Article 6 — "Funding-rate carry in crypto perps: does the edge survive costs?"

**Angle.** The honest backtest of a strategy that's all over crypto
Twitter: short-perp / long-spot to harvest positive funding, plus the
mirror trade. The story isn't "I found alpha" — it's "here's what
realistic transaction costs, basis decay, and tail liquidations actually
do to the headline number."

**Honest research question.** After 2 bps round-trip on the perp,
realistic spot borrow / margin cost, and a stress test against the worst
funding-rate weeks of 2022 and 2024, what is the Sharpe of the canonical
funding-carry trade on BTC and ETH perps over the last 36 months — and
does it survive a 3-sigma stress to the worst observed funding day?

**Data source.** Hyperliquid, Binance, and dYdX funding histories
(public, free). For BTC-spot and ETH-spot: Coinbase Pro and Kraken via
public APIs. Funding-rate publishing is hourly on Binance and 1/8th-day
on Hyperliquid.

**Key papers / sources to engage with.**
1. Alexander, C., Heck, D. F., & Kaeck, A. (2022). *Price discovery in
   Bitcoin spot, futures and perpetual swap markets.* JFM. The price-
   discovery hierarchy.
2. Coelho, D., Bornholdt, S., & Roehner, B. M. (2022). *Empirical analysis
   of funding rates in crypto perpetual swaps.* The most-cited descriptive
   study of funding-rate dynamics.
3. BIS (2024). *Quarterly Review: Crypto derivatives and the funding-rate
   carry trade.* Industry-level summary of carry-trade sizing.
4. Makarov, I., & Schoar, A. (2020). *Trading and arbitrage in
   cryptocurrency markets.* JFE. Cross-exchange basis behaviour.

**Effort.** Medium-high. Funding-rate plumbing is fiddly (per-exchange
sign and timing conventions differ); the basis / spot leg is more work
than it looks. **~3-4 days.**

---

## My pick for the next post to develop

If forced to choose: **Article 4 (event-study methodology explainer)**.
Rationale:

- Builds directly on the published Post 1 and turns the blog into a coherent
  thread ("the empirical result → here's the maths that makes the result
  defensible").
- Lowest data-plumbing burden.
- The exact "linear algebra + statistics" combination that quant-research
  job postings name explicitly.

Second choice: **Article 5 (prediction-market calibration)** — it's a clean
empirical post that doesn't depend on any other project and is the most
*differentiated* of the five (everyone has opinions about prediction
markets; few people actually grade them).

Third choice: **Article 2 (Deribit dashboard companion)** — leverages
existing work, easiest to write once I've drafted Article 4's
methodology framing.

Articles 3 and 6 are useful but require either a longer reflective process
(3) or substantially more data engineering (6) — both are post-MVP.
