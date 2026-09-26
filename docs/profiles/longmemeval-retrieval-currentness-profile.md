# LongMemEval Retrieval and Currentness Profile

Status: bounded external benchmark profile for #516 under #498/#519.

## Source binding

```text
upstream repository: xiaowu0162/LongMemEval
inspected revision:  9e0b455f4ef0e2ab8f2e582289761153549043fc (repository license: MIT)
dataset distribution: huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
dataset card license: mit (declared independently on the dataset card)
headline input:      longmemeval_s_cleaned.json (277,383,467 bytes as listed by the Hub)
```

The upstream release contains 500 questions spanning single-session user/assistant/preference recall, multi-session reasoning, knowledge updates, temporal reasoning, and abstention (`_abs`) variants. Records bind questions to timestamped history sessions through `haystack_session_ids`, `haystack_dates`, `haystack_sessions`, `answer_session_ids`, and turn-level `has_answer` labels.

This profile does not vendor the external dataset. A real run consumes an explicitly supplied local LongMemEval JSON artifact and records its SHA-256 digest and size. `longmemeval_oracle.json` removes the retrieval challenge and is not a headline retrieval input.

## Replicated upstream semantics

Corpus construction, gold labels, question exclusion, and metric arithmetic replicate the bound revision exactly:

| Upstream (`@9e0b455`) | Replicated behavior |
| --- | --- |
| `run_retrieval.py::process_item_flat_index` | Only **user** turns are indexed. A session item is the space-joined user contents; a turn item is one user turn with id `<session_id>_<turn_index+1>`. An `answer` session (or turn) with no user `has_answer` is relabelled `noans`. |
| `run_retrieval.py` `correct_docs` | Gold items are corpus ids containing `answer`. |
| `run_retrieval.py::main` averaging | Questions whose id contains `_abs` are excluded, and so are questions with no user-side `has_answer` target (for example, assistant-only evidence). |
| `eval_utils.py::evaluate_retrieval` | `recall_any@k`, `recall_all@k`, and `ndcg_any@k`, where `ndcg_any` is binary-relevance NDCG normalized by the ideal ordering of *all* gold items, with upstream's `dcg` weighting (`rel₁ + Σ relᵢ / log₂ i`, i ≥ 2). |
| `eval_utils.py::evaluate_retrieval_turn2session` | Turn runs also report `turn_to_session` metrics with upstream's distinct-session k expansion. |

Metrics are computed at k ∈ {1, 3, 5, 10, 30, 50}. The headline families follow upstream `print_retrieval_metrics.py`:

- session: `recall_all@5`, `ndcg_any@5`, `recall_all@10`, `ndcg_any@10`;
- turn: the same, plus `recall_all@50` and `ndcg_any@50`.

Parity with upstream `evaluate_retrieval`, `evaluate_retrieval_turn2session`, and `process_item_flat_index` was checked differentially against the pinned upstream source: randomized full and truncated rankings, and randomized upstream-shaped haystacks. Focused unit tests pin representative cases.

A backend that returns fewer items than the corpus is scored against its returned list. Unreturned items count as not retrieved, so a backend earns no credit it did not produce.

## Separately reported surfaces

```text
headline retrieval metrics (upstream families, scored questions only)
by question type
currentness: knowledge-update metrics + latest-gold-ranked-first diagnostic
abstention diagnostic (returned-any rate; not an upstream metric)
failures: runtime and ingestion, counted, never dropped
Agent Memory governance: candidates, admitted, refusal reasons, unmapped admissions
timing: wall seconds; Agent Memory ingest/recall seconds
execution: Agent Memory revision + dirty flag, package version, Python, platform, start/end
```

`latest_gold_ranked_first` is profile-local: among scored knowledge-update questions whose gold items span two or more dates, it is the fraction where the most recently dated gold item is returned ahead of every older gold item. It is a currentness *retrieval-ordering* signal, not answer correctness. Resource consumption (memory, token, compute cost) is `not_measured`.

## Backends

```text
no_memory        returns nothing
lexical_overlap  deterministic token-overlap/Jaccard baseline (profile-local)
agent_memory     public AgentMemory facade
```

All three consume the same frozen input and the same corpus items. `agent_memory` retains every item through ordinary governed commit, under a fresh tenant/scope per question. It then invokes `recall(question)`: candidate generation followed by the canonical governed admission pass. Benchmark item ids never enter Agent Memory, because target references are opaque positional handles. Ids are recovered only from admitted fact UUIDs. A runtime exception is recorded per question and the question scores as a miss.

Upstream's `flat-bm25` and dense retrievers are not reproduced. Results are therefore comparable across this profile's backends, not to paper retriever tables.

## Answer-quality boundary

LongMemEval's upstream QA evaluation is a separate model-dependent answer evaluator. This profile does not invoke it.

```text
retrieval/currentness result != LongMemEval QA score != answer-generation quality
```

## Running

Synthetic smoke fixture: evaluator/adapter conformance only, never external evidence.

```bash
PYTHONPATH=reference python reference/run_longmemeval.py
```

The fixture is upstream-shaped. It covers `answer_` session ids, a `noans` relabel, a knowledge update across two dated sessions, a multi-session question, an assistant-only question (no user target), and an `_abs` question that still carries `answer_session_ids`.

Bounded external subset (deterministic, not cherry-picked: SHA-256 of `seed ‖ NUL ‖ question_id`, first N, source order preserved):

```bash
PYTHONPATH=reference python reference/run_longmemeval.py \
  --input /path/to/longmemeval_s_cleaned.json --corpus-class external_frozen \
  --subset-size 50 --output longmemeval-s-subset50.json
```

Full LongMemEval_S:

```bash
PYTHONPATH=reference python reference/run_longmemeval.py \
  --input /path/to/longmemeval_s_cleaned.json --corpus-class external_frozen \
  --omit-rows --output longmemeval-s-full.json
```

`external_frozen` only means that the supplied artifact is treated as a frozen external input. It does not claim paper-result reproduction or QA parity.

## Execution status

| Run | Status |
| --- | --- |
| Synthetic smoke | COMPLETE (conformance only) |
| LongMemEval_S deterministic subset (50) | COMPLETE (integration shakedown; not the headline) |
| LongMemEval_S full (500) | **COMPLETE** |
| LongMemEval_M | NOT RUN |
| Upstream QA (model-judged) | NOT RUN (no reader/judge credentials provisioned) |
| Store size on disk | NOT MEASURED (per-question stores are temporary) |

### LongMemEval_S full run: 2026-09-25

```text
input:      longmemeval_s_cleaned.json, 277,383,467 bytes
            sha256 d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442
            (equals the Hub's published LFS digest)
dataset:    xiaowu0162/longmemeval-cleaned@98d7416c24c778c2fee6e6f3006e7a073259d48f
upstream:   xiaowu0162/LongMemEval@9e0b455f4ef0e2ab8f2e582289761153549043fc
revision:   Agent Memory f73b872c7f062d0b1e80b4812650b854e3bd2ac8 (clean; in main via #535)
runtime:    CPython 3.11.15, Linux x86_64, 4 vCPU, single process
questions:  500 = 419 scored + 30 abstention (_abs) + 51 no user-side target (upstream exclusions)
failures:   0 runtime, 0 ingestion, 0 out-of-corpus, 0 unmapped admissions (all backends, both planes)
wall/peak:  2,406 s / 2,404.8 MB RSS (peak dominated by the parsed dataset)
reports:    reports/benchmarks/longmemeval/longmemeval-s-full-f73b872.{json,rows.json.gz,analysis.json}
analysis:   reference/analyze_longmemeval_report.py reproduces the .analysis.json byte-for-byte
```

The four surfaces below are reported separately. No aggregate is formed.

#### 1. Retrieval quality (419 scored questions)

| plane / metric | no_memory | lexical_overlap | agent_memory |
| --- | --- | --- | --- |
| session recall_all@5 / @10 | 0 / 0 | 0.730 / 0.826 | 0.675 / 0.797 |
| session ndcg_any@5 / @10 | 0 / 0 | 0.767 / 0.793 | 0.722 / 0.756 |
| turn recall_all@5 / @10 / @50 | 0 / 0 / 0 | 0.487 / 0.587 / 0.761 | 0.439 / 0.525 / 0.764 |
| turn ndcg_any@5 / @10 / @50 | 0 / 0 / 0 | 0.527 / 0.560 / 0.598 | 0.502 / 0.528 / 0.578 |

Paired, per question (Agent Memory − lexical, bootstrap 95% interval):

- session recall_all@5: −0.055 [−0.084, −0.029] (Agent Memory better on 7, lexical better on 30, equal on 382)
- turn recall_all@10: −0.062 [−0.093, −0.031] (Agent Memory better on 10, lexical better on 36, equal on 373)

Agent Memory is **statistically below** the simple lexical baseline. The gap is largest for `single-session-preference` (session recall_all@5 0.333 vs 0.500) and `temporal-reasoning` (0.654 vs 0.756). At turn level it is also notable for `multi-session` (0.198 vs 0.264).

Omissions at k=10 (no gold item retrieved): session 31 vs 25 for lexical; turn 95 vs 81.

Abstention (not an upstream metric): both backends return candidates for all 30 `_abs` questions. Neither abstains, because neither has a relevance threshold.

#### 2. Currentness (knowledge-update, 72 scored; 70 with gold on ≥2 dates)

| | lexical_overlap | agent_memory |
| --- | --- | --- |
| session recall_all@5 (both old and new evidence retrieved) | 0.917 | 0.931 |
| session latest-gold-ranked-first | 0.457 | **0.343** |
| turn latest-gold-ranked-first | 0.614 | **0.486** |

Agent Memory retrieves update evidence about as well as the baseline, but it orders it **older-first more often**. Failure classification (session plane, 46 failures) uses Agent Memory's own candidate score (`|query ∩ fact| / |query|`):

- **20 exact score ties.** In every one, the older evidence was inserted earlier. Admitted candidates tie-break on ascending `candidate_ref`, and fact ids are zero-padded insertion counters, so ties systematically favor the earliest-ingested item.
- 26 cases where the older session scores strictly higher lexically. No recency term exists to counter that.

On the turn plane: 17 ties (all earlier-inserted older first), 15 lexically higher, and 4 where the latest gold was not returned in the top 50.

This independently reproduces the #531 mechanism on natural data (AgentMemBench staleness 1.00) and adds the tie-break detail.

#### 3. Operational cost (Agent Memory; baselines are in-memory and ~free)

| plane | corpus size per question (quartiles) | mean ms per governed commit | mean recall ms |
| --- | --- | --- | --- |
| session | 38–45 → 50–62 | 5.94 → 6.60 | 20.2 → 22.8 |
| turn | 197–235 → 254–305 | 16.51 → 18.85 | 78.9 → 87.8 |

Per-commit cost roughly triples from about 45 to about 250 stored facts and keeps rising within the turn plane, as #522 predicts (O(store) per commit). Turn-plane ingest was 2,162 s of the 2,406 s total. The slowest question ingested 305 turns in 6.93 s, and the slowest recall took 172 ms.

#### 4. Failures and pathological cases

There were no exceptions, timeouts, ingestion refusals, governance refusals, or unmapped admissions. With one tenant and scope per question, every candidate was admitted. That matches the expectation for this workload, and it means governance is not exercised as a filter here.

The largest per-question deficits come from coarse ranking, not errors. For example, `19b5f2b3` ("How long was I in Japan for?") has its gold session at Agent Memory rank 11 against rank 1 for the baseline. Agent Memory counts raw token overlap including stopwords, and its tie-break is insertion order. The baseline breaks ties with Jaccard similarity, which favors dense matches.

### Interpretation boundary

These are retrieval and ordering results only. They are not QA accuracy. Agent Memory ran its default configuration: lexical candidate route, no vector route configured. The evidence says that configuration does not beat a trivial lexical baseline on LongMemEval_S, and that its tie-break is anti-recency on chronologically ingested data.

## Governance and evidence boundaries

```text
retrieval relevance != recall authority
candidate hit != admitted memory
benchmark result != memory authority
knowledge-update retrieval != proof of answer correctness
synthetic smoke != external evidence
```

Quality, currentness, abstention behavior, performance, and governance remain separate surfaces. No aggregate memory-health score is defined.

## Relationship to evaluator integrity

#518 owns wiring benchmark-integrity mutation probes into accepted external profiles. Those probes test whether the evaluator notices controlled damage. They do not improve or certify Agent Memory's score.
