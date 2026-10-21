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

**This tranche edits protected runtime source after the v7 declaration and does not amend that
declaration.** `check_runtime_baseline_equivalence.py --candidate HEAD` exits 1 by design
(`logs/checker-d5563d63.txt`): two undeclared protected files (`api/context_package.py`,
`context_package.py`) and two declared blobs moved (`api/surface.py`, `runtime/adapter.py`). Passing the
v7-era tests therefore qualifies nothing by itself; the successor requirements are listed in §7.

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
  store stays usable;
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
  copied into the receipt so an audit reader can bind what was delivered without the text. For
  low-entropy memories a reader with audit access could confirm a guessed text against the digest. Audit
  readers are a separate authority; if that is not acceptable, the receipt could carry a keyed digest
  instead (owner decision).
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
   (`api/surface.py` → `a30c9d20…`, `runtime/adapter.py` → `85da3030…`, new `api/context_package.py`
   `10111d19…` and `context_package.py` `5e1ee201…`). docs/67 Step A: a tranche merging during the open
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
```
