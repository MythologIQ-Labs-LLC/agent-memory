# Agent Memory Benchmarks

Benchmarking is a first-class repository function, not an auxiliary test harness.

Agent Memory keeps benchmark adapters, evaluator-integrity probes, frozen run evidence, normalized manifests, accepted qualification gold, current dashboards, and remediation links alongside the runtime so behavior can be tied to exact revisions and replayed after change.

The governing repository relationship is documented in [`docs/REPOSITORY_OPERATING_MODEL.md`](docs/REPOSITORY_OPERATING_MODEL.md).

The canonical current portfolio view is [`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md). Historical generated scorecards remain revision-bound snapshots and are not the current-state dashboard.

## Governing benchmark rules

```text
benchmark score != authority
benchmark score != truth
retrieval quality != answer-generation quality
retrieval quality != production readiness
harness validation != external benchmark comparability
blocked != 0
not_run != 0
evidence_gap != 0
```

The benchmark program has three jobs:

1. measure the runtime honestly;
2. falsify product/architecture assumptions;
3. prove bounded remediation against the same frozen input when the workload can exercise the mechanism.

There is no universal memory-health aggregate.

## Current portfolio

### LongMemEval_S

Status: **complete frozen external run plus accepted remediation and #594 adapted-evidence replays**.

Current accepted retrieval/currentness highlights:

- session recall_all@5: **0.823389**;
- turn recall_all@10: **0.723**;
- session latest-gold-ranked-first: **0.457**;
- turn latest-gold-ranked-first: **0.557**;
- no runtime, ingestion, out-of-corpus, or unmapped-admission failures on the accepted profile.

The pre-remediation `f73b872` artifacts remain immutable. Current evidence exceeds the lexical baseline on the accepted headline retrieval metrics, while currentness remains a deliberately separate weakness rather than being hidden inside one score.

#594 Phase A created a source-anchored adapted-external profile using defensible session timestamps as caller-declared `observed_at`, plus a separate host-declared question-date reference-time diagnostic.

Result: C, P1 and P2 are metric/rank identical. Interpreted self-validity resolves for only 8 session memories and 33 turn memories and reaches no metric-visible demotion case. The correct classification is **EVIDENCE GAP for #550 demotion efficacy on this corpus**, not failure.

The S profile remains retrieval/currentness evidence. It is not the upstream model-judged LongMemEval QA score.

### LongMemEval_M

Status: **complete bounded external run**.

Accepted recall_all@5:

- session: **0.708831**;
- turn: **0.532220**.

The earlier hold caused by known ingest/per-commit scale cost is historical. M was promoted only after the blocking performance work was bounded; it is no longer `not_run` or `held` in the current portfolio.

### AgentMemBench / MemDialogue

Status: **complete bounded external operational profile plus replayed remediation evidence**.

Current accepted highlights:

- exact-source recall@5: **0.899**;
- PERSONAL_FACT: **0.962**;
- TASK_REQUEST: **0.836**;
- conflict new-fact-first: **0.20**;
- staleness: **0.80**;
- cross-user leakage: **0**;
- audited post-delete absence: **1.0**;
- concurrency operation/materialization success after runtime-owned serialization: **1.0**.

The pre-remediation `03197cd` evidence stays immutable.

### Proposition-semantics natural qualification (#594 Phase B)

Status: **accepted repository-owned conformance evidence**.

A 268-turn natural-language sample was selected before scoring: 100 random Part R turns plus 168 stratified Part S turns. Five versioned annotation drafts were reviewed without consulting interpreter predictions. Maintainer review `5339771805` accepted v5 as the immutable source for `gold-v1.json`.

First accepted score, unbiased Part R:

| status | precision | recall |
| --- | ---: | ---: |
| known | **0.800** | **0.148** |
| ambiguous | 0.210 | **1.000** |
| unknown | **1.000** | 0.848 |

The dominant defect is under-recognition / over-ambiguity: 46 of 54 gold-known Part R turns become `ambiguous`.

The property-alias table was frozen empty before scoring. Therefore strict slot/value conformance is an exact-label diagnostic, not semantic synonym precision. #597 owns a pre-score canonicalization contract; aliases are not fitted after seeing failures.

Follow-on defects are tracked as:

- #596 proposition recognition / over-ambiguity;
- #597 property/value boundary canonicalization;
- #598 write-time temporal-aspect calibration.

Full disposition: [`reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md`](reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md).

### SWE-ContextBench Lite

The synthetic smoke harness is executable and revision-bound but deliberately **non-comparable** to the external research result.

The protocol-comparable external lane remains blocked on the exact frozen research-compatible past-task projection and provenance required by #467. Do not substitute the synthetic fixture and call it equivalent.

### Internal RC conformance fixtures

Repository-owned deterministic fixtures prove specific architecture behavior such as multi-route recovery, current-state vs historical-evidence admission, lifecycle/restart safety, and temporal/currentness invariants.

These are conformance/falsification evidence, not independent external efficacy.

### Orthogonal temporal gauntlets

[`docs/59-orthogonal-temporal-gauntlet-qualification.md`](docs/59-orthogonal-temporal-gauntlet-qualification.md) qualifies candidate gauntlets:

- Ground Truth First remains blocked on artifact availability;
- Microsoft RHELM is runnable but cannot falsify the targeted temporal claims.

#580 supplies the repository-owned temporal/currentness qualification surface. #594 adds adapted external natural-data evidence but does not manufacture an external demotion-efficacy case where the corpus has none.

## Contributor contracts

Two contributor paths are specified and executable; both are documented in [`docs/CONTRIBUTOR_ARCHITECTURE.md`](docs/CONTRIBUTOR_ARCHITECTURE.md):

```text
system author     adapter manifest -> operation envelopes -> capability negotiation
                  -> Gauntlet profile -> native + normalized evidence
benchmark author  integration descriptor -> benchmark-native runner -> native evidence
                  -> optional common-dimension mappings -> evaluator-integrity controls
                  -> optional Gauntlet profile binding
```

Every benchmark in this portfolio has a committed integration descriptor (`reference/agentmem_ref/evaluation/integrations/`, validated against `schemas/memory-benchmark-integration.schema.json`) that records its exact upstream revision, source rights, input-digest and selection rules, native metrics, runner, system invocation surface, provider requirements, normalization mappings, negative controls, and Gauntlet relationship. `agent-memory benchmark list | inspect | validate-integration` read them without executing anything. The `golden-keyed-retrieval-v1` integration is the executable demonstration of the benchmark-author path; it is `baseline_or_probe` evidence and is deliberately absent from the portfolio above.

## Current dashboard and historical scorecards

Canonical current dashboard:

- [`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md)
- `reports/benchmarks/dashboard/current.json`

It reports current accepted evidence, previous accepted evidence/deltas where available, exact provenance, evidence class, and non-numeric states.

Historical generated scorecards remain at:

- `reports/benchmarks/scorecards/scorecards.md`
- `reports/benchmarks/scorecards/scorecards.json`

Those artifacts are useful revision-bound history. They are not the current portfolio authority after #591/#594.

## Remediation evidence

Benchmark-driven remediation evidence is preserved in [`docs/56-benchmark-gauntlet-remediation-evidence.md`](docs/56-benchmark-gauntlet-remediation-evidence.md) and `reports/benchmarks/replays/`.

Important completed steps include:

- explicit ranking/currentness policy and admitted-set BM25;
- runtime-owned serialization for shared handles;
- incremental integrity attestation;
- domain/identity candidate prefiltering;
- deterministic BM25 summation (#576);
- typed write-time semantic evidence (#550);
- identity-first candidate materialization performance repair (#591);
- natural semantic qualification (#594).

## Active RC evaluation path

```text
#591 complete
#594 qualified
canonical dashboard complete
  -> #585 query-intent span calibration
  -> #598 write-time temporal-aspect calibration
  -> redesigned #583
  -> final #580 replay
  -> #584 policy ruling
  -> RC1 declaration decision
```

#596/#597 are high-priority interpreter-quality limitations and can be promoted onto the RC critical path if final evidence shows the declared RC contract cannot tolerate them. They are not automatically authority/safety blockers because the dominant current behavior is conservative ambiguity/abstention.

## Rules for benchmark-driven changes

Do not:

- hardcode benchmark dataset IDs, phrases, or question classes into runtime behavior;
- change frozen input or evaluator semantics while claiming a before/after product comparison;
- populate gold/property aliases after inspecting predictions simply to improve a score;
- collapse missing, blocked, not-run, or evidence-gap states into numeric zero;
- treat a benchmark score as recall admission or mutation authority;
- weaken scope, tenant, currentness, deletion, or PAMA boundaries solely to improve recall.

Do:

- preserve exact revision, input digest, sample/selection identity, configuration, and evidence class;
- keep benchmark-native metrics alongside normalized portfolio dimensions;
- report regressions/tradeoffs as visibly as improvements;
- separate product defects from evaluator defects and external blockers;
- keep pre-remediation and pre-gold evidence immutable;
- use Part R and stratified Part S according to their actual statistical meaning.

## Evaluator integrity

Evaluator correctness is its own evidence dimension.

Mutation probes verify that evaluators react to corruption/failure classes they claim to measure. #594 additionally proves that accepted gold cannot be loaded from draft annotations, verifies the accepted source hash before materializing items, and freezes property aliases before scoring.

```text
evaluator-integrity pass != memory efficacy
```

A trustworthy ruler does not imply the thing measured is good. It merely prevents us from congratulating ourselves with a broken ruler, which is already more discipline than software usually volunteers for.
