# Developer Facade and Local Open Path

Status: RC1 developer-facing surface for issue #477 under umbrella #410.

## Purpose

Agent Memory already had a schema-backed public contract, a restart-safe composition, and a qualified transactional SQLite substrate. What it did not have was a small installed surface that let a developer open that composition and use the memory lifecycle without manually assembling internal PAMA dataclasses.

The RC facade is deliberately a wrapper, not a second API doctrine:

```text
AgentMemory facade
    -> public contract 1.2.0
    -> validated runtime-configuration plan
    -> SQLite configured composition
    -> PAMA / lifecycle / recall admission
    -> canonical receipts and audit evidence
```

Convenience never becomes authority.

## Install and open

From a checkout:

```bash
python -m pip install .
```

Then:

```python
from agentmem_ref import AgentMemory

with AgentMemory.open("./agent-memory-state", tenant="tenant:local") as memory:
    retained = memory.remember(
        "memory:preferred-editor",
        "Preferred editor is VS Code",
    )

    recalled = memory.recall(
        "preferred editor",
        logical_memory_refs=("memory:preferred-editor",),
    )

    history = memory.history("memory:preferred-editor")
    posture = memory.posture()
```

The first open writes an inspectable `runtime-config.json` from the packaged `rc1-local.json` profile and initializes the qualified SQLite state. Later opens validate the same configuration and recover the existing SQLite state. Existing or partial durable state is never silently replaced with an empty runtime.

## Explicit defaults

The local facade makes these ordinary-use defaults visible in its constructor rather than hiding them in policy:

```text
tenant             tenant:local
actor              agent:local
charter            charter:local-v1
scope              project:local
purpose            local memory
contract            1.2.0
```

`remember()` maps to a low-risk reversible `promotion` proposal. The result is still a governed `commit` result with its PAMA decision and receipt.

`correct()` maps to the existing `correction` operation. Corrections are not convenience-authorized. If current PAMA requires review, calling `correct()` without qualifying evidence returns that review outcome and leaves current state unchanged. Callers may supply the existing evidence or external-verification inputs explicitly.

`forget()` defaults to reversible `pruning`, which tombstones current influence while preserving reconstructable history. `forget(permanent=True)` maps to the stricter `permanent_deletion` operation and does not acquire extra authority merely because it was requested through the facade.

## Recall

`recall()` uses the configured multi-route planner and then the one canonical governed admission boundary.

The result keeps:

- candidate identifiers separate from admitted identifiers;
- refusal decisions separate from ranking;
- per-candidate route provenance inside the existing `admissions` object;
- exact-identity, lexical, and bounded relational provenance when those routes produce a candidate;
- retrieval evidence at `authority_effect = none`.

The packaged local profile does not enable a learned retrieval controller. It also does not claim a vector route is active merely because native vector machinery exists elsewhere in Agent Memory. A route is reported only when that configured runtime actually executes it.

## Posture

`posture()` returns the public posture stage backed by the canonical doctor implementation. The doctor now recognizes both historical file-checkpoint state and the qualified SQLite runtime. For SQLite it reports configuration binding, exact recovery, base SQLite durability profile, SQLite version, substrate profile, and currentness separately.

It does not emit a universal health score. Configuration validity, durable-state recovery, currentness, and provider availability remain separate facts.

## Recovery and failure posture

The local open path is fail closed:

```text
SQLite database present
    -> recover and verify

configuration binding present but database absent
    -> refuse as incomplete state

SQLite database corrupt or incompatible
    -> refuse recovery

requested tenant differs from recovered tenant
    -> refuse recovery
```

The facade never interprets a recovery problem as permission to create fresh memory over the same state directory.

## Threading contract (#530)

One `AgentMemory` handle may be called from any thread, including worker pools and async executors. Every public operation (`remember`, `correct`, `recall`, `forget`, `history`, `posture`, `close`) runs under a single runtime-owned reentrant lock (`handle.runtime.serialization_lock`). That lock also guards the SQLite connection, the observed generation (CAS), governance state, visibility snapshots, and journal publication.

- Operations never interleave. Each still commits as one single-writer SQLite generation.
- Concurrency therefore gives correctness, not parallel write throughput.
- A failing operation rolls back and restores governance state before the next operation runs.
- Closing waits for any in-flight operation. Later calls from any thread raise `RuntimeError("AgentMemory runtime is closed")`.
- Objects reached through `handle.runtime` are not independently thread-safe. Direct callers must hold `handle.runtime.serialization_lock`.
- Multiple independent handles on the same store in one or more processes are not part of this contract. The bounded single-host profile remains single-writer, with generation-conflict detection.

## Boundaries

This surface does not establish:

- production 1.0 readiness;
- distributed SQLite semantics;
- multi-host consensus;
- automatic review or approval;
- learned authority;
- a universal memory health score;
- a dependency on EvolveAI, CodeGenome, COREFORGE, Jev, TRACE, Agent Manifest, or another peer;
- completion of the external SWE-ContextBench evidence gate.

It closes a product usability gap: the already-governed architecture can now be opened and exercised as one developer-facing system without weakening the machinery underneath it.
