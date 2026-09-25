# RC1 Evidence Closeout

Status: active RC1 release-evidence package for issue #481 under umbrella #410.

## Purpose

Agent Memory now has a supported developer facade and a deterministic end-to-end cognitive-memory scenario. The remaining RC1 closeout problem is therefore not another architecture slice. It is evidence packaging: state exactly what the current runtime proves, keep evidence dimensions separate, and refuse to turn external blockers into invented results.

The machine-readable companion is emitted by:

`reference/run_rc1_evidence_closeout.py`

## Current product boundary

The bounded RC product path is:

```text
AgentMemory.open(...)
-> remember
-> multi-route candidate generation
-> governed final admission
-> correct / supersede
-> close and reopen
-> corrected state remains current
-> governed prune / forget
-> close and reopen
-> tombstone, history, currentness and configuration binding reconstruct
```

The developer facade landed through #478. The composed lifecycle proof landed through #480.

## Evidence dimensions

### Product usability

Status: **bounded**.

The facade and scenario prove a developer can use the supported local runtime without manually assembling internal PAMA objects for ordinary low-risk work. Governed decisions and receipts remain inspectable.

This is not a production 1.0 claim.

### Retrieval and memory quality

Status: **bounded**.

#466 provides the continuous retrieval and memory regression contract. #469 provides the protocol-ready real SWE-ContextBench Lite runner that preserves the 99-query / 100-gold-edge denominator, including the multi-gold query.

Repository-owned deterministic fixtures are useful regression evidence. They are not a substitute for the exact external corpus and selection provenance required for protocol-comparable measurement.

### Performance

Status: **bounded**.

The qualified SQLite single-host profile and benchmark runners report performance separately from retrieval quality and governance. No universal latency, scale, or resource envelope is claimed.

### Governance

Status: **bounded**.

Current evidence includes wrong-scope refusal, supersession/currentness behavior, confidence non-authority, metabolism non-authority, external-peer evidence normalization, and the exact-version Agent Manifest 0.12.0 plus TRACE 0.10.0 qualification.

The governing boundary remains:

```text
retrieval relevance != recall authority
confidence != mutation authority
external verification != Agent Memory authority
checkpoint acceptance != appended-operation semantics
```

### Runtime recovery

Status: **bounded**.

The qualified `sqlite_single_host_v1` profile reconstructs correction/currentness, history, tombstone state, and configuration binding across restart in the RC scenario.

Distributed or multi-host SQLite behavior is not established.

## External SWE-ContextBench status

Status: **external blocked** under #467.

The Agent Memory runner is ready. Protocol-comparable measurement still requires the exact frozen inputs from the external rerun:

- exact redacted past-task projections;
- exact batch and distractor selection;
- consistency-query identity when explicitly selected.

Until those inputs and their provenance are available, the truthful statement is:

```text
runner readiness = complete
protocol-comparable external result = not yet available
```

No external score is inferred from the public parquet subset or from historical metadata.

## Harvest closeout status

Status: **open** under #470.

The planned native-harvest sequence through semantic/vector retrieval, typed temporal/entity/causal graph traversal, memory metabolism, and continuous regression is complete. That is not the same claim as exhaustive ancestry absorption.

#470 remains responsible for final disposition of the remaining implementation-ancestry, UOR, external-peer, and source-rights rows. Its open status does not prevent repository-owned RC evidence packaging, and RC evidence packaging does not close #470 by implication.

## Known limitations

Current RC evidence does not establish:

- production 1.0 readiness;
- distributed SQLite durability;
- a protocol-comparable external SWE-ContextBench result before exact frozen inputs arrive;
- exhaustive ancestry/source-rights harvest completion;
- physical permanent-deletion completion from the reversible pruning path used in the RC product scenario;
- answer-generation quality from retrieval-only evidence;
- authority from confidence, similarity, reinforcement, graph proximity, vector score, metabolism score, or external verifier success;
- a learned controller with authority over PAMA, durable commit, deletion, tenancy, scope, or recall admission.

## Reproducible closeout artifact

Generate the machine-readable manifest against an exact revision:

```bash
PYTHONPATH=reference python reference/run_rc1_evidence_closeout.py \
  --agent-memory-revision <exact-40-hex-commit> \
  --output rc1-evidence-closeout.json
```

The manifest preserves product usability, quality, performance, governance, runtime recovery, external benchmark status, and harvest status as separate surfaces. It deliberately emits no aggregate memory-health score.

## Release posture

RC1 should be evaluated as a usable, governed, single-host memory system with explicit evidence boundaries. It should not be marketed or documented as production 1.0 merely because the bounded RC gates are green.

The next evidence changes should update this package only when a real underlying gate changes, especially #467 or #470. Cosmetic score inflation would be easier, naturally, which is precisely why it is not the contract.
