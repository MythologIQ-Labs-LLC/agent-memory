# Plan: Runtime Baseline v6 evidence — `-v6` lanes, `mesa-formal-v3` (extractor off), B1/B2

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #732 (remediation plan `docs/plan-732-remediation.md`, Gate PASS Entry #116; implementation Entry #118, merged at #741 `e98e6e7`)
**declared transition**: v5 → v6 (`reports/runtime/baseline-v6-declaration.json`; acceptance evidence: the public Gauntlet probe, `amb-precisionmembench-retrieval-v6`, `longmemeval-s-retrieval-parity-v6` and replay `mesa-formal-v3`)
**precedent**: `docs/plan-671-evidence-v5.md` (E1–E9), whose machinery is reused unchanged unless stated
**iteration**: 1

## Purpose

v6 adds typed write-time propositions and an opt-in extractor. The extractor is **off** by default, and nothing in the lanes or MESA declares a typed proposition. So with the extractor off, v6 must be **observationally identical** to v5 on every same-harness workload.

The only differences allowed are version identity strings:
- ranking policy 3.4.0;
- assertion filter 6.1.0;
- contract 1.6.0.

This plan freezes that claim before any score and publishes v6 through docs/67, with the typed and extractor path marked **unaccepted** (remediation advisory V1).

## Decisions

**V6-E1 — The `-v6` rule is equality, not attribution.**
- **LongMemEval** (agent_memory, budget 50, both planes): every question's `ranked_top` and `metrics` equal the accepted `-v5` control.
- **AMB** (agent-memory): every case's `correct`, `context` and the nine `meta` fields equal the accepted `-v5` control.
- **Cross-fact records.** These are the existing E2 records: LongMemEval `cross_fact` and the AMB `cross-fact.jsonl` sidecar. They must equal `-v5` in `limited_count`, `limited_item_ids`/`limited_document_ids` and `refusal_counts`, with `-v5`'s 0 limited carried over.
- **The attribution script.** `scripts/check_cross_fact_attribution.py` is reused unchanged against `-v5` as the reference. Any result other than `EQUAL` (that is, `ATTRIBUTED` or `UNATTRIBUTED`) **blocks** v6 publication. It is stricter than v5 because no mechanism is expected to act.
- **Reported, never gated:** up/down counts and summary deltas, which must be zero.

**V6-E2 — Other `-v6` rows.**
- **Re-executed:** lexical overlap, BM25 and Mem0. Lexical and BM25 must equal `-v5` exactly. A Mem0 difference is an environment finding, as at `-v4` and `-v5`.
- **Deferred rows:** the shadow and semantic rows stay `deferred`. Their reasons gain one sentence: "ranking policy 3.4.0 and assertion filter 6.1.0 add only typed-basis branches that no lane input reaches; the next measurement belongs to #673's lanes".
- **Scorecards:** all 9 `-v6` sources are appended to `SOURCES` (append-only), and `evidence_history` grows.

**V6-E3 — Lane-file differences from `-v5`, exhaustive and tested field for field.** These follow plan-671-evidence-v5 E4, with `-v5` read as `-v4` and `-v6` as `-v5`:
- **Top level:** `lane_id`, `status`, `frozen_on`, `owning_issue: 732`, `description`, `freeze_rationale` and `comparability.notes`.
- **Findings:** the `-v5` acceptance finding is not carried forward.
- **Rows:**
  - executed rows are `frozen`;
  - deferred reasons follow V6-E2;
  - the control's `display_name` names the declared v6 transition.
- **`runtime_baseline_posture`:** predecessor v5, `declared_successor` v6, the declaration path and blob.
- **`comparability.not_comparable_to[0]`:** describes the `-v5` relation as **equality** (V6-E1).
- **Runner and bridge blobs:**
  - every occurrence of the `-v5` LongMemEval runner blob is replaced by the `-v6` runner blob, which is the same file if unchanged;
  - the AMB bridge blob and version are carried over unchanged (0.4.0).

  A test asserts the serialised lane holds exactly these strings.
- **Workflows:** the `lane_id` choice gains the `-v6` id and makes it the default. The AMB cross-fact sidecar env var is unchanged.

**V6-E4 — `mesa-formal-v3`: a successor freeze, extractor off.**
- **The freeze.** `reference/fixtures/benchmarks/agentmembench/mesa-formal-v3-freeze.json` is a new file; v2 is never edited. Relative to v2, these fields change, and they are listed and tested exhaustively:
  - `freeze_id`: `agent-memory-agentmembench-mesa-formal-v3`;
  - `owning_issue`: 732;
  - `supersedes`: `{freeze_id, path, sha256}` of v2;
  - `frozen_on` and `status`;
  - `run_id`: `agent_memory_formal_v3_s2027_9170`;
  - `adapter.surface`: "contract 1.6.0";
  - `adapter.ranking_policy`: "runtime default (multi-route-default 3.4.0 at freeze time); no variant; no proposition extractor";
  - `agent_memory.runtime_tree`: the `reference/agentmem_ref` tree at the freeze PR's base;
  - `agent_memory.ranking_policy_version` `3.4.0` and `public_contract_version` `1.6.0`;
  - `runner.sha256`: unchanged if the runner is unchanged;
  - `predictions`: V6-E5.

  Everything else is copied unchanged, including D1–D6, the upstream pins, arguments, phases, judge identity, stop lines and classifier version.
- **The runner.** `reference/run_agentmembench_formal.py` already takes `--freeze`, and no runner change is expected. If one is needed, its source-hash pins follow v5 E5, and the change is listed as an amendment before any score.

**V6-E5 — MESA confirmation (frozen in the v3 freeze before the replay).** v3 must reproduce v2 exactly:
- **P1:** `outcomes == {"new_fact": 250}`, and the upstream `dual_version_rate == 0.0`;
- **P2:** `win_basis_counts == {"currentness_mechanism": 250}`;
- **P3:** `primary_stage_counts == {}` and `unmet_stage_counts == {}`;
- **P5:** `upstream_consistency.consistent == true`;
- **P6:** M1 retrieval digests and the isolation, deletion, concurrency and scale non-latency fields all equal v2. Latency is reported only.

Missing any of P1–P3 or P5, or any P6 difference, blocks v6 publication. Nothing is tuned; a remedy would be a new plan.

The extractor-on MESA run is **not** part of this plan. It belongs to remediation R6, after the provider-freeze record.

**V6-E6 — Guards at the execution revision.**
- #584 M1–M15 and the #580 frozen labels are unchanged; the existing tests are re-run.
- The C7 ordering-difference report is regenerated with 0 blockers and M4 250/250 limited.

**V6-E7 — Sequencing.** Nothing writes into `reference/agentmem_ref` between the freeze and the replay.
1. **MESA PR:** the v3 freeze, the E8-style re-pins (the formal-runner test binds the v2 freeze to its historical record) and this plan's acceptance skeleton. It never touches `reference/agentmem_ref`.
2. **Replay** at the MESA PR's merge commit. Output: `reports/benchmarks/agentmembench-mesa-formal/agent_memory_formal_v3_s2027_9170.json`.
3. **Lanes PR:** the V6-E3 lane files, the workflows and the re-pins (`test_same_harness_lanes_v5.py` reads its committed evidence; the default `lane_id` regex is widened).
4. **Dispatch.**
   - LongMemEval: `agent_memory`, `lexical_overlap` and `mem0_explicit` on both planes (6 runs).
   - AMB: `agent-memory`, `bm25` and `mem0-explicit` (3 runs).
   - Imports go through the existing importers. A re-dispatch is allowed only for an infrastructure failure before any score.
5. **Acceptance,** in one ledger entry: V6-E1 (all EQUAL), V6-E2, V6-E3, V6-E5 and V6-E6.
6. **docs/67 Step B1 for v6:**
   - the record, boundary, qualification and `.md`;
   - the Gauntlet manifest and stdio adapter (`PUBLIC_CONTRACT_VERSION` 1.6.0);
   - the register entry;
   - the CONTRIBUTOR_ARCHITECTURE ranking text (3.3.0 → 3.4.0).

   The v6 record, `.md` and dashboard state that **the typed proposition and extractor path is unaccepted** until the remediation R6 acceptance PR. If acceptance fails, the next attempt needs a v7 declaration.
7. **Step B2** binds the probe from the `runtime-baseline.yml` run on the B1 PR head.

## Boundaries
- **Non-goals:**
  - any runtime change;
  - the extractor-on MESA run;
  - holdout work;
  - provider configuration;
  - #673.
- **Exclusions:**
  - no `-v5` lane is edited;
  - no v2 freeze is edited;
  - nothing is re-scored after any result.

## Open Questions
None.
