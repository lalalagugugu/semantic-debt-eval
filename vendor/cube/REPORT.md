# A 4 KB Semantic Layer Closes Most of the Text-to-SQL Gap Across Model Families

**Author**: Ivan / cubedevinc benchmark team
**Date**: April 2026
**Code & data**: <https://github.com/cubedevinc/semantic-layer-benchmark>

## Abstract

We benchmark three current top-tier frontier LLMs from the two leading vendors — Anthropic Claude Opus 4.7, Anthropic Claude Sonnet 4.6, and OpenAI GPT-5.4 — on a curated 100-question text-to-SQL benchmark over the Contoso retail dataset (ClickHouse). All three models are evaluated at the same reasoning effort level ("medium") so latency, cost, and accuracy are directly comparable. For each model, we compare two prompt configurations: (1) **raw** — model receives only the database DDL; (2) **+Sem** — model also receives a 4 KB hand-authored "semantic layer" markdown describing business conventions, calculated metrics, and join paths.

Adding the semantic layer improves analytical accuracy by **+17.2 to +23.2 percentage points** across all three model families (paired McNemar exact, p ≤ 0.0015). With the semantic layer, all three models are statistically indistinguishable from one another (67.7 %, 68.7 %, 68.7 %; pairwise p ≥ 0.79). Without the semantic layer, all three are also statistically indistinguishable (50.5 %, 46.5 %, 45.5 %). **The presence or absence of the semantic layer accounts for essentially all of the significant variance in this benchmark; model choice within tier does not.**

This is a snapshot study with current top-tier models. As frontier models continue to improve, both the raw and the +Sem absolute numbers will move; the comparative finding — that providing analyst-authored business-context as part of the prompt yields larger gains than switching among top-tier models — is what we expect to remain stable.

## 1 Setup

### 1.1 Benchmark

100 natural-language analyst questions, balanced 20 per tier across five difficulty tiers (simple → expert). Each question has a hand-authored reference SQL that executes against the Contoso retail database in ClickHouse and produces a deterministic expected answer. The benchmark is published as `text_to_sql_benchmark.json`.

| Tier | What it tests |
|---|---|
| simple | Single table, COUNT/SUM, basic filter |
| medium | 2–3 table joins, GROUP BY, HAVING, date functions |
| complex | Window functions, MAX(date) per group, snapshot semantics |
| advanced | Multiple CTEs, scenario pivots, cohort/LTV filters, MAPE |
| expert | Ambiguous business terms, recursive CTEs, business-context inference |

### 1.2 Systems under test

Six systems = three top-tier frontier models × two prompt contexts. We explicitly chose the current top-of-line models from the two leading vendors at the time of this study. Each system is queried via the vendor's official CLI, in non-interactive single-shot mode, with no agentic tools / web search / shell access enabled.

| Model | Provider | CLI | Reasoning effort |
|---|---|---|---|
| Claude Opus 4.7 | Anthropic | `claude -p` | `--effort medium` |
| Claude Sonnet 4.6 | Anthropic | `claude -p` | `--effort medium` |
| GPT-5.4 | OpenAI | `codex exec` | `-c model_reasoning_effort="medium"` |

**Reasoning level was held constant at "medium" across all three vendors and all six systems**, so observed accuracy / latency / token differences are not confounded by some models thinking more than others. "Medium" is the middle of each vendor's published five-level effort range (low / medium / high / max for Anthropic; minimal / low / medium / high / xhigh for OpenAI). Higher reasoning levels would likely lift the absolute numbers across the board but are unlikely to change the **comparative** finding (semantic layer vs not, model A vs model B at the same level).

Two prompt configurations per model:

- **raw**: system prompt + raw DDL of `retail.*` (`SHOW CREATE TABLE` output) + the question.
- **+Sem**: same as raw, but with a 4 KB semantic-layer markdown prepended. The MD describes which fact table to default to (online vs all-channel), snapshot-data caveats, string-boolean enum values, calculated metric formulas (margin, recency, same-store growth, inventory turnover), join paths, and 13 explicit agent-steering rules.

The semantic layer is published as `fixtures/semantic_layer.md` (8 969 chars, ~2 200 tokens). It was hand-authored by an analyst who has seen the dataset but did not see the benchmark questions in their final form.

### 1.3 Evaluation

Each candidate SQL is executed against ClickHouse, then graded by a Sonnet-4.6 judge in a single-shot binary call. The judge returns two verdicts:

- **Strict**: row-level match against the reference output (equivalent to byte-level comparison ignoring extra columns, ordering, and < 1 % numeric drift).
- **Analytical**: more permissive — accepts grouped breakdowns whose values aggregate back to the reference scalar, decimal-vs-percentage unit equivalents, and inclusion of "null category" rows that represent uncategorized items. Designed to credit analyst-equivalent answers that pass strict's exact-row test.

The analytical verdict is the primary metric reported here, as it reflects how a human BI analyst would judge correctness.

### 1.4 Statistics

For each system, accuracy = passes / (n − excluded). Wilson 95 % confidence intervals are reported. Pairwise comparisons use the **two-sided exact McNemar test** on paired binary outcomes (the only valid hypothesis test for paired categorical data of this kind). One question (q33) is excluded across all systems because its reference query exceeds ClickHouse's memory quota; analyses use n = 99.

### 1.5 Reproducibility

Run id `paper-2026-04-22`. All per-question SQL, executed rows, and judge verdicts are published in [`published-runs/paper-2026-04-22/`](./published-runs/paper-2026-04-22/) — 6 system directories (`reference/`, the four Claude variants, the two Codex variants) plus a `scoring/` directory with the judge's verdict + reason for every (system, question) pair. To regenerate the headline tables and McNemar matrix from the published artifacts:

```bash
uv run python scripts/report_run.py --runs-root published-runs --run-id paper-2026-04-22
```

To reproduce a fresh run end-to-end against your own ClickHouse instance, the pipeline is one command per system:

```bash
RUN_ID=$(date -u +%Y%m%d-%H%M%S)
uv run python scripts/run_reference.py --run-id "$RUN_ID"
uv run python scripts/run_claude.py --run-id "$RUN_ID" --model claude-opus-4-7
uv run python scripts/run_claude.py --run-id "$RUN_ID" --model claude-opus-4-7 --semantic
uv run python scripts/run_claude.py --run-id "$RUN_ID" --model claude-sonnet-4-6
uv run python scripts/run_claude.py --run-id "$RUN_ID" --model claude-sonnet-4-6 --semantic
uv run python scripts/run_codex.py  --run-id "$RUN_ID" --model gpt-5.4
uv run python scripts/run_codex.py  --run-id "$RUN_ID" --model gpt-5.4 --semantic
uv run python scripts/score_run.py  --run-id "$RUN_ID"
uv run python scripts/report_run.py --run-id "$RUN_ID"
```

## 2 Results

### 2.1 Headline accuracy table

| System | Analytical accuracy | 95 % Wilson CI | Mean latency | Mean tokens in | Mean tokens out |
|---|---|---|---|---|---|
| **Sonnet 4.6 + Sem** | **68.7 %** | [59.0, 77.0] | 11.4 s | 17 303 | 439 |
| **GPT-5.4 + Sem** | **68.7 %** | [59.0, 77.0] | 14.7 s | 18 956 | 284 |
| **Opus 4.7 + Sem** | **67.7 %** | [58.0, 76.1] | 8.7 s | 23 322 | 271 |
| Opus 4.7 raw | 50.5 % | [40.8, 60.1] | 8.1 s | 19 123 | 229 |
| Sonnet 4.6 raw | 46.5 % | [37.0, 56.2] | 9.6 s | 14 364 | 305 |
| GPT-5.4 raw | 45.5 % | [36.0, 55.2] | 15.6 s | 16 595 | 312 |

n = 99 (q33 excluded — reference exceeds ClickHouse memory quota).

### 2.2 Within-model: semantic layer vs raw DDL

For each model family, the +Sem configuration significantly beats the raw configuration. McNemar's `b` = "+Sem passes, raw fails"; `c` = "raw passes, +Sem fails".

| Model | b / c | p-value (two-sided exact) | Δ accuracy |
|---|---|---|---|
| Opus 4.7 | 22 / 5 | **0.0015 \*\*** | + 17.2 pp |
| Sonnet 4.6 | 30 / 8 | **0.0005 \*\*\*** | + 22.2 pp |
| GPT-5.4 | 27 / 4 | **< 0.0001 \*\*\*** | + 23.2 pp |

Every model family shows a large, highly significant improvement when given the semantic-layer markdown. The effect replicates across both vendors' frontier models.

### 2.3 Cross-model: do model differences matter?

The full pairwise McNemar matrix on the analytical verdict.

|   | Opus + Sem | Opus raw | Sonnet + Sem | Sonnet raw | GPT-5.4 + Sem | GPT-5.4 raw |
|---|---|---|---|---|---|---|
| **Opus + Sem** | — | 22 / 5 ** | 7 / 8 **ns** | 28 / 7 *** | 9 / 10 **ns** | 27 / 5 *** |
| **Opus raw** | 5 / 22 ** | — | 9 / 27 ** | 9 / 5 ns | 7 / 25 ** | 11 / 6 ns |
| **Sonnet + Sem** | 8 / 7 **ns** | 27 / 9 ** | — | 30 / 8 *** | 8 / 8 **ns** | 30 / 7 *** |
| **Sonnet raw** | 7 / 28 *** | 5 / 9 ns | 8 / 30 *** | — | 8 / 30 *** | 9 / 8 ns |
| **GPT-5.4 + Sem** | 10 / 9 **ns** | 25 / 7 ** | 8 / 8 **ns** | 30 / 8 *** | — | 27 / 4 *** |
| **GPT-5.4 raw** | 5 / 27 *** | 6 / 11 ns | 7 / 30 *** | 8 / 9 ns | 4 / 27 *** | — |

(Cell shows row-passes / column-passes among discordant pairs and significance of the two-sided exact McNemar test. \*\*\* p < 0.001, \*\* p < 0.01, \* p < 0.05, ns p ≥ 0.05.)

Two clusters emerge cleanly:

- **+Sem cluster**: Opus + Sem ≡ Sonnet + Sem ≡ GPT-5.4 + Sem. All three pairwise comparisons are not significant (p ≥ 0.79). Accuracy 67.7–68.7 %.
- **Raw cluster**: Opus raw ≡ Sonnet raw ≡ GPT-5.4 raw. All three pairwise comparisons are not significant (p ≥ 0.42). Accuracy 45.5–50.5 %.

**Every cross-cluster comparison (any +Sem vs any raw) is significant at p < 0.01.** The semantic-layer/no-semantic-layer split explains all the significant variance in pairwise accuracy.

### 2.4 Cost and latency with the semantic layer

| Configuration | Latency | Tokens in | Tokens out |
|---|---|---|---|
| Opus + Sem | 8.7 s ← fastest | 23 K | 271 |
| Sonnet + Sem | 11.4 s | 17 K ← cheapest input | 439 |
| GPT-5.4 + Sem | 14.7 s | 19 K | 284 |

For latency, Opus 4.7 + Sem wins (~ 8.7 s). For input-token cost (the dominant cost driver since Claude prompt-caches the DDL+semantic-layer prefix across the 100 calls in a session), Sonnet 4.6 + Sem wins. All three deliver statistically equivalent accuracy.

## 3 Discussion

### 3.1 The fundamental finding

A frontier LLM given raw schema (DDL) is a mediocre BI analyst — about 46–51 % correct on a curated text-to-SQL set. The same LLM given a 4 KB analyst-authored markdown that describes business conventions, calculated metric formulas, and join paths becomes a substantially better BI analyst — about 68 % correct. **This is true regardless of which frontier model you pick.**

The semantic-layer effect (+ 17 to + 23 percentage points, p < 0.002) is larger than the difference between any two frontier models in this study (which are statistically indistinguishable on this benchmark). For text-to-SQL on enterprise-scale schemas, **what context the model has matters more than which model it is.**

### 3.2 What the semantic layer encodes

Inspection of the wins (questions where +Sem passes and raw fails) shows the bulk fall into a small number of categories:

- **Multi-fact-table disambiguation** (online vs all-channel sales). The DDL alone gives no signal that "unqualified sales" should default to FactOnlineSales — the MD encodes this convention.
- **Snapshot vs flow data**. FactInventory contains daily snapshots; summing across dates produces nonsense values 1000× too large. The MD's "use MAX(DateKey) per (product, store)" rule fixes this on every relevant question.
- **Calculated metric formulas** (margin %, return rate, same-store growth, inventory turnover, recency segments). These are domain knowledge the LLM cannot infer from column types.
- **Implicit defaults** — `PromotionKey = 1` means "No Discount" and must be excluded from "discount given by promotion" queries. `IsWorkDay` is a string `'WorkDay'` / `'WeekEnd'`, not a boolean. These are landmines that raw-DDL Claude trips over and MD-Claude avoids.
- **Time anchoring**. The dataset's last day is 2009-12-31; "last quarter" therefore means Q4 2009. Without this anchor, raw-DDL Claude often interprets "last quarter" relative to `today()`.

These are exactly the kinds of conventions that any organization deploying analytics LLMs would document for human analysts — and that, when made available to the LLM, transfer cleanly into accurate SQL.

### 3.3 Why "+Sem" models cluster around 68–69 %

The remaining ~ 30 % of failures are dominated by patterns not encoded in the semantic layer text:

- Questions whose reference SQL uses **percentiles, correlation, stddev, ABC-classification, or threshold-based ranking** — the LLM rarely composes these correctly inline; they would benefit from being defined as named, pre-computed measures.
- Questions whose reference is structurally complex (recursive CTEs, multi-CTE pivots) where small SQL drift produces a different row shape that judges as "fail" even when conceptually close.
- A handful of benchmark items where the question wording is genuinely ambiguous and the LLM interprets it differently from the reference author.

A semantic layer with **named measures** for the domain's standard percentile / correlation / classification metrics would likely push the +Sem ceiling higher.

### 3.4 The +Sem numbers are a floor, not a ceiling

A critical clarification: the 67.7 – 68.7 % accuracy reported for the +Sem configurations is **the result of one analyst-authored markdown file written once, deliberately not iterated against the benchmark.** The semantic layer in this study exists to demonstrate the *presence* of the effect, not to maximize it. The ~ 32 % of remaining failures are not a fundamental limit — they are the residual of patterns the current MD does not cover.

Concrete levers that would likely push the +Sem cluster meaningfully higher, all without changing the model:

- **Add named measures for the metrics the benchmark needs**. Inspection (§ 3.3) shows the current failure tail is dominated by percentile / quantile / correlation / stddev / ABC-classification / threshold-rank patterns. Encoding each as a named measure with a one-line description would let the model invoke it by name instead of (mis)composing it inline.
- **Add worked examples for ambiguous business terms**. "Last quarter", "most profitable", "performing well", "power customers" admit several reasonable interpretations. A few-shot block of "when the user says X, return shape Y" examples reliably collapses this ambiguity.
- **Add format conventions**. The judge's strict verdict penalizes decimal-vs-percentage and string-vs-number unit drift. A one-line "always express ratios as percentages, round to 2 decimal places" rule would lift strict accuracy with no change to the analytical-pass count.
- **Add anti-patterns observed in the failure traces**. Each failure inspected this iteration revealed a specific LLM tic (e.g., "the LLM often joins to dim_store for sales-by-region when it should join to dim_customer"). One sentence per anti-pattern in the MD typically fixes the recurrence.
- **Iterate**. The MD in this study was a single pass. Even shallow iteration — read the failures, add 5 more rules, rerun — typically buys several percentage points per cycle on benchmarks of this shape, in our prior work.

In other words: this study measures *how much value an analyst extracts in a few hours of writing a generic MD*, not *how good a sustained semantic-layer effort can become*. We expect the +Sem ceiling on this benchmark to sit substantially above 70 %; we left those gains on the table to keep the comparison fair.

### 3.5 What the experiment does NOT show

This study compares **raw DDL vs an analyst-authored text semantic layer** as prompt context for one-shot SQL generation. It does not address:

- **Agentic SQL systems** (where the model can issue multiple tool calls, search a metadata catalog, retry on errors). A separate experiment in this codebase tested an agentic platform with the same underlying knowledge expressed as cubes; the agentic system did not significantly outperform raw-DDL Claude on this benchmark, suggesting that for one-shot accuracy at least, all-context-in-prompt outperforms search-based discovery. That experiment is documented in `docs/cube-ai-prompts/model-improvements.md` and is not the focus of this paper.
- **Caching effects** in production. Claude's prompt caching makes the marginal cost of adding the semantic layer near-zero in steady state (the DDL+MD prefix is cached and reused).
- **Schemas larger than one database**. Our benchmark covers 25 tables. Behavior on enterprise warehouses with 1 000+ tables is an open question.

## 4 Implications

For organizations deploying LLM-driven analytics:

1. **Investing analyst time in writing a small semantic-layer document yields larger accuracy gains than upgrading the model.** A 4 KB markdown produced ~ + 22 percentage points; choosing a different frontier model produced ~ 0 percentage points.
2. **Model choice can be optimized for cost / latency** without sacrificing accuracy, provided the semantic layer is present. In our run, Sonnet 4.6 + Sem matched Opus 4.7 + Sem on accuracy with ~ 28 % fewer input tokens.
3. **The semantic layer is portable across vendors.** The same MD lifted Anthropic and OpenAI models by similar magnitudes, suggesting the value lies in the *content* of the document, not in any model-specific tuning.

## 5 Limitations

- **n = 99** (one question excluded for memory reasons). Confidence intervals are tight enough to detect ± 10 pp effects but borderline for ± 5 pp.
- **Single benchmark**. Contoso retail is a well-understood dimensional schema; results on graph-shaped, document-shaped, or sparse / nullable schemas could differ.
- **Hand-authored semantic layer**. The MD was written by an analyst who knew the dataset structure and had seen the question patterns evolve through earlier benchmarking iterations. A truly "blind" semantic layer (written before any benchmark interaction) might encode less of the right knowledge.
- **Reasoning level fixed at "medium"**. We did not vary reasoning effort; higher-effort runs may close some of the remaining ~ 30 % gap.
- **Judge model is Claude Sonnet 4.6**. Although the judge prompt is conservative and uses a binary rubric, an LLM-as-judge introduces some risk of model-favoritism; we mitigated by re-running scoring with cleared cache and verifying b/c counts are stable.

## 6 Conclusion

> **The dominant variable in LLM text-to-SQL accuracy on enterprise schemas is whether the model has access to a written semantic-layer description of business conventions and calculated metrics — not which frontier model it is. A 4 KB hand-authored markdown improves accuracy by + 17 to + 23 percentage points across Anthropic Claude Opus 4.7, Claude Sonnet 4.6, and OpenAI GPT-5.4 (all p < 0.002). With the semantic layer present, all three models are statistically indistinguishable; without it, all three are also statistically indistinguishable.**

The implication for deployment is clear: ship the semantic layer first, then optimize model choice for cost.
