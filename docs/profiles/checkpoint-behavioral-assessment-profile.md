# Checkpoint Behavioral Assessment Profile

**Status:** current first-party conformance harness profile  
**Profile ID:** `agent-memory/checkpoint-behavior-conformance`  
**Profile version:** `1.0.0`  
**Implementation:** `reference/agentmem_ref/harness/checkpoint_behavior_harness.py`

## Purpose

This profile evaluates whether a checkpoint transition preserves four retrieval behaviors that Agent Memory treats as important evidence about memory correctness:

1. **correction precedence**: a corrected/current memory must not be missing or outranked by its superseded predecessor;
2. **anchor preservation**: declared stable anchors must remain retrievable without unacceptable rank collapse;
3. **scope isolation at a declared recall stage**: forbidden logical refs or scope refs must not appear at the stage being assessed;
4. **state-conditioned differentiation**: retrieval must remain sensitive to meaningful state changes rather than collapsing distinct checkpoint states into the same observed result.

These probes were originally explored on historical branch `implementation/332-checkpoint-behavioral-assessment`. The current implementation deliberately does **not** resurrect that branch's standalone August API. The useful concepts are represented as an evidence-only harness in the current layered package architecture.

## Authority boundary

Checkpoint behavioral evidence is not authority.

Every assessment and requirement evaluation is fixed at:

```text
authority_effect = none
```

A verified assessment may support conformance, qualification, review, or release evidence. It does not grant:

- PAMA permission;
- durable mutation authority;
- recall admission;
- certification;
- deployment or release authority;
- provider trust;
- scope-crossing permission.

A caller that needs one of those consequences must still satisfy the owning governance contract.

## Evidence binding

The harness binds evidence to:

- exact baseline checkpoint reference and state digest;
- exact candidate checkpoint reference and state digest;
- observer identity/version/configuration digest;
- declared recall stage (`candidate`, `admitted`, or `context_surfaced`);
- explicit tie-policy reference;
- probe contract digest.

State digests are checked both before and after observation collection. If either checkpoint changes during assessment, the harness raises `CheckpointStateChanged` instead of binding evidence across a TOCTOU window.

Tie policy and recall stage participate in observer applicability. Evidence gathered at candidate generation does not silently become evidence about admitted or surfaced context.

## Result semantics

Each probe resolves to one of:

- `verified`: the exercised observation satisfies the declared invariant;
- `contradicted`: exercised evidence demonstrates a violation;
- `inconclusive`: the required observation was unavailable or the baseline itself was insufficient to establish the property.

Unavailable evidence is not treated as contradiction, and absence of contradiction is not generalized into a stronger guarantee than the exact probe supports.

The aggregate result is conservative:

```text
any contradiction -> contradicted
else any inconclusive -> inconclusive
else -> verified
```

## Content minimization

Machine-readable evidence stores checkpoint/contract bindings, reason codes, and observation digests rather than raw query text or retrieved memory content. The harness therefore preserves enough evidence for reproducibility/applicability without turning conformance output into a second memory store.

## Conflicting and historical evidence

`evaluate_requirement(...)` only considers assessments whose checkpoint bindings, contract digest, and observer binding digest exactly match the requirement.

For applicable evidence:

- any contradiction dominates a verified assessment;
- inconclusive-only evidence does not satisfy a requirement;
- verified evidence satisfies the evidence requirement only for that exact binding;
- an old contradiction against a different remediated candidate checkpoint remains historical evidence but does not automatically poison the new checkpoint.

This preserves failed evidence without laundering it into unrelated current-state decisions.

## Scope of the profile

This profile proves only the four declared behavioral properties at the declared observation stage and exact checkpoint/configuration bindings. It does not prove:

- complete memory quality;
- semantic answer correctness;
- global deletion completeness;
- production substrate durability;
- privacy/security beyond the declared scope-isolation observation;
- model calibration;
- provider qualification;
- RC release readiness by itself.

## Historical branch disposition

The useful behavior from `implementation/332-checkpoint-behavioral-assessment` has been re-expressed in the current harness layer. The historical branch's standalone implementation shape is superseded and should not be merged wholesale.

Once the harness/tests/profile land on `main`, the historical branch is deletion-eligible because it no longer contains unexplained unique capability.
