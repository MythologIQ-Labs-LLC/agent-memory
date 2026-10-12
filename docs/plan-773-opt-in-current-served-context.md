# #773 Slice S1: Explicit-target governed current-context selector

**Status: REPAIRS ADOPTED / CHANGES REQUIRED. Independent review applies to the prior runtime blob; policy 0.2.0 requires exact-head revalidation.**

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
`authority_effect="none"`, and selection policy version `0.2.0`.
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

## Independent defects reconciled

Claude Code review `validation/773-current-context-selector-review` @
`d56665ec5bde2d494dc05319cf7f356cb6fe7e4e` discovered:
- **D773-1:** a current-context query targeted *before* a governed state
  change, but current-state admission had already refused the previously
  true value. The method now fails closed, directing the caller to
  historical/as-of retrieval, rather than silently serving the later value.
  Out-of-domain and error-corrected records do not create false flags.
- **D773-2:** a known-ended validity window can still answer an affirmative/
  negative historical applicability question ("is it still active?").
  The result now includes **admitted-only, ordered, bounded and disjoint**
  `known_inapplicable_refs`, distinct from the evidence served as
  *current*. Consumers can explain a known interval's end without
  misrepresenting it as an active current fact.

Those fixes were imported without overwriting independent validation reports.
The API output contract was bumped to `0.2.0` because the result shape
changed. This exact new blob must be retested; prior cloud logs were against
the unbumped repaired version.

**Critical measurement finding:** With an identical explicit reference instant,
the frozen v7 multi-route ranking returns the same top-k on every tested
Halcyon v1.1 and Cedarline v1.1 query as this selector. The observed drop
in stale exposure from 1 to 0 per corpus is attributable to **supplying
the instant to v7**, not to this selection API. A post-v7 baseline must
not claim a proven P0/P1/P2 improvement from these holdouts. The selector
only has a distinct effect in sparse candidate/budget cases and may
degrade usefulness without the separate not-current evidence channel.

## Proposed v8 declaration, NOT activated

The staged schema-conformant artifact
`reports/runtime/proposals/773-runtime-baseline-v8-declaration.DRAFT.json`
pins the protected source blob to a hypothetical successor of v7.
It is **a DRAFT PROPOSAL ONLY**. `reports/runtime/baseline-register.json`
still declares v7 as successor to published v6. It is not valid to
replace that pending declaration with v8 or pretend v7 is published.
Any future promotion needs a sanctioned v7 -> v8 transition, a
versioned source boundary, lane re-executions, independent provenance
review and explicit publication authority. This draft's v8 lanes and
replays are **requirements**, not observed test results or created lanes.
`identity_deltas=[]` means existing tracked runtime identities were
not altered, not that the opt-in contract lacks its own `0.2.0` version;
a future identity registry/replay for this opt-in surface is still required.

Given **zero demonstrated quality gain** on both first-stage holdouts,
treat this as **hold for product qualification**, not a candidate to
merge because it merely has a baseline declaration on paper.

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

**Status:** Source code and tests committed; cloud validation performed on a prior repaired blob. Exact-current-SHA Python execution, measurable independent quality gain, frozen-lane parity and formal protected-runtime acceptance are **not** established.
