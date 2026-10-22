# #691 post-v7 consumer context tranche: validation and qualification record

Branch `integration/post-v7-context-preview-no-ci`, descended from the frozen cumulative v7 candidate
`72d6a9036437edefbc6efe9962cfceba18cb1d16` (PR #836). Evidence in this folder was produced at the heads
named below, in this cloud container (CPython 3.12.3, `reference/requirements.txt` in a venv, 4 vCPU),
with no GitHub Actions, no model inference and no credential.

| Head | Content |
|---|---|
| `2444ed31` | the owner's staged integration (nine files; `recall_context`, provenance minimisation, schema, tests, demo) |
| `dfdfffc6` | + `reference/tests/test_691_authorization_privacy_challenge.py` (Phase 2, 13 tests) |
| `d5563d63` | + content-delivery audit receipt (`memory.context_delivery`) with schema addition and 8 tests (Phase 3) |
| `4e4c7d66` | review 5609515530 (A/B): receipt appended only after the final package validates; refusal without a recall event; the owner's three controls carried byte-identical (§9) |
| `024d9af3` | review B completed: the cited recall event must agree on principal, scope and admission outcomes; `FailClosed` matrix (§9.3) |
| `d489ac19` | schema: `audit.recall_event_id` required, non-empty string. **Protected runtime tree `83f0ff99…` from here on** |
| `8964d6fd` | test-only: DoD-20 classification of the public exception type; evidence of §9 |

**This tranche edits protected runtime source after the v7 declaration and does not amend that
declaration.** `check_runtime_baseline_equivalence.py --candidate HEAD` exits 1 by design
(`logs/checker-d5563d63.txt`, `review-839/checker-d489ac19.txt`): two undeclared protected files
(`api/context_package.py`, `context_package.py`) and two declared blobs moved (`api/surface.py`,
`runtime/adapter.py`). Passing the v7-era tests therefore qualifies nothing by itself; the successor
requirements are listed in §7 (blobs updated in §9.7).

Sections 1–8 describe the heads up to `d5563d63`; **§9 records the remediation of the independent review
(PR #839 review 5609515530) at `4e4c7d66`–`8964d6fd`** and supersedes §3 and §6 where it says so.

## 1. Phase 1: the staged integration, tested as written

| Check | Result | Record |
|---|---|---|
| ancestry | `2444ed31` is one commit on `72d6a903`; nine files, +1160/-6; protected tree `f9b5ff9e` → `109211eb` | `git log`, `git diff --stat` |
| `recall()` unchanged | `AgentMemory.recall` AST-identical to `72d6a903`; `_recall_document_and_context` body identical to the former `_recall_document` except the final `return` now also yields the context (19 statements, 1 differs) | AST comparison in this record's session log |
| `test_context_package.py` + `test_691_cross_actor_provenance_review.py`, unmodified | **22 passed** | `logs/phase1-staged-tests-2444ed31.txt` |
| security, facade, runtime, deletion, restart, recovery, temporal, provenance suites (`-k` selection) | **635 passed**, 3 skipped, 1 xfail, 480 subtests | `logs/phase1-broad-suites-2444ed31.txt` |

Verified behaviours (1–9 of the assignment): content is resolved only for the recall's `returned` list
(`test_content_is_resolved_only_for_returned_facts`); each fact is re-checked against admission in the
recall's mode and against the #777 withholding predicate inside the same hold of the runtime-owned
serialization lock (`resolve()` in `recall_context`; `test_concurrent_correct_and_forget_never_leak_stale_content`);
deleted, superseded, other-project and other-tenant content cannot escape (`Authority`, `Workflow`,
`DeletedContentNeverReappears`); character, item and token budgets bind (`Budgets`, `test_default_item_cap`);
memory text is `untrusted_memory_text` with `authority_effect: none` and an instruction policy
(`Integrity`, `InstructionsInMemoryGrantNothing`); provenance carries `content_sha256`, `content_chars`,
`currentness`, admission decision and mode, write channel and clocks (`ReviewRegressions`); schema and
exports work from the source checkout and from an installed wheel and sdist (§5); correction, forgetting,
historical recall and restart behave as before (`Workflow`, broad suites, crash matrix §4).

## 2. Phase 2: authorization and privacy challenge (`reference/tests/test_691_authorization_privacy_challenge.py`)

Run as written against `2444ed31` first: **13 passed** (`logs/phase2-challenge-as-written-2444ed31.txt`).
The staged provenance minimisation already satisfies every scenario; no assertion was weakened.

| Scenario | Outcome |
|---|---|
| writer retrieves own content and provenance | content, `memory_ref`, writer-declared `source_ref`, digest, channel |
| same-project colleague | content, digest, currentness and channel; **no** `memory_ref`, `source_ref` or writer actor id anywhere in the package, also when the colleague names the logical reference via `logical_memory_refs` |
| other project | nothing, under current, historical and logical-reference recall |
| other tenant | cannot open the store (`RuntimeRecoveryError`) |
| missing writer provenance (legacy fact) / malformed provenance | private default even for the declared writer: no lineage or source reference, no channel |
| deleted memory | never reappears through current, historical or logical-reference recall, `history()` (tombstoned, no content), a correction of the deleted reference (refused), restart, another actor, or a re-created id |
| caller overrides | `project_ref`, `target_domain_refs`, `principal_ref`, `purpose`, `task_ref`, `budget`, `consumer_profile`, `public` are refused with `TypeError` before any recall is recorded |
| remembered instructions | delivered verbatim as untrusted data with their own digest; provenance and policy unchanged |
| spoofed `actor_id` | a second handle opened with the writer's actor string receives the writer's provenance; asserted as a documented limitation |

**Boundary determination.** The implementation preserves the distinction between content eligibility
(admission under the handle's tenant/scope, re-checked at resolution) and provenance visibility (writer
identifiers only when the fact's immutable `write_provenance.actor_id` equals the handle's declared
actor). It is a disclosure-minimising projection, not an authorization check: `AgentMemory.open(actor_id=…)`
is host-declared. **Host requirements before multi-user delivery:** the consuming host must (a) bind
`actor_id`, `tenant` and `scope` to an authenticated principal and never let an untrusted client choose
them; (b) open one handle per authenticated actor; (c) treat delivered content as untrusted data in its
own prompt assembly; (d) keep the store's filesystem private to the host process. These are stated in
the facade docstring and in the audit payload (`actor_binding: host_declared`).

## 3. Phase 3: content-delivery audit receipt (implemented at `d5563d63`)

A `memory.recall` event proves identifiers were recalled; it did not prove text was delivered.
`recall_context` now records one `memory.context_delivery` audit event per call
(`memory-audit-event.schema.json`, `component: public-facade`, `event_version 1.0.0`):

- **published through the runtime's transactional read seam** (`durable_runtime.run_governed_read`), the
  same mechanism that makes recall events durable, as its own SQLite generation; identifier state advances
  inside that generation (`GovernedMemoryAdapter.allocate_event_id`, read-only otherwise);
- **bound** to the recall by `correlation_id` (the recall event's correlation) and `causation_id` (its event
  id): the first `memory.recall` event appended for this principal after the call began, so a shadow
  recall-control pass is never the basis; and to the admission decisions by `payload.recall_decision_ids`;
- **records per returned identifier** `resolved`/`truncated` with `content_sha256` and `delivered_chars`,
  or `omitted_budget`/`unresolved`/`unsupported` with the reason token the caller saw; package status,
  state counts, budget and a `package_sha256`; principal and scope as in the recall event, plus
  `actor_binding: host_declared`;
- **never carries memory text** and names only identifiers the recall already returned to this caller
  (deleted-lineage identifiers are projected away before `returned` is formed);
- **fails closed**: if the receipt cannot be recorded the call raises and no content is delivered; a
  failure inside the seam rolls the receipt back with its generation; the lock is released and the
  store stays usable; **since `4e4c7d66` (§9.2) the receipt is appended only after the complete package,
  audit block included, has validated, and never without the recall event it cites**;
- **not a second authority**: it lives in the adapter's existing `events` log, under the existing
  schema and persistence, and is not projected by `history()` (which is memory-scoped);
- the package carries an optional `audit` block (`delivery_event_id`, `recall_event_id`,
  `correlation_id`), an **additive, optional schema change**; packages without it remain valid and the
  candidate identity stays `agent-memory-context/0.1.0`. Whether that addition is acceptable within
  0.1.0 or warrants 0.2.0 is an owner call (§7).

Tests: `reference/tests/test_691_context_delivery_audit.py`, 8 tests, run with the staged and challenge
suites: **43 passed** (`logs/phase3-audit-and-691-suites-d5563d63.txt`). Durability across restart,
empty/truncated/exhausted/unresolved packages, deleted-lineage non-disclosure, refused calls recording
nothing, unrecordable receipt delivering nothing, and in-seam rollback are covered.

## 4. Phases 4–5: hardening and regression at `d5563d63`

No genuine defect was found in the staged code; the only source changes are the audit receipt (§3).
The rejected `consumer_profile="lexical_content"` experiment is not present (refused as an unknown
keyword, `test_scope_and_identity_overrides_are_refused_before_any_recall`).

| Gate | Result | Record |
|---|---|---|
| full reference suite (CPython 3.12.3) | **3197 passed, 5 failed**, 27 skipped, 1 xfail, 2186 subtests. The five: one thread-race test that passes 3/3 in isolation (load during the run), and four freeze/pin guards that fail by design on a tree whose protected runtime differs from the v7 pin (two #770 replay-freshness guards, the #644 Gauntlet identity guard, the baseline-equivalence contract test) | `logs/full-suite-d5563d63.txt`, `logs/full-suite-d5563d63.failure-classification.txt` |
| 13 replay families re-executed on this head (786 v2/v3, #809, #835 DSL/4, five #644) | all PASS; `observations_sha256` **identical** to the `2ad4cf23` v7 record for all 13; `verify_786_security_replays.py --reexecute --declaration …` 5/5 VERIFIED, `verify_644_v7_replays.py` 5/5 VERIFIED, `evidence_verified: true` | `replays/` |
| #821 crash-window matrix (9 kill points) | outcome-identical to the v7 record | `logs/crash-window-d5563d63.*` |
| validators | schemas (75), fixtures (64), architecture index (84), doctrine boundaries, wiki links: OK; `git diff --check` clean on the tranche's files | `logs/validator-*.txt` |
| AMB PrecisionMemBench agent-memory row (77 cases, retrieval-only, frozen harness), executed at `dfdfffc6` | **77/77 L1-equal to accepted v6**; cross-fact sidecar 73 records; checker state recorded as FAIL (by design, not lane evidence, not imported) | `parity/compare-amb-agent-memory-dfdfffc6.json`, `parity/amb-agent-memory-dfdfffc6.*` |
| LongMemEval_S agent_memory rows (500/500 questions, session and turn, frozen dataset `d6f21ea9…`, top-50), executed at `d5563d63` | **500/500 equal to accepted v6** on both planes (ranked_top, metrics, cross-fact records; aggregates equal; no lost required evidence); checker state recorded as FAIL (by design, not lane evidence, not imported) | `parity/compare-lme-agent_memory-{session,turn}-d5563d63.json`, `parity/lme-agent_memory-*-d5563d63.*` |

Public recall output parity against the unchanged v7 base is therefore exact on every executed row (AMB 77/77, LongMemEval 1000/1000), as expected from an AST-identical `recall()`.

## 5. Installed package and consumer demonstration (`install/`)

Built from `git archive HEAD` at `d5563d63` with `python -m build` (setuptools): wheel
`agent_memory_reference-0.2.0-py3-none-any.whl` sha256 `4ba7fa7b…`, sdist
`agent_memory_reference-0.2.0.tar.gz` sha256 `61e9fe2f…` (`install/dist-sha256-d5563d63.txt`). Each
installed into a fresh CPython 3.12 venv; from a directory outside the checkout with `python -I`:
`agentmem_ref` imports from site-packages, `agentmem_ref.api.context_package` and the compatibility alias
resolve, the packaged `api-context-package.schema.json` is present, a remember → `recall_context` round
trip validates against the packaged schema with the audit block and records a `memory.context_delivery`
event (`install/install-smoke-d5563d63.txt`).

`scripts/demo_context_package.py` (open → remember → recall_context → correct → recall_context →
injected "SYSTEM:" text delivered as untrusted evidence → forget → close → reopen → recall_context →
other-project read): **ALL CHECKS PASSED** against the installed wheel and from the source checkout
(`install/demo-installed-wheel-d5563d63.json`, `install/demo-source-checkout-d5563d63.json`).

## 6. Security findings and residual risks

- **No way found to obtain text that `recall()` would not return to the same handle**, nor a writer's
  identifiers from another handle, nor deleted content through any lifecycle path (§2).
- **Host identity binding is the controlling assumption** (§2): the facade does not authenticate; a host
  that lets clients choose `actor_id`/`scope`/`tenant` has no privacy and no scope boundary from this API.
- **Content digests in the audit log.** Per-item `content_sha256` (already in the package, by design) is
  copied into the receipt: it is the digest of the fact's **full source text**, and `delivered_chars`
  records how much of it a truncated item delivered. For low-entropy memories a reader with audit access
  could confirm a guessed text against the digest. The trust-boundary analysis and the exact owner
  decision are in §9.6; the wording "binds what was delivered" used earlier was imprecise and is withdrawn.
- **Audit growth.** One event per `recall_context` call, like one per recall; same persistence.
- **`unresolved: withheld` at resolution** is defensive only: under the lock the same predicate and
  context that formed `returned` are reused, so the state is not reachable by a caller; it cannot disclose
  a deletion the recall projection did not already hide.
- **Legacy stores**: facts without `write_provenance` receive content on admission but no lineage or
  source references for anyone (§2); the #809 `legacy_unqualified` quarantine is unchanged.
- Unchanged and out of scope: #802 physical sidecar residue, #816 adapter-level durability boundary,
  the 1.8.0 contract decision.

## 7. What this tranche still needs (not supplied here)

1. **Successor declaration.** This head changes four protected blobs beyond the v7 declaration
   (at `d5563d63`: `api/surface.py` → `a30c9d20…`, `runtime/adapter.py` → `85da3030…`, new
   `api/context_package.py` `10111d19…` and `context_package.py` `5e1ee201…`; **current blobs in §9.7**).
   docs/67 Step A: a tranche merging during the open
   transition amends the open v7 declaration (same baseline id); since v7 is frozen for acceptance, the
   owner either amends v7 after its acceptance decisions or publishes v7 first and this tranche declares
   v8. Identity deltas: none (contract stays `1.8.0`; the context package is separately versioned).
2. **Replay and freeze evidence at the declared revision**: regenerate the committed replay evidence
   roots at that revision (the freshness guards fail until then, §4) and re-pin the Gauntlet contestant
   (the #644 identity guard fails until then).
3. **Lane evidence**: new lane ids for the successor (docs/67 `prereq-lane-v3-ids`); the parity rows here
   are checks against accepted v6, not importable evidence.
4. **Owner rulings**: (a) the cross-actor provenance default (implemented as private-by-default);
   (b) the optional `audit` block within `agent-memory-context/0.1.0` or a `0.2.0`; (c) docs/44 wording for
   `recall_context` as a candidate surface; (d) the audit-digest question in §6.
5. **Consuming host**: authenticated actor binding (§2) and a single handle per actor.

## 8. Reproduce

```
# at d5563d63, venv with reference/requirements.txt, PYTHONPATH=reference
python -m pytest reference/tests/test_context_package.py reference/tests/test_691_cross_actor_provenance_review.py \
    reference/tests/test_691_authorization_privacy_challenge.py reference/tests/test_691_context_delivery_audit.py
python -m pytest reference/tests
python scripts/check_runtime_baseline_equivalence.py --candidate HEAD          # exits 1 by design
PYTHONPATH=reference python reference/run_786_security_replays.py --all --output-dir <dir>   # and _dsl2, _dsl3, _dsl4, run_644_v7_replays.py
python scripts/verify_786_security_replays.py --evidence-root <dir> --reexecute --declaration reports/runtime/baseline-v7-declaration.json
python reports/validation/821-atomic-config-binding/probes/crash_window.py reference --json <out>
python -m build && pip install dist/*.whl   # then the installed smoke in install/install-smoke-d5563d63.txt
python scripts/demo_context_package.py --json <out>
bash parity/run_amb_row_691.sh agent-memory <run_id>; bash parity/run_lme_row_691.sh agent_memory session <run_id>
# §9: the reviewer's controls (fail-first at 2f9ce22b, green from 4e4c7d66) and the race probe
python -m pytest reference/tests/test_839_context_audit_failclosed_review.py reference/tests/test_691_context_delivery_audit.py
PYTHONPATH=reference python reports/validation/691-post-v7-context/review-839/race_probe.py 3 5 40   # run 4 copies concurrently to reproduce
```

## 9. Remediation of the independent review (PR #839 review 5609515530, source inspection at `2f9ce22b`)

The review required changes for two audit-integrity edge paths (A, B), preregistered three controls on
`review/839-context-audit-failclosed-no-ci` @ `bec68419` (not executed by the reviewer), asked for an
owner decision on audit-digest semantics and for a disposition of the one thread-race failure. Everything
in this section ran in the same container as §1–§8 (CPython 3.12.3, 4 vCPU), on the heads named.
Evidence files: `review-839/`.

### 9.1 Reproduction (Phase 1): both findings confirmed, fail-first

The reviewer's module `reference/tests/test_839_context_audit_failclosed_review.py` (blob `4cf1a47e`) was
run unmodified against the unmodified head `2f9ce22b` (`review-839/839-controls-failfirst-2f9ce22b.txt`):

| Control | Predicted | Observed at `2f9ce22b` |
|---|---|---|
| 1 final schema validation faulted → zero durable receipts, also after restart | RED | **RED**: one `memory.context_delivery` event persisted although the call raised (`FileNotFoundError` from the missing schema) |
| 2 `_first_recall_event_since` → `None` → refusal, no unbound receipt | RED | **RED**: no exception; a receipt with `recall_bound: false` and `correlation_id` = its own event id was written |
| 3 ordinary delivery binds the recall and survives reopen | GREEN | GREEN |

Finding A (receipt committed before the final package validation) and finding B (a missing recall event
yields an unbound receipt with a synthesised correlation) are therefore **CONFIRMED** as stated.

### 9.2 Corrections (Phase 2), protected tree `83f0ff99…` since `d489ac19`

- **A, ordering** (`api/surface.py`, `4e4c7d66`): `recall_context` no longer validates after recording.
  `_record_context_delivery` builds the event, validates it against `memory-audit-event.schema.json`,
  attaches the `audit` block to the package and validates the **complete package** against
  `api-context-package.schema.json`, all inside `durable_runtime.run_governed_read` and **before**
  `adapter.events.append`. Any exception propagates through the seam (the generation rolls back), the
  `audit` block is stripped from the discarded package and no content is returned. The transactional
  generation, the serialized lock and `allocate_event_id` are unchanged.
- **B, binding** (`api/surface.py`, `api/context_package.py`, `4e4c7d66` + `024d9af3`): before the seam
  opens, the recall event the receipt would cite is checked by `_recall_binding_defect`: it must exist, be
  a `memory.recall` event with an event id and a correlation id, name this principal
  (`context.principal_ref`) and this scope (`payload.project_ref`, `payload.target_domain_refs`), and its
  `payload.outcomes` must record every identifier the recall returned as `admit`. Otherwise
  `ContextDeliveryUnboundError` (a `RuntimeError`, exported) is raised and nothing is recorded or
  delivered. `delivery_event` itself refuses a missing event or correlation id (`ValueError`), never
  substitutes its own id, always sets `causation_id`, and `recall_bound` is always `true` in an emitted
  receipt. `_first_recall_event_since` (the first recall event for this principal after the call began,
  under the same lock) is unchanged, so the reviewer's control patches it as written.
- **Schema** (`d489ac19`): `audit.recall_event_id` is required and a non-empty string (was
  `string|null`). Packages without an `audit` block stay valid; `agent-memory-context/0.1.0` unchanged
  (§9.6).
- **Not changed**: `recall()` (AST-identical to `72d6a903`, re-checked at `d489ac19`), selection, ranking,
  budgets, deletion/withholding, provenance minimisation, the package body, the event type and version.
- **Test-only** (`8964d6fd`): `test_api_dod20` classifies the exported exception type.

### 9.3 Red-to-green and the adversarial matrix (Phase 3)

| Suite | Result | Record |
|---|---|---|
| reviewer's three controls, unmodified, after `4e4c7d66` | **3/3 pass** (RED, RED, GREEN → GREEN ×3) | `review-839/839-controls-after-repair-4e4c7d66.txt` |
| `test_691_context_delivery_audit.py` (8 → **19 tests**) + reviewer's 3 + `test_context_package` + cross-actor review + Phase 2 challenge (13, unchanged) + DoD-20 | **63 passed** at `8964d6fd` | `review-839/691-and-839-suites-8964d6fd.txt` |

New tests, each checked in memory and after reopening the store, with ordinary delivery afterwards:

| Case (brief) | Test |
|---|---|
| receipt appended only after the final package (audit included) validates | `Receipt.test_receipt_is_appended_only_after_the_final_package_validates` |
| missing recall event → `ContextDeliveryUnboundError`, no receipt; `delivery_event(None)` and a recall event without correlation → `ValueError` | `Receipt.test_missing_recall_event_refuses_delivery_without_a_receipt` |
| malformed recall event: wrong type, empty id, no correlation, other principal, other scope, outcomes missing, outcomes refused (7 defects) | `FailClosed.test_malformed_recall_event_is_refused` |
| another actor's real recall event | `FailClosed.test_another_actors_recall_event_is_refused` |
| event append failure | `FailClosed.test_event_append_failure_leaves_no_receipt` |
| generation persistence failure (`_persist_unlocked` raises) → rollback, governance restored, restart clean, writes still commit | `FailClosed.test_persistence_failure_rolls_the_receipt_back_and_restarts_clean` |
| invalid completed package carrying audit identifiers | `FailClosed.test_invalid_completed_package_with_audit_identifiers_is_refused` |
| five repeated deliveries: unique event ids, five distinct recall causations, same order after reopen | `FailClosed.test_repeated_deliveries_have_unique_ids_and_distinct_recalls` |
| `recall_control="shadow"`: exactly one recall event, the receipt is caused by it | `FailClosed.test_shadow_recall_control_binds_to_the_executed_recall` |
| other-project reader: `empty` package, receipt with no identifiers and nothing of this project | `FailClosed.test_other_project_receipt_names_nothing_of_this_project` |
| already present (§3): failure after append inside the seam rolls back; unrecordable receipt delivers nothing; empty/truncated/exhausted/unresolved states; deleted-lineage identifiers never enter a receipt; refused calls record nothing; restart durability | `Receipt.*` |

Broader selection at `8964d6fd` (44 modules: #786/#777/#809/#835/#821/#802/#816, restart, SQLite,
facade, temporal, durable, security, provenance, deletion, authorization, surface, #691, #839):
**518 passed, 2 skipped, 1 xfail** (`review-839/broad-security-facade-durability-8964d6fd.txt`).

### 9.4 The thread-race failure: dispositioned as pre-existing, fail-closed, load-dependent

`test_786_cross_scope_write_authority.py::CompetingWriters::test_threads_racing_as_both_projects_never_move_the_owners_head`
failed once in the §4 full-suite run with `RuntimeRecoveryError('cannot restore governance after SQLite
rollback')` collected in `errors` (raised from a `remember`, not from `open`, which the test tolerates).

Investigation (`review-839/race-*.txt`, probe `review-839/race_probe.py`):

| Condition | Head `d489ac19` (this tranche) | Base `72d6a903` (unchanged v7) |
|---|---|---|
| the test alone, 25 + 40 repetitions, light/moderate load | 65/65 pass | 65/65 pass |
| probe, test shape (3 threads × 5 writes), 100 rounds, one process | 0 recovery errors in `remember` | 0 |
| probe, 8 threads × 10 writes, 30 rounds, one process | 0 | 0 |
| probe, test shape, **4 concurrent processes** (CPU oversubscribed on 4 vCPU), 40 rounds each | **5 rounds of 160** with one `remember`-path `RuntimeRecoveryError` | **2 rounds of 160** |
| owner's head moved, or any other-project write committed, in any round | **never** (0 of 710 rounds) | **never** (0 of 710 rounds) |

Mechanism: `SQLiteRestartSafeRuntime._transactional_operation` restores governance after a rolled-back
generation by two separate reads (`read_runtime_state`, then `governance.load_verified(digest)`); when
another handle publishes a generation between them the digest check fails closed. It is the same class
as the open-time recovery error the test already tolerates ("a recovery that reads while another handle
publishes a checkpoint fails closed … instead of opening on a torn view"), surfacing on the `remember`
path instead. The handle stays usable (the probe's later writes are refused or conflict as designed).
`runtime/sqlite_runtime.py`, `restart_runtime.py`, `configured_restart.py` and `state/substrate.py` are
byte-identical to the v7 base (`1c1d456f`, `85014e40`, `11ec6ac9`, `9d9aed0a`).

Disposition: **not introduced by this tranche; not an integrity defect (the invariant the test protects
held in every round); a liveness/fail-closed behaviour of the v7 SQLite profile under multi-process
contention that the test's tolerance does not cover on the `remember` path.** It belongs with the #816
SQLite durability boundary. Nothing here is changed for it (the protected v7 runtime is out of this
tranche's scope); the owner can either widen the test's tolerance to the `remember` path or have a
runtime tranche read state and governance in one transaction.

### 9.5 Requalification at the repaired head (Phase 5)

| Gate | Result | Record |
|---|---|---|
| full reference suite at `8964d6fd`, from the repository root (CPython 3.12.3) | **3211 passed, 4 failed**, 27 skipped, 1 xfail, 2186 subtests, 322 s. The four: exactly the v7 identity guards (two #770 replay-freshness guards, the #644 Gauntlet identity guard, the baseline-equivalence contract test). The thread-race test passed in this run; its disposition is §9.4. Integration-introduced failures: none | `review-839/full-suite-8964d6fd.txt` |
| 13 replay families re-executed at `d489ac19` (786 v2/v3, #809, #835 DSL/4, five #644) | all PASS; `observations_sha256` **identical** to the `2ad4cf23` v7 record for all 13; `verify_786…` 5/5 VERIFIED, `verify_644…` 5/5 VERIFIED, `evidence_verified: true` (re-executed) | `review-839/replays-d489ac19/` |
| #821 crash-window matrix at `d489ac19` (9 kill points) | outcome-identical to the v7 record and to `d5563d63` (only timestamps, elapsed, revision differ) | `review-839/crash-window-d489ac19.*` |
| `check_runtime_baseline_equivalence --candidate HEAD` | exits 1 **by design** (same four protected deltas) | `review-839/checker-d489ac19.txt` |
| validators (schemas 75, fixtures 64, architecture index 84, doctrine boundaries, wiki links), `git diff --check` | all OK | `review-839/validator-*.txt` |
| public `recall()` vs the v7 base | AST-identical; `_recall_document_and_context` and the three new methods are the only `AgentMemory` changes | §9.2 |
| AMB PrecisionMemBench agent-memory row (77 cases, retrieval-only, frozen harness) at `8964d6fd` | **77/77 L1-equal to accepted v6**, no flips; cross-fact sidecar 73 records; checker state recorded as FAIL (by design; parity check, not lane evidence, not imported) | `review-839/parity/` |
| LongMemEval_S agent_memory rows (500 questions, session + turn, top-50) at `8964d6fd` | **500/500 equal to accepted v6 on both planes** (ranked_top, metrics, cross-fact records; aggregates equal; no lost required evidence); checker state FAIL by design, not imported | `review-839/parity/` |
| wheel + sdist from `git archive` at `d489ac19`, fresh CPython 3.12 venvs, `python -I` from outside the checkout | installed smoke OK for both (`recall_context` with the audit block, receipt bound, a faulted final validation and a faulted recall linkage each leave the receipt count unchanged, count unchanged after reopen). The first quiet `pip install` of the wheel produced no package (no error surfaced); it was repeated with visible output and succeeded (`install-smoke-wheel-retry-…`) | `review-839/install/` |
| `scripts/demo_context_package.py` against the installed wheel and from the source checkout | ALL CHECKS PASSED (both) | `review-839/install/demo-*` |

Four of the full-suite failures are the v7 identity guards described in §4 (two #770 freshness guards, the
#644 Gauntlet identity guard, the baseline-equivalence contract test); they must clear through the
successor declaration (§9.7), not by weakening them. An earlier full-suite run of this head executed from
`reference/` instead of the repository root produced four additional cwd-dependent failures (Gauntlet
adapters and a fixture path) and one genuine one (DoD-20, fixed at `8964d6fd`); that run is kept as
`review-839/full-suite-d489ac19-from-reference-dir.txt` and is not the qualification run.

### 9.6 Security and privacy review of the two open design questions (Phase 4)

**Audit digest semantics.** The receipt carries, per delivered identifier, `content_sha256` (SHA-256 of
the fact's full source text, the same value the package's provenance gives the caller) and
`delivered_chars`; and `package_sha256` over the canonical package without `audit` (which contains the
rendered text). Findings:

1. *Trust boundary today.* The receipt lives in the adapter's event log, which the runtime persists in
   the governance sections of the **same SQLite file** that holds the fact text
   (`agent-memory.sqlite3`, `0700` directory, single-user profile). There is no separate audit-reader
   authority in the runtime: anyone who can read the receipt can read the fact rows. Within the supported
   local single-user envelope a plain digest therefore discloses nothing the reader lacks, and keying it
   would protect nothing.
2. *Where it would matter.* A host that **exports** the event log to a sink with a wider readership
   (central audit, SIEM, backups readable by others) turns `content_sha256` and `package_sha256` into a
   confirmation oracle for low-entropy memories ("is the gate code 4471?"). Hashing is not secrecy.
3. *Source vs delivered.* `content_sha256` is the source digest by construction; it lets an auditor check
   a delivered item against the stored fact, and a consumer check the full text it received. For a
   `truncated` item the receipt does not independently bind the delivered prefix (only its length). A
   `delivered_sha256` for truncated items would close that gap; it is an additive payload change
   (`payload` is free-form under the audit schema).

Recommendation and the **exact owner decision required**: keep plain source digests for the local
single-user envelope and document the export restriction (a host that exports the event log must strip
or key the two digest fields); add `delivered_sha256` for truncated items when the package version next
moves. The owner must rule between (a) *accept*: plain digests, export restriction documented in docs/44
when `recall_context` is adopted, or (b) *require keyed/opaque digests*: an HMAC under a host-supplied
key, which adds a key requirement to `AgentMemory.open` and a payload change, and needs an approved
requirement first. No key management was introduced here.

**Package schema version.** `agent-memory-context/0.1.0` gained an optional `audit` block (`d5563d63`) whose
`recall_event_id` is now required (`d489ac19`). The schema is top-level `additionalProperties: false`, so
a consumer validating with a copy of the pre-`d5563d63` schema would reject packages carrying `audit`;
a consumer reading fields ignores it. Three distinct identities: the **package version** (this schema, a
candidate that docs/44 does not yet name and that nothing has published), the **public runtime contract**
`1.8.0` (unchanged: `recall_context` is a facade method, no result-envelope stage or field changed), and
the **distribution version** `agent-memory-reference==0.2.0` (`pyproject.toml` unchanged; #836 owner gate 3).
Recommendation: **stay at `0.1.0`** while the package is an unaccepted candidate with no external consumer
(the only shape anyone has seen is this review's), and bump to `0.2.0` at the first change after the
owner accepts the shape, or now if the owner regards the `2444ed31` staging as already exposed. The
decision is the owner's; the code bumps nothing.

### 9.7 Successor-baseline requirements (Phase 6, replaces the blob list in §7.1)

| Requirement | Exact value at `8964d6fd` |
|---|---|
| protected blobs beyond the v7 declaration (`7de94f11`) | `api/surface.py` `ba8924d4` → `66b1ee45`; `runtime/adapter.py` `2c0d3b6d` → `85da3030`; new `api/context_package.py` `6ae5bc41`; new `context_package.py` `5e1ee201` (protected tree `83f0ff99…`). `schemas/api-context-package.schema.json` (`942febd9`) is outside the protected surface |
| declaration route (docs/67 Step A.6) | amend the open v7 declaration only after v7's acceptance decisions, or declare v8 after v7 publishes; one `declared_successor` at a time. **v7 is on HOLD, so #839 stays independently reviewable and is not merged into #836** |
| identity deltas | none (`public_contract_version` stays `1.8.0`; `pyproject_change: null`); the package version is separate (§9.6) |
| lane evidence | new lane ids for the successor (docs/67 `prereq-lane-v3-ids`); the §9.5 AMB/LME rows are parity checks against accepted v6, not importable lane evidence |
| replays | regenerate the committed `reports/validation/644-v7-replays/` and `security-replays-*` roots at the declared revision (the #770 freshness guards clear then); the 13 families already re-execute identically here |
| public Gauntlet | re-pin the contestant adapter/manifest to the declared revision (`FROZEN_RUNTIME_REVISION`, tree, adapter blob); the #644 identity guard clears then; B1/B2 publication route is the #836 owner gate 4 |
| acceptance | independent security disposition (§6, §9.6 decision), docs/44 wording for `recall_context`, package-version ruling; `#691` stays open |
| installed consumer qualification | wheel/sdist + demo at the declared revision (this section's runs are at `d489ac19`, same protected tree) |

### 9.8 Verdict

**PASS FOR INTEGRATION REVIEW** (unchanged): both review findings reproduced, repaired minimally and
covered by the reviewer's controls and a fail-closed matrix; replays, crash matrix, broad suites and
installed demonstrations hold; benchmark parity with accepted v6 is exact. **Not accepted, not a
successor qualification**: the four v7 identity guards fail by design until the successor declaration,
and the owner rulings in §9.6/§9.7 are open.
