# Plan: #732 independent currentness generalization gate (measurement against unchanged Runtime Baseline v5)

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #732 (parent #671; deficit `cross-fact-currentness-generalization-2026-10-07`, #733; machinery #719)
**owner direction in force (2026-10-07)**:
- The order is v5 B2, then this gate, then the #673 re-plan.
- The gate is a **decision gate**, not an informational detour.
- The corpus, metrics, thresholds and holdout strategy are frozen independently of #673 and before any #732 remediation.
- The first measurement runs against the accepted Runtime Baseline v5 unchanged.
- No route fusion, no fusion-derived tuning and no #673 behaviour enters the runtime before this measurement is accepted.
- G12 is not changed before this measurement.

**doctrine**: a benchmark identifies a gap but never defines the production grammar; a perfect benchmark score is not closure evidence; no tuning after any score
**iteration**: 1

## Purpose

#671 Option A scores 1.000 on MESA M4, with every win attributed to `currentness_mechanism`. Its G12 assertion filter evolved through seven gate rounds that were checked against MESA. The `-v5` lanes show that the mechanism is inert on natural benchmark language (0 limited). Whether currentness semantics *generalize* is unmeasured.

This plan freezes an independent challenge, runs it once against the unchanged v5 runtime, and maps the result to the owner's three-way fork:
- **pass:** the #673 re-plan may proceed on v5;
- **fail:** #673 stays held and #732 remediation comes first;
- **mixed:** results are reported per family through #719, never averaged.

## Decisions

**G1 — Independence of authorship (the core constraint).**
- **Who writes the corpus.** A fresh agent writes it from a sealed brief that contains only:
  - the #732 capability families and adversarial families, in prose;
  - the public facade contract: `AgentMemory.open`, `remember(target, text, source_ref=…)` and `recall(query, temporal_intent={"mode":"current"})`;
  - the case schema in G3.
- **What the brief must not contain:**
  - `reference/agentmem_ref/runtime/**`, in particular `cross_fact_currentness.py` (G12) and `proposition_semantics.py`;
  - any MESA template or fixture;
  - `docs/plan-671-*`;
  - this repository's tests and reports;
  - the C7 report;
  - the `-v5` refusal counts.
- **Authoring conditions.**
  - The author runs in a worktree whose runtime directories are removed before it starts. The brief forbids reading them, and the authoring transcript's tool calls are audited for reads under those paths. Any such read invalidates the corpus, which is then re-authored by a new agent.
  - The orchestrator, which wrote G12, does not edit case text. It may only reject a case for a schema defect, with the reason recorded.
  - The author never runs the runtime and never sees an outcome. Expected labels come from the brief's semantic definitions alone.
- **Contamination report (recorded, never used to edit cases).** Each case gets:
  - its maximum token-trigram overlap with the five MESA conflict templates;
  - its maximum overlap with the `-v5` lane questions.

  Any case with trigram Jaccard ≥ 0.5 against a MESA template is excluded mechanically. The exclusion rule is frozen here, and the count is reported.

**G2 — Families (frozen list).** Positive families (legitimate single-valued state changes), from #732:
- P1 software or application version;
- P2 configuration endpoint;
- P3 service or provider;
- P4 employment, team or role;
- P5 project status;
- P6 device or model;
- P7 address or contact;
- P8 ownership or assignment;
- P9 preference paraphrases;
- P10 numeric limits and quotas in several natural forms;
- P11 feature enable or disable;
- P12 environment or deployment state;
- P13 other single-valued transitions unlike MESA.

Negative families (must **not** engage):
- N1 quoted third-party claim;
- N2 forwarded text;
- N3 sarcasm or joke;
- N4 hedge or uncertainty;
- N5 conditional change;
- N6 negated change;
- N7 competing sources (a different declared `source_ref`);
- N8 same actor, distinct declared source;
- N9 different actor (separate handle);
- N10 different scope or project;
- N11 multi-valued or coexistence-compatible property ("also");
- N12 embedded clause that reports someone else's change;
- N13 source disputed or forgotten before recall.

Robustness families. These are positive by meaning; the brief states that they *should* engage when the change is genuine:
- R1 Unicode punctuation and apostrophes;
- R2 alternate sentence order;
- R3 lowercase multi-token values;
- R4 non-location proper nouns;
- R5 case-irrelevant values;
- R6 punctuation variants;
- R7 clear semantics in a surface form unlike typical declarative templates.

**G3 — Case schema and size.**
- **Fields.** Each case has:
  - `case_id` and `family`;
  - `writes`: an ordered list of `{handle, scope, source_ref?, text, after_write_action?}`, where an action is `dispute` or `forget`;
  - `query`;
  - `temporal_intent`, always `{"mode":"current"}`, because the mechanism is explicit-current by contract;
  - `expected`: `engage` or `refrain`;
  - `older_fact_index` and `newer_fact_index`;
  - `rationale`, one sentence.
- **Size.**
  - Each P family has at least 12 cases, so at least 156 positive.
  - Each N family has at least 8 cases, so at least 104 negative.
  - Each R family has at least 8 cases, so at least 56.
- **Metamorphic pairs.** For 40 positive cases chosen by a frozen seeded selection, the author also writes:
  - six **invariance** variants: punctuation, apostrophe variant, adverb placement, subject wording, value case, unit spelling, each expected to match the base outcome;
  - eight **must-change** variants: add a hedge, attribute to another source, add a conditional, change `source_ref`, change actor, change scope, make the property coexistent, dispute the source; each expected to `refrain`.

**G4 — Measurement (the runner is evaluation-only and runs on the unchanged v5 runtime).**
- **Runner.** `reference/run_currentness_generalization.py` executes each case through the public facade on a fresh store.
- **Observations:**
  - **engage**: the older fact's `ranking_evidence.temporal_applicability == "limited_by_cross_fact_state_change"`;
  - **ranking**: the newer fact ranks above the older one;
  - **refusal**: `cross_fact_refusal_reason`;
  - **write-time**: whether a `state_change_candidate` relation exists.
- **Recorded, never reinterpreted.** Each case also records:
  - its *stage*: write-time relation missing, a guard refusal (G1–G13 by name), or engaged;
  - the mechanism-off recompute (shared helper);
  - attribution: whether any ranking change occurs without `cross_fact_limitation`.

**G5 — Metrics and thresholds (pre-registered; thresholds owner-ratified, OQ1 resolved).** Metrics are reported per family and never aggregated into one headline.
- **M-recall:** engagement rate over positive and robustness cases.
- **M-safety:** false-engagement rate over negative cases.
- **M-attr:** number of ranking changes not attributable to the mechanism. It must be 0.
- **M-inv:** the share of invariance variants that match their base outcome.
- **M-flip:** the share of must-change variants that refrain.

**Gate thresholds (owner-ratified 2026-10-07, OQ1). Frozen before any corpus is seen and never moved:**
- **PASS requires all of:**
  - legitimate-change engagement recall ≥ 0.80 overall (positive and robustness families);
  - recall ≥ 0.60 in every positive semantic family (P1–P13, R1–R7);
  - ≤ 1 false engagement in total across the non-structural adversarial families (N1–N6, N11, N12);
  - semantic-preserving metamorphic invariance (M-inv) ≥ 95%;
  - 0 mechanism-unattributed ranking changes (M-attr);
  - 0 structural-guard false engagements (N7–N10, N13);
  - 100% of must-change metamorphic variants refrain (M-flip).
- **FAIL:** legitimate-change engagement recall < 0.50 overall, or a violation of any fixed zero-tolerance invariant (M-attr, structural-guard false engagement, M-flip).
- **MIXED:** everything between PASS and FAIL.
  - Each semantic family is classified independently.
  - Each family is either remediated or explicitly narrowed out of the supported product contract before currentness generalization is treated as qualified.

**G6 — Holdout strategy (frozen now, authored later).**
- **When it is written.** If remediation follows, a separate holdout corpus is authored by a new independent agent under G1. This happens only after the remediation hypothesis is frozen and before any remediated runtime runs.
- **What it is built from.** The same family list and schema, with fresh cases. That agent never sees the measurement corpus's failures or the remediation.
- **How remediation is accepted.** Remediation acceptance requires all of:
  - G5 PASS on the holdout;
  - no regression on MESA `mesa-formal-v2` (M4 floor 1.000, every win `currentness_mechanism`);
  - #580 and #584 unchanged;
  - the measurement corpus reported again.

  The measurement corpus never becomes the acceptance target on its own.

**G7 — Fork (owner direction).**
- **PASS.** #673 may be re-planned on v5. #732's typed write-time migration continues as separately governed work.
- **FAIL.** #673 stays held. The fails are classified by stage (G4) and remediated generically: typed write-time semantics, never G12 case-by-case expansion. Remediation is proven under G6, and only then is #673 re-planned.
- **MIXED.** Every family is classified independently and recorded in #719 with its stage classification. Each failing or partial family is either remediated (under G6) or explicitly narrowed out of the supported product contract (#732 closure option 2, an owner decision recorded per family). Currentness generalization is not treated as qualified, and #673 stays held, until every family has one of those two outcomes.

**G8 — Execution order.**
1. Gate this plan.
2. **Freeze PR:**
   - brief, corpus, contamination report, exclusions and the frozen selection seed;
   - the runner and its tests (on a synthetic two-case fixture, never the corpus);
   - the thresholds and the content hash of the corpus.

   It makes no runtime change, so the checker reports PASS against v5.
3. **Measure:** execute once on `main` after the freeze merges, and commit the report.
4. **Classify** in an acceptance PR: per family, per stage, with the fork outcome, recorded in the ledger and in #719. If the result is FAIL or MIXED, open the remediation plan. The fork outcome is not re-scored or re-thresholded.

## Boundaries
- **Non-goals:**
  - any runtime change;
  - any G12 change;
  - remediation design;
  - #673;
  - judged or LLM evaluation (the corpus is deterministic and facade-only).
- **Exclusions:**
  - no case edited after the first run;
  - no threshold changed after the freeze;
  - no family dropped after the freeze;
  - the orchestrator does not author case text.

## Open Questions

None. OQ1 (thresholds) was resolved by the owner on 2026-10-07 with the values in G5.
