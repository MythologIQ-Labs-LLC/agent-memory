# Plan: #669 — semantic vector route reachable through the public facade (Runtime Baseline v3 declared)

**change_class**: feature
**doc_tier**: standard
**risk_grade**: L2
**research_artifact**: docs/research-brief-north-star-six-tranches-2026-10-06.md (Finding A: the vector seam is unreachable from the facade); roadmap `fact-vector-route-seam`, `fact-baseline-capability-inventory-drift`
**roadmap**: `.qor/roadmaps/north-star-best-in-class` scope `scope-tranche-1-vector-route` (nodes `fact-vector-route-seam`, `fact-baseline-mechanism`, `decision-embedding-dependency` resolved seq 49, `prereq-lane-v3-ids`)
**owner rulings in force**: `decision-embedding-dependency` (pinned, versioned local provider behind the existing abstraction, shipped as an optional extra), `decision-capacity-split`, `decision-temporal-posture`
**baseline**: Step A of docs/67 for Runtime Baseline **v3** (the register shows v2 published, `declared_successor: null`)
**evidence that orders this tranche**: formal MESA (docs/69). M2 answer-substring 0.728 vs Naive RAG 0.794 and source text 0.899 vs 0.971, against dense verbatim retrieval. LongMemEval_S lane v2 turn-plane recall_all@50: 0.859 for Agent Memory vs 0.895 for Mem0 (dense MiniLM).
**iteration**: 1

## Problem (verified on `main` 728d01d)

- `runtime/vector_retrieval.py` defines `VectorRepresentationProvider`, `VectorRepresentationSpec` and `NativeVectorCandidateRetriever`. `ConfiguredCompositionRuntime.__init__/create` accepts `vector_retriever` (runtime_composition.py:357, :382, :391).
- `SQLiteConfiguredCompositionRuntime.create/recover` (sqlite_composition.py:16-45), the only class `AgentMemory.open` uses (surface.py:282-350), never accept or forward one. **No facade recall has ever run the semantic route**, yet baseline-v2.json:164 records `semantic_vector_retrieval: native_qualified`.
- The only providers are test fixtures (test_native_vector_retrieval.py:107; test_retrieval_quality_benchmark.py:39).
- `NativeVectorCandidateRetriever.search` (vector_retrieval.py:158-195) has two defects that ship today:
  - it re-embeds **every fact on every query**, which `decision-embedding-dependency` and #669 forbid;
  - it applies **no domain eligibility**: it filters only `group_id == tenant` and does not skip event-invalid or transaction-expired facts. Under contract 1.3.0 `candidates` are domain-eligible (docs/44), while the lexical route uses `eligible_search` (adapter.py:150-170).

## Locked Decisions

**LD1 — One pinned ONNX representation provider, `runtime/representation_onnx.py`.**
- `PINNED_MINILM_L6_COS_V1` is a frozen manifest:
  - model `sentence-transformers/multi-qa-MiniLM-L6-cos-v1`, revision `b207367332321f8e44f96e224ef15bc607f4dbf0`, the same model and revision the Mem0 lane row uses (amb_mem0_explicit_bridge.py:43-45);
  - files and sha256: `onnx/model.onnx` `826501e8…afc2`, `tokenizer.json` `7fa9272f…3331`, `config.json` `953f9c0d…8b41`;
  - 384 dimensions; mean pooling over the attention mask, then L2 normalization (the upstream `modules.json` is Transformer → Pooling (mean) → Normalize); max sequence length 512.
- `OnnxSentenceEmbeddingProvider(model_dir)`:
  - imports `onnxruntime` and `tokenizers` lazily and raises `RepresentationUnavailable` if either is missing;
  - verifies every file digest before loading, failing closed on a mismatch;
  - runs one `InferenceSession` with `intra_op_num_threads = inter_op_num_threads = 1` on `CPUExecutionProvider` for determinism;
  - `embed(text)` returns a 384-tuple of floats.
- `spec`:
  - `representation_ref = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1@b207367"`;
  - `representation_version = "onnx-mean-l2/1.0.0"`;
  - `config_digest` = sha256 of the canonical JSON of the manifest plus the `onnxruntime` and `tokenizers` versions, so a numerics-relevant library change is a new representation identity;
  - `deterministic_rebuild = True`.
- Similarity stays retrieval evidence (`authority_effect: none`).

**LD2 — The model is never fetched implicitly.** `python -m agentmem_ref.runtime.representation_onnx fetch [--dir D]` downloads exactly the three pinned files from `https://huggingface.co/<model>/resolve/<revision>/<file>`. It verifies each sha256 before an atomic rename into `D`, which defaults to `$AGENT_MEMORY_REPRESENTATION_DIR` or `~/.cache/agent-memory/representations/multi-qa-MiniLM-L6-cos-v1-b207367`. Recall, open and restart perform no network I/O.

**LD3 — A derived, rebuildable vector store, `runtime/representation_cache.py`.**
- `DerivedVectorStore(path, spec)` lives in `<root>/derived/vectors-<config_digest[:16]>.sqlite`, a separate file outside the canonical SQLite generation.
- Table `vectors(fact_uuid TEXT, content_sha256 TEXT, vector BLOB, PRIMARY KEY(fact_uuid, content_sha256))`, with float32 little-endian vectors and a `meta` row binding the full `config_digest`. On a meta mismatch or unreadable file, the store is discarded and rebuilt.
- It is never canonical and never authority. Deleting it changes no recall result, only latency. Vectors are recomputed deterministically (LD1), and a test proves cached vectors equal freshly computed ones.
- Lookup is by `(fact_uuid, sha256(fact_text))`. A corrected fact is a new uuid; a tombstoned or invalid fact is skipped by LD4 before lookup.
- Rows are written only for missing keys. A query embeds the query text plus only the facts not yet cached; there is no per-query re-embedding of the corpus.
- Writes happen under the handle's serialization lock, because recall already holds it (sqlite_composition.py:77-97).

**LD4 — The vector route applies the same domain eligibility as the lexical route.**
- `NativeVectorCandidateRetriever.search` gains keyword-only `eligible: Callable[[Fact], bool] | None = None` and `store: DerivedVectorStore | None = None`.
- It skips facts with `is_event_invalid` or `is_transaction_expired`, and facts for which `eligible(fact)` is False, **before** embedding.
- `DeterministicMultiRouteRecallPlanner.recall` passes `eligible=lambda fact: self.adapter.domain_eligible(fact, context)`, the same predicate as `eligible_search` (runtime_composition.py:186-189).
- Without `store`, the old O(N) embed path remains for direct callers (tests and the retrieval-quality fixture), so existing fixture tests keep passing.
- Every candidate still crosses the single governed admission boundary.

**LD5 — The facade wiring: `AgentMemory.open(..., semantic_retrieval="auto", representation_dir=None)`.**
- `"auto"`: if the extra is importable and a verified model directory resolves (argument, then environment, then default cache), build the provider, store and retriever and pass them to `SQLiteConfiguredCompositionRuntime.create/recover`, which gain a `vector_retriever` keyword forwarded to `ConfiguredCompositionRuntime`. Otherwise run lexical-only and record the reason.
- `"off"`: never enabled.
- `"required"`: raises `RepresentationUnavailable` instead of degrading.
- `AgentMemory.semantic_retrieval_posture()` (new, read-only) returns `{"status": "enabled"|"disabled", "mode", "reason", "representation": spec fields | null, "store": path | null, "authority_effect": "none"}`. The doctor posture schema is unchanged; a closed-schema change is a separate contract decision.
- The facade default becomes "on when installed and fetched". Base installs and CI without the extra keep today's exact behaviour (the reason is recorded as `extra_not_installed` or `model_not_present`).

**LD6 — The optional extra.** `pyproject.toml` `[project.optional-dependencies]` gains `semantic = ["onnxruntime==1.30.0", "tokenizers==0.23.2", "numpy>=1.26,<3"]`, exact-pinned as in `comparators`. The base dependency list is unchanged.

**LD7 — Ranking is unchanged in code; the change is declared as v3.**
- `MULTI_ROUTE_RANKING_POLICY` already orders `route_score_order = (semantic_vector, shared_evidence, lexical)` after corroboration and exact identity (runtime_composition.py:119-125). Enabling the route therefore changes ordering wherever it runs.
- No policy constant changes. Fusion and calibration are #673. The observable change is declared as Runtime Baseline v3:
  - `reports/runtime/baseline-v3-declaration.json`: issue 669, predecessor v2;
  - `identity_deltas` for the new identity rows (LD8);
  - `pyproject_change: {"reason": "optional extra 'semantic' for the pinned ONNX representation provider (decision-embedding-dependency)"}`;
  - `acceptance_evidence_required`: the public gauntlet probe, the `-v3` lanes (LD9) and the MESA successor replay;
  - the register's `declared_successor` points at v3;
  - `declared_changes` is produced by `scripts/declare_runtime_baseline_changes.py` after the last protected edit, and the checker must print `TRANSITION`.
- Merge with a merge commit (docs/67 Step A.5).

**LD8 — Identity sources.** `scripts/runtime_baseline_identity.py` `IDENTITY_SOURCES` gains:
- `identity.semantic_representation.ref`, `.revision` and `.version`, read from constants in `runtime/representation_onnx.py`;
- `identity.semantic_retrieval.default_mode`, read from the facade default in `api/surface.py`.

The v3 record (Step B1) carries them, and they are validated by `validate_runtime_baseline_source.py`.

**LD9 — Acceptance evidence.**
- (a) Unit and conformance tests (LD10).
- (b) Retrieval-quality CI is unchanged. It runs without the extra, and its frozen numbers and `vector_persistence_claimed False` stay true for the lexical profile.
- (c) A local MESA successor replay. A successor freeze copies the v1 freeze with only the `agent_memory` block changed: new runtime tree, `semantic` packages and an `AGENT_MEMORY_REPRESENTATION_DIR` binding. It reports per-axis deltas and M4 `win_basis`. An M4 change is reported as whatever `win_basis` says, never as currentness capability.
- (d) New lane ids `longmemeval-s-retrieval-parity-v3` and `amb-precisionmembench-retrieval-v3`, frozen in this PR per docs/plan-640 LD6, with workflows that install `.[semantic]` and fetch the pinned model by digest. They are dispatched after merge for Step B1, with the Mem0 row re-run for parity.
- (e) A LongMemEval_S local run with the v3 runner configuration, if the dataset downloads at its pinned digest. It is diagnostic until the lane row is accepted.

**LD10 — Tests.**
- `test_representation_onnx.py`: manifest digests; refusal on a tampered file; determinism (the same text gives a byte-identical vector); dimension and norm; `RepresentationUnavailable` without the extra. Model-dependent cases are skipped only when the model directory is absent, and the skip reason is stated.
- `test_representation_cache.py`: miss then hit; cached equals recomputed; config-digest mismatch triggers a rebuild; deleting the file changes no recall result.
- `test_native_vector_retrieval.py` additions: ineligible, invalid and expired facts are never vector candidates; candidates are domain-eligible.
- `test_developer_facade.py` additions: `semantic_retrieval="off"` behaves exactly as v2; `"required"` without the model raises; `"auto"` without the model records the reason and degrades to lexical; with the fixture provider injected, the vector route appears in `route_provenance`, every candidate is admitted or refused by the same admission, and nothing outside the domain appears.
- The frozen #584, #580, MESA-formal and lane tests keep passing.

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

1. `auto` as the facade default. #669 asks for default-on with an explicit opt-out; the owner ruling makes the dependency optional. `auto` satisfies both.
2. The doctor posture schema stays closed. Route status is exposed by a new read-only method, not inside the posture report.

## Steps

1. LD1–LD6 and LD10, with the full suite green.
2. LD7–LD8: declaration and register, `declared_changes`, `TRANSITION`.
3. LD9 (c) and (e) locally; (d) frozen.
4. Ledger entry, PR, merge commit.
5. Step B1/B2 in a follow-up after lane dispatch.
