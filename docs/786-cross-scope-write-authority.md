# #786 cross-scope write authority: a live logical memory is writable only by its scope

**Status:** IMPLEMENTED and TESTED on `claude/eager-dirac-bftkfg-786-write-authority`
(stacked on PR #784 @ `060e7cd`); INDEPENDENTLY REVIEWED at `36a6ef4d` with every confirmed finding remediated (section below); NOT DECLARED
(protected change outside the published v6 and frozen v7 declarations), NOT QUALIFIED as a
baseline successor, NOT MERGED.

## The invariant

A governed write (`promotion`, `correction`, `pruning`, `permanent_deletion`, dispute) that
targets a logical memory with a **live current fact** is admitted only if the writer is
eligible for that fact under the same tenant / isolation-domain / shared-membership /
project / task gates recall applies (`GovernedMemoryAdapter._domain_identity_refusal`).
A refused write changes nothing: not the head, not the version, not the rejected-value
registry, no tombstone, no dispute mark, no episode, no new generation.

An id with **no live head** (never written, or governed-deleted) is open: creation is
unchanged, and the #776 re-creation of a deleted id by another scope still produces a fresh,
isolated generation (the former owner's tombstoned view is stable; the new generation sees
nothing of the old one; the old owner can no longer write the id while the new generation is
live; every deleted generation stays a #774 as-of barrier for everyone).

## Source-level cause (before this branch)

Logical memory ids are tenant-wide and every write path resolved its target through
tenant-wide maps with no scope check on the target:

- `commit_proposal` (`promotion`/`correction`) consulted `_is_stale`, the rejected-value
  registry and `_supersede_current` on `_current_fact_by_memory[target]`, then wrote a new
  current fact. Any same-tenant proposal replaced the head.
- `_delete_refusal` / `_dispute_refusal` checked existence, tenant and fact->memory binding,
  but not the writer's project/domain/task eligibility.
- The facade (`AgentMemory.correct/forget/dispute`) resolved "does the target exist" with
  `adapter.current_fact_uuid(target)` (tenant-wide) and resolved its `state_snapshot` from the
  tenant-wide `state_version`, so a refused out-of-scope writer still learned the protected
  memory's version through its proposal and receipt.
- `commit_proposal` added the optional `episode` to the substrate **before** policy evaluation
  and target admission (hypothesis in the #786 review comment, now falsified as true for the
  pre-repair tree: a `require_review` denial and a cross-project denial both persisted the
  episode durably, `reference/tests/test_786_cross_scope_write_authority.py::DeniedProposalWithEpisode`
  fails on `060e7cd` and passes here).

## The repair (canonical boundary first)

`reference/agentmem_ref/runtime/adapter.py`:

- `writer_context(...)` / `_writer_context(proposal)`: the authority context a write carries,
  derived exactly as `_write_scope` derives the scope a new fact is stored under.
- `fact_eligible_for_writer(fact_uuid, proposal)` / `fact_eligible_in_context`: the recall
  gates applied to a writer; unknown scope is ineligible (fail closed, as on read).
- `write_target_refusal(proposal)`: live head outside the writer's scope -> refusal, evaluated
  **before** staleness, readmission and the rejected-value registry. `promotion` reports
  `target_unavailable` (`WRITE_TARGET_REFUSAL`); every operation that presupposes an existing
  fact reports `fact_not_found`, the same token an id nobody wrote reports.
- `commit_proposal`: a refused target selects as a blocked action, commits nothing, reports
  `before_state = after_state = "v0"`, and the `episode` is now added only inside the commit
  branch, so no refused or parked proposal leaves episodic content.
- `_delete_refusal` / `_dispute_refusal`: after the existence and tenant checks and before the
  binding map is consulted, an ineligible fact reads `fact_not_found`; a refused deletion or
  dispute reports `v0` states.

`reference/agentmem_ref/api/surface.py` (result-shape and non-disclosure only; the authority
decision is the adapter's):

- `_writer_context(envelope)`, `_visible_head(target, envelope)`, `_state_snapshot(target, envelope)`:
  the proposal's **effective** scope (overrides applied) decides whether the facade treats
  the target as present; `correct`, `forget` and `dispute` from another scope return the
  identical bare `fact_not_found` result the unknown-id case returns, and `remember` carries
  `state_snapshot: v0` so neither the proposal id nor the receipt discloses the protected
  memory's version.

## Dispositions for the same-class paths (each tested, not assumed)

| path | pre-repair | now |
|---|---|---|
| B `remember` onto A's live head | commits, replaces A's head | refused `target_unavailable`, `v0/v0`, A intact |
| B `correct` A's head | commits, invalidates A's fact, records rejected value | bare `fact_not_found` identical to unknown id; A's fact stays valid |
| B `forget` / permanent forget of A's memory | commits, tombstones / physically deletes A's lineage | bare `fact_not_found`; no tombstone |
| B `dispute` A's memory (by id or by fact uuid) | commits, marks disputed | `fact_not_found`; no dispute mark |
| B re-creates A's **deleted** id | allowed (fresh generation) | unchanged, with isolation proven (A cannot write it back while B's generation is live) |
| three generations across two scopes | #774 barriers | barriers hold for both contexts; B's own view is its DUR-DEL-001 tombstone |
| wrong-scope correction after restart (x2) | commits | refused; `_fact_scope` survives every restart |
| concurrent second handle / racing threads | B's write commits through its own handle | B never commits; A's head intact; a handle behind the generation gets the designed `RuntimeCheckpointConflict` |
| forged partial scope (`project_ref` only, `tenant_ref`) | commits | refused (`required_isolation_domain_missing` / `project_scope_mismatch` internally; nothing disclosed) |
| override leaving `required ⊄ domains` (domains only, or domains + project) | commits or PAMA-blocks with a version-bearing receipt | malformed proposal, `ValueError` before any target is resolved (review F3) |
| override with a superset of domains + the owner's project | commits, orphans the head | `remember`/`correct` refused by scope continuity (review F2); `forget`/`dispute` admitted as an eligible reader's |
| forged **complete** scope via `overrides` | commits | commits (documented: `overrides` is the host re-declaring scope exactly as `AgentMemory.open(scope=...)` would; existing fixtures depend on it; the facade is not an authentication boundary) |
| denied proposal carrying an episode (cross-project and `require_review`) | episode persisted and recoverable after restart | no episode; committed proposals keep theirs |
| same text in unrelated memories of two projects | independent | independent (positive control) |
| shared-domain member / non-member, task-scoped head (adapter level) | any same-tenant writer | member and same-task writers commit; others refused as above |

## Independent adversarial review of `36a6ef4d` and its remediation

An independent reviewer (separate worktree, 39 probe tests, `reference/tests/test_zz_786_review.py`
in its worktree; the confirmed ones are ported into `test_786_cross_scope_write_authority.py::ReviewFindings`
and `::ProceduralReviewFindings`) reported seven findings. Dispositions:

| # | finding | severity | disposition |
|---|---|---|---|
| F1 | a deleted generation's rejected values blocked a fresh generation of the id (`rejected_value_requires_reconciliation`, a content oracle) and were served to it through `history(fact_text=...)` | P0 confidentiality / P1 availability | FIXED: `_readmission_blocked` ignores rejections whose superseded fact is deleted or when the id has no live head; the public `history` projection drops rejected values of deleted generations |
| F2 | an override declaring a *superset* of domains plus the owner's `project_ref` passed the eligibility gates and stored a head with `required_domain_refs` the owner does not hold: the memory became unreadable by everyone | P1 integrity (owner lockout) | FIXED: `write_target_refusal` now also requires **scope continuity** -- the head's own scope, read as a context, must be eligible for the scope the new fact would be stored under. A write cannot move a live memory out of its holders' reach (orphaning, or private capture of a tenant-wide or shared memory). Deletion and dispute store no scope and need no continuity check; a superset-domain writer is an eligible reader and may delete or dispute (documented) |
| F3 | an internally inconsistent override (`required ⊄ domains`) was judged visible, then blocked by PAMA, and its receipt carried the protected version | P1 confidentiality | FIXED: the facade refuses such a proposal as malformed (`ValueError`, identical for any target) before any target is resolved |
| F4 | `revoke_skill` copied the *target's* scope into the revocation, making the gate vacuous there | P1 design bypass | FIXED: the caller declares its scope (`scope`, `isolation_domain_refs`, `required_isolation_domain_refs`, `purpose`); no declaration proposes under the bare component label and fails closed; callers updated |
| F5 | `propose_skill`'s version rule disclosed another scope's version in its `ValueError` | P2 disclosure | FIXED: the version is resolved as the artifact's scope may see it (`_visible_version`) |
| F6 | an owner handle behind the generation gets `fact_not_found` from correct/forget/dispute instead of a conflict | P2 | DISPOSITION, unchanged: pre-existing multi-handle semantics (the stale handle has no in-memory view of the memory; before #786 it read `fact_not_found` too); a write that reaches the checkpoint still raises `RuntimeCheckpointConflict`; nothing commits |
| F7 | a refused `remember` left propose/authorize/receipt events on the target id that the other scope's `history()` served | P2 audit disclosure | FIXED: the authorize event of a write-target-refused proposal carries `authority_refs: ["write-target:refused"]` (schema-valid) and the public history projection withholds that correlation; `_canonical_history` keeps it as audit |
| ctx | `recall(query, target_domain_refs=..., project_ref=...)` widens a handle's scope | pre-existing | the same "facade is not an authentication boundary" class as `overrides`; recorded, not changed |

## Owner review of PR #788 (`dd467789`) and the second slice

The owner's source-boundary review verified the 13 declared blobs at `dd467789` and asked
for a reversible runtime slice before any publication decision. Dispositions:

| ask | disposition |
|---|---|
| separate replay-DSL security contracts for #776, #777 and #786, preserving the five v7 contracts | DONE: a separate family, `786-security-replay-dsl/1` (`reference/run_786_security_replays.py`, `reference/fixtures/786-security-replays/`, `scripts/verify_786_security_replays.py`, evidence `reports/validation/786-security-replays/`); the v7 runner, fixtures, evidence and verifier are byte-untouched. Three fixtures, 22 cases, driven through the public facade with preregistered negative controls (`reference/tests/test_786_security_replays.py` proves falsifiability and tamper detection). The expectations were written by the implementing session from the contracts and executed once before freezing (one corrected expectation recorded in `development_history`); they are not independent of the implementer and need an independent read. |
| P2 privacy gate: the cross-project re-creation receipt carried the memory-wide version counter (`before_state v3` while public history read 0) | REMEDIATED, not excepted: versions are **generation-relative**. `GovernedMemoryAdapter.public_state_version` reports `0` for an id whose head was governed-deleted; the facade resolves `state_snapshot` from it; a re-creating write resets the counter, so its receipt reads `v0 -> v1` and the new generation's history counts from 1; `_is_stale` accepts either faithful name of the no-head state (the public `v0` or the retired counter) so adapter-level callers that read the canonical counter keep binding; `public_deleted_version` serves the *latest* readable deletion's recorded version (not the largest), so the owner of a deleted generation still reads the version its own deletion recorded. Tested live and after restart (`test_p2_gate_a_recreated_generation_starts_its_own_version_counter`, replay cases W8, R3, R5, R6). Residual: none of the former generation's count reaches the new generation through proposals, receipts or history. |
| contract 1.8.0 | unchanged in code (`1.7.0`); the recommendation stands and the declaration is regenerated whenever a protected blob moves (`786-v8-successor-proposal.md`) |
| preserve `main`, v7, lanes; new cumulative declaration; fresh evidence and contestant; no activation | held: declaration regenerated at the new head, evidence re-run, register and v7 untouched; the `-v8` Gauntlet contestant stays a post-publication item |
| adversarial review of the final exact head (overrides, shared membership, deleted-generation leakage, scope continuity, multi-handle restart) | run on the final head; findings and dispositions in the PR |

## What remains disclosed, and why

- A refused `promotion` tells the writer that the id is unavailable to it. Under tenant-wide
  ids there is no refusal that cannot be distinguished from a successful creation; the
  alternative (scope-qualified ids) is a canonical keying change outside this slice.
- (Closed by the second slice.) B re-creating A's deleted id used to receive a receipt with
  `before_state` = the memory-wide version counter (`v3`) while its `history()` read `0`;
  versions are now generation-relative (see the owner-review section).
- `cross_tenant_delete` / `cross_tenant_dispute` still name a foreign fact's existence for a
  guessed uuid across adapters sharing one substrate (test-only configuration); pre-existing.

## Outside #786, observed while testing

A handle opening (`AgentMemory.open`, SQLite profile) while another handle publishes a
checkpoint can fail closed with `RuntimeRecoveryError("SQLite canonical substrate digest
mismatch")`: recovery reads the runtime state and the substrate digest outside the checkpoint
lock. It never opens on a torn view and never commits anything; it is a concurrency
availability gap of the recovery path, not an authority gap. Reported in the PR, not fixed here.

## Evidence

See the PR description for the exact SHA, focused and full suite counts, gauntlet, replay and
holdout re-execution, and the independent review log.
