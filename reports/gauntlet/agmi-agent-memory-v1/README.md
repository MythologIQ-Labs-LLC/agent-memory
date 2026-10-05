# agmi Agent Memory integrity qualification

This slice qualifies `tech4biz-yasha/agmi` as independent external integrity evidence for Agent Memory Runtime Baseline v1. It does not add agmi as a runtime dependency and it does not remediate findings discovered by the benchmark.

## Exact source boundary

- agmi repository: `tech4biz-yasha/agmi`
- agmi revision: `76ddf21af25ce35e427e5614afb70d1fe96e32a2`
- package: `agent-memory-integrity` `0.6.2`
- license: MIT
- upstream adapter: `agmi/adapters/agent_memory.py`
- upstream Agent Memory test: `tests/test_agent_memory.py`
- Agent Memory frozen runtime revision: `f2aef57293b516e065cad5d0afea26ac7e3c28a9`
- Runtime Baseline v1 merge: `32783fad3c5cf50a9d712c8bcc0a023907ce9433`

The CI qualification refuses to run if `reference/agentmem_ref` or `pyproject.toml` differs from the frozen runtime revision. That allows qualification work to evolve around the runtime without silently moving the measured system.

## Attacked persisted surface

The upstream adapter uses the public `AgentMemory` facade for normal seed/read lifecycle operations and direct SQLite access only for the attacker-side mutation. T1-T8 target the canonical `facts` table while deliberately leaving the integrity digest structures and `configuration-binding.json` sidecar untouched. T9 restores an older genuine copy of the complete state directory after a newer genuine write.

The evaluator's ability to edit disposable storage is not treated as a native Agent Memory capability.

## Expected external observation

The frozen upstream result is intentionally mixed:

| Attack | agmi observation | Gauntlet behavioral outcome | Evidence qualification |
| --- | --- | --- | --- |
| tamper | `safe` | pass | sufficient |
| truncate | `safe` | pass | sufficient |
| delete_middle | `safe` | pass | sufficient |
| reorder | `safe` | pass | sufficient |
| forge | `safe` | pass | sufficient |
| cross_replay | `safe` | pass | sufficient |
| rollback_replay | `safe` | pass | sufficient |
| metadata_tamper | `safe` | pass | sufficient |
| snapshot_rollback | `VULNERABLE` | fail | sufficient |

For the Agent Memory adapter, detection occurs on the read/open path. The eight raw row-level edits are refused by runtime recovery/integrity checks. T9 is different: rolling back the SQLite store and its colocated configuration-binding sidecar together restores a previously genuine state, so the older directory opens as current and the newest genuine memory is absent without an integrity error.

That T9 finding is part of the evidence contract. CI must preserve it. This qualification is successful when the external result is reproduced accurately, not when every security cell is green.

The upstream pinned test also records that the current persisted row-digest scheme uses unkeyed SHA-256. Recomputing those digests after an edit is outside the frozen T1-T9 attack contract and remains an explicit limitation rather than an implied tested capability.

## Vocabulary mapping

`agmi safe` with read-path detection maps to a Gauntlet behavioral pass with sufficient evidence and detection point `read`.

`agmi reported` in systems that detect only through a separate audit surface may map to a behavioral pass, but detection point `audit` remains explicit and must never be presented as read-time refusal.

`agmi VULNERABLE` maps to behavioral failure only when the system actually claims the corresponding integrity behavior. A system with no such claim remains `unsupported` for claim qualification while the external observation may still be preserved descriptively.

An agmi error or failed mutation-landed guard maps to `blocked` with insufficient evidence, not pass or fail.

## #571 coverage ruling

Accepted external coverage is intentionally narrower than the full durability program:

| #571 capability | agmi posture |
| --- | --- |
| tamper_detection | `exact_external_coverage` |
| journal_integrity | `compatible_external_coverage` |
| snapshot_generation_binding | `exact_external_coverage` through T9 pressure |
| restart_recovery | `not_covered` |
| checkpoint_recovery | `not_covered` |
| durable_deletion | `not_covered` |
| durable_correction | `not_covered` |
| concurrent_handle_safety | `not_covered` |
| stale_writer_rejection | `not_covered` |
| deterministic_recovery | `not_covered` |
| migration_compatibility | `not_covered` |
| mixed_version_recovery | `not_covered` |

The resulting integration ruling is **partial reuse** if the pinned reproduction succeeds: use agmi for independent storage-integrity/tamper evidence and keep #571 native for positive recovery, lifecycle durability, concurrency, stale-writer and migration qualification.

## Evidence classes

The raw agmi row against Agent Memory is `independent_external_benchmark` evidence.

The workflow, normalization and provenance checks in this repository are `gauntlet_external_integration` evidence.

The remaining #571 tests are `gauntlet_native_gap` evidence.

Agent Memory's internal restart/integrity tests remain implementation-conformance evidence. None of these classes silently substitutes for another.
