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
| P1, served correctness | Task-critical evidence groups covered under the actual return budget, top-1 task relevance, answerability and empty-context delivery | Essential product-quality floor; do not hide missing memories behind aggregate recall |
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
compound-answer slot. Its "good" run serves the right evidence and returns an empty context
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

## Implemented reference-composition execution lane (next slice)

A second, separately frozen input/gold pair is now available:

- Input corpus: reference/fixtures/evaluation/served-memory-integration-v1-input.json
- Relevance gold: reference/fixtures/evaluation/served-memory-integration-v1-gold.json
- Live runner: scripts/run_served_memory_scenarios.py
- Independent alignment and scoring: scripts/qualify_served_memory_run.py
- New tests: reference/tests/test_771_served_memory_integration.py and
  tests/test_served_memory_provenance.py

The input corpus has seven distinct memory writes, two project scopes,
five concrete questions (current endpoint, compound evidence, historical
release reason, unavailable owner, and current release), caller-declared
temporal intent, explicit return budgets, and no relevance/answer labels.
The composed runner passes the declared temporal intent to the actual
recall applicability policy, distinguishing current, historical, and
atemporal/unspecified requests without passing any expected answer. The gold is in a DIFFERENT file and
is never loaded by the runtime runner.

The runner executes ConfiguredCompositionRuntime.retain (real governed
canonical commits) and ConfiguredCompositionRuntime.multi_route_recall
(actual composed ranking and admission). The evaluator applies an explicit
top-k return budget to the ranked admitted identities and maps fact UUIDs
back to stable opaque corpus IDs. Those are the facts a bounded reference
context would receive. It does not fabricate an LLM-generated answer and
is not proof of a downstream user-facing response or a future production
facade's exact return behavior.

The optional backend --backend governed-lexical calls the canonical adapter's
governed lexical recall instead of the composed multi-route planner. It does
not accept caller-declared temporal intent as an input, unlike the composed
planner. Therefore it is a distinct diagnostic profile, **not a matched
historical-intent comparator**. Historical-intent scored differences between
these paths are descriptive, not an accepted same-protocol frontier.
Compare with explicit profile identity and a reviewer ruling on eligibility.

The alignment step refuses score laundering: every written source must have
a label in every query case, every out-of-project source must be prohibited,
and query identity, wording, intent and budget must match gold exactly.
It rejects unannotated returned facts rather than calling them irrelevant.

### Execute with a clean, full Git checkout (Claude Code local or cloud)

The CLI refuses execution on a dirty checkout and records actual git HEAD
as the candidate revision. Use fresh output/store paths. No Actions workflow
is needed.

~~~sh
python -m unittest discover -s tests -p 'test_served_memory_*.py'
python -m unittest discover -s reference/tests -t reference \
  -p 'test_771_served_memory_integration.py'

python scripts/run_served_memory_scenarios.py \
  --inputs reference/fixtures/evaluation/served-memory-integration-v1-input.json \
  --store /tmp/am-771-composed-store \
  --lane-id reference-composed-v1 \
  --backend composed-multiroute \
  --output /tmp/am-771-composed-run.json

python scripts/qualify_served_memory_run.py \
  --inputs reference/fixtures/evaluation/served-memory-integration-v1-input.json \
  --gold reference/fixtures/evaluation/served-memory-integration-v1-gold.json \
  --runs /tmp/am-771-composed-run.json \
  --output /tmp/am-771-composed-quality.json
~~~

For the canonical lexical path, use an independent empty store/output
and --backend governed-lexical with --lane-id reference-lexical-v1.

The qualification output has the source/input/gold/run SHA-256 digests,
per-question P0/P1/P2 results, and explicitly no weighted overall score.
A third-party run must show source SHA, actual returned IDs, status and
any ordinary-refusal decisions separately before being called accepted.

This slice is a **REAL executable reference evaluation path but not yet
an executed measurement**. It must not be called evidence of improved
product memory quality until exact-SHA results have been obtained.
The authored synthetic corpus is only a baseline/smoke. The independent
unseen holdout is still a mandatory next lane.

## Measurement-integrity corrections before cloud qualification

### Context delivery is not answer-level abstention

The initial evaluator incorrectly treated `returned=[]` as proof that the
consumer abstained from answering. **That is not observable in retrieval-only
data.** A retriever can serve contextual evidence when no answer exists;
it can return nothing even if a downstream agent will hallucinate an answer.
The scorer now reports `empty_delivery_on_answerable_count`,
`no_safe_answer_empty_context_count`, and
`no_safe_answer_with_context_count` as **delivery observations only**.
`answer_abstention_verified` remains `null` and
`answer_abstention_status=not_measured_without_answering_layer`.
Actual answer correctness/refusal requires a separate downstream answer
transcript and independent adjudication. Do not publish a "correct answer
abstention" rate from this evaluator.

### Protect corpus/run identity

Each real execution manifest now carries `input_sha256`, a SHA-256 of the
canonical JSON representation of its validated **execution-only** corpus,
and `execution_backend` identifying whether actual recall used
`composed-multiroute` or `governed-lexical`. These fields are required
when the post-hoc qualifier scores a *real* run. Legacy synthetic scorer-only
fixtures remain accepted by the scorer for evaluator tests, but cannot be
passed through real-run qualification without the binding.

A changed memory text with identical opaque IDs fails real-run validation;
missing/wrong input digests and unsupported backend values fail closed.
These are **integrity consistency checks, not cryptographic authentication**:
a malicious author can recalculate an unkeyed SHA-256. Exact source SHA,
immutable evidence review and independent runner replay remain required.

The runner now also refuses reused/nonempty SQLite store directories prior to
any new governed write. A local run may reuse an existing *empty* directory
(such as `tempfile.TemporaryDirectory()`), but not one with remnants from
another scenario. This guards against accidentally comparing outputs from
different corpora.

**No source gold** is ever loaded by the runner. The scenario/gold pair remains
preregistered and held separate from the default/runtime recall algorithms.
These corrections are evaluation-only; no protected runtime file changed.

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
  empty context when no eligible answer exists. Verifying answer refusal
  requires a separate downstream answering-layer execution and oracle.
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
4. Assess P2 graded context utility, avoiding a win that is just over-empty-delivery.
5. Measure P3 scalability/latency separately with the same store and workload.
6. Independently check cases the implementer has not seen. No benchmark-specific
   code or post-evaluation gold-driven tuning may be introduced into runtime.

Benchmark quality can be improved without new authority or a universal number.
The first real baseline will need a versioned lane, frozen labels, source
manifests, different scorer/comparator identities and independent replays.
