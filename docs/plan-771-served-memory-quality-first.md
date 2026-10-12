# Quality-first evaluation of *served* memories (#771)

**Maturity:** evaluation-only scorer and synthetic controls, not an accepted
benchmark, user-quality claim, or qualified runtime. Published v6 remains
unchanged. This is a separate measure from p50/p95 throughput.

## Product question

> Did the governed runtime serve **the correct memory for the actual caller's
> task and time**, early enough to be useful, while excluding memories that
> should not have been visible or should no longer be used?

Merely finding an exact source somewhere in a deep result list is not enough.
Returning a fast but irrelevant result is a product failure; returning an old
version as the current answer or leaking a forbidden memory is worse.

## Independent measurement axes

| Tier | Native evidence | Release implication |
| --- | --- | --- |
| P0, safety | Forbidden/refused/deleted source exposure, inappropriate stale-version exposure, cross-scope leakage and unauthorized memory-control action | Any verified breach blocks the candidate regardless of retrieval speed |
| P1, served correctness | Task-critical evidence groups covered under the actual return budget, top-1 task relevance, answerability and correct abstention | Essential product-quality floor; do not hide unsafe or absent answers behind aggregate recall |
| P2, context utility | Graded nDCG@budget, macro relevant precision, macro relevant recall, critical coverage, irrelevant/distractor burden | Optimize rankings and useful context without admitting extra evidence |
| P3, resource performance | Cold/warm p50/p95/p99, indexed scan amplification, memory and ingest/build cost | Independent scalability/reliability constraints, not tradeable against P0/P1 defects |

No metric weighting into a global scalar is permitted. Empty results must be
rewarded **only** on explicitly no-safe-answer cases, and count against recall
on cases with an available safe answer. An otherwise relevant but forbidden
memory cannot earn relevance credit.

A quality win requires meaningful improvements on frozen and *independently
held-out* scenarios. Do not compare published vendor scores to internally
different protocols.

## Implemented scorer

`scripts/score_served_memory_quality.py` evaluates complete ordered result
lists returned by the runtime, not route candidates the user never receives.
The cases have a declared intent (`current`, `historical`, `timeless`),
maximum return budget, graded relevance per source (0..3), disjunctive
task-critical evidence groups, explicitly prohibited sources, stale sources
relative to that query intent and an annotation of safe answer availability.

The run file supplies only the lane identity, exact runtime revision and
returned ordered IDs. The scorer refuses missing/extra questions, duplicate
refs, unlabeled returned refs, malformed or grade-forged gold, and over-budget
outputs. Reports include exact input SHA-256s and per-case scores without
reproducing source text or scenario content.

**Current fixture is synthetic.** Its "bad" run intentionally serves stale
and forbidden memories, ranks an irrelevant item first, and misses a critical
compound-answer slot. Its "good" run serves the right evidence and abstains
when the only candidate is forbidden. This is an evaluator counterexample,
**not** evidence of production Agent Memory quality.

### Reproduce locally or in Claude Code cloud

```bash
python -m unittest discover -s tests -p test_served_memory_quality.py
python scripts/score_served_memory_quality.py \
  --cases reference/fixtures/evaluation/served-memory-quality-v1-cases.json \
  --runs reference/fixtures/evaluation/served-memory-quality-v1-good.json

python scripts/score_served_memory_quality.py \
  --cases reference/fixtures/evaluation/served-memory-quality-v1-cases.json \
  --runs reference/fixtures/evaluation/served-memory-quality-v1-bad.json
```

There is **no GitHub Actions workflow** for this tranche. Do not claim tests
executed until a trusted runner does so and records the exact SHA.

## Real composed-memory qualification, not synthetic overfitting

Future frozen data must come from scenarios not designed by the runtime author,
including:

- "What is the **current** setting?" where older values are still visible for
  historical questions and only correct current evidence may be served.
- "Why was this architectural decision made ten years ago?" requiring genuine
  historical causal provenance rather than a new but unrelated recollection.
- Compound tasks requiring several distinct evidence groups in one bounded
  context; recall@50 cannot conceal a missed group in the actual top-k.
- Real corrections, disputed facts, partial overlap, coexistence, and
  contradicting sources, with appropriate uncertainty.
- Role/task/project/tenant exclusions, deletion, permitted shared domains and
  correct abstention when no safe answer exists.
- Paraphrases, unseen terminology, multiple speakers, quoted claims and
  incremental updates without relying on handwritten lexical cues.

Integrate the scorer only as a **post-hoc evaluator** after canonical governed
recall and return-budget processing. Gold labels and inferred "correct"
propositions never feed the candidate selector, admission policy or stop
controller. Source eligibility needs independent policy provenance, not the
model or scorer asserting its own authority.

### Evaluation precedence

1. Verify run/lane/source/execution identity and case selection before scoring.
2. Enforce P0 safety and provenance; any verified breach is a blocker.
3. Compare P1 product correctness with separate strata (current, historical,
   compound, no-answer, correction, source-privacy).
4. Assess P2 graded context utility, avoiding a win that is just over-abstention.
5. Measure P3 scalability/latency separately with the same store and workload.
6. Independently check cases the implementer has not seen. No benchmark-specific
   code or post-evaluation gold-driven tuning may be introduced into runtime.

Benchmark quality can be improved without new authority or a universal number.
The first real baseline will need a versioned lane, frozen labels, source
manifests, different scorer/comparator identities and independent replays.
