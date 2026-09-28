# Write-Time Proposition Identity, Cardinality, and Temporal Self-Description (#550)

Status: implementation and evidence for #550 on draft PR, not merged. ADR-039 remains **Proposed**; nothing here promotes it. The #580 gauntlet used below is repository-owned conformance and falsification evidence, not independent external validation. AgentMemBench and LongMemEval are external benchmark evidence, bounded to their corpora and retrieval profiles.

## 1. What #550 had to solve

The frozen #580 Phase 1 baseline (docs/60) showed that the largest currentness failure class is not temporal phrase harvesting. It is **proposition identity and cardinality**:

```text
old: "The user lives in Denver."
new: "The user has moved and now lives in Boston."
```

Giving Boston its own validity does not make Denver stale unless the runtime also knows that both statements occupy the same proposition slot (entity `user`, property `live in`) and that the slot is single-valued. The #583 external replay (PR #587, HOLD) added a second constraint. Lexical overlap on words such as `currently` is today the only carrier of a memory's own temporal self-description. #550 therefore has to provide a **typed** carrier before #583 can safely separate query intent cues from relevance.

## 2. Architecture

```text
memory text + caller-declared write metadata
  -> bounded, deterministic, versioned write-time interpretation      (evidence)
       proposition candidate: entity / property / value, known | unknown | ambiguous
       cardinality: single_valued | multi_valued | hierarchical | unknown
       markers: change, coexistence, hedge, self-claim           (data, never instructions)
       self-validity: anchored interval / start                  (basis: interpreted)
  -> classification against current same-scope same-slot memories  (evidence)
       same_value | coexistence | state_change_candidate | conflict | unresolved
  -> governed state_change proposal, only for explicit unhedged change   (evidence)
  -> existing lifecycle: AgentMemory.correct(replacement_kind="state_change") under PAMA
       only when a caller chooses to apply it (apply_semantic_proposal)
```

Load-bearing invariants, each pinned by a test in `reference/tests/test_write_time_proposition_semantics.py`:

```text
interpretation != authority                 classifier confidence != truth
proposition match != authority to replace   single-valued candidate != automatic supersession
conflict detection != mutation              proposal != application
newer != superseding                        historically true != corrected-as-false
```

### 2.1 Typed contracts (`agentmem_ref.runtime.proposition_semantics`)

| contract | content |
| --- | --- |
| interpreter identity | `agent-memory-deterministic-write-semantics` 1.0.0; classifier 1.0.0 |
| proposition | `status` known / unknown / ambiguous, `entity`, `property`, `value`, `basis` (`interpreted`; `caller_declared` is reserved), `reason` when not known |
| cardinality | `class` single_valued / multi_valued / hierarchical / unknown, `basis`, `evidence` |
| markers | `change` (no longer, used to, not anymore, moved, changed, switched, updated, ...), `coexistence` (also, too, as well, ...), `hedge`, `self_claims`, `aspect` (present / prospective / past_habitual, with cue words) |
| self-validity | `status` none / resolved / unanchored / hedged_not_resolved / ambiguous / superseded_by_caller_declared, `valid_from`, `valid_until`, `anchor` {value, source}, `basis: interpreted` |
| relation | `classification`, `basis`, `other_fact_uuid`, `other_memory_ref`, `slot`, optional `proposal` |
| proposal | `proposal_id`, `operation: correction`, `replacement_kind: state_change`, target reference and fact, source fact, replacement text, `effective_no_later_than` (an upper bound only), `applied: false`, `authority_effect: none` |

Every interpretation carries `authority_effect: none`.

### 2.2 Proposition identity

A bounded clause grammar reads determiner-led noun phrases and subject pronouns, auxiliaries, negation (`no longer`, `not ... anymore`, `used to`), modals, and a verb or copula with an optional preposition. It uses generic English function words only; there is no property list and no domain vocabulary. Slot identity is `entity|property` with an inflection-insensitive verb key (`lives` / `living` / `live`). Pronouns resolve to the nearest preceding explicit subject; a clause about the memory itself ("this memory is ...") is never an antecedent. **Unknown** is the fail-safe result: imperatives, proper-noun subjects, and anything the grammar cannot parse stay `unknown`. More than one affirmed slot or value in one write is `ambiguous`.

### 2.3 Cardinality

Cardinality is never inferred from the property. It is `unknown` unless:

* the write itself carries a **coexistence** marker (`also`, `too`, `as well`, ...), giving `multi_valued`; or
* the write itself carries a **replacement** marker (`moved`, `changed`, `switched`, a revision qualifier such as `updated`), giving `single_valued` for this write's slot.

`hierarchical` is part of the contract but is never produced from text. It is reserved for caller-declared cardinality (see §6). The same property with and without a marker is classified differently, and a test pins this.

### 2.4 Temporal self-description

Anchored relative expressions (`for the next N days|weeks|months|years`, `starting|from tomorrow|next week|next month|next year`, `until ...`, and ISO starts and ends) resolve **only** against a caller-declared `observed_at`. Without an anchor the status is `unanchored` and nothing is resolved: imported text is never silently anchored to ingestion time. Hedged or conflicting expressions are not resolved. Caller-declared `valid_from`/`valid_until` always win (`superseded_by_caller_declared`), and the interpreted window is never reported as a clock or as a caller-declared basis.

### 2.4a Temporal aspect: the typed carrier #583 lacked

Independently of whether a proposition parses, the interpreter records the temporal **aspect** the memory asserts about itself, together with the cue words that set it:
* `present`: currently, right now, these days, ...;
* `prospective`: planning to, going to, will, next week, ...;
* `past_habitual`: used to, no longer, previously, ...

The marker is evidence only. It creates no validity window and no applicability basis, and ranking does not read it. It exists so that a memory's own "currently" is carried by **type**, not only by lexical overlap. On LongMemEval_S user turns it carries every occurrence of the #583 cues (§4.2).

### 2.5 Classification and proposals

Only current, same-scope (domain refs, project, task) memories of the same slot are compared. Superseded, tombstoned, disputed, and other-scope facts never are.

| condition | classification | proposal |
| --- | --- | --- |
| same slot, same value | `same_value` | no |
| new write explicitly ends the other's value (`no longer X`, `used to X`) | `state_change_candidate` (`explicit_termination`) | yes, unless ineligible |
| either side multi-valued or hierarchical | `coexistence` | no |
| new write single-valued with a replacement marker | `state_change_candidate` (`single_valued_replacement_marker`) | yes, unless ineligible |
| single-valued without change evidence | `conflict` | no |
| cardinality unknown | `unresolved` | no |

A write is **ineligible** to originate a proposal when it is hedged (`maybe`, `might`, `probably`, `I think`, ...), carries a self-claim (authority, verification, supersession, currentness, instructions), or has an unknown or ambiguous proposition. Its change evidence is then recorded as `unresolved: change_evidence_not_proposable:<reasons>`.

`semantic_proposals()` derives each proposal's status (`open` / `applied` / `stale`) from lifecycle state. `apply_semantic_proposal(id, evidence=..., ...)` is the caller's explicit decision. It is exactly `correct(target, replacement_text, replacement_kind="state_change")` under ordinary PAMA, cites the proposal id as an evidence ref, is not auto-satisfied (it is refused without qualified review evidence), and refuses a proposal that is not `open`. The #549 boundary holds: the replaced fact is a state change, never an error correction. It is refused for current intent and admitted only as labelled historical evidence under explicit historical intent.

### 2.5a Visibility of semantic evidence

`write_semantics()` and `semantic_proposals()` are bounded exactly like recall. Evidence is readable only for facts that are domain-eligible for the calling handle's own context (tenant, isolation domains, project, task), and never for tombstoned facts or facts derived from tombstoned sources. A proposal is hidden when its target is not visible. Adversarial review before the PR found that the first version filtered by tenant only, which would have let another scope read interpreted values and, through `replacement_text`, memory text. That is fixed and pinned by tests.

### 2.6 Ranking: policy 3.0.1 -> 3.1.0 (applicability tier only)

Lexical relevance, BM25, and its #576 sorted accumulation are unchanged. The only ranking change: when the caller declared no validity, a resolved interpreted window may **limit** a memory's own applicability (`outside_target_interval`, and `prospectively_applicable` under current and as-of intent; `outside_target_interval` and `applicable_not_prospective` under prospective intent). It never **affirms** applicability: a label that would not demote stays `unknown_temporal_basis`. `temporal_applicability_basis` records `caller_declared` or `interpreted` for every label.

The asymmetry was chosen on evidence, not preference. A first, symmetric version let interpreted windows also affirm `applicable`. Against the frozen gauntlet it converted 7 target units from `honest_unknown` to `fail` (F26 during-interval, F27 after-start and prospective-explicit) without changing any order: the self-describing memory became affirmed while its rival stayed unknown-basis, so relevance still decided. The same effect is docs/60 finding 1 and #584's territory. A memory's text may always make a weaker claim about itself; affirming its own currentness is the self-promotion class F30 forbids.

### 2.7 Persistence and versioning

The interpretation, its relations, and any proposal are computed once at write and stored in the fact's attributes (canonical JSON, immutable after write). They are version-pinned and never recomputed. A later interpreter version therefore cannot silently reinterpret historical writes. Facts written before #550 carry no interpretation and are treated as `unknown`; reinterpreting them would need a declared migration. The in-memory (slot, scope) index is derived, rebuilt lazily from persisted attributes on recovery, and every hit is re-validated against lifecycle state. Restart reproduces interpretation, classification, proposals, and recall exactly (tests), and interpretation is identical across `PYTHONHASHSEED` 0, 1, and 2.

The index is also invalidated whenever adapter checkpoint state is restored (including a SQLite rollback), so a rolled-back write leaves no semantic residue (test).

Storage is bounded and compact. The persisted form keeps only non-default evidence plus one version tag (`"version": "<interpreter>/<classifier>"`). Diagnostic clause parses are not stored (only `clause_count`). Relations are capped at 8, most significant first, and plain same-slot pairs with unknown cardinality are kept as a count only. `write_semantics()` expands the stored form back to the full typed contract.

## 3. #580 before/after (repository-owned evidence)

Artifacts: `reports/benchmarks/temporal-currentness/post-550-eb44c34/`. The full matrix is regenerated at `eb44c34` with a clean runtime tree. Fixture sha256 `394be82e…4492`, unchanged; gold unchanged.

Columns: frozen pre-#550 baseline `0bace49` (3.0.1) | `main` `550abf0` (3.0.1, includes #582) | #550 `eb44c34` (3.1.0). Cells: value (pass / honest_unknown / fail of units). There is no aggregate score.

| metric | level | frozen `0bace49` | `main` `550abf0` | #550 `eb44c34` |
| --- | --- | --- | --- | --- |
| current_applicability_accuracy | required | 1.0 (13/0/0) | 1.0 (13/0/0) | 1.0 (13/0/0) |
| current_applicability_accuracy | target | 0.545 (6/4/1) | 0.545 (6/4/1) | 0.545 (6/4/1) |
| stale_as_current_rate | required | 0.0 (0 of 11) | 0.0 | 0.0 |
| stale_as_current_rate | target | 0.2 (1/7/2 of 10) | 0.2 (1/7/2) | 0.2 (**3/5/2**) |
| current_demoted_as_stale_rate | required | 0.0 (0 of 13) | 0.0 | 0.0 |
| as_of_state_accuracy | required | 1.0 (5/5) | 1.0 | 1.0 |
| historical_state_admission_accuracy | required | 1.0 (7/7) | 1.0 | 1.0 |
| corrected_false_as_historical_rate | required | 0.0 (0 of 2) | 0.0 | 0.0 |
| prospective_applicability_accuracy | required / target | 1.0 / 0.0 (0/1/0) | same | same |
| unknown_temporal_basis_honesty_rate | required | 1.0 (3/3) | 1.0 | 1.0 |
| atemporal_relevance_preservation_rate | required | 1.0 (2/2) | 1.0 | 1.0 |
| clock_source_accuracy | required | 1.0 (4/4) | 1.0 | 1.0 |
| intent_interpretation_accuracy | required / target | 1.0 / 0.0 (0/0/2) | same | same |
| state_change_vs_error_correction_accuracy | required | 1.0 (4/4) | 1.0 | 1.0 |
| coexistence_preservation_rate | required | 1.0 (15/15) | 1.0 | 1.0 |
| timeline_preservation_rate | required | 1.0 (2/2) | 1.0 | 1.0 |
| metabolism_validity_separation_rate | required | 1.0 (3/3) | 1.0 | 1.0 |
| self_description_currentness_rate | target | 0.091 (1/9/1 of 11) | 0.091 (1/9/1) | **0.273 (3/7/1)** |
| authority_or_scope_violation_count | required | 3 | 1 (#582 fixed B9) | 1 |
| temporal_self_claim_rank_influence_count | required | 1 (F30) | 1 | 1 (F30 stays #583) |
| conflict_coexistence_classification_accuracy | – | not measurable | not measurable | not measurable by the frozen gold (no assertions); measured by the #550 test suite and the counterfactual below |
| restart_reproduction_rate | – | 1.0 (50/50) | 1.0 | 1.0 |
| cross_process_order_reproduction_rate | – | 1.0 (50/50) | – | 1.0 (50/50) |

**Units changed by #550 (vs `main`): 4, all target `honest_unknown -> pass`.**
* F26 after-interval: `temporary` is now `outside_target_interval` (interpreted), so it is `not_current` and demoted. Stale-as-current and self-description both pass.
* F27 before-start: `green` is now `prospectively_applicable` (interpreted), so blue precedes green and green is prospective.

Both probes' "precedes" orderings were previously **incidental** passes (decided by BM25 while both memories were unknown-basis). They now hold for the intended temporal reason, so incidental target passes fall from 7 to 5.

**Required passes regressed: none.** No target unit worsened. Probe digests changed only in the 2 improved probes. Every ablation and runtime mutant still regresses units and improves none, and the F25 over-eager fixture control is still detected.

### 3.1 Previously failing #550-related cases

| case / probe | frozen | #550 | why |
| --- | --- | --- | --- |
| F23 current-inferred / current-explicit | honest_unknown | honest_unknown | `state_change_candidate` + open proposal (Denver); **not applied**, so Denver stays current |
| F24 current-inferred | honest_unknown | honest_unknown | `state_change_candidate` (explicit_termination: no longer) + open proposal |
| F28 current-inferred | honest_unknown | honest_unknown | `state_change_candidate` (explicit_termination: used to) + open proposal |
| F28 plain-now | fail | fail | as above; the query-side "now" calibration is #585 |
| C11 current-after-effective | honest_unknown | honest_unknown | "runs on the old cluster" vs "is scheduled to move to the new cluster" parse to different slots, so no relation. Honest limitation |
| F26 after-interval | honest_unknown | **pass** | interpreted self-validity limits `temporary` |
| F26 during-interval | honest_unknown | honest_unknown | interpretation never affirms; exception precedence is #586 |
| F27 before-start | honest_unknown | **pass** | interpreted start limits `green` |
| F27 after-start, prospective-explicit | honest_unknown | honest_unknown | interpretation never affirms; imperatives have no proposition |
| F25 (also) | pass (required) | pass | `coexistence`, no proposal |
| F29 (maybe) | pass (required) | pass | hedged; different slot (`move to`); no proposal |
| F30 (self-claims) | 1 required fail (#583) | same | self-claims recorded; no relation, proposal, or authority; the rank influence is #583 |

### 3.2 Governed-application counterfactual

`proposal-application-counterfactual.json` plays a reviewing caller who applies every open proposal through `apply_semantic_proposal` with qualified evidence, then re-scores with the unmodified evaluator.

| case | proposal | target units converted | required units broken by the mutation |
| --- | --- | --- | --- |
| F23 | Boston -> Denver (`single_valued_replacement_marker`) | 6 | 4 |
| F24 | Globex -> Acme (`explicit_termination: no longer`) | 2 | 2 |
| F28 | Coffee -> Tea (`explicit_termination: used to`) | 4 (including the plain-now fails) | 4 |

The proposals are the right ones, and accepting them would reach every F23/F24/F28 target. Accepting them also breaks the fixture's **required** `no_mutation`/`admitted` units, because the gold encodes that text alone must not mutate memory. This is concrete evidence that the proposal must remain a proposal: automatic application would violate required doctrine.

## 4. External replay (bounded external evidence)

Candidate `eb44c34` (the reviewed head), compared with the canonical policy-3.0.1 evidence of #576 (`reports/benchmarks/replays/576-deterministic-bm25/*8bd6c91*`). The inputs are byte-identical to the #583 replay:

* AgentMemBench `memdialogue_v2.jsonl` sha256 `33632710…ca2a6` at `186c9a54`;
* LongMemEval_S `longmemeval_s_cleaned.json` sha256 `d6f21ea9…a442` at dataset revision `98d7416c`.

Evidence: `reports/benchmarks/replays/550-write-time-semantics-eb44c34/`.

**AgentMemBench** (all phases, seeds 0 and 1): **0 non-timing differences** in every dimension and in the governance tallies. All 2,051 per-search orders and every BM25 score bit are identical to canonical. This is expected: the harness declares no `observed_at`, so no interpreted window resolves, and proposals are never applied.

The typed evidence does recognize the benchmark's conflict class (evaluation-only probe of the five conflict templates). Location, role, preference, status, and numeric updates each become a same-slot `state_change_candidate` with an open proposal. The rules that recognize them are generic (replacement verbs, simple-past subject boundaries, revision qualifiers), and none is applied, so the benchmark's staleness rate is unchanged by design.

### 4.1 LongMemEval_S

`compare-lme-s-eb44c34-seed1-vs-8bd6c91.json` gives **IDENTICAL**: all 53 checks, and 3,000/3,000 rows (session and turn planes, all three backends) semantically identical, with **0 rank differences**.
* Headline retrieval, knowledge-update currentness, and latest-gold-ranked-first are unchanged (session 0.457, turn 0.557).
* Governance (admissions, refusals), failures, authority effect, and boundary are unchanged.
* Wall time is 997 s against 1,078 s canonical, on a different machine load; it is not a semantic signal.

Row classification: there are no changed rows, so no row falls into `INTENDED_550_EFFECT`, `NUMERICAL_ONLY`, `UNRELATED_DRIFT`, `FAILURE_OR_GOVERNANCE_CHANGE`, or `UNEXPLAINED`. This is expected: the default replay declares no `observed_at`, so no interpreted window resolves, and proposals are never applied.

**LongMemEval_M is not required.** None of the escalation triggers holds (no drift, currentness change, retrieval regression, or governance change), and S characterizes the affected population exactly: it is zero rows, by construction of the anchoring rule.

### 4.2 Typed-carrier coverage on natural data

`lme-s-carrier-coverage-eb44c34.json` covers 93,931 unique LongMemEval_S user turns, interpreted exactly as the default replay writes them:

| measure | value |
| --- | --- |
| proposition known / ambiguous / unknown | 13,655 (14.5%) / 44,692 (47.6%) / 35,584 (37.9%) |
| cardinality single / multi / unknown | 25 / 8,435 / 85,471 |
| turns with aspect / change / coexistence / hedge / self-claim markers | 13,809 / 206 / 8,435 / 22,285 / 320 |
| #583 cues carried by the typed aspect marker | `currently` 551/551, `planning to` 2,076/2,076, `going to` 1,314/1,314 |

## 5. Costs (idle, against a clean `550abf0` worktree)

| workload | `main` | #550 `eb44c34` |
| --- | --- | --- |
| AgentMemBench all phases, wall (3 runs each, alternated) | 47.4–48.2 s | 53.6–55.6 s (+15%) |
| AgentMemBench retrieval write p50 / read p50 / read p95 | 4.90 / 15.0 / 25.3 ms | 5.42 / 17.7 / 31.0 ms |
| 1,000 natural first-person writes, per write | 5.3 ms | 6.3 ms (+18%) |
| 1,000 same-slot facts in one scope, per write | 5.0–5.6 ms | 7.2–7.8 ms (+40%) |
| DB size after 1,000 writes | 4.04–4.10 MB | 4.30–4.33 MB (+6%) |
| recall over 1,000 rich-text candidates | 319–322 ms | 341–350 ms (+7–9%) |
| LongMemEval_S full replay wall | 1,078 s (canonical) | 997 s |

**Where the read cost comes from.** Candidate generation decodes the attributes of every fact in the tenant on each search (in AgentMemBench, about 1,000 facts per search, before domain filtering). That was harmless while attributes were almost always `{}`. #550 gives every fact a small write-semantics record, so each of those decodes costs about 1 µs more. The persisted form is already compact: 25 bytes with no evidence, about 150 bytes with one proposition, and about 250 bytes for a rich turn (an earlier 440–1,000-byte form measured +68% read p50 and was replaced). Removing the rest is a substrate change: decode attributes lazily, or store write semantics outside the fact row. It is proposed as a separate follow-up rather than widening this PR.

**Update (#591).** Candidate discovery now applies the #548 prefilter to a fact's identity before materializing it, and decodes attributes only for surviving candidates. The #550 semantics stay with the fact. AgentMemBench read p50 went from 17.9 ms to 7.7 ms and total wall from 54.6 s to 38.6 s, below the pre-#550 values, with semantically identical replays. Evidence: `reports/benchmarks/replays/591-identity-first-materialization-f76c441/`.

**Write cost** is interpretation plus same-slot classification. In the same-slot worst case, classification compares against every current same-slot fact in the scope (O(k)) using an in-memory index. It never re-reads SQLite.

## 6. Known limitations

* **Grammar coverage on natural data.** Of 93,931 unique LongMemEval_S user turns, 14.5% yield a *known* proposition, 47.6% *ambiguous* (usually several propositions in one turn), and 37.9% *unknown*. Cardinality is `unknown` for 91%. The typed **aspect** carrier covers every #583 cue occurrence, but proposition-level evidence is sparse on long conversational turns.
* **Grammar coverage, specific gaps.** Proper-noun subjects ("Kevin lives in ..."), imperatives, and many natural sentences resolve to `unknown` or `ambiguous`. That is honest, but it limits recall of the mechanism. C11 is a concrete miss: "runs on" and "is scheduled to move to" are different slots.
* **No caller-declared proposition input yet.** `hierarchical` cardinality and `basis: caller_declared` are in the contract but not yet reachable from the facade, because threading them through the commit chain is a separate change.
* **Pre-#550 facts** are `unknown`. A declared migration would be needed to interpret them.
* **Interpretation never affirms applicability.** Inside a self-described window a memory stays `unknown_temporal_basis`. Whether affirmed-over-unknown should order is #584.
* **Nothing is applied automatically.** Currentness improves for F23, F24, and F28 only when governance accepts a proposal. Whether any class of proposal should ever apply without review is a separate ruling and not part of #550.

## 7. What this means for #583

#550 now provides the typed memory-side carrier #583 lacked. Per fact, it persists and versions:
* the aspect marker, which carries 551/551 `currently`, 2,076/2,076 `planning to`, and 1,314/1,314 `going to` occurrences on LongMemEval_S user turns;
* the proposition slot and cardinality;
* change and self-claim markers;
* an anchored self-validity window.

A redesigned #583 can therefore require that removing a consumed query cue from lexical relevance never discards the equivalent **typed** evidence the memory carries. For example, a query cue `currently` would be separated from BM25 only if memories that assert `present` aspect keep an equivalent typed signal. Whether that signal should *order* results is itself a ranking decision entangled with #584 (unknown-basis posture), because aspect is self-assertion, not validity. That redesign is not done here. This PR provides the carrier and does not change #583's HOLD.

ADR-039 remains **Proposed**. Interpretation grants no authority.
