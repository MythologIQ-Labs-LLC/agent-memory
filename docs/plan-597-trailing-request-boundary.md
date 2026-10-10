# #597: Declarative memory followed by a request

**Stage:** isolated, unqualified runtime candidate. **Owning issue:** #597.
**Evidence state:** CHANGES REQUIRED pending executable tests, independent review, and
successor-baseline declaration. No approved benchmark result or production rollout.

## Problem

The write-time interpreter treated a comma-attached request as part of an otherwise
asserted proposition value. For example, a user recording a beverage preference
and asking for a recommendation in the same message could persist the entire
request in the preference value. This is a syntactic boundary error, not evidence
of any domain-specific proposition identity.

## Bounded implementation

The candidate changes only `runtime/proposition_semantics.py` and adds
`test_597_trailing_request_boundary.py`.

The write-time parser recognizes an explicit request opening *after a comma*
(including `, and ...`), retains the preceding declarative span, and refuses to
interpret the request span as an asserted proposition. It does not guess whether
the preceding declaration is factually true, derive a new entity/property alias,
or infer currentness. General conjoined assertions without a request opener keep
their existing multi-slot ambiguity.

`INTERPRETER_VERSION` advances from 1.1.0 to **1.2.0** because new writes may
persist different evidence. Previously written facts are not reinterpreted.
This branch does **not** belong in the frozen v6 baseline or the in-progress
#644 v7 qualification without a separately governed successor transition.

## Falsification gates

1. Independently run `python -m unittest discover -s reference/tests -t reference -p test_597_trailing_request_boundary.py`
   from the repository root, then all interpretation/temporal tests and the full reference suite.
2. Show equivalent principal proposition/value for a declarative sentence alone and
   the same sentence followed by an auxiliary question, a polite imperative,
   and a conjoined request. Show standalone requests are not promoted to known.
3. Independently test negative controls: multiple declarative claims remain
   ambiguous; quotation, conditions, hedges, unrelated comma lists and legitimate
   subordinate clauses do not gain unauthorized proposition status.
4. Inspect `_scoped_aspect` interaction, persisted/expanded version tags,
   old write compatibility, deterministic replay, and no application/authority change.
5. Measure on the accepted #594 Part R gold **after** freezing implementation and
   new adversarial tests, with per-status confusion matrices; never fit new rules to
   the gold labels. Preserve the original gold and compare separate unknown/
   ambiguous overreach and value-boundary diagnoses.
6. Verify independent unseen corpus and same-harness LongMemEval/AMB floors,
   governance, isolation, restart, and baseline equivalence.
7. Regenerate the appropriate protected-runtime successor declaration and ledger
   entry before merge; don't repin or publish v6 and don't silently absorb into #644 v7.

**No claims:** no gain in Part R known recall, no full-suite PASS, no benchmark
frontier improvement, and no release qualification are asserted for this branch.
