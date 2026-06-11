# `sp500_index_addition_premium/`

Reproducible event-study code backing the blog post
**"Has the S&P 500 index-addition premium disappeared?"**.

## What it does

1. `fetch_events.py` — pulls the historical "Selected changes to the list of
   S&P 500 Components" table from Wikipedia and writes `data/wiki_changes_raw.csv`.
2. `fetch_prices.py` — for each addition event between 2000 and 2022, pulls
   ~10 months of daily adjusted closes from Yahoo Finance via `yfinance`. Also
   pulls the S&P 500 (`^GSPC`) benchmark once over the full range. Writes one
   parquet per event under `data/prices/` plus a `data/fetch_meta.csv`.
3. `event_study.py` — for each event with sufficient price history:
   - log returns over the [−120, +20] window
   - OLS market-model fit on the [−120, −21] estimation window
   - abnormal returns and cumulative abnormal returns on [−10, +20]
   - one row per event written to `data/event_study_results.csv`.
4. `analyze.py` — aggregates the results, runs a Welch t-test on pre-2010 vs.
   post-2010, and writes the charts in `charts/`.

## Run it

```bash
pip install -r requirements.txt
python fetch_events.py
python fetch_prices.py   # ~5-10 min, network-bound
python event_study.py
python analyze.py
```

## Sample

311 effective-date events between 2000 and 2022 (Wikipedia's coverage gets
thin before that). 232 ticker pulls returned prices; 26 had insufficient
estimation-window observations; 1 was dropped as a corporate-action artefact
(`|AR| > 50%` on a single day). **Final sample: 204 events.**

## Sign conventions

- Returns are **log returns** throughout.
- Abnormal return $\mathrm{AR}_{i,t} = r_{i,t} - (\hat\alpha_i + \hat\beta_i \, r_{m,t})$.
- Cumulative abnormal return over $[a, b]$ is $\sum_{\tau = a}^{b} \mathrm{AR}_{i,\tau}$.
- Positive CAR$_{[-5,0]}$ means the stock outperformed the market in the 5 days
  ending on the effective date — the classic "addition premium".

## Limitations

- Wikipedia gives effective dates, not announcement dates. A proper Petajisto-
  style study uses announcement dates.
- No matched sector / Carhart-factor benchmark — just the S&P 500 itself as
  the market factor.
- Pre-2010 sample is small because the historical changes table is sparse
  before 2007.
- yfinance occasionally rate-limits; rerun if you see empty rows.

## License

The code in this directory is MIT-licensed. The Wikipedia data carries its
own licence (CC-BY-SA 3.0).
