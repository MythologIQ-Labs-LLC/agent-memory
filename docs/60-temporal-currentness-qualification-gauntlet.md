# Temporal/Currentness Qualification Gauntlet: Pre-#550 Baseline

Status: Phase 1 of #580. This document covers the evaluator and the frozen pre-#550 baseline. Nothing in this slice implements #550.

**Evidence class.** This is repository-owned conformance and falsification evidence. It is not independent external validation, and it is not proof of superiority. A pass here does not accept ADR-039, which remains **Proposed**. External temporal benchmarks (docs/59) are a later comparison layer; internal convergence does not depend on them.

## Artifacts

| artifact | location |
| --- | --- |
| Gold corpus v1.0.0 (26 cases, 50 probes, 211 assertions) | `reference/fixtures/benchmarks/temporal-currentness/temporal-currentness-gauntlet-v1.json`, sha256 `394be82e8dfabe30ad1faf064f36a88d0b0b8e7ab8157f746ecb4cbae9e64492` |
| Evaluator (evaluation-only, v1.1.0) | `reference/agentmem_ref/evaluation/temporal_currentness.py` |
| Runner and baseline matrix | `reference/run_temporal_currentness_gauntlet.py` |
| Tests (evaluator, not the score) | `reference/tests/test_temporal_currentness_gauntlet.py` |
| Frozen baseline | `reports/benchmarks/temporal-currentness/baseline-0bace49/` (`baseline.json`, `summary.json`, one report per ablation) |

**Runtime measured.**
- The runtime is exactly the reviewed boundary `0bace49` (policy 3.0.1, interpreter 1.0.0).
- The baseline was produced at branch revision `8851ce8`. Every report records `runtime_changes_since_boundary: []`, meaning no file under `reference/agentmem_ref/` differs from `0bace49` except this evaluator.
- `benchmark_ranking_variants.py` (evaluation tooling) gains a `no_temporal_preference` variant.

**Gold independence.**
- The corpus was committed (`6e0d1c0`) before any evaluator existed and before it had been run against any runtime.
- The gold has not changed since. The digest is pinned by a test.
- Later commits changed only evaluator mechanics:
  - pairwise diagnostic rungs;
  - `not_applicable` for unobservable intent;
  - flagging incidental passes.
- No expected outcome was edited to match the runtime.

## Gold method

Gold is grounded in docs/18, docs/21 and docs/26 (accepted), in the ADR-039 conformance cases (Proposed), in the #549 ruling, and in #580/#550.

Assertions state **semantic roles**, not runtime enum strings (ADR-039 L345):

| role | meaning |
| --- | --- |
| `current_applicable` | canonical current, affirmatively applicable at the target instant |
| `not_current` | refused as non-current, labelled historical, or demoted |
| `not_affirmed_current` | not affirmed applicable at the target instant |
| `prospective` | labelled valid only after the target instant |
| `historical_evidence` | admitted as labelled non-current historical evidence |
| `unknown_basis` | exposed as having no established validity basis |
| `not_demoted` | admitted and not demoted by temporal applicability |

Every assertion has a level:
- **required**: doctrine MUST/SHOULD, or a maintainer ruling.
- **target**: a doctrinally desirable outcome that pre-#550 doctrine does not require. The main example is currentness from write-time self-description. ADR-039 Decision 8 forbids inferring supersession from an independent later write.
- **ambiguous**: doctrine is permissive or silent. This is recorded per probe and never scored. Examples:
  - unknown-basis rank position;
  - exception precedence during an interval;
  - interval boundaries;
  - recency among unknown-basis ties.

**Honest unknown.** When a *target* outcome is missed but every memory involved exposes `unknown_temporal_basis`, the status is `honest_unknown`. It is counted separately and never as a pass. Not inventing currency is an honest outcome, not a solved one.

**Incidental passes.** A target ordering that holds while neither memory has an affirmed temporal basis was decided by relevance, not by temporal knowledge. Such orderings are listed in `incidental_target_passes`.

## Coverage (#580 items 1–30)

| dimension | cases | exercised |
| --- | --- | --- |
| A current applicability | A1–A5 | expired exact vs weaker current, not-yet-valid, relevance among valid, no basis, explicit vs ambiguous cues |
| B as-of / historical | B6, B8, B9, B10 | A→B→C `state_change` chain with as-of inside each interval, `error_correction` never historical, tombstone / dispute / foreign scope under historical and as-of, timeline |
| C prospective | C11–C13 | commitment vs present, reversal under current intent, unknown future basis |
| D relevance vs currentness | D14, D16–D18 | atemporal old exact vs new distractor, no validity and no intent, transaction vs valid time, observation vs valid time |
| E metabolism | E19–E22 | reinforced expired, decayed valid, old but valid, decay as proposal only |
| F write-time self-description (#550) | F23–F30 | moved/now, no longer/now, **also** (cardinality control), next two weeks, starting next month, used to/now, hedged language, adversarial authority/currentness claims |

Clocks disagree on purpose. D17 writes the later-valid memory first. D18 observes a validity long before it starts, and observes an old validity recently.

**Not exercised** (recorded in the fixture):
- purpose-bound admission: the facade has no purpose-restricted memory, and recall under another purpose admits the same set;
- sensitivity compartments: not reachable through the public facade;
- conflict/coexistence *classification*: the runtime exposes none, so this metric is not measurable pre-#550.

## Baseline metrics (policy 3.0.1, `0bace49`)

Cells show value (pass / honest_unknown / fail of units). There is no aggregate score.

| metric | kind | required | target |
| --- | --- | --- | --- |
| current_applicability_accuracy | accuracy | **1.0** (13/0/0 of 13) | 0.545 (6/4/1 of 11) |
| stale_as_current_rate | event rate | **0.0** (0 of 11) | 0.2 (2 of 10; 7 honest unknown) |
| current_demoted_as_stale_rate | event rate | **0.0** (0 of 13) | – |
| as_of_state_accuracy | accuracy | **1.0** (5/5) | – |
| historical_state_admission_accuracy | accuracy | **1.0** (7/7) | – |
| corrected_false_as_historical_rate | event rate | **0.0** (0 of 2) | – |
| prospective_applicability_accuracy | accuracy | **1.0** (3/3) | 0.0 (0/1/0 of 1) |
| unknown_temporal_basis_honesty_rate | accuracy | **1.0** (3/3) | – |
| atemporal_relevance_preservation_rate | accuracy | **1.0** (2/2) | – |
| clock_source_accuracy | accuracy | **1.0** (4/4) | – |
| intent_interpretation_accuracy | accuracy | **1.0** (7/7) | 0.0 (0/0/2 of 2) |
| state_change_vs_error_correction_accuracy | accuracy | **1.0** (4/4) | – |
| coexistence_preservation_rate | accuracy | **1.0** (15/15) | – |
| timeline_preservation_rate | accuracy | **1.0** (2/2) | – |
| metabolism_validity_separation_rate | accuracy | **1.0** (3/3) | – |
| self_description_currentness_rate | accuracy | – | 0.091 (1/9/1 of 11) |
| authority_or_scope_violation_count | count | **3** | 0 |
| temporal_self_claim_rank_influence_count | count | **1** | 0 |
| conflict_coexistence_classification_accuracy | – | not measurable pre-#550 | |
| restart_reproduction_rate | – | 1.0 (50/50 probes) | |
| cross_process_order_reproduction_rate | – | 1.0 (50/50, `PYTHONHASHSEED` 0 vs 1) | |

**Required failures: 4 assertions in 3 probes.** Their authority/scope and self-claim counts overlap: one F30 assertion counts toward both.
- B9 `historical-codename` and `as-of-codename`: a disputed superseded state is admitted as historical evidence. See finding 5.
- F30 `currently-live`: memory text's own "currently" changes its rank. See finding 3.

## Ablations and negative controls

Each configuration runs in its own process. The table counts units that changed and units that regressed from pass relative to the baseline.

| configuration | changed | regressed | improved |
| --- | ---: | ---: | ---: |
| `universal_newer_first` (policy 2.x, every intent) | 75 | 52 | **0** |
| `no_temporal_preference` (no temporal stage) | 73 | 50 | 0 |
| `transaction_only` (declared clocks removed from writes) | 47 | 45 | 0 |
| `inferred_only` (explicit caller intent removed) | 27 | 22 | 0 |
| mutant `ignore_validity` (nothing demoted) | 46 | 25 | 0 |
| mutant `invent_currency` (unknown basis reported applicable) | 29 | 8 | 0 |
| fixture control F25 `overeager_cross` ("also" read as replacement) | – | detected | – |

- The evaluator catches each deliberately bad behavior.
- No ablation improves any unit, **including every #550 target**. Universal newer-first does not solve the self-description class, so recency is not the missing mechanism.
- Scorer-level controls in the test suite corrupt real observations and check that the matching metric moves:
  - reversed order;
  - invented currency;
  - a leaked corrected-as-false value;
  - granted authority or mutated history;
  - lost timeline;
  - demoted current state.

## Failure taxonomy

Diagnostics re-run each failing case under counterfactual *inputs*, never runtime changes:
- `explicit_intent`: caller-declared intent.
- `declared_self`: validity derivable from the memory's own text, anchored on its declared observation time.
- `declared_cross`: also assigns validity to the related prior proposition, which requires proposition identity and cardinality.
- `governed_state_change`: the caller routes the update through the existing governed `correct(..., replacement_kind="state_change")`.

The first passing rung names the smallest missing mechanism. When no single rung passes, pairs are tried.

| class | probes (units) | level | smallest resolving mechanism |
| --- | --- | --- | --- |
| missing proposition identity / cardinality | C11 after-effective; F23 ×2; F24; F27 after-start; F27 prospective; F28 current (17) | target | `declared_cross`; `governed_state_change` also resolves every one tested |
| missing temporal self-description | F26 after-interval; F27 before-start (4) | target | `declared_self` |
| query intent interpretation | A5 "Where do I live now?"; F28 "…now?" (2) | target | none by input: "now" is a low-confidence cue, so no current ordering happens |
| resolvable today by governed state change | F28 plain-now (2) | target | `governed_state_change` (intent- and identity-independent, because refusal happens at admission) |
| exception precedence unmodelled | F26 during-interval (2) | target | none, not even with declared validity (ADR-039 C4 first half) |
| historical admission (root cause: dispute durability) | B9 ×2 (2) | **required** | not an input problem; see finding 5 |
| relevance ranking rewards temporal self-claims | F30 currently-live (2) | **required** | not an input problem; see finding 3 |

### Answers to the #580 questions

1. **Already correctly solved.**
   - With declared validity:
     - current, as-of and prospective applicability;
     - non-compensation (A1, A2, E19);
     - relevance among valid memories (A3).
   - Valid time over transaction and observation time (D17, D18).
   - Atemporal relevance without recency (D14, D16).
   - Historical admission (#549):
     - `state_change` history admitted only under explicit intent and inside validity (B6);
     - `error_correction` never historical (B8);
     - inferred intent never widens admission;
     - tombstone and foreign scope controlling.
   - Timelines (B6, B10).
   - Unknown-basis honesty (A4, C13, D18).
   - Metabolism kept out of validity (E19–E22).
   - "Also" coexistence (F25).
   - Hedged language kept non-authoritative (F29).
   - Adversarial authority text gains no authority, supersession, mutation or declared basis (F30 safety).
   - Restart and cross-process reproduction.
2. **Missing temporal metadata.**
   - Two self-description probes: F26 after the two weeks and F27 before "next month". Here the self-describing memory is the one that should be demoted.
   - The `transaction_only` ablation shows **45 required units** that pass only because callers declared validity. Without declared clocks the runtime is honest (unknown basis), but it cannot establish currentness.
3. **Missing query intent.**
   - "Now" questions (A5, F28): target-level, a confidence-calibration question (ADR-039 L652 vs L669).
   - The `inferred_only` ablation shows **22 required units** that depend on explicit caller intent. These are chiefly as-of and historical admission, which #549 restricts to explicit intent by design.
4. **Missing proposition/property identity or cardinality.** The largest class: C11 after-effective, F23, F24, F27 after-start / prospective, F28. See finding 1.
5. **Genuine relevance-ranking failures.** F30 (temporal self-claim tokens), required. In addition, **every one of the 7 target-level passes** (6 in the self-description cases, 1 in A5) is **incidental**: BM25 happened to order two memories whose temporal basis was unknown or not evaluated the right way. They are listed in `incidental_target_passes` and are not temporal capability.
6. **Historical admission.** B9, required. The admission logic is correct; the dispute that should control it does not survive restart (finding 5).
7. **Metabolism confused with temporal validity.** None observed. The separation holds trivially, though, because policy 3.0.1 does not use metabolism at all (`metabolic_evidence: not_used`). It is not yet evidence that a metabolism-using policy would keep the separation.
8. **Correctly unknown.**
   - A4 and C13: unknown basis exposed.
   - D18: observation time alone is not validity.
   - Nine self-description probes end `honest_unknown`: F23 ×2, F24, F26 ×2, F27 ×3, F28. The runtime neither invents currency nor supersedes. It just cannot say which state is current.
9. **Failures that specifically justify #550.**
   - The identity/cardinality class: C11 after-effective, F23, F24, F27, F28.
   - The self-description class: F26 after-interval, F27 before-start.
   - **Not** justified by #550:
     - F30: a ranking fix;
     - B9: governance-state durability;
     - "now" calibration: the interpreter;
     - F26 during-interval: exception precedence.

## Findings that challenge current assumptions

1. **Own-text temporal self-description alone does not fix the #550 class. Proposition identity does.**
   - With `declared_self`, "moved and now lives in Boston" gains `valid_from` and becomes `applicable`. The prior "lives in Denver" is still `unknown_temporal_basis`, is never demoted, and keeps outranking Boston on relevance (F23 goes from honest_unknown to **fail**). The same holds for F27 prospective / after-start and C11 after-effective.
   - Own-text metadata helps only when the self-describing memory is the one to demote (F26 after, F27 before).
   - Every replacement case needs validity on the *other* memory, which requires knowing the two are the same single-valued proposition.
   - #550 therefore cannot be "harvest temporal phrases into declared validity". Its load-bearing part is proposition identity and cardinality.
2. **ADR-039's unknown-basis posture neutralizes partial temporal knowledge.**
   - Under explicit current intent, an unknown-basis candidate is not demoted relative to an affirmed-applicable one, so relevance decides between them.
   - Doctrine permits this: the posture is policy-defined (ADR-039 L791-803, L1657). But it means any temporal evidence that attaches to only one side of a replacement is invisible to ranking.
   - A policy tier "affirmed applicable > unknown basis" under explicit or high-confidence current intent would change this without #550. That would be a separately versioned ranking-policy decision, not part of #550.
3. **Temporal cue words act as lexical relevance (F30, required failure).**
   - A memory whose text asserts "currently" outranks the established memory for "Where does the user currently live?". BM25 0.841 vs 0.491. With the self-claims replaced by neutral tokens of equal length, the order reverses.
   - Memory text is thereby granting itself rank through temporal self-claims, against `interpretation != authority` and ADR-039's temporal/intent-poisoning cases (L1513-1529).
   - Smallest mechanism: remove the tokens the query temporal interpreter consumed (its recorded cue evidence) from the relevance query. This is a ranking-policy patch, independent of #550.
4. **Recency acts as currency among unknown-basis ties (A4, recorded as ambiguous, not scored).**
   - Under current intent with no validity on either memory, relevance ties are ordered newest-transaction-first (`temporal_order_within_query_regime`, `transaction_time`).
   - This is the documented weak fallback (ADR-039 L802, docs/57). It is also exactly what #580 item 4 ("do not invent currency") and item 16 warn against, one tier down.
5. **Dispute state is not durable on its own (B9, required failure).**
   - The only dispute mechanism, `adapter.mark_disputed`, changes in-memory state. It reaches durable state only if some later operation persists governance state in the same session.
   - If the session closes first, the dispute is lost on reopen. Explicit historical and as-of recall then admit the disputed, superseded state as labelled historical evidence.
   - #549's "disputed stays controlling" silently depends on persistence ordering, and the facade has no governed dispute operation.
   - This is a governance-state durability defect, not a temporal one. It is out of scope here and reported separately.
6. **"Now" is not current intent.**
   - The frozen interpreter treats "now" as a low-confidence cue, so "Where do I live now?" establishes no current ordering.
   - ADR-039 L652 says unambiguous explicit query language should dominate. This is recorded as a target failure and an open calibration question (ADR-039 L1640).
7. **Exception precedence is still unmodelled (C4, first half).** Even with exact declared validity, a two-week override does not outrank the standing rule during its interval, because there is no exception/specificity dimension.

## Recommended bounded design target for #550

This recommendation is derived from the frozen failures. The smallest general mechanism that could resolve the identity class, without granting interpretation authority:

```text
memory text (+ declared observed_at)
  -> deterministic, versioned write-time interpretation
       * self-validity evidence from anchored relative expressions
         ("for the next two weeks", "starting next month"), basis = interpreted,
         interpreter id/version/confidence recorded, always weaker than caller_declared
       * proposition identity candidate (entity, property) + cardinality class
         {single_valued, multi_valued, unknown}; unknown by default
  -> if an explicit change marker ("moved", "no longer", "used to … now") targets an
     existing CURRENT memory of the same single-valued proposition:
       a governed state_change PROPOSAL on the existing correct(replacement_kind=
       "state_change") path, decided by PAMA like any correction; never auto-applied
  -> multi-valued / unknown cardinality ("also", hedges): no proposal, coexistence kept
```

**Acceptance against this suite.**
- F23, F24, F27 after-start / prospective, F28 and C11 after-effective reach target `pass` only through an accepted proposal or explicitly identified cross-proposition validity. `honest_unknown` must not be converted by relevance.
- F26 after-interval and F27 before-start pass via interpreted self-validity.
- **Every required unit stays `pass`.** In particular:
  - F25 coexistence, where the over-eager control must still be detected;
  - F29, no authoritative metadata from hedges;
  - F30 safety, where text claims change nothing;
  - #549 admission semantics.
- Incidental passes are not counted as progress.

**Out of scope for #550, owned by separate decisions.**
- The unknown-basis tier (finding 2).
- Temporal-cue tokens in relevance (finding 3).
- "Now" calibration (finding 6).
- Exception precedence (finding 7).
- Dispute durability (finding 5).

## Reproduce

```bash
PYTHONPATH=reference python reference/run_temporal_currentness_gauntlet.py --matrix OUTDIR
PYTHONPATH=reference python -m unittest discover -s reference/tests -t reference -p 'test_temporal_currentness_gauntlet.py'
```

`test_live_runtime_reproduces_frozen_pre_550_baseline` fails on any behavior change. A deliberate change, #550 included, must regenerate the matrix and explain every changed unit (Phase 3 of #580).
