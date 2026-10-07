# Plan: #732 independent currentness generalization gate (measurement against unchanged Runtime Baseline v5)

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #732 (parent #671; deficit `cross-fact-currentness-generalization-2026-10-07`, #733; machinery #719)
**owner direction in force (2026-10-07)**:
- The order is v5 B2, then this gate, then the #673 re-plan.
- The gate is a **decision gate**.
- The corpus, metrics, thresholds and holdout strategy are frozen independently of #673 and before any #732 remediation.
- The first measurement runs against the accepted Runtime Baseline v5 unchanged.
- No route fusion and no #673 behaviour enters the runtime before this measurement is accepted.
- G12 is not changed before this measurement.
- The thresholds are owner-ratified (G5).

**doctrine**: a benchmark identifies a gap but never defines the production grammar; a perfect benchmark score is not closure evidence; no tuning after any score
**iteration**: 4

**Gate history**:
- **Attempt 1: VETO (B1–B6).**
  - B1: the independence rule was neither enforceable nor auditable.
  - B2: the schema could not express a runnable case.
  - B3: the stage taxonomy had gaps.
  - B4: denominators and per-family classes were not pre-registered.
  - B5: the seed and exclusion rule were not frozen.
  - B6: the holdout was not single-use.
- **Attempt 2: VETO (C1–C6).**
  - C1: the orchestrator's user-role channels into the author were not audited, and the variant prompt was not frozen.
  - C2: MIXED could resolve vacuously, and one pre-freeze exclusion could foreclose PASS.
  - C3: S7 and S5 were not attributed to the newer write, so a distractor could turn N8 into a structural FAIL.
  - C4: G3b and G3c left choices open (query count, empty trigram sets, "valid", the variant schema, write order).
  - C5: the structural families were not structurally constrained.
  - C6: the deficit row was schema-invalid.

- **Attempt 3: VETO (E1–E2).**
  - E1: the audit's byte-equality rule did not match the harness's wrapper on coordinator messages, and the hand-back tool was not addressed.
  - E2: a missing must-change variant was a MIXED cause that no family carried.

The owner's thresholds were never in question. Iteration 3 fixed C1–C6 and D1–D9. Iteration 4 fixes E1–E2 and folds in advisories F1–F6.

**Frozen inputs.** Every text the orchestrator can send the author is committed under `reports/benchmarks/currentness-generalization/prompts/` (C1, D3). These files are canonical, and the appendices restate them. Their sha256 values are bound by the gate entry that passes this plan:

| File | sha256 |
|---|---|
| `brief.md` | `672cc56070b08441f0337f93f8ae2c83c5f7f30ee3a469db709b9fc9b2db6794` |
| `spawn.txt` | `bb9057ff55ec2a6ea6354483d81f28e0d921a32f811bb49fdc7e6cf3db0cbab3` |
| `variants.txt` | `52b3ca6b8129f2ba22e1cf2f3595750cd30033c3669a95f7e33e38c84a5493b7` |
| `replace.txt` | `4741ab43f902e90250c0a3d4f3d5dcc17bf0aeac9ee0666b6d979ae77d146ac8` |

## Purpose

#671 Option A scores 1.000 on MESA M4, with every win attributed to `currentness_mechanism`. Its G12 assertion filter evolved through seven gate rounds that were checked against MESA. The mechanism is inert on the `-v5` lanes, where 0 candidates were limited. Generalization is unmeasured.

This plan:
1. freezes an independent challenge;
2. runs it once against the unchanged v5 runtime;
3. maps the result to the owner's PASS/FAIL/MIXED fork.

## Decisions

**G1 — Independent authorship, enforceable and auditable (B1, C1, D1, D2).**
- **Authoring environment.** `author732-<n>/` sits in the session scratchpad. It is outside the repository and has no `.git`. Before the author starts it holds exactly one file: `brief.md`, byte-identical to the frozen `prompts/brief.md`. The subagent's recorded working directory is still the repository (D1), so containment comes from the tool rule, which `spawn.txt` restates against any mode reminder.
- **Author.** One fresh subagent. Its only inputs are four frozen prompts:
  - `spawn.txt`, with `{AUTHOR_DIR}` interpolated;
  - `variants.txt`, with `{AUTHOR_DIR}` and `{CASE_IDS}` interpolated;
  - `replace.txt`, with `{AUTHOR_DIR}` and `{REJECTIONS}` interpolated;
  - `brief.md`, which the author reads itself.

  The variant and replacement passes go to the same subagent by message. The orchestrator sends no other message.
- **Interpolations are mechanical only.**
  - `{AUTHOR_DIR}` is that attempt's absolute directory.
  - `{CASE_IDS}` is the compact JSON output of `scripts/select_metamorphic_bases.py` (G3c).
  - `{REJECTIONS}` is the compact JSON output of `scripts/check_generalization_corpus.py`, a list of `{id, file, rule}` (G3).
- **Tool rule.**
  - The only permitted tool calls are:
    - `Write` and `Read` on paths under `{AUTHOR_DIR}`;
    - at most one hand-back call per pass (`SubagentHandback`) whose entire input is `{"message": "done"}`. It carries no information inward. Ending a pass in plain text is equally valid (E1).
  - Any other tool call invalidates the attempt. That covers Bash, Grep, Glob, any read outside the directory, web, GitHub or other MCP tools, and agents.
  - An invalidated attempt is discarded. A new subagent starts in `author732-<n+1>/`, and the discarded attempt is recorded.
- **Audit** (`scripts/audit_authoring_transcript.py`, new). It runs over the subagent's `.jsonl` transcript and fails the attempt unless all of these hold:
  - (a) every assistant `tool_use` obeys the tool rule;
  - (b) every `type:"user"` record is exactly one of these (E1):
    - (1) a `tool_result`;
    - (2) a harness reminder: an `isMeta` record with no `origin.kind == "coordinator"`, whose entire content is one or more `<system-reminder>…</system-reminder>` blocks separated only by whitespace;
    - (3) a coordinator message: a record with `origin.kind == "coordinator"`, whose content equals `PREFIX + P + SUFFIX` byte for byte. Here `P` is the interpolated `variants.txt` or `replace.txt`, and its interpolated values equal the recorded script outputs and directory for that attempt. The harness wrapper is frozen as observed in the attempt-2 and attempt-3 tribunal transcripts:
      - `PREFIX` = `"The coordinator sent a message while you were working:\n"`;
      - `SUFFIX` = `"\n\nAddress this before completing your current task."`;
    - (4) the first record, as in (c).

    Anything else, including a coordinator record that does not match (3) and a reminder carrying a coordinator origin, invalidates the attempt.
  - **Wrapper drift.** If the harness wrapper differs from the frozen strings, the audit fails closed. The attempt is discarded, and the observed wrapper is reported to a tribunal before any new attempt. The rule is never loosened silently.
  - **Dry run.** The freeze PR includes a dry run of the audit on a throwaway subagent transcript. The throwaway subagent receives the frozen prompts interpolated with a dummy directory, and does no authoring.
  - (c) the first `type:"user"` record that is not a harness reminder is the interpolated `spawn.txt`, as a plain string without a coordinator origin.
- **Transcript binding (D2).**
  - The transcript is copied into the freeze PR under `reports/benchmarks/currentness-generalization/authoring/`, with its sha256.
  - The freeze tribunal runs in the same container. It hashes the live `~/.claude/projects/<session>/subagents/agent-<id>.jsonl` itself, compares the hash with the committed copy, and re-runs the audit.
- **Orchestrator role.** The orchestrator wrote G12 and authors **no** text. It runs the mechanical checks (G3, G3b) and sends `replace.txt` with their output. It sends `variants.txt` with the selection output. It does nothing else.
- **Brief content (D4).**
  - The brief contains:
    - #732's family lists, quoted;
    - the public interface;
    - the schema;
    - the structural rules (C5);
    - the label definitions.
  - It contains **no example case sentences** and nothing derived from G12, the runtime, MESA, tests or reports.
  - The positive definition, "directly … asserts that the value has **changed**", encodes the product contract that write order alone never limits. So the measured claim is **explicit change assertions**. A bare restatement of a new value is out of scope, and the report says so.

**G2 — Families and exact sizes.** The families are quoted from #732 and coded in `brief.md`.
- P1–P13 (`engage`): **12 cases each**, 156 in total.
- R1–R7 (`engage`): **8 each**, 56 in total.
- N1–N13 (`refrain`): **8 each**, 104 in total.
- **Structural-guard families:** N7, N8, N9, N10 and N13. **Non-structural:** N1–N6, N11 and N12.

**G3 — Runnable schema, mechanical checks and frozen harness (B2, C4, C5).**
- **Case schema.** Each case has exactly these fields:
  - `case_id`, `family`, `expected`;
  - `writes`: each `{handle, scope, target_reference, text, source_ref}`;
  - `older_write`, `newer_write`, `actions`: each `{action, write}`;
  - `recall_as`: `{handle, scope}`;
  - `query`, `rationale`.

**Mechanical checks.** These are implemented in `scripts/check_generalization_corpus.py`, and each rule name is emitted in `{REJECTIONS}`. They run on `corpus.json` and `variants.json` before the freeze.
- **`K1_fields`:** the exact field set and types.
  - `handle` is in {A, B} and `scope` is in {S1, S2}.
  - `action` is in {dispute, forget}.
  - Ids are unique, and `target_reference`s are unique within the case.
  - Indices are in range.
- **`K2_expected`:** P and R cases give `engage` and N cases give `refrain`. Variant `expected` must match its kind (C4).
- **`K3_order`:** `older_write < newer_write`.
- **`K4_recall_as_wrote`:** `recall_as` equals the `(handle, scope)` of at least one write.
- **`K5_structure_<family>`** (C5). This applies to base cases only (F3); variants are governed by K6.
  - "Same" compares the **effective** `source_ref`, where null means `actor:<actor_id of that write's handle>` (F1).
  - A non-null `source_ref` beginning with `actor:` fails `K1_fields` outright, so that an author cannot accidentally restate the implicit actor source.
  - **P, R, N1–N6, N11, N12:** older and newer have the same `handle`, `scope` and `source_ref`; `actions` is empty; `recall_as` is the older write's `(handle, scope)`.
  - **N7:** same `scope`; both `source_ref`s are non-null and different; `actions` is empty.
  - **N8:** same `handle` and `scope`; different `source_ref`; `actions` is empty.
  - **N9:** different `handle`; same `scope` and `source_ref`; `actions` is empty.
  - **N10:** different `scope`; same `handle` and `source_ref`; `actions` is empty.
  - **N13:** same `handle`, `scope` and `source_ref`; at least one action has `write == newer_write`.
- **`K6_variant_<type>`.** A variant is compared with its base. "Identical" means every field except `variant_id`, `base_case_id`, `variant_type`, `kind`, `expected` and `rationale`.
  - **Invariance types:** identical except the write texts and the query. At least one text differs.
  - **`hedge`, `attribution`, `conditional`, `coexistent`:** identical except the newer write's `text`, which must differ.
  - **`change_source_ref`:** identical except the newer write's `source_ref`, which must differ from the older write's.
  - **`change_actor`:** identical except the newer write's `handle`, which must differ from the older write's.
  - **`change_scope`:** identical except the newer write's `scope`, which must differ from the older write's.
  - **`dispute`:** identical except that `actions` equals the base's actions plus `{dispute, newer_write}`.
  - **Variant set completeness:** every selected base has all 14 types. `n/a` (`na_reason`, no other fields) is allowed only for invariance types.
- **`K7_g3b_overlap`:** the G3b rule, applied to cases **and** variants (D6).
- **Replacement, not exclusion (C2b).**
  - Every rejected record goes back to the same author in `replace.txt`.
  - There are at most 3 replacement rounds for the corpus, and then at most 3 for the variants.
  - A family still short after its rounds is recorded as `insufficient_pre_freeze` with the reasons.
  - A rejected variant still failing after its rounds counts as `n/a` (invariance) or as a missing must-change variant. Missing must-change variants are reported.
  - Pre-freeze rejection never silently shrinks a denominator.

**Frozen harness** (prototype verified by execution in the attempt-2 audit):
- **Identifiers.** A is `agent:gen732-a` and B is `agent:gen732-b`. S1 is `project:gen732-s1` and S2 is `project:gen732-s2`. The tenant is `tenant:gen732`, and the purpose is `currentness generalization (#732)`.
- **Opening.** `AgentMemory.open(root, tenant, actor_id, scope, purpose)`, with no other keyword arguments. Each case gets a fresh store. Each write opens and closes its `(handle, scope)` facade handle, in write order, on the same root.
- **Write.** `remember(target_reference, text, source_ref=…)`. The argument is omitted when `source_ref` is null.
- **Dispute.** `dispute(target_reference, fact_uuid=<that write's fact>, evidence=procedural_memory.evidence_for(skill:gen732-governed-dispute v1 scoped to the acting scope), risk_class="low")`.
- **Forget.** `forget(target_reference)`.
- **Recall.** As `recall_as`: `recall(query, temporal_intent={"mode": "current"}, reference_time="2026-10-08T12:00:00Z")`.

**G4 — Ordered stages, attributed to the newer write (B3, C3).**
- **Timing.** Immediately after the last write and **before any action**, the runner reads `write_semantics(uuid)` for the newer write and for every write other than the older and newer ones. Each read goes through that write's own `(handle, scope)` facade handle (F2).
- **Stages.** The first stage that applies is the case's stage:
  - **S0 `invalid_harness:<reason>`.** The reasons are:
    - `write_not_committed`;
    - `action_not_committed`;
    - `ambiguous_relation`: any write other than the newer write carries a write-time relation whose target is the older fact (C3). The brief requires distractors on unrelated topics.
  - **S1 `older_not_admitted`.**
  - **S2 `newer_not_admitted`.**
  - **S3 `no_write_time_relation`:** no relation from the newer fact to the older fact.
  - **S4 `relation_not_state_change`.**
  - **S5 `guard_refusal:<Gn>`:** `cross_fact_refusal_reason` on the older fact, mapped by Appendix B. Under S0 `ambiguous_relation`, the newer fact is the only possible source, so the refusal is the newer write's.
  - **S6 `labelled_not_reordered`:** the S7 label condition holds, but the newer fact does not rank above the older one.
  - **S7 `engaged`:** all of these hold:
    - the older fact's `temporal_applicability` is `limited_by_cross_fact_state_change`;
    - its `cross_fact_limitation` contains an entry with `source_fact_uuid` equal to the newer fact's uuid;
    - the newer fact ranks above the older one.
- **What counts as engagement.** Only S7 is "engage". S1 and S2 are retrieval misses, routed to retrieval (G7). For negatives, the refraining layer is reported: admission (S1/S2), write-time (S3/S4) or guard (S5).
- **Mechanism-off recompute.** Every case is recalled again under `cross_fact_mechanism_off.mechanism("off")` on the same store. A difference in admitted order between on and off, where no candidate carries `cross_fact_limitation`, is **unattributed** (M-attr).

**G5 — Metrics, denominators and thresholds (thresholds owner-ratified 2026-10-07, frozen).** Every denominator excludes S0. Metamorphic variants never enter recall or the false-engagement counts.
- **Overall recall:** a pooled micro rate. S7 cases over all valid **base** cases in P1–P13 and R1–R7.
- **Family recall:** S7 over the family's valid base cases. "Every positive semantic family" means P1–P13 **and** R1–R7.
- **False engagements:** S7 base cases in N families, structural and non-structural counted separately.
- **M-inv:**
  - Denominator: applicable invariance variants whose **base is valid** (not S0) and which are not S0 themselves.
  - Numerator: those whose outcome (S7 or not) equals their base's.
  - Invariance variants of an S0 base are excluded and reported (C4).
  - The diagnostic M-inv over engaged bases is reported, and it gates nothing.
- **M-flip:** must-change variants that are not S0 and do not reach S7, over all must-change variants that are not S0. They are scored independently of the base's validity. A missing must-change variant (G3) is reported. If any are missing, PASS is not available.
- **M-attr:** the unattributed count, over bases and variants.

**Gate (owner-ratified, verbatim intent):**
- **PASS requires all of:**
  - overall recall ≥ 0.80;
  - recall ≥ 0.60 in every P and R family;
  - ≤ 1 false engagement in total across the non-structural N families;
  - M-inv ≥ 0.95;
  - M-attr = 0;
  - 0 structural-guard false engagements;
  - M-flip = 100%;
  - no family `insufficient`.
- **FAIL:** overall recall < 0.50, or any zero-tolerance violation (M-attr > 0, a structural-guard false engagement, M-flip < 100%).
- **MIXED:** everything else.

**Per-family classification (frozen):**
- **P and R:**
  - `supported`: recall ≥ 0.80;
  - `adequate`: 0.60 ≤ recall < 0.80;
  - `deficient`: recall < 0.60.
- **Non-structural N:** `safe` with 0 false engagements; `unsafe` with ≥ 1.
- **Structural N:** a false engagement is a gate FAIL.
- **Insufficient (C2b).** Any family with fewer valid base cases than its exact size, from `insufficient_pre_freeze` or from measurement-time S0, is **also** `insufficient`. The recall class is still reported.
- **M-inv mismatches** are attributed to the base's family. Metamorphic results feed only M-inv and M-flip.

**MIXED causes and their discharge (C2a).** Each MIXED result lists its causes. The causes, and the families that carry each, are:
- (i) a `deficient` P or R family: that family;
- (ii) an `unsafe` N family: that family;
- (iii) overall recall in [0.50, 0.80): every P and R family that is not `supported`;
- (iv) M-inv < 0.95: every family with at least one invariance mismatch;
- (v) an `insufficient` family: that family;
- (vi) a missing must-change variant (G3: still failing after its replacement rounds): the family of its base case (E2).

Each carried family is either **narrowed** or **remediated**:
- **Narrowed:** an owner decision recorded per family, which removes it from the supported product contract.
- **Remediated:** included in the next holdout.

Generalization is **qualified after MIXED only** when a single G6 holdout run satisfies **every** PASS criterion over the non-narrowed families. No criterion is waived. Narrowing is the only way to shrink the claim, and it is per family. Every cause (i)–(vi) names its carrying families, so no cause can be left without a family. When a (vi) family is remediated rather than narrowed, the holdout's variant pass must produce every must-change variant for that family's selected bases.

**G3b — MESA contamination check, frozen (B5, C4).**
- **Tokens.** Text is lower-cased and tokenised with the regex `[a-z0-9]+`.
- **Templates.** The reference set is the **15** texts of `CONFLICT_TEMPLATES` in `reference/run_semantic_route_ordering_report.py` at blob `745f789c` (5 old, 5 new and 5 queries), with `{old}` and `{new}` deleted.
- **Similarity.** For a pair of texts:
  - if both texts have at least 3 tokens, similarity is the Jaccard of their token-trigram sets;
  - otherwise, it is the Jaccard of their token sets (unigrams);
  - two empty sets have similarity 0.
- **Rule.** A record (case or variant) fails `K7_g3b_overlap` when any write text or its query has similarity ≥ 0.5 with any of the 15 texts. Failing records are replaced (G3), not excluded.
- **Reported only.** The maximum similarity against the `-v5` lane questions.

**G3c — Metamorphic selection, frozen (B5, C4).**
- **Eligible bases.** Selection runs after the corpus replacement rounds, over base cases that pass every check K1–K7 (schema-valid). Measurement-time validity is not knowable here, and its consequence is handled in G5.
- **Selection.** For each of the 20 P and R families, the 2 eligible cases with the smallest `sha256("plan-732-metamorphic-v1|" + case_id + "|" + writes[newer_write].text)` (hex, compared as strings) are selected, for 40 in total. A family with fewer than 2 eligible cases contributes what it has.
- **Script.** `scripts/select_metamorphic_bases.py` emits the sorted `case_id` list. That list is `{CASE_IDS}`.
- **Variant definitions.** The variant types, their schema and the `n/a` convention are frozen in `prompts/variants.txt` (Appendix A).

**G6 — Holdout, single-use (B6, D7).**
- **When it is written.** Only if a MIXED or FAIL outcome is followed by remediation or by a holdout re-measurement, and only after both of these:
  - every narrowing decision is recorded;
  - the remediation hypothesis is frozen. For an attempt that changes no runtime (a "null attempt"), the hypothesis is recorded as such.
- **Null attempts.** A null attempt is allowed **once**, and only when every MIXED cause other than (v) and (vi) has been narrowed. This prevents re-rolling an unchanged runtime.
- **Who writes it.** A new author under G1, using hash-identical frozen prompts. Its exact sizes cover only the non-narrowed families.
- **Contamination.** It passes G3/G3b and its replacement rounds. In addition, any holdout record whose G3b similarity function (any write text or query, against any write text or query) is ≥ 0.5 against any record of the measurement corpus **or any earlier burned holdout** fails `K8_holdout_overlap` and is replaced.
- **Single-use.** Each attempt is scored **once** on its own fresh holdout. A failed attempt's holdout is burned and never re-scored.
- **Acceptance requires all of:**
  - every G5 PASS criterion over the non-narrowed families;
  - `mesa-formal-v2` with M4 = 1.000, every win `currentness_mechanism`;
  - #580 and #584 unchanged;
  - the measurement corpus re-reported, for reporting only.

**G7 — Fork (owner direction, D9).**
- **PASS.** #673 may be re-planned on v5. #732's typed write-time migration continues as separately governed work.
  - A non-structural `unsafe` family that PASS tolerates (at most one false engagement in total) gets an open deficit row (G8).
  - It requires no gating action, and it is carried into #732's typed-semantics work.
- **FAIL.** #673 stays held. Failures are routed by stage:
  - S1 and S2 go to retrieval;
  - S3 and S4 go to write-time recognition (#596/#597);
  - S5 and S6 go to the read-path guards and typed semantics.

  Remediation is generic, and G12 is never expanded case by case. It is accepted only under G6.
- **MIXED.** The causes and the families that carry them are recorded per G5. #673 stays held until G6 accepts a holdout run over the non-narrowed families.

**G8 — Records and binding (C6, D8).**
- **Deficit rows.** Each MIXED cause family (i)–(vi), each FAIL-only cause, and each `unsafe` family under PASS adds one row. The FAIL-only causes are:
  - a structural false engagement: a `false_engagement` row for that N family;
  - M-flip < 100%: a `must_change_flip` row per base family with a variant reaching S7;
  - M-attr > 0: one `all:attribution` row;
  - overall recall < 0.50: the `recall` rows of every non-`supported` P and R family.

  The rows go to `reports/benchmarks/deficits/current.json`. Every value is pre-registered. The rows validate against `schemas/benchmark-deficit-ledger.schema.json` and pass `test_benchmark_deficit_ledger.py`.

| Field | Value |
|---|---|
| `deficit_id` | `cross-fact-currentness-generalization-2026-10-07:<family>:<metric>`, where `<metric>` ∈ {`recall`, `false_engagement`, `invariance`, `insufficient`, `missing_variant`, `must_change_flip`}; the M-attr row uses `<family>` = `all` and `<metric>` = `attribution` |
| `benchmark_profile` | `currentness-generalization-732 (corpus sha256 <first 12 hex>)` |
| `evidence_class` | `independent challenge corpus; deterministic public-facade harness; Runtime Baseline v5 unchanged` |
| `metric` | `engagement_recall`, `false_engagements`, `metamorphic_invariance`, `valid_case_count`, `must_change_variant_count`, `must_change_refrain_rate` or `unattributed_ranking_changes` |
| `direction` | `higher` (recall, invariance, counts, refrain rate) or `lower` (false engagements, unattributed changes) |
| `agent_memory` | the family rate rounded to 4 places, or the integer count |
| `adequacy_target` | `>=0.80` (recall; `>=0.60` floor stated), `0` (false engagements), `>=0.95` (invariance), or the exact size (count) |
| `gap` | null |
| `priority` | `P0` for a structural-guard false engagement and for `attribution`; `P1` for `deficient`, `unsafe`, `must_change_flip` and the overall-recall cause; `P2` for `adequate`, `invariance`, `insufficient` and `missing_variant` |
| `posture` | `architecture_gap`; `implementation_defect` for `attribution`; `evaluator_protocol_defect` for `insufficient` and `missing_variant` |
| `primary_stage` | the G4 stage most frequent among the family's non-S7 positive cases (or S7 for `unsafe`, structural false engagements and `must_change_flip`); for `insufficient`, `S0` when measurement-time S0 caused it, else null; for `missing_variant` and `attribution`, null; ties go to the lower stage number (F6) |
| `secondary_stages` | the other stages present, sorted |
| `evidence_refs` | `[<measurement report path>, "docs/plan-732-generalization-gate.md"]` |
| `owning_issue` | 732 |
| `replay_requirements` | `["single-use G6 holdout meeting every PASS criterion over non-narrowed families", "mesa-formal-v2 M4 = 1.000 with every win currentness_mechanism", "#580 and #584 unchanged"]` |
| `state` | `open` |
| `opened_at` | the classification PR's date |
| `closed_at` / `closure_evidence` | null and `[]` while the row is open |

  - **Narrowed family.** The row stays and changes to:
    - `posture: unsupported_deliberate_non_goal`;
    - `state: deliberate_non_goal`;
    - `closed_at`: the decision date;
    - `closure_evidence`: the owner's decision reference and the ledger entry.
  - **Parent row (D8).** `cross-fact-currentness-generalization-2026-10-07` is created by #733, the owner's PR. If #733 has not merged when the classification PR opens, the classification PR waits for it. The orchestrator does not author the parent row.
- **Report binding.** The measurement report binds:
  - the executing commit, with the checker PASS against v5;
  - `ASSERTION_FILTER_VERSION` 6.0.0;
  - ranking policy 3.3.0;
  - the corpus, variants, prompt-file and transcript sha256 values;
  - the scope statement from D4 ("explicit change assertions").
- **"Execute once."** This means one complete run.
  - A crash before any case is scored allows one re-run with identical inputs.
  - A crash after scoring has begun is recorded, and the run repeats in full with identical inputs. Both outputs are kept.

**G9 — Execution order.**
1. Gate this plan, with the prompt files and Appendix B.
2. Authoring under G1, followed by the check and replacement rounds, selection, variants, and variant rounds.
3. **Freeze PR**, containing:
   - the corpus, the variants and their hashes;
   - the transcript, its live-hash comparison and its audit;
   - the check, rejection and replacement logs;
   - the selection;
   - the runner and the scripts, with tests on a synthetic fixture only.

   The freeze PR is gated, and the checker reports PASS against v5.
4. Measure once on `main` and commit the bound report.
5. **Classify** in an acceptance PR: per family and per stage, with the causes, the fork outcome and the G8 rows. Nothing is re-scored or re-thresholded.

## Boundaries
- **Non-goals:**
  - any runtime change;
  - any G12 change;
  - remediation design;
  - #673;
  - LLM judging;
  - bare restatements of a new value without an explicit change assertion (D4).
- **Exclusions:**
  - no case edited after the freeze;
  - no threshold, rule, prompt or family changed after this gate;
  - the orchestrator authors no case or variant text.

## Open Questions
None. OQ1 (thresholds) was resolved by the owner on 2026-10-07.

## Appendix A — Frozen prompts

The canonical bytes are in `reports/benchmarks/currentness-generalization/prompts/` (hashes above). They are not restated here, so there is only one source of bytes (D3). Their content in summary:
- **`brief.md`:**
  - the behaviour under test, including the explicit change assertion;
  - the interface;
  - the coded family lists, quoted from #732;
  - the structural rules K3–K5, with distractors on unrelated topics;
  - the writing rules and exact schema;
  - notice of the variant and replacement passes.

  It has no example sentences.
- **`spawn.txt`:** the directory, an instruction to read the brief, and the tool rule restated, overriding any mode reminder.
- **`variants.txt`:**
  - the tool rule;
  - `{CASE_IDS}`;
  - the 6 invariance and 8 must-change definitions;
  - the `n/a` convention (invariance only);
  - the exact variant schema.
- **`replace.txt`:** the tool rule, `{REJECTIONS}`, and the replace-by-new-id rule.

## Appendix B — Refusal-string to guard table (frozen)

| `cross_fact_refusal_reason` | Guard |
|---|---|
| `not_explicit_current_profile` (never emitted, because G1 returns `{}`; kept for completeness, D5) | G1 |
| `relation_not_state_change` | G2 |
| `relation_basis_not_accepted` | G3 |
| `no_open_proposal` | G4 |
| `proposal_not_open:*` | G5 |
| `hedged_or_untrusted_claim` | G6 |
| `cross_fact_identity_unavailable` | G7 |
| `actor_mismatch` | G8 |
| `source_mismatch` | G9 |
| `scope_mismatch` | G10 |
| `contradictory_cross_fact_evidence` | G11 |
| `change_evidence_not_assertive:*` | G12 |
| `declared_clock_contradicts_direction`, `declared_clock_unconfirmed` | G13 |
| `target_has_temporal_basis`, `source_has_temporal_basis` | policy (C3) |
