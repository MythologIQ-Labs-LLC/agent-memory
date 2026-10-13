# #774 + #776 interop contract: reused logical memory IDs and lineage generations

**Status:** TEST-ONLY PREREGISTRATION, NOT EXECUTED, NO MERGE PROPOSED.
**Base:** `implementation/774-anchor-guard-and-routing-no-ci` @
`a6745a9218a46f99d57a049ed9203294f96959af`.
**Proposed #776 repair source blob:** `reference/agentmem_ref/runtime/adapter.py`
Git blob `251972b0f85a4bdc286db9d58f23f35cf7479d6c`;
this blob is **not** imported to this test-only branch.

## Why this contract exists

#774's `memory_deleted(fact_uuid)`,
`lineage_head(fact_uuid, context)` and
`governed_state_change_predecessor(fact_uuid, context)` inspect
`memory_id in tombstoned_ids()`. That is invalid after #776:
a `forget`/pruning tombstone attaches to a historical *generation*
of a logical memory, and a subsequent properly governed `remember`
with the identical logical memory ID creates a **new live generation**.
Reusing the logical ID does not revive the deleted generation or make
all future facts deleted.

## Four predeclared tests

`reference/tests/test_774_776_lineage_recreation_contract.py`:

1. Deleting an old lineage, then re-creating the same logical memory
   ID must make the new current fact visible, without returning any
   old deleted version in explicit historical retrieval.
2. The new generation's head must not traverse into the deleted
   generation to invent a predecessor.
3. Tombstoning only one superseded version must not mark its still-live
   current successor deleted or hide it from current recall.
4. Reuse of one deleted memory ID must not disrupt an unrelated
   memory's valid historical predecessor, even with overlapping text.

No test is claimed to pass here. The precombined #774 candidate is
expected to fail. Tests are intended to be executed first on the
unaltered code to verify they detect the conflict, and only then on
a deliberately planned integration of independently qualified P0 #776
and historical targeting #774.

## Required integration implementation

- Represent lineage generation by **fact identity plus governed
  deletion-record membership**, not by `memory_id` alone.
- A public visibility gate for a fact must use the same canonical
  admission/deletion decision as `write_semantics` and recall.
  Do not inspect internal caches, emulate admission decisions or
  resurrect previously deleted generations from previous events.
- Historical predecessor traversal must not cross generation
  boundaries after memory-ID re-creation. Ordinary stated
  state-change history remains reachable when not deleted.
- Deletion of one superseded fact must not hide its live successor.
- If the resolved successor is outside reader scope or has been
  deleted, return no predecessor without leaking the fact ID.
- A global forbidden/deleted set must not be used to mark all future
  facts of the same logical memory identifier.
- Repeat independent Brightwater/Fenmoor and Halcyon/Cedarline
  quality corpora, original admissibility/temporal suites, persistence,
  graph and public API paths, plus truly unseen cases.

This branch intentionally **does not combine** #774, #776 or #773
protected runtime changes. A sanctioned successor declaration,
exact-SHA independent replay and explicit user approval are required
before any protected combined candidate can be considered for merge.
No GitHub Actions, PR or published baseline changes.
