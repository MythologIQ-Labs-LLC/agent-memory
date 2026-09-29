# #585 temporal query intent interpreter 1.1.0: targeted evidence

Evidence class: repository-owned conformance and targeted replay. It is not independent external validation, and it does not accept ADR-039, which remains Proposed.

- Interpreter: `agent-memory-deterministic-temporal-cues` `1.0.0` → `1.1.0`
- Base: `main` @ `187ab271006024eed311c697f903bfffd1930623`
- Frozen adversarial oracle: `reference/fixtures/runtime/temporal-query-intent-v1.1-adversarial.json`, committed before the implementation
- Machine-readable results: [`evidence.json`](evidence.json)

## #580 temporal/currentness gauntlet (211 assertions)

| | required pass | required fail | target pass | target honest_unknown | target fail |
|---|---|---|---|---|---|
| `main` (1.0.0) | 184 | 1 | 9 | 12 | 5 |
| 1.1.0 | 184 | 1 | 11 | 13 | 2 |

- **No required regressions.** The one required failure is the pre-existing F30 `currently-live` lexical invariant, which belongs to #583. It is unchanged.
- **Three target improvements, all for the intended reason.**
  - `A5/plain-now-inferred` ("Where do I live now?") and `F28/plain-now` ("What does the user prefer to drink now?") intent: fail → pass. Clause-final temporal `now` is now query-language-explicit current, `inferred`/`high`, and orders temporally.
  - `F28/plain-now` semantic: fail → honest_unknown. With current ordering active, the remaining gap is the memory's unknown temporal basis (#584), not interpretation.
- **Admitted order changes: 0 of 50 probes.** Observation digests change only in interpreter-owned intent fields (`interpreter_version`, `evidence`, `intent_basis`, `spans`, `declined_spans`). The #580 monotonic comparator now exempts exactly that, and only when the interpreter version changed.

## LongMemEval_S (500 questions, cleaned release)

Only 7 questions change resolved intent between 1.0.0 and 1.1.0:

| question | change | reason |
|---|---|---|
| `cf22b7bf` "…since I started going to the gym consistently?" | prospective/high → unspecified | `going to` declined as `habitual_or_motion` (the known regression) |
| `a2f3aa27` "How many followers do I have on Instagram now?" | current/low → current/high | clause-final temporal `now` is query-language-explicit |
| `031748ae` "…How many engineers do I lead now?" | current/low → current/high | same |
| `f685340e` "…previously? How often do I play now?" | historical/high → ambiguous | two stated modes: the conflict is preserved |
| `50635ada` "…previous … status before I got the current status?" | current/high → ambiguous | `current` co-occurs with `before`, so the stated-mode conflict rule applies |
| `gpt4_93159ced` and `_abs` "…before I started my current job…" | current/high → ambiguous | same |

The last three are side effects of the stated-mode conflict rule. In each, `current` names a referent ("my current job") rather than asking about present state, so losing current ordering there is conservative. No ambiguous result orders temporally.

Retrieval replay of those 7 questions, `agent_memory` backend, turn and session granularity, with temporal metadata `none` and with `source_observed_at`: every top-50 ranking is identical to `main`, and the headline metrics are identical. So 1.1.0 corrects interpretation without moving LongMemEval_S ranking. The `cf22b7bf` rank change recorded on the #587 branch came from removing lexical cue tokens (#583), not from intent.

Not rerun here: the full 500-question LongMemEval_S and M profiles, and AgentMemBench. Ranking is identical on every question whose intent changed, and unchanged interpretation cannot change ranking, so a full replay is left to the later #580 cycle.

## Boundary

- `ranking_policy.py` is unchanged. BM25 still scores every query token, including consumed cue words. A test asserts that a memory containing `currently` still outscores an otherwise identical one for "Where does the user currently live?".
- The query is never rewritten. Spans are evidence for a redesigned #583.
- Query-language intent is never caller authority. Historical-evidence admission requires `intent_basis = caller_declared`.
- PR #587 remains Draft/HOLD. It was not reused, merged or cherry-picked.
