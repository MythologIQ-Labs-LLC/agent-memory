# Independent AMB competitive profile

Status: **IMPLEMENTED BRIDGE / COMPETITIVE SCORE NOT YET RUN**  
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
 -> Gemini answer generation
 -> Gemini judge
```

and reports retrieval time separately from generation. Therefore an end-to-end AMB accuracy result is **not** numerically interchangeable with Agent Memory's native LongMemEval retrieval-only `recall_all@k` evidence.

## Agent Memory bridge

Implementation:

- `reference/amb_agent_memory_bridge.py`
- `reference/run_amb_external.py`
- `reference/tests/test_amb_agent_memory_bridge.py`

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
- answer model identity;
- judge model identity;
- retrieval/context budget;
- output artifact digest;
- execution failures separately from score;
- the same AMB protocol used for the systems being compared.

### `published_reference`

Vendor/project scores copied from public sources remain a separate reference layer. They do not become `same_harness_external` merely because AMB or another project publishes them.

### `blocked`

A run requiring credentials or an unavailable managed service is `blocked` until those requirements are satisfied. Missing credentials are not score zero.

## Initial execution posture

The bridge itself can be validated credential-free in repository CI. A full AMB `run` currently requires the external harness's configured Gemini credential for its default generate/judge lane.

Until that credential is supplied to an explicitly authorized execution environment, the first end-to-end Agent Memory AMB score is:

**BLOCKED_PENDING_EVALUATION_CREDENTIAL**

This is an execution dependency, not a product result.

Retrieval-only AMB profiles that do not require answer generation/judging may be admitted separately when their dataset/profile semantics match the intended comparison.

## First comparison sequence

1. prove the Agent Memory bridge against repository-owned integration tests;
2. execute a small AMB smoke run at the frozen revision;
3. freeze answer/judge model and run configuration before competitive scoring;
4. run Agent Memory and at least two reproducible non-Agent-Memory providers under the same AMB profile;
5. retain raw outputs and digests;
6. add results to the canonical dashboard only after comparability review;
7. repeat on additional AMB datasets only when they add a materially distinct pressure dimension.

The native Agent Memory Gauntlet remains responsible for governance/currentness-specific pressure that AMB does not model.

## Governance

Still load-bearing:

```text
external harness score != Agent Memory authority
published vendor score != same-harness evidence
benchmark adapter != product policy
query timestamp != memory authority
competitive advantage != architecture truth
```

No Agent Memory runtime behavior may be specialized to AMB dataset IDs, gold labels, benchmark phrases, or expected outcomes.
