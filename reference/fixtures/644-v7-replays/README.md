# #644 Runtime Baseline v7 replay fixtures (`644-v7-replay-dsl/1`)

This directory freezes the five replay contracts that `reports/runtime/baseline-v7-declaration.json` requires:

- `typed-sufficiency-noninterference-and-negative-controls-v1`
- `governed-persisted-typed-slot-sufficiency-admission-recheck-v1`
- `governed-admitted-typed-value-coherence-v1`
- `committed-governed-transition-witness-v1`
- `same-slot-safety-counterevidence-and-immutable-stop-gate-v1`

**Freeze rule.** Every fixture was written from the contract documents named in its `contract_sources`, before any replay runner existed. They were committed in their own commit, ahead of the runner. A fixture is never edited after its first execution. A wrong expectation is superseded by a `-v2` fixture that records the reason, following the `mesa-formal` precedent. The vocabulary, values and categories of the original 126-case independent holdout are not used.

`author_fixtures.py` is the one-shot script that generated the JSON. It is kept for provenance. Tests and the runner never execute it.

## Fixture shape

| Field | Meaning |
|---|---|
| `replay_id`, `fixture_version` | The identity the v7 declaration names, and the fixture revision. |
| `contract_sources` | The contract documents, with their sha256 at `base_commit`. |
| `invariants[]` | `id`, a falsifiable `statement`, and `falsified_by`. |
| `cases[]` | `id`, the `invariants` it tests, a `kind`, the scenario, and `expect`. |
| `stop_lines`, `independence` | Governance text. |

## Scenario operations (`setup`, `between`)

Each case starts from a fresh store: tenant `tenant:v7r`, project `project:a`, actor `agent:v7r`.

| Operation | Effect |
|---|---|
| `remember` (`ref`, `text`, optional `prop`, `valid_from`, `valid_until`, `scope`) | Public `AgentMemory.remember`. `prop` is `{s, a, v, assertion, cardinality, flags?, replaces?}`. With `scope`, the write goes to another project in the same store, under the label `b:<ref>`. |
| `retain_extracted` (`ref`, `text`, `prop`) | Governed retain whose typed record has basis `extracted:v7r@1`, not caller-declared. |
| `forget`, `dispute` (`ref`) | Public facade lifecycle operations. |
| `correct` (`ref`, `text`, `kind`, `cite`) | Public facade correction. `kind` is `state_change` or `error_correction`. `cite` is `none`, `open_proposal` (cites the single open semantic proposal) or `forged` (cites a fabricated proposal identity). |
| `apply_open_proposal` | Public `apply_semantic_proposal` of the single open semantic proposal. |
| `reopen` | Close and reopen the store. |
| `observe_all` | Twin cases only. Both twins perform a governed controlled recall; only the observing twin then runs every observer. |

**Labels.** The first fact of a memory is labelled with its `ref`. Each later current head of the same memory, created by `correct` or `apply_open_proposal`, is `ref@2`, `ref@3`, and so on. `@literal:x` is the raw string `x`. `@canonical:S|A` is the canonical typed slot of subject `S` and attribute `A`.

## Observation kinds

| Kind | What the runner does |
|---|---|
| `coverage` | Governed `ControlledRecallPlanner.recall(query)`. Optional `lexical_limit` and `count_target` set the deterministic controller's plan. `between` operations run after recall. `mutations` are applied to the result. Then `observe_persisted_typed_coverage` runs under `observe_scope` (default: the writer's project). |
| `manual_coverage` | `ControlledRecallResult.observe_evidence_sufficiency` with caller-supplied coverage labels. |
| `pure_assess` | `assess_sufficiency` over a hand-built observation. |
| `forge_report`, `forge_receipt` | Construct a report or receipt carrying a forged field. |
| `witness` | `ControlledRecallPlanner`-independent call of `GovernedMemoryAdapter.governed_applied_transition_witnesses(admitted, context)` with the given labels. |
| `receipt` | Recall, optional mutations, then receipt inspection. |
| `twin` | Two identical stores; compares normalized facade outputs, canonical facts and audit events. |
| `controller_authority` | A controller whose plan claims authority. |

## Observables and matchers

Matchers are `eq`, `ne`, `in` and `not_in`. An observation that raises yields `raises` (the exception class name) and `raises_any`. Otherwise the observables come from the public report (`to_dict()`), the receipt, the witnesses, or the named `probes`:

- `state_unchanged`: substrate digest and audit event count before and after observation.
- `result_unchanged`: candidates, admitted, ranked and refusals.
- `permutation_invariant`: the report with needs reversed.
- `census_oracle`: an independent enumeration of every fact under the same reader.
- `restart_identical`: the same query after reopening.
- `values_absent:<v>`: the string `<v>` does not appear in the serialized report.
- `text_absent`: no fact text appears in the serialized witnesses.

Fields listed under `record` are reported without being asserted.

## Verdicts

- **PASS:** every expectation holds and provenance is clean.
- **FAIL:** an expectation does not hold.
- **BLOCKED:** a precondition is not met, such as a dirty source tree, a missing dependency or a fixture hash mismatch.

A verdict is evidence for review, not v7 acceptance.
