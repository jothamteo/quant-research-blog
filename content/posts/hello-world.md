---
title: "Hello, world (and a typesetting check)"
date: 2026-06-11
draft: false
math: true
tags: ["meta"]
summary: "First post — exists so I can verify that math, code blocks, tables, and footnotes all render correctly before publishing real research."
---

This post is a build sanity check for the blog: math, code blocks, tables and
footnotes. Real research starts with the next post.

## Inline and display math

Volatility scaling on log-returns: $\sigma_T = \sigma_1 \sqrt{T}$.

The OLS estimator in matrix form, used throughout event-study and factor-model
work on this blog:

$$
\hat{\boldsymbol{\beta}} = (\mathbf{X}^\top \mathbf{X})^{-1} \mathbf{X}^\top \mathbf{y}
$$

with variance under homoskedasticity

$$
\mathrm{Var}(\hat{\boldsymbol{\beta}} \mid \mathbf{X}) = \sigma^2 (\mathbf{X}^\top \mathbf{X})^{-1}.
$$

## Code blocks

Python with syntax highlighting:

```python
import numpy as np

def market_model_resid(stock: np.ndarray, mkt: np.ndarray) -> np.ndarray:
    """Residuals from a Brown-Warner market-model regression on the estimation window."""
    X = np.column_stack([np.ones_like(mkt), mkt])
    beta, *_ = np.linalg.lstsq(X, stock, rcond=None)
    return stock - X @ beta
```

## Tables

| metric              | symbol      | typical use                |
|---------------------|-------------|-----------------------------|
| Sharpe ratio        | $\mathrm{SR}$ | risk-adjusted performance |
| max drawdown        | $\mathrm{MDD}$ | tail-risk summary         |
| cumulative abnormal | $\mathrm{CAR}$ | event-study response      |

## Footnotes

I use footnotes for citations and caveats[^petajisto], not for hidden hype.

[^petajisto]: Petajisto, A. (2011). The Index Premium and Its Hidden Cost for
    Index Funds. *Journal of Empirical Finance*, 18(2), 271-288.
