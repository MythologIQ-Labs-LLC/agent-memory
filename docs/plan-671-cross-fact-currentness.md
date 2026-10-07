# Plan: #671 read-path currentness — interpreted cross-fact applicability (Option A; ranking policy 3.3.0; Runtime Baseline v5)

**change_class**: runtime
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #671
**owner rulings in force**:
- `decision-671-currentness-mechanism`: Option A now, Option D next (roadmap seq 55–56, Entry #96);
- `decision-baseline-sequencing-v4-v5`;
- `decision-semantic-default` (stays off);
- `decision-temporal-posture`.

**doctrine**: relevance != currentness; newer != superseding; proposal != authority; ranking != recall admission; interpretation != authority; benchmark score != truth; recency is never authority.
**design evidence**:
- formal MESA M4: 250/250 pairs pass every write-time stage, and read-path currentness separates 0;
- `docs/plan-673-route-fusion.md` gate attempt 1: relevance currently decides "current" between unknown-basis facts;
- the #671 code map in this plan's research notes.

**iteration**: 2

Gate history:
- **Attempt 1: VETO.** An independent prototype was run (`scratchpad/gate671/`).
  - **What worked.** With the mechanism off, MESA M4 reproduces v1 exactly. With it on, 250/250 pairs become `new_fact` wins, every one credited `currentness_mechanism` through `temporal_applicability_tier` by the unchanged classifier. All 16 #584 facade runs keep their order.
  - **Blocking findings:**
    1. **#580.** Eight target units go `honest_unknown` → `fail` (F23, F24 and F28, on the `self_description_currentness_rate` and `stale_as_current_rate` metrics). The frozen evaluator's `DEMOTED_LABELS` does not know the new label. Two order digests change on labels alone, which `VERSIONED_RANKING_TRANSITIONS` cannot express. Six test files had unlisted pins, including the #550 behavioural pin.
    2. **Interpreter misfires.** C6.8 and C6.9 were false. Each of these limits the true fact: "The user's sister moved and now lives in Boston", "has not moved", a trailing "according to a spam message", and a question.
    3. **Write order against declared clocks.** Write order alone decided which fact was older, even when the declared clocks said the opposite.
    4. **"Same source" degenerated.** It reduced to same actor, and the tenant could be overridden by the caller.
    5. **Unverifiable evidence claims.** The byte-identity claims contradicted the refusal field. MESA could not report guard failures under an unchanged runner. Lane attribution was not checkable from retained evidence.

  Iteration 2 amends C1–C3, C6, C7 and C9, and adds G12 and G13. The attempt-1 advisories are folded in.

## Purpose

Today an explicit-current query has no way to use the change evidence the runtime has already detected. Consider "The user moved and now lives in Boston" (newer) against "The user lives in Denver" (older), with no declared validity on either.
- **Write time succeeds.** The newer write is recognised and the slot is identified. A `state_change_candidate` relation with an open correction proposal is persisted on the newer fact.
- **Read time fails.** Both facts have an unknown temporal basis. The #584 pairwise rule needs one side `applicable`, so no edge forms, and lexical relevance decides which fact ranks as "current".

Option A connects the two. When guarded, typed, open change evidence exists between two live, same-actor, same-source, same-scope facts, an **explicit-current** recall **limits the older fact's applicability** for that currentness decision, under a new explicit basis `interpreted_cross_fact`.
- Nothing is mutated or corrected.
- The proposal stays open.
- History and non-current recall are untouched.
- Time order never substitutes for the typed evidence.

## Decisions

**C1 — Write provenance per fact (new; the guard identities).**
Facts carry no actor today. The facade's default evidence ref is a per-text content digest, so evidence refs can never serve as a shared "source".

- **What is recorded.** `_write` records an immutable `attributes["write_provenance"]` on every fact it commits:
  - `version: "1.0.0"`;
  - `actor_id`: the PAMA proposal's actor;
  - `tenant`: the adapter's `fact.group_id`, never the caller-overridable `tenant_ref`;
  - `purpose`;
  - `channel`: `caller_observation` for `promotion`, `caller_correction` for `correction`, `other:<operation>` otherwise;
  - `source_ref`.
- **`source_ref`** is a new optional facade `remember(..., source_ref=...)` argument: the caller-declared origin of the statement, for example `user:alice`, `conversation:42` or `tool:web-search`.
  - It defaults to `actor:<actor_id>`, meaning the acting agent's own direct observation.
  - It is validated as a non-empty string of at most 256 characters.
  - It is not settable through `overrides`.
- **Same source** means all three of these hold:
  - equal `source_ref`;
  - equal (`tenant`, `purpose`);
  - both channels are `caller_observation`.

  Callers that write statements from several origins through one actor can now separate them, and a mismatch refuses. A caller that declares nothing gets the actor-level default. Under that default, "same source" coincides with "same actor": the acting agent is the only source the runtime has evidence of.
- **Owner-ratified reading.** This definition of "same source" was ratified by the owner on 2026-10-07 (`decision-671-same-source`; see Open Questions).
- **Same actor** means `actor_id` is equal and non-empty.
- **Same scope** means `_same_semantic_scope` (domain_refs set, project_ref, task_ref) plus equal `required_domain_refs` and equal `tenant`. This is the isolation domain the write-time classifier already used.
- **Missing identity fails closed.** A fact without `write_provenance` never participates: any fact committed before v5, or by a harness path that bypasses `_write`. The refusal reason is `cross_fact_identity_unavailable`, and pre-v5 stores gain nothing.
- **What provenance is excluded from.** It is excluded from BM25 text, from the content-identity digest, from every ranking input other than this guard, and from the facade `write_semantics` view. The gate prototype verified that BM25 and the digest read only `fact_text`.

**C2 — Cross-fact evidence construction (adapter; read-only).**
`GovernedMemoryAdapter.cross_fact_applicability(admitted, context, intent) -> {target_uuid: evidence}` is a pure read. For each admitted fact S, and each persisted relation on S whose other fact T is also admitted in this recall, it accepts the pair only when **every** guard below holds. The first failing guard is recorded as the refusal reason.

| # | Guard | Refusal reason |
|---|---|---|
| G1 | Explicit-current profile (`temporal_order_constraints.explicit_current_profile`: mode current, posture explicit, basis caller_declared or query_language_explicit). Inferred `latest`, atemporal, historical and as-of intents are refused. | `not_explicit_current_profile` |
| G2 | The relation classification is `state_change_candidate`. A conflict, coexistence or unresolved relation never qualifies. | `relation_not_state_change` |
| G3 | The relation basis is `single_valued_replacement_marker` or `explicit_termination:*`. | `relation_basis_not_accepted` |
| G4 | The relation carries a proposal, with `applied: false` and `authority_effect: "none"`. | `no_open_proposal` |
| G5 | `_proposal_status(...) == "open"`. Both facts are the current fact of their own memory, neither is tombstoned or disputed, and the proposal has not been applied. This covers forget, tombstone, dispute and supersession at read time. | `proposal_not_open:<status>` |
| G6 | S's persisted markers carry no `hedge` and no `self_claims`, and S's `proposal_ineligible_reasons` is empty. This repeats the write-time downgrade at read time, as defence in depth. | `hedged_or_untrusted_claim` |
| G7 | Both facts carry `write_provenance`. | `cross_fact_identity_unavailable` |
| G8 | Same actor. | `actor_mismatch` |
| G9 | Same source (C1). | `source_mismatch` |
| G10 | Same scope (C1). | `scope_mismatch` |
| G11 | No mutual limitation. If T also carries an accepted relation to S, both are refused. This is unreachable on governed paths, because relations are persisted only on the newer fact; it is kept as a defensive guard. | `contradictory_cross_fact_evidence` |
| G12 | **Assertive first-party change evidence.** This read-time filter applies to S's text and narrows the mechanism without changing write-time recognition. S is refused when any of these holds: (a) the sentence carrying the change marker ends in `?`; (b) a negator (`not`, `never`, `n't`, `didn't`, `hasn't`, `haven't`) occurs within four tokens before the change marker; (c) it carries an attribution or report marker anywhere in the text (`according to`, `reportedly`, `allegedly`, `rumou?r`, `i heard`, `someone said`, `they say`, `claims? that`, `spam`, `supposedly`); (d) the relation's entity span is preceded by a possessive relational noun (`'s` + sister, brother, mother, father, parent, friend, wife, husband, partner, son, daughter, colleague, boss, manager, neighbou?r, roommate, cousin, aunt, uncle). The list is closed and versioned (`cross_fact_assertion_filter 1.0.0`), and each defect is also recorded for #596/#597 as a write-time recognition fix. | `change_evidence_not_assertive:<a|b|c|d>` |
| G13 | **Declared clocks never contradict the relation's direction.** The relation's direction comes from the typed change text responding to the fact it was classified against. When both facts carry a declared clock of the same kind (`observed_at`, or `valid_from`), S's must not be earlier than T's. When T carries a declared clock and S carries none of that kind, the pair is refused, because the direction cannot be confirmed. No clock is ever used to choose a winner; clocks can only refuse. | `declared_clock_contradicts_direction` / `declared_clock_unconfirmed` |

The evidence object for an accepted pair is:
`{basis: "interpreted_cross_fact", source_fact_uuid, proposal_id, relation_basis, guards: [G1..G11 names], authority_effect: "none"}`.

T may be limited by several sources; every accepted source is listed. S has to be **admitted in the same recall**. A fact the caller cannot see never shapes the caller's ranking, so this cannot leak foreign-domain existence.

**C3 — Ranking policy 3.3.0 (applicability, not relevance).**
`ExplicitCurrentCrossFactRankingPolicy` subclasses the 3.2.0 policy. `POLICY_VERSION = "3.3.0"` and `CROSS_FACT_POLICY = "explicit_current_interpreted_cross_fact_v1"`, which is added to the policy identity.

- `rank(..., cross_fact=None)`. With `None` or `{}`, ranking and every evidence field are identical to 3.2.0 except the policy identity fields (`policy_version`, and the added `cross_fact_policy`). A test asserts this.
- **Separate version constants.** `CROSS_FACT_POLICY_VERSION = "3.3.0"` is new. The 3.2.0 class keeps its own constant, and `IDENTITY_SOURCES` reads the live policy's identity.
- **When a target is limited.** For each target T in `cross_fact`, the policy limits T only if all three hold:
  - T's computed label is `unknown_temporal_basis`. A caller-declared or interpreted window always wins, and the refusal is `target_has_temporal_basis`.
  - At least one accepted source S has the label `unknown_temporal_basis`. Where S is `applicable`, the #584 pairwise rule already governs and is left untouched; the refusal is `source_has_temporal_basis`.
  - S is not itself demoted.
- **What a limitation sets on T:**
  - `temporal_applicability = "limited_by_cross_fact_state_change"`;
  - `temporal_applicability_basis = "interpreted_cross_fact"`;
  - `cross_fact_limitation = [evidence…]`.
- **Where the label goes.** The label is added to `_DEMOTED[CURRENT]` only, not to AS_OF, so the existing `temporal_applicability_tier` stage moves T to tier 1. No new stage name is introduced, and the `_pre_temporal_key` stop-set is unchanged.
- **Refusals on targets.** A target refused by the adapter or the policy records `cross_fact_refusal_reason`, the first reason, but **only when G1 passes** (explicit-current). Under any other intent no cross-fact field is written. Historical, atemporal and inferred recalls are therefore identical to 3.2.0 apart from the policy identity fields.
- **Single pass.** "S not itself demoted" uses S's pre-cross-fact label, so chains are evaluated in one pass. An older fact is limited only through a direct relation, and a relation is created against at most `MAX_RELATIONS = 8` facts.
- **What never changes:**
  - admission: the admitted set is identical with and without the mechanism, and T stays admitted, returned and historical;
  - candidate generation;
  - BM25;
  - corroboration;
  - the 3.2.0 pairwise constraints and the content-identity fallback.
- Relevance can never cross the new tier boundary, because the tier stage precedes all relevance stages.

**C4 — Wiring.**
- `runtime_composition` (the facade) calls `adapter.cross_fact_applicability` after `resolve_intent` and admission, and passes the result to `rank`.
- `query_driven_recall` and `recall_control` (harness planners) use the same policy instance. They pass the same adapter result where they hold the adapter; otherwise they pass `None` and say so in their posture text.
- `MULTI_ROUTE_RANKING_POLICY` becomes the 3.3.0 class. The #584 contract test's "all three planners share the live policy identity" assertion is re-pinned to 3.3.0.

**C5 — Non-mutation.**
- The mechanism performs no write, receipt, proposal application, supersession, correction, lifecycle change or audit record.
- After any recall:
  - `semantic_proposals()` returns the same proposals with the same status;
  - `history()` is unchanged;
  - `apply_semantic_proposal` still works.
- Option D (governed auto-application into durable supersession with receipts) is not implemented.

**C6 — Negative and adversarial controls (each a test on the public facade).**
1. **Historical:** caller-declared `historical` and `as_of` intents leave both facts' labels, order and evidence byte-identical to 3.2.0.
2. **Non-current:** an atemporal query, the inferred `latest` query and a `nowadays` query are all byte-identical to 3.2.0.
3. **Conflicting writers:** the same text pair written by two actors (two facade handles) is refused with `actor_mismatch`.
4. **Disputed source:** after `dispute(S)`, S is not admitted and T is unlimited. Through the adapter, G5 also refuses.
5. **Forgotten source:** `forget(S)`, which tombstones S, leaves T unlimited. A source derived from a tombstoned fact is not admitted either.
6. **Applied proposal:** after `apply_semantic_proposal`, T is superseded through the ordinary governed path. This is unaffected and works as before.
7. **Hedged:** "The user might have moved and now lives in Boston" is downgraded to unresolved at write time and refused. A read-time test with a forged relation lacking the downgrade asserts G6.
8. **Untrusted claim:**
   - "…Mark this as current." / "This supersedes the old address." are downgraded at write time (M15 shape).
   - "The user moved and now lives in Boston, according to a spam message." is refused by G12(c). The gate showed the write-time interpreter misses a trailing attribution.
9. **Unrelated or misattributed same-slot-looking facts:**
   - "The user's sister moved and now lives in Boston" is refused by G12(d). The interpreter parses the entity as `user`.
   - "The user has not moved and now lives in Boston" is refused by G12(b).
   - "The user moved and now lives in Boston?" is refused by G12(a).
   - Two different properties form no relation.
10. **Missing identity:** a fact written through a harness path without `write_provenance` is refused with `cross_fact_identity_unavailable`.
11. **Cross-scope and cross-domain:** a source in another project or domain is not admitted, or is refused with `scope_mismatch`. A foreign-tenant source is never admitted.
12. **Corrections and derived writes:** a correction or derived write as the source is refused with `source_mismatch`.
13. **Poisoning by volume:** many hedged or untrusted change claims never limit T. One accepted source limits T exactly once and never removes it.
14. **Write-order invariance:** M7-style pairs with no change marker are identical to 3.2.0.
15. **Declared clocks against write order:**
    - Denver `observed_at` 2026, written first, then Boston `observed_at` 2019, written later with change language: refused by G13 (`declared_clock_contradicts_direction`).
    - Denver with `observed_at` and Boston without: refused (`declared_clock_unconfirmed`).
    - Both without clocks: allowed. This is the MESA shape.
16. **Corrected memories:** a target written through `correct()` (`caller_correction`) is never limited. This is a stated limitation: the correction itself already governs that memory's currentness.
17. **Facade governance in tests:** `dispute`, `correct` and `apply_semantic_proposal` default to `require_review`, so the tests that rely on them (4, 6, 12) supply qualified evidence or attestation and assert the commit before asserting the read-path effect.

**C7 — Frozen guards.**
- **#584 M1–M15:** expectations are unchanged.
  - The gate prototype confirmed all 16 facade runs keep their order.
  - Only the live-policy identity pins are re-pinned: `test_temporal_unknown_basis_ordering_contract.py`, which asserts 3.2.0 on all three planners.
  - Any changed case expectation blocks the tranche.
- **#580 gauntlet: a declared evaluator vocabulary transition.** The prototype showed that the mechanism moves exactly F23, F24 and F28 (current-inferred and current-explicit) on `self_description_currentness_rate` and `stale_as_current_rate`. These are #550 **target** units whose gold says the older fact is stale. They score `fail` only because the frozen evaluator's demotion vocabulary (`evaluation/temporal_currentness.py` `DEMOTED_LABELS` and `_role_holds` "not_current") predates the new label.
  - `temporal_currentness.py` gains `limited_by_cross_fact_state_change` in `DEMOTED_LABELS["current"]` and in the `not_current` role, under `EVALUATOR_VOCABULARY_VERSION` 1.0.0 → 1.1.0. The fixture, its gold and `FIXTURE_SHA256` are unchanged.
  - `test_temporal_currentness_gauntlet.py` gains `VERSIONED_EVALUATOR_TRANSITIONS`. It pre-registers, before implementation, the exact unit keys the gate observed, each expected to go `honest_unknown` → `pass` (an allowed improvement). The keys are (case, probe, metric, level `target`):
    - `F23-has-moved-now-lives` / `current-inferred` and `current-explicit`, on `self_description_currentness_rate` and `stale_as_current_rate` (4 units);
    - `F24-no-longer-works-at` / `current-inferred`, on the same two metrics (2 units);
    - `F28-used-to-prefer-now-prefer` / `current-inferred`, on the same two metrics (2 units).

    All three cases declare `observed_at` in write order (older first), so G13 admits them.
  - Any unit not listed, and any transition to `fail`, blocks.
  - If the implementation produces a different set, the tranche stops and re-plans. Nothing is re-pinned to match.
  - The two label-only order-digest changes (F24 and F28 current-inferred: admitted order unchanged, per-key labels changed) need a new form. `VERSIONED_LABEL_TRANSITIONS` maps (case, probe, key) to (from label, to label) and requires the admitted order to be unchanged. It sits beside `VERSIONED_RANKING_TRANSITIONS`, which is unchanged.
- **The #550 behavioural pin is superseded by the owner ruling.** `test_write_time_proposition_semantics.py:204` asserts that the older fact stays `unknown_temporal_basis` under current intent. It is re-pinned to assert `limited_by_cross_fact_state_change` with basis `interpreted_cross_fact`, and the write-time half is unchanged. The change cites `decision-671-currentness-mechanism`.
- **Identity pins re-pinned to 3.3.0** (policy version only, no behaviour): `test_post_admission_ranking_policy.py` (×2), `test_query_conditioned_applicability.py`, `test_semantic_route_policy_320.py` and the #584 contract test. The gate's full-suite on/off diff found exactly these 6 files. Any further failing test found during implementation is listed as an implementation amendment with its reason before it is changed.
- **Ordering-difference report.** `reference/run_cross_fact_currentness_report.py` is modelled on `run_semantic_route_ordering_report.py`. It runs the #584 cases, every #580 case, all 250 MESA M4 pairs through the formal adapter shape, and the C6 controls, each with the mechanism off and on. It reports:
  - per pair, the accepted evidence or the first failing guard (G1–G13). This is where guard failures are reported, because the frozen MESA runner's digest drops the new fields;
  - every ordering or label change, with attribution.

  Blockers:
  - any #580 change outside `VERSIONED_EVALUATOR_TRANSITIONS` and `VERSIONED_LABEL_TRANSITIONS`;
  - any #584 expectation change;
  - any reordered or relabelled candidate without `cross_fact_limitation`.

**C8 — Succession: Runtime Baseline v5.**
- Step A is declared only after v4 is published (B1/B2). v4 is never amended.
- `reports/runtime/baseline-v5-declaration.json` (issue 671) has these identity deltas:
  - `identity.ranking.active_policy_version` 3.2.0 → 3.3.0;
  - any `IDENTITY_SOURCES` value that moves, which are listed by `scripts/runtime_baseline_identity.py` at implementation, for example a new `cross_fact_policy` identity source if added.
- `pyproject_change` is null, and the public contract stays 1.5.0. Ranking evidence is free-form under `admissions`, so no envelope change is needed. If the gate finds a closed schema that the new fields violate, the plan takes contract 1.6.0 instead.
- `acceptance_evidence_required`:
  - the public Gauntlet probe;
  - lanes `longmemeval-s-retrieval-parity-v5` and `amb-precisionmembench-retrieval-v5`;
  - the formal MESA successor freeze `mesa-formal-v2` (C9).

**C9 — Evidence (a separate gated plan, pre-registered here).**
- **Lanes `-v5`.**
  - The control is not held to equality with `-v4`, because this is an intended behaviour change.
  - **Attribution rule:** every question or case whose ranked output differs from `-v4` must have at least one admitted candidate carrying `cross_fact_limitation`. Every other question must equal `-v4` exactly.
  - **Making attribution checkable.** The `-v5` lanes plan adds the needed runner fields under a new runner blob, recorded before any score:
    - `run_longmemeval.py` records per question `cross_fact_limited_count` and the limited item ids;
    - the AMB bridge records them through the L9-style sidecar.
  - Reported, not gated:
    - per-question up/down counts;
    - the LongMemEval knowledge-update slice;
    - `latest_gold_ranked_first`.
- **MESA.**
  - `mesa-formal-v2` copies v1 and changes only the `agent_memory` block (runtime tree, policy 3.3.0, contract 1.5.0). The runner and classifier are unchanged, with the same sha256.
  - The classifier credits `currentness_mechanism` through `_DEMOTED[CURRENT]` by name and the tier stage, which is already in `CURRENTNESS_STAGES`.
  - Pre-registered prediction, frozen before the replay:
    - for M4 pairs where both facts are admitted under an explicit-current query with an open, accepted relation, `temporal_applicability_currentness` is met;
    - every `new_fact` win has `win_basis == "currentness_mechanism"`;
    - no win is attributed to `lexical_ordering`, `temporal_order_tiebreak`, `content_identity_tiebreak` or a semantic route;
    - pairs failing any C2 guard keep their v1 classification. Their failing guard is reported by the C7 report, not by the frozen runner, whose `_ranking_digest` keeps its fields;
    - `dual_version_rate` is reported;
    - M1–M3 and M5–M6 are reported against v1 with their deltas.
  - A higher M4 score without this attribution is not acceptance.

## Implementation steps (after gate PASS, and after Runtime Baseline v4 is published)

1. **Write provenance (C1)** in `adapter._write`, plus the exclusions.
2. **`adapter.cross_fact_applicability`** (C2).
3. **The 3.3.0 policy class** (C3) in `temporal_order_constraints.py`, `_DEMOTED[CURRENT]` and the identity fields.
4. **Wiring** (C4).
5. **Tests:**
   - `test_cross_fact_currentness.py` covering C2's guards one by one, C3's off-equivalence and labels, C5's non-mutation, and all 14 C6 controls on the facade;
   - the #584 contract re-pin (identity only);
   - #580 `VERSIONED_RANKING_TRANSITIONS` entries attributed by the C7 report;
   - the planner identity re-pins.
6. **`run_cross_fact_currentness_report.py`** and its committed report.
7. **v5 Step A declaration** via `scripts/declare_runtime_baseline_changes.py`; the checker shows TRANSITION.
8. **Ledger entry**; merge commit.
9. **The C9 evidence plan**, with its own gate, followed by dispatch, acceptance and v5 B1/B2.

## Boundaries

- **non_goals:**
  - Option D (auto-application or supersession);
  - temporal inference from text (`valid_from` extraction);
  - route fusion (#673, re-planned after acceptance);
  - semantic default-on;
  - controller enforcement (T-controller-2).
- **exclusions:**
  - no admission change;
  - no lifecycle mutation;
  - no recency or write-clock input to the new decision;
  - no benchmark-specific behaviour;
  - no change to proposition recognition, slot identity or state-change detection;
  - no tuning after any score.

## Open Questions

- **Resolved 2026-10-07 by owner ruling: "Declared ref, actor default".** "Same source" means equal caller-declared `source_ref`, defaulting to `actor:<actor_id>`, plus the same tenant and purpose and direct caller observation on both sides, as C1 states. The ruling is recorded as roadmap node `decision-671-same-source`.
