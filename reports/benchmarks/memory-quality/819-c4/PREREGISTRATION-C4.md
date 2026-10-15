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

## Erratum (recorded during implementation, before any cohort or benchmark run on C4)

The preregistered test "passing mention does not count as coverage" (`bring ... Rex`) could not
be satisfied together with "covered entity adds nothing" (`Mom's new mailing address`). Measured
on those fixtures, the admitted-set relevance of the selected fact to the entity is 0.64 of the
best for Rex and 0.66 for Mom. No lexical measure available to selection separates a subject from
a passing mention.

C4 takes the conservative reading the cycle brief asks for: a selected fact that names the entity
with at least half the best relevance covers it. Two expectations were changed accordingly, and
the change is visible in the diff:

- the C4 Rex test now asserts that only the vet fact is returned;
- the slice-1 React/MongoDB test no longer requires the React fact, because the selected
  error-handling fact names React. MongoDB, which no selected fact names, is still covered.

The diagnostics test fixture gained a third fact so that the dominance path is actually exercised,
and its expected term count is 2 ("number" is a frame word).

## Erratum 2: dominance never withholds a newer statement (before freeze; held-out v3 unread)

The first C4 working tree met every preregistered unit test. My preregistered regression tracking
then flagged LongMemEval-S, a seen, diagnostic-only set:

| Session plane | C3 | First C4 working tree |
|---|---:|---:|
| recall_all@10 | 0.905 | 0.878 (−0.027, beyond the 0.01 tolerance) |
| knowledge-update | 0.972 | 0.903 |

Pooled precision rose from 0.381 to 0.469.

The two other C4 mechanisms traded well:

| Mechanism | Returns removed | Gold among them |
|---|---:|---:|
| `ranked_above_sufficient` | 409 | 7 |
| Entity coverage | 39 | 0 |

The loss came from dominance: 14 gold sessions.

The general flaw: a later statement that matches fewer query words is often the update to an
earlier, fuller one. Withholding it returns a stale state alone, which is worse than an extra fact.

**Repair, chosen on principle and applied once.** A fact is dominated only if it is not newer than
its dominator, on the first clock both carry: declared valid-from, then declared observed-at, then
transaction time (the ranking stage's order). If the order is unknown, nothing is withheld.

**Test changes:**
- The two dominance tests now write the partial facts before the answer.
- A function-level test pins both orders.

No further LongMemEval-driven changes follow. Its rerun is reported as measured.

## Erratum 3: term-coverage dominance removed after independent review (before freeze; held-out v3 unread)

The independent adversarial review of `3caf0c13` (`REVIEW-C4-adversarial.md`) showed that
preregistered change 3 is unsound:

- **Matching more of the question's words is not answering it.** A newer fact that restates the
  question ("I want to buy more blue running shoes…") withheld the older fact holding the answer
  ("Blue running shoes are from Fleet Feet."). Any writer, including a tool, could suppress a
  correct answer by restating the question.
- **Its statement-order guard was manipulable.** Equal declared days withheld the newer update,
  and caller-declared dates overrode write order.
- **List questions without an aggregate cue lost items**, because they are read as single.
- **The pairwise loop was quadratic:** about 6× slower at 3,000 matching facts.

Change 3 is **removed**, not patched. Changes 1 and 2 remain. Change 1 gains the review's F5 fix:
a selected fact covers an entity only if it writes it as a name (capitalised or letter–digit),
so a lowercase homograph such as "mark it urgent" does not cover Mark.

The acceptance measures are unchanged. The first acceptance criterion now rests on changes 1 and 2
alone. The dominance tests are replaced by the reviewer's reproductions, which fail on
`3caf0c13`; the per-fact diagnostics no longer carry `dominated_by`.
