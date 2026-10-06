# Independent AMB competitive profile

Status: **IMPLEMENTED BRIDGES / FIRST SAME-HARNESS LANE FROZEN (#640) / NO ROW EXECUTED OR ACCEPTED**  
Owner: #601  
Parent maturity program: #600  
External harness: `vectorize-io/agent-memory-benchmark` (AMB)  
Frozen harness revision: `03c1d0f1d27da63034f0931121c858faba512383`

## Purpose

This profile adds an independent competitive evaluation axis without making another project's benchmark logic part of Agent Memory doctrine.

AMB owns its datasets, prompts, answer generation, judging, provider comparison, and result format. Agent Memory contributes only a provider bridge that translates AMB's document/retrieval interface into the public `AgentMemory` facade.

```text
AMB dataset + protocol
        |
        v
AMB MemoryProvider contract
        |
        v
Agent Memory bridge
        |
        v
public AgentMemory facade
        |
        v
qualified Agent Memory runtime
```

The result is external-harness evidence. It is not authority, conformance proof, or permission to tune Agent Memory to one benchmark.

## Why this profile exists

The canonical Agent Memory dashboard contains two different kinds of missing comparison:

1. a new Agent Memory metric may legitimately have no earlier Agent Memory baseline;
2. a mature product still needs evidence showing how it performs relative to other current memory systems under a common protocol.

The second is a real pre-1.0 evidence gap. #601 owns it.

AMB is useful because its harness already defines a shared provider interface and already carries providers for multiple memory systems, including Hindsight, Mem0, Cognee, Supermemory, Mastra and baseline retrieval systems. Using the independent harness reduces the risk that Agent Memory defines every ruler used to judge itself.

## Frozen external boundary

The bridge refuses an AMB checkout unless `git rev-parse HEAD` exactly equals:

`03c1d0f1d27da63034f0931121c858faba512383`

The pinned AMB project identifies itself as `amb` 0.1.0 and depends on Python 3.11+, Gemini evaluation tooling, Mem0, Cognee, Hindsight, Supermemory, and related provider dependencies at the frozen revision.

The AMB README describes the default evaluation flow as:

```text
ingest
 -> retrieve
 -> answer generation
 -> judge
```

The frozen harness also provides `retrieval` mode for PrecisionMemBench. That mode explicitly makes no LLM calls: the provider-returned document IDs are scored directly against required and forbidden belief IDs.

Therefore an end-to-end AMB accuracy result is **not** numerically interchangeable with Agent Memory's native LongMemEval retrieval-only `recall_all@k` evidence, and an AMB PrecisionMemBench retrieval score is a distinct exact-ID retrieval profile rather than a conversational QA score.

## Agent Memory bridge

Implementation:

- `reference/amb_agent_memory_bridge.py`
- `reference/run_amb_external.py`
- `reference/tests/test_amb_agent_memory_bridge.py`
- `.github/workflows/amb-competitive.yml`

The bridge:

- registers `agent-memory` into AMB's runtime provider registry without modifying AMB source;
- uses only the public `AgentMemory` facade;
- maps AMB `user_id` to a deterministic isolated Agent Memory scope;
- maps AMB document IDs to deterministic logical memory IDs;
- passes source document timestamps as caller-declared `observed_at` evidence;
- records but does not use AMB query timestamps as memory authority;
- preserves original AMB document IDs/content in a revision-bound sidecar so retrieved Agent Memory fact UUIDs can be projected back into AMB's contract;
- binds resume state to bridge version and exact Agent Memory revision;
- runs provider query concurrency at `1` until multi-handle/multi-writer semantics are independently qualified.

The adapter does not implement ranking, admission, isolation policy, lifecycle policy, or benchmark scoring.

## Evidence classes

### `same_harness_external`

A locally executed AMB run may use this class only when all of the following are recorded:

- exact AMB revision;
- exact Agent Memory revision;
- exact dataset/split identity;
- memory provider/configuration;
- answer model identity, or explicit `none` for retrieval mode;
- judge model identity, or explicit `none` for retrieval mode;
- retrieval/context budget;
- output artifact digest;
- execution failures separately from score;
- the same AMB protocol used for the systems being compared.

### `published_reference`

Vendor/project scores copied from public sources remain a separate reference layer. They do not become `same_harness_external` merely because AMB or another project publishes them.

### `blocked`

A run requiring credentials or an unavailable managed service is `blocked` until those requirements are satisfied. Missing credentials are not score zero.

## Execution posture

The bridge itself is validated credential-free in ordinary repository CI.

### Credential-free retrieval lane

For `mode=retrieval` with `agent-memory` or `bm25`, the workflow admits execution without a real model credential. The frozen AMB `RetrievalMode` explicitly makes no LLM calls. Because the frozen CLI still constructs its configured answer client before selecting that mode, the workflow may provide an inert placeholder API-key value solely to satisfy client construction. That placeholder is never used to generate, judge, extract, rank, or authorize memory.

The first intended profile is:

```text
dataset: precisionmembench
split: single-turn
mode: retrieval
providers: agent-memory, bm25
```

This lane can validate independent-harness ingestion/retrieval/scoring immediately. BM25 is a baseline comparator, not a claim of market competitiveness.

### LLM-judged / provider-LLM lanes

RAG and any provider that requires model-assisted ingestion remain fail-closed on real credentials. The workflow freezes both answer and judge configuration to:

`gemini:gemini-2.5-flash-lite`

until #601 explicitly versions a different competitive profile.

Until an authorized environment supplies the required evaluation credential, the first end-to-end Agent Memory AMB RAG score is:

**BLOCKED_PENDING_EVALUATION_CREDENTIAL**

This is an execution dependency, not a product result.

## First comparison sequence

1. prove the Agent Memory bridge against repository-owned integration tests;
2. run PrecisionMemBench retrieval for Agent Memory and BM25 under the frozen external harness;
3. retain raw outputs and execution identity as workflow artifacts;
4. configure authorized evaluation credentials;
5. execute a bounded AMB RAG smoke at the frozen revision;
6. freeze answer/judge model and run configuration before full competitive scoring;
7. run Agent Memory and at least two reproducible non-Agent-Memory providers under the same profile;
8. add results to the canonical dashboard only after comparability review;
9. repeat on additional AMB datasets only when they add a materially distinct pressure dimension.

The native Agent Memory Gauntlet remains responsible for governance/currentness-specific pressure that AMB does not model.

## Frozen same-harness lane v1 (#640)

The first comparator lane is frozen, before any score exists, in
`reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v1.json`
(schema `schemas/same-harness-lane.schema.json`, validated and cross-checked against the
`amb-precisionmembench-retrieval-v1` benchmark integration by
`agent-memory benchmark validate-lane`). The freeze digest printed by
`agent-memory benchmark lanes` is the identity recorded on #640.

```text
lane:        amb-precisionmembench-retrieval-v1
harness:     vectorize-io/agent-memory-benchmark @ 03c1d0f1d27da63034f0931121c858faba512383
dataset:     precisionmembench / single-turn (tenurehq/precisionmembench @ b95d6ab, MIT)
             beliefs.seed.json     35659b3b…3de98
             retrieval.cases.json  09e99f08…b709c
             input_sha256          caf5869b…682dd
selection:   all 77 cases, no query limit, no category, AMB_PMB_RETURN_CAP unset
budget:      per-case maxBeliefs (default 20) passed as k; scorer keeps top-20 distinct beliefs
evaluator:   retrieval mode, no LLM, no answer/judge model; scorer blob 47432e9c
rows:        agent-memory (control) · bm25 (baseline) · mem0-explicit (comparator, frozen)
             hindsight (comparator, deferred)
headline:    active_passes/43, total passes/77, mean precision, mean recall
```

### Mem0 OSS row

`reference/amb_mem0_explicit_bridge.py` registers `mem0-explicit`:

- `mem0ai==2.2.1` exactly (tag `v2.2.1`, commit `94c3fe9f…`, Apache-2.0), verified through
  `mem0.__version__` before any memory is built; base package install, no extras, so Mem0's
  optional fastembed keyword search and spaCy lemmatizer are absent by product default and
  that posture is recorded in the execution identity;
- explicit memory: `Memory.add([...document.content...], user_id=<AMB user_id>, metadata={'doc_id': ...}, infer=False)`;
  the constructed LLM is replaced by a guard, so any inference call aborts the run;
- local embeddings: `sentence-transformers/multi-qa-MiniLM-L6-cos-v1` at Hugging Face
  revision `b2073673…`, 384 dimensions; local on-disk Qdrant, fresh per run;
- retrieval: `Memory.search(query, top_k=<case k>, filters={'user_id': ...})`; Mem0's own
  ranking, threshold, and entity boosts are product behaviour and are not altered;
- belief identity returns through `metadata.doc_id` as `Document.source_ids`, so the
  frozen resolver takes its `source_id` path and every result records which path fired.

Why not AMB's own `mem0` provider at the frozen revision: it extracts through Gemini on
every `add` (credentialed, model-dependent, a Mem0+Gemini composition), floats
`mem0ai>=1.0.5`, and calls `Memory.search(query, user_id=..., limit=...)`, which Mem0
2.2.1 rejects (`Top-level entity parameters ... are not supported in search()`). A
reflective Mem0 lane is a different system composition and is listed as a deferred lane,
to be frozen separately before any reflective score is seen.

### Executing the lane

`.github/workflows/amb-competitive.yml` with `dataset=precisionmembench`,
`split=single-turn`, `mode=retrieval`, `query_limit=0`, once per provider
(`agent-memory`, `bm25`, `mem0-explicit`). The workflow installs the frozen harness under
pip constraints exported from the harness's own `uv.lock`
(`scripts/amb_harness_constraints.py`): the frozen `pyproject.toml` floats most of its
dependency set and re-resolving it from scratch exhausts pip's backtracking budget
(`resolution-too-deep`, run 37343360127) before a single query runs, while the lock the
harness authors shipped resolves in seconds. Only this repository's own pins and the Mem0
row's `mem0ai==2.2.1` (which lifts the lock's `posthog`) depart from the lock, and the lock
blob plus every lifted pin is written into the execution identity. The lock also carries
`fastembed` for the harness's Cognee provider; because Mem0 2.2.1 silently switches to
BM25 hybrid retrieval whenever that package imports, the Mem0 row removes it after the
constrained install (a declared, recorded removal), and the posture check refuses to run
the row if it is present. The workflow then
validates the lane file, downloads and digest-checks both fixtures against it, runs the
harness self-check (a perfect provider must reproduce 43/43 active and 77/77 total),
verifies the Mem0 row's version and extras posture, and writes an
`execution-identity.json` with resolved package versions and the optional-component
posture. Raw AMB `EvalSummary` artifacts are retained unmodified.

A row becomes `same_harness_external` only after its raw artifact and execution identity
are reviewed against the lane and an `evidence_history` entry is added to the integration
descriptor. `scripts/import_amb_lane_evidence.py` (run by
`.github/workflows/amb-evidence-import.yml` against a reviewer's branch, never `main`)
copies the raw artifacts byte for byte into
`reports/benchmarks/amb/<lane_id>/<provider>-<revision12>/`, re-verifies them against the
run's own sha256 inventory, re-hashes the pinned fixtures, and writes `evidence.json`, the
record an `evidence_history` entry binds through `input.sha256` and `system.revision`.

### Accepted rows (lane v1, 2026-10-05)

The lane's status is `accepted`; its record is never edited in place again (any changed
frozen fact is a new lane id). The three executed rows were accepted from these runs,
each on the lock-constrained install with the self-check reproducing the perfect-provider
row first:

| row | role | system revision | workflow run | evidence record |
| --- | --- | --- | --- | --- |
| agent-memory | control | Agent Memory `703be5ba1c7e558edb16ac38508508e5ef592595` | 37349431401 | `reports/benchmarks/amb/amb-precisionmembench-retrieval-v1/agent-memory-703be5ba1c7e/evidence.json` |
| bm25 | baseline | AMB `03c1d0f1d27da63034f0931121c858faba512383` | 37349435243 | `…/bm25-703be5ba1c7e/evidence.json` |
| mem0-explicit | comparator | mem0ai 2.2.1 (`94c3fe9f238f3dbf29c9ce98643bd71eb13077cd`), fastembed and spaCy absent | 37351804149 | `…/mem0-explicit-b38d91631169/evidence.json` |

Native PrecisionMemBench numbers, in the frozen harness's own shape (`active_passes/43` is
the only number comparable to upstream's Active passes column; total passes include
structural and trivially-empty cases that a provider returning nothing can satisfy):

| row | total passes | active | structural | trivially-empty | mean precision | mean recall | ID resolution |
| --- | --- | --- | --- | --- | --- | --- | --- |
| agent-memory | 15/77 | 4/43 | 6/25 | 5/9 | 0.18 | 0.95 | source_id |
| bm25 | 8/77 | 0/43 | 5/25 | 3/9 | 0.05 | 0.97 | doc_id |
| mem0-explicit | 10/77 | 0/43 | 7/25 | 3/9 | 0.10 | 1.00 | source_id |

These rows are `same_harness_external` evidence for this lane only. They produce no
overall score and no market claim: BM25 is a baseline and Agent Memory is the control.
Every row returned nearly everything relevant and failed on precision, which is what the
active cases test. The Hindsight row stays deferred.

### Normalized manifests

`normalize_amb_precisionmembench()` (`reference/agentmem_ref/evaluation/normalize.py`)
turns each committed `evidence.json` into one `memory-benchmark-run` manifest under
`reports/benchmarks/normalized/amb-precisionmembench-<lane_id>-single-turn-<system>-<rev12>.json` (the lane id entered the run id with the `-v2` lanes so a later lane generation can never overwrite an earlier manifest).
It maps only what the harness's own summary table states: `retrieval` carries
`active_passes/43`, `structural_passes/25`, `trivially_empty_passes/9`,
`total_passes/77`, `mean_precision` and `mean_recall`; `efficiency` carries
`mean_retrieve_ms` and `ingestion_time_ms` (environment-bound, GitHub-hosted runner);
`reproducibility` carries the input, selection, budget, harness-lock and self-check
facts. `currentness` and `reasoning` are `not_applicable`, `governance` and
`evaluator_integrity` are `not_measured` with their reasons. The whole evidence record
stays under `native_results` and the raw per-case `EvalSummary` is referenced by digest,
never restated. The three rows share one comparison identity, so they land on one
scorecard with the BM25 row as the lexical baseline; the deltas it shows are
per-metric, direction-aware and fail closed, and still no aggregate exists.

## Governance

Still load-bearing:

```text
external harness score != Agent Memory authority
published vendor score != same-harness evidence
benchmark adapter != product policy
query timestamp != memory authority
competitive advantage != architecture truth
placeholder client credential != evaluation credential
```

No Agent Memory runtime behavior may be specialized to AMB dataset IDs, gold labels, benchmark phrases, or expected outcomes.
