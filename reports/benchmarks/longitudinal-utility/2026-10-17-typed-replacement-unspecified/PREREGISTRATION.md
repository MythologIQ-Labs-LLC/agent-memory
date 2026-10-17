# Longitudinal utility lane: preregistration (#819 lane 5)

Committed before any runtime change. Base: `main` `38f6a7d`. Local only; no hosted CI, no
model, no network, no hidden-cohort (e4/e5/e6) material.

## Fixture

`reference/fixtures/benchmarks/longitudinal-utility/scenarios-v1.json`, 13 scenarios, 40 probes,
deterministic (`generate_scenarios.py` regenerates it). Each session is a fresh
`AgentMemory.open` on the same durable root. Writes go through public `remember`/`correct`/`forget`;
probes go through public `recall` with budget 5. Expectations name writes and are read only by
the scorer (`reference/agentmem_ref/evaluation/longitudinal_utility.py`).

Families: preference_change, corrected_fact, superseded_commitment, evolving_project,
no_false_supersession, isolation, withdrawn, cross_session_recall, untyped_episodic_change,
governed_admission, history_preservation.

## Baseline observation (`baseline-main-38f6a7d.json`)

31/40 succeed. All 9 failures are `stale_used`; no isolation, supersession, dependency,
history or abstention failure. Six of the nine share one mechanism: a **caller-declared typed
`change`** written on a new reference in a later session (the guarded #671/#732 cross-fact
evidence exists and passes G2–G13), but the probe is phrased the way agents ask
("What diet does the user follow?"), the interpreter resolves `atemporal_or_unspecified`, and
`cross_fact.evaluate` returns nothing outside explicit-current intent (G1). The replaced value
is returned first and unlabelled.

Out of scope for this candidate (recorded, not fixed): untyped text changes
("standup moved to 10am", 2 failures; no typed evidence exists, and inferring it from text is
an authority risk) and intent-interpreter misreads ("When will … ship?" → prospective;
"… ship now?" → atemporal; 1 failure each in atlas-ship-date).

## Hypothesis and candidate

ADR-039: "Unspecified must not silently mean current unless the policy explicitly justifies
that default for the query class and records the inference." The candidate is that
justification for one narrow class: an unspecified-intent recall whose admitted set contains a
**typed** (caller-declared or extracted) open state-change relation that passes every existing
cross-fact guard G2–G13. Only then is the replaced fact labelled
`limited_by_cross_fact_state_change` and moved below non-limited facts. Opt-in per handle
(`unspecified_intent_currentness="typed_replacement"`), default `off`. No recency signal, no
text interpretation, no admission change, no mutation; the replaced fact stays returned and
labelled, and its activation is recorded on the ranking evidence.

## Arms

- A `baseline`: defaults (main and candidate head; must be identical).
- C `typed_replacement`: candidate head with the opt-in.

## Acceptance (all required)

1. A on the candidate head is byte-identical to A on main for this fixture.
2. C fixes ≥4 of the 6 typed-change `stale_used` probes.
3. C introduces zero new failures of any class, in particular `incorrect_supersession`,
   `history_lost`, `isolation_violation`, and zero change in the `typed-change-guards`
   (hedged, other source, other scope) and historical probes.
4. Existing cross-fact, temporal-order, ranking, facade and API test suites pass unchanged.
