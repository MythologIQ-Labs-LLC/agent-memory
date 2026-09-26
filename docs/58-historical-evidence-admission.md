# Historical-Evidence Admission

Status: reference implementation for #549. This is an **admission and governance** change, not a ranking change. It implements existing doctrine (docs/18 and docs/26) more precisely. It does not depend on ADR-039 acceptance, and it does not rewrite accepted doctrine.

## Mismatch closed

`docs/26-governed-recall-planner.md` requires temporal queries to distinguish four states:

```text
current state
state at time T
historically true but superseded state
incorrect state later corrected
```

It also says a time-scoped query "can retrieve superseded historical truth without replacing current state". `docs/18-temporal-causality-layer.md` separates stale from false, and superseded from corrected.

Before this change, the runtime:

- had one replacement path, `correction`. It recorded every replaced value as **rejected**, which means corrected-as-false.
- refused every event-invalid fact (`superseded_not_current`) for **every** query intent.

As a result, "historically true but superseded" was not representable, and not recallable.

## Two replacement kinds

`correct(..., replacement_kind=...)` rides the same governed correction and the same PAMA decision. The kind grants nothing on its own.

| kind | meaning | record |
| --- | --- | --- |
| `error_correction` (default) | the prior value was wrong | rejected-value registry (readmission control), plus a replacement record of kind `error_correction` |
| `state_change` | the prior value was true until the replacement took effect | **not** a rejected value; a replacement record with the prior `valid_from` and the replacement's `valid_from` as `valid_until` (falling back to the replacement time) |

Replacement records are governance state in `extension_state.replacement_records`. They survive checkpoint and restart unchanged.

## Two admission modes

```text
current_state        (default; every inferred intent)
  event-invalid fact -> refused superseded_not_current

historical_evidence  (only EXPLICIT historical or as_of intent)
  event-invalid fact, state_change, inside validity  -> admit_with_warning
                                                        reason historical_evidence_not_current
  event-invalid fact, state_change, outside validity -> refused outside_historical_validity
  event-invalid fact, error_correction               -> refused corrected_as_false
  event-invalid fact, no replacement record          -> refused superseded_not_current
```

In both modes these checks keep their current order and precedence:

- tenant;
- tombstone and deleted-source derivation;
- dispute;
- the #548 domain-eligibility predicate: isolation domains, compartments, shared-space membership, project, task.

A historical query cannot reach tombstoned, disputed, or wrong-scope state.

Inferred intent never selects historical-evidence admission, however confident the inference is. Temporal intent inference orders; it never widens admission.

## Inspectability

Every admitted candidate on the facade carries `admission_basis`:

- current: `admission_mode: current_state`, `currentness: current_state`.
- historical: `admission_mode: historical_evidence`, `currentness: historical_evidence_not_current`, `replacement_kind`, `valid_from`, `valid_until`, `replaced_at`, `authority_effect: none`.

The canonical decision record uses the schema's existing `admit_with_warning` outcome, so the decision schema is unchanged. Historical admission mutates nothing: `current_fact_uuid` and history are untouched.

## Adversarial evidence

The tests are in `reference/tests/test_historical_evidence_admission.py`. They show:

- a current query and an inferred-historical query both keep superseded state refused;
- explicit historical recall admits a state change as labelled non-current evidence;
- explicit as-of recall respects the validity interval;
- an error-corrected value is refused as `corrected_as_false`;
- disputed and tombstoned superseded state stays refused;
- wrong-scope historical state is never a candidate;
- replacement kinds survive restart;
- an unknown kind is rejected before any commit.

## Boundaries and residual risk

- **The kind is caller-declared, within a governed correction.** Mislabelling an error correction as `state_change` would let a wrong value surface under explicit historical recall. It would surface only as labelled non-current evidence, under the same PAMA decision, evidence, and audit. Stronger evidence requirements for `state_change` are a policy decision and are not added here.
- **The module-level `surface.recall` (contract path) stays current-state only.** Historical-evidence admission is reachable through the facade and planners with explicit intent.
- `history()` is unchanged.
