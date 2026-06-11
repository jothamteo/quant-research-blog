# `prediction_market_calibration/`

Reproducible calibration analysis of Manifold Markets resolved binary
markets, backing the blog post **"Are prediction markets well-calibrated?"**.

## Run it

```bash
pip install -r requirements.txt
python fetch_markets.py    # ~3-5 min (paginated public API)
python calibration.py      # ~3 sec
```

Outputs:
- `data/resolved_markets.csv` — 5,125 resolved BINARY markets with the
  closing probability, the YES/NO resolution, volume, and bettor count.
- `data/calibration_bins.csv` — 10-bin reliability table.
- `data/calibration_by_volume.csv` — same table split by volume tier.
- `data/scores.json` — Brier, log score, ECE vs two naive baselines.
- `charts/reliability_overall.png` — the headline reliability diagram.
- `charts/reliability_by_volume.png` — by-tier comparison.

## Notes

- This uses the latest snapshot probability for each market, i.e. the
  *closing* probability. A more honest study would use the probability
  at some fixed lead time (e.g. 7 days before resolution) and requires
  per-market bet-history pulls. That is a project's worth of additional
  work and is not done here.
- Manifold is play-money; the conclusions transfer to Polymarket /
  Kalshi only as hypotheses.
- The sample includes only markets that resolved YES or NO. Markets
  that resolved MKT (multiple choice) or CANCEL are not in the sample.

MIT license. Manifold's market data carries its own terms.
