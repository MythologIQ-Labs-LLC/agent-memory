# ADR-037: Fail-Closed Review Requires a Traversable Remediation Path

## Status

Proposed

Completes the authority leg opened by [ADR-004](ADR-004-pama-controls-mutation-authority.md) and closed in part by ledger entries #15 and #17. Depends on the ratification anchor sealed at entry #16.

## Context

`policy._apply_review` currently discharges `require_review` on `review_satisfied=True` plus any non-empty `approval_refs`. Both are caller-asserted. 51 call sites across 26 files rely on this.

Two of the three legs of this defect are closed. Self-approval is now derived from identity rather than trusted (entry #15), and `require_external_verification` can no longer be discharged by assertion at all (entry #17). The remaining leg is ordinary `require_review`, and the owner has determined it should fail closed.

**Fail-closed alone would deadlock an autonomous agent, and the escape hatches are not real.**

`_envelope` already names three permitted actions in every blocking outcome: `enter_pending_verification`, `collect_more_evidence`, and `defer`. Investigation found **no runtime consumes any of them**. They appear in `policy.py:281-289`, are mirrored in `domain_schema_mutation.py:38-44`, are mapped once in `enforcement_composition.py:58`, and are asserted in tests. No module acts on them. There is no parked state, no evidence-collection loop, and no defer-and-retry.

They are vocabulary, not machinery — and their absence is only harmless while assertion still discharges review. The moment it does not, a blocked autonomous caller has nowhere to go.

The one genuinely working route is a verified reusable grant discharging `require_review` through `evaluate_pama_with_reusable_grant`, made forgery-resistant at entry #16. But `ratify_reusable_grant` refuses self-ratification by construction, so an agent can only *use* a grant it already holds. It cannot obtain one at the moment it blocks.

**The remediation lifecycle already exists in one module.** `DurableDecisionRegistry.propose()` parks a proposal as `PENDING`; `commit(proposal_id, grant)` resumes it when authority arrives. Park, wait, resume on evidence. That is the fourth time this program has found a needed control implemented in one module and absent from the shared evaluator — after identity-derived self-approval, verified/unverified provenance, and the ratification registry.

## Decision

**Fail-closed is adopted for `require_review`, and does not take effect until the remediation path is traversable.** Sequencing is part of the decision, not an implementation detail: flipping 51 sites before `enter_pending_verification` is real would strand every autonomous caller, and that pressure becomes a workaround that outlives the control.

### 1. Sufficiency is a separation-of-parties test, not a human test

The governing invariant is **not** "a human must approve". It is **the proposer may not be the approver**. The codebase already enforces exactly this, and already admits non-human authority:

| Existing control | What it actually requires |
|---|---|
| `_apply_modifiers` derived self-approval (entry #15) | approver ≠ actor |
| `_grant_refusal:364` `self_approval_prohibited` | `grant.principal_id` ≠ `proposal.proposing_actor` |
| `_grant_refusal:378` `delegation_not_permitted_for_risk` | `DELEGATED_POLICY` — a **non-human** authority kind — is valid at low and medium risk |
| `_grant_refusal:372` `human_confirmation_required` | human confirmation required only at **high/critical** risk, or when the target was human-confirmed |

So agent-produced evidence is already a first-class authority source below high risk. This ADR generalizes that graduation into the shared evaluator rather than inventing a new rule.

**Agent-produced evidence may be of higher value than human ratification** where it is more direct, more reproducible, or more current. Provenance class is not a proxy for evidential quality. What matters is whether the evidence meets criteria appropriate to the circumstance, and the circumstance is already encoded as risk class.

### 2. Independence is the bar, and repetition is not independence

The one way this becomes authority laundering is a fleet manufacturing consensus by repeating itself. The repository already rejects that:

- `authority_laundering_harness.py:168` asserts `repetition_not_independent_corroboration` and holds `independent_corroboration` at `not_established` for a repeated observation.
- `autonomous_maintenance_harness.py:35-41` collapses a dependence group before cross-group fusion precisely so that "duplicate/derived/correlated observations [cannot] present themselves as independent evidence merely by increasing row count", with `row_count_is_not_corroboration` asserted.

Evidence from N agents sharing a substrate, a prompt, a model, or an upstream observation is **one** evidence, not N. Independence must be established, not inferred from cardinality — the same standard `reusable_grants` already applies to human precedents via `minimum_independent_human_evidence` (≥2, refused below).

### 3. `enter_pending_verification` becomes a real parked state

Generalize `DurableDecisionRegistry`'s lifecycle: a proposal that cannot discharge parks with its decision, its unmet criteria, and its correlation identity, and is resumable when qualifying evidence arrives. Parking is a governed outcome that emits evidence, not a silent failure.

### 4. `collect_more_evidence` must state what would discharge *this* proposal

Today an actor learns only that it is blocked. It must learn what would unblock it: which criteria are unmet, what class of evidence satisfies each, and what independence bar applies at this risk class. A remediation route an agent cannot compute is not a route.

### 5. The parked state must not become a standing authority

A parked proposal carries no permission. Resumption re-evaluates against current policy and current state — it does not replay a decision made under earlier conditions. The staleness guard (entry #14) applies to resumption exactly as it applies to commit.

## Consequences

**Positive.** Autonomous operation survives fail-closed. Agent evidence is usable where the risk class permits, on stated criteria rather than provenance class. The escape hatches named since the first policy implementation stop being decorative.

**Costs, accepted.**

- 51 call sites must present real evidence or park. That is the point, and it is why the path lands first.
- Parked proposals are state that must be retained, bounded, and expired — retention is [#363](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/363)'s domain, and this ADR adds to its load.
- Establishing independence is harder than counting approvals, and will sometimes conclude that plentiful evidence is one evidence.

**Risks.**

- **Authority laundering by fleet consensus** — the primary risk, mitigated by §2, which is doctrine the repository already holds and tests.
- **Parked-state pressure.** If parking is common, the fix is the criteria or the risk grading, not loosening the gate.

## Open questions for the owner

1. **May an agent's parked proposal be resumed by evidence that agent itself later produces**, given the proposer ≠ approver invariant? A same-actor resumption looks like deferred self-approval. Suggested: no at any risk class, consistent with `self_approval_prohibited`.
2. **What establishes independence between two agents** — distinct model, distinct substrate, distinct observation channel, distinct operator? §2 sets the bar without defining the test, and the test is the load-bearing part.
3. **Does `delegated_policy` at medium risk require one separated agent or two?** `reusable_grants` demands ≥2 independent human precedents for review reduction; the agent analogue is unstated.

## Related

- Ledger entries #14 (staleness on delete), #15 (derived self-approval), #16 (ratification anchor), #17 (external verification requires attestation)
- [#362](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/362) public API boundary — the parked-state type is a public contract
- [#363](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/363) production state profile — parked proposals are retained state
