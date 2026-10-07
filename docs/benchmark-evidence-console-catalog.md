# Benchmark Evidence Console catalog contract

Status: **F1 implementation under #698**

Related: #696, PRD-002, proposed ADR-041.

## Purpose

The Benchmark Evidence Console consumes one deterministic, read-only projection:

`reports/benchmarks/ui/catalog.json`

The catalog is presentation infrastructure. It does not execute benchmarks, modify evidence, authorize runtime behavior, or create an aggregate memory score.

The source direction is:

~~~text
native benchmark evidence
  -> normalized run manifests
  -> scorecards + canonical dashboard
  -> benchmark UI catalog
  -> future static UI
~~~

The frontend must not rebuild comparison semantics by crawling native benchmark files.

## Build and freshness

Generate:

~~~bash
python scripts/build_benchmark_ui_catalog.py
~~~

Verify the committed catalog is current:

~~~bash
python scripts/build_benchmark_ui_catalog.py --check
~~~

The check compares the parsed committed catalog with a freshly generated projection. This avoids treating harmless JSON formatting differences as evidence drift while still refusing semantic drift.

The writer itself is deterministic: unchanged repository inputs produce the same Python object and the same sorted/indented JSON bytes.

## Snapshot identity

The snapshot identity is bound to the Git object identities of exactly three projection inputs:

- `reports/benchmarks/dashboard/current.json`;
- `reports/benchmarks/scorecards/scorecards.json`;
- the `reports/benchmarks/normalized/` Git tree.

Conceptually:

~~~text
git-evidence-v1:
  <dashboard blob>:
  <scorecards blob>:
  <normalized tree>
~~~

Unrelated repository commits do not create a new benchmark snapshot.

The catalog separately exposes whether the repository revision executing the builder is newer than the dashboard's evidence revision. That is contextual staleness information, not part of snapshot identity.

## Catalog domains

### benchmarks

One registry record per benchmark/task-profile identity represented by normalized runs.

The record preserves source, dataset/input identities, systems and run ids. Profiles are not collapsed merely because they belong to the same benchmark family.

### metrics

Typed native metric definitions keyed by:

~~~text
benchmark profile
  + dimension
  + native metric id
~~~

The registry preserves:

- native metric name;
- dimension;
- directions observed;
- units observed;
- states observed;
- native metric notes.

A future UI may organize metrics by capability, but it must retain this native identity.

### systems

One registry record per system id, retaining observed kinds, revisions, adapters and run ids.

A system name alone is never a comparison identity.

### runs

Presentation-safe summaries of every committed normalized run.

A run contains:

- benchmark identity;
- system identity;
- execution identity;
- dimension states;
- typed metric observations;
- limitations;
- evidence pointers.

`native_results` is intentionally not duplicated into the summary catalog. Deep native evidence remains available through evidence pointers.

### comparison_sets

Comparison sets are projected from the existing deterministic scorecards.

The UI does not independently group systems.

Every set carries:

- the existing fail-closed comparison identity;
- systems and revisions;
- baseline system where one exists;
- scorecard dimensions/metric cells;
- exact comparison state;
- evidence class.

Accepted frozen external lanes are marked `same_harness`. Other exact profile groups are `same_profile`.

Both use the existing comparison contract. Neither is a universal market verdict.

### published_references

Published vendor/research values from the canonical dashboard remain a separate domain.

Every published reference carries:

~~~text
comparison_state: published_reference
eligible_for_numeric_delta: false
~~~

The future UI can show these values as market context. It may not silently add them to an exact comparison set.

### longitudinal_tracks

The catalog preserves the canonical dashboard's Agent Memory longitudinal tracks.

These remain revision-bound evidence. They are not market comparisons.

### coverage

Coverage projects:

- portfolio profiles;
- measured and unmeasured dimensions;
- benchmark evidence states;
- product findings;
- the explicit missing-state vocabulary.

The missing-state vocabulary is:

- `not_run`;
- `not_measured`;
- `evidence_gap`;
- `blocked`;
- `unsupported`;
- `not_applicable`;
- `non_comparable`;
- `absent`.

These states are never numeric zero.

### evidence_index

Every projected measured run resolves to its normalized manifest and any committed artifact pointers carried by that manifest.

Published references resolve to their recorded external source.

## Comparison rule

A numeric UI delta is permitted only inside a catalog `comparison_set` whose `eligible_for_numeric_delta` is true and whose metric row itself contains compatible measured values.

The catalog never emits a numeric delta between a published reference and a local/same-harness run.

The existing `agentmem_ref.evaluation.contract.compare_runs` and scorecard pipeline remain the comparison authority.

## Wireframe contract

The canonical structural inventory lives at:

- `docs/prd/PRD-002-wireframes.md`;
- `docs/prd/PRD-002-wireframe-fixtures.json`.

The F1 test suite verifies all F00-F24 and R01-R04 frame seed classes can be represented by catalog domains.

A new production frame that requires semantics the catalog cannot express must change the projection contract deliberately. It must not introduce frontend-only evidence semantics.

## Adding a benchmark/profile

1. Add/freeze the benchmark through the existing evaluation registry and evidence process.
2. Normalize the accepted result through the common run contract.
3. Regenerate scorecards.
4. Regenerate the canonical dashboard where the evidence program requires it.
5. Regenerate the UI catalog.
6. Add a test only when the new benchmark introduces a genuinely new catalog contract.

Do not special-case a benchmark in the UI solely to make its score convenient to display.

## Adding a metric

Metrics enter the catalog from normalized run dimensions.

To add a metric:

1. define it in the benchmark normalizer with native semantics;
2. provide state, direction and unit/population where applicable;
3. regenerate normalized evidence and scorecards;
4. regenerate the UI catalog.

Do not create presentation-only metric values that have no normalized evidence origin.

## Adding a system/comparator

A system enters the registry when a normalized run exists.

To participate in numeric comparison, the run must enter an exact scorecard comparison identity under the existing fail-closed contract.

A published external score may be added as published-reference context without becoming comparison-eligible.

## Adding a comparison profile

Comparison profiles are created by the benchmark/evaluation layer, not the UI.

The UI catalog consumes the resulting scorecard groups.

If two runs do not share the existing comparison identity, the UI catalog must not manufacture one.

## Validation

The F1 contract tests cover:

- JSON Schema validation;
- deterministic snapshot identity;
- snapshot change when projection-relevant evidence changes;
- real LongMemEval same-harness Agent Memory vs Mem0 values;
- published Hindsight isolation from numeric comparison;
- explicit missing-state preservation;
- no aggregate score;
- evidence pointers for measured runs;
- native metric identity;
- coverage for every canonical PRD-002 wireframe seed class;
- committed catalog freshness.

This is the boundary that lets #699 and #700 proceed without inventing benchmark semantics in the frontend.
