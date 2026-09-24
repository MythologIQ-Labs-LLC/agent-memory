# P4.5c TRACE-compatible external action evidence

Status: **Executable interoperability evidence**, re-qualified under #440 for TRACE 0.10.0. This slice maps P4.5a portable Agent Memory governance evidence into the existing AgenTrust external action-evidence surface without making TRACE or cMCP responsible for PAMA, isolation-domain membership, or memory lifecycle semantics.

Parent implementation issue: #63. Dependency-pair qualification: #440.

## Pinned external surfaces

The executable/reference surfaces are pinned to:

```text
TRACE SDK:        agentrust-trace==0.10.0
TRACE tag:        v0.10.0
TRACE tag object: d7a9310395e135e2b5ca52b09fc79e74af6c1ce2
TRACE source:     3a561d84d752794b9afa994ce16ed35c24ac0acb
Agent Manifest:   agent-manifest==0.12.0
cMCP runtime:     cmcp-runtime==0.4.0
cMCP release:     a2e95151356c9ae6c545330c900f3d4af0e447c1
RFC 8785 library: rfc8785==0.1.4
```

Relevant upstream contracts:

- [TRACE verification guidance](https://github.com/agentrust-io/trace-spec/blob/3a561d84d752794b9afa994ce16ed35c24ac0acb/docs/verification.md)
- [TRACE 0.10.0 changelog](https://github.com/agentrust-io/trace-spec/blob/3a561d84d752794b9afa994ce16ed35c24ac0acb/CHANGELOG.md)
- [TRACE external execution evidence guidance](https://github.com/agentrust-io/trace-spec/issues/34)
- [cMCP external execution evidence schema](https://github.com/agentrust-io/cmcp/blob/a2e95151356c9ae6c545330c900f3d4af0e447c1/schemas/audit-entry.schema.json)
- [cMCP released verifier implementation](https://github.com/agentrust-io/cmcp/blob/a2e95151356c9ae6c545330c900f3d4af0e447c1/src/cmcp_verify/verify.py)

The released packages are comparators and interoperability dependencies for this reference slice. They do not become Agent Memory doctrine.

## TRACE 0.10.0 qualification

The version bump is not treated as clerical maintenance. The exact release materially changes verification semantics relevant to evidence interpretation:

- schema verification now rejects private `cnf.jwk` material;
- `verify_record()` returns explicit revocation-check state and can consume the section 3.2.3 revocation bundle;
- action-receipt chains distinguish a signed disclosed gap from silent absence;
- canonicalization/delegation coverage includes a supplementary-plane-key vector that distinguishes RFC 8785 ordering from code-point sorting;
- schema/model validation and URI handling fail closed in several previously divergent cases.

The non-skippable #440 gate executes two target-specific facts directly: a signed record with private `cnf.jwk.d` is rejected by the schema path, and `verify_record()` returns explicit revocation state.

TRACE 0.10.0's `receipt_gap_disclosed` is an upstream receipt-chain semantic. The current Agent Memory P4.5c bundle is a bounded cMCP `external_execution_evidence` integration rather than an implementation of the full TRACE receipt-chain profile, so Agent Memory does not fabricate a local gap-disclosure state merely to mirror the upstream vocabulary.

## Ownership boundary

The evidence chain is:

```text
Agent Memory canonical receipt
        |
        | P4.5a content-free signed projection
        v
portable Agent Memory governance evidence
        |
        | content-addressed reference + action_ref
        v
P4.5c detached action payload
        |
        | evidence_hash
        v
cMCP external_execution_evidence envelope
        |
        | linked_call_id + issuer signature
        v
TRACE/cMCP action-evidence verification
```

The meanings remain separate:

```text
TRACE/cMCP receipt integrity != PAMA permission
TRACE/cMCP receipt integrity != isolation-domain membership
external accepted outcome    != lifecycle satisfaction
external rejected outcome    != malformed evidence
valid action evidence         != physical completion
TRACE revocation state        != Agent Memory lifecycle authority
```

Agent Memory remains authoritative for memory-action meaning, PAMA, canonical receipt semantics, isolation-domain meaning and membership continuity, correction/deletion obligations, residue, and lifecycle satisfaction.

## Existing envelope, no new TRACE wire format

P4.5c uses the existing six-field cMCP `external_execution_evidence` envelope exactly:

```json
{
  "issuer": "spiffe://runtime.example/agent-memory-controller",
  "issuer_key_id": "<sha256 raw Ed25519 public key hex>",
  "signature": "<base64url Ed25519 signature>",
  "evidence_hash": "sha256:<detached payload hash>",
  "evidence_type": "opaque-receipt",
  "linked_call_id": "<audit call_id>"
}
```

`opaque-receipt` is deliberate. Agent Memory evidence is not itself a controller-native receipt, a TEE attestation, or a JWT. Reusing an existing generic envelope value is more accurate than proposing a new normative TRACE evidence type before implementation exposes a generic need.

`linked_call_id` remains the audit-chain identifier. It is not overloaded with Agent Memory `action_ref`.

## Detached payload

Schema: `../../../schemas/trace-action-evidence-bundle.schema.json`.

The detached payload is content-free:

```json
{
  "profile": "agent-memory.trace-action-evidence.v1",
  "call_id": "<audit call_id>",
  "action_ref": "<signed Agent Memory runtime action reference>",
  "portable_evidence_ref": "sha256:<P4.5a evidence reference>",
  "canonical_receipt_ref": "sha256:<Agent Memory receipt reference>",
  "execution_outcome": "accepted | rejected",
  "execution_time": "2026-08-11T21:00:03Z",
  "source_domain_ref": "<optional opaque reference>",
  "destination_domain_ref": "<optional opaque reference>",
  "domain_authorization_state_ref": "<optional opaque membership/authorization-state reference>"
}
```

It intentionally excludes raw memory content, hidden reasoning, full canonical receipts, PAMA policy contents, tenant/project/domain display names when opaque references suffice, and any claim that TRACE understands Agent Memory authority or lifecycle semantics.

## Two canonicalization domains

The upstream contracts currently use two serialization rules, and P4.5c preserves both.

The detached payload uses **RFC 8785/JCS**:

```text
evidence_hash = sha256(JCS(detached_payload))
```

The cMCP released verifier signs the six-field envelope using compact, key-sorted JSON with `ensure_ascii=True`, excluding only `signature` from the signing input.

P4.5c reproduces that verifier behavior exactly for the envelope. It does not silently substitute JCS and claim wire compatibility where the released verifier has a different pre-image.

TRACE 0.10.0's expanded canonicalization vectors strengthen the upstream JCS boundary; they do not change cMCP 0.4.0's released envelope serialization contract.

## Replay and binding model

P4.5c deliberately checks both identifiers:

```text
linked_call_id -> audit-chain call identity
action_ref     -> Agent Memory runtime action identity
```

A receipt replayed onto another call fails `linked_call_id` binding. A receipt correlated to the wrong Agent Memory action fails `action_ref` binding even if the call identifier is unchanged.

The verifier also binds detached payload hash, portable evidence reference, canonical receipt reference, optional opaque domain references, optional domain-authorization-state reference, and external execution time. No external receipt is allowed to manufacture execution-time PAMA authority or isolation-domain membership.

## Domain-authorization non-escalation

A valid TRACE/cMCP receipt proves the configured action-evidence binding. It does not prove that the Agent Memory actor still held permission to cross a memory-domain boundary at execution time.

For a signed cross-domain consequence, Agent Memory independently evaluates:

```text
source_domain_ref
destination_domain_ref
domain_authorization_state_ref
domain_authorization_valid_at_execution
```

The executable paths distinguish authorized, unauthorized, and unverifiable execution-time membership without rewriting historical receipt authenticity.

## Local result taxonomy

The bounded P4.5c adapter reports:

```text
receipt_valid_accepted
receipt_valid_rejected
receipt_missing_required
receipt_invalid
receipt_unverified
```

A valid rejection is first-class negative evidence. It does not make the receipt malformed.

This local taxonomy is not claimed to be the whole TRACE 0.10.0 receipt-chain state machine. In particular, `receipt_gap_disclosed` belongs to the upstream chain profile and would require its own explicit integration before Agent Memory could represent it faithfully.

Unknown issuer trust is reported locally as `receipt_unverified` when every non-cryptographic binding is otherwise sound. The released cMCP comparator is stricter once `external_evidence_keys` verification is enabled: an unknown key fails bundle verification. Both behaviors remain explicit.

## Lifecycle non-escalation

P4.5c executes externally accepted action evidence with both Agent Memory lifecycle `residual` and `satisfied`. Both TRACE bindings remain valid. The lifecycle difference comes from Agent Memory evidence.

It also executes a valid external `rejected` outcome while retaining governance and lifecycle dimensions separately. A downstream negative outcome is evidence, not a signature failure.

## Real upstream comparator

`../../../reference/run_trace_cmcp_comparator.py` runs in a dedicated virtual environment and calls the released `cmcp_verify.verify_audit_bundle()` against the P4.5c envelope.

The comparator proves that cMCP 0.4.0, with TRACE 0.10.0 and Agent Manifest 0.12.0 installed, accepts the correctly signed envelope and rejects wrong-call replay, signature tampering, and missing configured issuer trust.

Comparator isolation remains intentional because the cMCP/AGT dependency line has a different cryptography constraint from the repository's main validation profile.

## Executed local vectors

`../../../reference/tests/test_trace_action_evidence.py` covers exact TRACE/cMCP release identities, accepted and rejected outcomes, lifecycle non-escalation, execution-time authorization changes, call/action replay, detached payload and envelope tampering, unknown issuer trust, missing receipt, isolation/domain-authorization mismatch, schema validation, and content minimization.

The #440 pair gate additionally exercises target-specific TRACE 0.10.0 schema/revocation-result behavior and records zero skipped qualification checks.

Run the local profile:

```bash
python -m pip install -r reference/requirements.txt
PYTHONPATH=reference python reference/run_dependency_pair_qualification.py \
  --agent-memory-commit <exact-40-hex-commit> \
  --output dependency-pair-qualification.json
python -m unittest discover -s reference/tests -t reference
python scripts/validate_schemas.py
```

Run the isolated upstream comparator:

```bash
python -m venv /tmp/agent-memory-p45c-cmcp
/tmp/agent-memory-p45c-cmcp/bin/python -m pip install \
  cmcp-runtime==0.4.0 \
  agentrust-trace==0.10.0 \
  agent-manifest==0.12.0 \
  rfc8785==0.1.4
PYTHONPATH=reference \
  /tmp/agent-memory-p45c-cmcp/bin/python reference/run_trace_cmcp_comparator.py
```

## Upstream contribution surface

The implementation evidence may support an upstream integration contribution through the existing AgenTrust integration surface. P4.5c does **not** justify a normative TRACE schema proposal. A core-spec change should be proposed only if later integration work exposes a generic requirement that cannot be represented without one.

## What this slice proves

P4.5c demonstrates that Agent Memory governance evidence can be bound to an existing TRACE/cMCP action-evidence path, checked for call and action replay, verified by the released cMCP implementation, and interpreted without TRACE implementing PAMA or receiving raw memory.

The evidence remains multi-dimensional rather than collapsed into a trust or health score.

## What remains unproven

This slice does not prove TRACE Trust Record hardware attestation of an Agent Memory process, physical completion, functional-safety certification, production issuer-key/revocation infrastructure, production isolation-domain membership infrastructure, upstream integration acceptance, generic trust-anchor discovery, or any Agent Memory conformance-level increase.
