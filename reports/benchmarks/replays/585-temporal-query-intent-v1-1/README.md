# #585 temporal query intent interpreter 1.1.0: targeted evidence

Evidence class: repository-owned conformance and targeted replay. It is not independent external validation, and it does not accept ADR-039, which remains Proposed.

- Interpreter: `agent-memory-deterministic-temporal-cues` `1.0.0` → `1.1.0`
- Base: `main` @ `187ab271006024eed311c697f903bfffd1930623`
- Oracles, both frozen before the code they judge:
  - initial `FROZEN_PREIMPLEMENTATION_ORACLE`: `temporal-query-intent-v1.1-adversarial.json` @ `8a6f517`. It is preserved byte-identical and pinned by sha256.
  - reviewed `FROZEN_POST_REVIEW_PRE_REMEDIATION_ORACLE`: `temporal-query-intent-v1.1-reviewed-oracle.json` @ `090582d`. It supersedes 23 field expectations in 10 initial cases, which the PR #630 review required, and adds 12 cases. A test asserts that the initial-vs-reviewed differences equal the recorded list exactly.
- Machine-readable results: [`evidence.json`](evidence.json)

## Posture contract

| `intent_basis` | posture | caller authority / widens admission |
|---|---|---|
| `caller_declared` | `explicit` | yes |
| `query_language_explicit` | `explicit` (confidence `None`) | **no** |
| `query_cue_inference` | `inferred` | no |
| `none` | `unspecified` | no |

## #580 temporal/currentness gauntlet (211 assertions)

| | required pass | required fail | target pass | target honest_unknown | target fail |
|---|---|---|---|---|---|
| `main` (1.0.0) | 184 | 1 | 9 | 12 | 5 |
| 1.1.0 | 183 | 2 | 9 | 13 | 4 |

- `A1/current-inferred` intent, required: pass → fail. **Superseded frozen gold.** The #580 gold encodes the 1.0.0 posture `inferred` for "Who is the current chief executive officer…?". 1.1.0 resolves it as `explicit`/`query_language_explicit` with the same mode and the same ordering. The #580 comparator enumerates this unit as the only permitted gold supersession.
- `F28/plain-now` semantic, target: fail → honest_unknown. Temporal `now` now orders as current, so the remaining gap is the memory's unknown temporal basis (#584).
- The two plain-`now` intent targets now resolve `current`/`explicit`/orders temporally. They still fail only because the frozen gold posture is `inferred`.
- **Admitted order changes: 0 of 50 probes.**
- Intent changes versus the frozen baseline are exactly two enumerated transitions:
  - 24 probes: `inferred/high/query_cue_inference` → `explicit/None/query_language_explicit`, with identical admitted, candidate and per-key evidence;
  - 2 plain-`now` probes: `inferred/low` → `explicit`, `orders_temporally` false → true. Only per-key evidence changes.

## LongMemEval_S (500 questions, cleaned release)

28 questions change resolved intent:

| transition | count | cause |
|---|---|---|
| current `inferred/high` → current `explicit` | 21 | query-language explicit posture; mode and ordering unchanged |
| current `inferred/high` → historical `inferred/low` | 3 | `gpt4_93159ced`, `gpt4_93159ced_abs`, `50635ada`: `current` after `before` is declined as `referent_modifier` |
| current `inferred/low` → current `explicit` | 2 | `a2f3aa27`, `031748ae`: clause-final temporal `now` |
| historical `inferred/high` → ambiguous | 1 | `f685340e` "…previously? How often do I play now?": genuinely two stated modes |
| prospective `inferred/high` → unspecified | 1 | `cf22b7bf` "…since I started going to the gym…": `going to` is declined as `habitual_or_motion` |

The three false ambiguities from the first revision are gone. Those questions now resolve as historical/low, because `current` names the referent (`my current job`, `the current status`).

Retrieval replay of all 28, `agent_memory` backend, turn and session granularity, with temporal metadata `none` and with `source_observed_at`: every top-50 ranking is identical to `main`, and the headline metrics are identical.

Not rerun here: the full LongMemEval_S/M profiles and AgentMemBench. Ranking is identical on every question whose intent changed, so a full replay is left to the later #580 cycle.

## Boundary

- `ranking_policy.py` is unchanged, and BM25 still scores consumed cue words. A test asserts this.
- The query is never rewritten. Spans are evidence for a redesigned #583.
- Historical-evidence admission requires `intent_basis = caller_declared`. A test asserts that explicit-posture query-language intent in `historical` and `as_of` modes does not widen admission.
- PR #587 remains Draft/HOLD and was not reused.
