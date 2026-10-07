# ADR-041: Benchmark Reporting Is a Deterministic Read-Only Projection With Fail-Closed Comparability

Status: **Proposed**

Related: #696, PRD-002, #574, #600, #601, #668, #694

## Context

Agent Memory now maintains several benchmark evidence classes:

- Agent Memory longitudinal evidence;
- same-harness multi-system evidence;
- published external reference evidence;
- adapted/diagnostic evidence;
- runtime/implementation qualification evidence;
- explicit missing states such as blocked, not-run, unsupported, and evidence-gap.

The repository already has deterministic benchmark normalization and scorecard generation.

A future reporting UI creates an architectural risk: a presentation layer can accidentally become a second evidence system by recomputing metrics, deciding comparability, copying scores into application data, flattening missing states, or mixing incompatible benchmark semantics.

The reporting UI therefore needs an explicit architecture boundary before implementation.

## Decision

### 1. Benchmark evidence remains canonical outside the UI

The UI is not an evidence authority.

Canonical evidence remains repository-owned benchmark artifacts and accepted deterministic derivations.

The data flow is one direction:

~~~text
native evidence
  -> deterministic normalization
  -> deterministic scorecards/dashboard
  -> deterministic UI projection
  -> presentation
~~~

Presentation never reverses this direction.

### 2. The frontend consumes a versioned UI catalog

The frontend does not crawl arbitrary repository files and infer benchmark semantics at runtime.

A deterministic projection builder produces a versioned catalog, conceptually at:

reports/benchmarks/ui/catalog.json

The catalog may point to larger per-case artifacts rather than embedding them.

The catalog includes at least:

- snapshot identity;
- benchmark/profile registry;
- typed metric registry;
- system registry;
- run summaries;
- valid comparison sets;
- longitudinal transition metadata;
- evidence coverage states;
- published-reference records;
- evidence/provenance pointers.

### 3. Comparability is decided before presentation

The frontend must not infer comparability from matching labels, units, percentages, benchmark-family resemblance, system names, or user selection.

A shared comparison contract or deterministic projection builder records comparison eligibility.

A comparison identity may include:

- benchmark;
- source/dataset revision;
- input digest;
- task profile/plane;
- selection;
- sample count;
- retrieval/context budget where material;
- answer/judge identity where material;
- metric semantics.

Comparison is fail-closed.

No valid comparison state means no numeric delta.

### 4. Evidence class and result outcome are separate dimensions

Examples:

~~~text
Ahead       + Same harness
Behind      + Same harness
Improved    + Longitudinal
High score  + Published reference
Unknown     + Evidence gap
~~~

Visual treatment must not imply that a published reference is equivalent to same-harness evidence.

### 5. Missing states remain typed states

The projection preserves states such as:

- not_run;
- not_measured;
- evidence_gap;
- blocked;
- unsupported;
- not_applicable;
- non_comparable;
- absent.

They are never converted to numeric zero.

### 6. Native metric semantics remain inspectable

Normalization may support capability navigation, but every normalized metric remains traceable to native benchmark name and definition.

The UI may not promote retrieval recall into generic "memory accuracy" or otherwise strengthen a metric's meaning.

### 7. No universal aggregate score

The projection does not define a weighted overall Agent Memory score or universal system rank.

The UI may calculate/display deltas within a valid comparison set according to typed metric direction.

Capability-level posture may be derived only from explicit explainable rules and must not be presented as authority or a universal scalar.

### 8. Snapshot identity is deterministic and shareable

A generated UI evidence state has a stable snapshot identity bound to catalog/evidence revision.

Shareable historical views resolve to that immutable evidence state.

A current mutable route may point to the newest accepted catalog, but historical share links remain revision-bound.

### 9. Protocol changes create longitudinal discontinuities

A benchmark/profile/evaluator change that invalidates direct comparison produces a break in longitudinal presentation.

The UI does not calculate or draw a continuous trend across a comparison boundary unless the comparison contract permits it.

### 10. Static-first deployment is preferred initially

F1-F4 should not require a database or application server.

Preferred shape:

~~~text
repository evidence
  -> deterministic catalog build
  -> static assets
  -> static application
~~~

This supports reproducible snapshots, local use, simple hosting, low operational complexity, and reporting/runtime isolation.

A dynamic service is optional later if real requirements justify it.

### 11. Row-level evidence is separately indexed

Per-case evidence can be large.

The main catalog contains summary metadata and deterministic pointers/indexes.

Failure-analysis views load row-level chunks on demand.

### 12. The UI remains read-only with respect to Agent Memory authority

The reporting surface may expose links to issues, PRs, evidence, and methodology.

It does not mutate memory state, approve benchmark evidence, authorize architecture changes, or make benchmark results operational authority.

## Proposed architecture

~~~text
                         CANONICAL EVIDENCE

 native reports    execution identity    lane/profile    references
      \                  |                   |              /
       \                 |                   |             /
        +---------- normalization / scorecards -----------+
                               |
                               v
                      UI PROJECTION BUILDER
                               |
             +-----------------+------------------+
             |                 |                  |
             v                 v                  v
       registries        comparison sets      evidence index
             \                 |                  /
              +----------------+-----------------+
                               |
                               v
                    versioned UI catalog
                               |
                     +---------+----------+
                     |                    |
                     v                    v
                static console      row-level chunks
~~~

The projection builder may derive presentation-safe facts such as valid delta, coverage state, current accepted run, and snapshot identity.

It may not reinterpret native benchmark outcomes beyond declared normalization contracts.

## Consequences

### Positive

- presentation cannot silently redefine benchmark truth;
- same-harness and published evidence remain structurally distinct;
- invalid comparisons fail closed;
- static snapshots are reproducible;
- frontend implementation can evolve without changing evidence semantics;
- public and engineering views can share one catalog;
- row-level diagnostics can scale independently.

### Costs

- metric and benchmark registries require explicit maintenance;
- new benchmark families may require schema evolution;
- frontend features are constrained by evidence that actually exists;
- historical snapshots require retention of catalog/evidence identities;
- some convenient cross-benchmark charts are intentionally unavailable.

## Rejected alternatives

### Frontend reads raw reports directly

Rejected because it duplicates normalization/comparison logic and invites semantic drift.

### Database becomes canonical benchmark store

Rejected for the initial architecture because revision-bound repository evidence already exists and a database would add synchronization/provenance problems without a demonstrated need.

### One normalized score per benchmark/system

Rejected because distinct benchmarks measure different constructs.

### One overall system leaderboard

Rejected because a universal scalar would erase evidence class, capability differences, and benchmark semantics.

### Live benchmark execution from the console

Rejected for the initial architecture because execution has separate freezing, reproducibility, and evidence workflow.

### Published vendor data mixed into same-harness tables without structural distinction

Rejected because published-reference context is not locally reproduced head-to-head evidence.

## Relationship to doctrine

This ADR extends benchmark/reporting doctrine only.

It preserves:

~~~text
benchmark score != memory authority
published vendor score != same-harness comparator
historical self-comparison != market position
implementation language != doctrine
~~~

The UI projection has no authority effect on memory state, recall admission, currentness, lifecycle, or runtime governance.

## Decision status

**Proposed.**

Accept only when implementation of the benchmark evidence console becomes an active tranche or when the projection contract is otherwise needed as a stable repository interface.

Documenting it now protects future UI work from creating an accidental second benchmark truth system while keeping the feature post-RC.
