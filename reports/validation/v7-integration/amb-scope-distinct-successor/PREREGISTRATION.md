# AMB v7 scope-distinct successor: pre-score qualification contract

**State: FROZEN CANDIDATE ONLY; ZERO NEW SCORE RUNS.**
Created on 2026-10-28 from the integrated v7 branch at
`f0a001b42100186edaceca2f61a59207ba6c94e7`, after the original
`amb-precisionmembench-retrieval-v7` Agent Memory control aborted at its
second-user open. This record was written before any execution of the successor
control. It is not lane acceptance, v7 publication, or independent review.

## Immutable identities and scope

- **Original, untouched**: `reference/amb_agent_memory_bridge.py`
  (bridge 0.4.0, blob `3d9ccb31587b55edf4ddb714d6e8ff41d5b03228`),
  `reference/run_amb_external.py`, and frozen
  `amb-precisionmembench-retrieval-v7`. The blocked control remains blocked.
- **New bridge**: `reference/amb_agent_memory_bridge_scope_distinct.py`
  (bridge 0.5.0, blob `535da278990f1619934544d4e406d0c315233403`).
  Its only executable differences from 0.4.0 are importing
  `STORE_PROFILE_SCOPE_DISTINCT`, reporting bridge 0.5.0, and passing
  `store_profile=scope_distinct_v1` on *both* ingest and retrieve.
- **New runner**: `reference/run_amb_external_scope_distinct.py`
  (blob `f2ff518eb3ea1e542ced1f4fcd939fabc6dd331f`).
  It imports the new bridge without modifying the frozen external runner.
- **New lane**: `amb-precisionmembench-retrieval-v7-scope-distinct-v1`, stored in this separate qualification directory (not under `reference/agentmem_ref`), to preserve the exact package tree pinned by the unexecuted `mesa-formal-v5` freeze;
  `status=frozen` before its first score. It binds the integrated candidate
  v7 declaration blob `981108866e45a46b9e96ab283517324d6349e586`
  and the new bridge and runner blobs.

The same one SQLite root hosts the 34 `test-user` documents and one
`other-user` negative control under distinct project scopes. The bridge's
stable `_scope(user_id)`, `_logical_id(user_id, document_id)`, and global
fact UUID-to-document index are unchanged. Nothing enables raw tenant-wide
handles, caller-controlled scope upgrades or legacy store migration.

The original AMB external checkout remains pinned at
`03c1d0f1d27da63034f0931121c858faba512383`.
The two dataset fixtures and their individual and combined SHA-256 digests,
all 77 query cases, case ordering, budgets, gold identities, scorer, dependency
posture, telemetry and 0-limited cross-fact obligation are unchanged.

## Preregistered acceptance falsifiers

1. The old bridge must still fail with `StoreIdentityError` on the second
   project. The new bridge must ingest both without creating a second root or
   reusing a project key across scopes.
2. The exact same public document ID in different scopes must not overwrite
   either fact; no UUID-to-document index collision or cross-user disclosure
   is permitted.
3. Two-user retrieval, restart with `reset=False`, project-bound visibility,
   the blank-query cases, scope-derived IDs and cross-fact sidecar ordering
   must match the frozen external harness contract.
4. Store profile can be selected by trusted benchmark setup, not changed by an
   untrusted caller or an overridden facade handle. A stale/default-profile
   attempt must continue failing closed.
5. Pre-score independent review must confirm **only the authorized bridge
   change**, full 77-case selection, unchanged scorer/gold/budgets, correct
   pinning, clean fixtures, and no alternate raw access path.
6. Execute the **entire** 77-query Agent Memory control under the pinned
   external AMB harness. Compare its exact accepted-v6 case fields:
   `correct`, `context`, `relevant_beliefs`, `pinned_beliefs`,
   `retrieved_questions`, `retrieval_precision`, `retrieval_recall`,
   `pinned_coverage`, `resolution`, `failures`, `retrieved_count`,
   plus returned-document and cross-fact records. Require 77 EQUAL verdicts
   and per-case cross-fact 0 limited. Any difference is a STOP and independent
   investigation, never permission to retune cases or relax equality.
7. BM25 and Mem0 comparators are frozen for a successor run, not automatically
   accepted from v6/v7. Prefer reexecute all three qualified rows under the
   successor's exact environment and pin every artifact/digest before import.
8. A changing runtime/declaration/bridge/lane digest invalidates the successor
   result. Re-freeze under a new lane ID rather than edit a scored lane.

## Executable qualification commands (on an authenticated full checkout)

From the repository root with pinned Python 3.12 and reference dependencies:

```sh
python3.12 -m unittest discover -s reference/tests -t reference -p 'test_amb_scope_distinct_*.py' -v
python3.12 -m unittest discover -s reference/tests -t reference
```

Use `reference/run_amb_external_scope_distinct.py` with the frozen external
`--amb-root`, passing `run --dataset precisionmembench --split single-turn
--mode retrieval --memory agent-memory`, plus the identical frozen control
sidecar environment and package pins. The exact invocation, input/blob
verification, 77 raw cases, baseline comparison, stdout/stderr, execution
identity and integrity checks must be recorded before any import.

## Qualification limits

No executable benchmark, SQLite integration or Python suite has yet been run
against these new commits by this GitHub-only authoring environment. The
successor is an **unexecuted frozen engineering candidate**. The original v7
lane is still the named item in the live v7 declaration, so publication remains
blocked until independent review, complete external lane execution, a governed
declaration/manifest successor binding, and docs/67 publication evidence.
No Actions, merge, release, tag, evidence rewrite or register change is authorized.
