# Plan: #732 remediation — typed write-time propositions (caller-declared + model extractor)

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #732 (parent #671; deficit `cross-fact-currentness-generalization-2026-10-07`, #733; machinery #719)
**gate result being remediated**: `docs/plan-732-generalization-gate.md` measurement v1 = **FAIL** (META_LEDGER Entry #115)
**owner decision (2026-10-08)**: remediation direction is a typed caller API plus a model extractor, chosen over a caller-API-only design, a generalized deterministic parser, and embedding slot matching
**doctrine**: a benchmark identifies a gap but never defines the production grammar; no tuning after any score; G12 is never expanded case by case
**iteration**: 1

## Diagnosis (from the bound measurement; for diagnosis only, never a tuning target)

The measurement found 0 engagements in 212 legitimate changes. 197 of them stopped at S3: no write-time relation. Running only the stored interpreter (`proposition_semantics.interpret_write` 1.1.0) over the frozen texts gives this breakdown of the 197:

| Write-time proposition outcome | Cases |
|---|---|
| Neither fact parses to a known proposition | 92 |
| The older fact parses; the newer does not | 83 |
| Both parse, but to different slots (`speaker\|be` vs `speaker\|squad be`) | 10 |
| The newer parses; the older does not, or is ambiguous | 10 |
| Same slot, another reason | 2 |

**Root cause.** Write-time identity is a surface-syntax slot key, `entity|verb-stem`, produced by a narrow English grammar. Natural statements of the same change rarely reduce to the same key. The read-path mechanism and G12 are never reached. The other 15 cases are retrieval misses (S1/S2), which are out of scope here and handled under G6 reporting.

## Decisions

**R1 — Typed proposition contract (caller-declared, deterministic).**
- **New parameter.** `AgentMemory.remember(..., proposition=None)` accepts:

  ```
  {"subject": str, "attribute": str, "value": str,
   "assertion": "state" | "change",
   "cardinality": "single" | "multi" | null,
   "replaces_value": str | null}
  ```
- **Validation.** Strings must be non-empty, at most 200 characters, and must not contain control characters. Enums are closed.
- **Persistence.** The declaration is stored in `write_semantics` as `typed_proposition`, with `basis: "caller_declared"`.
- **Slot.** The typed slot is `typed:<norm(subject)>|<norm(attribute)>`, where `norm` lower-cases, collapses whitespace and strips edge punctuation. There is no stemming and no synonym table.
- **Authority.** A declaration is evidence about the caller's own write. It grants nothing: PAMA, guards and lifecycle are unchanged.

**R2 — Model extractor (optional, versioned, computed once and persisted).**
- **Interface.** A `PropositionExtractor` protocol: `extract(new_text, candidates) -> TypedExtraction`.
  - `candidates` are up to K = 8 retained current memories in the writer's own tenant and scope, as `(fact_uuid, text)`. They are chosen by the existing lexical recall over the new text, with the same admission the writer has.
  - The result has the R1 fields plus:
    - `updates_fact_uuid`: one candidate uuid or null;
    - `flags`: closed booleans `hedged`, `attributed_to_other`, `conditional`, `negated`, `joke_or_sarcasm`, `quoted_or_forwarded`, `coexistent`;
    - `extractor_id` and `extractor_version`.
- **Persistence.**
  - The extraction is stored with the fact as `typed_proposition` with `basis: "extracted:<id>@<version>"`, and it is never recomputed for an existing fact.
  - A caller declaration (R1) always outranks extraction, and the extractor is not called when the caller declares.
  - Extraction failure (an error, a timeout, or invalid output against the closed schema) persists `typed_proposition: null`, with a typed reason. The write still commits.
- **Default.** Off. It is enabled per handle through `AgentMemory.open(..., proposition_extractor=<instance>)`. `semantic_retrieval` is not involved.
- **Frozen prompt.** The reference provider is a Claude model through the Anthropic API.
  - Its prompt and output schema are frozen in this plan's implementation PR. They are written from the R1 and R2 definitions only.
  - The prompt is **never iterated against the measurement corpus or any score** (doctrine).
  - Provider model id, temperature 0 and the prompt sha256 are recorded in the extractor version.
- **Deterministic stub for tests.** A recorded-fixture extractor maps exact input to output for synthetic fixtures. Tests never read the frozen corpus.

**R3 — Relation classification uses the typed slot first.**
- **Classifier version.** `classify_write` 1.1.0. When the new fact has a `typed_proposition`, relation candidates are found in this order:
  1. **Extracted link:** if `updates_fact_uuid` is set and that fact is retained, current, in the same tenant and scope, and admitted to the writer, the pair is related by the extracted link. Basis: `typed_link`.
  2. **Typed slot:** otherwise, a retained fact with a `typed_proposition` on the same typed slot is related. Basis: `typed_slot`.
  3. **Fallback:** otherwise, the 1.1.0 interpreted slot logic applies, unchanged.
- **When a typed relation is a `state_change_candidate`.** All of these must hold:
  - `assertion == "change"`;
  - cardinality is not `multi`;
  - every R2 flag is false;
  - the values differ.

  Otherwise the relation is `coexistence`, `same_value` or `unresolved`, with a typed basis, and the existing `proposal_ineligible_reasons` still apply.
- **Proposals.** These still go to the existing correction lifecycle. Nothing is applied automatically.
- **Facts written before this change** carry no `typed_proposition` and behave exactly as before.

**R4 — Read path (policy 3.4.0) and G12.**
- **Gate first.** G3 accepts relation basis `typed_link` or `typed_slot` only when the `typed_proposition` basis is `caller_declared` or `extracted:*`.
- **Typed-basis relations: G12 changes.** For a relation of typed basis, G12 consumes the persisted typed flags instead of re-parsing English. Any true flag refuses with `typed_assertion_not_assertive:<flag>`.
- **Interpreted-basis relations: G12 unchanged.** Version 6.0.0 still applies to them, which preserves the MESA path and the #580/#584 behaviour exactly.
- **Other guards unchanged:** G1, G2, G4–G11 and G13 (actor, source, scope, proposal state, dispute or forget, identity, clocks). The typed path cannot bypass actor, source or scope checks.
- **Version bumps.**
  - `ASSERTION_FILTER_VERSION` becomes 6.1.0: the typed branch is added and the interpreted branch is byte-identical.
  - Ranking policy becomes 3.4.0.

**R5 — Runtime baseline succession.** This is a runtime change.
- **Declaration.** Runtime Baseline v6 is declared under docs/67, with a declared successor to v5 and record and boundary files.
- **Equivalence.** The `-v6` lanes must be EQUAL to `-v5` with the extractor **off**, which is the default. Any difference is UNATTRIBUTED and blocks.
- **MESA.** `mesa-formal-v2` replays on v6:
  - extractor off: M4 = 1.000, every win `currentness_mechanism`, so the interpreted path is unchanged;
  - extractor on: reported, with M4 ≥ 1.000 required as a floor.
- **Guards:** #580 and #584 unchanged in both modes.

**R6 — Acceptance (plan-732 G6, single-use holdout).**
- **Holdout authoring.**
  - The remediation hypothesis (R1–R5, the frozen extractor prompt and the model id) is frozen in the implementation PR **before** the holdout is authored.
  - A new independent author writes the holdout under plan-732 G1 (prompts hash-identical, A1/A2 tooling, N1 pre-flight, K8 against the measurement corpus).
- **Two modes, each scored once on the same holdout:**
  - **(a) Natural text with extractor on.** This is the product claim, and the mode that must PASS.
  - **(b) Caller-declared.** The holdout author's own typed `proposition` for each write, authored in the same G1 pass. This is a second brief section, frozen in this plan's implementation PR. Mode (b) is reported, and it must also satisfy every zero-tolerance invariant.
- **Accepted when all of these hold:**
  - every plan-732 G5 PASS criterion in mode (a), over the non-narrowed families;
  - the R5 floors;
  - the measurement corpus re-reported, for reporting only.

  A failed attempt burns its holdout.

**R7 — Credential (owner action required before R6 runs).**
- **Blocker.** The reference extractor needs an Anthropic API key for the runtime. The session has none, the same class of blocker as #706.
- **What proceeds without it:** R1–R5 implementation, deterministic-stub tests, the `-v6` lanes (extractor off) and MESA with the extractor off.
- **What is blocked:** R6 mode (a) and the extractor-on MESA replay, until the owner provides a key as an environment secret (`ANTHROPIC_API_KEY`) or names another provider.

## Boundaries
- **Non-goals:**
  - #673 fusion;
  - retrieval-miss remediation (the S1/S2 cases), which are reported and fall to a separate issue if they remain material;
  - any change to interpreted-basis behaviour;
  - LLM judging of answers;
  - re-scoring the measurement corpus.
- **Exclusions:**
  - no extractor prompt iteration after any score;
  - no G12 case-by-case expansion;
  - the extractor never runs on stored facts retroactively;
  - typed evidence never grants authority.

## Execution order
1. Gate this plan.
2. Implementation PR, which contains:
   - R1–R4;
   - the frozen extractor prompt and schema;
   - the holdout brief addendum for mode (b);
   - stub-fixture tests;
   - the v6 declaration and `-v6` lanes plus MESA, extractor off.

   It is gated, then merged after acceptance and B1/B2.
3. Owner provides the credential (R7).
4. Holdout authoring under G1, then the freeze PR, which is gated.
5. A single holdout scoring in modes (a) and (b), plus MESA with the extractor on.
6. Acceptance PR. It classifies against plan-732 G7, discharges the deficit rows, and only then lets the #673 re-plan begin.

## Open Questions
- **OQ1 (owner):** the reference provider and model. The default proposal is a current Claude model through the Anthropic API, at temperature 0 (exact id recorded in the extractor version at implementation). Alternatively, name a different provider or a local model.
- **OQ2 (owner):** whether the extractor stays opt-in after acceptance or becomes a profile default. This plan keeps it opt-in.
