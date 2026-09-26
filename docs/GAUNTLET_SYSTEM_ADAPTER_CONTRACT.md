# Agent Memory Gauntlet System Adapter Contract

**Status:** Proposed foundation specification under #554  
**Contract family:** `agent-memory-gauntlet-system-adapter`  
**Initial contract version:** `0.1.0`  
**Authority effect:** none

## 1. Purpose

The Agent Memory Gauntlet needs a system-neutral way to place different memory systems under the same benchmark and adversarial pressure without requiring them to implement Agent Memory's architecture.

This contract defines the boundary between:

1. a **system under test** (SUT), such as Agent Memory, a vector-memory service, a graph-memory system, a conversational-memory product, or a research prototype;
2. a **Gauntlet system adapter**, which translates the Gauntlet's bounded operation vocabulary into the SUT's native interface;
3. a **benchmark adapter**, which preserves one benchmark's native dataset, task, and scoring semantics;
4. the existing **Memory Evaluation** subsystem, which records normalized evidence and performs fail-closed comparison.

The contract exists to make this composition possible:

```text
benchmark-native task
        |
        v
benchmark adapter
        |
        v
Gauntlet operation vocabulary
        |
        v
system adapter
        |
        v
system under test
        |
        v
native result / observations
        |
        v
benchmark-native evaluator
        |
        +--> benchmark-native evidence
        |
        +--> Memory Evaluation normalized evidence
```

The contract is not a memory ontology and is not a lowest-common-denominator replacement for benchmark-native protocols.

```text
adapter compatibility != benchmark comparability
adapter support != system quality
adapter translation != system capability
benchmark score != authority
```

## 2. Design principles

### 2.1 Capability negotiation, not architectural conformity

A system may enter a Gauntlet suite with only the capabilities that suite requires.

A retrieval-only memory system should not need to implement correction, deletion, history, governance, or recovery merely to run a retrieval benchmark.

Unsupported capability is represented explicitly. It is never silently converted to a numeric zero unless the native benchmark itself defines lack of support as task failure.

### 2.2 The adapter may translate interfaces; it may not manufacture product claims

The adapter may:

- map field names;
- convert an input record into the SUT's native request format;
- call multiple native operations when the benchmark protocol itself requires a compound operation;
- normalize transport errors;
- expose native identifiers through opaque Gauntlet handles;
- collect timing and resource observations externally.

The adapter must not:

- add a vector index and then claim the SUT natively supports semantic retrieval;
- implement correction in adapter state and claim the SUT supports governed correction;
- add tenant filtering outside the SUT and report that as native tenant isolation;
- add temporal ranking outside the SUT and report the result as the SUT's currentness behavior;
- add deletion bookkeeping outside the SUT and claim deletion support;
- use benchmark labels, gold answers, question identifiers, or expected outputs to modify SUT behavior.

If adapter-side behavior materially contributes to the measured capability, that behavior must be declared and the result classified accordingly.

### 2.3 Native semantics remain native

The system adapter is not allowed to rewrite the benchmark.

LongMemEval remains LongMemEval. AgentMemBench remains AgentMemBench. A future governance suite retains its own threat model and verdict semantics. A future memory-to-action benchmark retains its own task completion semantics.

The Gauntlet provides an execution boundary and evidence envelope, not a replacement scoring system.

### 2.4 Reproducibility is part of the result

Every run should bind:

```text
system identity
system revision/version
system adapter identity/version
adapter configuration digest
benchmark identity/revision
benchmark adapter identity/version
frozen input identity
suite/profile identity
selection/sample identity
execution environment where measured
```

A result without enough identity to reconstruct the run may still be useful exploratory evidence, but it cannot be promoted to comparison evidence.

### 2.5 Evaluator authority remains none

The Gauntlet does not grant memory authority, mutate the SUT outside the benchmark protocol, or make benchmark output authoritative product state.

All normalized Gauntlet evidence retains:

```text
authority_effect: none
```

## 3. Roles

### 3.1 System under test (SUT)

The actual memory system being evaluated.

Examples may include:

- Agent Memory runtime;
- an embedded memory library;
- a network memory service;
- a database-backed memory layer;
- a graph memory implementation;
- an agent framework's built-in memory;
- a research prototype;
- a deterministic baseline.

### 3.2 System adapter

A thin, inspectable translation layer implementing this contract for one SUT configuration.

The adapter is part of the evidence identity.

### 3.3 Benchmark adapter

A benchmark-specific layer responsible for preserving the benchmark's native semantics and translating benchmark actions into only the Gauntlet operations required for that profile.

### 3.4 Gauntlet orchestrator

A future execution layer that:

1. validates the system manifest;
2. negotiates benchmark requirements against declared capabilities;
3. starts or connects to the SUT through its adapter;
4. executes the benchmark adapter;
5. records native evidence;
6. normalizes eligible dimensions through Memory Evaluation;
7. produces a coverage-aware report.

## 4. System manifest

Every system adapter must expose a manifest before execution.

Conceptual shape:

```json
{
  "contract_family": "agent-memory-gauntlet-system-adapter",
  "contract_version": "0.1.0",
  "system": {
    "id": "example-memory",
    "kind": "external_memory",
    "version": "2.4.1",
    "revision": "git-or-build-revision",
    "configuration_digest": "sha256:..."
  },
  "adapter": {
    "id": "example-memory-gauntlet-adapter",
    "version": "1.0.0",
    "revision": "..."
  },
  "transport": {
    "kind": "stdio",
    "startup": ["python", "adapter.py"]
  },
  "capabilities": {
    "reset": {"support": "native"},
    "remember": {"support": "native"},
    "recall": {"support": "native"},
    "correct": {"support": "unsupported"},
    "forget": {"support": "native"}
  }
}
```

The concrete schema should be implemented in a later code slice after this specification is reviewed.

## 5. Capability support classes

Each declared capability has one of these support classes.

| Class | Meaning |
| --- | --- |
| `native` | The SUT directly implements the semantic capability. |
| `mapped` | The adapter performs bounded interface translation to an equivalent native SUT capability without adding material semantics. |
| `derived` | The capability/result is constructed partly outside the SUT. It may be useful evidence but is not evidence of native SUT capability. |
| `unsupported` | The SUT does not provide the capability in this configuration. |
| `unknown` | The adapter cannot establish support truthfully. Qualification should fail closed where the capability is required. |

`derived` is intentionally visible. It prevents useful experimental composition from becoming a product claim by accident.

A benchmark profile may declare which support classes it accepts.

Example:

```text
retrieval profile:
  recall -> native | mapped accepted

native-governance isolation profile:
  tenant isolation -> native only

end-to-end application profile:
  derived may be acceptable if the benchmark measures the whole stack,
  but the report must name the composition rather than the memory subsystem alone
```

## 6. Core operation vocabulary

The operation vocabulary is intentionally small. Benchmark adapters should request only what they actually need.

### 6.1 `describe`

Return the system manifest and adapter identity.

**Required for every Gauntlet adapter.**

### 6.2 `reset`

Return the SUT to an empty benchmark state for the declared test namespace.

Minimum semantics:

- prior benchmark records in the test namespace are no longer available;
- the operation is bounded to the benchmark-owned namespace or disposable instance;
- reset completion is observable before the next operation starts.

A system that cannot safely reset may instead require a fresh disposable instance per run. That posture must be declared.

### 6.3 `remember`

Present one memory observation/record to the SUT.

Conceptual request:

```json
{
  "operation": "remember",
  "record_id": "benchmark-owned-opaque-id",
  "content": "...",
  "context": {
    "tenant": null,
    "scope": null,
    "purpose": null,
    "source": null,
    "observed_at": null,
    "valid_from": null,
    "valid_until": null,
    "metadata": {}
  }
}
```

Not every SUT must support every context field. Unsupported metadata must be declared; it must not be silently discarded when the benchmark requires it for protocol fidelity.

### 6.4 `recall`

Ask the SUT for memory relevant/applicable to a query.

Conceptual request:

```json
{
  "operation": "recall",
  "query_id": "...",
  "query": "...",
  "limit": 10,
  "context": {
    "tenant": null,
    "scope": null,
    "purpose": null,
    "reference_time": null,
    "temporal_intent": null,
    "metadata": {}
  }
}
```

Conceptual response:

```json
{
  "status": "ok",
  "items": [
    {
      "item_id": "opaque-sut-or-adapter-handle",
      "content": "...",
      "score": null,
      "rank": 1,
      "native_metadata": {}
    }
  ],
  "native_metadata": {}
}
```

A score is optional. Rank order is not assumed to be derived from a common unit across systems.

### 6.5 `correct`

Express a SUT-supported correction/replacement operation where the benchmark requires one.

This capability is distinct from writing a second contradictory fact.

The adapter must state whether correction semantics are:

- native lifecycle correction;
- mapped to an equivalent native update/version operation;
- derived/emulated outside the SUT;
- unsupported.

### 6.6 `forget`

Request deletion/forgetting according to SUT-native semantics.

The adapter must not conflate:

```text
logical deletion
physical deletion
retrieval suppression
tombstoning
expiry
benchmark namespace reset
```

A benchmark adapter may require one of these specifically.

### 6.7 `history`

Return SUT-native history/provenance/version information where supported.

No system is required to expose history merely to run retrieval tests.

### 6.8 `checkpoint`

Request durable synchronization/checkpoint if the SUT exposes one.

### 6.9 `recover`

Restart/reopen the SUT using its supported durability path.

A recovery benchmark may own the surrounding crash/kill process while the adapter supplies startup and readiness semantics.

### 6.10 `health`

Return bounded readiness state required by orchestration.

This must not become a product-health score. It answers only whether the test endpoint is ready to receive the next operation.

## 7. Optional capability families

The manifest may advertise additional semantic capability families without requiring new universal operations for each one.

### Retrieval

- lexical retrieval;
- semantic/vector retrieval;
- graph/relational retrieval;
- temporal retrieval;
- exact identity retrieval;
- hybrid/composed retrieval;
- abstention/no-result behavior;
- structured timeline/transition recall.

### Temporal

- caller-declared observation time;
- valid-from / valid-until;
- as-of recall;
- historical recall;
- prospective memory;
- event-relative queries;
- multiple clock support.

### Lifecycle

- correction;
- supersession;
- dispute;
- deletion;
- forgetting;
- retention/expiry;
- consolidation;
- reinforcement;
- decay/metabolism;
- pruning.

### Governance

- tenant isolation;
- scope isolation;
- purpose limitation;
- source/provenance policy;
- consent/sensitivity controls;
- mutation authorization;
- recall admission controls;
- auditability;
- policy/version evidence.

### Operational

- restart durability;
- checkpointing;
- tamper detection;
- concurrency;
- multi-writer behavior;
- bounded scale;
- deterministic replay.

### Agent/application

- personalization;
- multi-agent memory;
- memory-to-action/tool use;
- multimodal memory;
- user/profile memory;
- procedural memory.

Capability declarations are descriptive evidence. They are not trusted proof. A relevant Gauntlet suite may test the claim adversarially.

## 8. Capability requirement negotiation

Each Gauntlet profile should publish machine-readable requirements.

Conceptual example:

```json
{
  "profile_id": "governance-scope-isolation-v1",
  "requires": {
    "reset": ["native", "mapped"],
    "remember": ["native", "mapped"],
    "recall": ["native", "mapped"],
    "governance.scope_isolation": ["native"]
  },
  "optional": {
    "governance.audit": ["native", "mapped"]
  }
}
```

Negotiation outcomes:

| Outcome | Meaning |
| --- | --- |
| `eligible` | Required capabilities are truthfully available in accepted support classes. |
| `eligible_with_limitations` | Core protocol can run but optional dimensions will be unmeasured/partial. |
| `unsupported` | SUT does not claim the required capability. This is not an execution failure. |
| `blocked` | Required input, credential, environment, or adapter condition is unavailable. |
| `invalid` | Adapter manifest or capability claim is internally inconsistent. |

## 9. Transport

The first implementation should support a small number of explicit transport modes rather than pretending all memory systems look alike.

Candidate initial transports:

1. **stdio process adapter**: preferred local/reproducible boundary;
2. **HTTP adapter**: for service-native memory systems;
3. **in-process Python adapter**: useful for repository-local systems and baselines, but should not be required for external participation.

A shell-command transport may be added only if request/response framing can remain deterministic and safe.

Secrets must never be written into normalized evidence, manifests, or committed benchmark artifacts.

## 10. Operation result envelope

Every adapter operation should return a small common envelope:

```json
{
  "contract_version": "0.1.0",
  "operation": "recall",
  "status": "ok",
  "request_id": "...",
  "result": {},
  "error": null,
  "timing": {
    "elapsed_ms": 12.4
  },
  "adapter_evidence": {}
}
```

Statuses should include at least:

```text
ok
unsupported
refused
invalid_request
timeout
system_error
adapter_error
blocked
```

The distinction between `system_error` and `adapter_error` is important. Adapter defects must not be attributed to the SUT.

## 11. Error and timeout semantics

A benchmark profile owns whether one failed operation invalidates a case, a phase, or the entire run.

The Gauntlet must preserve the failure source:

```text
benchmark input failure
benchmark adapter failure
Gauntlet orchestrator failure
system adapter failure
system under test failure
expected SUT refusal
```

Expected governance refusals are observations, not infrastructure errors.

Timeout values must be profile/configuration evidence and must not change silently across compared runs.

## 12. Benchmark-state isolation

Every run must have an isolation strategy, such as:

- disposable process and temporary store;
- benchmark-specific namespace;
- benchmark-specific tenant/database;
- container/VM sandbox;
- remote test project explicitly created for the run.

The strategy must be recorded.

The Gauntlet must never run destructive deletion/reset operations against an adapter that cannot prove the target is a disposable or explicitly authorized benchmark namespace.

## 13. Governance and trust boundary

The system adapter is not trusted merely because it is installed.

For community-facing execution, future implementations should consider:

- process isolation;
- resource ceilings;
- network policy;
- filesystem sandboxing;
- secret scoping;
- output size limits;
- schema validation;
- path traversal protections;
- command allowlisting or explicit user authorization.

A benchmark dataset may contain adversarial content. Dataset text must be treated as data, not executable instruction for the Gauntlet host.

## 14. Benchmark fairness and privileged metadata

A benchmark adapter must declare what information is supplied to every system.

If an Agent Memory-specific lane receives rich metadata that another system does not receive, the lane is not automatically protocol-comparable.

Examples:

```text
text-only lane
explicit temporal metadata lane
provenance-aware lane
system-native enrichment lane
```

These may all be valuable, but they are different profiles.

Gold labels, evaluator answers, relevance judgments, and hidden test metadata must never be passed to the system adapter unless the benchmark protocol explicitly defines them as system inputs.

## 15. Native versus composed system identity

The Gauntlet may evaluate compositions such as:

```text
LLM + vector DB + custom memory policy
agent framework + memory plugin
memory service + host-side metadata layer
```

When adapter-side or host-side components materially change behavior, the `system.id` must identify the **composition**, not falsely attribute the result to one component.

Example:

```text
honest:
  system.id = "framework-x + custom-temporal-wrapper"

misleading:
  system.id = "framework-x"
```

## 16. Report obligations

A Gauntlet run report should include:

- SUT manifest;
- adapter identity and configuration;
- accepted and unsupported capabilities;
- benchmark/profile identity;
- native benchmark results;
- normalized evidence where mapping is defensible;
- infrastructure failures separately from SUT failures;
- capability limitations;
- provenance class of the benchmark;
- comparability posture;
- evaluator-integrity posture when measured;
- no universal overall score.

## 17. Conformance tests for adapters

Before an adapter may be used for published Gauntlet evidence, the Gauntlet should test the adapter itself.

Minimum adapter conformance should include:

1. manifest schema validity;
2. deterministic `describe` output for a fixed configuration;
3. reset/fresh-instance behavior;
4. remember-then-recall smoke test if those capabilities are claimed;
5. unsupported operation returns `unsupported`, not fabricated success;
6. timeout behavior;
7. malformed request rejection;
8. no benchmark gold metadata in SUT requests;
9. no secrets in emitted evidence;
10. adapter failure distinguishable from SUT failure;
11. configuration digest changes when behaviorally material configuration changes;
12. a declared `native` capability is not implemented solely in adapter-local state.

## 18. Versioning

This contract follows semantic versioning at the contract level.

- patch: clarifications or backward-compatible validation fixes;
- minor: additive operations/fields/support classes understood by older orchestrators through explicit compatibility rules;
- major: incompatible semantic or framing changes.

Adapters must declare the contract version they implement.

The orchestrator must fail closed on unknown major versions.

## 19. Relationship to existing Agent Memory evaluation contracts

This specification builds on, rather than replaces:

- `docs/53-memory-evaluation-subsystem.md`;
- `docs/54-memory-evaluation-cli.md`;
- `schemas/memory-benchmark-run.schema.json`;
- `reference/agentmem_ref/evaluation/`;
- benchmark-native runners and adapters.

The existing Memory Evaluation contract owns **evidence identity and comparison**.

This adapter contract owns **how an arbitrary external memory system can participate in execution**.

The future Gauntlet orchestrator composes the two.

## 20. Initial CLI target

The eventual user-facing surface should be shaped approximately as:

```bash
agent-memory gauntlet adapter validate ./system.yaml
agent-memory gauntlet adapter describe ./system.yaml
agent-memory gauntlet list
agent-memory gauntlet inspect <profile>
agent-memory gauntlet run --system ./system.yaml --suite <suite>
agent-memory gauntlet report <run-directory>
```

This is a product target, not an implementation commitment in this specification slice.

## 21. Acceptance criteria for the first executable adapter contract

The contract may move from specification to executable `1.0.0` when:

- a machine-readable manifest schema exists;
- at least three meaningfully different systems implement it, including Agent Memory, a simple baseline, and one external memory system;
- at least two distinct benchmark families run through the common adapter without protocol loss;
- unsupported capability is represented independently of execution failure;
- adapter-side derived behavior is visible in evidence;
- adapter conformance tests exist;
- normalized evidence retains exact system/adapter/config identity;
- benchmark gold/evaluator metadata cannot cross into SUT inputs accidentally;
- one governance suite can negotiate a native governance claim without requiring Agent Memory-specific APIs;
- no benchmark-specific branch exists in the SUT runtime.

## 22. Governing principle

> **The Gauntlet should make different memory systems testable on common ground without making them pretend to be the same system.**
