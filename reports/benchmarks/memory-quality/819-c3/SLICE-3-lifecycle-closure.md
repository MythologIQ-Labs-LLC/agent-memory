# C3 slice 3: lifecycle closure (verification record)

Base: slice 2 `86be4a95` on `claude/eager-dirac-bftkfg-819-evidence-sets`. C2 is untouched.
Selection policy `2.2.0`. This is a candidate within the 1.9.0 contract line. No contract version
advance and no baseline declaration.

## Problem: C2's selection broke a lifecycle guarantee

The runtime records **write-time state-change relations**: #671 typed slots, with the open,
unapplied proposal evidence that a later fact changes an earlier one. Return selection (C2 onward)
judged each fact by word overlap only, and so returned a changed state as if it still held:

```
remember "I live in Boston."                 (typed: residence = Boston, state)
remember "I moved to Denver last month."     (typed: residence = Denver, change, replaces Boston)
recall   "Where do I live now?"
  C2 / slice 2  -> ["I live in Boston."]                       "Denver" withheld: no topical overlap
  slice 3       -> ["I moved to Denver last month.", "I live in Boston."]
```

The pre-C2 ranked prefix returned both facts (ranking already orders the change first), so this
was a C2 regression, not a new capability. The ranking stage even labelled Boston
`limited_by_cross_fact_state_change`, but only for explicit-current queries (#671 gate G1).
"Who is my manager?" carried no label at all.

## Change (selection policy 2.2.0)

- **`GovernedMemoryAdapter.lifecycle_successors(admitted)`** (read-only):
  - For each admitted fact, it returns the admitted facts whose write-time state-change relation
    targets it.
  - It uses the **same #671 guards G2–G13**: an open proposal, the same actor, source, tenant,
    purpose and scope, an assertive change with no hedge, negation or attribution flag, and clock
    order.
  - It drops **G1**, the explicit-current gate, because closure makes no currentness decision. It
    never removes, demotes or relabels a fact, and `cross_fact_limitation` still appears only for
    explicit-current recalls.
  - Only facts in the write-time slot index are read.
- **Selection.** After primary, set and entity evidence, a selected fact brings the admitted facts
  that change it (`lifecycle_successor`), transitively, in ranked order.
  `return_policy.lifecycle_successor_count` counts them.

**Scope and type: what was examined and deliberately not changed.**

- **Scope.** The isolation model already expresses breadth: a fact without `project_ref` is
  visible across the tenant's projects. Probing this base showed that a `project:a` handle can
  write into `project:b` through `overrides`. That is the #786 write-authority defect, which is
  fixed on the #783 security stack and not on this branch's base. A scope-breadth API therefore
  waits for #786 to integrate and for a governance decision. **It is a merge dependency: this
  candidate must be integrated with the #783 stack before any adoption.**
- **Types.** Caller-declared typed propositions (`subject`, `attribute`, `value`, `assertion`,
  `cardinality`, flags) already exist (contract 1.6.0). This slice makes them affect what recall
  returns. It adds no new type inference at retrieval.

## Tests

`reference/tests/test_lifecycle_closure.py`, 12 tests, covering:

- **Closure behaviour:**
  - a limited state brings its later state;
  - transitive chains;
  - closure without a "now" cue;
  - no closure without typed evidence, including text that claims "this supersedes memory:…";
  - no closure for a hedged change (G12) or a change from a different `source_ref` (G9);
  - closure never reaches beyond admitted facts.
- **Governance:**
  - a forgotten successor is never added;
  - a corrected successor returns only its current version;
  - an other-scope successor is never added;
  - selection is deterministic across a reopen;
  - `ranked_prefix` is unchanged.

The two closure tests failed on slice-2 code before the change, as recorded during development.

**Full suite**, run from the repository root: 2623 tests, 36 skipped, 1 failure. The failure is
the Runtime Baseline equivalence gate, which fails by design.

## Measurements (diagnostic)

**Engineer-authored typed-lifecycle fixture** (`reference/fixtures/memory-quality/lifecycle-typed.json`,
11 scenarios). This is not holdout evidence; I wrote it. Each scenario is a state, then a later
change in different words, then a question about the current value. The later state must be
returned; the earlier one may be. Run with `scripts/run_memory_quality_scenarios.py`, which now
forwards an optional `source_ref` and `proposition`. A key-only check confirmed the sealed held-out
v2 cohort uses neither key, so the runner's behaviour on it is unchanged.

| | A `1df28f84` | C2 `eaf60e4d` | Slice 2 `86be4a95` | Slice 3 |
|---|---:|---:|---:|---:|
| Typed state change (8) | 6/8 | 1/8 | 1/8 | **6/8** |
| Mean returned (typed) | 1.88 | 0.75 | 0.75 | 1.38 |
| Untyped control (3) | **3/3** | 0/3 | 0/3 | 0/3 |
| Safety violations | 0 | 0 | 0 | 0 |

- **Typed changes.** Slice 3 restores A's coverage while returning fewer facts.
- **The two remaining typed failures** ("Which editor do I use?", "What is my diet?") share no
  topical word with either memory. Selection abstains, which is a discovery gap, not a lifecycle
  one.
- **Untyped controls stay lost (0/3, against A's 3/3).** Without a typed proposition the runtime
  has no state-change relation, and slice 3 infers none from text by design. Callers that do not
  declare propositions, which is most callers today, still get C2's behaviour: the earlier state
  alone. This is the most important lifecycle gap left in C3.

**LongMemEval-S and AMB.** Neither declares typed propositions, so no relation exists. Slice 3's
selection traces are byte-identical to slice 2 on all 500 LongMemEval-S questions, and AMB is
38/77 with 0 fixed and 0 broken.

## Cost

Same 4-CPU container. Synthetic store, p50 over five repetitions:

| | Slice 2 | Slice 3 |
|---|---:|---:|
| 3000 facts, 1640 candidates, warm handle | 414 ms | 432 ms |
| 3000 facts, 1649 candidates, warm handle | 384 ms | 426 ms |
| 3000 facts, 0 candidates | 50 ms | 52 ms |
| 2000 facts, fresh handle per recall (open + recall) | 736 ms | 765 ms |

The extra cost (+4–10%) is reading the slot index and evaluating guards over the admitted facts
that carry slot evidence.

## Security review (self-review; the independent review is at freeze)

- **Closure can only add facts that are already admitted.** Scope, forgetting, correction and
  tenancy are decided before it runs, and tests attack each.
- **The relation is runtime write-time evidence**, gated by the reviewed #671 guards. Memory text
  cannot create it: a "this supersedes" sentence does nothing, and a hedged proposition or a
  different source does not close.
- **Dropping G1 is safe because closure makes no currentness decision.** G1 protects the
  *limitation* label, which still requires an explicit-current recall.
- **Open dependency:** the #786 cross-project write path on this base, described above.

## Remaining gaps after slice 3

1. Untyped state changes (see above). Options: the #732 extractor path (off by default), or a
   governed, text-derived relation under #671's interpreted branch.
2. Zero-overlap discovery: semantic route calibration.
3. The falling precision of returned sets (slice 2 record).
4. A scope-breadth API, after #786 integration and a governance decision.
