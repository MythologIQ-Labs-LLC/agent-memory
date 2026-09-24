# Agent Manifest External Evidence Profile

Status: reference interoperability profile for #223 and version-exact requalification #440. Agent Manifest remains an optional peer, not a canonical Agent Memory dependency.

## Exact peer pin

```text
repository: agentrust-io/agent-manifest
package: agent-manifest==0.12.0
release/tag: python-v0.12.0
tag object: ed11fef5d02c7d8a6d57b24c7b92509342522445
source commit: 9478b56cc349bef01441db4e17e61849c8d69d6f
manifest envelope: v0.2 COSE
```

This profile is intentionally pinned. A later Agent Manifest release is unsupported evidence until its changed semantics are reviewed and the source tuple is updated deliberately.

## 0.12.0 security/semantic qualification

The 0.12.0 release materially tightens the verifier boundary consumed by Agent Memory. The requalification records these changes rather than treating the dependency update as package maintenance:

- `attestation_verified` requires independent hardware appraisal evidence; an enforced attestation without that appraisal fails closed as `ATTESTATION_UNAVAILABLE`;
- `audit_key_sealed` is enforced when attestation is required;
- timestamp and memory-baseline TTL parsing fail closed rather than skipping validity checks;
- HITL `approval_method` is signature-bound;
- TPM AK-chain appraisal uses the shared certificate-chain verifier;
- nested omissions cannot bypass the full-binding requirement;
- certificate-chain path-length constraints are enforced.

The executable comparator proves the first boundary directly and keeps hardware attestation separate from signed identity/configuration evidence.

### Exact 0.12.0 memory-delta limitation

The released 0.12.0 `verify_delta()` accepts an `ops` argument but does not bind the supplied appended operation bytes to the checkpoint advance. A later upstream revision adds that binding, but it is not part of this exact release.

Agent Memory therefore preserves this boundary explicitly:

```text
accepted Agent Manifest 0.12.0 checkpoint delta
!= proof of which operation was appended
```

The #440 qualification gate executes a mismatched-operation case and records that 0.12.0 still accepts the checkpoint. Agent Memory action semantics remain in separately signed Agent Memory evidence and are never inferred from that checkpoint verdict.

## Responsibility boundary

Agent Manifest can provide cryptographically and structurally useful evidence about a declared agent identity and bound deployment artifacts.

Agent Memory retains authority over memory semantics:

```text
Agent Manifest
  signed manifest identity
  bound deployment/configuration artifacts
  verifier result
  optional runtime attestation
        |
        v
Agent Memory external-evidence adapter
        |
        +-> identity evidence
        +-> runtime-configuration evidence
        +-> attestation evidence
        |
        v
normal Agent Memory provenance/currentness/scope/PAMA boundaries
```

The separation is deliberate because the peer verifier can prove different facts with different strength.

## Three evidence records

### Identity evidence

A verified COSE signature can establish that the trusted signing key authenticated the manifest carrying the declared agent/manifest identity.

It does not establish:

- authorization for a particular invocation;
- memory mutation authority;
- execution;
- semantic correctness;
- lifecycle satisfaction.

A configuration mismatch therefore does not retroactively erase a correctly verified manifest signature. Identity and configuration remain separate evidence facts.

### Runtime/deployment configuration evidence

The profile records only minimized references needed to describe bindings that the real verifier checked, such as:

```text
system prompt hash
policy bundle hash
tool catalog hash
model identity/version
memory baseline snapshot hash
RAG root where present
decision-trace root where present
supply-chain/container digest where present
```

Raw prompts, policy bodies, tool schemas/descriptions, RAG documents, memory contents, and trace bodies are not required by the normalized record.

A matching tool catalog means the running catalog matched the declared catalog binding. It does **not** authorize parameters or consequences of a particular tool invocation.

A matching `memory_baseline.snapshot_hash` is evidence about a bound snapshot. It does **not** become canonical/current Agent Memory state and does not satisfy Agent Memory correction, recall, deletion, or lifecycle obligations.

### Attestation evidence

Hardware/runtime attestation is represented separately.

```text
manifest signature verified
+
attestation_verified = false
-> identity/configuration may still be applicable
-> hardware attestation remains insufficient evidence
```

The adapter never upgrades software-only manifest validity into a hardware assurance claim. Under 0.12.0, asking the peer verifier to enforce attestation without independent appraisal must fail closed rather than manufacture `attestation_verified` from manifest-local data.

## HITL and delegation

Agent Manifest may carry HITL and delegation structures. This profile does not translate them directly into Agent Memory approval or reusable authority.

Preserve:

```text
manifest HITL record
!= Agent Memory approval record

manifest delegation chain
!= reusable Agent Memory delegated authority
```

The 0.12.0 signature binding for `approval_method` improves the integrity of Agent Manifest HITL evidence. It does not change the authority boundary above.

## Action-authority negative proof

The real comparator uses one fully valid manifest/configuration evidence set as input to two materially different Agent Memory proposals.

```text
low-risk runtime assembly
-> normal low-risk PAMA outcome

critical irreversible cross-scope expansion
-> PAMA block
```

The Agent Manifest verifier sees the same valid manifest in both cases because invocation consequence is outside the manifest verification boundary. Agent Memory therefore cannot treat `VALID` as a shortcut around PAMA.

## Failure/currentness behavior

The comparator exercises at least:

- matching signed COSE manifest;
- enforced attestation without independent appraisal;
- mismatched memory-baseline binding;
- missing trusted key / unverifiable signature;
- tampered COSE envelope;
- expired manifest;
- revoked manifest;
- unsupported manifest version.

The profile keeps these states distinct. In particular, a revoked or expired manifest can retain historical signature evidence while becoming stale for current applicability.

## Evidence minimization

Normalized evidence prefers:

- manifest/verification references;
- exact source/package version;
- signer/verifier identity;
- COSE digest;
- artifact digests/versions;
- currentness/revocation posture;
- explicit limitations.

It does not persist raw bound artifacts merely because the peer manifest can describe them.

## Non-claims

A passing comparator establishes only the bounded interoperability behavior at the tested Agent Memory and Agent Manifest versions.

It does not establish:

- Agent Manifest production deployment;
- hardware attestation where no independent appraisal was verified;
- universal Agent Manifest conformance;
- action authorization through Agent Manifest;
- execution enforcement;
- canonical Agent Memory identity;
- canonical memory-baseline truth;
- appended-operation identity from a 0.12.0 checkpoint verdict;
- reusable delegation or HITL authority;
- certification.

## References

- #165 attestation/identity/trust interoperability research
- #175 implementation-readiness sequencing
- #223 Agent Manifest implementation
- #440 version-exact dependency-pair qualification
- ADR-021 portable governance evidence
- `schemas/external-evidence-normalized.schema.json`
- `reference/agentmem_ref/memory/external_evidence.py`
- `reference/agentmem_ref/memory/agent_manifest_external_evidence.py`
- `reference/run_dependency_pair_qualification.py`
