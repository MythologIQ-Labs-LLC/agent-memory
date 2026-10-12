# #773 Slice S1: Explicit-target governed current-context selector

**Status: COMMITTED / CHANGES REQUIRED until independently executed and qualified.**

Base: `9b025f945e7ec4a1e349e56bba251e3122413e88` (frozen #770 v7 implementation).  
Candidate: `implementation/773-explicit-current-context-selector-no-ci`.

## Product behavior implemented

`ConfiguredCompositionRuntime.current_served_context(query, context,
budget=N, reference_time="2026-10-12T12:00:00Z")` executes normal
`multi_route_recall` with a caller-declared current *reference instant*
and canonical governed admission. It selects a bounded subset of
`ranked_admitted` and excludes evidence that the existing versioned ranking
policy **already classifies as known inapplicable** to that current instant:

- `outside_target_interval` (including `valid_until <= instant`);
- `prospectively_applicable` (declared future `valid_from > instant`);
- `limited_by_cross_fact_state_change` when the existing guarded
  cross-fact currentness policy establishes the limitation.

An excluded candidate remains in canonical memory and is **still
historically retrievable**. This is *served-context selection*, not new
admission/refusal/deletion semantics. If the existing ranking policy cannot
establish applicability, `unknown_temporal_basis` remains unknown; this
slice does not invent positive currentness evidence.

The caller must supply an explicitly timezone-aware full ISO-8601 date/time.
Missing, unzoned and invalid instants fail closed before issuing a recall.
It is **not** a trusted live clock: the caller or consuming application is
responsible for establishing the target time. The system does not infer "now"
from wall clock, benchmark labels, stored text, or answer keys.

The immutable `CurrentServedContext` result includes `served_refs`,
the declared reference time, counts of known-inapplicable and
unknown-applicability candidates, `complete_evidence_attested=False`,
`authority_effect="none"`, and selection policy version `0.1.0`.
No positive stopping, answer refusal inference, or completeness claim.
It does not solve the G1 relevance/no-answer deficit or G6 historical
rank-one deficiency.

## Isolation and changed files

- Only `reference/agentmem_ref/runtime/runtime_composition.py` is an
  updated protected runtime source, and the method is **opt-in**.
- `reference/tests/test_773_current_served_context.py` adds 10 test
  methods, committed before its implementation. The tests cover expired
  and future windows, inclusive start/exclusive end, timezone-equivalent
  instants, missing or naive timestamp rejection, bad budget, historical
  noninterference, selection emptiness not proving answer abstention, and
  lack of mutation of the default recall result.
- `reports/runtime/proposals/773-explicit-current-served-context-overlay.json`
  records the exact changed protected blob and explicitly refuses to
  silently re-pin frozen #770 v7 evidence.

This changes a protected runtime tree. The existing v7 baseline declaration
must **not** be rewritten. A separate sanctioned successor declaration and
independent exact-head qualification are prerequisites to any main merge.

## Falsification and qualification

Run in a trusted full checkout, with no GitHub Actions:

```bash
python -m unittest discover -s reference/tests -t reference \
  -p test_773_current_served_context.py
python -m unittest discover -s reference/tests -t reference \
  -p test_runtime_composition.py
python -m unittest discover -s reference/tests -t reference
```

The current versioned applicability label and its clock/ref provenance
must be verified for every selected/withheld candidate. A successful focused
suite **does not** establish privacy, retrieval quality or publication
readiness. The separate #771 post-hoc scorer can be used to compare the
actual served IDs at the same budgets, but must not feed gold into the
selector.

Evaluate both unchanged Halcyon v1.1 and the separately committed
Cedarline v1.1 (the initial Cedarline v1 no-answer C11 question had a
pre-execution annotation ambiguity, preserved and corrected in v1.1).
Cedarline's actual gold and first author's query strings cannot be used
to tune source logic. Require independent new holdout cases and original
AMB/LongMemEval guard replays before broader acceptance.

**Hard negative controls**: A historical question must still retrieve the
previously true valid interval; a correction invalidates a prior error and
cannot be reinstated as valid history; missing reference time must fail;
unknown currentness may not be announced as verified; standard
`multi_route_recall` must retain original admission and ranking behavior;
hidden and refused memories cannot enter the selected set.

**Status:** Source code and tests committed. No actual Python executions,
quality-score improvements, benchmark parity, or formal protected-runtime
acceptance are claimed here.
