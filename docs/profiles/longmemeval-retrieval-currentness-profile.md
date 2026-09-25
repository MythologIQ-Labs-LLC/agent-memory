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
| LongMemEval_S bounded subset | NOT RUN: `huggingface.co` was denied by the executing environment's egress policy |
| LongMemEval_S full | NOT RUN: same input-access blocker |
| LongMemEval_M | NOT RUN |
| Upstream QA (model-judged) | NOT RUN |

No external LongMemEval number exists for Agent Memory until a run binds the exact input SHA-256 and Agent Memory revision.

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
