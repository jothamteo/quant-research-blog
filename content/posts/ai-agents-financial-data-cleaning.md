---
title: "Using AI agents to clean financial data: a year's worth of honest notes"
date: 2026-06-11T12:00:00+08:00
draft: false
math: false
tags: ["practitioner", "data-engineering", "ai-agents", "llm", "tooling"]
summary: "Notes from a year of using AI coding agents in my quantitative-research workflow — specifically for the messy, low-glamour data work that sits between a vendor feed and a backtest. Where agents reliably helped, where they reliably failed, and what an honest reproducible-pipeline discipline looks like once non-deterministic tools are in the loop."
---

I have spent a meaningful chunk of the last year doing quantitative
research with coding-agent tools — primarily Claude Code, with occasional
detours through other harnesses — in the loop. Most of the discussion of
these tools focuses on the green-field cases: write me an app, debug this
crash, refactor that module. Quantitative research is *not* a green-field
case. It is mostly cleaning data, reconciling vendor feeds against each
other, parsing messy filings, building features from primary sources, and
documenting why a half-fixed thing is the way it is.

I don't have a benchmark to share. I have field notes. They are most useful
read as a *practitioner's discipline document* — what to use the agent
for, what to keep on a tight leash, and how to keep the pipeline
reproducible when one of your tools is non-deterministic by construction.

## Where agents reliably help

**Boilerplate parsers for messy formats.** Vendor CSVs that use a header
row that's actually two header rows; fixed-width text dumps from a
regulator; nested-JSON option chains where the strike grid is encoded as
a string. The agent writes a correct parser faster than I do, every time,
because most of the work is mechanical pattern-matching against the
sample I paste in. The trick is to feed it three or four diverse samples
(quiet day, busy day, partial outage day) rather than one.

**Schema profiling.** "Here is a 200-column dataframe — group columns by
inferred semantic role, flag which have suspicious null patterns, list
columns whose dtype disagrees with their values." This is a task that is
boring, expensive in human attention, and pattern-shaped. The agent's
output is wrong about ~15% of the columns on a first pass, but the wrong
columns are *obvious* to a human reviewer — usually nullable optional
fields that look numeric but are sometimes the literal string `"N/A"`.

**Anomaly *proposal*.** "Here is a price time-series. List candidate
splits or special dividends that the adjustment factor probably missed."
The agent's hit rate is around 60%. The misses are obvious; the hits save
real time because each hit suggests a specific manual cross-check (look
up the corporate-action calendar; cross-reference against the SPLITS file
from a different vendor; etc.).

**Fuzzy date and entity parsing.** "Here are 40,000 free-text entries
mentioning company names and dates — produce a structured table." This is
exactly where LLMs shine: tolerant of noise, robust to spelling
variations, decent at disambiguating "Bank of America" from "Bank of
America Merrill Lynch". I still validate with a deterministic check (fuzzy
ratio above 90% to a reference table) but the agent's first pass takes
me from "this is a multi-day cleanup" to "this is a one-hour QA pass".

## Where agents reliably fail

**Silent hallucination of column meanings.** This is the failure mode I
warn other people about most. The agent reads my CSV, sees a column
called `PX_CLOSE_ADJ`, and writes code that treats it as already-split-
adjusted. If it actually is, great. If it isn't — and Bloomberg's column
naming is *not* a contract — the agent's code silently produces wrong
returns, the backtest looks fine, and the bug is invisible until someone
checks against a second source. The agent will *cheerfully* assert column
semantics it cannot verify; the assertions read with the same confidence
as the parts it can.

The discipline I have settled on: *never* trust the agent's interpretation
of a column whose meaning isn't documented in the actual vendor schema
file. Force the agent to write a short paragraph stating its assumption
about every column it consumes; review the paragraph before code runs.

**Non-determinism that breaks reproducibility.** Two runs of the same
agent against the same data produce subtly different code. If that code
is in the pipeline that produces the numbers in a paper, the paper is no
longer reproducible from `git pull && make` — it is reproducible from
`git pull && make && hope`. The fix is to keep the agent out of the
critical path: use it as a *scratchpad* during development, then commit
the deterministic code it landed on. Pin LLM versions and prompts when
the agent itself is part of the pipeline (e.g. for the fuzzy-entity
matcher above); log every prompt and response so the run can be
re-executed exactly.

**Plausible-but-wrong fix proposals on noisy fields.** When an
intraday-volume series has a single spike that's *plausibly* a real
trade or *plausibly* a feed error, the agent's first instinct is to
"clean" it — typically by interpolating across the spike. That is the
wrong call about half the time: the spike is sometimes a real fat
print that you *want* in the dataset. The fix is to instruct the agent
to *flag* and *propose* rather than *apply*; the apply step is a human
decision logged in the cleaning notebook.

**Bugs that don't crash anything.** A subtle one. The agent's code rarely
throws — it tends to silently coerce, fill, or skip. If you wrap an agent
output in a `try/except`, you have made the problem worse, not better.
The discipline that helps: prefer *strict* code (raise on unexpected
schema, type-check inputs at the function boundary, no implicit nulls)
and let the agent's output crash loudly when it's wrong.

## A reproducible-pipeline discipline that works

After enough scar tissue, the operating pattern I have settled on for
quant data work with an agent in the loop:

1. **Discovery is agent-friendly.** Use the agent for the first pass at
   anything that involves *reading* messy data — schema profiling,
   sample-driven parsing, candidate-anomaly enumeration. Embrace the
   non-determinism here; it's exploration, not artefact.

2. **Code is human-reviewed and committed.** Whatever the agent writes
   becomes a PR I read line-by-line before merging. The PR description
   includes the prompts that produced it. If the agent re-wrote
   something tomorrow, I'd want to see the diff against today's version.

3. **Pipelines are deterministic.** The agent's *output* goes into the
   tree; the agent itself does not run as part of the build. The one
   exception is when the agent's role is structural — e.g. the
   fuzzy-entity matcher — in which case the LLM call is wrapped in a
   cache that keys on (prompt, model version, input hash) and replays
   from cache on subsequent runs. Reproducibility is preserved as long
   as the cache is committed.

4. **Strict types and loud failures.** No silent coercion. Schema
   checks at the read boundary. Tests that assert *known* properties of
   the cleaned data (column ranges, expected null fractions, alignment
   to a calendar). The agent's code path is invisible until the
   property-tests fire on the cleaned output.

5. **Human-confirm gates on apply-vs-flag decisions.** "Clean the
   spike" is a human decision; the agent gets to propose it but not
   apply it. Anomaly review happens in a notebook with the proposed
   change and the data context side by side.

6. **Documented prompts.** Every non-trivial agent intervention is
   recorded in a `prompts/` directory in the project, with the date,
   model version, and a short note on what the agent was asked to do
   and what part of its output was kept. This is the analogue of the
   research notebook — it is what lets me reconstruct, three months
   later, *why* a particular cleaning rule looks the way it does.

## What I am no longer doing

A short list of things I tried in the first few months and have since
walked back:

- **Letting the agent run the pipeline.** This loses determinism for no
  speedup once the pipeline is built. Build the pipeline with the
  agent's help; run it without.
- **Putting an LLM call inside an inner loop.** Per-row LLM calls
  produce inscrutable cost, inscrutable latency, and inscrutable
  failure modes. If the loop has 10,000 rows, write the deterministic
  function once and apply it 10,000 times.
- **Trusting the agent on numerical accuracy.** Agents are great at
  setting up a Monte Carlo but bad at noticing that the Monte Carlo
  has a $\sqrt{T}$ scaling error in the variance. Verify numerics
  against textbook closed-forms or independent reference implementations.

## Why I keep using agents anyway

A balance-sheet question: given the failure modes above, is the agent
in the loop actually a net win for quant data work? My honest answer is
*yes*, with a strong caveat: the win is concentrated in the *discovery*
and *boilerplate* phases. The *production* phases (running the
pipeline that produces the numbers in a report) want to be
deterministic, type-checked, and human-readable, and the agent's
contribution there is only as a co-author of the human-reviewed code.

The most important reframing for me: the agent is a *teammate*, not a
*service*. I would not ship a backtest produced by a teammate who
silently coerces my data, refuses to crash on unexpected input, and
writes different code every time. I do not ship one produced by an
agent that does the same.

The discipline is the value-add. A team that has the discipline and uses
the agents will outpace a team that has either *only* discipline or
*only* the agents.

## Sources

The discipline above is informed by:

- Anthropic (2026). *Best practices for building Claude-powered agents.*
  The official guidance on prompt design, tool use, and the agent-vs-
  chatbot distinction.[^anthropic]
- Sambasivan, N. et al. (2021). *"Everyone wants to do the model work,
  not the data work": data cascades in high-stakes AI.* CHI 2021. The
  empirical study of how upstream data mistakes compound downstream,
  whose framing of *data cascades* has become the standard reference.[^sambasivan]
- Liu, N. F. et al. (2023). *Lost in the middle: how language models
  use long contexts.* TACL 2024. The empirical evidence behind the
  context-window failure mode that hits big-CSV inspection.[^liu]

---

[^anthropic]: Anthropic. *Building agents.* claude.ai/docs/agents-best-practices.
[^sambasivan]: Sambasivan, N., Kapania, S., Highfill, H., Akrong, D.,
    Paritosh, P., & Aroyo, L. M. (2021). "Everyone wants to do the
    model work, not the data work": data cascades in high-stakes AI.
    *Proceedings of the 2021 CHI Conference on Human Factors in
    Computing Systems*.
[^liu]: Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M.,
    Petroni, F., & Liang, P. (2024). Lost in the middle: how language
    models use long contexts. *Transactions of the Association for
    Computational Linguistics*, 12, 157-173.
