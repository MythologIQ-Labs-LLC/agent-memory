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

## Additional frozen-v6 comparison guard

`reference/tests/test_597_v6_noninterference.py` loads the write
interpreter from published v6 main `3eebb6d54e2a218c4fd10cf53c52acac8384c3e6`
through `git show`, without installing a second checkout or accessing the
accepted #594 labels. It compares unrelated fresh input outputs after ignoring
only the new interpreter version, probes the intended request-boundary delta,
and verifies that 1.1.0 persisted write semantics still expand with the original
version and proposition.

Historical #598 tests in `test_write_temporal_aspect_v1_1.py` explicitly pin
new-write version 1.1.0 and the 1.1.0-only non-aspect behavior. That suite was
written for a previous runtime and may fail under the 1.2.0 candidate. **Do not
rewrite the historical oracle to accept 1.2.0 by replacing constants, marking
broad skips or deleting frozen comparisons.** Qualification must preserve a
v1.1.0 replay on its pinned runtime and independently validate 1.2.0's
intentional behavioral differences. Until this is done, full-suite and
successor-baseline status are CHANGES REQUIRED.

## Falsification gates

1. Independently run `python -m unittest discover -s reference/tests -t reference -p test_597_trailing_request_boundary.py`
   from the repository root, then all interpretation/temporal tests and the full reference suite.
2. Show equivalent principal proposition/value for a declarative sentence alone and
   the same sentence followed by an auxiliary question, a polite imperative,
   and a conjoined request. Show standalone requests are not promoted to known.
3. Independently test negative controls: quoted request-like text stays in the value, a request following a conjunction without a comma is excluded, and multiple declarative claims remain
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
