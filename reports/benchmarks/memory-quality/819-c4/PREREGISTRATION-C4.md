# #819 C4 preregistration: selection precision without losing evidence completeness

Written and committed **before** any C4 runtime change. Base: C3 evidence head `8549e942` (runtime
identical to frozen C3 `6a2255c0`). Branch: `claude/eager-dirac-bftkfg-819-c4`. C2 `eaf60e4d`, C3
`6a2255c0`/`8549e942` and the independent evaluator's branches are not modified.

## Problem (from C3's frozen evidence)

On held-out v2, C3 had 19 strict regressions against C2. 16 of them returned every required
fact plus at least one unnecessary one. The C3 selection bases behind those extras:

- **`entity_coverage`.** It added "the fact most about" an entity that the selected evidence already
  covered, for example a kinship name such as "Mom".
- **`ranked_above_sufficient`.** It promoted any fact with a trace of topical evidence that was
  ranked above the *lowest* primary fact: ordering noise among similar facts.
- **Primary relevance.** Facts matching only part of what a higher-ranked selected fact matches
  were returned beside it for single-answer questions. This is also C2 behaviour.

Held-out v2 is spent: it was opened after the C3 freeze and is not used for C4 development.

## Intended changes (selection policy 2.3.0 candidate)

1. **Uncovered-entity coverage.** An entity mention is *covered* when an already-selected fact is
   substantially about it. Concretely, that fact's admitted-set BM25 for the mention is at least
   `COVERAGE_FRACTION` (0.5, the same relative scale as the primary floor) of the best such score
   among admitted facts with topical evidence. Only an uncovered mention adds the admitted fact
   most about it. A passing mention ("bring Rex") does not cover an entity; a fact centrally about
   it does.
2. **Ranking consistency anchored on the best primary fact.** A below-floor fact with topical
   evidence is promoted only when ranking places it above the *highest-ranked* primary-evidence
   fact. Only ranking's non-lexical stages (currentness, temporal applicability, identity,
   corroboration) can do that, and those are the cases the rule exists for.
3. **Term-coverage dominance for single-answer questions.** For a query whose information
   requirement is `single`:
   - A primary or promoted fact is withheld (`dominated_by_selected`) when the set of query terms
     it matches is a *strict* subset of the set matched by a selected, higher-ranked fact.
   - Equal sets are kept, so possibly conflicting answers are not collapsed.
   - Exempt: facts ranked above the best primary fact, exact-identity hits, non-lexical-route
     facts, entity-coverage additions and lifecycle successors.
   - Aggregate and relational questions are unchanged.
4. **Diagnostics.** Each admitted fact's `return_selection` record adds:
   - `requirement`: the query's information requirement;
   - `query_terms_matched` and `query_terms_added`: counts of the caller's own query terms;
   - `entities_added`: count;
   - for a dominated fact, `dominated_by`: an admitted, selected ref.

   Records exist only for admitted facts, so no refused, forgotten or other-scope identifier
   enters selection diagnostics.

## Invariants that must not change

- Candidate discovery, governed admission, ranking and `admitted` are untouched. Selection only
  chooses among admitted facts.
- `ranked_prefix` is exactly the pre-#819 (1.4.0) behaviour. Check: 0/500 differing lists against
  A on both LongMemEval planes.
- Tenant, project and task isolation; forgetting; correction and supersession; deterministic
  restart. All existing tests pass, the one exception being the Runtime Baseline guard, which
  fails by design.
- Lifecycle closure (typed relations only) and the #583 mask on normal forms.
- No model calls, no new storage, no new dependencies. Selection is bounded and deterministic.
- The contract number is not advanced, no baseline is declared, and defaults are not
  re-decided. The default remains as on the candidate branch, pending governance.

## Fail-first tests

`reference/tests/test_c4_selection_precision.py`, 12 new ordinary cases with no benchmark text. On
the C3 code, three fail and one errors: a covered entity adds a fact, noise between primaries is
promoted, a partial match is returned beside the full answer, and the diagnostics are missing. The
other eight pass on C3 and must keep passing. They cover:

- uncovered-entity coverage, and a passing mention not counting as coverage;
- equal matches kept and aggregate completeness;
- the ranked-above-best case;
- correction, forgetting and `ranked_prefix`.

## Acceptance measures (fixed now)

**Primary: a fresh, independently authored held-out cohort (v3).**
- It is authored by a separate agent without access to the runtime, tests or earlier cohorts. Its
  seal (sha256, population, scoring rules = `scripts/run_memory_quality_scenarios.py`, safety
  gates) is committed before C4 is frozen.
- It is run once per system (A, C2, C3, C4) after the freeze, with the same runner.

Accept C4 over C3 only if all of these hold:
1. Strict pass improves over C3 (paired; report exact McNemar and a bootstrap 95% interval).
2. Mean recall is not lower than C3's by more than 0.02.
3. Zero safety violations (superseded, forgotten or other-scope returns).

Report per category, with special attention to correction, abstention, distractors and
multi-evidence. A gain in one dimension with a meaningful loss in another is reported as a
trade-off, not a win.

**Diagnostic regression tracking.** These sets are not pristine (seen during development) and are
not tuning targets.
- LongMemEval-S native: session recall_all@5/@10 and turn recall_all@10 not more than 0.01 below
  C3; `ranked_prefix` 0/500 differences.
- AMB 77: report strict, precision and recall against C3.

**Cost.** Held-out recall p50 latency within +10% of C3; no new storage.
