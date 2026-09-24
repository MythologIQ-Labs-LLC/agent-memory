# P4.5b Agent Manifest memory checkpoint correlation

Status: **Executable interoperability evidence**, re-qualified under #440 for Agent Manifest 0.12.0. This slice correlates Agent Memory portable governance evidence with the Agent Manifest v0.2 memory checkpoint/delta protocol. It does not adopt Agent Manifest as Agent Memory doctrine, does not duplicate its checkpoint protocol, and does not change repository conformance level.

Parent implementation issue: #63. Dependency-pair qualification: #440.

## Pinned external comparator

The executable comparator is pinned to:

```text
repository: https://github.com/agentrust-io/agent-manifest
spec:       Agent Manifest v0.2
package:    agent-manifest==0.12.0
tag:        python-v0.12.0
tag object: ed11fef5d02c7d8a6d57b24c7b92509342522445
source:     9478b56cc349bef01441db4e17e61849c8d69d6f
```

Pinned upstream source surfaces:

- [v0.2 memory checkpoint/delta implementation](https://github.com/agentrust-io/agent-manifest/blob/9478b56cc349bef01441db4e17e61849c8d69d6f/python/src/agent_manifest/_memory_delta.py)
- [v0.2 RFC 9162 Merkle implementation](https://github.com/agentrust-io/agent-manifest/blob/9478b56cc349bef01441db4e17e61849c8d69d6f/python/src/agent_manifest/_merkle.py)
- [v0.2 specification](https://github.com/agentrust-io/agent-manifest/blob/9478b56cc349bef01441db4e17e61849c8d69d6f/spec/agent-manifest-spec-v0.2.md)

The upstream package is a **test comparator**, not an Agent Memory runtime dependency. P4.5b deliberately calls the upstream checkpoint verifier instead of copying its Merkle, sequence, TTL, drift, or delta-budget logic into this repository.

## Ownership boundary

Agent Manifest v0.2 models evolving memory as an append-only operation log. A checkpoint binds:

```text
memory_root
tree_size
seq
approved_at
ttl_seconds
```

Its verifier owns whether a checkpoint advance is a valid append-only delta under its consistency-proof, monotonic-sequence, TTL, and delta-budget rules.

Agent Memory owns:

```text
what the memory action means
whether PAMA permitted it
what canonical receipt records it
whether execution was authorized
whether correction/deletion lifecycle obligations are satisfied
whether declared or undeclared derived residue remains
```

No arrow reverses semantic ownership.

## Exact 0.12.0 operation-binding limitation

The exact `agent-manifest==0.12.0` implementation accepts an `ops` argument to `verify_delta()`, but that release does not bind the supplied operation bytes to the new checkpoint root. The #440 qualification gate executes this rather uncomfortable fact instead of improving it with optimism: the same valid checkpoint/proof remains accepted when a materially different one-element `ops` list is supplied.

A later upstream revision adds representation-aware append binding. That later behavior is not attributed retroactively to 0.12.0.

Therefore:

```text
Agent Manifest 0.12.0 delta accepted
!= supplied appended operation cryptographically bound
!= proof that the appended operation was DEL
```

Agent Memory keeps `memory_action` in separately signed portable governance evidence and never infers it from checkpoint acceptance.

## Correlation contract

Schema: `../../../schemas/agent-manifest-memory-correlation.schema.json`.

The canonical Agent Memory decision receipt already has a generic `evidence_refs` array. P4.5b therefore does not modify the receipt schema. The checkpoint tuple is projected without operation content and content-addressed with Agent Memory canonical JSON:

```text
checkpoint_ref = sha256(canonical({
  memory_root,
  tree_size,
  seq,
  approved_at,
  ttl_seconds
}))
```

That `checkpoint_ref` is placed in the canonical receipt's `evidence_refs`.

P4.5a portable evidence then binds:

```text
canonical_receipt_ref
memory_action
state.before_ref = previous checkpoint_ref
state.after_ref  = new checkpoint_ref
```

P4.5b validates all four relationships:

1. the portable evidence signature resolves to the supplied canonical receipt;
2. canonical receipt `selected_action` equals signed portable `memory_action`;
3. the receipt contains the new checkpoint reference in `evidence_refs`;
4. the portable before/after state references match the previous/new checkpoint references.

The correlation artifact also records the pinned upstream spec/package/commit identity and the **upstream verifier's** `accepted/rejected` verdict and reason.

Checkpoint projection is deliberately strict at the boundary: hash values must use a supported algorithm plus a 64-character lowercase hexadecimal digest, counters must be non-negative integers rather than booleans masquerading as integers, TTL must be positive, and approval time must be timezone-aware.

## What is not duplicated

Agent Memory does not reproduce:

- RFC 9162 consistency proof generation or verification
- Agent Manifest Merkle leaf construction
- Agent Manifest sequence monotonicity rules
- checkpoint TTL evaluation
- delta-budget evaluation
- Agent Manifest drift classification

Those are executed by `agent-manifest==0.12.0` in CI. The local correlation layer only binds the resulting checkpoint identity and verdict to Agent Memory evidence.

## DEL is not forgetting

The P4.5b test constructs an upstream operation log containing an actual key-value `DEL` and executes the upstream checkpoint verifier against the resulting checkpoint/proof.

The portable correlation artifact deliberately does not claim `operation_kind = DEL`. The deletion semantic is carried by signed Agent Memory `memory_action = permanent_deletion`; the fact that the bounded test vector was built from `DEL` remains an executable test fact, not a property inferred from the checkpoint verdict.

P4.5b executes the same upstream-accepted checkpoint advance in two Agent Memory outcomes:

```text
Agent Manifest: accepted checkpoint advance
Test input:     appended DEL
Agent Memory:   committed permanent_deletion
Lifecycle:      residual
```

and:

```text
Agent Manifest: accepted checkpoint advance
Test input:     appended DEL
Agent Memory:   committed permanent_deletion
Lifecycle:      satisfied
```

Both correlation artifacts are valid. The difference is Agent Memory lifecycle evidence, not Agent Manifest checkpoint integrity.

The 0.12.0 qualification also adds a third pressure case:

```text
Same checkpoint/proof
Supplied ops argument: materially different PUT
Agent Manifest 0.12.0: accepted
Agent Memory memory_action: unchanged, separately signed
```

This is why an accepted checkpoint cannot be laundered into operation semantics.

## Negative outcomes remain evidence

A failed Agent Manifest consistency proof produces the upstream `drift` verdict. P4.5b records that as:

```text
correlation_integrity = valid
agent_manifest.delta_verification = rejected
agent_manifest.delta_reason = drift
```

The correlation itself is valid because it correctly binds a negative external result. It does not mutate the negative result into an Agent Memory governance denial.

By contrast, these are correlation-integrity failures:

- the portable evidence does not verify against the canonical receipt;
- canonical receipt `selected_action` disagrees with signed portable `memory_action`;
- the receipt does not reference the new checkpoint;
- portable `before_ref` does not identify the previous checkpoint;
- portable `after_ref` does not identify the new checkpoint.

## Privacy boundary

The correlation artifact contains checkpoint roots and metadata, not operation payloads. The executed deletion vector intentionally uses a memory key and value that are absent from the emitted correlation object.

The upstream verifier receives the operation list because it owns checkpoint verification. Agent Memory does not copy those operations into portable evidence or the correlation artifact.

## Executed vectors

`../../../reference/tests/test_agent_manifest_correlation.py` executes:

- the exact `agent-manifest==0.12.0` package identity;
- the pinned upstream source commit identity;
- the Agent Manifest v0.2 normative KV root vector;
- a valid RFC 9162 checkpoint advance whose test operation log contains `DEL`;
- the exact 0.12.0 mismatched-supplied-operation limitation;
- canonical receipt to checkpoint-reference binding;
- portable before/after state to checkpoint-reference binding;
- canonical receipt action to signed portable memory-action binding;
- accepted checkpoint + signed Agent Memory `permanent_deletion` + lifecycle `residual`;
- accepted checkpoint + signed Agent Memory `permanent_deletion` + lifecycle `satisfied`;
- rejected consistency proof surfaced as Agent Manifest `drift`;
- missing receipt checkpoint reference;
- mismatched receipt/portable action;
- tampered portable after-state binding;
- malformed checkpoint root and timezone-less timestamp rejection;
- schema validation of the content-free correlation artifact;
- absence of the raw deleted key/value from the correlation artifact;
- absence of an unproven `operation_kind` claim from the correlation artifact.

The non-skippable #440 pair gate separately fails if the installed package identity is not exactly 0.12.0.

Run:

```bash
python -m pip install -r reference/requirements.txt
PYTHONPATH=reference python reference/run_dependency_pair_qualification.py \
  --agent-memory-commit <exact-40-hex-commit> \
  --output dependency-pair-qualification.json
python -m unittest discover -s reference/tests -t reference
python scripts/validate_schemas.py
```

## What this slice proves

P4.5b demonstrates that Agent Memory can correlate its canonical receipt and P4.5a portable evidence to Agent Manifest's existing memory checkpoint/delta protocol without duplicating that protocol or delegating memory semantics to it.

It also proves a more useful negative fact for this exact release: checkpoint acceptance is not sufficient evidence of the supplied appended operation identity.

## What remains unproven

This slice does not prove:

- a content-free third-party proof that a 0.12.0 checkpoint's newly appended operation was specifically `DEL`;
- production Agent Manifest trust/attestation deployment;
- hardware attestation of Agent Memory runtime state;
- multi-party checkpoint approval;
- a generic cross-standard checkpoint URI or registry;
- production key/trust-anchor distribution;
- any Agent Memory conformance level increase.

Those remain separate evidence gates.
