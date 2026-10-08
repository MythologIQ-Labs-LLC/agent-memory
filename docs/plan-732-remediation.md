# Plan: #732 remediation — typed write-time propositions (caller-declared + model extractor)

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #732 (parent #671; deficit `cross-fact-currentness-generalization-2026-10-07`, #733; machinery #719)
**gate result being remediated**: `docs/plan-732-generalization-gate.md` measurement v1 = **FAIL** (META_LEDGER Entry #115)
**owner decision (2026-10-08)**: the remediation direction is the typed caller API plus a model extractor
**doctrine**: a benchmark identifies a gap but never defines the production grammar; no tuning after any score; G12 is never expanded case by case
**iteration**: 2

**Gate history**: attempt 1 was a VETO (Q1–Q3; advisories S1–S9).
- **Q1:** the typed path was switched off by the interpreter's `proposition_*` ineligibility reasons.
- **Q2:** a model-chosen link could relate facts about different properties.
- **Q3:** the two-mode holdout broke plan-732 G6, because the prompts were no longer hash-identical and the authoring was contaminated. The MESA floor was also ill-formed.

The direction was not in question. Iteration 2 fixes Q1–Q3 and folds in S1–S9.

## Diagnosis (from the bound measurement; for diagnosis only, never a tuning target)

The measurement found 0 engagements in 212 legitimate changes: 197 at S3 (no write-time relation), 12 at S2 and 3 at S1. Running only `proposition_semantics.interpret_write` 1.1.0 over the 197 frozen S3 texts gives this split (reproduced by the tribunal):

| Write-time proposition outcome | Cases |
|---|---|
| Neither fact parses to a known proposition | 92 |
| The older fact parses; the newer does not | 83 |
| Both parse, but to different slots | 10 |
| Both parse to the same slot (other reason) | 2 |
| The older fact does not parse; the newer parses (8) or is ambiguous (2) | 10 |

176 of the 197 newer writes also carry an interpreter ineligibility reason. 173 of these are `proposition_unknown`.

**Root cause.** Write-time identity is a surface-syntax `entity|verb-stem` slot. Proposal eligibility is tied to the same parser. The read path and G12 are never reached.

## Decisions

**R1 — Typed proposition contract (caller-declared, deterministic).**
- **New parameter.** `AgentMemory.remember(..., proposition=None)` accepts:

  ```
  {"subject": str, "attribute": str, "value": str,
   "assertion": "state" | "change",
   "cardinality": "single" | "multi" | null,
   "replaces_value": str | null,
   "flags": {"hedged", "attributed_to_other", "conditional", "negated",
             "joke_or_sarcasm", "quoted_or_forwarded", "coexistent": bool}}
  ```

  `flags` is optional, and each flag defaults to false.
- **Validation.** Strings are non-empty, at most 200 characters, with no control characters. Enums and flag keys are closed.
- **Persistence.** The declaration is stored in `write_semantics` as `typed_proposition`, with `basis: "caller_declared"`.
- **Typed slot.** `typed:<norm(subject)>|<norm(attribute)>`, where `norm` lower-cases, collapses whitespace and strips edge punctuation. There is no stemming and no synonym table.
- **Authority.** None. PAMA, guards and lifecycle are unchanged.
- **Contract version (S2).** `PUBLIC_CONTRACT_VERSION` is bumped (minor) for the `proposition` and `proposition_extractor` parameters. The Gauntlet configuration digest follows under R5.

**R2 — Model extractor (optional, versioned, computed once and persisted).**
- **Interface.** `PropositionExtractor.extract(new_text, candidates) -> TypedExtraction`. The output is the R1 record plus `updates_fact_uuid`, `extractor_id` and `extractor_version`.
- **Candidates (Q2, S3).**
  - Up to K = 8 memories, chosen by the writer's own governed recall over the new text.
  - They are filtered exactly as `_interpret_write` filters retained facts: same tenant and scope (including `task_ref`), current, not disputed, not tombstoned, and admitted to the writer.
  - Every candidate must also pass the egress policy below.
- **Data egress (S3).**
  - Enabling the extractor sends the new text and the candidate texts to the configured provider.
  - The reference facade carries no per-fact sensitivity classification: the docs/19 classifier is not implemented at the facade.
  - So egress is governed by two explicit caller acts:
    - **(a) Per-handle opt-in.** It is off by default, and enabled through `AgentMemory.open(..., proposition_extractor=<instance>)`. This is the caller's consent under docs/29, scoped to that handle's tenant and scope. The facade docs state the egress.
    - **(b) A required egress policy.** The extractor constructor takes an `egress_policy(text) -> bool` argument, with no default. The caller must decide which texts may leave the process, consistent with docs/19 ("classifier uncertain != non-sensitive").
  - A refused new text is not sent. It is stored with `typed_proposition: null` and reason `egress_refused`.
  - A refused candidate is dropped from the candidate list.
  - The acceptance harness passes an allow-all policy only because the holdout is synthetic test text. This is recorded in the report.
- **Persistence (S4).**
  - Stored with the fact:
    - `typed_proposition`, with `basis: "extracted:<id>@<version>"`;
    - the raw provider output;
    - the provider request id;
    - the candidate uuid list;
    - the prompt sha256.
  - It is never recomputed for an existing fact.
  - A caller declaration (R1) outranks extraction, and the extractor is not called when the caller declares.
- **Failure (S5).**
  - Each provider call has a 20-second timeout.
  - An error, a timeout or schema-invalid output persists `typed_proposition: null` with a typed reason. The write always commits.
  - Tests cover timeout, invalid output and provider error.
- **Frozen prompt (S6).**
  - The prompt and output schema are frozen in the implementation PR. They are written only from the R1 and R2 definitions.
  - A mechanical check (the G3b similarity function) shows that every text in the prompt, the schema and the test stubs has similarity < 0.5 against every measurement-corpus text.
  - The prompt is never iterated against any score.
  - No credential exists in this environment before the freeze, so the prompt cannot have been tuned against model outputs on the corpus. The implementation PR records this.

**R3 — Relation classification (classifier 1.1.0).** For a new fact with a `typed_proposition`, this replaces the interpreted slot logic for that fact. Facts without one use 1.0.0 behaviour unchanged.
- **Candidates.** The same filter as R2 is used for every typed relation (Q2).
- **Typed slot match.** A retained fact whose `typed_proposition` has the same typed slot is related with basis `typed_slot`.
  - When several match, each gets its own relation (S9), as 1.0.0 already does for same-slot facts. The read path's existing per-target handling applies.
- **Typed link.**
  - `updates_fact_uuid` counts only when it is **deterministically confirmed** (Q2). Confirmation requires both of these:
    - (i) the linked fact is a filtered candidate;
    - (ii) **either** it has a `typed_proposition` with the same typed slot, **or** `replaces_value` is non-empty, its normalized token sequence occurs in the linked fact's normalized text, and it differs from `value`.
  - A confirmed link is basis `typed_link`.
  - An unconfirmed link is recorded as `unresolved` with basis `typed_link_unconfirmed`, and never creates a proposal.
- **When a typed relation is a `state_change_candidate`.** All of these must hold:
  - `assertion == "change"`;
  - cardinality is not `multi`;
  - every flag is false;
  - the values differ.

  Otherwise the relation is `coexistence`, `same_value` or `unresolved`, with a typed basis.
- **Typed eligibility (Q1).**
  - For typed relations, `proposal_ineligible_reasons` is replaced by `typed_ineligible_reasons`. This set:
    - **drops** `proposition_unknown`, `proposition_ambiguous` and `proposition_known`-dependent reasons;
    - **keeps** `untrusted_self_claim` (from the interpreter's self-claim scan);
    - **keeps** `hedged` when either the typed flag or the interpreter's lexical hedge scan finds a hedge. The conservative OR means a typed write cannot be less cautious than 1.0.0.
  - A non-empty set gives `unresolved`, basis `change_evidence_not_proposable:<reasons>`, and no proposal.
  - Proposals still go to the existing correction lifecycle. Nothing is applied automatically.

**R4 — Read path (policy 3.4.0; assertion filter 6.1.0).**
- **G3.** Accepts `typed_slot` and `typed_link` only when the `typed_proposition` basis is `caller_declared` or `extracted:*`.
- **G6 (Q1).** For typed relations, it reads `typed_ineligible_reasons`. For interpreted relations it is unchanged.
- **G12 for typed relations.** G12 consumes the persisted typed flags, and any true flag refuses with `typed_assertion_not_assertive:<flag>`.
  - A **caller-declared** relation is never re-checked against its text (S7). The caller's typed declaration and flags are the assertion evidence.
  - The interpreter's self-claim and hedge scans still apply through R3.
- **G12 for interpreted relations.** 6.0.0, byte-identical.
- **Unchanged guards:** G1, G2, G4, G5 and G7–G11, G13. In particular, actor, source, scope, proposal state and dispute or forget are re-checked for every typed relation. Same-property identity for typed links is enforced at write time by the R3 confirmation; the read path cannot be given a typed link that was never confirmed.

**R5 — Runtime baseline succession (docs/67).**
- **Declaration.** Runtime Baseline v6 is declared as successor to v5, with record, boundary, qualification and Gauntlet manifest. The contract version is bumped (S2).
- **Equivalence.** The `-v6` lanes must be EQUAL to `-v5` with the extractor **off**, the default; any UNATTRIBUTED difference blocks.
- **MESA, extractor off.** `mesa-formal-v2` M4 = 1.000, with every win `currentness_mechanism`.
- **Guards.** #580 and #584 unchanged.
- **Order (S8).**
  1. The implementation PR is gated.
  2. Then the v6 declaration.
  3. Then the `-v6` lanes and MESA, with the extractor off.
  4. Then acceptance, then B1, then merge, then B2.

  The holdout runs against the **published v6** commit.

**R6 — Acceptance (plan-732 G6, unchanged; Q3).**
- **Holdout authoring.**
  - The remediation hypothesis (R1–R5, the frozen extractor prompt and schema, the provider and model id) is frozen in the implementation PR before any holdout is authored.
  - A new independent author writes the holdout under plan-732 G1, with prompts **hash-identical** to the measurement's (no new brief section), the A1/A2 tooling, the N1 pre-flight, and K8 against the measurement corpus.
- **Scoring.** One scoring of natural text on published v6, with the extractor on and no caller declarations.
- **Accepted when all of these hold:**
  - every plan-732 G5 PASS criterion over the non-narrowed families;
  - `mesa-formal-v2` with the extractor on: M4 = 1.000, every win `currentness_mechanism` (Q3d);
  - the extractor-off floors from R5;
  - the measurement corpus re-reported, for reporting only.

  A failed attempt burns its holdout.
- **Caller-declared mode (Q3c).** It is not scored on the holdout. It is covered by deterministic tests:
  - each flag refuses;
  - an unconfirmed link refuses;
  - actor, source and scope mismatches refuse;
  - dispute or forget refuses;
  - a confirmed change engages;
  - pre-existing facts are unaffected.

**R7 — Credential (owner action required before R6 runs).**
- **Blocker.** The reference extractor needs a provider API key; the session has none (the same class of blocker as #706).
- **What proceeds without it:** R1–R5, the stub tests, and the `-v6` lanes and MESA with the extractor off.
- **What is blocked:** holdout acceptance and MESA with the extractor on, until the owner provides `ANTHROPIC_API_KEY` as an environment secret or names another provider.

## Boundaries
- **Non-goals:**
  - #673 fusion;
  - retrieval-miss remediation (the 15 S1/S2 cases are reported; a separate issue if they remain material);
  - any change to interpreted-basis behaviour;
  - LLM answer judging;
  - re-scoring the measurement corpus;
  - plan-732 amendments.
- **Exclusions:**
  - no extractor prompt iteration after any score;
  - no G12 case-by-case expansion;
  - no retroactive extraction;
  - typed evidence never grants authority;
  - no sensitive memory is sent to a provider.

## Execution order
1. Gate this plan.
2. **Implementation PR**, gated, containing:
   - R1–R4;
   - the frozen prompt and schema, with the S6 check;
   - the stub and control tests;
   - the v6 declaration;
   - the `-v6` lanes and MESA with the extractor off.
3. Owner credential (R7).
4. Holdout authoring and freeze PR, gated.
5. A single holdout scoring on published v6, plus MESA with the extractor on.
6. Acceptance PR: classification against plan-732 G7, then B1, merge and B2. The deficit rows are discharged, and only then does the #673 re-plan begin.

## Open Questions
- **OQ1 (owner):** the provider and model. The proposal is a current Claude model through the Anthropic API at temperature 0, with the exact id recorded in the extractor version at implementation. Alternatively, name another provider or a local model.
- **OQ2 (owner):** whether the extractor stays opt-in after acceptance. This plan keeps it opt-in.
