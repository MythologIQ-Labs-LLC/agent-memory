# PAMA Decision Table

## Purpose

This document turns the governance model in [`04-governance-and-pama.md`](04-governance-and-pama.md) into an inspectable decision table: mutation type and risk class map to a minimum authority outcome, and named modifiers raise or lower that minimum under defined conditions.

The table is policy data, not code. An implementation may encode it as configuration, rules, or a policy engine, but the mapping must satisfy the authority resolution invariant: for fixed committed inputs, current state, and policy version, the resulting authority envelope is deterministic or formally bounded.

This document implements the decision-table requirement of [`adr/ADR-004-pama-controls-mutation-authority.md`](adr/ADR-004-pama-controls-mutation-authority.md).

## How to read the table

Outcomes are ordered by strictness:

```text
allow < allow_with_ledger < require_review < require_external_verification < block
```

- A cell is the **minimum** outcome for that mutation type at that risk class. Policy may always be stricter; it must not be weaker.
- Modifiers move the outcome along this ordering. A modifier can only relax an outcome when the table row explicitly marks it relaxable.
- `abstain`, `quarantine`, and `collect_more_evidence` are lateral outcomes: they defer the decision without granting authority. A deferral never counts as satisfaction of a review or verification requirement.
- `block` is absorbing. No modifier, score, or estimator output relaxes a `block` produced by a prohibited-action rule.

## Base decision table

Mutation classes are those defined in `04-governance-and-pama.md`. Risk classes follow the same doc: low, medium, high, critical.

| Mutation type | Low | Medium | High | Critical |
|---|---|---|---|---|
| Runtime assembly | allow_with_ledger | allow_with_ledger | require_review | require_review |
| Score adjustment | allow_with_ledger | allow_with_ledger | require_review | block |
| Link creation | allow_with_ledger | allow_with_ledger | require_review | require_review |
| Link deletion | allow_with_ledger | require_review | require_review | require_external_verification |
| Correction | require_review | require_review | require_review | require_external_verification |
| Promotion | allow_with_ledger | require_review | require_review | require_external_verification |
| Crystallization | require_review | require_review | require_external_verification | require_external_verification |
| Pruning | allow_with_ledger | allow_with_ledger | require_review | require_external_verification |
| Permanent deletion | require_review | require_review | require_external_verification | require_external_verification |
| Scope expansion | require_review | require_review | require_external_verification | block |
| Policy mutation | require_review | require_external_verification | require_external_verification | require_external_verification |

Reading notes:

- Score adjustment at critical risk is `block` because a score change on identity, credential, compliance, or safety-boundary memory is not a score change; it is an attempt to route around governance. Re-evaluation of such memory goes through correction or policy mutation instead.
- Scope expansion at critical risk is `block` because cross-tenant expansion of critical-class memory has no autonomous path. It requires a policy-level decision, which is a policy mutation, not a scope-expansion request.
- `require_external_verification` means verification by an authority outside the requesting component: a human approver, an independent certification service, or an equivalently authoritative system. The requesting estimator can never be its own verifier.
- Policy mutation never resolves below `require_review` at any risk class, and human approval remains the default expectation per `04-governance-and-pama.md`.

## Modifier rules

Modifiers apply after the base cell is selected, in the order listed. Escalating modifiers accumulate; the outcome is the strictest produced.

### Escalating modifiers

| Modifier | Condition | Effect |
|---|---|---|
| M-IRREV | mutation is irreversible or destroys its own rollback path | raise to at least require_review; at high/critical risk raise to at least require_external_verification |
| M-EVID | evidence quality below policy floor for this mutation type | raise one step and require collect_more_evidence before re-evaluation |
| M-DISPUTE | target memory is disputed or contradiction pressure is material | raise to at least require_review |
| M-DISAGREE | material estimator disagreement on a required input | raise one step |
| M-OOD | out-of-distribution or out-of-calibration-scope signal on a required estimate | raise to at least require_external_verification for promotion, crystallization, deletion, and scope expansion |
| M-CERT | certification missing, expired, or revoked where the mutation type requires it | block crystallization; raise promotion to require_review |
| M-AUTH | actor authority cannot be reconstructed | block |
| M-POLICY | policy version missing or ambiguous | block for high/critical; require_review otherwise |
| M-SCOPE | target actor, tenant, or purpose is unclear | block any sharing or scope expansion; raise others to require_review |
| M-EVIDENCE-DESTRUCTION | mutation would remove evidence referenced by audit, dispute, or hold | block until the retention conflict is resolved per `28-retention-deletion-and-tombstones.md` |

### Relaxing modifiers

Relaxation exists so reversible, well-evidenced, narrow mutations are not buried under review queues. It is deliberately harder to trigger than escalation.

| Modifier | Condition | Effect |
|---|---|---|
| R-REV | mutation is cheaply reversible with a verified rollback path and a reversible tombstone | may lower require_review to allow_with_ledger, only for rows marked relaxable below |
| R-DELEG | acting under an explicit, unexpired, in-scope delegation record | may lower one step, never below allow_with_ledger, never for policy mutation or scope expansion |

Relaxable rows: link deletion (low/medium), pruning (high), promotion (medium). No other cell is relaxable. Crystallization, permanent deletion, scope expansion, and policy mutation are never relaxable.

Reversibility works in both directions and asymmetrically: irreversibility escalates everywhere, reversibility relaxes only where the table says so. A verified rollback path is a precondition for relaxation, not evidence of safety.

### What modifiers never do

```text
high confidence        -> never relaxes any outcome
high saturation        -> never relaxes any outcome
repetition / access    -> never relaxes any outcome
prior similar approval -> never substitutes for current authority
deferral outcomes      -> never satisfy review or verification
```

Confidence is an input to evidence quality at most. It has no direct lane to authority.

## Worked mutation examples

Each example gives the request, the resolved outcome, the before and after state, and the ledger requirement. Receipts follow [`../schemas/decision-receipt.schema.json`](../schemas/decision-receipt.schema.json); events follow [`30-memory-observability-and-audit-events.md`](30-memory-observability-and-audit-events.md).

### 1. Score adjustment

Request: decay pass lowers sigma on a task note after two weeks without meaningful reuse.

- Base cell: score adjustment × low = `allow_with_ledger`. No modifiers trigger.
- Before: `sigma 0.58`, state `reinforced`. After: `sigma 0.44`, state `reinforced`.
- Ledger: score-adjustment event with estimator refs, estimator version, and decay-profile ref. No receipt approval refs required.

### 2. Link creation

Request: planner proposes an evidence-backed relation between a decision memory and the commit that implemented it.

- Base cell: link creation × medium = `allow_with_ledger`. M-EVID does not trigger: both endpoints carry provenance and the relation cites the commit as evidence.
- Before: no relation. After: `implements` edge with evidence ref.
- Ledger: graph-mutation event recording both endpoint ids, relation type, and evidence refs.

### 3. Link deletion

Request: remove a `supports` edge that a retracted source had justified.

- Base cell: link deletion × medium = `require_review`. R-REV applies (edge restoration is cheap, tombstone retained): relaxed to `allow_with_ledger`.
- Before: edge present, source marked retracted. After: edge tombstoned, not destroyed; dependent saturation re-scored.
- Ledger: graph-mutation event plus tombstone ref; the retraction that motivated the deletion is cited as evidence.

### 4. Correction

Request: user corrects a stored preference that was inferred wrongly.

- Base cell: correction × high (user preference) = `require_review`. The user's own correction with explicit approval satisfies review; M-AUTH does not trigger because the actor is the memory's owner principal.
- Before: `preference: weekly summary`, state `crystallized`, dispute open. After: `preference: daily summary`, state `corrected`, prior value preserved as history with supersession link per `18-temporal-causality-layer.md`.
- Ledger: correction event with approval ref (the user's action), before/after state, and rollback path. The old value is superseded, not erased.

### 5. Promotion

Request: recurring, corroborated project decision reaches candidate threshold; system proposes promotion toward durable state.

- Base cell: promotion × high (durable decision) = `require_review`. M-DISAGREE does not trigger; trap-class check passes.
- Before: state `reinforced`, `sigma 0.86`, certification absent. After: state `pending_verification`. Not durable yet.
- Ledger: lifecycle-transition event with pama inputs, permitted-action set, and selected action. Receipt records that review is the binding step; saturation alone did not promote.

### 6. Crystallization

Request: the reviewed decision from example 5, now certified, requests crystallization.

- Base cell: crystallization × high = `require_external_verification`. Satisfied by the certification gate: certifier is independent of the proposing estimator. M-CERT does not trigger.
- Before: state `pending_verification`, certification `pass`, dispute clear, scope defined. After: state `crystallized`, bound to evidence set, policy version, estimator context, and scope of approval.
- Ledger: crystallization receipt binding certification ref, approval refs, scope, and rollback path (demotion per `31-recovery-rollback-and-replay.md`). If certification were missing: blocked, regardless of sigma.

### 7. Pruning

Request: eviction pass proposes pruning a stale runtime trace from active recall.

- Base cell: pruning × low = `allow_with_ledger`. M-EVIDENCE-DESTRUCTION does not trigger: nothing references the trace as evidence.
- Before: state `stale`, in active recall. After: state `pruned`, reversible tombstone retained per `28-retention-deletion-and-tombstones.md`; content recoverable within the retention window.
- Ledger: pruning event with tombstone ref. Contrast: the same request against a memory cited in an open dispute is blocked by M-EVIDENCE-DESTRUCTION until the hold resolves — see `fixtures/pruning-with-audit-preservation.json`.

### 8. Policy mutation

Request: agent proposes lowering the candidate threshold from 0.80 to 0.70 because "too few memories are promoting."

- Base cell: policy mutation × high = `require_external_verification`. No relaxation path exists for policy mutation.
- Before: `candidate_threshold 0.80`, policy version `p-14`. After (only if approved by human or equivalently authoritative review): `candidate_threshold 0.70`, policy version `p-15`, prior version retained for replay.
- Ledger: policy-mutation receipt with approval refs, both policy versions, and effective time. An agent observing its own promotion rate is an estimator; an estimator proposing to widen its own authority is exactly what this row exists to stop.

## Interaction with lifecycle gates

The table composes with, and never replaces, the promotion and crystallization gates of `04-governance-and-pama.md`:

```text
can_promote     requires pama_outcome in [allow, allow_with_ledger, require_review]
can_crystallize requires pama_outcome in [allow, allow_with_ledger] and certification pass
```

A table outcome of `require_review` therefore admits a memory to Pending Verification at most. Crystallization additionally requires the review to have resolved and certification to pass. The decision table decides authority; the gates decide sequence.

## Conformance cases

| Case | Expectation | Fixture |
|---|---|---|
| High-confidence false memory requests promotion | confidence does not relax the promotion row | [`../fixtures/high-confidence-false-promotion.json`](../fixtures/high-confidence-false-promotion.json) |
| Sigma jitter at the candidate threshold | outcome stable under M-DISAGREE and hysteresis; no churn | [`../fixtures/threshold-jitter.json`](../fixtures/threshold-jitter.json) |
| Unauthorized actor requests correction | M-AUTH blocks regardless of estimate quality | [`../fixtures/unauthorized-mutation-attempt.json`](../fixtures/unauthorized-mutation-attempt.json) |
| Deletion proposed from predicted low utility | permanent-deletion row plus M-IRREV; utility estimate cannot authorize | [`../fixtures/irreversible-deletion-under-uncertain-utility.json`](../fixtures/irreversible-deletion-under-uncertain-utility.json) |
| Delegated actor acts after delegation expiry | R-DELEG does not apply; expired delegation escalates, not relaxes | [`../fixtures/expired-delegation.json`](../fixtures/expired-delegation.json) |
| Concurrent conflicting mutation requests | no silent last-writer-wins; second request re-resolves against new state | [`../fixtures/concurrent-conflicting-mutation.json`](../fixtures/concurrent-conflicting-mutation.json) |
| Authority laundering through a permissive path | outcome depends on mutation type actually requested, not the path that carried it | [`../fixtures/authority-laundering.json`](../fixtures/authority-laundering.json) |
| Policy applied under drifted estimator version | M-OOD escalates consequential mutations | [`../fixtures/policy-estimator-version-drift.json`](../fixtures/policy-estimator-version-drift.json) |

## Doctrine

The decision table is the shape of PAMA, not a replacement for it.

A cell grants nothing by itself. It states the weakest outcome a compliant policy may return, given committed inputs whose provenance and uncertainty are inspectable.

Estimates inform the inputs. Authority comes from the table, its modifiers, and the approvals they require — never from the estimate.
