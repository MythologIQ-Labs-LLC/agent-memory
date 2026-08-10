# Governance and PAMA

## Purpose

PAMA defines mutation authority for agentic memory systems.

The central question is not whether an agent can change memory. The central question is whether it is allowed to change memory, under what scope, with what evidence, and with what rollback path.

PAMA also defines the boundary between uncertain inference and governed consequence.

**Probabilistic or learned systems may estimate confidence, trust, relevance, contradiction, sensitivity, utility, or risk. PAMA determines what those estimates are allowed to change.**

## PAMA definition

PAMA means Proportional Adaptive Mutation Authority.

It is a governance model for deciding when memory, policy, state, identity relations, or derived representations may be changed by an agent or system.

## Why PAMA exists

Agentic memory becomes dangerous when the system can:

- rewrite durable memory without review
- promote repeated claims into truth
- mutate user preferences without consent
- overwrite project decisions because a new session felt confident
- prune evidence needed for later accountability
- crystallize hallucinations
- convert probabilistic confidence directly into mutation authority
- infer missing permission because an action appears useful

The point of PAMA is to make adaptive memory useful without letting adaptation become silent self-corruption.

## Mutation classes

| Class | Description | Default authority |
|---|---|---|
| Runtime assembly | Build context from existing memory | allowed with audit |
| Score adjustment | Update saturation, confidence, or decay pressure | allowed with ledger when low risk |
| Link creation | Add graph relation between memory units | allowed if evidence-backed |
| Link deletion | Remove graph relation | require review unless low risk |
| Correction | Amend disputed memory | require provenance and ledger |
| Promotion | Move memory toward durable state | require certification gate |
| Crystallization | Make memory canonical or exact-address durable | require explicit authority |
| Pruning | Remove from active recall | require reversible tombstone unless ephemeral |
| Permanent deletion | Intentionally make recovery unavailable | explicit high-consequence authority and deletion scope required |
| Scope expansion | Share memory with broader actor or tenant scope | explicit authority appropriate to target scope |
| Policy mutation | Change governance rules | require human approval |

## Authority outcomes

PAMA should return one of these outcomes:

```text
allow
allow_with_ledger
require_review
require_external_verification
block
```

Implementations may add outcomes such as `abstain`, `quarantine`, or `collect_more_evidence` when useful, but every outcome must have defined consequence semantics.

## Authority resolution invariant

For a fixed set of committed inputs, current state, and policy version, PAMA must produce a **deterministic or formally bounded authority envelope**.

This does not require all upstream inputs to be deterministic.

It requires that:

1. the policy knows which inputs are estimates
2. their provenance and uncertainty are inspectable
3. the estimator cannot grant itself authority
4. prohibited actions remain prohibited regardless of confidence
5. any stochastic behavior after authorization selects only among already-permitted actions
6. the resulting authority decision can be reconstructed from its receipt

## Risk classes

| Risk | Examples | Required handling |
|---|---|---|
| Low | temporary context, low-impact links, ephemeral cache decay | allow with normal ledger |
| Medium | task memory, project notes, reusable summaries | allow with evidence and reversible correction |
| High | user preferences, security policy, durable decisions, code mutation plans | require review or certification |
| Critical | identity, credentials, compliance, permanent deletion, cross-tenant scope expansion, safety boundaries | require explicit human or equivalently authoritative approval |

## Consequence proportionality

Governance strength should rise with consequence, not merely with estimator confidence.

Relevant dimensions include:

```text
reversibility
persistence horizon
sensitivity
scope / tenancy
blast radius
canonicality
authority level
dependency fan-out
ability to destroy evidence
ability to alter future governance
```

A low-confidence, reversible cache decision may still be acceptable.

A high-confidence proposal for permanent deletion may still require explicit review.

## PAMA evaluation inputs

```text
memory_state
mutation_type
risk_class
actor
source_authority
evidence_quality
saturation
confidence
contradiction_pressure
reversibility
blast_radius
certification_status
user_approval_state
policy_scope
estimator_refs
estimator_versions
calibration_refs
uncertainty_summary
estimator_disagreement
out_of_distribution_signal
requested_scope_change
```

PAMA should distinguish required inputs from optional advisory signals. Missing advisory signals may reduce decision quality. Missing required authority inputs must not be silently guessed for consequential actions.

## Promotion rule

Promotion requires more than saturation.

```text
can_promote =
  identity_resolved
  and provenance_present
  and saturation >= candidate_threshold
  and trap_class_check == pass
  and pama_outcome in [allow, allow_with_ledger, require_review]
```

This is a simplified gate, not a claim that a point threshold is sufficient.

If PAMA returns `require_review`, the memory may enter Pending Verification but must not crystallize.

If estimator uncertainty, disagreement, drift, or scope invalidates the confidence of a consequential promotion proposal, PAMA may return:

```text
require_review
require_external_verification
block
```

rather than inferring permission from the score.

## Crystallization rule

```text
can_crystallize =
  can_promote
  and certification_status == pass
  and pama_outcome in [allow, allow_with_ledger]
  and scope_defined
  and dispute_status == clear
```

Crystallization should bind to the evidence set, policy version, estimator context, authority record, and scope under which it was approved.

## Bounded stochastic action

PAMA does not require every downstream choice to be deterministic.

If governance produces a permitted set such as:

```text
permitted_actions = [
  store_ephemeral,
  request_more_evidence,
  defer
]
```

a planner may choose deterministically or stochastically among those actions if policy allows.

It may not sample from:

```text
[
  store_ephemeral,
  request_more_evidence,
  defer,
  crystallize_without_certification
]
```

and then claim the unsafe action was merely a probabilistic outcome.

Randomness does not create permission.

## Anti-patterns

### Repetition as authority

Wrong:

```text
many accesses -> crystallized
```

Correct:

```text
many meaningful accesses -> possible saturation increase -> candidate -> certification -> governed crystallization
```

### Confidence as authority

Wrong:

```text
model says it confidently -> durable memory
```

Correct:

```text
model confidence -> evidence signal -> calibrated scoring -> governance -> verification path
```

### Summary as authority

Wrong:

```text
summary says X -> source can be discarded
```

Correct:

```text
summary says X -> source refs retained -> provenance survives compression
```

### Determinism as correctness

Wrong:

```text
fixed threshold produced same answer twice -> safe decision
```

Correct:

```text
reproducible decision + calibrated inputs + valid policy + appropriate consequence controls -> auditable governed decision
```

### Probabilistic utility as deletion authority

Wrong:

```text
predicted_future_utility < 0.05 -> permanently delete
```

Correct:

```text
low predicted utility -> deletion candidate -> retention/dependency/privacy policy -> authorized deletion mode
```

## Adaptive authority

PAMA is proportional and adaptive.

Authority may increase when:

- memory is low risk
- mutation is reversible
- evidence is strong
- policy scope is narrow
- prior similar mutations succeeded
- user has delegated authority explicitly
- estimator calibration is valid for the current scope

Authority must decrease or escalate when:

- contradiction pressure rises
- source authority weakens
- trap-class behavior appears
- mutation blast radius grows
- certification is missing or expired
- system confidence exceeds evidence quality
- estimator disagreement is material
- estimator calibration is stale or out of scope
- a requested mutation expands sharing or tenancy scope
- the action destroys rollback, evidence, or future governance options

## Uncertainty handling

PAMA should distinguish at least:

```text
epistemic uncertainty: uncertainty about the content or model
aleatoric uncertainty: irreducible variability/noise where relevant
policy uncertainty: policy is missing, ambiguous, conflicting, or version-misaligned
authority uncertainty: actor permission cannot be reconstructed
scope uncertainty: target user, tenant, or domain is unclear
```

Not all uncertainty should be handled the same way.

For example:

- low-risk epistemic uncertainty may still permit an ephemeral write
- policy uncertainty on a high-impact mutation should block or escalate
- authority uncertainty must never be resolved by estimator confidence
- scope uncertainty should prevent broad sharing until resolved

## Fail-safe behavior

For high or critical consequence actions, PAMA should fail closed or escalate when required governance state cannot be reconstructed.

Examples:

```text
policy version missing -> block / require review
actor authority unresolved -> block
scope ambiguous for cross-tenant sharing -> block
certification reference invalid -> block crystallization
estimator outside calibration scope -> require verification for consequential promotion
```

Low-risk, reversible operations may use explicitly defined degraded modes if policy permits them.

## Audit requirements

Every mutation decision should record:

```text
mutation_id
memory_id
actor
requested_mutation
pama_inputs
estimator_refs
estimator_versions
calibration_refs
uncertainty_summary
pama_outcome
permitted_action_set
selected_action
selection_mode
policy_refs
policy_version
evidence_refs
approval_refs
before_state
after_state
rollback_path
timestamp
```

`selection_mode` should identify whether a permitted downstream choice was deterministic, stochastic, human-selected, or externally determined.

## Replay requirement

A decision receipt should allow an auditor to answer:

1. What did the uncertain components estimate?
2. Which estimator and calibration versions produced those estimates?
3. Which policy version interpreted them?
4. What actions were prohibited?
5. What actions were permitted?
6. Which permitted action was selected and how?
7. What state changed?
8. Could the change be rolled back?

Exact replay of a stochastic estimator is not always possible or necessary. Exact reconstruction of **authority and consequence** is required.

## Runtime enforcement

PAMA should be enforced at the boundary where the system changes memory, not merely where it explains memory.

Good enforcement points:

- Vault write boundary
- crystallization gate
- graph mutation API
- agent action planner
- code governance layer
- correction workflow
- pruning workflow
- deletion workflow
- scope-sharing boundary

## Required adversarial cases

PAMA conformance should eventually include:

- high-confidence false memory requesting durable promotion
- threshold jitter near promotion boundary
- estimator disagreement about sensitivity
- high semantic relevance from the wrong tenant
- stochastic planner offered both permitted and prohibited actions
- permanent deletion proposed from uncertain future utility
- policy-version drift after a prior authorization
- missing authority record during replay
- concurrent conflicting mutation requests
- unsafe multi-memory composition that was not visible at individual write time

## Doctrine

PAMA is not a memory score.

PAMA is the authority layer that decides whether a proposed memory transition is allowed.

Probability may inform PAMA. Probability does not become PAMA.
