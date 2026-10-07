# Plan: #672 tranche 5 — harvests into implementation tranches (closeout v2 as data)

Roadmap scope `scope-tranche-5-harvests` (node `fact-harvest-dispositions`, resolved at Entry #74 by `docs/research-brief-tranche-5-harvests-and-ci-cost-2026-10-07.md`, findings A–D and recommendations 1–5). Evaluation-only: nothing under `reference/agentmem_ref/` except `evaluation/**` changes, no runtime behaviour changes, `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` stays `PASS`. The tranches this plan records are runtime work for later plans; this plan makes the record complete, enforced and attributable so that each tranche can start from a verified fact rather than from the word `absorbed`.

Invariants kept: Runtime / Memory Evaluation / Gauntlet separation; `unsupported ≠ failed ≠ zero`; `derived ≠ native`; benchmark score ≠ authority; no universal health scalar; the published baseline records are immutable (docs/67), so the capability-inventory drift of finding D is stated in prose and corrected only by the next successor record.

## Open Questions

- **OQ1 — tranche issues.** Rows classified `tranche` must cite an issue. Existing issues cover the vector route (#669), ranking (#673) and the Jev-Mem controller work (#644); no issue exists for typed relation vocabulary, metabolism/consolidation composition, failure-memory composition or the consumer-aware package. Decision: Phase 3 opens one issue per missing tranche (four), labelled by the `Enforce Issue Labels` workflow's baseline label, each body quoting its fixture rows and lane gate, and the fixture cites the numbers; until the numbers exist the fixture carries `"issue": null` and the test's `expected_unassigned` list names those rows, emptied in Phase 3 (the same expected-failures pattern as `docs/plan-662-ci-cost-phases-2-4.md` Phase 1).
- **OQ2 — UOR saturation-based decay** (finding B: no harvest row; `docs/03-scoring-and-decay.md:5, 97-110`; runtime formula `cmhl-bounded-v1`, `reference/agentmem_ref/memory/metabolism.py:24`). Decision: `declined` with reason "lineage only; no saturation/`T_ctx` code exists and the runtime decay formula is `cmhl-bounded-v1`; a saturation model would be a metabolism-tranche proposal, not a harvest", and the metabolism tranche row's notes name it as research pressure. No new UOR tranche (#672 item 3 closes).
- **OQ3 — `evaluated_against_agent_memory_revision`.** The v2 fixture pins the `main` head the rows were verified against. Decision: the merge commit of PR #687 (the current `main` when this plan is written), re-verified by the test's module-existence and evidence-resolution checks on every run, so a later revision that moves a module fails the test rather than silently invalidating the record.
- **OQ4 — rows the brief marks "shipped (evaluation)".** Decision: `disposition: shipped` with `reachability: evaluation_only` and the evidence being the workflow or test that exercises them; a `shipped` row never claims a runtime path it does not have.
- **OQ5 — the attribution convention before any adapted code.** Decision: the convention is declarative in `docs/SOURCE_RIGHTS_POLICY.md` (a file-header line and a root `THIRD_PARTY_NOTICES.md` created by the first PR that adapts code, carrying the verbatim notice from the frozen revision); this plan creates the Jev-Mem registry record with `reuse_mode: citation_only` and does not create `THIRD_PARTY_NOTICES.md`, because nothing is adapted yet and an empty notices file would be a claim without material.

## Locked Decisions

**LD1 — The closeout is versioned data with a closed vocabulary.** New `reference/fixtures/harvest-closeout-final-v2.json` (v1 at `reference/fixtures/harvest-closeout-final-v1.json` is untouched; `supersedes` names it): `{"schema_version": "2.0.0", "artifact_id": "agent-memory-harvest-closeout-final-v2", "issue": 672, "status": "complete_mechanism_closeout", "supersedes": {"artifact_id": "agent-memory-harvest-closeout-final-v1", "path": "reference/fixtures/harvest-closeout-final-v1.json"}, "evaluated_against_agent_memory_revision": "<OQ3>", "dispositions": ["shipped", "tranche", "declined"], "reachability": ["facade", "evaluation_only", "library_only", "harness_only", "absent"], "rows": [...], "out_of_mechanism_scope": [...]}`. One row per mechanism of finding A plus the saturation-decay row (OQ2): 28 rows (10 of them carry a v1_ref, 13 a Jev-Mem id, one the Jev-Mem rejection list, and four are split or new rows with no v1_ref of their own). Row shape: `row_id` (unique slug), `v1_ref` (`{"source": <v1 source>, "mechanism": <v1 mechanism string verbatim>}` or `{"doc": "docs/research-jev-mem-harvest.md", "id": "JH-nn"}` or `null` for the new row), `mechanism` (one line), `disposition`, `reachability`, `modules` (repository paths that must exist; empty only for `declined` and `absent`), `evidence` (list; each item is `{"integration": "<file name under reference/agentmem_ref/evaluation/integrations/>", "variant": "<evidence_history variant>"}`, `{"workflow": "<file under .github/workflows/>"}` or `{"path": "<committed report or test>"}`), `tranche` (`{"issue": <int|null>, "lane_gate": "<string>", "order": "<tranche name>"}`, present on `tranche` rows only), `reason` (non-empty on `tranche` and `declined` rows), `notes`. The disposition rule: `shipped` ⇔ reachability `facade` or `evaluation_only` and at least one evidence item; `tranche` ⇔ reachability `library_only`, `harness_only` or `absent` and a `tranche` block; `declined` ⇔ a reason and no `tranche` block. `out_of_mechanism_scope` lists every v1 `(source, mechanism)` pair and every Jev-Mem id (JH-01, JH-11, JH-15) that is identity, authority or interoperability rather than a retrieval/memory mechanism, each with `class` ∈ {`identity`, `authority`, `interop`, `evaluation_discipline`}; v1's 15 `sources` entries carry 23 mechanisms (`closeout` in v1 is the summary block, not the rows), and the test requires every one of them to appear exactly once across `rows[*].v1_ref` and `out_of_mechanism_scope`, and every JH-01…JH-16 likewise.

Row dispositions (from finding A; `tranche` rows name the tranche of LD5):

| row_id | v1_ref / JH | disposition | reachability | modules (exist) | evidence / tranche |
|---|---|---|---|---|---|
| evolveai-vector-retrieval | EvolveAI "semantic/vector retrieval, temporal behavior, lifecycle/metabolism, consolidation and prune pressure" (split: this row carries the v1_ref; the two rows below cite the same v1_ref via `v1_ref_shared: true`) | tranche | library_only | `reference/agentmem_ref/runtime/vector_retrieval.py` | T-vector (#669) |
| evolveai-temporal-behaviour | same v1_ref, shared | shipped | facade | `runtime/temporal_order_constraints.py`, `runtime/ranking_policy.py` | integration `agent-memory-longmemeval-retrieval-currentness-v1.json`, variants `lane:longmemeval-s-retrieval-parity-v2:agent_memory:session` and `:turn` |
| evolveai-metabolism | same v1_ref, shared | tranche | library_only | `memory/metabolism.py`, `memory/maintenance_run.py` | T-metabolism (OQ1) |
| evolveai-typed-traversal-claim | null (the claim lives in v1 `current_agent_memory_equivalent`, not a mechanism; DRIFT) | tranche | absent | none | T-typed-relations (OQ1); reason: no entity/causal vocabulary, graph relation types are caller-supplied (`runtime/recall_control.py:80-87`) |
| evolveai-failure-memory | EvolveAI "ShadowGenome typed failure identity, recurrence evidence and bounded persistence" | tranche | library_only | `memory/failure_memory.py` | T-failure-memory (OQ1) |
| codegenome-graph-propagation | CodeGenome "generic weighted directional relation propagation and traversal" | tranche | harness_only | `runtime/recall_control.py` | T-controller (#644) |
| codegenome-regression-pressure | CodeGenome "continuous experiment and regression pressure" | shipped | evaluation_only | `reference/retrieval_regression.py` | workflow `retrieval-quality-benchmark.yml` |
| codegenome-noisy-or | CodeGenome "noisy-OR numerical confidence fusion as generic evidence qualification" | declined | absent | none | reason: ADR-037, numeric fusion cannot stand in for authority |
| uor-r4-geometric-model | uor-r4 "geometric predictive memory model" | declined | absent | none | reason: no superiority over matched controls |
| uor-r4-keyed-rebinding | uor-r4 "repeated exact-key rebinding, matched controls, stale-value measurement and negative-result discipline" | shipped | facade | `runtime/adapter.py`, `reference/run_keyed_rebinding_benchmark.py` | workflow `long-horizon-memory-benchmark.yml`; the currentness lane variants above |
| uor-saturation-decay | null (OQ2) | declined | absent | none | reason per OQ2 |
| uor-jcs-nfc-mutation-sensitivity | uor-jcs-nfc "mutation sensitivity for conformance and benchmark checks" | shipped | evaluation_only | `reference/run_benchmark_integrity_mutants.py` | path `reference/tests/test_benchmark_integrity_mutants.py` |
| prismpm-mutation-pressure | PrismPM "positive/negative corpora and mutation pressure against stale, bypassed or trivially passing verification" | shipped | evaluation_only | same | same |
| coreforge-context-assembly | COREFORGE "generic Vault/Neurospace provider ownership boundary and generic mutation/lineage authority" | shipped | facade | `api/surface.py`, `api/contract.py` | integration `amb-precisionmembench-retrieval-v1.json`, variant `lane:amb-precisionmembench-retrieval-v2:agent-memory`; notes: packaging and redaction declined (product concerns) |
| jh-02-write-time-candidate-search | JH-02 | tranche | facade (identity-first only) → recorded as `library_only` because the four-way comparison never ran | `runtime/adapter.py`, `runtime/proposition_semantics.py` | T-controller-2 (#644) |
| jh-03-typed-relation-judgments | JH-03 | tranche | absent | `state/substrate.py` | T-typed-relations (OQ1) |
| jh-04-route-needs | JH-04 | tranche | harness_only | `runtime/recall_control.py` | T-controller (#644) |
| jh-05-budget-allocator | JH-05 | tranche | harness_only | same | T-controller-2 (#644) |
| jh-06-call-deadline-budget | JH-06 | tranche | absent | same; `reference/fixtures/runtime/system-one-controller-contract-v1.json` | T-controller (#644) |
| jh-07-sufficiency-stopping | JH-07 | tranche | harness_only | same | T-controller-2 (#644) |
| jh-08-traversal-value | JH-08 | tranche | facade (1 of 5 factors) → `library_only` | `runtime/ranking_policy.py` | T-ranking (#673) |
| jh-09-bounded-traversal | JH-09 | tranche | harness_only | `runtime/recall_control.py` | T-controller (#644) |
| jh-10-consolidation-vocabulary | JH-10 | tranche | library_only | `memory/metabolism.py` | T-metabolism (OQ1) |
| jh-12-typed-probabilities | JH-12 | tranche | absent | `contracts/cognitive_classification.py` | T-controller-2 (#644) |
| jh-13-decision-cache | JH-13 | tranche | absent | same | T-controller-2 (#644) |
| jh-14-telemetry | JH-14 | tranche | harness_only | `runtime/recall_control.py`, `api/surface.py` | T-controller (#644) |
| jh-16-consumer-package | JH-16 | tranche | library_only | `api/contract.py` | T-consumer-package (OQ1) |
| jev-mem-explicit-rejections | Jev-Mem do-not-import list (J:419-439) | declined | absent | none | reason: explicit upstream rejections (admission authority, recency-as-currentness, benchmark QA heuristics, best-of-N, MAGMA fallback) |

Reachability values on rows marked "→" are the recorded value (the arrow explains the judgment in `notes`). Module paths are relative to `reference/agentmem_ref/` where unprefixed in this table; the fixture carries full repository paths, each resolved against the working tree before its row is written (iteration 2 after Entry #80: `runtime/proposition_semantics.py`, not `memory/`; `reference/fixtures/runtime/system-one-controller-contract-v1.json`). The remaining v1 mechanisms (UOR-Framework identity lineage, uor-addr, uor-foundry ×2, uor-jcs-nfc canonicalization, uor-matmul, PrismPM typed authority binding and OCI release graph, microsoft/agent-governance-toolkit, AgentTrust TRACE, Agent Manifest, cmcp v0.4.0 and v0.5.0, COREFORGE is above) go to `out_of_mechanism_scope` with their class; JH-01, JH-11 and JH-15 go there with class `evaluation_discipline` and a note that they join the first tranche that makes the controller reachable.

**LD2 — One test enforces the record.** New `reference/tests/test_harvest_closeout_v2.py`, a pure function of committed files: (a) vocabulary closure (`disposition`, `reachability`, `class`) and `row_id` uniqueness; (b) coverage: every v1 `(source, mechanism)` pair (derived by loading v1) and every `JH-01`…`JH-16` id (derived from the table rows of `docs/research-jev-mem-harvest.md` that start with `| JH-`) appears exactly once across `rows[*].v1_ref` (shared refs count once) and `out_of_mechanism_scope`; (c) the disposition rule of LD1 per row; (d) every `modules` path exists; (e) every evidence item resolves: an `integration`/`variant` pair is an `evidence_history` entry with `status: "complete"` in that integration file, a `workflow` is a file under `.github/workflows/` with an entry in `data/github-actions-workflow-policy.json`, a `path` exists; (f) every `tranche` row has a non-empty `lane_gate` and `order`, and `issue` is a positive integer unless the `row_id` is in the test's `EXPECTED_UNASSIGNED` list (OQ1; emptied in Phase 3); (g) the rc1 closeout manifest agrees: `build_manifest(<any revision>)["harvest_closeout"]` has `status` equal to the fixture's `status`, `issue` 672 and `artifact` equal to the fixture path.

**LD3 — The rc1 closeout manifest stops saying `active_open`.** `reference/run_rc1_evidence_closeout.py:103-109` becomes `{"status": "complete_mechanism_closeout", "issue": 672, "artifact": "reference/fixtures/harvest-closeout-final-v2.json", "supersedes_issue": 470, "claim": "every harvested mechanism is shipped with evidence, assigned to an implementation tranche with an issue and a lane gate, or declined with a reason", "dependency_effect": "does_not_block_repository_owned_rc_evidence_packaging", "external_dependency_required": False}`; `reference/tests/test_rc1_evidence_closeout.py:37-45` is renamed `test_harvest_closeout_is_complete_and_independent` and asserts the new values. No committed manifest carries `active_open` (grep over `reports/`, `docs/` finds only the brief and the ledger), so nothing is regenerated.

**LD4 — The standing rule and the attribution preconditions.** `docs/CONTRIBUTOR_ARCHITECTURE.md` gains "## 11a. Harvest closeout rule" after §11: a harvest closes only when every mechanism is `shipped` (a module on the facade or evaluation path plus resolving evidence), `tranche` (an issue, a lane gate and an order) or `declined` (a reason); `absorbed` is not a terminal state; the record is the latest `reference/fixtures/harvest-closeout-final-v*.json`, enforced by `reference/tests/test_harvest_closeout_v2.py`; a new mechanism or a changed disposition is a new fixture version, never an edit of a published one; and a tranche that adapts third-party code needs its `sources/source-registry.json` record and the notice convention before the first adapted line. §8 gains one sentence: the current baseline record's `native_qualified` statuses for `semantic_vector_retrieval`, `typed_relations_graph_traversal` and `memory_metabolism` describe library capability not reachable from the facade (closeout v2 rows `evolveai-vector-retrieval`, `codegenome-graph-propagation`, `evolveai-metabolism`); the next successor declares the corrected statuses as identity deltas. `sources/source-registry.json` gains the record `{"source_id": "jev-mem", "title": "Jev-Mem (System-One memory control, MAGMA-derived)", "source_type": "external_research_implementation_ancestry", "public_url": "https://github.com/libingzheren/Jev-Mem", "repository": "libingzheren/Jev-Mem", "access": "public", "copyright_owner_or_originator": "Jev-Mem contributors (MAGMA upstream notice preserved by the source)", "license_spdx": "MIT", "license_url": "https://github.com/libingzheren/Jev-Mem/blob/7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44/LICENSE", "rights_status": "verified_open_license", "reuse_mode": "citation_only", "reuse_basis": "Repository MIT license verified at the frozen revision 7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44 (docs/research-jev-mem-harvest.md); nothing is adapted yet; the harvest is implementation ancestry, not a runtime dependency.", "material_reused": "None registered. Mechanism characterization only.", "attribution_required": true, "notice_required": true, "modification_notice_required": false, "provenance_note": "Frozen upstream revision 7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44; Jev / TypeSafe / Laya / weights / datasets carry separate terms and are out of scope.", "limitations": "Direct or substantial adaptation must preserve the MIT copyright and permission notice per the adapted-code notice convention (docs/SOURCE_RIGHTS_POLICY.md); a record with reuse_mode licensed_reuse replaces this one when code lands.", "verified_at": "2026-10-07"}` (validated by `python scripts/validate_schemas.py` against `schemas/source-record.schema.json`). `docs/SOURCE_RIGHTS_POLICY.md` gains the section "Adapted-code notice convention": a file that adapts code carries, in its module docstring's first line, `Adapted from <source_id> at <revision> (<SPDX>); notice in THIRD_PARTY_NOTICES.md`; the root `THIRD_PARTY_NOTICES.md` is created by the first adapting PR and holds, per source, the verbatim copyright and permission notice from the frozen revision; the registry record's `notice_required` is the trigger, and `NOTICE` gains one pointer line to the section.

**LD5 — The tranches, as the fixture's `tranche.order` values and the issues that own them.** T-vector (#669): the semantic vector route reachable from the facade with a shipped provider (owner decision `decision-embedding-dependency` gates it). T-controller (#644, first Jev-Mem tranche): a facade-level recall-control seam making the controlled planner reachable without changing ranking: JH-06 call/deadline budget, the fixture's four stop-reason classes, JH-14 telemetry, JH-04 route needs, JH-09 bounds and the CodeGenome typed-graph route; `controller_calls` stops being a constant; JH-11 and JH-15 join here. T-controller-2 (#644, second): JH-07 sufficiency, JH-05 allocation, JH-02 four-way comparison, JH-12, JH-13. T-ranking (#673): JH-08's remaining traversal-value factors inside the post-admission ranking stage. T-typed-relations (OQ1 new issue): entity/causal relation vocabulary and JH-03 judgments. T-metabolism (OQ1 new issue): a runtime caller for `propose_consolidation` and `plan_metabolism_maintenance`, JH-10 vocabulary; saturation decay is research pressure only. T-failure-memory (OQ1 new issue): compose `FailureMemory` into recall admission evidence. T-consumer-package (OQ1 new issue, after T-controller): JH-16 beyond the k-prefix. Every tranche's `lane_gate` is the same sentence: "a new lane id on the accepted `-v2` lane configurations (§10 lane generations) with no regression of the accepted v2 rows' scored metrics, and a declared Runtime Baseline successor for any runtime change (docs/67)". No tranche changes ranking semantics except T-ranking, and none is scheduled by this plan (owner decision `decision-capacity-split`).

**LD6 — Governance.** `docs/GOVERNANCE_INDEX.md` Tier 4 row; ledger IMPLEMENTATION entry; roadmap scope `scope-tranche-5-harvests` resolved by pointer at the merge commit; one comment on #672 listing the 24 rows' dispositions, the eight tranches with their issues, and the UOR item-3 conclusion; the four new issues (OQ1) reference #672 and #668.

## Phase 1: the closeout record as data, enforced

### Affected Files

- `reference/tests/test_harvest_closeout_v2.py` - new (LD2), with `EXPECTED_UNASSIGNED` naming the rows whose tranche issue does not exist yet (OQ1)
- `reference/tests/test_rc1_evidence_closeout.py` - the harvest test asserts the LD3 values
- `reference/fixtures/harvest-closeout-final-v2.json` - new (LD1)
- `reference/run_rc1_evidence_closeout.py` - LD3

### Changes

Per LD1–LD3. The fixture is written by hand from finding A's table (every cell is a fact the brief verified by file:line); the test is what keeps it true.

### Unit Tests

- `reference/tests/test_harvest_closeout_v2.py` - checks (a)–(g) of LD2 against the committed fixture; plus two negative cases on an in-memory copy: a `shipped` row whose evidence variant is `blocked` fails (e), and a v1 mechanism removed from both lists fails (b).
- `reference/tests/test_rc1_evidence_closeout.py` - `harvest_closeout.status == "complete_mechanism_closeout"`, `artifact` is the v2 fixture path, independence fields unchanged.

## Phase 2: rule, attribution record, documentation

### Affected Files

- `reference/tests/test_harvest_closeout_v2.py` - gains the registry precondition check: every `tranche` row whose `v1_ref.doc` is the Jev-Mem document requires a `sources/source-registry.json` record with `source_id` `jev-mem` and `notice_required: true`
- `docs/CONTRIBUTOR_ARCHITECTURE.md` - §11a and the §8 sentence (LD4)
- `docs/SOURCE_RIGHTS_POLICY.md` - "Adapted-code notice convention" (LD4)
- `NOTICE` - one pointer line
- `sources/source-registry.json` - the `jev-mem` record (LD4)
- `docs/GOVERNANCE_INDEX.md` - Tier 4 row (LD6)

### Changes

Per LD4 and LD6; `python scripts/validate_schemas.py` validates the registry record.

### Unit Tests

- `reference/tests/test_harvest_closeout_v2.py` - the registry precondition.

## Phase 3: tranche issues, ledger, roadmap

### Affected Files

- the four OQ1 issues (GitHub), then `reference/fixtures/harvest-closeout-final-v2.json` - `issue` numbers filled; `reference/tests/test_harvest_closeout_v2.py` - `EXPECTED_UNASSIGNED` emptied
- `docs/META_LEDGER.md` - IMPLEMENTATION entry
- `.qor/roadmaps/north-star-best-in-class/events.jsonl` - `scope-tranche-5-harvests` resolved by pointer to the merge commit

### Changes

Per LD5 and LD6. The #672 comment is posted after merge.

### Unit Tests

- none beyond Phases 1–2; `qor-logic governance-health --profile skill-entry` and `qor-logic verify-ledger` are the gates.

## Definition of Done

### Deliverable: the record

- **D1**: `reference/fixtures/harvest-closeout-final-v2.json` covers every v1 mechanism and every Jev-Mem id exactly once, uses only the closed vocabularies, and `test_harvest_closeout_v2.py` fails on a missing module, an unresolved evidence item, a `tranche` row without an issue, or a disposition that breaks the LD1 rule.

### Deliverable: the rule and the preconditions

- **D2**: §11a states the rule, the `jev-mem` registry record validates, the notice convention is written, and the rc1 closeout manifest no longer reports `active_open`.

### Deliverable: the tranches

- **D3**: eight tranches named in the fixture with issues (#669, #644 ×2, #673, four new), one shared lane gate, and the roadmap scope resolved by pointer with the ledger entry and the #672 comment.

## Feature Inventory Touches

| entry_id | operation | test_path | test_descriptor |
|---|---|---|---|
| n/a (fixtures, tests, docs, registry; no `reference/agentmem_ref` module is touched) | n/a-justified | `reference/tests/test_harvest_closeout_v2.py` | the harvest closeout as data, enforced against the repository |

## CI Commands

- `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` — stays `PASS`
- `python -m unittest reference.tests.test_harvest_closeout_v2 reference.tests.test_rc1_evidence_closeout` — the record and the closeout manifest
- `python scripts/validate_schemas.py` — the registry record against its schema
- `python -m unittest discover -s reference/tests -t reference` — the whole suite (runs in `Validate Doctrine Evidence`)
