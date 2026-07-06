# Governance and PAMA

## Purpose

PAMA defines mutation authority for agentic memory systems.

The central question is not whether an agent can change memory. The central question is whether it is allowed to change memory, under what scope, with what evidence, and with what rollback path.

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

## Risk classes

| Risk | Examples | Required handling |
|---|---|---|
| Low | temporary context, low-impact links, ephemeral cache decay | allow with normal ledger |
| Medium | task memory, project notes, reusable summaries | allow with evidence and reversible correction |
| High | user preferences, security policy, durable decisions, code mutation plans | require review or certification |
| Critical | identity, credentials, compliance, permanent deletion, safety boundaries | require explicit human approval |

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
```

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

If PAMA returns `require_review`, the memory may enter Pending Verification but must not crystallize.

## Crystallization rule

```text
can_crystallize =
  can_promote
  and certification_status == pass
  and pama_outcome in [allow, allow_with_ledger]
  and scope_defined
  and dispute_status == clear
```

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
model confidence -> evidence signal -> calibrated scoring -> verification path
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

## Adaptive authority

PAMA is proportional and adaptive.

Authority may increase when:

- memory is low risk
- mutation is reversible
- evidence is strong
- policy scope is narrow
- prior similar mutations succeeded
- user has delegated authority explicitly

Authority must decrease when:

- contradiction pressure rises
- source authority weakens
- trap-class behavior appears
- mutation blast radius grows
- certification is missing or expired
- system confidence exceeds evidence quality

## Audit requirements

Every mutation decision should record:

```text
mutation_id
memory_id
actor
requested_mutation
pama_inputs
pama_outcome
policy_refs
evidence_refs
approval_refs
before_state
after_state
rollback_path
timestamp
```

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

## Doctrine

PAMA is not a memory score.

PAMA is the authority layer that decides whether a proposed memory transition is allowed.
