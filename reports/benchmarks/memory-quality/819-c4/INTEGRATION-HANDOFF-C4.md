# C4 integration handoff (for the delivery integrator, #410)

**C4 is not independently safe to adopt, and this handoff merges nothing.** It describes what a
landing would require. The owner and the delivery integrator decide.

## 1. Exact revisions

| Item | SHA | Branch |
|---|---|---|
| C4 runtime (frozen) | `bc2be6319a3eda96731fdb235f4feba882bcb9be` | `claude/eager-dirac-bftkfg-819-c4` |
| C4 lineage | `6a2255c0` (C3) → `eaf60e4d` (C2) → `4bd38e6c` (C1) → `1df28f84` | `claude/eager-dirac-bftkfg-819*` |
| Security successor head | `77c472e6` (#815) on `28f257c9` (#805) | `claude/eager-dirac-bftkfg-809` on `claude/eager-dirac-bftkfg-stack-main` |
| #691 context package (separate) | see the #691 record | `claude/eager-dirac-bftkfg-691-context` (on `77c472e6`) |

## 2. Dependencies on the v8 security successor

- **The C4 lineage branches from `1df28f84`, which predates the security stack.**
  - Its base still accepts a cross-project write through `overrides`. That is the #786 defect,
    fixed on #783 → #805.
  - It lacks the #777 public deleted-lineage redaction and the #809 derivation binding.
- **Selection changes only post-admission return selection and lexical discovery**
  (`runtime/return_selection.py`, `runtime/query_interpretation.py`,
  `runtime/lexical_normalization.py`, `runtime_composition._discovery_query`,
  `adapter.discovery_admissible`, `adapter.lifecycle_successors`, `api/surface.recall`,
  `api/contract.apply_return_selection`).
- **Expected merge conflicts with #805/#815:**
  - `api/surface.py`: the #777 public projection wraps `_recall_document`, while C4 adds return
    selection, `discovery_expansion` and the selection summary;
  - `api/contract.py`: `CONTRACT_VERSION` and the return-policy schema;
  - `runtime/adapter.py`: #786 write authority and #809 accessors, against C4's
    `discovery_admissible`/`lifecycle_successors`;
  - `schemas/api-result-envelope.schema.json`;
  - docs/44.
- **Required ordering:** land the security successor first, then rebase or merge the C4 selection
  onto that integrated head. The #777 projection must run on the final `returned` list after
  selection. Selection diagnostics must only ever name admitted facts, which C4 guarantees, so they
  cannot reintroduce withheld identifiers.

## 3. Contract and Runtime Baseline succession

- **Numbering.** The C-lineage carries the candidate number `1.9.0`. The v8 stack carries `1.8.0`.
  #815 separately proposes `1.9.0` (for `identity.derivation_semantics`). **The two `1.9.0`s
  conflict.** The owner must pick one numbering. One proposal: the security successor takes `1.9.0`
  as #815 asks, and return selection becomes the next minor, `1.10.0`, or a separately versioned
  return-selection profile. Either way it is not promoted merely because the number exists.
- **Runtime Baseline.** A successor declaration is required. `test_evaluation_only_change_keeps_runtime_baseline_equivalence`
  fails on every C-lineage head by design. The declaration must cover the integrated head, not
  `bc2be631` alone.

## 4. LongMemEval lane version

The runner scores the facade's `returned` list, so the default return changes the accepted lane's
numbers. A **new lane id** is required (evaluator recommendation 2). The accepted rows must not
move.

C4's diagnostic numbers are in `FREEZE-C4.md` and `longmemeval/`. They come from the native runner on the same frozen input. On the session plane all@10 is 0.907 and all@50 is 0.907; on the turn plane all@10 is 0.759 and all@50 is 0.816. `ranked_prefix` reproduces A exactly. The benchmarking
owners decide the lane.

## 5. Default and opt-in configurations

- **Stable today:** `return_selection="ranked_prefix"`, byte-identical to 1.4.0 (verified: 0/500
  differences on both LongMemEval planes for C3, and identical to C3 at C4).
- **Candidate default:** `relevance_sufficient` (policy 2.3.0).
  - **Recommendation: ship it opt-in first.** Keep `ranked_prefix` as the integrated default until
    an independent evaluator verdict and a governance decision say otherwise.
  - The fresh held-out puts C4 at parity with C2 on strict pass (p = 0.20) with higher recall, and
    slightly ahead of C3 (+2/−0, not significant).
- **Not enabled:** semantic route, extractor, multi-hop bridging (rejected).

## 6. Tests required on the integrated head

1. The full suite. Expected failures only: the Runtime Baseline guard until the successor is
   declared, and the environment-dependent ancestry tests listed in the #805/#815 records.
2. All selection suites: `test_relevance_sufficient_return_selection`, `test_evidence_set_selection`,
   `test_lexical_normalization`, `test_lifecycle_closure`, `test_c3_review_regressions`,
   `test_c4_selection_precision`.
3. The #786/#809 security replays (v2, v3, evidence-reference-authorization), **re-executed** at
   the integrated head, with replay evidence regenerated there.
4. #777: deleted-lineage identifiers never appear in `admissions`, `return_selection` records or
   any per-fact selection diagnostic after selection. Add a test that runs selection diagnostics through
   the public projection.
5. `ranked_prefix` equivalence against the integrated head's own 1.4.0 behaviour (LongMemEval both
   planes, 0 differences).
6. Held-out: a new independently sealed cohort for the integrated head. v2 and v3 are spent.

## 7. Outstanding blockers and limitations

**Blockers:**
- the independent evaluator's verdict on C3, in progress, and on C4, requested;
- the owner's numbering decision and the baseline successor;
- integration onto the security successor;
- the lane version.

**Limitations:**
- C2 still beats C4 on correction, currentness and entity-redundant single answers.
- Untyped state changes: the newer statement can fall below the floor.
- Zero-overlap paraphrase.
- Multi-hop.
- Plural list questions without an aggregate cue.
- Possessive homographs.
- English-only rules.

## Predecessor branches that can eventually retire

Retire only after the integrated landing is verified; none are closed now.

- `claude/eager-dirac-bftkfg-819` (C1/C2): superseded by C4 once integrated. Keep it until the
  evaluator's records stop citing it.
- `claude/eager-dirac-bftkfg-819-evidence-sets` (C3): superseded by C4 once integrated.
