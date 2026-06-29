# Mark to Model — Locked Visual Identity

The brand is the **capybara quant**. Every cover and brand asset shares the same DNA;
only the *post-specific props* on the desk/screen change.

## Locked style string (use verbatim in every ComfyUI prompt)

```
studio ghibli soft illustration, hand-painted, warm amber and sage green pastel palette,
soft window light, gentle bokeh, cozy quant office, a few potted plants, clean lines,
miyazaki aesthetic, no harsh 3d render, warm cinematic glow
```

## Negative (verbatim)

```
human, person, people, text, letters, words, watermark, ugly, deformed, blurry,
dark, horror, extra limbs, mutation, photorealistic, harsh lighting, low quality
```

## Per-post props (the ONLY thing that changes)

The capybara is always the hero. Swap the desk/screen props to match the paper:

| Post topic                | Props on the capybara's screen / desk                |
|---------------------------|------------------------------------------------------|
| Market making / microstructure | limit order book ladder, green bid / red ask, bid-ask spread, step curve |
| FX / transient impact     | a price curve that spikes then mean-reverts          |
| Funding-rate carry        | a perpetual funding-rate curve, basis line           |
| Vol buying / options      | an implied-vol smile / surface                        |
| Prediction-market calibration | a reliability diagram (predicted vs realised)     |
| Event study               | cumulative abnormal return around an event line       |
| GARCH / volatility        | a volatility cone / clustering series                 |

## Generation settings (ComfyUI, SDXL base 1.0)

- Cover: render **1216×640**, resize to **1200×630** (OG ratio). Save to `static/covers/<slug>.png`.
- Sampler `dpmpp_2m` / scheduler `karras`, steps 38, cfg 7.5, denoise 1.0.
- Composition tail: `wide composition, capybara as the central hero, no humans`.

## X / brand assets

- **Profile pic** — Ghibli portrait of JT (img2img + Canny ControlNet from a real photo,
  denoise ~0.82, canny strength ~0.35, end ~0.42). Same warm palette, plants, soft light.
- **Banner** — capybara at the quant desk, wide 1536×512; overlay the title "Mark to Model"
  in post-processing (SDXL cannot render clean text).
