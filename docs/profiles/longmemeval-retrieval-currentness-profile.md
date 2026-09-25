# LongMemEval Retrieval and Currentness Profile

Status: bounded external benchmark profile for #516 under #498/#519.

## Source binding

```text
upstream repository: xiaowu0162/LongMemEval
inspected revision: 9e0b455f4ef0e2ab8f2e582289761153549043fc
license: MIT
```

The inspected upstream release describes 500 questions spanning information extraction, multi-session reasoning, knowledge updates, temporal reasoning, and abstention. Its released records bind questions to timestamped history sessions through `haystack_session_ids`, `haystack_dates`, `haystack_sessions`, `answer_session_ids`, and turn-level `has_answer` labels.

This Agent Memory profile does not vendor the external dataset. A real run consumes an explicitly supplied local LongMemEval JSON artifact and records its SHA-256 digest.

## What this profile measures

The profile evaluates two retrieval granularities:

```text
session
turn
```

For non-abstention questions it reports the upstream retrieval metric family:

- session: `recall_all@5`, `ndcg_any@5`, `recall_all@10`, `ndcg_any@10`;
- turn: the same @5/@10 metrics plus `recall_all@50` and `ndcg_any@50`.

Abstention questions remain outside the retrieval-recall denominator because the upstream retrieval evaluation excludes them when no answer location exists. Their retrieval activity is reported separately instead of quietly manufacturing a gold location.

Question-type metrics are also kept separate. In particular, `knowledge-update` is preserved as a bounded currentness slice rather than averaged into a universal memory score.

## Backends

The runner supports materially different retrieval postures under the same frozen input:

```text
no_memory
lexical_overlap
agent_memory
```

`no_memory` returns nothing. `lexical_overlap` is a deterministic credential-free overlap/Jaccard baseline. `agent_memory` uses the public `AgentMemory` facade, retains each session or turn through ordinary governed commit, invokes recall without an exact-identity shortcut, and converts admitted fact UUIDs back to benchmark item IDs.

Agent Memory candidate generation and final admission remain distinct. A benchmark-relevant item can be discovered and still refused by governance.

## Answer-quality boundary

LongMemEval's upstream QA evaluation is a separate model-dependent answer evaluator. This profile deliberately does not invoke it.

```text
retrieval/currentness result
    !=
LongMemEval QA score
    !=
answer-generation quality
```

A future answer-generation profile may bind an exact reader/evaluator model and configuration. Until then, this runner must not be presented as an official LongMemEval QA result.

## Synthetic smoke fixture

The repository contains:

```text
reference/fixtures/benchmarks/longmemeval/synthetic.json
```

It exercises a simple single-session fact, one knowledge update, and one abstention question. It exists to prove the benchmark contract and Agent Memory adapter path. It is not external benchmark evidence.

Run it with:

```bash
PYTHONPATH=reference python reference/run_longmemeval.py
```

A real frozen input can be run with:

```bash
PYTHONPATH=reference python reference/run_longmemeval.py \
  --input /path/to/longmemeval_s_cleaned.json \
  --corpus-class external_frozen \
  --output longmemeval-agent-memory.json
```

The report binds the exact input SHA-256. `external_frozen` means only that the supplied artifact is being treated as a frozen external input for this profile. It does not claim paper-result reproduction or upstream QA parity.

## Governance and evidence boundaries

```text
retrieval relevance != recall authority
candidate hit != admitted memory
benchmark result != memory authority
knowledge-update retrieval != proof of answer correctness
synthetic smoke != external evidence
```

Quality, currentness, abstention behavior, performance, and governance must remain separate surfaces. No aggregate memory-health score is defined.

## Relationship to evaluator integrity

#518 owns wiring the benchmark-integrity mutation probes into accepted external benchmark profiles. Those probes test whether the evaluator notices controlled damage. They do not improve or certify Agent Memory's benchmark score.

## Remaining full-run work

This slice establishes the reproducible runner, input binding, profile semantics, focused tests, and bounded smoke. A publication-quality external result still requires selecting and SHA-binding the exact released LongMemEval artifact, recording any reader/evaluator configuration used for answer-quality work, and publishing the resulting evidence against an exact Agent Memory revision.
