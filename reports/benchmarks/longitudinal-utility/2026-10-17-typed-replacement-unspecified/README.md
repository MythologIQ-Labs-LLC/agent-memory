# Longitudinal utility lane: typed-replacement default for unspecified recall (#819 lane 5)

**Status: experimental candidate, self-measured, not independently evaluated.** Opt-in only;
the default, the contract version, the Runtime Baseline and the hidden e6 evaluation are
untouched. Local only; no hosted CI, no model, no network.

Preregistration (committed before any runtime change): [`PREREGISTRATION.md`](PREREGISTRATION.md).

## What was measured

`reference/fixtures/benchmarks/longitudinal-utility/scenarios-v1.json`: 13 deterministic
scenarios, 40 probes. Each session is a fresh `AgentMemory.open` on the same durable root
(so recall crosses restarts). Writes use only public `remember` / `correct` / `forget`;
probes use only public `recall(query, budget=5)`. Expectations name writes and are read only
by the scorer (`reference/agentmem_ref/evaluation/longitudinal_utility.py`).

A probe succeeds when it has none of: `stale_used` (a superseded / corrected / replaced write
is returned unlabelled, or outranks every current write), `incorrect_supersession`,
`missing_current`, `missing_dependency`, `history_lost`, `isolation_violation`,
`unnecessary_abstention`. "Labelled" uses the temporal-currentness gauntlet's own
`not_current` definition.

## Baseline (`main` `38f6a7d`): 31/40

| Class | Count |
|---|---:|
| stale_used | 9 |
| incorrect_supersession, missing_current, missing_dependency, history_lost | 0 |
| isolation_violation, unnecessary_abstention | 0 |
| cross-session recall of needed writes | 48/48 |

What already works: governed `correct()` (both `state_change` and `error_correction`) makes the
old value `superseded_not_current` across restarts; historical intent returns it as history;
scope isolation, forget, multi-valued typed facts, different-subject typed facts, a parked
(unreviewed) correction and long-gap cross-session recall all succeed.

**Highest-impact deficiency.** 6 of the 9 failures share one mechanism. An agent records a
change on a *new* reference in a later session with a caller-declared typed proposition
(`assertion: "change"`, `replaces_value`). The write-time state-change relation exists and
passes every #671/#732 guard. But the agent asks the way agents ask, without a temporal cue
("What diet does the user follow?"), the interpreter resolves `atemporal_or_unspecified`, and
`cross_fact.evaluate` returns nothing outside explicit-current intent (G1). The replaced value
is returned **first and unlabelled**. Adding "now"/"currently" to the same query fixes it, so the
capability exists and is gated off for the most common phrasing.

Other failures, recorded and not addressed: untyped text changes ("standup moved to 10am",
2 probes; no typed evidence exists), and an interpreter misread ("When will … ship?" →
`prospective`, low confidence; 1 probe).

## Candidate

`AgentMemory.open(..., unspecified_intent_currentness="typed_replacement")` (default `"off"`).
For a recall with **no temporal cue at all** (mode `atemporal_or_unspecified`, posture
`unspecified`):

- `cross_fact.evaluate` runs with the same guards G2–G13 but accepts **typed relations only**
  (caller-declared or extracted). An interpreted text-only relation is refused with
  `unspecified_intent_requires_typed_relation`.
- Since this intent evaluates no applicability, "no validity window" stands in for the
  explicit-current `unknown_temporal_basis` precondition; a declared window refuses as before.
- A limited target is labelled `limited_by_cross_fact_state_change`, carries
  `cross_fact_activation: "unspecified_intent_typed_replacement_v1"` (the recorded inference
  ADR-039 requires), and takes the demoted tier. It stays admitted and returned within budget.

Unchanged: admission, refusals, lifecycle, proposals (stay `open`), history, explicit-current
and historical and inferred-intent recalls (byte-identical on/off), and every recall when the
option is off. No recency signal and no text interpretation is added.

Diff: `adapter.py` (+option, passes flag), `cross_fact_currentness.py` (activation),
`temporal_order_constraints.py` (labels + one tier override), `api/surface.py` (opt-in).

## Result (same fixture, same budget, same commit)

| Arm | Success | stale_used | incorrect_supersession | history_lost | isolation_violation |
|---|---:|---:|---:|---:|---:|
| A baseline on `main` | 31/40 | 9 | 0 | 0 | 0 |
| A baseline on candidate | 31/40 (byte-identical report) | 9 | 0 | 0 | 0 |
| C `typed_replacement` on candidate | **36/40** | 4 | 0 | 0 | 0 |

Paired per-case: **5 fixed, 0 broken**, 35 unchanged (exact sign test, one-sided p = 0.031;
two-sided p = 0.0625). Fixed: `atlas-ship-date/p4`, `teammate-languages/p2`,
`diet-change/p1`, `diet-change/p2`, `language-history/p1`. Preregistered target was ≥4 of 6.

Not fixed, by design: `atlas-ship-date/p2` ("When will the Atlas beta ship now?") resolves to
*inferred* low-confidence atemporal intent (conflicting "will"/"now" cues), outside the
preregistered class. Widening to inferred intent was not tried, to avoid tuning to the fixture.

Guard probes unchanged under C: hedged change, other `source_ref`, other scope, the
`attributed_to_other` hearsay write, multi-valued allergies, Alice vs Bob, historical probes,
and the history-seeking unqualified probe ("Which favorite languages have I mentioned…?")
still return the replaced value as labelled history.

## Tests

- `reference/tests/test_longitudinal_utility.py` (7): scorer semantics, fixture never leaks
  expectations to runtime calls, deterministic run.
- `reference/tests/test_unspecified_typed_replacement.py` (6): off-by-default equivalence;
  label + activation + demotion while still returned; proposals stay open and history is
  unchanged; explicit-current / historical / inferred byte-identical on vs off; interpreted
  relation refused under unspecified; hedged / other source / attributed / declared-window
  guards still refuse; unknown mode rejected.
- Focused existing suites (cross-fact, temporal, ranking, facade, API, contracts, recall,
  propositions): 629 tests OK. Full suite vs `main`: no new failures after the layout fix (4 pre-existing failures on both); see `TEST-RECORD.md`.

## Limits

- Self-authored fixture, 40 probes, one author. The fix can only act where typed
  propositions exist: callers who declare them, or an opted-in extractor. Default
  LongMemEval and AMB bridges declare none. With the option on, both lanes were measured
  identical to off and to `main` (AMB 15/77 case-identical; LongMemEval-S 500 session and turn
  row-identical in ranking and metrics; activation fired 0 times): see
  [`external-lanes/README.md`](external-lanes/README.md). The same holds for any untyped workload.
- Demotion orders within the returned budget; with a very small budget the labelled replaced
  value can fall out of `returned` (it stays in `admitted`).
- Not an independent evaluation; e6 was neither read nor used.

## Reproduce

```bash
cd reference
PYTHONPATH=. python run_longitudinal_utility.py --arm baseline --out A.json
PYTHONPATH=. python run_longitudinal_utility.py --arm typed_replacement --out C.json
PYTHONPATH=. python -m unittest tests.test_longitudinal_utility tests.test_unspecified_typed_replacement
```
