# Plan: #669 — semantic vector route reachable through the public facade (Runtime Baseline v3 declared)

**change_class**: feature
**doc_tier**: standard
**risk_grade**: L2
**research_artifact**: docs/research-brief-north-star-six-tranches-2026-10-06.md (Finding A: the vector seam is unreachable from the facade); roadmap `fact-vector-route-seam`, `fact-baseline-capability-inventory-drift`
**roadmap**: `.qor/roadmaps/north-star-best-in-class` scope `scope-tranche-1-vector-route` (nodes `fact-vector-route-seam`, `fact-baseline-mechanism`, `decision-embedding-dependency` resolved seq 49, `prereq-lane-v3-ids`)
**owner rulings in force**: `decision-embedding-dependency` (pinned, versioned local provider behind the existing abstraction, shipped as an optional extra), `decision-capacity-split`, `decision-temporal-posture`
**baseline**: Step A of docs/67 for Runtime Baseline **v3** (the register shows v2 published, `declared_successor: null`)
**evidence that orders this tranche**: formal MESA (docs/69). M2 answer-substring 0.728 vs Naive RAG 0.794 and source text 0.899 vs 0.971, against dense verbatim retrieval. LongMemEval_S lane v2 turn-plane recall_all@50: 0.859 for Agent Memory vs 0.895 for Mem0 (dense MiniLM).
**iteration**: 3 (attempt-1 VETO grounds 1-9 addressed in "Iteration 2 changes"; attempt-2 VETO grounds A2-1..A2-3 and advisories addressed in "Iteration 3 changes")

## Problem (verified on `main` 728d01d)

- `runtime/vector_retrieval.py` defines `VectorRepresentationProvider`, `VectorRepresentationSpec` and `NativeVectorCandidateRetriever`. `ConfiguredCompositionRuntime.__init__/create` accepts `vector_retriever` (runtime_composition.py:357, :382, :391).
- `SQLiteConfiguredCompositionRuntime.create/recover` (sqlite_composition.py:16-45), the only class `AgentMemory.open` uses (surface.py:282-350), never accept or forward one. **No facade recall has ever run the semantic route**, yet baseline-v2.json:164 records `semantic_vector_retrieval: native_qualified`.
- The only providers are test fixtures (test_native_vector_retrieval.py:107; test_retrieval_quality_benchmark.py:39).
- `NativeVectorCandidateRetriever.search` (vector_retrieval.py:158-195) has two defects that ship today:
  - it re-embeds **every fact on every query**, which `decision-embedding-dependency` and #669 forbid;
  - it does not apply the domain-eligibility prefilter that the lexical route applies through `eligible_search` (adapter.py:150-170, runtime_composition.py:173-176). It filters only `group_id == tenant`, so domain-ineligible facts could appear in `candidates` (contract 1.3.0 declares candidates domain-eligible) before admission refuses them.

## Iteration 2 changes (gate attempt 1: VETO on nine grounds)

| Ground | Disposition |
| --- | --- |
| 1 LD8 identity rows break the checker/validator | **Dropped.** No new `IDENTITY_SOURCES` rows in this tranche. The only identity delta is `identity.ranking.active_policy_version` 3.1.2 → 3.2.0, an existing row (test_runtime_baseline_succession.py:271 already models this delta). Representation identity is bound per candidate in `route_provenance` (representation_ref/version/config_digest) and by `semantic_retrieval_posture()`. An `introduced_in` mechanism for new identity rows is a follow-up. |
| 2 LD4 eligibility | **Fixed.** The vector route receives exactly `adapter.domain_eligible` (the predicate `eligible_search` receives at runtime_composition.py:173-176). Validity is left to admission. A test proves explicit historical-intent vector candidates are admitted. The Problem statement is corrected. |
| 3 `auto` default is environment-dependent | **Default is `off`.** `semantic_retrieval="off"` is the facade default in this tranche, so no installed file or environment variable changes recall for an unchanged caller. `"auto"` and `"required"` are explicit opt-ins. Evidence runs use `"required"`. Default-on is deferred to #673, after fusion is designed and analysed against #584. |
| 4 cosine before temporal stages | **Policy 3.2.0: the semantic route is ordering-subordinate** (LD7). |
| 5 MESA successor cannot run on the frozen runner | **Removed from acceptance.** A `mesa-formal-v2` runner/freeze is a separate evaluation item. Any local MESA run here is labelled diagnostic. |
| 6 lane work under-specified | **Moved out.** The `-v3` lanes get their own plan (`prereq` for Step B1). This PR declares v3 with `acceptance_evidence_required` naming the public gauntlet probe and the lane ids the follow-up freezes. |
| 7 tokenizer/numerics | **Fixed** (LD1/LD3). |
| 8 CI never exercises the provider | **Fixed.** New workflow `semantic-representation.yml` (LD10). |
| 9 store integrity | **Fixed** (LD3). |

## Iteration 3 changes (gate attempt 2: VETO on three grounds)

**A2-1 — BM25 statistics scope.**
- `rank()` builds admitted-set BM25 statistics from every admitted fact (ranking_policy.py:524-534). Under 3.2.0 the statistics are computed only over admitted candidates with **at least one non-subordinate route hit**.
- `identity()` reports `lexical_relevance_statistics_scope: "admitted_set_primary_routes"` when `subordinate_routes` is non-empty, and keeps `"admitted_set"` otherwise.
- Test: adding semantic-only admitted candidates leaves every lexical candidate's `lexical_relevance_score` byte-identical, and the lexical order unchanged.

**A2-2 — The MESA v1 freeze test.**
- `reference/tests/test_agentmembench_formal.py:278-282` asserts that the live policy equals the v1 freeze. It is re-scoped to assert that the freeze's `agent_memory` block equals the **Runtime Baseline v2** values read from `reports/runtime/baseline-v2.json` (policy 3.1.2, contract 1.4.0). This is a deliberate historical-binding change.
- From this PR on, the v1 freeze binds a historical runtime. `run_agentmembench_formal.py` refuses on the live tree by design, and replays run at `7b041a7` (docs/69 "Determinism").
- The freeze file and the runner are not edited.

**A2-3 — The exact re-pin list.**
- Only these assertions change, and only version strings or stage names/positions:
  - test_post_admission_ranking_policy.py:117, :120-128 (the stage slice positions shift by the subordinate stage), :133, :231;
  - test_query_conditioned_applicability.py:268;
  - test_temporal_order_constraints.py:65, :264;
  - test_temporal_unknown_basis_ordering_contract.py:46, :62 (`test_all_active_recall_planners_share_policy_312_boundary` is renamed to `..._share_policy_boundary`, and its assertion becomes 3.2.0 for all three active planners);
  - test_agentmembench_formal.py:278-282 (A2-2);
  - docs/44:100 prose.
- The #584 contract fixture's historical `ranking_policy` 3.1.1 dependency is unchanged.
- **Re-pinning any other assertion, or any ordering assertion in these files, is a blocker.**

**Advisories applied.**
- Golden vectors: the CI check compares against pinned float32 vectors with `max |Δ| ≤ 1e-6`, plus identical top-k order on a fixed 12-sentence mini-corpus. A byte sha256 is recorded alongside as informational, with `platform.machine()` and the CPU flags.
- `subordinate_routes=()` keeps `PostAdmissionRankingPolicy.identity()` byte-identical, so base 3.1.1 identities do not move. A test covers this.
- The subordinate stage name is added to the `_pre_temporal_key` stop set (temporal_order_constraints.py:324-327).
- The ordering-difference report explicitly covers two cases:
  - an applicable semantic-only candidate outranking a demoted lexical candidate, because the tier stage comes first;
  - #584 edges lifting a semantic-only winner.
- Full manifest digests:
  - `onnx/model.onnx` `826501e8460f6e1a83fa30a9b173f051100abda5559e1352efc0e3fe3136afc2`
  - `tokenizer.json` `7fa9272f7ef1ebd1666bb3bfd9d4707660ff0076ca9d1671cd9a9c6e18e03331`
  - `config.json` `953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41`
  - `modules.json` `84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf`
  - `1_Pooling/config.json` `4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23`
  - `sentence_bert_config.json` `ec8e29d6dcb61b611b7d3fdd2982c4524e6ad985959fa7194eacfb655a8d0d51`
- The extra pins `onnxruntime==1.30.0` and `tokenizers==0.23.2` with `numpy>=1.26,<3`. The exact `numpy==2.4.6` pin lives in `reference/requirements-semantic.txt` for CI. The numpy version is part of `config_digest`, so a different numpy is a different representation identity, not silent drift.
- The declaration description states that `controlled-multi-route` and `query-driven-relational` report 3.2.0 with unchanged behaviour (class-level version).

## Locked Decisions

**LD1 — Pinned ONNX provider, `runtime/representation_onnx.py`.**
- The manifest pins model `sentence-transformers/multi-qa-MiniLM-L6-cos-v1` at revision `b207367332321f8e44f96e224ef15bc607f4dbf0`, with these files and sha256:
  - `onnx/model.onnx` `826501e8…afc2`
  - `tokenizer.json` `7fa9272f…3331`
  - `config.json` `953f9c0d…8b41`
  - `modules.json`
  - `1_Pooling/config.json` `4be450dd…`
  - `sentence_bert_config.json` `ec8e29d6…`
- Pooling (`pooling_mode_mean_tokens: true`) and Normalize are asserted from those files at load, not only in code.
- Tokenization: `truncation max_length = 512` set explicitly, matching `sentence_bert_config.json` and the sentence-transformers behaviour of the Mem0 row. The pinned tokenizer.json's own `max_length 250` and fixed padding to 250 are overridden. No padding for single-text encoding.
- ONNX Runtime: `CPUExecutionProvider`, `intra_op_num_threads = inter_op_num_threads = 1`, `graph_optimization_level = ORT_ENABLE_BASIC`, all set explicitly.
- Outputs are mean-pooled over the attention mask, L2-normalized, then **canonicalised to float32**. Vectors are returned as float32-rounded Python floats on every path.
- `config_digest` = sha256 of the canonical JSON of:
  - the file digests;
  - truncation, padding, pooling, normalize;
  - the optimization level and thread counts;
  - the `float32` canonicalisation flag;
  - the `onnxruntime`, `tokenizers` and `numpy` versions.
- Determinism is claimed per library versions and CPU instruction set. A golden test (LD10) pins the sha256 of the float32 vectors for fixed texts in the declared CI environment.
- File digests are re-verified on every provider construction (every `open`).

**LD2 — Explicit fetch only.**
- `python -m agentmem_ref.runtime.representation_onnx fetch [--dir D]` downloads exactly the pinned files at the pinned revision.
- Each file goes to a temporary file in `D` and is renamed atomically after its sha256 verifies.
- Downloads are capped at the manifest size plus 1%. Symlinked targets and existing non-regular files are refused.
- `D` defaults to `$AGENT_MEMORY_REPRESENTATION_DIR`, else `~/.cache/agent-memory/representations/multi-qa-MiniLM-L6-cos-v1-b207367`.
- No network I/O happens at open, recall or restart.

**LD3 — Derived vector store with integrity, `runtime/representation_cache.py`.**
- Location: `<root>/derived/vectors-<config_digest[:16]>.sqlite`, created with mode 0600 inside the durable root's trust boundary (the same boundary as the canonical SQLite file). Backup, copy and restore may omit it; it is rebuilt on demand.
- Rows: `(fact_uuid, content_sha256, vector BLOB, row_sha256)`, where `row_sha256` = sha256(config_digest ‖ fact_uuid ‖ content_sha256 ‖ vector bytes).
- A row whose checksum fails is treated as a miss, recomputed and rewritten, and the event is counted.
- A `meta` row binds the full `config_digest`. On mismatch the file is discarded and rebuilt.
- `python -m agentmem_ref.runtime.representation_onnx verify --root R` recomputes every row and reports mismatches. `--rebuild` rewrites the store.
- `semantic_retrieval_posture()` reports `store_rows`, `checksum_failures_since_open` and the last verify result.
- The store is never canonical and never authority. Cached vectors equal recomputed vectors because of the float32 canonicalisation; a test covers this.

**LD4 — Eligibility.**
- `NativeVectorCandidateRetriever.search(..., eligible=None, store=None)` skips facts where `eligible(fact)` is False before embedding.
- The planner passes `lambda fact: self.adapter.domain_eligible(fact, context)`.
- Validity, invalidity and expiry are not filtered in the route. Admission decides them, as it does for lexical candidates, including explicit historical and as-of intent.
- Without `store`, the existing O(N) embed path remains for direct callers.

**LD5 — Facade wiring.**
- `AgentMemory.open(..., semantic_retrieval="off", representation_dir=None)`, with values `"off"` (default) | `"auto"` | `"required"`.
- `"auto"` enables the route when the extra imports and a verified model directory resolves; otherwise it stays off and records the reason. `"required"` raises `RepresentationUnavailable`.
- `SQLiteConfiguredCompositionRuntime.create/recover` gain `vector_retriever` and forward it.
- `AgentMemory.semantic_retrieval_posture()` (read-only) returns status, mode, reason, the spec fields, the store path and the integrity counters, with `authority_effect: none`.
- The doctor/posture schema is unchanged.

**LD6 — Extra.**
- `pyproject.toml` gains `semantic = ["onnxruntime==1.30.0", "tokenizers==0.23.2", "numpy>=1.26,<3"]` (iteration 3; exact numpy pin in the CI constraints file).
- Transitive dependencies of `onnxruntime` (`protobuf`, `flatbuffers`, `coloredlogs`, `sympy`, `packaging`) are pinned in the workflow constraints file `reference/requirements-semantic.txt`, not in the extra. The extra pins the three packages that determine numerics; the constraints file pins the CI environment.

**LD7 — Ranking policy 3.2.0: the semantic route is ordering-subordinate.**
- `PostAdmissionRankingPolicy` gains `subordinate_routes: tuple[str, ...] = ()`. A subordinate route:
  - contributes candidates;
  - is excluded from `route_corroboration_count` and from the primary `route_score_desc:*` stages;
  - is recorded in `ranking_evidence.subordinate_route_scores`;
  - orders only through a stage `route_score_desc_subordinate:<route>` placed **after** `temporal_order_within_query_regime` and before the stable fallback.
- Consequences:
  - The temporal applicability tier, lexical relevance and newer-first ordering keep exactly their 3.1.2 meaning and order.
  - `_neutralize_unknown_ties` (temporal_order_constraints.py:319-363) groups on the unchanged pre-temporal key.
  - Semantic-only candidates (lexical score 0) rank after lexical matches and are ordered among themselves by similarity.
- `MULTI_ROUTE_RANKING_POLICY` becomes `route_score_order=(SHARED_EVIDENCE_ROUTE, LEXICAL_ROUTE)` with `subordinate_routes=(SEMANTIC_VECTOR_ROUTE,)`. `POLICY_VERSION` becomes 3.2.0 (temporal_order_constraints.py:47, the existing identity row).
- `query-driven-relational` is unchanged apart from the version string. `controlled-multi-route` (#644, not facade-reachable) keeps its stage order; its version string moves with the class. #644 owns that decision.
- **With the route off, 3.2.0 orders identically to 3.1.2.** A test compares rankings over the #580/#584/M4 fixtures with the route off. With the fixture provider on, the same fixtures are run, and every ordering difference is listed in the PR. Any explicit-current expectation that flips is a blocker, not a re-pin.
- `minimum_similarity` for the facade retriever is 0.30 with `vector_candidate_limit` 16. It is recorded in posture. The rationale: MiniLM cosine below about 0.3 is near-random relatedness. The value is a declared parameter, not tuning, and #673 re-examines it.

**LD8 — Succession (v3 declaration).**
- `reports/runtime/baseline-v3-declaration.json`: issue 669, predecessor v2.
- `identity_deltas`: `[identity.ranking.active_policy_version 3.1.2 → 3.2.0]`.
- `pyproject_change`: `{"reason": "optional extra 'semantic' (decision-embedding-dependency)"}`.
- `acceptance_evidence_required`: the public gauntlet probe, plus lanes `longmemeval-s-retrieval-parity-v3` and `amb-precisionmembench-retrieval-v3` (frozen by the follow-up lane plan before Step B1).
- The declaration's description states that the facade default is `off`, so existing stores do not change ranking on recover unless a caller opts in.
- New modules are `git add`ed before `declare_runtime_baseline_changes.py` runs, and the checker must print `TRANSITION`.

**LD9 — Acceptance evidence in this PR.**
- (a) LD10 tests.
- (b) The retrieval-quality CI and the continuous-regression `vector_persistence_claimed False` (retrieval_regression.py:379) stay true: the default is off.
- (c) The ordering-difference report from LD7.
- (d) A local LongMemEval_S diagnostic run with `semantic_retrieval="required"`, if the dataset downloads at its pinned digest. It is labelled diagnostic.
- Formal lane rows and MESA are follow-ups.

**LD10 — Tests and CI.**
- `test_representation_onnx.py`:
  - manifest and pooling assertions;
  - tamper refusal;
  - truncation at 512;
  - float32 canonicalisation;
  - a golden sha256 of the vectors for three fixed texts;
  - `RepresentationUnavailable` without the extra.
- `test_representation_cache.py`:
  - miss then hit;
  - cached equals recomputed;
  - checksum failure is recomputed;
  - config mismatch rebuilds;
  - the file is 0600;
  - `verify` reports a tampered row.
- `test_native_vector_retrieval.py`: domain-ineligible facts never become candidates; event-invalid facts are candidates admitted only under historical intent.
- `test_post_admission_ranking_policy.py`: the 3.2.0 subordinate stage order; route-off equivalence with 3.1.2.
- `test_developer_facade.py`:
  - the default is off and identical to v2;
  - `"required"` raises without a model;
  - `"auto"` records the reason;
  - with the fixture provider, the semantic route appears in `route_provenance` and admission is unchanged.
- Model-dependent tests skip when the model is absent, **unless `AGENT_MEMORY_REQUIRE_REPRESENTATION=1`**, which turns skips into failures.
- New workflow `.github/workflows/semantic-representation.yml`:
  - runs on pull_request for the touched paths and on push to main;
  - concurrency `cancel_superseded`, timeout 20 minutes, `full_suite_passes` 0;
  - registered in `data/github-actions-workflow-policy.json` and the inventory;
  - installs `.[semantic]` with `reference/requirements-semantic.txt`;
  - fetches the model by digest with `actions/cache` keyed on the manifest digest;
  - sets `AGENT_MEMORY_REQUIRE_REPRESENTATION=1`;
  - runs the four test modules.

## Boundaries

- **limitations:**
  - an O(N) scan over cached vectors (no ANN index yet; the store makes it embedding-free per query);
  - CPU only;
  - English-trained model;
  - no score fusion (#673).
- **non_goals:**
  - currentness (#671, held on an owner ruling);
  - a reranker;
  - changing the doctor or posture schema;
  - changing `_profiles/rc1-local.json`. The capability declaration of a representation component in the runtime configuration schema is a follow-up (#410) recorded in the v3 record's limitations.
- **exclusions:**
  - no network at open, recall or restart;
  - no embedding stored as canonical state;
  - no change to admission, scope, PAMA, lifecycle or tombstone semantics;
  - similarity is never currentness, truth, scope, permission or authority.

## Open Questions

None blocking. Two defaults are flagged:

1. **Default `off`.** #669 asks for default-on. That is deferred to #673, because default-on ordering needs fusion analysed against #584. This tranche makes the route reachable and qualified, but opt-in.
2. The doctor posture schema stays closed. Route status is exposed by a new read-only method, not inside the posture report.

## Steps

1. LD1–LD7 and LD10, with the full suite green.
2. LD8: declaration and register, `declared_changes`, `TRANSITION`.
3. LD9 (c) and (d).
4. Ledger entry, PR, merge commit.
5. Follow-ups:
   - a `-v3` lane plan, then Step B1/B2;
   - a `mesa-formal-v2` runner and replay;
   - an `introduced_in` identity mechanism;
   - #673 default-on and fusion.
