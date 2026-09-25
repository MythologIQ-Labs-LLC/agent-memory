# AgentMemBench / MemDialogue Operational Profile

Status: bounded external benchmark profile for #517 under #498/#519.

## Source binding and rights

```text
upstream repository: mazaiying/AgentMemBench
inspected revision:  186c9a54edd47aae42d8b6990520f8e902b60303
harness:             agentmembench/evaluation/unified_benchmark.py
harness SHA-256:     d0d407129aa506f6eacbf6df19a26c1a9ddd000aa0bfb931cb4e4ae984e594df
code license:        MIT
dataset:             data/memdialogue_v2.jsonl (9,170 records; 8,607 unique sources)
dataset SHA-256:     33632710ae6495b95724df455ff6f9947d231ee68ebc0ef10eb8291fd55ca2a6
                     (matches upstream data/SHA256SUMS)
data license:        ODC-By 1.0 (derived from WildChat-4.8M @ c827c6df8fcf008219ffaffa4d1dd77491099367)
```

> MemDialogue is derived from WildChat-4.8M by the Allen Institute for AI.

The MIT code license does not replace the ODC-By data license. MemDialogue records are **not** vendored into Agent Memory. A run binds the supplied file's SHA-256 and reports whether it matches the upstream release. Rights are recorded in `sources/source-registry.json` (`agentmembench-memdialogue`).

## What is reproduced

`reference/run_agentmembench.py` re-expresses the deterministic phases of the bound upstream harness. It keeps identical workload strings, default parameters, and metric formulas behind the upstream five-method adapter protocol (`reset / add / search / delete / close`):

| Upstream axis | Phase | Metrics |
| --- | --- | --- |
| M1 write efficiency | retrieval write pass | write success rate, write/read latency |
| M2 retrieval quality | retrieval | **`exact_source_recall@k` (profile-local, deterministic)**, by event type |
| M3 scalability | scale (100 / 1,000 facts) | `recall_at_3`, write/read latency |
| M4 temporal consistency | conflict (250 pairs) | `new_fact_rate`, `staleness_rate`, `dual_version_rate` |
| M5 isolation & privacy | isolation (100 users × 5) and deletion (200) | `cross_user_leak_rate`, `audited_deletion_rate` |
| operational | concurrency (1/4/8/16 workers × 200) | operation success, materialization, throughput |
| M6 LLM portability | none | `not_exercised` (no LLM backend in this profile) |

Parity was checked differentially against the pinned upstream module. Upstream `load_records` output on the real dataset is identical for three `(limit, seed)` configurations, the scale query indices match `numpy.linspace`, and **upstream's own** `run_conflict`, `run_isolation`, `run_deletion`, `run_scale`, and `run_concurrency`, driven with each of this profile's adapters, produce the same non-latency metrics as the re-expressed phases.

### Retrieval metric boundary

Upstream `recall_at_k` is **LLM-judged**: a local model decides whether any retrieved memory supports the reference answer. This profile does not run a judge and reports `upstream_llm_judged_recall_at_k: not_run`. It reports `exact_source_recall@k` instead: whether the record's own memory text is among the top-k results for its query within its 10-record user group. This is stricter than semantic support in one sense (paraphrases do not count) and looser in another (it does not check answer sufficiency). It is not comparable to upstream judged numbers.

## Backends

```text
no_memory        stores nothing, returns nothing
lexical_overlap  deterministic per-user token-overlap store (profile-local)
agent_memory     public AgentMemory facade
```

`agent_memory` uses one governed runtime per phase reset under a single tenant. Each upstream `user_id` becomes its own governed scope and isolation domain. Writes go through ordinary `remember` (governed commit) and reads through `recall` (candidate generation followed by canonical governed admission, targeted at the requesting user's domain). Deletion uses the facade default, a governed tombstone. User separation is therefore enforced by recall admission, not by the adapter, and cross-user candidates appear in the governance tallies as refusals.

Latency is local and in-process. It is not comparable to upstream's service-backed Mem0, Graphiti, LangMem, Letta, or Naive RAG latencies, which are not reproduced here.

## Running

Synthetic smoke (conformance only; repository-owned records, never external evidence):

```bash
PYTHONPATH=reference python reference/run_agentmembench.py --retrieval-records 12 --group-size 3 \
  --conflict-pairs 10 --isolation-users 4 --isolation-facts 2 --deletion-records 5 \
  --concurrency-records 6 --workers 1,2 --scales 10,30 --scale-read-queries 5
```

Bounded external run at upstream defaults. Retrieval sampling needs `numpy`, as it does upstream.

```bash
git clone https://github.com/mazaiying/AgentMemBench && git -C AgentMemBench checkout 186c9a54edd47aae42d8b6990520f8e902b60303
PYTHONPATH=reference python reference/run_agentmembench.py \
  --input AgentMemBench/data/memdialogue_v2.jsonl --corpus-class external_frozen \
  --backend agent_memory --output agentmembench-agent_memory.json
```

## Execution status

| Run | Status |
| --- | --- |
| Synthetic smoke | COMPLETE (conformance only; CI) |
| MemDialogue v2, upstream default parameters, all three backends | **COMPLETE** (bounded external) |
| Upstream LLM-judged retrieval recall | NOT RUN (no judge endpoint/credentials provisioned) |
| M6 LLM portability | NOT EXERCISED |
| Upstream reference systems (Mem0, Graphiti, LangMem, Letta, Naive RAG) | NOT RUN |

### Bounded external result: 2026-09-25

```text
input:     memdialogue_v2.jsonl  sha256 33632710…ca2a6  (matches upstream release)
revision:  Agent Memory 03197cd5c866b890b1f9b4505eee3b6f93bcbe2b (clean worktree)
upstream:  mazaiying/AgentMemBench@186c9a54 harness sha256 d0d40712…94df
params:    upstream defaults: retrieval 1000 (seed 2027, group 10, top_k 5), conflict 250,
           isolation 100x5, deletion 200, concurrency 200 x {1,4,8,16}, scale {100,1000} x 200 reads
runtime:   CPython 3.11.15, numpy 2.4.6, Linux x86_64, 4 vCPU; one process per backend
reports:   reports/benchmarks/agentmembench/memdialogue-v2-<backend>-03197cd.json
```

Each dimension is reported separately. The 95% intervals are upstream-style bootstrap intervals.

| Dimension | no_memory | lexical_overlap | agent_memory |
| --- | --- | --- | --- |
| write success (retrieval pass) | 0.000 | 1.000 | 1.000 |
| exact_source_recall@5 | 0.000 | 0.912 [0.894, 0.929] | 0.889 [0.869, 0.909] |
| — PERSONAL_FACT / TASK_REQUEST | 0 / 0 | 0.972 / 0.852 | 0.938 / 0.840 |
| conflict new_fact / staleness / dual | 0 / 0 / 0 | 0.20 / 0.80 / 0 | **0.00 / 1.00 / 0** |
| cross_user_leak_rate | 0.00 | 0.00 | 0.00 |
| audited_deletion_rate | n/a (nothing visible) | 1.00 | 1.00 (governed tombstone) |
| scale recall@3 at 100 / 1,000 | 0 / 0 | 1.00 / 1.00 | 1.00 / 1.00 |
| concurrency operation success (1/4/8/16 workers) | 1.0 all | 1.0 all | **0.0 all** |
| retrieval write latency mean / p95 (ms) | ~0 | ~0 | 56.8 / 111.2 |
| retrieval read latency mean / p95 (ms) | ~0 | ~0 | 1,273.7 / 2,059.0 |
| scale write mean at 100 / 1,000 (ms) | ~0 | ~0 | 7.95 / 52.59 |
| scale read mean at 100 / 1,000 (ms) | ~0 | ~0 | 41.9 / 497.2 |
| peak RSS (process) | 52.7 MB | 52.7 MB | 678.4 MB |
| wall time | 0.1 s | 0.3 s | 1,626 s |

Agent Memory governance observations (per phase, from the governed recall/commit path):

- isolation: 50,000 candidates, 500 admitted, 49,500 refused `required_isolation_domain_missing`, zero leaks. Separation comes from canonical admission, not from candidate generation.
- deletion: 200/200 `forget` committed (`allow_with_ledger`), and every post-delete candidate was refused `tombstoned`. Permanent deletion is a separate, externally verified request and was not exercised.
- retrieval: 993,210 candidates, 9,937 admitted, 983,273 cross-user refusals. Candidate generation is tenant-wide, so admission does the scoping work.

### Interpretation (bounded)

- **Retrieval.** Agent Memory's default candidate route is lexical. On this workload it is statistically indistinguishable from, and nominally below, the simple lexical baseline (overlapping 95% intervals). No semantic/vector route was configured in this profile.
- **Temporal consistency.** When an update arrives as an independent write (upstream's workload: no `correct()` linkage), recall ranking has no recency term and returned the superseded fact at top-1 in every pair. Agent Memory's currentness guarantees apply to governed corrections and supersession; this workload does not exercise those (#531).
- **Isolation and deletion.** Both were enforced by governance with zero leaks and full audited deletion.
- **Concurrency.** The `AgentMemory` facade handle is bound to its creating thread. Every write from a worker thread (including a single-worker pool) failed with `sqlite3.ProgrammingError` (#530).
- **Scale and latency.** Recall cost grows with tenant size, because every tenant fact is a candidate before admission. Commit cost grows with store size (#522).


## Governance and evidence boundaries

```text
retrieval hit != recall authority
candidate != admitted memory
tombstone != permanent erasure (permanent deletion requires external verification)
benchmark result != memory authority
synthetic smoke != external evidence
```

Write efficiency, retrieval, temporal consistency, isolation, deletion, concurrency, scale, and governance remain separate surfaces. No aggregate memory-health score is defined.

Evaluator integrity for this profile is exercised by `reference/run_benchmark_integrity_mutants.py` (`agentmembench_memdialogue`; see [`docs/51-benchmark-integrity-mutation-probes.md`](../51-benchmark-integrity-mutation-probes.md)).
