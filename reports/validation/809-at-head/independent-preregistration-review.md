# Independent pre-execution review of the #809 (F-R3-2) preregistered expectations

**Commit reviewed:** `10a0d70e0941e04e3561f8dcc8c2baf641093c0f` (branch `claude/eager-dirac-bftkfg-809`, parent `28f257c9`).
**Reviewer stance:** independent; read-only. **Nothing was executed**: no pytest, no runtime, no git write command. Every
runtime and contract file was read at `HEAD` through `git show HEAD:<path>`, because at review time the worktree carried
**uncommitted modifications** (see "Worktree state" below). The committed expectations are what is reviewed; the in-flight
implementation is noted only where it bears on a finding and is otherwise not reviewed.

**Files read (all at `10a0d70e` unless stated):**
- `scratchpad/review-809/issue-809.md` (owner direction; items 1-8 and the additional user bullets)
- `reports/validation/805-at-head/f-r3-2-disposition.md`
- `reference/tests/test_809_evidence_reference_authorization.py` (485 lines)
- `reports/validation/809-at-head/preregistration-baseline.log` (170 lines)
- `reference/tests/test_786_cross_scope_write_authority.py` lines 40-125 (`_TwoProjects`), 920-985 (`EvidenceReferenceOracle`), 1130-1145 (`_proposal`), and the commit's diff to it
- `reference/agentmem_ref/runtime/adapter.py` (HEAD): 225-245, 300-330, 470-580, 715-770, 910-945, 1210-1240, 1275-1300, 1365-1470, 1598-1660, 1740-1890, 1890-2000, 1995-2057, 2055-2165, 2190-2240
- `reference/agentmem_ref/api/surface.py` (HEAD): 50-150, 190-215, 445-460, 598-700, 715-726, 898-920, 955-1020, 1030-1130, 1240-1305
- `reference/agentmem_ref/runtime/contextual_recall_adapter.py` 51-110; `runtime/runtime_composition.py` 345-440; `runtime/query_driven_recall.py` 250-280; `runtime/recall_control.py` 1050-1080; `runtime/restart_runtime.py` 395-412; `memory/procedural_memory.py` 548-575; `memory/checkpoint_migration.py` 705-725; `harness/forbidden_hits.py` 238-256; `core/receipts.py` (grep); `core/policy.py` (grep)
- `reference/agentmem_ref/state/sqlite_substrate.py` 717-720, 797-816, 876-905, 982-990; `state/substrate.py` 50-62, 73-96, 393-400, 433-434, 503-530
- `docs/44-public-api-contract.md` HEAD 174-196 and worktree 176-195; `docs/786-cross-scope-write-authority.md` HEAD 150-185 and worktree 145-190
- `reference/tests/test_776_transitive_traversal_review.py` 35-115; `test_776_deletion_decision_properties.py` 1-130; `test_776_adversarial_review.py` 53-135; `test_644_combined_independent.py` 32-44; and grep hits in `test_recall_unknown_scope.py`, `test_governed_paths.py`, `test_candidate_materialization.py`, `test_777_public_projection_review.py`, `test_metabolism_maintenance_integration.py`, `test_procedural_memory.py`
- `git diff HEAD` of the worktree (awareness only)

**Worktree state at review time.** `git status` reported uncommitted modifications to `reference/agentmem_ref/runtime/adapter.py`,
`reference/agentmem_ref/api/surface.py`, `docs/15-memory-threat-model.md`, `docs/44-public-api-contract.md`,
`docs/786-cross-scope-write-authority.md`, `reference/tests/test_776_deletion_decision_properties.py`,
`reference/tests/test_776_transitive_traversal_review.py`, `reference/tests/test_786_security_replay_evidence_kind.py`,
`reference/tests/test_786_security_replays_v3.py`, `scripts/verify_786_security_replays.py` and the PROPOSED v6->v8
declaration; the set grew while this review ran (the implementation agent is working concurrently). The committed baseline
log's header (lines 3-9) states that no runtime file was touched when the baseline ran, and `git show --stat 10a0d70e`
confirms the commit touches no runtime file. The review below therefore holds for the committed expectations; it says
nothing about the uncommitted implementation except where flagged "(worktree, for awareness)".

---

## A. Every test method, with verdict

Verdict key: DERIVED (follows from direction/contract), REASONABLE (not stated by the owner, consistent, worth pinning),
QUESTIONABLE (readable either way; alternative stated), WRONG (contradicts direction/contract). BLOCKING = must change before
the first execution on the changed runtime.

Common harness facts used below: `_Citer.observe` (test 116-134) reads the citer's `recall(logical_memory_refs)`, a
historical recall, `history`, `write_semantics`, and builds four "shapes" through `_shape` (67-75). `_shape` replaces the
citer's own uuid, the cited string and then **the bare case label** (`.replace(label, "<label>")`, line 75) after `_fold`.
`cite` (110-114) names the memory `memory:b-{label}` and the text `... digest {label}`.

### A.1 `FourReferencesIndistinguishable::test_after_pruning_and_after_attested_permanent_deletion` (161-166)
Asserts, for pruning and attested permanent deletion of A's `memory:a`, that B's four citations (A's deleted `a1`, A's live
`a2`, a guess, none) each commit, are admitted once by reference and historically, show exactly the four lifecycle events,
have write semantics, and that the deleted and live-foreign shapes equal the unknown shape on all four channels
(148-159).
- Direction: issue item 2 ("foreign-deleted, foreign-live, unbound and no-ref controls are externally indistinguishable at
  both write and recall, including history and all public projections"), item 1 (both pruning and attested permanent
  deletion), user bullets "deleted foreign / live foreign / unknown / absent; pruning and attested permanent deletion;
  public history, receipts, recall, write semantics ... indistinguishability". Contract: docs/44 HEAD has no clause yet
  (the worktree draft at docs/44:195 states exactly this).
- Verdict on the *intent*: DERIVED.
- Verdict on the *assertion as written*: **WRONG as a harness, BLOCKING.** The bare-label replacement in `_shape` (line 75)
  collides with constant runtime strings, so the deleted-vs-unknown comparison can never succeed on any runtime:
  1. Every public `recall` and `history` result carries `public_projection = {"policy_id":
     "public-deleted-lineage-redaction", "policy_version": "1.0.0", "deleted_lineage": "withheld"}` (surface.py HEAD
     57-61, 1113, 1292). For the `deleted` case `_shape` rewrites these to `"public-<label>-lineage-redaction"` and
     `"<label>_lineage"`; for the `unknown` case they stay. The two strings differ by construction.
  2. The `write_semantics` payload for a digest without a proposition contains the runtime literal `unknown`
     (`"class": "unknown"`, `"proposition_unknown"`, `"status": "unknown"`). The baseline log shows this literally: line 25
     prints the unknown side as `"class": "<label>"`, `["proposition_<label>"]`, `"status": "<label>"` -- the label fold
     has rewritten the runtime's own vocabulary. The deleted side keeps `"unknown"`. They can never be equal.
  3. The `live` label is a substring risk of the same kind (any payload word containing `live`); it has never been
     exercised because the live-vs-unknown comparison sits after the deleted-vs-unknown `assertEqual` inside the same
     `subTest` (156-159) and has therefore never run for `recall`, `history`, `write_semantics` (only the `remember`
     channel reached it on the baseline).
  Consequence: executed on a *correct* repaired runtime these subtests stay RED for a reason unrelated to the oracle, and
  the pressure at that moment would be to "fix the test after execution", which the preregistration discipline forbids.
  This must be corrected and re-baselined before execution (see F, SF-1).
- Also note: the `none` control is deliberately excluded from shape equality (it cannot be byte-equal: its receipt carries
  a `content:sha256` evidence ref instead of a citation, surface.py HEAD 695). It is checked only on
  admitted/events/write_semantics. Acceptable; say so in the docstring.

### A.2 `FourReferencesIndistinguishable::test_the_same_after_an_in_process_reopen` (168-174)
Same assertions after `reopen("project:b")` (handle closed and reopened on the same SQLite root). Direction: user bullet
"same-process reopen". DERIVED in intent; **same harness defect as A.1, BLOCKING** for the same three channels.

### A.3 `FourReferencesIndistinguishable::test_the_same_in_a_genuine_process_restart` (176-188, `_CHILD` 208-223)
Permanent deletion only; a child interpreter opens the root as project B and reports admitted count, event list and
write-semantics presence for the four memories; all must read `{1, FOUR, True}`. Direction: user bullet "genuine process
restart"; item 3 "restart/recovery". DERIVED. Not blocking. Notes: (i) only the negative side (nothing binds) is restarted;
no positive control (own-scope dependency survives a genuine restart and a purge) is exercised in a child process (see B);
(ii) only `permanent=True`; (iii) shapes are not compared in the child, only the three booleans; (iv) the child inserts
`REFERENCE` at `sys.path[0]` (line 210) while the parent resolves `agentmem_ref` through pytest's path -- neither records
`agentmem_ref.__file__`, so a shadowing installed copy would go unnoticed (NOTE, see F).

### A.4 `FourReferencesIndistinguishable::test_a_dispute_citing_a_foreign_deleted_reference_is_indistinguishable_in_the_citers_history` (190-205)
B disputes its own memory citing `a1` (deleted foreign) vs a guess; both commit; `memory.dispute` must appear in B's
history; the dispute result shape and the history shape must be equal between the two cases. Direction: item 2 ("history
and all public projections"), docs/786 HEAD 156 (F-R3-2 row: "a dispute citing one is scrubbed from the citer's own
history"). DERIVED in intent. The mechanism is real: the dispute event carries `payload.evidence_refs` (adapter HEAD
1771) and `history()` drops any event that `_mentions` a withheld id (surface HEAD 1285, 107-122); the baseline log
line 13 shows exactly that (`memory.dispute` absent for the deleted case).
**Harness defect, BLOCKING:** the history shape includes `public_projection` (surface 1292), so with label `deleted` the
`_shape` fold mangles `deleted_lineage` / `public-deleted-lineage-redaction` and `shapes["deleted"] != shapes["unknown"]`
on every runtime (same root cause as A.1). Also the unknown case's history assertion (line 202) has never executed on the
baseline because the deleted case failed first.

### A.5 `CanaryAndReCreation::test_a_canary_citing_a_live_foreign_fact_does_not_vanish_when_that_fact_is_deleted` (227-241)
B cites A's live `a3`; A prunes / permanently deletes it; B's canary stays admitted and its events and all four shapes are
unchanged before/after. Direction: docs/786 HEAD 156 names the canary explicitly; item 2; user bullet "live foreign".
DERIVED. Not blocking (before/after use the same label `canary`, so the label fold is harmless here).

### A.6 `CanaryAndReCreation::test_the_citing_scope_may_re_create_the_deleted_id_and_its_own_derivations_follow_its_own_deletions` (243-256)
B cites deleted foreign `a1`, re-creates `memory:a` (docs/44 HEAD 182: an id with no live head is open to any writer),
cites its own new head, forgets its own generation: the foreign citation stays admitted (1), B's own derivation is withheld
(0), also after reopen. Direction: item 3 "re-creation"; user bullet "deletion followed by another scope's re-creation";
docs/44 HEAD 182. DERIVED. Not blocking. Gap: A's view after B's re-creation/deletion (A's old derivations stay withheld;
A's citation of B's generation never binds) is not asserted here (see B).

### A.7 `CrossScopeChains::test_a_purged_foreign_identifier_binds_nothing` (260-266)
After A's attested permanent deletion the payload of `a1` is gone (`fact(a1) is None`); B citing it is admitted.
Direction: item 2 + user bullet on purged sources (negative side: a purged *foreign* id is an unknown reference).
DERIVED. Not blocking. The positive side (own-scope purged dependency) is A.11/A.12.

### A.8 `CrossScopeChains::test_a_chain_rooted_in_a_foreign_deleted_reference_is_not_tainted` (268-275)
B's three-link chain rooted in deleted foreign `a1` is admitted throughout. Direction: item 3/5 "transitive"; a foreign
root is an unknown reference so nothing to propagate. DERIVED. Not blocking.

### A.9 `OwnScopeDeletionCompleteness::test_direct_and_transitive_derivations_are_withheld_after_pruning_and_after_permanent_deletion` (291-304)
Positive control: A's `d1 -> a1` and `d2 -> d1` are withheld after pruning and after permanent deletion, live and after
reopen; a control citing only an external id stays admitted; after a purge `fact(a1)` is None and `d1, d2` remain withheld.
Direction: item 3 ("direct and transitive references to facts the writer is authorized to read still propagate deletion
taint"), user bullets "physically purged sources ... must not silently discard valid deletion dependencies", "canonical
deletion completeness for legitimate derivations". DERIVED. GREEN on the baseline as declared. Not blocking.

### A.10 `OwnScopeDeletionCompleteness::test_a_derivation_written_after_its_own_source_was_purged_is_still_withheld` (306-315)
Positive control: A cites its own already-purged `a1`; the derivation is withheld live and after reopen. Direction: user
bullet on purged sources; item 3. DERIVED. This is the test that forces the design to keep a purged fact's canonical scope
(`_fact_scope`, which `governed_delete` never pops, adapter HEAD 2151-2153; persisted in the SQLite governance maps,
`sqlite_substrate.py:138`, restored at `restart_runtime.py:402-410`), so that a purged *own* id still binds while a purged
*foreign* id (A.7) does not. Not blocking.

### A.11 `OwnScopeDeletionCompleteness::test_external_evidence_identifiers_are_preserved_as_evidence_and_carry_no_deletion_state` (317-326)
`episode_uuids` of `d1` are exactly `(a1, "evidence:ticket-7")` and of `ctl` `("evidence:ticket-7",)`;
`evidence_neighbors(ctl)` still relates `d1` through the shared external id; after pruning `a1`, `ctl` is admitted.
Direction: user bullet "Preserve genuine external evidence identifiers where the architecture requires them", item 4
"without modifying unrelated evidence refs". DERIVED. Note it pins **verbatim retention of `episode_uuids`** (including the
own fact ref `a1`), i.e. it co-decides the RecordedDerivation design (D). Not blocking.

### A.12 `LateBinding::test_a_reference_that_names_no_fact_at_commit_never_binds_later` (343-354)
Two-pass deterministic-id construction (the construction of `test_776_transitive_traversal_review`): a forward note citing
an id that does not exist at commit stays admitted live and after reopen, even after that id materialises as a fact derived
from a deleted source; the late derivation itself is withheld. Direction: item 4 "evaluate authorizations fail-closed and
before persisting derived references" and "inspect ... late-binding implications of references that become facts later".
Verdict: positive half (late derivation withheld) DERIVED; forward half **QUESTIONABLE** -- see C. It is a defensible,
literal reading of "fail-closed at commit" and of "only provenance references that the writer is entitled to read may
participate" (one cannot be entitled to read what does not exist), but the owner asked to *inspect* late binding, and this
test *decides* it by flipping an existing pinned guarantee. Not blocking on its own, provided the completion evidence states
the trade-off and the owner accepts it explicitly (F, SF-4).

### A.13 `RecordedDerivation::test_the_canonical_derivation_is_recorded_apart_from_the_caller_supplied_evidence` (357-374)
Pins a module attribute `adapter.DERIVATION_KEY`, that `episode_uuids` keep the caller's refs verbatim (own: `(a1,
"evidence:ticket-7")`, foreign: `(a1,)`), and that `fact.attributes[DERIVATION_KEY]["bound"]` is `[a1]` for the own
citation and `[]` for the foreign and unknown citations. Direction: item 4 ("before persisting derived references, without
modifying unrelated evidence refs") plus the user bullet on preserving identifiers while not letting them become
"unauthorized canonical fact dependencies". REASONABLE: the owner did not prescribe a separate recorded set, and the
disposition's option (b) sketched the *opposite* mechanics ("record a provenance link (`episode_uuids`) only for cited
facts the writer is eligible to read", f-r3-2-disposition.md, option (b) row). The committed design is the better reading
of indistinguishability (a filtered `episode_uuids` would itself distinguish a dropped foreign ref from a kept guess at
the substrate), but it freezes an implementation shape (attribute key, `"bound"` list) that the owner has not seen. Not
blocking; state the deviation from the disposition sketch in the completion evidence. Security review of the design in D.

### A.14 `SharedDomainAndRestrictions::test_a_member_binds_a_stranger_does_not` (406-413)
Adapter level (InMemory): a member of `shared:x` citing a shared fact is refused after the fact's deletion; a non-member
citing it is admitted. Direction: item 3 "shared domain membership"; user bullet "shared-domain authorization". DERIVED.
Weakness: `assertIsNotNone(self._refused(...))` accepts *any* refusal; candidates are pre-filtered to domain-eligible facts
(adapter HEAD 1226-1233), so a non-deletion refusal is unlikely but the family should be pinned (F, SF-3). Not blocking.

### A.15 `SharedDomainAndRestrictions::test_revocation_after_binding_keeps_the_dependency` (415-421)
Membership revoked after the digest was written; the deletion of the shared source still withholds the digest.
Direction: item 3 "Include revoked membership"; user bullet "membership revocation", "previously authorized references
whose access changes". DERIVED. GREEN on baseline as declared (unconditional taint). Same `assertIsNotNone` weakness.
Not blocking.

### A.16 `SharedDomainAndRestrictions::test_membership_granted_later_gives_no_retroactive_binding` (423-429)
A non-member's citation does not become a dependency when membership is granted later. Not stated by the owner;
consistent with "evaluate ... before persisting" (item 4) and with the content argument (no content could have flowed at
commit). REASONABLE. Not blocking.

### A.17 `SharedDomainAndRestrictions::test_project_and_task_restrictions_decide_what_binds` (431-444)
A tenant-wide fact restricted to `project:p`/`task:1`: a same-project/task digest is refused after deletion; other-task and
other-project digests are admitted. Direction: item 3 "valid project/task scoping"; user bullet "project/task
restrictions". DERIVED. Not blocking.

### A.18 `SharedDomainAndRestrictions::test_a_foreign_unknown_reference_binds_nothing_at_the_adapter` (446-454)
The F-R3-2 case at the adapter boundary (no facade projection in the way). Direction: item 2. DERIVED. Not blocking.

### A.19 `LegacyFacts::test_a_fact_without_a_recorded_derivation_keeps_its_episode_provenance_as_the_dependency` (460-481)
A governed derivation whose recorded derivation attribute is removed (simulating pre-#809 data) is still refused after its
source's deletion. Direction: user direction "no silent weakening of deletion completeness" (issue "Keep ... deletion
completeness"; item 3). REASONABLE-to-DERIVED. Validity: `InMemoryTemporalGraph.get_fact` returns the stored instance
(substrate.py HEAD 433-434) and `Fact.attributes` is a mutable dict on a frozen dataclass (85-96), so the pop is effective
*if the implementation reads the bound set from the fact's attributes at evaluation time*. If an implementation kept an
adapter-side derivation cache the pop would be ineffective and the test would pass without exercising the fallback.
Not blocking; harden (F, SF-5).

### A.20 (declared alteration) `test_786_cross_scope_write_authority.py::EvidenceReferenceOracle::test_fr3_2_...` (now 963-977)
Body unchanged; `@unittest.expectedFailure` added (commit diff +5 lines). Issue item 1 says "Do not edit the old negative
proof". The decorator *is* an edit of the proof file, though not of its body, and it inverts its role (pass = oracle closed,
"unexpected success" = oracle reopened), which is the useful direction. QUESTIONABLE under the letter of item 1; the
alternative (leave untouched, accept a permanently red test) is worse. Two NOTES: (a) `expectedFailure` masks *any*
failure in the body, including an unrelated setup error (e.g. a broken attested `forget`); the 809 module carries that
coverage, so accept. (b) `expectedFailure` around `subTest` under pytest's unittest bridge plus pytest-subtests has
version-dependent reporting; the baseline shows the "unexpected success" path works (log 135-138, 169), but the
"expected failure inside a subtest" path has not been observed. Verify at first execution that it reports as xfail, not as
SUBFAILED.

---

## B. Gaps against the owner's preregistration list

Covered well: item 1 (both deletion modes: A.1, A.5, A.9); item 2 at write/recall/history/write_semantics for the citing
handle (A.1-A.4, once the harness defect is fixed); item 3 direct/transitive/own scope/shared/project/task/revocation/
re-creation/purge (A.6, A.9-A.11, A.14-A.17); item 4 fail-closed at commit and verbatim refs (A.12, A.13).

Not covered or weak:
1. **Genuine process restart, positive side.** Only B's negative reads run in a child process (A.3), only for permanent
   deletion. No test restarts a process between (a) an own-scope citation and the source's deletion, (b) the deletion and a
   purge, or (c) a shared-domain binding and a revocation, and then checks the dependency survives. In-process `reopen`
   (A.9) does rebuild the adapter from SQLite, which covers durability of `_fact_scope`/tombstones but not process-level
   isolation of caches. Owner bullet "same-process reopen and genuine process restart" is therefore half-covered.
2. **Timing-sensitive status** (issue: "without revealing their existence through a refusal, timing-sensitive status,
   receipt ..."): nothing measures time. `_fold` strips `elapsed_ms` (line 63) rather than comparing it. The disposition
   argued the write path does identical work for every citation; after the repair the write path does *more* work for a
   reference that names a fact (`_fact_scope` lookup + scope gates) than for a guess -- a constant-time concern at the
   adapter. Not measured; should at least be argued in the completion evidence.
3. **State snapshot** (user bullet): B's `state_snapshot` for its own target is unaffected by the cited ref; covered only
   implicitly through receipt equality. Acceptable, but name it.
4. **Semantic admission / `semantic_proposals` / typed claims** (item 5): no test cites a foreign deleted id from a
   memory with a proposition and reads `semantic_proposals`, `current_governed_typed_claim` or the cross-fact currentness
   consumers (`runtime/cross_fact_currentness.py` reads `_fact_scope`, not `episode_uuids`, so probably unaffected --
   unverified).
5. **Provenance audit / `undeclared_residue` / `revoke_skill`** (item 5 "provenance audit"): `undeclared_residue` (adapter
   HEAD 2199-2208) lists every substrate fact whose `episode_uuids` names the tombstoned fact; through
   `ProceduralMemory.revoke_skill` (procedural_memory.py 561-568) and `run_procedural_memory.py:209` it is a host-facing
   projection *to the deleting scope*. No preregistered expectation says whether a foreign citation is residue of A's
   deletion after the repair (see D(i)).
6. **`dispute(fact_uuid=<foreign deleted uuid>)` by uuid** and `write_semantics(<foreign deleted uuid>)` /
   `write_semantics(<guess>)` as *direct* probes of the cited id (not of the citer's own fact) are not compared. Both should
   already read `fact_not_found` / `None` identically (surface HEAD 995-1005; adapter 921-930), but the contract claim "no
   projection serves such an identifier" (worktree docs/44) deserves a pin.
7. **Shared-domain tests are adapter-level and in-memory only**; `set_shared_domain_members` persistence across reopen/
   restart with a bound-then-revoked dependency is not exercised through the facade/SQLite path.
8. **Other scopes' views after re-creation** (A.6 gap): A's citation of B's re-created generation never binds; A's old
   derivations remain withheld after B's re-creation and B's deletion.
9. **Inference-backed consumers** (item 5): the shared-evidence recall route (`evidence_neighbors`, three callers) is
   touched by the design only through candidate generation; `admit_preselected_candidates` drops domain-ineligible facts
   before they become candidates (`contextual_recall_adapter.py` 99-102, #548), so no new oracle; not pinned by a test.
10. **Replay generation** (item 7, "additive replay generation"): outside this module; the worktree shows a DSL/3 runner
    being added (awareness only). The preregistered expectations do not include the replay fixture; the fixture must get
    its own pre-execution review when committed.
11. **Counting claim in the commit message**: "30 failed, 9 passed (the 9 are the positive controls that must hold before
    and after)" is inaccurate; see E.

---

## C. The declared changes to existing tests

**Declared (module docstring 27-35):** (1) `test_776_transitive_traversal_review.py::TransitiveTraversal::
test_decision_does_not_depend_on_query_order` will flip `assertFalse(fresh)` (HEAD line 79) to "the forward note stays
admitted", keeping the memo-stability equality; (2) the from-scratch `oracle()` of `test_776_deletion_decision_properties.py`
(HEAD 21-45) will follow "the fact's bound canonical derivation, not every string in `episode_uuids`".

**Is "a forward citation of an id that does not exist at commit time never binds" the right reading of item 4?**
Reading for it: item 4 says "evaluate authorizations fail-closed and before persisting derived references". A reference to
a not-yet-existing fact cannot be authorized at commit (there is no scope to judge, `_domain_identity_refusal` returns
`unknown_scope`, adapter HEAD 1608-1615); fail-closed means it does not bind; "before persisting" means the decision is
fixed at commit. The issue also frames the defect as the writer "encod[ing] foreign lineage it never had authority to
see" -- an id that does not exist is the limiting case of a reference the writer could not read. Under this reading the
test and the declared flip are DERIVED.

**Strongest argument against:** the query-order test did not exist by accident. It pins a #776 guarantee: "a fact whose
provenance becomes tainted WITHOUT a new deletion (a later write deriving from an already-deleted version) must be refused"
(HEAD 69-72), and the adapter's `_derives_from_deleted` memo key carries explicit machinery for it (HEAD 1961-1965).
With sequential, predictable ids a writer in its *own* scope can pre-cite the next id, then write the content under that id,
then delete it; the forward note escapes deletion completeness. "Fail-closed" for *authorization* is "fail-open" for
*deletion completeness*, and the owner's governing constraint is "no silent weakening of deletion completeness". A design
that keeps late binding is available and is arguably the *smaller* behavioural change: bind at materialisation time under
the writer's commit-time context (the fact's own recorded scope + actor from `WRITE_PROVENANCE_KEY` reconstruct it), which
closes F-R3-2 equally (binding still requires eligibility) while preserving the existing guarantee and the existing test.
Its cost is the retained memo-staleness machinery and a stored evaluation context.

**Assessment:** the counter-argument is real but bounded: provenance is caller-declared, and `test_unknown_provenance_is_not_deletion` (HEAD 40-45) already establishes that a writer who cites nothing escapes the rule, so pre-citation
gives the writer no power it did not have by omission. The chosen reading is therefore a legitimate disposition of item
4's "inspect late-binding implications", not a violation of it. It should **not block** execution, on two conditions:
(a) the completion evidence names the flipped guarantee explicitly as a behavioural change the owner accepts (the worktree
docs/786 draft lists it under "What remains disclosed" (2), which is the right place); (b) the owner's item 7 spirit
("rather than rewriting old expectations") is honoured by keeping the old assertion visible in the test's comment or by
keeping a dated note in docs/776 evidence, rather than silently inverting it.

**The property oracle (declared change 2):** the declared replacement reads the runtime's own recorded bound set
(worktree: `_dependencies(fact)` returns `attributes["canonical_derivation"]["bound"]`). That makes the "independent
from-scratch oracle" dependent on the very function under test (`_bound_derivation`): a defect that binds a foreign or a
forward reference would be mirrored by the oracle and the property would still pass. This is a weakening of an existing
independence property and should be fixed before that test is executed on the changed runtime: compute the bound set
independently from substrate-level facts -- refs that (i) name a fact whose uuid is in `adapter._fact_scope` (survives
purge), (ii) were minted before the citing fact (deterministic ids are one monotonic sequence, `DeterministicIds.next`,
substrate.py 57-59), and (iii) are scope-eligible for the citing fact's own recorded scope (in the property test every write
shares one scope, so (iii) is trivially true, but write it). See F, SF-6. Not blocking for the 809 module itself.

---

## D. Security review of the implied design

Design as pinned by A.11 and A.13: `Fact.episode_uuids` keeps the caller's refs verbatim; a canonical derivation set
(`attributes[DERIVATION_KEY]["bound"]`) is decided once at commit under the writer context and is the only thing deletion
taint follows; a fact without the attribute falls back to `episode_uuids`.

**(i) Does keeping verbatim refs in `episode_uuids` leave a route that distinguishes a foreign-deleted citation from a
guess?** Enumerated readers of `episode_uuids` at HEAD (`git grep`): adapter 744 (write), 928 (`_semantics_visible`),
1384 (`_admission_refusal`), 1949/1988 (`_deleted_lineage_reason`/`_derives_from_deleted`), 2208 (`undeclared_residue`);
substrate `evidence_neighbors` (sqlite 876-899, in-memory 503-530); `checkpoint_migration.py:716` (protects the field as
immutable). Findings:
- Adapter 928 and 1384 are **separate** `episode_uuids` tombstone checks that run *before* `_deleted_lineage_reason` and
  before the scope gate (1384 returns `derived_from_tombstoned_source` ahead of `_domain_eligibility_refusal`, whereas the
  lineage branch at 1400-1401 returns the scope refusal first). The repair must redirect both to the bound set, not only
  `_deleted_lineage_reason`; A.1/A.14-A.18 would catch an omission (the baseline failures at log 127-134 come from 1384),
  and A.1's `write_semantics` channel would catch 928 once the harness is fixed. Covered.
- `evidence_neighbors` relates facts by shared `episode_uuids`. The route is seeded only from heads eligible in the
  caller's context (F-R3-6 fix, docs/786 HEAD 160) and `admit_preselected_candidates` drops domain-ineligible neighbours
  before candidacy (99-102). The visible `shared_evidence_refs` in `route_provenance` are intersections of two eligible
  facts' refs, i.e. strings the reader's own scope wrote. No new distinguishing route. Not pinned by a test (B.9).
- Receipts carry `basis.evidence_refs` verbatim (receipts.py 355, 418) and are not scrubbed (`_commit_result`, surface
  715-725): identical for all four cases by construction. Covered by the `remember` channel (already GREEN on baseline).
- History: commit/receipt events carry no evidence refs (adapter 535-573); only the dispute event (1771) and the
  replacement record (1424, consumed by `rejected_values`) do. These are the scrub routes; see (iii).
- `undeclared_residue` (2199-2208): at HEAD a foreign citation of A's deleted uuid is reported *to A* (through
  `revoke_skill` -> `RevocationResult.undeclared_residue`) as a remnant uuid. That is a pre-existing reverse-direction
  disclosure (A learns a fact uuid in another scope cites its fact), not F-R3-2. If the repair makes residue follow the
  bound set (worktree: yes), that disclosure closes and the verbatim string in B's row is left as an unreported remnant --
  defensible (it is B's own input, inert to B after the repair) but it is a change in what A's revocation audit reports and
  is **not preregistered** (B.5). Pin it either way.
- Conclusion (i): with 928/1384/1949/2208 all reading the bound set, no public projection or substrate route distinguishes
  the cases. The one route I could not close by reading is timing (B.2).

**(ii) Legacy fallback.** A fact without the attribute keeps `episode_uuids` as its dependency set. Consequence: for every
fact persisted before the repair the F-R3-2 channel persists exactly as before (a pre-repair B memory citing A's uuid is
withheld from B when A's generation is or becomes deleted). This does not *reopen* the oracle for *new* writes (a new write
always records the attribute), but it preserves it for old rows, and it cannot be fixed by a later deletion (the withheld
state tracks A's deletions forever). Under "no silent weakening of deletion completeness" the fallback is the right
default; under "close the oracle" it is a documented residual that must be stated as such (the worktree docs/786 draft
does, item (1) of "What remains disclosed"), together with the harness facts that most existing tests write derived facts
*directly into the substrate* without the attribute (test_recall_unknown_scope 112-113, test_governed_paths 224-229,
forbidden_hits.py 241-251) and therefore keep exercising the legacy path -- which is good for regression coverage of the
fallback but means those suites do not test the new rule. Acceptable. One hardening: a migration or audit tool should be
able to *report* legacy rows with cross-scope refs (not rewrite them) so the residual is measurable; out of scope here.

**(iii) Making `public_identifier_withheld` reader-aware.** At HEAD the predicate is tenant-wide (adapter 1822-1835); the
dispute test (A.4) and the history channel (A.1) require it to stop withholding, from B, an identifier B supplied itself.
Can an out-of-scope reader obtain a deleted-generation identifier from a projection other than its own input? **Yes, in
one path:** the history of a *shared* memory held by A and B (`shared:x`), when A disputes it citing a private deleted
`a1`: the dispute event's `payload.evidence_refs` (adapter 1771) reaches B's `history()` of that memory. Under the HEAD
predicate the whole event is dropped from B's view the moment `a1` is deleted (while it was shown when `a1` was live) --
which is itself an F-R3-2-class canary channel over *A's* citations, so the reader-aware predicate improves it. Under the
reader-aware predicate B is served the string `a1`. Is that a disclosure? After the repair the string is inert to B: citing
it is unknown (A.1), `dispute(fact_uuid=a1)` is `fact_not_found` (surface 995-1005 via `fact_eligible_in_context` with the
retained `_fact_scope`), `write_semantics(a1)` is `None` (adapter 921-930, scope gate), `recall` cannot address it. What B
learns is "A cited ref-N", which B learned identically for a live private ref before and after. So the reader-aware scrub
is **safe provided every B-facing route treats `a1` exactly as a guess** -- which is the whole of this repair -- and the
contract sentence in the worktree docs/44 ("No projection of this runtime serves such an identifier to that reader") is
**overstated**: a co-holder's dispute evidence in shared history does serve it. Recommend wording: "no projection serves
such an identifier *as anything other than an opaque string the reader cannot act on*", and add a pin (B.6). Second
condition: the reader-aware predicate must use the *reader's* context, never the citer's; `_withheld_predicate` is built
per call from `_handle_recall_context()` / the validated recall envelope (surface 905-916, 1073-1075), which is the
reader. Third: `public_memory_withheld` (1836-1840) made reader-aware must not flip a co-holder's `tombstoned` view
(`public_deleted_version` already scopes head deletions to readers who could read the head, 1878-1897) -- consistent.

---

## E. Harness validity and the baseline log

- **Declared RED/GREEN sets vs the log.** Docstring (17-25) declares RED: FourReferences (4), Canary (2), CrossScope
  (2), LateBinding, RecordedDerivation, SharedDomain (4 of 5); GREEN: OwnScope (3), revocation, LegacyFacts. Log lines
  140-168 list exactly those 19 module tests as FAILED/SUBFAILED and nothing else; the five GREEN tests have no entry.
  Line 169 is the oracle's "unexpected success". Match: **exact**.
- **Counts.** Progress line (11): 11 `F`, 9 `.`, 20 tests. "30 failed" = 11 test-level FAILED + 19 SUBFAILED; "9 passed"
  = 9 test *bodies* whose own frame passed, which includes the four oracle tests whose failures were reported at subtest
  level (`test_after_pruning`, `..._reopen`, `..._restart`, canary). The docstring's "29 failed, 9 passed" is the module-only
  count (30 minus the oracle). The commit message's gloss "the 9 are the positive controls" is **wrong**: the positive
  controls are 5 tests (plus the 23 passing subtests, which include the live/unknown/none sides and the `remember`
  channel). Correct the wording in the completion evidence; no test change needed.
- **Can an expected-RED test pass on the unmodified tree trivially?** No: each RED test failed on its core oracle
  assertion (log 15-134), not on setup. `RecordedDerivation` failed on its first line (`DERIVATION_KEY` absent, 125-126),
  so its remaining assertions (367-374) have never executed and are unvalidated as harness code.
- **Can a positive control pass vacuously?** `_refused` asserts candidate presence (398), so the SharedDomain positives
  are not vacuous. `LegacyFacts` is non-vacuous on the InMemory substrate for the reason in A.19, conditional on the
  implementation reading the attribute at evaluation time. OwnScope controls are real (log shows them GREEN while their
  RED neighbours fail on the same harness).
- **`evidence_neighbors` availability:** A.11 calls it on the SQLite substrate behind the facade; it exists (sqlite 876).
- **Child process import path:** A.3 inserts `reference/` at `sys.path[0]`; non-vacuous (an import failure raises via
  `check=True`), but which `agentmem_ref` the *parent* imported is not recorded (NOTE).
- **The blocking defect** (A.1, A.2, A.4): the deleted-vs-unknown and live-vs-unknown shape equalities for `recall`,
  `history` and `write_semantics` are unsatisfiable because `_shape` folds the bare label and the payloads contain the
  literals `deleted` (`public_projection`) and `unknown` (write-semantics vocabulary). The baseline log proves the second
  collision directly (line 25). Because the deleted comparison fails first inside each `subTest`, the live comparison has
  never run. These three tests cannot turn GREEN on any runtime as written.
- **Minor:** `_fold` (58-64) folds `ref-\d+`, ISO `Z` timestamps, `facade:` and `content:sha256:` hashes and
  `elapsed_ms`; it does not fold `recovery:<memory>:<vN>` rollback refs or proposal ids of other shapes, but those are
  equal across cases anyway (same memory-id pattern, folded via `<label>`). Timestamps are evidently deterministic or
  folded, since the `remember` channel compared equal on the baseline.

---

## F. Overall verdict and SHOULD FIX list

**Verdict: NO -- not as committed.** The implementation agent may **not** execute `FourReferencesIndistinguishable::
test_after_pruning_and_after_attested_permanent_deletion`, `::test_the_same_after_an_in_process_reopen` and
`::test_a_dispute_citing_a_foreign_deleted_reference_is_indistinguishable_in_the_citers_history` on the changed runtime as
they stand: their shape equalities are unsatisfiable by construction (SF-1), so an execution would produce RED results that
mean nothing and invite a post-execution edit. Every other test in the module may be executed as committed (with NOTE
items). The three defective tests must be corrected, the baseline re-run on the unmodified tree (`28f257c9` content, i.e.
runtime at `10a0d70e`), both committed, and the correction re-reviewed (a one-line mechanical change; the re-review can be
short) before their first execution on the changed runtime.

### SHOULD FIX (SF-1 is the blocking item)

- **SF-1 (BLOCKING)** `test_809_evidence_reference_authorization.py::_shape`, line 75. Replace the bare-label fold with
  exact-token folds so runtime vocabulary is never rewritten:
  `text = text.replace(f"memory:b-{label}", "memory:b-<label>").replace(f"memory:d-{label}", "memory:d-<label>").replace(f"digest {label}", "digest <label>")`
  (keep the `self_uuid` and `ref` replacements). Alternatively pass the memory id and query into `_shape` and fold those.
  Then re-run the baseline on the unmodified tree and commit the new log beside the old one (do not overwrite
  `preregistration-baseline.log`; add `preregistration-baseline-2.log` and reference both in the docstring). Expect the
  same RED/GREEN sets; the `write_semantics` channel will then show the real baseline difference (`null` vs document).
- **SF-2** `_assert_indistinguishable` (156-159): put the deleted-vs-unknown and live-vs-unknown `assertEqual`s in
  *separate* `subTest`s (`subTest(channel=..., case="deleted")` / `case="live_foreign"`) so a failure of one does not hide
  the other; same for A.4 (split the two shapes into two assertions).
- **SF-3** `SharedDomainAndRestrictions::_refused` callers (411, 420, 442) and `LegacyFacts` (480): replace
  `assertIsNotNone(...)` with `assertIn(..., {"derived_from_tombstoned_source", "derived_from_deleted_logical_memory"})`
  so the positive controls pin the deletion family, not "any refusal".
- **SF-4** `LateBinding` docstring (344-347) and the declared flip of `test_776_transitive_traversal_review.py:79`:
  record in the test comment the guarantee being withdrawn ("a forward citation that materialises later no longer binds")
  and cite the owner's acceptance; the completion evidence must present this as a behavioural change for the owner's
  explicit sign-off (item 4 "inspect"), not as a consequence of the repair.
- **SF-5** `LegacyFacts` (474-476): after the pop, `self.assertNotIn(key, fact.attributes or {})`, and reset every
  adapter-side memo the implementation introduces (at HEAD only `_derived_taint_memo` exists; if the implementation adds
  a derivation cache, clear it here too or the test is vacuous). Add the same scenario on the SQLite path by writing a
  legacy row (attribute removed through the substrate) and reopening, so the fallback is proven on durable data.
- **SF-6** Declared property-oracle change (`test_776_deletion_decision_properties.py::oracle`): do not read
  `attributes["canonical_derivation"]`; compute the dependency set independently as `{r for r in episode_uuids if r in
  adapter._fact_scope and seq(r) < seq(uuid)}` (+ scope eligibility of the citing fact's own recorded scope), so the oracle
  still checks `_bound_derivation`, not only the traversal.
- **SF-7** Add preregistered positives for the uncovered items in B before execution, each small: (a) child-process
  restart after an own-scope citation then source purge -> still withheld (B.1); (b) `dispute(target, fact_uuid=a1)`,
  `write_semantics(a1)` vs the guess from B -> byte-equal results (B.6); (c) `undeclared_residue(a1)` after B's foreign
  citation -> decide and pin (B.5); (d) A's view after B's re-creation (B.8); (e) a facade/SQLite shared-domain
  bind-then-revoke-then-reopen case (B.7).
- **SF-8** Completion-evidence wording: correct "the 9 are the positive controls" (E); state the deviation of the
  recorded-derivation design from the disposition's option (b) sketch (A.13); add the timing argument or measurement (B.2);
  soften the docs/44 draft sentence "No projection of this runtime serves such an identifier to that reader" (D(iii)).

### NOTE items (non-blocking)
- N-1 `@unittest.expectedFailure` on the pre-repair proof is an edit of the proof file under item 1's letter; acceptable,
  say so explicitly; verify the expectedFailure-inside-subTest reporting under the pinned pytest-subtests at first run.
- N-2 Record `agentmem_ref.__file__` in both parent and child of A.3 (or assert they share the `reference/` root).
- N-3 `RecordedDerivation` lines 367-374 have never executed; a harness error there on first execution is not a finding
  about the runtime.
- N-4 The worktree already contains an uncommitted implementation, docs edits, edits to the two declared 776 tests and to
  the -v3 replay verifier/tests. None of that is covered by this review; the replay fixture for the new generation and the
  changed verifier need their own pre-execution review (item 7), and the -v3 verifier changes must be shown not to alter
  what the frozen -v3 evidence verifies against.
