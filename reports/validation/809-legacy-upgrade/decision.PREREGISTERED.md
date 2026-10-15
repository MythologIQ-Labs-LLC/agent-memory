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
| the citing fact's memory binding and the tombstone records (governance witnesses that a reference was governed even where no scope record exists) | yes | governance maps `fact_memory`, `tombstones` (v7 tombstones are pre-#776: no `deleted_fact_uuids`) | yes |
| shared-domain membership **at the time of the citing write** | **no** (for stores that used the membership seam) | only current membership is persisted (`shared_domain_members`); `set_shared_domain_members` is an in-memory seam published by the next governed act. The governed path (`commit_shared_domain_membership_change`) leaves a durable trace in `extension_state["shared_domain_membership_authority"].changes` with receipt ids from the fact-id sequence, from which write-time membership could be reconstructed; audit `events` themselves are not durable in the SQLite profile. The frozen stores used the seam (`extension_state` empty); using the governed trace is deferred (section 6) | — |

So the writer's commit-time context can be reconstructed faithfully for every gate except shared
membership: `writer_context(isolation_domain_refs=scope.domain_refs, actor_id=provenance.actor_id,
project_ref=scope.project_ref, task_ref=scope.task_ref, purpose=scope.purpose)` is exactly what
`_write_scope` derived the record from. Membership is not reconstructed and not assumed.

## 3. Classification of each cited reference `r` of a legacy fact `F` (decided from durable state only)

A **legacy fact** is a fact row without `attributes["canonical_derivation"]`. The upgrade is an explicit governed operation (`upgrade_canonical_derivation`); opening a store never implies it, so an un-upgraded store keeps the legacy rule and shows the oracle (`LegacyOracleDemonstrated`). Content placeholders (`content:sha256:…`, the facade's default evidence reference of a write without `evidence_refs`) are references like any other and classify under rule 1; the cross-scope store therefore has 7 classified edges (two of them the seed facts' placeholders).

1. `r` has no governance witness at all (no `fact_scope` record, no fact row, no `fact_memory` binding, no tombstone naming it) → **unknown_reference** (an external identifier or an id this store never governed): never a dependency. `r` with a witness but no scope record, or a citing fact `F` without a scope record (stores older than `fact_scope`) → **scope_undecidable**: kept bound, quarantined, reported; nothing is dropped without evidence.
2. `r` minted after `F` (id sequence) → **forward_reference**: never binds (owner's non-retroactive ruling; a dependency cannot have carried content that did not exist). Ids not comparable → **order_undecidable** (kept bound, quarantined).
3. The reconstructed context of `F` fails the isolation-domain, required-domain, project or task gate against `fact_scope[r]` → **ineligible_scope**: provably unreadable by the writer under any membership; never a dependency.
4. Every matching isolation domain between `F` and `r` is a governed shared space, judged by the current `shared_domain_members` keys (the runtime never removes a key, so a domain shared now was shared or unknown at write time; a domain shared now but not then is classified undecidable, the conservative side) → the decision depends on write-time membership → **membership_undecidable**: kept bound (deletion completeness preserved), quarantined, reported.
5. Otherwise → **eligible**: bound.

The upgrade rewrites the row's attribute to `canonical_derivation = {policy: "writer-eligible-reconstructed/1", bound: [...], classification: {r: class}}`; `episode_uuids` stay verbatim (nothing is dropped from the row). Facts already carrying a record (new writes) are untouched. The rewrite is a canonical write published as one runtime generation (digest-verified on the next recovery). A store-level record `canonical_derivation_upgrade` (policy, status, counts per class, quarantined facts, runs) is kept in the persisted extension state; `AgentMemory.legacy_upgrade_status()` reads it and reports `fresh` / `legacy_pending` / `legacy_qualified` / `legacy_unqualified`; `AgentMemory.upgrade_canonical_derivation()` performs the upgrade and is idempotent: a repeated run rewrites nothing and reports the store record's totals (`facts_legacy` is the count at the first upgrade, `facts_rewritten` 0). Both operations are public facade operations.

## 4. Decision

- **Provable classes are acted on** (unknown, forward, ineligible → unbound; eligible → bound): each decision cites a durable record; none relies on current membership, on current deletion state, or on content.
- **Undecidable classes are quarantined, not resolved**: kept bound (the conservative side for deletion completeness), listed in the store record, and the store is labelled **`legacy_unqualified`**. Two readings of "explicit governed quarantine" were weighed: (a) keep bound and label (this decision): deletion completeness for legitimate dependencies such as a member's digest is preserved and no non-readability is asserted without evidence, at the cost that an unqualified store, although not activatable, **still serves the quarantined citers' oracle to its own callers**; (c) withhold quarantined citers unconditionally pending a governed act: closes the oracle everywhere at an availability cost and asserts, for every quarantined citer, a withholding its writer may not have deserved. Reading (a) is the preregistered behaviour; reading (c) is presented to the owner as the stricter option and would need its own preregistration. Resolving a quarantined edge needs a governed act by a principal with authority over the shared domain (a future explicit re-derivation mechanism, the owner's ruling), never the upgrade.
- **Activation rule** (for the declaration/profile, the owner's to adopt): Runtime Baseline v8 may be activated over a store only if `legacy_upgrade_status()` reads `fresh` or `legacy_qualified`; `legacy_pending` and `legacy_unqualified` block activation. A fresh-store-only profile is exactly that and is not universal closure.
- **No fabrication**: an edge is marked `eligible` only when every gate passes and the membership gate did not apply (pinned by `NoFabrication` across the three stores); undecidable edges are never marked eligible and never dropped; `fact_scope` is never created or altered by the upgrade.

## 5. Expected outcomes (preregistered; fail-first on `0808cb61`, where the operation does not exist)

| store (v7-origin, frozen) | edges | expected after upgrade | status |
|---|---|---|---|
| `cross-scope`: A owns `a1`/`a2` (each citing only its content placeholder), A's `d1`→`a1`, A's `ctl`→external, B's `bd`→`a1`, `bl`→`a2`, `bu`→guess; A pruned `memory:a` | 7 edges: bd, bl: ineligible_scope (required domain `project:a` absent from B's domains); a1, a2, bu, ctl: unknown_reference; d1: eligible | bd/bl/bu admitted and byte-identical (folded) on recall, history, write semantics; d1 withheld; ctl admitted; idempotent; durable across reopen and a genuine restart | `legacy_qualified` |
| `shared-membership`: O's `s1` in `shared:x` alone; `sm` (member at write), `sc` (stranger at write), `sl` (granted after its write) each cite `s1`; O pruned `memory:s` | sm, sc, sl: membership_undecidable | all three kept bound and quarantined; sm and sl still withheld (deletion completeness preserved; sl's oracle persists and is reported) | `legacy_unqualified` |
| `forward-reference`: A's `fwd` cites the id `late` receives later; `late`→`a1` (deleted) | fwd→late: forward_reference; late→a1: eligible | fwd admitted (was withheld under v7 late binding); late withheld | `legacy_qualified` |
| fresh store written by this runtime | none | no-op | `fresh` |

Expected RED on `0808cb61`: everything but `Fixtures` and `LegacyOracleDemonstrated`.

## 5a. Fixture metadata

`ids.json` and `MANIFEST.json` embed the producer's checkout path (`…/scratchpad/wt-v7/…`) as the `package` field: environment metadata of the producing run, frozen with the fixtures and not read by any test. A later generation should strip it. The store files themselves carry no absolute paths or wall-clock values (review, section 5).

## 6. What this decision does not claim

It does not close the oracle for quarantined edges; it labels the store. It does not reconstruct
membership from governed membership audit events (possible for stores whose membership changes
went through `commit_shared_domain_membership_change`; left for a later revision with its own
preregistration). It does not change the new-write rule, the register, or activation itself.

## 7. Addendum after the independent code review at `0808cb61` (SF-1, L2, L3, SF-4)

- **SF-1** (fixed before any upgrade executes): a checkpoint-migration transformer could add, alter or strip `attributes["canonical_derivation"]` or `write_provenance`; `checkpoint_migration.py` now protects both (`PROTECTED_FACT_ATTRIBUTES`), with a test. The sanctioned legacy upgrade is a governed runtime operation, never a checkpoint transformer, so the protection and the upgrade do not conflict.
- **L2** (accepted residual, resolved by the upgrade for provable edges): a legacy row that cited not-yet-minted sequential ids binds each when minted, through the fallback, and flips on its deletion (a standing canary). Under rule 2 such edges are `forward_reference` and are unbound by the upgrade.
- **L3** (accepted residual, resolved by the upgrade): a new write that legitimately binds a legacy row inherits that row's `episode_uuids` taint transitively, so the residual is per chain. After the upgrade the legacy row carries a record and the chain follows bound edges only; for quarantined edges the inheritance persists and is part of why the store reads `legacy_unqualified`.
- **SF-4**: the Graphiti driver persists no fact attributes; stores on that substrate are outside every #809 claim and outside this decision.
