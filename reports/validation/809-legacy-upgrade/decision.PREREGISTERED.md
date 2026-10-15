# #809 legacy-upgrade threat and migration decision (PREREGISTERED, not executed)

Owner requirement (PR #815 checkpoint review 5527842455): before security acceptance, a separate,
preregistered legacy-upgrade threat and migration decision, demonstrated on a real recoverable
v7-origin store, stating what is available for secure reconstruction, showing no cross-scope
public oracle after upgrade, and preserving (or explicitly quarantining) legitimately derived
deletion dependencies; never dropping legacy edges without evidence, never fabricating historical
read authority; labelling stores `legacy_unqualified` and blocking activation over them when an
upgrade cannot be proven sound. This record and `reference/tests/test_809_legacy_upgrade.py` are
committed before any implementation and executed once on the unmodified head as the fail-first
baseline; an independent reviewer compares them to this record before the first execution on the
changed runtime.

## 1. Threat

A fact persisted before #809 carries no `canonical_derivation` record. `_derivation_refs` then
falls back to every `episode_uuids` entry, so a pre-upgrade citer of another scope's fact keeps
carrying deletion taint from that fact: when the cited generation is deleted, the citer's own
recall, history and write semantics change (withheld, scrubbed, `null`), exactly the F-R3-2
oracle, now limited to legacy rows. The new-write repair does not touch those rows. Demonstrated
(section 5, `LegacyOracleDemonstrated`) on `reference/fixtures/809-legacy-stores/cross-scope`,
written by the published v7 runtime `16a248b1` and opened by the repaired runtime without any
migration step.

## 2. Durable state available for reconstruction (what the v7 runtime actually recorded)

| input | durable? | where | survives purge of the cited fact? |
|---|---|---|---|
| the citing fact's scope record (isolation domains, required domains, project, task, purpose) | yes | governance map `fact_scope`, restored on recovery | n/a (it is the citer's) |
| the citing fact's writer (actor id, purpose, operation channel) | yes | fact attribute `write_provenance` (C1, immutable) | n/a |
| the cited fact's scope record | yes | `fact_scope` (never popped by `governed_delete`) | **yes** |
| the order of minting (citing vs cited) | yes | deterministic ids `ref-NNNN`, one monotonic sequence per store | yes |
| shared-domain membership **at the time of the citing write** | **no** | only current membership is persisted (`shared_domain_members`); `set_shared_domain_members` is an in-memory seam published by the next governed act; the governed membership change path leaves audit events, but the v7 stores in scope used the seam and no v7 store is required to carry such events | — |

So the writer's commit-time context can be reconstructed faithfully for every gate except shared
membership: `writer_context(isolation_domain_refs=scope.domain_refs, actor_id=provenance.actor_id,
project_ref=scope.project_ref, task_ref=scope.task_ref, purpose=scope.purpose)` is exactly what
`_write_scope` derived the record from. Membership is not reconstructed and not assumed.

## 3. Classification of each cited reference `r` of a legacy fact `F` (decided from durable state only)

1. `r` not in `fact_scope` → **unknown_reference** (an external identifier or an id this store never governed): never a dependency.
2. `r` minted after `F` (id sequence) → **forward_reference**: never binds (owner's non-retroactive ruling; a dependency cannot have carried content that did not exist). Ids not comparable → **order_undecidable** (kept bound, quarantined).
3. The reconstructed context of `F` fails the isolation-domain, required-domain, project or task gate against `fact_scope[r]` → **ineligible_scope**: provably unreadable by the writer under any membership; never a dependency.
4. Every matching isolation domain between `F` and `r` is a governed shared space → the decision depends on write-time membership → **membership_undecidable**: kept bound (deletion completeness preserved), quarantined, reported.
5. Otherwise → **eligible**: bound.

The upgrade rewrites the row's attribute to `canonical_derivation = {policy: "writer-eligible-reconstructed/1", bound: [...], classification: {r: class}}`; `episode_uuids` stay verbatim (nothing is dropped from the row). Facts already carrying a record (new writes) are untouched. The rewrite is a canonical write published as one runtime generation (digest-verified on the next recovery). A store-level record `canonical_derivation_upgrade` (policy, status, counts per class, quarantined facts, runs) is kept in the persisted extension state; `AgentMemory.legacy_upgrade_status()` reads it and reports `fresh` / `legacy_pending` / `legacy_qualified` / `legacy_unqualified`; `AgentMemory.upgrade_canonical_derivation()` performs the upgrade and is idempotent.

## 4. Decision

- **Provable classes are acted on** (unknown, forward, ineligible → unbound; eligible → bound): each decision cites a durable record; none relies on current membership, on current deletion state, or on content.
- **Undecidable classes are quarantined, not resolved**: kept bound (the conservative side for deletion completeness), listed in the store record, and the store is labelled **`legacy_unqualified`**. For such a store the F-R3-2 oracle persists for the quarantined citers and is reported as such; the label is the evidence that the upgrade is not proven sound. Resolving a quarantined edge needs a governed act by a principal with authority over the shared domain (a future explicit re-derivation mechanism, the owner's ruling), never the upgrade.
- **Activation rule** (for the declaration/profile, the owner's to adopt): Runtime Baseline v8 may be activated over a store only if `legacy_upgrade_status()` reads `fresh` or `legacy_qualified`; `legacy_pending` and `legacy_unqualified` block activation. A fresh-store-only profile is exactly that and is not universal closure.
- **No fabrication**: an edge is marked `eligible` only when every gate passes and the membership gate did not apply (pinned by `NoFabrication` across the three stores); undecidable edges are never marked eligible and never dropped; `fact_scope` is never created or altered by the upgrade.

## 5. Expected outcomes (preregistered; fail-first on `0808cb61`, where the operation does not exist)

| store (v7-origin, frozen) | edges | expected after upgrade | status |
|---|---|---|---|
| `cross-scope`: A owns `a1`/`a2`, A's `d1`→`a1`, A's `ctl`→external, B's `bd`→`a1`, `bl`→`a2`, `bu`→guess; A pruned `memory:a` | bd, bl: ineligible_scope; bu, ctl: unknown_reference; d1: eligible | bd/bl/bu admitted and byte-identical (folded) on recall, history, write semantics; d1 withheld; ctl admitted; idempotent; durable across reopen and a genuine restart | `legacy_qualified` |
| `shared-membership`: O's `s1` in `shared:x` alone; `sm` (member at write), `sc` (stranger at write), `sl` (granted after its write) each cite `s1`; O pruned `memory:s` | sm, sc, sl: membership_undecidable | all three kept bound and quarantined; sm and sl still withheld (deletion completeness preserved; sl's oracle persists and is reported) | `legacy_unqualified` |
| `forward-reference`: A's `fwd` cites the id `late` receives later; `late`→`a1` (deleted) | fwd→late: forward_reference; late→a1: eligible | fwd admitted (was withheld under v7 late binding); late withheld | `legacy_qualified` |
| fresh store written by this runtime | none | no-op | `fresh` |

Expected RED on `0808cb61`: everything but `Fixtures` and `LegacyOracleDemonstrated`.

## 6. What this decision does not claim

It does not close the oracle for quarantined edges; it labels the store. It does not reconstruct
membership from governed membership audit events (possible for stores whose membership changes
went through `commit_shared_domain_membership_change`; left for a later revision with its own
preregistration). It does not change the new-write rule, the register, or activation itself.
