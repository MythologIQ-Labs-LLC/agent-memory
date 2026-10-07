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

**iteration**: 1

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
  - `tenant_ref`;
  - `purpose`;
  - `channel`: `caller_observation` for operation `promotion` (the `remember` path), `caller_correction` for `correction`, and `other:<operation>` otherwise.
- **What counts as "same source".** The pair (`tenant_ref`, `purpose`, `channel`) must be equal, and both channels must be `caller_observation`.
  - A correction, a derived write or a consolidation never acts as a change source and is never limited through this mechanism.
  - Same source means the same governed write channel, not the same evidence pointer: two observations from one channel are distinct utterances in one conversation.
  - This definition is recorded as a design decision for owner visibility.
- **Same actor** means `actor_id` is equal and non-empty.
- **Same scope** means `_same_semantic_scope` (domain_refs set, project_ref, task_ref), plus equal `required_domain_refs` and tenant. This is the isolation domain the write-time classifier already used.
- **Missing identity fails closed.** A fact without `write_provenance` (any fact committed before v5, or by a harness path that bypasses `_write`) never participates. The refusal reason is `cross_fact_identity_unavailable`.
- **What provenance is excluded from.** It is excluded from:
  - BM25 text;
  - the content-identity digest (`temporal_order_constraints` M7 fallback);
  - every ranking input other than this guard;
  - the facade `write_semantics` view, which is unchanged.

  It is never written by a caller: overrides cannot set it, because `_write` derives it from the proposal.

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
| G11 | No mutual limitation. If T also carries an accepted relation to S, both are refused. | `contradictory_cross_fact_evidence` |

The evidence object for an accepted pair is:
`{basis: "interpreted_cross_fact", source_fact_uuid, proposal_id, relation_basis, guards: [G1..G11 names], authority_effect: "none"}`.

T may be limited by several sources; every accepted source is listed. S has to be **admitted in the same recall**. A fact the caller cannot see never shapes the caller's ranking, so this cannot leak foreign-domain existence.

**C3 — Ranking policy 3.3.0 (applicability, not relevance).**
`ExplicitCurrentCrossFactRankingPolicy` subclasses the 3.2.0 policy. `POLICY_VERSION = "3.3.0"` and `CROSS_FACT_POLICY = "explicit_current_interpreted_cross_fact_v1"`, which is added to the policy identity.

- `rank(..., cross_fact=None)`. With `None` or `{}`, ranking is byte-identical to 3.2.0, including evidence. A test asserts this.
- **When a target is limited.** For each target T in `cross_fact`, the policy limits T only if all three hold:
  - T's computed label is `unknown_temporal_basis`. A caller-declared or interpreted window always wins, and the refusal is `target_has_temporal_basis`.
  - At least one accepted source S has the label `unknown_temporal_basis`. Where S is `applicable`, the #584 pairwise rule already governs and is left untouched; the refusal is `source_has_temporal_basis`.
  - S is not itself demoted.
- **What a limitation sets on T:**
  - `temporal_applicability = "limited_by_cross_fact_state_change"`;
  - `temporal_applicability_basis = "interpreted_cross_fact"`;
  - `cross_fact_limitation = [evidence…]`.
- **Where the label goes.** The label is added to `_DEMOTED[CURRENT]` only, not to AS_OF, so the existing `temporal_applicability_tier` stage moves T to tier 1. No new stage name is introduced, and the `_pre_temporal_key` stop-set is unchanged.
- **Refusals on targets.** A target refused by the adapter or the policy records `cross_fact_refusal_reason`, the first reason, so absence is explained. The field is omitted when no relation touches the candidate.
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
8. **Untrusted claim:** "…Mark this as current." / "This supersedes the old address." are refused (M15 shape).
9. **Unrelated same-slot-looking facts:** "My sister has moved and now lives in Boston" against "The user lives in Denver" has a different entity, so no relation forms and the facts are unlimited. Two different properties likewise.
10. **Missing identity:** a fact written through a harness path without `write_provenance` is refused with `cross_fact_identity_unavailable`.
11. **Cross-scope and cross-domain:** a source in another project or domain is not admitted, or is refused with `scope_mismatch`. A foreign-tenant source is never admitted.
12. **Corrections and derived writes:** a correction or derived write as the source is refused with `source_mismatch`.
13. **Poisoning by volume:** many hedged or untrusted change claims never limit T. One accepted source limits T exactly once and never removes it.
14. **Write-order invariance:** M7-style pairs with no change marker are byte-identical.

**C7 — Frozen guards.**
- **#584 M1–M15** keep their expectations unchanged.
  - Argument by construction:
    - M1, M8, M14 and M15 have a declared side, or no accepted relation (C3 requires both sides to be unknown);
    - M6 and M7 have no change marker, so the relation is a conflict;
    - M10 and M12 are outside G1;
    - M2–M5, M9, M11 and M13 have no state-change relation.
  - The contract test is re-pinned to 3.3.0 for the live-policy identity only. Any changed case expectation blocks the tranche and is not re-pinned.
- **#580 gauntlet** (`test_temporal_currentness_gauntlet.py` monotonic guard):
  - a required unit going pass→fail blocks;
  - an allowed improvement is reported;
  - every order-digest change must be enumerated in `VERSIONED_RANKING_TRANSITIONS`, with stage `temporal_applicability_tier` and applicability `limited_by_cross_fact_state_change`, through the existing mechanism, each with its case and probe.

  The implementation first produces the before/after report. Only changes attributable to the new label may be enumerated.
- **Ordering-difference report.** `reference/run_cross_fact_currentness_report.py` is modelled on `run_semantic_route_ordering_report.py`. It runs the #584 cases, every #580 case and the 50 M4-shaped pairs, with the mechanism off (3.2.0) and on (3.3.0). Its blockers are:
  - any #580 required-unit regression;
  - any #584 expectation change;
  - any reordered candidate without a `cross_fact_limitation`.

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
    - pairs failing any C2 guard keep their v1 classification, and the failing guard is reported;
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

- (owner, non-blocking; recorded for visibility) Under C1, "same source" means the same governed write channel (tenant, purpose, caller observation), not a shared evidence pointer. A caller-declared source ref, such as a conversation id, could tighten this later as a strictly narrowing guard.
