# #769 Runtime slice: Opt-in governed competition diagnostics

**Candidate branch:** `implementation/769-post-v7-competition-diagnostics-no-ci`  
**Exact base:** `9b025f945e7ec4a1e349e56bba251e3122413e88` (#770 fully frozen v7 lane implementation).  
**Status:** CODE COMMITTED, UNQUALIFIED; not published, merged, or accepted.  
**Input ancestry:** `docs/plan-769-untyped-competition-safety-contract.md` on the sibling branch `evaluation/769-untyped-competition-contract-no-ci`. The independent 32-case fixture is intentionally **not** copied into this runtime branch or tailored to this implementation.

## System built, rather than just designed

The opt-in method `ControlledRecallPlanner.observe_competition_diagnostic(result, context, needs=(CoverageNeed(...),))`
now invokes the actual existing governed read path:

1. Verify the immutable planner observation receipt still matches the caller-visible
   mutable recall result **before** using any candidate IDs.
2. Reuse `observe_persisted_typed_coverage` for canonical current-admission
   rechecks, caller-declared typed slots, same-slot value coherence, and the
   indexed admission-scoped typed-slot obstacle census.
3. Independently recheck **each already-admitted result reference** through the
   canonical adapter's `current_governed_typed_claim`. A currently visible
   fact without eligible typed evidence contributes only to a redacted
   `admitted_untyped_count`.
4. Re-verify the receipt after the reads. If it no longer matches, return
   `recall_observation_unverified` with **no evidence counts**.
5. Classify the returned evidence with the new immutable
   `competition_diagnostics.CompetitionDiagnostic`, preserving distinctions
   among typed competing values, unresolved typed posture, typed slot
   obstacles, visible admitted untyped candidates, and unverified completeness.

Every response has `stop_recommendation="abstain"`, `authority_effect="none"`,
and `complete_enumeration_attested=False`. The original recall pipeline, its
ranking, admission, controller decisions, deletion and persistence have **no
new calls to the observer**. This is an explicitly invoked, optional
diagnostic, not a new default behavior or stopped-search gate.

**Important:** The count is *visible admitted untyped candidate presence*,
not proof of a same-slot competitor. Even zero such candidates cannot prove
competition absence. The current read path cannot produce a durable,
complete-scope, query-attested certificate; the status remains
`read_path_observed`. The sibling #769 evaluation fixture contains hypothetical
`attested_complete` examples for future policy, but **this runtime never
manufactures that state**.

## Implementation scope

- `reference/agentmem_ref/runtime/competition_diagnostics.py`: new
  typed, redacted, read-only result and pure diagnostic classifier.
- `reference/agentmem_ref/runtime/recall_control.py`: opt-in method added to
  the controlled planner; no default recall call-site changes.
- `reference/tests/test_769_competition_runtime_observer.py`: seven fresh
  integration regressions **committed before** the runtime implementation,
  including typed/no-competitor unknown completeness, admitted untyped
  presence, same-slot unresolved values, tampered receipt, cross-project
  isolation, absent typed coverage and result immutability.

The sibling preregistered 32-case contract and its evaluation-only CLI remain
separate. That prevents "passing the gold" by reshaping either corpus or
runtime grammar to match its labels.

## Reproducibility and acceptance gates

Run from the repository root, on the exact candidate SHA:

```bash
python -m unittest discover -s reference/tests -t reference -p test_769_competition_runtime_observer.py
python -m unittest discover -s reference/tests -t reference -p test_recall_control.py
python -m unittest discover -s reference/tests -t reference
python scripts/check_runtime_baseline_equivalence.py --candidate HEAD
```

**Expected protected-baseline status:** This branch adds a protected runtime
file and modifies another, *after the frozen #770 v7 run*. Until a new,
sanctioned successor/tranche declaration records the exact changes and
qualification gate, the checker should refuse equivalence or report an
undeclared delta. Do not modify or regenerate
`reports/runtime/baseline-v7-declaration.json` to absorb the delta, because
doing so would silently invalidate the already executed #770 v7 lane digests
and declaration identity.

Independent acceptance requires:

1. An adversarial review of every read and serialization boundary, including
   hidden/refused/forgotten sources and mutation of result membership.
2. Exact-head execution with all 7 new integration tests plus original suites;
   no changes to accepted v6 or frozen v7 evidence.
3. Side-by-side effect comparison confirming the default recall path has no
   new observer reads or execution variance.
4. Replay against #769's **already frozen** 32-case evaluation model and a
   second independently authored unseen corpus, without changing gold.
5. An indexed 1k/3k/10k SQLite performance profile for opt-in diagnostics,
   measured separately from the default recall latency. Audit cost is not
   allowed to grow into unbounded full-store scans.
6. A proper protected-runtime declaration for the **next** qualified baseline
   after the in-flight v7 publication protocol has completed.
7. Distinct evidence that any future positive stopping policy is both safe and
   useful. This slice **never** recommends a stop and cannot close #769 or #644.

## Next implementation track

Build a bounded, admission-filtered observation *of potentially related
untyped candidates* only after proving an identity-neutral way to gather
that evidence without inferring slot equivalence from lexical overlap. The
current counter is an intentionally broad visibility indicator. Do not turn it
into a declaration that same-slot competition is known or absent.

The operator can validate this branch on a trusted checkout at a later time.
Until then the commits exist and can be independently reviewed at source level;
no local Python, Actions, benchmark or governed baseline validation is claimed.
