# RC1 Evidence Closeout

Status: active RC1 release-evidence package under umbrella #410.

## Purpose

Agent Memory now has a supported developer facade, a deterministic end-to-end cognitive-memory scenario, a closed known-source ancestry harvest, and a governed cognitive-classification provider seam. The remaining RC1 work is therefore primarily empirical release evidence, not another core architecture slice.

The machine-readable companion is emitted by:

`reference/run_rc1_evidence_closeout.py`

## Current product boundary

The bounded RC product path is:

```text
AgentMemory.open(...)
-> remember
-> multi-route candidate generation
-> governed final admission
-> correct / supersede
-> close and reopen
-> corrected state remains current
-> governed prune / forget
-> close and reopen
-> tombstone, history, currentness and configuration binding reconstruct
```

The developer facade landed through #478. The composed lifecycle proof landed through #480. The known-source ancestry/peer harvest closed through #470/#494. The governed cognitive-classification provider seam and replay baselines landed through #490/#500/#515.

## Evidence dimensions

### Product usability

Status: **bounded, implemented**.

The facade and scenario prove a developer can use the supported local runtime without manually assembling internal PAMA objects for ordinary low-risk work. Governed decisions and receipts remain inspectable.

This is not a production 1.0 claim.

### Retrieval and memory quality

Status: **bounded internally; external portfolio in progress**.

#466 provides the continuous retrieval and memory regression contract. #469 provides the protocol-ready real SWE-ContextBench Lite runner that preserves the 99-query / 100-gold-edge denominator, including the multi-gold query. #493 adds a pull-and-run comparison harness spanning no-memory, deterministic lexical retrieval, and canonical governed Agent Memory behind one shared input contract.

Repository-owned deterministic fixtures are useful regression evidence. They are not a substitute for exact external corpora and provenance required for protocol-comparable measurement.

The external benchmark program is now broader than SWE-ContextBench alone:

- #467: protocol-comparable SWE-ContextBench Lite retrieval evidence;
- #516: LongMemEval retrieval/currentness profile;
- #517: AgentMemBench / MemDialogue operational profile;
- #518: evaluator-integrity mutation probes across accepted external profiles;
- #519: benchmark-portfolio execution coordination.

These profiles must continue to report retrieval, currentness, answer-generation, performance, privacy, governance, and evaluator-integrity dimensions separately where applicable.

### Benchmark evaluator integrity

Status: **implemented as a repository guard; external-profile integration in progress**.

#470/#494 harvested a generic lesson from the final UOR/PrismPM review: an evaluator should demonstrate that controlled failures actually damage the metrics expected to detect them.

`reference/run_benchmark_integrity_mutants.py` exercises admitted noise, missing gold edges, candidate/admission collapse, rank damage, and final-admission refusal.

```text
mutation-probe pass
    != benchmark quality
    != external comparability
    != memory authority
```

#518 owns carrying this guard into the accepted external benchmark profiles.

### Performance

Status: **bounded**.

The qualified SQLite single-host profile and benchmark runners report performance separately from retrieval quality and governance. No universal latency, scale, or resource envelope is claimed.

### Governance

Status: **bounded and strongly exercised**.

Current evidence includes wrong-scope refusal, supersession/currentness behavior, confidence non-authority, metabolism non-authority, external-peer evidence normalization, exact-version Agent Manifest/TRACE qualification, and classification-provider isolation from recall admission and durable mutation authority.

The governing boundary remains:

```text
retrieval relevance != recall authority
classifier output != truth
classifier confidence != permission
ranking != recall admission
recommendation != mutation authority
external verification != Agent Memory authority
checkpoint acceptance != appended-operation semantics
```

### Cognitive classification

Status: **provider-neutral seam implemented; live provider evidence pending**.

#515 reuses the existing component registry and adds Agent Memory-owned classification request/result semantics with reconstructable provider/model/runtime/config/evidence identity. It covers abstention, disagreement, malformed output, unavailability, explicit fallback, deterministic metadata override, cross-scope refusal, and stale-source refusal.

The ordinary-LLM and specialized-model replay providers are frozen simulation/conformance baselines. They are not live performance claims. #495 owns live provider qualification.

No hosted provider is required for Agent Memory operation.

### Runtime recovery

Status: **bounded**.

The qualified `sqlite_single_host_v1` profile reconstructs correction/currentness, history, tombstone state, and configuration binding across restart in the RC scenario.

Distributed or multi-host SQLite behavior is not established.

## External SWE-ContextBench status

Status: **external blocked** under #467.

The Agent Memory runner and comparison harness are ready. Protocol-comparable measurement still requires the exact frozen research-compatible inputs:

- exact redacted past-task projections;
- exact batch and distractor selection;
- consistency-query identity when explicitly selected.

Until those inputs and their provenance are available, the truthful statement is:

```text
runner readiness = complete
protocol-comparable external result = not yet available
```

No external score is inferred from the public parquet subset or from historical metadata.

## Harvest closeout status

Status: **complete** through #470/#494 for the known source set reviewed in that snapshot.

The final harvest matrix records explicit dispositions across EvolveAI, CodeGenome, COREFORGE, UOR-derived repositories, Microsoft Agent Governance Toolkit, TRACE, Agent Manifest, cMCP, Foundry, and PrismPM. Generic mechanisms judged useful are either native Agent Memory functionality or explicitly bounded follow-on implementation. Other mechanisms are classified as optional interoperability, specialized-source-only, intentionally not adopted, or obsolete/superseded.

Future upstream changes create new bounded reviews. They do not make the historical harvest permanently incomplete.

## Longitudinal evidence

Status: **instrumentation and field programs open; not missing core implementation**.

- #388 owns governed-memory field efficacy;
- #408 owns the semantic-recall/canonical-truth longitudinal case study;
- #496/#501 own reusable privacy-preserving longitudinal observation and analysis mechanics.

These programs should establish whether the architecture materially improves real work over time. Synthetic or replay evidence must never be mislabeled as field evidence.

## Known limitations

Current RC evidence does not establish:

- production 1.0 readiness;
- distributed or multi-host SQLite durability;
- a protocol-comparable external SWE-ContextBench result before exact frozen inputs arrive;
- broad real-world efficacy across independent external memory workloads until #516/#517 and later runs land;
- live cognitive-classifier provider performance until #495 records real executions;
- physical permanent-deletion completion from the reversible pruning path used in the RC product scenario;
- universal answer-generation quality from retrieval-only evidence;
- authority from confidence, similarity, reinforcement, graph proximity, vector score, metabolism score, classifier score, or external verifier success;
- authority for any learned controller over PAMA, durable commit, deletion, tenancy, scope, or recall admission.

## Reproducible closeout artifact

Generate the machine-readable manifest against an exact revision:

```bash
PYTHONPATH=reference python reference/run_rc1_evidence_closeout.py \
  --agent-memory-revision <exact-40-hex-commit> \
  --output rc1-evidence-closeout.json
```

The manifest preserves product usability, quality, performance, governance, runtime recovery, external benchmark status, and harvest status as separate surfaces. It deliberately emits no aggregate memory-health score.

## Release posture

Agent Memory should now be evaluated as a usable, governed, single-host memory system whose major core architecture is implemented. The remaining uncertainty is increasingly empirical: how well it performs across independent real-world workloads, how much operational value it creates over time, and where added complexity fails to earn its cost.

RC1 should not be documented as production 1.0 merely because bounded implementation gates are green. External and longitudinal evidence should tighten or weaken claims as results arrive, including negative results.
