# Exact-head qualification of the integrated #776/#777 candidate, with #772 and the DUR-DEL-001 repair

**Maturity:** implemented and locally tested on the exact head of this branch; **not independently
reviewed, not a successor declaration, not published.** No GitHub Actions, no main merge.
**Base:** `implementation/776-777-integrated-contract-1-7-no-ci` @ `6eaf5e8af308f016dae3a63d253bf73188d6e214`
(0 behind `main` `3eebb6d`). Published baseline stays v6; the open v7 declaration is not edited here.

## 1. Exact-head execution of the integrated candidate (the gate #776/#777 left open)

| Suite at `6eaf5e8` | Result |
|---|---|
| `test_776_*`, `test_777_*`, `test_api_*` | 115 passed |
| full reference suite (`python3 -m pytest reference/tests tests`) | 2755 passed, 5 failed, 34 skipped |

The five failures were four protected-surface freeze guards (`test_644_v7_gauntlet_identity`,
two `test_770…ReplayEvidenceFreshness`, `test_benchmark_integration_contract…equivalence`) and
`test_gauntlet_durability…first_durability_slice`. The durability failure was **not** the
`adapter_eof` transport failure earlier reports attributed it to: it was a behavioral regression,
DUR-DEL-001 `tombstone_retained` (`history_tombstoned: False` after a committed `forget`). On
`main` the same test passes (full suite on `main` `3eebb6d`: 2540 passed, 0 failed, 34 skipped).

## 2. DUR-DEL-001 repair: owner-scoped tombstone visibility (#776/#777)

The #777 projection made a governed-deleted memory read as *unknown* even to the scope that
deleted it, and moved the pre-existing developer-facade assertion onto the internal
`_canonical_history`. That contradicts docs/44 (`history` returns `tombstoned`), the frozen
durability profile DUR-DEL-001, and goes beyond what #777 decided (no deleted-generation
identifiers, timestamps, topology; out-of-scope indistinguishability).

Reconciled contract (`GovernedMemoryAdapter.public_deleted_visible`, `AgentMemory.history`):

- a reader who could have read the deleted head (same tenant; domain, project and task eligible
  against the canonical `_fact_scope`, which survives pruning and permanent deletion) reads
  `{"current_fact_uuid": null, "tombstoned": true, "events": [], "state_version": <canonical>}`
  and, with a value probe, `rejected_values: []`; no deleted-generation identifier, timestamp,
  event or value is served;
- a reader outside that scope reads byte-identically to a memory that never existed;
- a re-created memory shows only its live generation.

`test_776_777_owner_tombstone_review.py` covers live and restart reads, other-project
indistinguishability (history and logical-reference recall), re-creation, cache/query-order
independence, deleted-identifier probes, derived memories citing a deleted source, permanent
deletion, and that the projection is the identity on the canonical document until a deletion
exists. `test_777_public_projection_review` and `test_developer_facade` are realigned.

## 3. #772: the superlinear retain is the JSON checkpoint journal walk, not SQLite

| Path | 1000 governed writes | Growth |
|---|---|---|
| `AgentMemory.remember` (qualified SQLite), main and candidate, with/without typed propositions, shadow control | 5.8–6.9 s | flat, ~6 ms/write to 2000 |
| `ConfiguredCompositionRuntime.retain` (JSON checkpoint), before | 28.8 s | 11 → 55 ms/write by the 4th 250-write segment |
| same, after | 15.0 s; 3000 writes 89 s | 9 → 21 ms/write; the remaining growth is the whole-state serialization inherent to the JSON profile |

`JsonRuntimeStateStore` re-read, re-parsed and re-digested every journal record per checkpoint.
It now remembers the validated prefix (length, lines, running SHA-256, last record) per instance,
re-hashes the prefix bytes and chains only appended records; any prefix change, an unterminated
prefix or a shorter file falls back to the full walk. `test_772_journal_validation_scaling.py`
pins the cost bound and that seven prefix mutations reach exactly the cold recovery's verdict.
The checkpoint also serializes each payload once (bytes and digests unchanged; the
`_atomic_json_write` crash-injection seam is kept).

A second read-path cost from #777 is removed: with no governed deletion the public scrub is a
single-traversal copy (all-admitted recall at 2000 facts: 381 ms → 302 ms; main 253 ms).

## 4. Baseline succession: explicit, reviewable, not applied

`scripts/check_runtime_baseline_equivalence.py --candidate HEAD` fails on this branch exactly as
on its parent: the protected surface differs from the frozen v7 declaration (11 changed paths
versus the 8 it declares; public contract 1.6.0 → 1.7.0). Two ways to make it `TRANSITION` were
prepared mechanically and **neither is applied**, because both are the succession decision the
owner reserved:

- `reports/runtime/proposals/644-v7-declaration-amended.PROPOSED.json`: the open v7 declaration
  re-run through `scripts/declare_runtime_baseline_changes.py` at this head plus the identity
  delta. Applied in a scratch copy, the checker prints `TRANSITION … 11 declared blobs;
  deltas=identity.public_contract_version 1.6.0->1.7.0`. Cost: the frozen `-v7` lane records bind
  the v7 declaration blob and `public contract 1.6.0 unchanged`, so they stop binding (the #770
  guards `every_agent_memory_row_carries_the_v7_posture` and `binding_admits_only_the_v7_posture`
  turn red); a new lane generation would be needed, as docs/67 requires for a successor.
- the owner's cumulative v6→v8 draft and chained v7→v8 draft, re-pinned to this head's blobs (the
  chained draft now lists the five paths that differ from the frozen v7 blobs, including
  `restart_runtime.py`).

Until one is sanctioned, four guards stay red by design: `test_644_v7_gauntlet_identity`
(contestant pinned to `16a248b`), the two #770 replay-freshness tests (evidence recorded at
`16a248b`), and the benchmark-integration equivalence test (checker FAIL). Fresh replay evidence
for this head is recorded separately (section 5) without overwriting the `16a248b` packages.

## 5. Evidence for this head

See `reports/validation/644-v7-replays-at-head/` (filled by the evidence commit): the five v7
replay contracts re-executed at this head with `scripts/verify_644_v7_replays.py --reexecute`,
and the public Gauntlet orchestration probe run against a scratch contestant pinned to this head.
