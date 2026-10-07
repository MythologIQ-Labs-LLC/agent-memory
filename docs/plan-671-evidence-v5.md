# Plan: #671 C9 evidence — `-v5` same-harness lanes and the `mesa-formal-v2` replay for Runtime Baseline v5

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**parent plan**: docs/plan-671-cross-fact-currentness.md. Gate PASS at attempt 7 (Entry #100); implementation is Entry #104 (PR #726); `main` prints TRANSITION to v5 once #726 merges. This plan is the parent's C9, which pre-registered its shape.
**precedent**: docs/plan-644-lanes-v4.md (L1–L9); docs/plan-669-lanes-v3.md (IA1, IA2); the mesa-formal-v1 freeze (`reference/fixtures/benchmarks/agentmembench/mesa-formal-v1-freeze.json`)
**owner rulings in force**: `decision-671-currentness-mechanism` (Option A now, Option D next, never D inside A); `decision-671-same-source`; `decision-eval-credential`
**doctrine**: benchmark score != truth; a higher score without attribution is not acceptance; no tuning after any score
**iteration**: 1

## Purpose

`reports/runtime/baseline-v5-declaration.json` requires three pieces of acceptance evidence:
- the public Gauntlet probe;
- the lanes `longmemeval-s-retrieval-parity-v5` and `amb-precisionmembench-retrieval-v5`;
- the replay `mesa-formal-v2`.

v5 changes ranking policy 3.2.0 → 3.3.0 and nothing else at the identity level. The only behavioural change is the guarded cross-fact applicability label under explicit-current recall. The contract stays 1.5.0.

The evidence has to show two things:
- **(a) Attribution.** Every ranked-output change against v4 is caused by `cross_fact_limitation`. Nothing else moved.
- **(b) The pre-registered MESA M4 prediction**, scored by the frozen classifier.

A higher score without (a) and (b) is not acceptance.

## Decisions

**E1 — The `-v5` control rows: an attribution rule, not equality.**
- **The rows.**
  - LongMemEval: `agent_memory`, budget 50, both planes.
  - AMB: `agent-memory`, the case budget.
  - Both run the v5 runtime with the facade default and declare no `recall_control` or `semantic_retrieval`.
- **The rule, checked against the accepted `-v4` control of the same lane:**
  - any question (LongMemEval) or case (AMB) whose ranked output differs from `-v4` must have at least one admitted candidate in that recall carrying `cross_fact_limitation`;
  - every other question or case must equal `-v4` exactly, on the L1 fields of plan-644-lanes-v4 (LongMemEval: `ranked_top`, `metrics`; AMB: the 77-case field list).

  A difference without a limitation **blocks** v5 publication.
- **Reported, never gated:**
  - per-question up/down counts against `-v4`;
  - the LongMemEval knowledge-update slice;
  - `latest_gold_ranked_first`;
  - the AMB summary deltas.
- **Expected effect.** The prediction is recorded here before any score, so a small effect cannot later be presented as a finding.
  - The mechanism engages only under explicit-current intent. That means caller-declared intent, or query language the 1.1.0 interpreter classifies `query_language_explicit`.
  - It also needs an open write-time proposal between two admitted facts that pass G1–G13.
  - LongMemEval turn questions and AMB cases declare no intent, are mostly not phrased as explicit-current, and are rarely written as first-party change sentences.
  - The expected number of changed questions on each lane is therefore **small, possibly zero**. Zero satisfies the rule.

**E2 — Making attribution checkable: runner and bridge fields, recorded before any score.**
- **`reference/run_longmemeval.py`.** For the `agent_memory` backend, each question row records `cross_fact`:
  - `limited_count`: the number of admitted candidates carrying `cross_fact_limitation`;
  - `limited_item_ids`: their benchmark item ids, in rank order;
  - `refusal_counts`: a count per `cross_fact_refusal_reason`.

  The report records `cross_fact_summary`:
  - the questions with `limited_count > 0`;
  - the total of limited candidates;
  - aggregated refusal counts.

  The fields are read only from the facade's `ranking_evidence`. They do not change retrieval, and an older runtime records zeros. The runner blob changes and is named in the `-v5` lane.
- **`reference/amb_agent_memory_bridge.py`** (`BRIDGE_VERSION` 0.4.0).
  - The `agent-memory` provider writes a `cross-fact.jsonl` sidecar when `AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR` is set. It holds one record per retrieve call: `{call_index, query_sha256, limited_count, limited_document_ids, refusal_counts}`.
  - Its join rules follow L9 of plan-644-lanes-v4:
    - concurrency 1;
    - `call_index` contiguous;
    - adjacent duplicates refused;
    - blank-query cases are "no recall executed", with `retrieved_count == 0`, `resolution == {}` and an empty `context`.
  - Retrieval output is unchanged.
  - The `agent-memory-shadow` provider is kept, but no `-v5` row uses it.
- **Importers.**
  - `scripts/import_longmemeval_lane_evidence.py` refuses a `-v5` `agent_memory` run without per-question `cross_fact` records.
  - `scripts/import_amb_lane_evidence.py` copies and hashes the sidecar, refuses the import without it on the `-v5` `agent-memory` row, and joins it per case.
- **Attribution check.** `scripts/check_cross_fact_attribution.py` (new) takes the accepted `-v4` evidence and the imported `-v5` evidence for one lane and prints, per changed question or case, the limited ids or `UNATTRIBUTED`. Any `UNATTRIBUTED` result blocks acceptance.

**E3 — The other `-v5` rows.**
- **Lexical overlap, BM25 and Mem0** are re-executed. Lexical and BM25 must equal `-v4` exactly. Mem0 is expected to equal `-v4`; any difference, such as the four L1 ranked diffs Mem0 turn showed at `-v4`, is an environment finding, as it was there.
- **The `-v4` shadow rows (`agent_memory_shadow`, `agent-memory-shadow`)** become `status: "deferred"`, with the reason: "measured at `-v4` (jh-14 shipped); the next controller measurement belongs to T-controller-2's lanes".
- **Semantic rows** stay deferred, with their `-v4` reasons unchanged.
- **Scorecards.**
  - The `-v5` control replaces `-v4` in the scorecards' current Agent Memory row, as `-v4` replaced `-v3` (SOURCES in `scripts/build_benchmark_scorecards.py`).
  - Comparators keep the one-system-per-group rule (IA2).
  - `evidence_history` gains the `-v5` entries.

**E4 — Lane-file differences from `-v4`, exhaustive (tested).**
- **Top level:** `lane_id`, `status: "frozen"`, `frozen_on`, `owning_issue: 671`, `description`, `freeze_rationale`, `comparability.notes`.
- **`findings`:** the `-v4` acceptance finding is not carried forward (IA1). All other findings are unchanged.
- **Rows:**
  - executed rows become `frozen`, with `status_reason` removed;
  - the shadow rows are deferred per E3;
  - the control's `display_name` names the declared transition to Runtime Baseline v5.
- **`runtime_baseline_posture`** in every Agent Memory row is replaced as a whole: predecessor v4, `declared_successor` v5, the declaration path, and the declaration blob.
- **`comparability.not_comparable_to[0]`** describes the `-v4` relation as attribution-checked (E1), not equality.
- **LongMemEval only:**
  - the runner blob in `harness.source_blobs`, `evaluator.scorer` and `adapter.revision_rule`;
  - `execution.environment.dispatch_unit`: the `-v5` lane with backends `{agent_memory, lexical_overlap, mem0_explicit}`;
  - `execution.execution_identity_requirements` gains: "every `agent_memory` question carries a `cross_fact` record; no other row carries one".
- **AMB only:**
  - the bridge blob and `bridge_version 0.4.0` in `harness.source_blobs` and the control's `adapter.revision_rule`;
  - `execution.artifact_requirements` gains `cross-fact.jsonl` (the control row only);
  - `execution.execution_identity_requirements` gains the E2 join line.
- **Both:** the workflows' `lane_id` choice gains the `-v5` id and becomes the default.
  - `amb-competitive.yml` sets `AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR` for `agent-memory` only.
  - `longmemeval-competitive.yml` needs no change beyond the lane id.

**E5 — `mesa-formal-v2`: a successor freeze, not an edit.**
- **The freeze.** `reference/fixtures/benchmarks/agentmembench/mesa-formal-v2-freeze.json` copies v1 field for field except:
  - `freeze_id`: `agent-memory-agentmembench-mesa-formal-v2`;
  - `supersedes`: v1's id and sha256 (v1 is never edited);
  - `frozen_on` and `status`;
  - `run_id`: `agent_memory_formal_v2_s2027_9170`;
  - **`agent_memory`**: `runtime_tree` is the `reference/agentmem_ref` tree at the `main` revision that merged #726, `ranking_policy_version` is `3.3.0` and `public_contract_version` is `1.5.0`;
  - **`runner.sha256`**: the runner's new blob, per the next bullet;
  - **`predictions`**: E6.

  The upstream revision, harness sha, dataset sha, arguments, phases, judge identity, deviations (D1–D3), stop lines and classifier version are **unchanged**.
- **The one runner change.** The parent plan said the runner would be unchanged, but `reference/run_agentmembench_formal.py` hard-codes `FREEZE_PATH` to v1. It gains a `--freeze` argument that defaults to v1, so the v1 replay stays reproducible byte for byte. The runner's sha changes; that is recorded as an amendment of the parent plan. `classify_conflict_case` and every frozen classifier constant are byte-identical: a test pins the sha256 of the function's source and the `CURRENTNESS_STAGES`, `RELEVANCE_STAGES` and `RELEVANCE_STAGE_PREFIXES` tuples.
- **The `_DEMOTED` binding.** The classifier credits `temporal_applicability_tier` through `ranking_policy._DEMOTED`, which now contains `limited_by_cross_fact_state_change`. That is the C3 design, not a classifier change.
- **The judge (M2).** The judge stays unprovisioned (#706, credential blocker), so deviation D1 holds and `recall_at_k` stays absent, exactly as in v1. M2's deterministic diagnostics are reported. M4 is exact containment and needs no judge.
- **Execution.** It runs on the verified upstream checkout, at a clean `main` revision whose runtime tree equals the freeze. The runner refuses on mismatch. Outputs:
  - `reports/benchmarks/agentmembench-mesa-formal/agent_memory_formal_v2_s2027_9170.json`, committed and linked-only;
  - the raw report, uncommitted.

**E6 — The pre-registered MESA prediction (frozen in the v2 freeze before the replay).**
- **Basis.** The prediction comes from v1's committed M4 classification (50 `new_fact`, all `lexical_ordering`; 200 `stale`, primary stage `temporal_applicability_currentness`) and from the #671 ordering-difference report. That report used the five upstream conflict templates with synthetic values: 250/250 pairs limited, top-1 new 50 → 250.
- **The prediction:**
  - **P1:** `outcomes.new_fact == 250`, `stale == 0`, `dual_version_rate == 0.0`;
  - **P2:** `win_basis_counts == {"currentness_mechanism": 250}`. No win is attributed to `lexical_ordering`, `temporal_order_tiebreak`, `content_identity_tiebreak` or a semantic route; the preference category's 50 wins move from `lexical_ordering` to `currentness_mechanism`;
  - **P3:** `primary_stage_counts == {}`, with no unmet stage on any pair;
  - **P4:** a pair that fails any C2 guard keeps its v1 classification. With P1, this predicts no such pair. Any that exists is listed with its guard by the C7 report shape, run over the replay's own M4 traces;
  - **P5:** `upstream_consistency.consistent == true`;
  - **P6:** M1, M3, M5 and M6 are reported against v1 with deltas.
    - Retrieval-phase queries carry no explicit-current language, so M1's deterministic diagnostics (retrieval digests) are predicted equal to v1.
    - Isolation, deletion, concurrency and scale outcomes are predicted equal to v1.
    - Latency is reported, not compared.
- **Outcomes.**
  - If the replay misses **P1–P3**, it is recorded as a finding. v5 is not published on that evidence, and nothing is tuned: any remedy is a new plan.
  - If **P6** shows a difference, it is recorded and attributed, and it blocks only if it is unattributed.

**E7 — Execution and acceptance (after this plan's PR merges, on `main`).**
- **Lanes.**
  - LongMemEval: `agent_memory`, `lexical_overlap` and `mem0_explicit` on both planes (6 runs).
  - AMB: `agent-memory`, `bm25` and `mem0-explicit` (3 runs).
  - Import through `amb-evidence-import.yml`. A re-dispatch is allowed only for an infrastructure failure before any score, with identical inputs.
- **MESA.** The `mesa-formal-v2` replay, locally on the verified checkout, at the `main` revision named in the freeze.
- **Acceptance.** E1 (attribution check), E3, E4 and E6, recorded as one ledger entry with the attribution output and the classifier output. The deficits ledger entry `mesa-m4-currentness` (ADR-043) cites v2.
- **Publication.** docs/67 Step B1 for v5:
  - the record, boundary, qualification and `.md`;
  - the Gauntlet manifest and adapter (`PUBLIC_CONTRACT_VERSION` 1.5.0);
  - the register entry, and the predecessor block copied from the declaration.

  Step B2 then binds the probe artifact.
- **#671 closes** at B2. #673 is re-planned after that, using the VETO lessons, with no post-score tuning.

## Boundaries

- **non_goals:**
  - Option D;
  - any runtime change (the runtime is frozen at #726);
  - semantic default-on;
  - controller enforcement;
  - judge provisioning (#706).
- **exclusions:**
  - no change to the upstream harness, dataset, arguments or classifier logic;
  - no gold-aware transformation;
  - no temporal enrichment in any lane or replay;
  - no budget change;
  - no tuning after any score;
  - no edit to `-v4` lanes, the v1 freeze or v4 records.

## Open Questions

None. Same-source and the Option A/D split are ruled. The judge credential stays a recorded blocker for M2 recall only.
