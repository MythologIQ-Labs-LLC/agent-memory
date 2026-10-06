# Plan: #670 — governed return budget on recall results, contract `1.4.0`

**change_class**: feature
**doc_tier**: standard
**risk_grade**: L2
**research_artifact**: docs/research-brief-north-star-six-tranches-2026-10-06.md (Finding C, Recommendation 4; ledger Entry #60; research gate `2026-10-06T1200-668ns/research.json`, gitignored)
**roadmap**: `.qor/roadmaps/north-star-best-in-class` scope `scope-tranche-3-budget` (handoff recorded on the resolved facts `fact-facade-return-shape` and `fact-ranking-attachment`)
**baseline**: the first runtime tranche under the successor-baseline procedure (`docs/67-runtime-baseline-succession.md`, PR #676): this PR declares Runtime Baseline v2 and merges in a pinned transition; publication of v2 is a later Step B1/B2
**iteration**: 2 (attempt-1 VETO V1-V2, C1-C4, A1-A4 amended; Entry #65; Shadow Genome Failure #15)

**terms**:
- term: return budget
  home: docs/44-public-api-contract.md
- term: return policy
  home: docs/44-public-api-contract.md

**boundaries**:
- limitations: the budget is a count `k` applied to the ranked admitted prefix after admission and after ranking; it never changes which facts are admissible, current, or visible, and `admitted` keeps carrying the full ranked admitted set, so nothing a `1.3.0` caller sees is removed. No score cutoff is offered: under ranking policy 3.1.2 route scores are declared not cross-comparable (`route_scores_cross_comparable` is `False`, research brief Finding B), so a cutoff has no meaning until the fusion stage (#673) exists. The default is unbudgeted: a recall with no `budget` returns exactly what it returns today plus the two additive fields; a budgeted default would change every lane control number and is a separate ruling (Open Question 1).
- non_goals: changing the runtime package (`runtime/`, `memory/`, `core/`, `state/`): the budget is a facade fact on the api layer and the `RecallContext` the runtime receives is unchanged; #670's third scope item (the LongMemEval and AMB bridges and the AgentMemBench runner reading the budget from the result, and the lanes recording it) is deferred to `prereq-lane-v3-ids`, so **this PR does not close #670**: `reference/run_longmemeval.py` is byte-pinned by the LongMemEval lane's `source_blobs` and `test_same_harness_lane.py:360-378`, while `reference/amb_agent_memory_bridge.py` and `reference/run_agentmembench.py` are only recorded at execution; all three stay unchanged here because a budgeted bridge changes the control's execution identity and therefore needs the new lane ids, not because a test forbids the edit; publishing Runtime Baseline v2 (Step B1/B2 of docs/67, after this merge); a score cutoff; the audit event (`memory.recall`, runtime/adapter.py:837-860) which records admission and is a runtime fact.
Grep-evidence for `reference/tests/test_same_harness_lane.py:360`:
`git show origin/main:reference/tests/test_same_harness_lane.py | grep -nE 'def test_lane_binds_the_runner_and_bridge_blobs_it_freezes' -> 360:    def test_lane_binds_the_runner_and_bridge_blobs_it_freezes(self):`
- exclusions: `reference/agentmem_ref/runtime/**`, `memory/**`, `core/**`, `state/**`, `_profiles/**` unchanged; `pyproject.toml` unchanged; the v1 baseline files unchanged; `candidate_policy`'s shape unchanged (it stays "how candidates were formed; no identifiers, no counts"); `admissions`, `candidates`, `admitted` unchanged in meaning and content; `reference/fixtures/api/recall-context.example.json` unchanged (`1.0.0`, an older minor that stays `current`).

## Open Questions

None blocking. Three defaults are taken and flagged for the owner:

1. **Default budget.** `budget` absent means unbudgeted (`returned == admitted`, `applied: false`). A default `k` would change the control numbers of both accepted lanes and the AgentMemBench figures, and belongs to a new lane id; the facade keeps today's default.
2. **`return_policy` beside `candidate_policy`, not inside it.** #670 says "recorded in `candidate_policy`"; the intent (a report can state what was returned and why) is met by a sibling object, and `candidate_policy` keeps the single meaning docs/44 gives it (candidate formation, no counts). Folding counts into it would make one object carry two stages.
3. **Acceptance lane ids in the declaration.** The declaration names `amb-precisionmembench-retrieval-v2` and `longmemeval-s-retrieval-parity-v2` as the lanes v2 publication must bind; those ids are frozen by the `prereq-lane-v3-ids` work, which reads `returned` under the case budget (AMB) and stays unbudgeted at k ≤ 50 (LongMemEval).

## Locked Decisions

**LD1 — Contract `1.4.0` is additive: one optional input, two result fields.** `schemas/api-recall-context.schema.json` and `schemas/api-result-envelope.schema.json` (and their byte-identical packaged copies under `reference/agentmem_ref/_schemas/`, which `core/receipts.py` resolves when the source tree is absent) add `"1.4.0"` to the `contract_version` enum (context :14-21, envelope :14-21). The context schema gains an optional closed object `budget: {"k": integer, minimum 1}` (`additionalProperties: false`, `required: ["k"]`). The result envelope gains `returned: array of string` and a closed `return_policy` object with required `policy_id` (`const "ranked-prefix-return-budget"`), `policy_version` (`const "1.0.0"`), `requested_k` (`integer ≥ 1` or `null`), `applied` (boolean), `admitted_count` (integer ≥ 0), `returned_count` (integer ≥ 0), `basis` (`const "post_admission_ranking_prefix"`), `authority_effect` (`const "none"`). `api/contract.py` `CONTRACT_VERSION = "1.4.0"` (:21); `compatibility()` is unchanged, so `1.0.0`–`1.4.0` envelopes are `current` and `1.5.0` is `MIGRATION_REQUIRED`. `recall_context_from_envelope` (:113-120) is unchanged: `RecallContext` never learns about the budget and the runtime receives the same context it receives today.
Grep-evidence for `reference/agentmem_ref/api/contract.py:21`:
`git show origin/main:reference/agentmem_ref/api/contract.py | grep -nE '^CONTRACT_VERSION' -> 21:CONTRACT_VERSION = "1.3.0"`
Grep-evidence for `schemas/api-recall-context.schema.json:19`:
`git show origin/main:schemas/api-recall-context.schema.json | grep -nE '"1\.3\.0"' -> 19:        "1.3.0"`
Grep-evidence for `schemas/api-result-envelope.schema.json:20`:
`git show origin/main:schemas/api-result-envelope.schema.json | grep -nE '"1\.3\.0"' -> 20:        "1.3.0"`

**LD2 — The return policy is one pure function in `api/contract.py`.** `apply_return_budget(ranked_admitted: Sequence[str], k: int | None) -> tuple[list[str], dict]` returns `(list(ranked_admitted)[:k] if k is not None else list(ranked_admitted), return_policy)` with `return_policy = {"policy_id": "ranked-prefix-return-budget", "policy_version": "1.0.0", "requested_k": k, "applied": k is not None and k < len(ranked_admitted), "admitted_count": len(ranked_admitted), "returned_count": len(returned), "basis": "post_admission_ranking_prefix", "authority_effect": "none"}`. It reads only the ranked admitted list; it never sees `admissions`, `candidates` or the runtime result, so it cannot change an admission. Constants `RETURN_POLICY_ID` and `RETURN_POLICY_VERSION` live beside `CONTRACT_VERSION`. `k` is validated by the schema before the function runs (`k ≥ 1`); the function raises `ValueError` on `k < 1` as a defensive statement, which no public path can reach.
Grep-evidence for `reference/agentmem_ref/api/contract.py:136`:
`git show origin/main:reference/agentmem_ref/api/contract.py | grep -nE '^def result\(' -> 136:def result(stage: str, compat: str, **fields: Any) -> dict:`

**LD3 — Both recall entry points apply the policy after admission and after ranking, and always return `returned` and `return_policy`.** Module-level `surface.recall(memory, query, context_envelope)` (:98-106) reads `k = validated.get("budget", {}).get("k")` and, since `GovernedMemoryAdapter.governed_recall` returns `admitted` in admission order with no ranking stage, applies the policy to `admission.admitted` (documented in docs/44 as "ranked prefix where ranking ran; admission order otherwise"). `AgentMemory.recall(...)` (:691-757) gains the keyword `budget: int | None = None`, adds `"budget": {"k": budget}` to the envelope only when `budget is not None` (so a `1.3.0`-shaped envelope stays byte-identical for unbudgeted calls), and applies the policy to `result.ranked_admitted`. Both pass `returned=` and `return_policy=` to `contract.result`; `admitted` stays the full list. The `memory.recall` audit event is unchanged.
Grep-evidence for `reference/agentmem_ref/api/surface.py:98`:
`git show origin/main:reference/agentmem_ref/api/surface.py | grep -nE '^def recall\(' -> 98:def recall(memory: GovernedMemoryAdapter, query: str, context_envelope: Mapping[str, Any]) -> dict:`
Grep-evidence for `reference/agentmem_ref/api/surface.py:691`:
`git show origin/main:reference/agentmem_ref/api/surface.py | grep -nE '^    def recall\(' -> 691:    def recall(`

**LD4 — This PR declares Runtime Baseline v2 and merges in a pinned transition.** `reports/runtime/baseline-v2-declaration.json`: `baseline_id` `agent-memory-runtime-baseline-v2`, predecessor v1, `issue` 670, `identity_deltas` `[{"identity_path": "identity.public_contract_version", "from": "1.3.0", "to": "1.4.0"}]`, `pyproject_change: null`, `acceptance_evidence_required` `[{"kind": "public_gauntlet", "ref": "gauntlet-orchestration-retrieval-probe-v1"}, {"kind": "lane", "ref": "amb-precisionmembench-retrieval-v2"}, {"kind": "lane", "ref": "longmemeval-s-retrieval-parity-v2"}]`, and `declared_changes` written by `python scripts/declare_runtime_baseline_changes.py --declaration reports/runtime/baseline-v2-declaration.json` after the last protected edit: exactly `reference/agentmem_ref/_schemas/api-recall-context.schema.json`, `reference/agentmem_ref/_schemas/api-result-envelope.schema.json`, `reference/agentmem_ref/api/contract.py`, `reference/agentmem_ref/api/surface.py` (four blobs; `schemas/*.json` are outside the protected paths). `reports/runtime/baseline-register.json` sets `declared_successor` to `{"baseline_id": "agent-memory-runtime-baseline-v2", "declaration": "reports/runtime/baseline-v2-declaration.json"}`. The PR is merged with a **merge commit** (the repository allows squash and rebase too; docs/67 Step A.5 requires a merge commit so the declared blobs survive the merge, and the PR body says so). The checker then prints `Runtime Baseline equivalence: TRANSITION; baseline=agent-memory-runtime-baseline-v1; declared_successor=agent-memory-runtime-baseline-v2 (issue #670); protected surface = frozen f2aef57293b516e065cad5d0afea26ac7e3c28a9 + 4 declared blobs; deltas=identity.public_contract_version 1.3.0->1.4.0; candidate=HEAD`, the validator prints `declared successor agent-memory-runtime-baseline-v2 (issue #670) is open`, and the three revision-claiming workflows skip their evidence steps with a transition notice. The v1 Gauntlet adapter keeps `PUBLIC_CONTRACT_VERSION = "1.3.0"` (it is v1's and is not run during the transition); the v2 adapter copy is a Step B1 artifact.
Grep-evidence for `reference/agentmem_ref/runtime/adapter.py:138`:
`git show origin/main:reference/agentmem_ref/runtime/adapter.py | grep -nE '^def candidate_policy_evidence' -> 138:def candidate_policy_evidence() -> dict:`

**LD5 — Tests pin the new contract and prove the twelve shape-pinning modules unchanged.** `reference/tests/test_api_contract.py`: `test_compatibility_states` cases become `1.0.0`–`1.4.0` `CURRENT`, `1.5.0` `MIGRATION_REQUIRED` and the final assertion `CONTRACT_VERSION == "1.4.0"` (:51); new `test_apply_return_budget` (unbudgeted → same list, `applied` False, counts equal; `k` below the length → prefix, `applied` True; `k` at or above the length → full list, `applied` False; `k = 0` → `ValueError`); new `test_recall_context_accepts_budget_and_refuses_zero` (schema accepts `{"k": 1}`, refuses `{"k": 0}`, refuses `{"k": 1, "cutoff": 0.5}`); new `test_result_envelope_carries_return_policy` (the closed object validates with the exact key set and refuses an extra key or `authority_effect: "ranking"`). `reference/tests/test_api_surface.py`: new `test_recall_budget_returns_ranked_prefix_and_keeps_admitted`; the `PublicSurface` fixture seeds one fact (`setUp`, :59-63), so the test first commits a second fact on a second target (`{**EXAMPLE, "proposal_id": "proposal-second", "target_reference": "memory:second-release-branch"}`, text `"release branch second"`) and recalls `"release branch"`: `budget {"k": 1}` → `returned` has one element equal to `admitted[0]`, `admitted` has two, `return_policy` counts `2`/`1` with `applied` True; without `budget` → `returned == admitted`, `applied` False; `admissions` identical between the two calls. New `test_blocked_recall_under_budget_is_empty_not_truncated` on the domain-blocked path (:184-187): `budget {"k": 1}` with `target_domain_refs: ["org:elsewhere"]` → `candidates []`, `admissions {}`, `admitted []`, `returned []`, `return_policy` with `admitted_count 0`, `returned_count 0`, `applied` False (an empty budgeted result is distinguishable from a truncated one by `applied` and by the counts, and from `unsupported`/`blocked` by the stage and the empty `admissions`). New `test_migration_required_envelope_carries_no_return_fields`: a `1.5.0` envelope with `budget {"k": 1}` → `stage: "none"`, `compatibility: migration_required`, and neither `returned` nor `return_policy` present; an envelope with no `contract_version` → `unknown`, same absence. `reference/tests/test_rc_cognitive_memory_scenario.py`: the `1.3.0` literal at :17 (the report's `contract_version`, set from `memory.contract_version` at `reference/run_rc_cognitive_memory_scenario.py:173`) becomes `contract.CONTRACT_VERSION`, so the third version literal stops being a literal. `reference/tests/test_developer_facade.py`: `contract_version` becomes `"1.4.0"` (:54); new `test_recall_budget_is_a_facade_policy` (two facts remembered on two targets; `memory.recall(query, budget=1)` returns `returned` of length one and `return_policy` with `applied` True, `admitted` and `admissions` identical to the unbudgeted call, and `memory.recall(query, budget=0)` raises the schema `ValueError` before any runtime call). `reference/tests/test_api_dod20.py`: unchanged (`recall` stays a reader; a budgeted recall is recorded as the same single `governed_recall` call). The modules the brief lists as pinning the recall shape (test_api_history_posture, test_recall_authority_record, test_domain_eligibility_prefilter, test_post_admission_ranking_policy, test_retrieval_quality_benchmark, test_continuous_retrieval_regression, test_structural_mutation_governance, test_agentmembench) pass without edits because `admitted` is unchanged and none asserts an exact result key set; the three version literals (`test_api_contract.py:51`, `test_developer_facade.py:54`, `test_rc_cognitive_memory_scenario.py:17`) are the only existing-test edits (`grep -rn '"1\.3\.0"' reference/tests reference/*.py` outside the PAMA schema version and the succession fixture finds exactly these three). New `test_packaged_schema_copies_are_byte_identical` in `test_api_contract.py` asserts the two packaged copies equal the source schemas byte for byte. `reference/tests/test_benchmark_integration_contract.py` keeps passing through its `TRANSITION` acceptance (PR #676).
Grep-evidence for `reference/tests/test_api_contract.py:51`:
`git show origin/main:reference/tests/test_api_contract.py | grep -nE 'assertEqual\(contract.CONTRACT_VERSION, "1\.3\.0"\)' -> 51:        self.assertEqual(contract.CONTRACT_VERSION, "1.3.0")`
Grep-evidence for `reference/tests/test_developer_facade.py:54`:
`git show origin/main:reference/tests/test_developer_facade.py | grep -nE 'contract_version, "1\.3\.0"' -> 54:            self.assertEqual(memory.contract_version, "1.3.0")`

**LD6 — Documentation states the budget as policy, never authority.** `docs/44-public-api-contract.md`: status line adds `1.4.0` (#670, this plan); the stages table row for `recall` gains `returned` and `return_policy`; a new section "Return budget (contract `1.4.0`, #670)" after "Recall candidates" (:71-90) stating: the budget is an optional `k` on the recall context, applied to the ranked admitted prefix after admission and after ranking; `admitted` is always the full ranked admitted set; `returned` is the budgeted prefix (equal to `admitted` when unbudgeted); `return_policy` names the policy, the requested `k`, whether it truncated (`applied` means truncated: a requested `k` at or above the admitted count reports `applied: false`), and both counts; `authority_effect: none`; no score cutoff under 3.1.2 and why; module-level `recall` applies the prefix in admission order because the adapter path has no ranking stage; compatibility: additive minor, a `1.3.0` envelope receives a `1.4.0` result with the two new fields. `docs/FEATURE_INDEX.md` FX024 row: "current contract 1.4.0 … adds `returned` and `return_policy` to recall results" with `test_api_contract.py`, `test_api_surface.py`, `test_api_dod20.py`, `test_developer_facade.py` (totals unchanged, 26). `docs/GOVERNANCE_INDEX.md` Tier 4: this plan `ACTIVE`. `docs/67` is unchanged; this PR is its Step A worked once.
Grep-evidence for `docs/44-public-api-contract.md:71`:
`git show origin/main:docs/44-public-api-contract.md | grep -nE '^## Recall candidates' -> 71:## Recall candidates (contract \`1.3.0\`, #548)`

## Phase 1: contract `1.4.0` (schemas and the policy function)

### Affected Files

- `schemas/api-recall-context.schema.json`, `reference/agentmem_ref/_schemas/api-recall-context.schema.json` - `1.4.0` in the enum; optional closed `budget {k ≥ 1}`, LD1
- `schemas/api-result-envelope.schema.json`, `reference/agentmem_ref/_schemas/api-result-envelope.schema.json` - `1.4.0` in the enum; `returned`; closed `return_policy`, LD1
- `reference/agentmem_ref/api/contract.py` - `CONTRACT_VERSION = "1.4.0"`, `RETURN_POLICY_ID`, `RETURN_POLICY_VERSION`, `apply_return_budget`, `__all__`, LD2
- `reference/tests/test_api_contract.py` - version cases; the four new tests (budget function, context schema, envelope schema, packaged-copy identity), LD5

### Changes

Per LD1 and LD2. The two packaged copies are byte-identical to the source schemas (`diff -q` in the CI commands).

### Unit Tests

- `reference/tests/test_api_contract.py` - `test_compatibility_states` (1.4.0 current, 1.5.0 migration_required), `test_apply_return_budget`, `test_recall_context_accepts_budget_and_refuses_zero`, `test_result_envelope_carries_return_policy`.

## Phase 2: the two recall entry points

### Affected Files

- `reference/agentmem_ref/api/surface.py` - module-level `recall` reads `budget.k`; `AgentMemory.recall(..., budget=None)`; both return `returned` and `return_policy`, LD3
- `reference/tests/test_api_surface.py` - `test_recall_budget_returns_ranked_prefix_and_keeps_admitted`, `test_blocked_recall_under_budget_is_empty_not_truncated`, `test_migration_required_envelope_carries_no_return_fields`, LD5
- `reference/tests/test_developer_facade.py` - version literal; `test_recall_budget_is_a_facade_policy`, LD5
- `reference/tests/test_rc_cognitive_memory_scenario.py` - the literal at :17 reads `contract.CONTRACT_VERSION`, LD5

### Changes

Per LD3. No other function in `surface.py` changes; the envelope built by the facade for an unbudgeted call is unchanged.

### Unit Tests

- `reference/tests/test_api_surface.py` and `reference/tests/test_developer_facade.py` as in LD5; `test_api_dod20.py` unchanged and green.

## Phase 3: declaration, register, documentation

### Affected Files

- `reports/runtime/baseline-v2-declaration.json` - new, LD4
- `reports/runtime/baseline-register.json` - `declared_successor`, LD4
- `docs/44-public-api-contract.md` - status, stages row, "Return budget" section, LD6
- `docs/FEATURE_INDEX.md` - FX024, LD6
- `docs/GOVERNANCE_INDEX.md` - Tier 4 row, LD6

### Changes

Per LD4 and LD6. The declaration's `declared_changes` is written by the helper as the last step before commit, and re-run if any protected file is edited afterwards.

### Unit Tests

- `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` prints the exact `TRANSITION` line of LD4 (four declared blobs, one delta); `python scripts/validate_runtime_baseline_source.py` ends with the open-declaration line; `reference/tests/test_runtime_baseline_succession.py` and `test_benchmark_integration_contract.py` stay green.

## Definition of Done

### Deliverable: contract `1.4.0` with a governed return budget

- **D1**: a domain-blocked recall under a budget returns empty `returned` with `applied: false` and zero counts, and a `migration_required` or `unknown` envelope returns `stage: none` with neither field; a recall with `budget {"k": n}` returns `returned` as the ranked admitted prefix of length ≤ n and `return_policy` stating the policy, `requested_k`, `applied`, `admitted_count` and `returned_count`; `admitted`, `admissions` and `candidates` are identical to the unbudgeted call; an unbudgeted call returns `returned == admitted` and `applied: false`.

### Deliverable: the first declared transition under docs/67

- **D2**: the register declares v2, the declaration pins the four changed blobs and the one identity delta, the checker prints `TRANSITION` and the validator accepts the open declaration; the revision-claiming workflows skip their evidence steps and say why; the PR merges with a merge commit.

### Deliverable: the contract is documented as policy, never authority

- **D3**: docs/44 carries the "Return budget" section and the `1.4.0` status; FEATURE_INDEX FX024 and GOVERNANCE_INDEX are updated.

## Feature Inventory Touches

| entry_id | operation | test_path | test_descriptor |
|---|---|---|---|
| FX024 | MODIFIED | `reference/tests/test_api_contract.py` | contract `1.4.0`: `1.0.0`–`1.4.0` current, `1.5.0` migration_required; `apply_return_budget` is a pure ranked-prefix policy with `authority_effect: none`; the recall context accepts `budget {k ≥ 1}` and the result envelope carries `returned` and a closed `return_policy` |

## CI Commands

- `diff -q schemas/api-recall-context.schema.json reference/agentmem_ref/_schemas/api-recall-context.schema.json && diff -q schemas/api-result-envelope.schema.json reference/agentmem_ref/_schemas/api-result-envelope.schema.json` — packaged copies identical
- `python scripts/validate_schemas.py` — every schema still valid
- `python -m unittest reference.tests.test_api_contract reference.tests.test_api_surface reference.tests.test_developer_facade reference.tests.test_api_dod20 reference.tests.test_package_layout` — the edited modules and the layout table
- `python -m unittest discover -s reference/tests -t reference` — the full suite, 0 failures (the known local-only `test_proposition_evaluator` ancestry skip on a shallow clone aside)
- `python scripts/declare_runtime_baseline_changes.py --declaration reports/runtime/baseline-v2-declaration.json` — rewrites the four declared blobs; idempotent on a second run
- `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` — prints the LD4 `TRANSITION` line
- `python scripts/validate_runtime_baseline_source.py` — v1 validates; `declared successor agent-memory-runtime-baseline-v2 (issue #670) is open`
- `qor-logic governance-health --profile skill-entry` — green after the index edits
