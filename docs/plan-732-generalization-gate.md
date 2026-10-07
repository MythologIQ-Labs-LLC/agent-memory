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
**iteration**: 2

**Gate history**: attempt 1 was a VETO with six blocking findings.
- **B1:** the independence rule was neither enforceable nor auditable.
- **B2:** the schema could not express a runnable case, and dispute without governance evidence would have made N13 an automatic FAIL.
- **B3:** the stage taxonomy had no class for a fact that is not admitted, and the write-time observation came too late.
- **B4:** denominators and the per-family classification were not pre-registered.
- **B5:** the metamorphic seed and the MESA exclusion rule were not frozen.
- **B6:** the holdout was not single-use.

The thresholds were not in question. Iteration 2 fixes all six and folds in advisories A1–A10. The authoring brief is now part of this plan (Appendix A), so it is gated before any corpus exists.

## Purpose

#671 Option A scores 1.000 on MESA M4, with every win attributed to `currentness_mechanism`. Its G12 assertion filter evolved through seven gate rounds that were checked against MESA. The mechanism is inert on the `-v5` lanes, where 0 candidates were limited. Generalization is unmeasured.

This plan:
1. freezes an independent challenge;
2. runs it once against the unchanged v5 runtime;
3. maps the result to the owner's PASS/FAIL/MIXED fork.

## Decisions

**G1 — Independent authorship, enforceable and auditable (B1).**
- **Authoring environment.** `/tmp/claude-0/…/scratchpad/author732/` is outside the repository and contains no `.git`. It holds exactly one input file, `brief.md`, which is Appendix A verbatim. Its sha256 is recorded in the gate entry that passes this plan.
- **Author.** A fresh subagent is started from that directory.
- **Tool rule.**
  - The only permitted tool calls are `Write` and `Read` on paths under `author732/`.
  - Any other tool call invalidates the corpus. That covers Bash, Grep, Glob, any read outside `author732/`, web fetches, GitHub or other MCP tools, and spawning agents.
  - An invalidated corpus is discarded, and a new author starts from a fresh directory. The discarded attempt is recorded.
  - The brief states this rule. The author never runs the runtime and never sees an outcome.
- **Audit trail.**
  - At hand-back, the author's full subagent transcript (`~/.claude/projects/<session>/subagents/<id>.jsonl`) is copied into the freeze PR, under `reports/benchmarks/currentness-generalization/authoring/`.
  - It is committed with its sha256, which is recorded in the ledger in the same commit.
  - `scripts/audit_authoring_transcript.py` (new) lists every `tool_use` input and fails if any input breaks the tool rule.
  - The freeze gate re-runs that audit.
- **Orchestrator role.** The orchestrator wrote G12 and does **not** edit case text. It may only run the mechanical schema checks in G3. A case that fails one is rejected with the check's name and goes back to the same author, which fixes it under the same tool rule. Each rejection is logged.
- **Brief content.**
  - #732's family lists are quoted verbatim, the public facade contract, the schema and the label definitions.
  - The brief contains **no example case sentences** and nothing derived from G12, the runtime, MESA, tests or reports.
  - Family names such as R3 and R4 come from the owner's issue text (A1). Knowledge of G12 shaped them, but that knowledge pushes results toward FAIL, not PASS, so they stay and are quoted verbatim.

**G2 — Families and exact sizes (A10).** The families are quoted from #732 in Appendix A.
- **Positive (`engage`).** P1–P13 hold the "legitimate capability families", **12 cases each** (156 in total).
- **Robustness (`engage`).** The adversarial-list items whose meaning is a legitimate change become R1–R7, **8 cases each** (56 in total):
  - R1 Unicode punctuation;
  - R2 alternate sentence order;
  - R3 legitimate lowercase multi-token values;
  - R4 non-location proper nouns;
  - R5 values whose capitalization is semantically irrelevant;
  - R6 punctuation variants;
  - R7 clear semantics in an unfamiliar surface form.
- **Negative (`refrain`).** N1–N13, **8 cases each** (104 in total):
  - N1 quoted third-party claims;
  - N2 forwarded text;
  - N3 sarcasm or jokes;
  - N4 uncertainty or hedging;
  - N5 conditional changes;
  - N6 negated changes;
  - N7 two competing sources;
  - N8 same actor, distinct declared source;
  - N9 different actor;
  - N10 different scope;
  - N11 multi-valued properties;
  - N12 coexistence-compatible statements or embedded clauses;
  - N13 source disputed or forgotten.
- **Structural-guard families:** N7, N8, N9, N10 and N13.

**G3 — Runnable schema and frozen harness (B2).** Each case is one JSON object with these fields:
- **Identity:** `case_id`, `family`.
- **`expected`:** must equal the family class (P/R gives `engage`, N gives `refrain`). A mismatch is a schema rejection before the freeze.
- **`writes`:** an ordered list of `{handle, scope, target_reference, text, source_ref|null}`.
  - `handle` is `A` or `B`, and `scope` is `S1` or `S2`.
  - Every `target_reference` is distinct and names a separate memory.
- **`older_write` and `newer_write`:** indices into `writes`.
- **`actions`:** a list of `{action: "dispute"|"forget", write}`, applied after all writes. It may be empty.
- **`recall_as`:** `{handle, scope}`.
- **Query fields:** `query`, and `rationale` (one sentence).

The harness is frozen here:
- **Handles:** A is `agent:gen732-a` and B is `agent:gen732-b`.
- **Scopes:** S1 is `project:gen732-s1` and S2 is `project:gen732-s2`.
- **Tenant and purpose:** tenant `tenant:gen732`; purpose `currentness generalization (#732)`.
- **Opening:** `AgentMemory.open(root, tenant, actor_id, scope, purpose)` with no other keyword arguments, on a fresh store per case. Each `(handle, scope)` is its own facade handle, opened and closed in write order on the same store root.
- **Recall:** `recall(query, temporal_intent={"mode": "current"}, reference_time="2026-10-08T12:00:00Z")`.
- **Write:** `remember(target_reference, text, source_ref=…)`. When `source_ref` is null, the argument is omitted.
- **Dispute:** `dispute(target_reference, fact_uuid=<that write's fact>, evidence=procedural_memory.evidence_for(<frozen skill>), risk_class="low")`. The frozen skill is `skill:gen732-governed-dispute`, version 1, scoped to the acting scope, which is the same shape as `reference/tests/test_cross_fact_currentness.py`.
- **Forget:** the facade's `forget(target_reference)`.
- **Invalid harness, decided mechanically:**
  - a write that does not commit;
  - an action that does not commit;
  - a `recall_as` handle and scope that never wrote.

  Such a case is excluded from every denominator and reported by case and reason. The case is never edited.

**G4 — Ordered stages, observed through the facade (B3, A5, A6, A7).**
- **Observation timing.** Write-time semantics are read with `write_semantics(newer_fact_uuid)` **immediately after the last write and before any action**.
- **Stages.** The first stage that applies is the case's stage:
  - S0 `invalid_harness`;
  - S1 `older_not_admitted`;
  - S2 `newer_not_admitted`;
  - S3 `no_write_time_relation`, where no relation links newer to older;
  - S4 `relation_not_state_change`, where the relation's classification is not `state_change_candidate`;
  - S5 `guard_refusal:<Gn>`, where `cross_fact_refusal_reason` is mapped to a guard by the frozen table in Appendix B;
  - S6 `labelled_not_reordered`, where the older fact carries the label but the newer fact does not rank above it;
  - S7 `engaged`, where the older fact's `temporal_applicability` is `limited_by_cross_fact_state_change` **and** the newer fact ranks above it.
- **What counts as engagement.** Only S7 is "engage". S1 and S2 are retrieval misses. They count as non-engagement in recall, but they are routed to retrieval, never to typed write-time semantics (G7).
- **Refraining layer.** For negative cases the report says which layer refrained: admission (S1/S2), write-time (S3/S4) or guard (S5).
- **Mechanism-off recompute (A4).** Every case is recalled again under `cross_fact_mechanism_off.mechanism("off")` on the same store. Any difference in admitted order between on and off, in a case where no candidate carries `cross_fact_limitation`, is **unattributed**. On v5 this count is 0 by construction (C3 off-equivalence), but it is measured anyway.

**G5 — Metrics, denominators and thresholds (B4; thresholds owner-ratified, OQ1 resolved).** Every denominator excludes S0 cases.
- **Overall recall:** a pooled micro rate, S7 cases over all valid **base** cases in P1–P13 and R1–R7. Metamorphic variants never enter recall.
- **Family recall:** S7 over the family's valid base cases. "Every positive semantic family" means P1–P13 **and** R1–R7.
- **False engagements:** S7 cases in N families. The structural families are N7–N10 and N13; the non-structural ones are N1–N6, N11 and N12.
- **M-inv:** the share of applicable invariance variants whose outcome (engage or refrain) equals their base outcome. The denominator is the applicable variants the author wrote; non-applicable types are marked `n/a` with a reason. M-inv restricted to engaged bases is also reported, as a diagnostic only (A9).
- **M-flip:** the share of must-change variants that refrain (not S7).
- **M-attr:** the unattributed count from G4.

**Gate (owner-ratified 2026-10-07, frozen):**
- **PASS requires all of:**
  - overall recall ≥ 0.80;
  - recall ≥ 0.60 in every positive semantic family;
  - ≤ 1 false engagement in total across the non-structural families;
  - M-inv ≥ 95%;
  - M-attr = 0;
  - 0 structural-guard false engagements;
  - M-flip = 100%.
- **FAIL:** overall recall < 0.50, or a violation of any zero-tolerance invariant (M-attr, a structural-guard false engagement, M-flip).
- **MIXED:** everything between PASS and FAIL. Each semantic family is classified independently by the frozen rule below. Every `deficient` or `unsafe` family is remediated or explicitly narrowed out of the supported product contract before currentness generalization is treated as qualified.

**Per-family classification (frozen):**
- **P and R families:**
  - `supported` when recall ≥ 0.80;
  - `adequate` when 0.60 ≤ recall < 0.80;
  - `deficient` when recall < 0.60.
- **Non-structural N families:** `safe` with 0 false engagements; `unsafe` with ≥ 1.
- **Structural N families:** any false engagement is a FAIL of the whole gate.
- **Insufficient families.** A family that falls below its exact size after S0 and G3b exclusions is `insufficient`. An insufficient P or R family cannot satisfy the PASS family floor, so the best possible result is MIXED. An insufficient N family is reported, and its false engagements still count.
- **Metamorphic results** are reported under their base's family. They feed only M-inv and M-flip.

**G3b — MESA contamination exclusion, frozen (B5).**
- **Tokens and trigrams.** Text is lower-cased and tokenised with the regex `[a-z0-9]+`. Each text becomes its set of token trigrams.
- **Templates.** The reference is the 10 raw strings (5 old, 5 new) of `CONFLICT_TEMPLATES` in `reference/run_semantic_route_ordering_report.py` at blob `745f789c`, with `{old}` and `{new}` deleted. The four query strings are added, for 14 texts in total.
- **Rule.** A case is excluded when any of its write texts or its query has trigram Jaccard ≥ 0.5 with any of the 14 texts.
- **Consequences.** Exclusions apply before metamorphic selection. A family that drops below its size becomes `insufficient` (G5). Every exclusion is reported.
- **Reported overlap.** The maximum Jaccard against the `-v5` lane questions is reported only.

**G3c — Metamorphic selection, frozen now (B5).**
- **Which bases.** After exclusions, for each of the 20 P and R families, the 2 valid base cases with the smallest `sha256("plan-732-metamorphic-v1|" + case_id + "|" + newer_write_text)` are selected, for 40 bases in total.
- **Who writes the variants.** The same author writes them in a second pass under the same tool rule. That pass receives only the selected `case_id`s, which are computed mechanically by `scripts/select_metamorphic_bases.py`.
- **Invariance variants** (6 types, each marked `n/a` with a reason where it cannot apply): punctuation; apostrophe variant; adverb placement; subject wording; value case; unit spelling.
- **Must-change variants** (8 types): add a hedge; attribute to another source; add a conditional; change `source_ref`; change actor (handle B); change scope (S2); make the property coexistent; dispute the source.

**G6 — Holdout, single-use (B6, A8).**
- **When it is written.** Only if remediation follows, and only after both of these:
  - the remediation hypothesis is frozen;
  - every narrowing decision is recorded (owner, per family).
- **Who writes it.** A new author under G1, with the hash-identical brief. Its exact sizes cover only the non-narrowed families.
- **Contamination check.** In addition to G3b, any holdout case with trigram Jaccard ≥ 0.5 against a measurement-corpus case is excluded.
- **Single-use.** Each remediation attempt is scored **once** on its own fresh holdout. A failed attempt's holdout is burned: it is reported and never re-scored. The next attempt needs a new holdout.
- **Acceptance of a remediation requires all of:**
  - G5 PASS on the holdout, computed over the non-narrowed families;
  - `mesa-formal-v2` with M4 = 1.000, every win `currentness_mechanism`;
  - #580 and #584 unchanged;
  - the measurement corpus reported again, for reporting only.

**G7 — Fork (owner direction).**
- **PASS.** #673 may be re-planned on v5. #732's typed write-time migration continues as separately governed work.
- **FAIL.** #673 stays held. Failures are classified by stage:
  - S1 and S2 go to retrieval;
  - S3 and S4 go to write-time recognition (#596/#597);
  - S5 and S6 go to the read-path guards and typed semantics.

  Remediation is generic. G12 is never expanded case by case. It is proven under G6.
- **MIXED.** Every family is recorded per G5. Each `deficient` or `unsafe` family is remediated (G6) or narrowed, and narrowing is an owner decision recorded per family. Generalization is not qualified, and #673 stays held, until every such family has one of those two outcomes.

**G8 — Records and binding (A2, A3).**
- **Deficit ledger.** At classification, `reports/benchmarks/deficits/current.json` gains one row per non-`supported` and non-`safe` family. Each row has these fields and no others, because the schema forbids additional properties:
  - `deficit_id` `cross-fact-currentness-generalization-2026-10-07:<family>`;
  - `metric` `engagement_recall` or `false_engagement`;
  - `primary_stage` from G4;
  - `owning_issue` 732.

  A narrowed family maps to `posture: unsupported_deliberate_non_goal` and `state: deliberate_non_goal`, with `closed_at` and `closure_evidence`. The parent row comes from #733.
- **Measurement report binding.** The report binds:
  - the executing commit, with the checker result PASS against v5;
  - `ASSERTION_FILTER_VERSION` 6.0.0;
  - ranking policy 3.3.0;
  - the corpus sha256, brief sha256 and transcript sha256.
- **"Execute once."** This means one complete run. If the run crashes before any case is scored, it may be re-run once with identical inputs. If it crashes after scoring has begun, the crash is recorded and the run repeats in full with identical inputs, and both outputs are kept.

**G9 — Execution order.**
1. Gate this plan, including Appendix A and B.
2. Run authoring under G1 and the mechanical schema checks.
3. **Freeze PR**, containing:
   - the corpus and its hash;
   - the transcript and its audit;
   - the exclusion report;
   - the metamorphic selection;
   - the runner and its tests, run on a synthetic two-case fixture only.

   The freeze PR is gated, and the checker reports PASS.
4. Measure once on `main` and commit the bound report.
5. **Classify** in an acceptance PR: per family and per stage, with the fork outcome and the deficit rows. Nothing is re-scored or re-thresholded.

## Boundaries
- **Non-goals:**
  - any runtime change;
  - any G12 change;
  - remediation design;
  - #673;
  - LLM judging.
- **Exclusions:**
  - no case edited after the freeze;
  - no threshold, rule or family changed after this gate;
  - the orchestrator authors no case text.

## Open Questions
None. OQ1 (thresholds) was resolved by the owner on 2026-10-07.

## Appendix A — Authoring brief (frozen; written verbatim to `author732/brief.md`)

> You are writing an independent test corpus for a memory system's "currentness" behaviour. Work only with the files in this directory. You may call only `Write` and `Read`, and only on paths inside this directory. Any other tool call (shell, search, web, GitHub, other agents, or reads elsewhere) invalidates your work. Do not try to learn how the system is implemented. You will never run it or see results.
>
> **Behaviour under test.** A user's agent stores facts as separate memories. Later it asks a question about the *current* state. When an earlier memory states a value and a later memory from the **same agent and the same declared source, in the same scope**, directly and sincerely asserts that the value has **changed** to a new single value, the system should treat the earlier value as no longer current. We call that *engaging*. It must **not** engage when the later statement is not a sincere first-hand assertion of a change, comes from a different source, agent or scope, concerns a property that can hold several values at once, or when the later memory was disputed or forgotten.
>
> **Interface.** For each memory you give `handle` (`A` or `B`: two different agents), `scope` (`S1` or `S2`: two different projects), a distinct `target_reference` (a short identifier naming that memory, for example `memory:<topic>:<n>`), `text`, and `source_ref` (null, meaning the agent's own observation, or a string such as `user:alice` or `tool:web` naming where the statement came from). After all writes you may list `actions` (`dispute` or `forget`) on a write. The question is asked as `recall_as` a `{handle, scope}`, always about the current state.
>
> **Families, quoted from the owner's issue #732.** Legitimate capability families (expected `engage`, 12 cases each): software/application version changes; configuration endpoint changes; service/provider changes; employment/team/role changes; project status changes; device/model changes; address/contact changes; ownership/assignment changes; preference changes expressed through paraphrases; numeric limits/quotas expressed in multiple natural forms; feature enable/disable state; environment/deployment state; relationship/state transitions that are single-valued but linguistically unlike common templates. Robustness families (genuine changes, expected `engage`, 8 cases each): Unicode punctuation; alternate sentence order; legitimate lowercase multi-token values; non-location proper nouns; values whose capitalization is semantically irrelevant; punctuation variants; statements whose semantics are clear but take an unusual surface form. Adversarial controls (expected `refrain`, 8 cases each): quoted third-party claims; forwarded text; sarcasm/jokes; uncertainty/hedging; conditional changes; negated changes; two competing sources; same actor but distinct declared source; a different agent; a different scope; multi-valued properties; coexistence-compatible statements or embedded clauses reporting someone else's change; the later memory disputed or forgotten.
>
> **Rules.** Write natural, varied, realistic language. Do not reuse one sentence pattern across cases. Each case has exactly one earlier and one later memory on the topic (you may add unrelated distractor memories). Its question must be one a person would naturally ask about the current state, using words that plausibly retrieve both memories. Use the schema exactly: `case_id`, `family`, `expected`, `writes`, `older_write`, `newer_write`, `actions`, `recall_as`, `query`, `rationale`. Write all cases to `corpus.json`. In a later pass you will be given some `case_id`s and asked to write variants.

## Appendix B — Refusal-string to guard table (frozen)

| `cross_fact_refusal_reason` | Guard |
|---|---|
| `not_explicit_current_profile` | G1 |
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
