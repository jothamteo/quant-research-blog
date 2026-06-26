---
title: "How much does it cost to lie to a DeFi oracle? Manipulating AMM-based price feeds, from first principles"
date: 2026-06-26
draft: false
math: true
tags: ["defi", "market-microstructure", "amm", "oracles", "market-making", "reproducible-research"]
summary: "DeFi lending protocols need to know the price of an asset, and many of them ask an automated market maker. But an AMM price is just the state of a pool — and pool state can be bought. I build up from the constant-product market maker (the x·y=k curve behind Uniswap) and what a DeFi oracle actually is, to the question in 'Cost of Manipulation in AMM-Based Oracles' (arXiv:2606.03548): what does it cost to shove an on-chain price feed somewhere false, why a spot oracle is nearly free to fool, and why time-averaging turns a flash loan into a sustained, expensive hold. Reproducible numpy, no external data."
cover:
  image: "/quant-research-blog/covers/amm-oracle-manipulation.png"
  alt: "amm-oracle-manipulation"
  relative: false
---

Most DeFi exploits you read about aren't a clever break of the cryptography. They're
a protocol being told a price that isn't true, and faithfully acting on it. To see
how that's even possible, you have to understand one thing: in DeFi, the "price" of
an asset is very often just *the current state of a trading pool* — and a trading
pool is something you can push around with money. This post builds that picture from
the ground up, then follows it into a recent paper,
[*Cost of Manipulation in AMM-Based Oracles*](https://arxiv.org/abs/2606.03548)
(arXiv:2606.03548), which asks the only question that actually matters for a
defender: not *can* you manipulate the feed, but *what does it cost*?

Everything below is reproducible from
[code](https://github.com/jothamteo/quant-research-blog/tree/main/code/amm_oracle_manipulation):
plain numpy, no external data.

## Foundation 1: an AMM is a vending machine for tokens

A traditional exchange matches buyers against sellers in an order book. An
**automated market maker (AMM)** throws the order book away. Instead, it holds a
reserve of two assets in a pool and quotes a price using a fixed formula. There's no
counterparty waiting for your trade — you trade against the pool itself, and the
formula moves the price as you do.

The dominant formula is the **constant-product market maker (CPMM)**, the one behind
Uniswap and most of DeFi. The pool holds $x$ units of a token and $y$ units of a
numeraire (say USDC), and it enforces a single rule on every trade:

$$
x \cdot y = k \quad (\text{constant}).
$$

The quoted **spot price** of the token is simply the ratio of the reserves,
$p = y / x$. That's the whole machine. If the pool holds 1,000 tokens and 1,000
USDC, the price is 1.00. Anyone can be the *liquidity provider* on the other side
just by depositing both assets into the pool — which is exactly why these pools are
everywhere, and why so much else in DeFi ends up leaning on them.

## Foundation 2: every trade moves the price, and size pays slippage

Because $k$ is fixed, you can't take tokens out without putting numeraire in, and the
ratio — the price — moves as you do. Buy tokens (remove $x$, add $y$) and the price
rises; sell and it falls. Crucially, the *average* price you pay on a finite trade is
worse than the price you started at, because you're walking along a curve. That gap
is **slippage**.

![the constant-product curve](/quant-research-blog/charts/amm-oracle-manipulation/cpmm_curve.png)

Every valid state of the pool sits somewhere on that hyperbola. A small trade barely
moves you along it; a big trade drags the reserve point a long way and the price
swings hard. This is the single most important property for everything that follows:
**the price an AMM shows is a direct, mechanical function of how much someone has
recently bought or sold.** It is not a poll of the world. It is the position of a
point on a curve, and money moves the point.

## Foundation 3: what a DeFi "oracle" is, and why AMMs get drafted into the job

A smart contract is sealed off from the outside world — it can't call an API or read
a Bloomberg terminal. So when a lending protocol needs to answer "is this loan still
safely collateralised?", it needs an on-chain source of truth for price. That source
is an **oracle**.

There are two broad kinds. *Off-chain* oracles (Chainlink being the canonical one)
have a network of nodes fetch prices from real exchanges and post them on-chain.
*On-chain* oracles skip all that and read a price that already lives on the
blockchain — and the most convenient such price is, of course, the spot price of a
big AMM pool. It's trustless, always available, and free to read. So a lot of
protocols do exactly that: they treat $p = y/x$ from a Uniswap pool as the truth, and
make billion-dollar collateral decisions on it.

You can already feel the problem. We just established that $y/x$ is *whatever the last
trader pushed it to*. If a lending market believes a manipulated pool price, an
attacker can make their collateral look more valuable than it is, borrow against the
illusion, and walk away. This is the engine behind a long list of real DeFi
hacks — and it's the setup the paper formalises.

## The paper's question: not *whether*, but *how much*

The contribution of *Cost of Manipulation in AMM-Based Oracles* is to stop treating
manipulation as a binary "vulnerable / safe" and instead price it. It sets up a game:
an attacker trades against CPMMs to drag the oracle away from the true efficient
price, arbitrageurs trade to pull it back, and an oracle *designer* chooses how to
read the pool. The right defensive question becomes economic — **how many dollars
must an attacker burn to move the feed by a given amount, and is that less than what
they can steal downstream?**

The first half of the answer is the slippage we already met. To push the quoted price
up by some fraction, the attacker has to buy through the curve and eat the impact.
Working it out on the constant-product invariant, the cost rises with the size of the
distortion — and, critically, scales with the **depth of the pool**:

![cost to manipulate vs pool depth](/quant-research-blog/charts/amm-oracle-manipulation/manip_cost.png)

A pool with \$5M of liquidity costs roughly ten times more to shove than a \$0.5M
pool for the same percentage move, because you're fighting a fatter curve. This is
the first and bluntest defense in DeFi, and the one practitioners reach for first:
*only trust deep pools.* A thinly-traded token's AMM price is cheap to fake; a
deep blue-chip pool is expensive. On the numbers in the code, distorting a \$1M pool
by 10% costs on the order of a thousand dollars in slippage — which tells you
immediately that a \$1M pool guarding a much larger lending market is a disaster
waiting to happen.

## The killer: a spot oracle is nearly free to fool

Here's the part that turns a theoretical cost into a real exploit. If the protocol
reads the **spot** price — the instantaneous $y/x$ at the moment it checks — then the
attacker doesn't even have to *keep* the price moved. They can do the whole thing
inside a single atomic transaction with a **flash loan**: borrow a fortune with no
collateral, push the pool price, trigger the victim protocol to read the false price
and lend against it, then unwind the pool trade and repay the loan — all before the
block closes. Because the pool trade is round-tripped in the same instant, the
slippage is *recovered*; the attacker's only unavoidable cost is the swap fee.

That's why a naive spot-price oracle is so dangerous: the cost to manipulate it
collapses to almost nothing, no matter how deep the pool, because depth only charges
you for *moving* the price, not for the round trip.

## The defense: time-averaging makes the lie expensive to hold

The fix the paper and the industry converge on is to stop reading the instantaneous
price and instead read a **time-weighted average price (TWAP)** over the last $N$
blocks. Now a one-block flash manipulation barely budges the average. To move a TWAP,
the attacker has to *hold* the false price across many blocks — and that changes the
economics completely, because between blocks, **arbitrageurs** show up. A pool quoting
30% above the real price is free money to them: they sell into it until it's back in
line. So the attacker has to re-push the price every single block, paying the
slippage again and again, against a current that's constantly dragging it back.

![spot vs TWAP cost](/quant-research-blog/charts/amm-oracle-manipulation/twap_defense.png)

The spot attack sits on the floor — a flat fee, flash-loanable. The TWAP attack
climbs roughly linearly in the window length, because each extra block of averaging is
another block the attacker must pay to dominate. Once that accumulating cost crosses
the value they could extract downstream, the attack stops being worth it. *That
crossing point is the whole game.* The oracle designer's job is to choose $N$ (and pool
depth requirements, and cross-venue checks) so that the cost line sits above the
extractable-value line for any attack the protocol could suffer.

## Why I care: this is a microstructure problem wearing a security costume

I run market-making and liquidation bots on on-chain venues, and the lesson here is one
I keep relearning: **on-chain "prices" are not data, they are positions** — the literal
state of a pool that anyone with capital can move. Reading them safely is a
market-microstructure problem, not a cryptography problem. The paper's framing is the
right one for a desk:

- **Price the attack, don't fear it.** Every oracle has a manipulation cost. If it's
  above the value at risk with comfortable margin, the feed is fine; if it's below,
  no amount of audit hand-waving saves you.
- **Depth is a parameter, not a vibe.** The cost scales with pool liquidity, so
  "which pool" and "what minimum TVL" are quantitative risk limits you can set.
- **TWAP windows trade safety against latency.** A longer window is harder to
  manipulate but staler — it lags real moves, which matters for liquidations in fast
  markets. That tension is exactly the kind of thing worth simulating against your own
  positions before trusting a feed.

The same machinery that prices manipulation also prices the *defender's* latency cost,
which is where this stops being a security paper and becomes a trading one. That's the
version of it I'll actually wire into a risk check.

*Code and charts: [`code/amm_oracle_manipulation`](https://github.com/jothamteo/quant-research-blog/tree/main/code/amm_oracle_manipulation). Paper: "Cost of Manipulation in AMM-Based Oracles," [arXiv:2606.03548](https://arxiv.org/abs/2606.03548). The CPMM simulation here illustrates the mechanism — slippage, depth-scaling, and the spot-vs-TWAP economics — and is not a reproduction of the paper's formal bounds or its arbitrage-equilibrium model.*
