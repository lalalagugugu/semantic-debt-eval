# semantic-layer-benchmark

A reproducible text-to-SQL benchmark that quantifies the value of giving an LLM
a small hand-authored semantic-layer markdown alongside the raw schema DDL.

## Question

> *Does adding a 4 KB hand-authored "semantic layer" markdown — describing
> business conventions, calculated metrics, default fact tables, and
> snapshot-data caveats — measurably improve text-to-SQL accuracy compared to
> giving the model only the raw DDL?*

## TL;DR

Yes — across three top-tier frontier models (Claude Opus 4.7, Claude Sonnet 4.6,
OpenAI GPT-5.4) the semantic layer adds **+17 to +23 percentage points** of
analytical accuracy on a 100-question Contoso retail benchmark, with paired
McNemar exact p < 0.002 in every case.

With the semantic layer, all three models converge to ~ 68 % accuracy and are
statistically indistinguishable. Without it, all three sit at ~ 46–51 % and are
also statistically indistinguishable. **Whether the model has the semantic
layer matters more than which model it is.**

> **The 68 % figure is a floor, not a ceiling.** The semantic layer in this
> repo was hand-authored once to demonstrate the *presence* of the effect,
> not iterated to maximize it. Adding named measures for percentile / corr /
> threshold-rank metrics, worked examples for ambiguous business terms, and a
> handful of anti-patterns from observed failures will push the +Sem cluster
> meaningfully higher. We left those gains on the table to keep the
> comparison fair. Swap in your own MD and rerun — see "Adding a new model"
> below; the same workflow applies to swapping the MD.

See [`REPORT.md`](./REPORT.md) for the full study.

## Architecture

For each model under test there are two configurations:

| Config | Prompt = |
|---|---|
| **raw** | system prompt + `SHOW CREATE TABLE` DDL for `retail.*` + the question |
| **+Sem** | same as raw, but with `fixtures/semantic_layer.md` prepended |

A single execution pipeline:

1. Reference SQL (from the benchmark JSON) is run against ClickHouse to produce
   the ground-truth rows.
2. Each model under test is given the prompt above and produces SQL.
3. The candidate SQL is executed against ClickHouse.
4. A judge (Claude Sonnet 4.6, different from any model under test) compares
   candidate rows vs reference rows and emits two verdicts:
   - **strict** — row-level match
   - **analytical** — OLAP-aware (accepts grouped breakdowns that aggregate to
     the reference scalar, decimal-vs-percentage unit equivalents, etc.)
5. Aggregate accuracy + 95 % Wilson CI + paired McNemar exact tests across
   models.

## Quickstart

### Prerequisites

- Python 3.11
- [`uv`](https://docs.astral.sh/uv/)
- `claude` CLI (Anthropic Claude Code, ≥ 2.x), authenticated
- `codex` CLI (OpenAI Codex), authenticated — only if you want GPT-5.4 results
- ClickHouse instance with the Contoso retail dataset

### Setup

```bash
cp .env.example .env
# edit .env with your CLICKHOUSE_* values
uv sync
uv run --env-file .env python scripts/ping_clickhouse.py   # expect "ClickHouse OK"
uv run --env-file .env python scripts/fetch_schema.py      # writes fixtures/retail_schema.sql
```

### Run a full benchmark

```bash
RUN_ID=$(date -u +%Y%m%d-%H%M%S)

# 1. Reference (executes the benchmark's expected SQL once)
uv run --env-file .env python scripts/run_reference.py --run-id "$RUN_ID"

# 2. The systems under test (parallelizable — each writes its own dir)
uv run --env-file .env python scripts/run_claude.py --run-id "$RUN_ID" --model claude-opus-4-7
uv run --env-file .env python scripts/run_claude.py --run-id "$RUN_ID" --model claude-opus-4-7 --semantic
uv run --env-file .env python scripts/run_claude.py --run-id "$RUN_ID" --model claude-sonnet-4-6
uv run --env-file .env python scripts/run_claude.py --run-id "$RUN_ID" --model claude-sonnet-4-6 --semantic
uv run --env-file .env python scripts/run_codex.py  --run-id "$RUN_ID" --model gpt-5.4
uv run --env-file .env python scripts/run_codex.py  --run-id "$RUN_ID" --model gpt-5.4 --semantic

# 3. Score every (system, question) pair with the judge
uv run --env-file .env python scripts/score_run.py --run-id "$RUN_ID"

# 4. Print the report — auto-discovers all systems with scoring data
uv run --env-file .env python scripts/report_run.py --run-id "$RUN_ID"
```

Runs are resumable — each per-question JSON file is written atomically and
skipped on re-run. A full 6-system run takes ~ 25–35 min wall-clock when
launched in parallel.

### Adding a new model

```bash
uv run --env-file .env python scripts/run_claude.py --run-id "$RUN_ID" --model NEW_MODEL_ID
uv run --env-file .env python scripts/run_claude.py --run-id "$RUN_ID" --model NEW_MODEL_ID --semantic
uv run --env-file .env python scripts/score_run.py --run-id "$RUN_ID"
uv run --env-file .env python scripts/report_run.py --run-id "$RUN_ID"
```

The reporter auto-discovers any `runs/<RUN_ID>/scoring/<system>/` directory
that has verdict files in it, so new models appear in the headline table and
the McNemar matrix without code changes.

## Reasoning effort

All systems are run at **medium** reasoning effort by default:

- Claude (`claude -p`): `--effort medium`
- Codex (`codex exec`): `-c model_reasoning_effort="medium"`

This is set on each runner so accuracy / latency / token comparisons are not
confounded by some models thinking more than others.

## Output layout

```
runs/<RUN_ID>/
├── reference/q001.json … q100.json
├── claude_claude_opus_4_7_raw/q001.json …
├── claude_claude_opus_4_7_semantic/q001.json …
├── claude_claude_sonnet_4_6_raw/q001.json …
├── claude_claude_sonnet_4_6_semantic/q001.json …
├── codex_gpt_5_4_raw/q001.json …
├── codex_gpt_5_4_semantic/q001.json …
└── scoring/
    ├── claude_claude_opus_4_7_raw/q001.json …    # {verdict, analytical_verdict, reason, judge_tokens, ...}
    ├── claude_claude_opus_4_7_semantic/q001.json …
    └── …
```

Each per-question JSON contains the generated SQL, the executed rows, latency,
input/output token counts, and any error.

## Benchmark questions

100 hand-authored natural-language analyst questions across 5 difficulty tiers
(20 per tier: simple → medium → complex → advanced → expert). Each has a
reference SQL that executes against the Contoso `retail.*` schema in
ClickHouse. See [`text_to_sql_benchmark.json`](./text_to_sql_benchmark.json).

| Tier | What it tests |
|---|---|
| simple | Single table, COUNT/SUM, basic filter |
| medium | 2–3 table joins, GROUP BY, HAVING, date functions |
| complex | Window functions, MAX(date) per group, snapshot semantics |
| advanced | Multiple CTEs, scenario pivots, cohort/LTV filters, MAPE |
| expert | Ambiguous business terms, recursive CTEs, business-context inference |

## Semantic layer

`fixtures/semantic_layer.md` (~ 9 KB / ~ 2.2 K tokens) is a hand-authored
analyst guide covering:

- Which fact table to default to (online vs all-channel sales)
- Snapshot-data caveat for FactInventory (use MAX(DateKey) per (product, store))
- String-boolean enum values (`IsWorkDay = 'WorkDay'/'WeekEnd'`, etc.)
- Implicit defaults (`PromotionKey = 1` = "No Discount")
- Calculated metric formulas (margin %, return rate, same-store growth,
  inventory turnover, recency segments)
- Join paths and customer-vs-store geography conventions
- Time anchoring (dataset latest date is 2009-12-31)
- 13 explicit agent-steering rules

Swap this file to test your own semantic-layer authoring against this
benchmark.

## Methodology and statistics

See [`REPORT.md`](./REPORT.md) for full methodology, the 6-way result table,
within-model McNemar tests, the cross-model McNemar matrix, cost / latency
comparison, and limitations.

## License

MIT.

## 本地来源记录

来源：https://github.com/cubedevinc/semantic-layer-benchmark

上游提交：`4c37310f9fae65255f6d0015475b430ceea3ab1f`

取得日期：2026-10-14。以上上游 README 原文保留；本节为本地追加说明。许可情况及保留文件见 [NOTICE.md](NOTICE.md)。
