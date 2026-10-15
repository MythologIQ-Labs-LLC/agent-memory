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
| separate replay-DSL security contracts for #776, #777 and #786, preserving the five v7 contracts | DONE: a separate family, `786-security-replay-dsl/1` (`reference/run_786_security_replays.py`, `reference/fixtures/786-security-replays/`, `scripts/verify_786_security_replays.py`, evidence `reports/validation/786-security-replays/`; required ids declared in the declaration itself under the first-class `security_replay` evidence kind since the owner's PR #805 checkpoint; before it, a companion file carried the refs because the #674 declaration schema enumerated only `public_gauntlet` / `replay` / `lane`); the v7 runner, fixtures, evidence and verifier are byte-untouched. Three `-v1` fixtures (22 cases, frozen at `b70ff58a`, never edited) superseded by three `-v2` fixtures (28 cases) after the second review; driven through the public facade with preregistered negative controls (`reference/tests/test_786_security_replays.py` proves falsifiability and tamper detection). The expectations were written by the implementing session from the contracts before first execution (every corrected expectation and every runtime finding of that first execution is recorded in `development_history`); they are not independent of the implementer and need an independent read. |
| P2 privacy gate: the cross-project re-creation receipt carried the memory-wide version counter (`before_state v3` while public history read 0) | REMEDIATED, not excepted: versions are **generation-relative**. `GovernedMemoryAdapter.public_state_version` reports `0` for an id whose head was governed-deleted; the facade resolves `state_snapshot` from it; a re-creating write resets the counter, so its receipt reads `v0 -> v1` and the new generation's history counts from 1; a governed head deletion records its own version in the tombstone and retires the counter (`_state_version` reset to 0), so the canonical counter and the public version are the same number and `_is_stale` is strict against it (second review F-A/F-B removed the earlier two-name tolerance, which let a snapshot probe the former count); `public_deleted_version` serves the *latest* readable deletion's recorded version (not the largest), so the owner of a deleted generation still reads the version its own deletion recorded. Tested live and after restart (`test_p2_gate_a_recreated_generation_starts_its_own_version_counter`, replay cases W8, R3, R5, R6). Residual: none of the former generation's count reaches the new generation through proposals, receipts or history. |
| contract 1.8.0 | unchanged in code (`1.7.0`); the recommendation stands and the declaration is regenerated whenever a protected blob moves (`786-v8-successor-proposal.md`) |
| preserve `main`, v7, lanes; new cumulative declaration; fresh evidence and contestant; no activation | held: declaration regenerated at the new head, evidence re-run, register and v7 untouched; the `-v8` Gauntlet contestant stays a post-publication item |
| adversarial review of the final exact head (overrides, shared membership, deleted-generation leakage, scope continuity, multi-handle restart) | run on `b70ff58a` by an independent subagent (nine failing probes, six findings F-A..F-F, all remediated) and extended by the first execution of the superseding `-v2` replays (F-G/F-H); the table in the next section |

## Second independent adversarial review of `b70ff58a` and the first execution of the `-v2` replays

An independent subagent reviewed the exact head `b70ff58a` through `AgentMemory.open` and the
adapter boundary with its own probes (nine failed). The first execution of the superseding
`-v2` security replays added two more. Every finding is reproduced as a regression in
`reference/tests/test_786_cross_scope_write_authority.py` (`SecondReviewFindings`,
`ReplayV2Findings`) and fixed in the runtime, not in a refusal string:

| # | finding | severity | disposition |
|---|---|---|---|
| F-A | a refused or parked proposal on a tombstoned id reported the former generation's count in its receipt (`before_state`/`after_state`) | P2 disclosure | FIXED: refused and parked writes report `v0/v0`; a governed head deletion retires the counter, so no later proposal can read it |
| F-B | the module-level `surface.commit` accepted `state_snapshot` values `v1`..`v3` differently on a tombstoned id (the stale verdict named the retired counter) | P2 disclosure (oracle) | FIXED: `_is_stale` is strict against the single public version; every snapshot on a no-head id is judged alike |
| F-C | re-pruning an already deleted head rewrote its tombstone (new `deleted_at`, shrunken lineage) | P1 integrity of the deletion record | FIXED: `already_deleted` for a tombstoned fact or a direct member of a deleted lineage; only pruning -> permanent deletion is a further governed act, and that escalation keeps `deleted_at`, `state_version` and the lineage (the tombstone is reassigned, not mutated, so the durable maps see it) |
| F-D | a former owner's partial deletion (`governed_delete` of its own superseded version) inside a memory whose live head belongs to another scope bumped that generation's version | P1 integrity | FIXED: a deletion in a memory whose live head the writer may not act on reads `fact_not_found` (ordered after the writer's own tombstone, see F-G) |
| F-E | a former owner's dispute of its own fact likewise moved the other scope's live generation | P1 integrity | FIXED: same rule on `_dispute_refusal` |
| F-F | a supersession by an eligible writer could store a head with a wider domain set or fewer required domains than the one it replaced, or drop `project_ref`/`task_ref` (widening a shared or guarded memory) | P1 confidentiality | FIXED: `_scope_continuity_refusal` also refuses widening (`scope_widened`): new domains must be within the old, old required domains within the new, project/task never cleared |
| F-G | (`-v2` replay W7c, first execution) with F-D/F-E in place, the live-head check ran **before** the writer's own tombstone check, so a former owner's re-deletion or dispute of its own deleted generation answered `fact_not_found` once another scope held the live head and `already_deleted` otherwise: an oracle for the re-creation | P2 disclosure | FIXED: the writer's own tombstone and deleted-lineage membership decide first; the live head is consulted only for a fact that is not deleted |
| F-H | the escalation of the owner's own reversible tombstone to a permanent deletion was judged stale against the raw counter (the other scope's generation) and would have reported that counter as `before_state` | P2 disclosure | FIXED: `visible_state_version(proposal)` (0 when the live head is outside the writer's scope, the same `v0` the facade snapshot resolves) is what `_is_stale` and the delete/dispute receipts use; the escalation commits identically with or without a foreign generation and never touches it |

Positive controls were re-run with every finding: the owner's own writes, corrections,
deletions, escalations and disputes commit as before; same-text unrelated memories stay
independent; the other project's generation and its history are byte-identical before and
after every former-owner attempt.

## Third independent adversarial review of the final runtime (`a7a81c45`)

A third independent subagent probed the final runtime through `AgentMemory.open`, the composition
runtime and the adapter (new probes only; 13 probe families, scripts recorded in the review log).
Six findings; five fixed in the runtime with a failing regression first (`ThirdReviewFindings`,
`ProceduralReviewFindings.test_fr3_*`), one recorded for the owner:

| # | finding | severity | disposition |
|---|---|---|---|
| F-R3-1 | scope continuity stopped widening but not **narrowing capture**: the head's scope read as one context admitted a writer through any single route, so a holder of one domain could supersede a multi-holder memory with a narrower scope (a dropped domain, an added required domain), lock every other holder out and occupy the id; shown at the adapter and through the facade (`overrides`) | P1 integrity | FIXED: a supersession keeps the head's scope **exactly** (domains, required domains, project, task); any difference is `scope_widened` or `scope_narrowed`. Re-scoping a shared memory is not a write; the other holders keep their read and their write, and a governed deletion remains the only act that closes a generation (and leaves them a tombstoned view and an open id) |
| F-R3-2 | citing a guessed fact uuid as `evidence_refs` is an oracle for that uuid's deleted-generation membership in *any* scope: a write deriving from a deleted source is withheld (`derived_from_tombstoned_source`), a dispute citing one is scrubbed from the citer's own history, and a canary citing a live foreign uuid vanishes when that uuid is deleted; uuids are sequential | P2 disclosure | RECORDED for the owner, not changed: this is #776/#777's deletion-completeness rule (content derived from a deleted source is withheld tenant-wide, whoever cites it) and the two goals conflict; scoping the taint to the citer's own scope would let a cross-scope derivation of deleted content survive. Mitigations to decide: opaque (non-sequential) fact identifiers, or refusing cross-scope `evidence_refs` at proposal time |
| F-R3-3 | `ConfiguredCompositionRuntime.delete_current` raised `RuntimeRecoveryError` for an id with no current fact but returned `fact_not_found` for a head the writer may not act on, an oracle for a re-creation below the facade | P2 disclosure | FIXED: no current fact is forwarded to the adapter as the empty uuid and refused `fact_not_found` with `v0` states, exactly as a foreign head |
| F-R3-4 | `revoke_skill` returned a refused result carrying the foreign head's `fact_uuid` and `physical_content_retained`, while an unknown skill raised `ValueError` | P2 disclosure | FIXED: a head the caller may not act on raises the unknown-skill `ValueError`; no uuid leaves |
| F-R3-5 | (regression of F5) `_visible_version` built its context without the principal, so a skill bound only to a shared domain read `v0` to its own members and could never be advanced | P2 availability | FIXED: the proposing principal is part of the context; members advance, strangers still read `v0` |
| F-R3-6 | in the opt-in `recall_control="shadow"` mode, `routes_executed` listed `shared_evidence_neighbor` only when a `logical_memory_refs` id had a live head in another scope (candidates and admitted were empty either way) | P2 disclosure (read path) | FIXED: the shared-evidence route is seeded only from heads eligible in the caller's context; never-written, deleted and foreign-live ids now produce the same provenance |
| noted | `isolation_domain_refs` naming another project's domain derives `project_ref` for `revoke_skill`; the module-level `surface.history(adapter, env)` is the unprojected host-level record | pre-existing | same "host-declared scope / host-level API" class as `overrides`; recorded |

Probes that found nothing: torn corrections under PAMA block (with restart); every former-owner
and third-project facade observable with and without a re-creation (only `remember` differs, the
documented disclosure); escalation of an own tombstone under a foreign generation with restart
and with `derived_refs` naming the foreign fact; crafted `state_snapshot` values through every
boundary; stale handles behind the generation; plain `recall(logical_memory_refs=...)`,
`history`, `write_semantics`, `semantic_proposals` for never / live / pruned / permanently
deleted ids; shared-membership declarations; task/project narrowing; 40 shared-member observer
observables.

## What remains disclosed, and why

- A refused `promotion` tells the writer that the id is unavailable to it. Under tenant-wide
  ids there is no refusal that cannot be distinguished from a successful creation; the
  alternative (scope-qualified ids) is a canonical keying change outside this slice.
- (Closed by the second slice.) B re-creating A's deleted id used to receive a receipt with
  `before_state` = the memory-wide version counter (`v3`) while its `history()` read `0`;
  versions are now generation-relative (see the owner-review section).
- A cited fact uuid's membership in a deleted generation of any scope is observable through the citer's own withheld derivation (third review F-R3-2); the owner decides between opaque identifiers, refusing cross-scope evidence refs, or accepting it as the price of tenant-wide deletion completeness.
- `cross_tenant_delete` / `cross_tenant_dispute` still name a foreign fact's existence for a
  guessed uuid across adapters sharing one substrate (test-only configuration); pre-existing.
- Scope is privileged host input (owner checkpoint on PR #805, 2026-10-14). The facade does not
  authenticate the caller of `AgentMemory.open(..., scope)`, of a proposal's `overrides` or of the
  recall scope keywords; it judges the write under the scope the host declares. Replay case W4
  (a complete-scope override is admitted) holds only in that privileged-host model and must not be
  read as end-user isolation: a user who controls the handle controls the declared scope. An exposed
  multi-user service binds authenticated authority to the scope before submitting it.

## Outside #786, observed while testing

A handle opening (`AgentMemory.open`, SQLite profile) while another handle publishes a
checkpoint can fail closed with `RuntimeRecoveryError("SQLite canonical substrate digest
mismatch")`: recovery reads the runtime state and the substrate digest outside the checkpoint
lock. It never opens on a torn view and never commits anything; it is a concurrency
availability gap of the recovery path, not an authority gap. Reported in the PR, not fixed here.

## Evidence

`reports/validation/786-at-head/README.md` names the exact SHA and the commands for the
focused and full suites, the Gauntlet probe, the v7 and security replay re-executions and the
holdouts; `reports/validation/786-security-replays/` holds the frozen security replay
evidence. The PR description carries the same with the independent review logs.
