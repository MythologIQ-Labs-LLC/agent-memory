# cMCP External Evidence Profile

## Purpose

This profile defines Agent Memory's inbound evidence relationship with cMCP while preserving exact-version provenance and historical evidence.

Two cMCP boundaries are intentionally retained:

- `v0.4.0` is the historical qualified boundary already used by existing comparator evidence;
- `v0.5.0` is the current requalified boundary under issue #485 / PR #486.

The repository also exercises the opposite direction through the released TRACE/cMCP audit-bundle comparator:

```text
Agent Memory portable governance evidence
-> TRACE action evidence
-> released cMCP verifier
```

The inbound path is:

```text
released cMCP GatewayClaim + verifier result
-> cMCP-specific adapter
-> Agent Memory generic external-evidence normalization
```

cMCP remains an optional independent peer. It does not become a required Agent Memory runtime, memory owner, policy store, or PAMA authority.

## Exact qualified peers

### Historical qualified boundary

```text
repository: agentrust-io/cmcp
release: v0.4.0
source commit: a2e95151356c9ae6c545330c900f3d4af0e447c1
runtime package: cmcp-runtime==0.4.0
TRACE package: agentrust-trace==0.10.0
Agent Manifest package: agent-manifest==0.12.0
```

Historical evidence produced against this boundary remains labeled as `0.4.0`. It is not rewritten as though it came from the newer release.

### Current qualified boundary

```text
repository: agentrust-io/cmcp
release: v0.5.0
source commit: d03b9af504535d3d43f192bc6d9eff89b8afd12f
runtime package: cmcp-runtime==0.5.0
TRACE package: agentrust-trace==0.10.0
Agent Manifest package: agent-manifest==0.12.0
verifier: cmcp-verify==0.5.0
```

Issue #485 and PR #486 execute this exact environment in CI. The qualification run installs the exact released packages, executes `cmcp_verify.verify_trace_claim`, normalizes the resulting field-level evidence, and preserves the authority boundary described below.

The exact-head cMCP workflow for the qualified PR head completed successfully after exercising both the historical 0.4 comparator and the 0.5 security-semantic qualification side by side.

## Why v0.5.0 required explicit requalification

The release changed evidence-relevant behavior rather than merely package metadata. Qualification therefore exercises the semantics Agent Memory can safely consume instead of assuming forward compatibility.

The bounded 0.5 qualification covers:

- regulated compliance-domain crossing data in the signed peer claim;
- RFC 8785 policy-bundle canonical hashing;
- `cert-pinned` catalog rotation mode being expressible;
- built-in regulated compliance domains;
- undeclared custom compliance domains failing closed;
- explicitly declared custom compliance-domain extension;
- software-only attestation remaining non-hardware;
- wrong approved policy hash invalidating enforcement evidence;
- exact source/version/verifier identity in normalized evidence.

The release repository is MIT-licensed at the inspected `v0.5.0` source commit. That rights fact permits reuse under the MIT terms where needed, but the current Agent Memory implementation remains an independently owned normalization boundary rather than importing cMCP as a runtime owner.

## One peer claim, multiple evidence records

A cMCP GatewayClaim can contain several different evidence responsibilities. Agent Memory deliberately refuses to collapse them into one trust boolean.

```text
signed gateway/session claim
+ approved policy bundle binding
+ audit-chain structure
+ enforcement mode
+ runtime measurement / attestation posture
+ optional agent identity
```

The adapter emits at least two independent Agent Memory candidates.

### Enforcement / configuration evidence

The enforcement record preserves bounded facts such as:

- gateway/session subject;
- exact cMCP source, package, release, and verifier identity;
- signed-claim digest;
- policy-bundle ref/hash;
- tool-catalog configuration ref;
- audit-chain root/tip refs;
- `enforce`, `advisory`, or `silent` posture;
- runtime ref;
- freshness;
- optional Agent Manifest ref.

A claim may establish this integrity/configuration posture when the released verifier checks the relevant fields even if hardware attestation remains unverified.

### Runtime attestation evidence

The attestation record separately preserves:

- runtime platform;
- runtime measurement ref;
- attestation verification posture;
- generated-at and validity window;
- hardware-verified versus software-only/unverified state;
- the same source-claim digest and bounded evidence refs.

A software-only claim therefore remains explicitly non-hardware-backed. It cannot inherit the verification status of the policy or audit fields merely because they occur in the same signed envelope.

## Claim-scoped verification

cMCP's verifier exposes a global status plus `verified_fields`, `unverified_fields`, and a failure reason.

Agent Memory consumes field-level evidence rather than copying the global label blindly.

For enforcement/configuration evidence, the adapter requires:

```text
schema
signature
policy_bundle.hash
tool_catalog.hash
audit_chain
+
(public_key_binding OR externally trusted_public_key)
```

Security-critical failures such as signature, signer binding, policy/catalog hash, audit-chain, claim-shape, or requested Agent Manifest binding failure make the enforcement evidence invalid.

Hardware-attestation failure is evaluated separately when the enforcement signer/configuration evidence remains independently bound.

For attestation evidence:

```text
hardware_attestation in verified_fields -> verified
software-only / absent hardware proof    -> unknown
hardware/key-binding verification failure -> failed
```

Freshness is evaluated independently by the generic Agent Memory normalizer.

## Source registration and historical immutability

The generic external-evidence normalizer recognizes both exact cMCP source tuples:

```text
(cMCP, cmcp-runtime==0.4.0, a2e95151356c9ae6c545330c900f3d4af0e447c1)
(cMCP, cmcp-runtime==0.5.0, d03b9af504535d3d43f192bc6d9eff89b8afd12f)
```

This is additive. The default adapter constants remain pinned to the historical 0.4 boundary so existing evidence cannot be silently relabeled. New 0.5 qualification evidence uses explicit source rebinding to the exact 0.5 tuple and verifier identity.

Unsupported future versions continue to normalize as `unsupported` until they receive their own executable qualification.

## Core boundaries

```text
configured policy != enforcing posture
enforcing posture != action execution
audit-chain integrity != lifecycle satisfaction
hardware attestation != semantic correctness
verified gateway identity != Agent Memory authority
policy allow != approval
software-only verification != hardware provenance
signed compliance-domain data != memory access authority
```

These remain true even when every cryptographic check available to the peer passes.

## Privacy and minimization

Normalized records use refs and digests rather than copying cMCP's rich payloads.

The adapter does not retain:

- raw tool arguments or responses;
- tool transcript entries;
- prompts or Agent Memory content;
- raw TEE/TPM evidence;
- quote signatures;
- certificate chains;
- complete Agent Manifest payloads;
- regulated-domain detail merely because it appears in the signed peer envelope.

The full cMCP claim may be held by the external evidence custodian while Agent Memory records the stable digest and bounded provenance needed to reconstruct where the evidence came from.

## Failure semantics

### Software-only

A real released software-only cMCP claim may verify its schema, signature, pinned signer, policy/catalog hashes, freshness, and audit-chain structure while the global result remains `partially_verified` because hardware attestation is absent.

Agent Memory therefore permits:

```text
enforcement/configuration evidence = verified
attestation evidence = unknown
```

when those exact field-level conditions hold.

### Policy/catalog/signature mismatch

A failed signed-policy/configuration binding invalidates the enforcement evidence. It is not softened merely because another field in the same peer claim verified.

### Stale attestation

Expired attestation evidence remains historical evidence but is not current hardware applicability. Its expiry does not retroactively expire an independently current signed configuration/enforcement record.

### Hardware evidence supplied but invalid

Hardware-attestation failure remains failed evidence. It must not degrade to a successful hardware claim.

## Relationship to execution evidence

cMCP may operate in an enforcing mode, but a GatewayClaim's declared enforcement posture is not itself an Agent Memory execution witness.

```text
enforcement_mode = enforce
!=
this specific Agent Memory action executed or was prevented
```

Execution claims continue to require the separate execution/evidence contracts already defined by Agent Memory.

## Executable evidence

The dedicated workflow runs both boundaries in isolated environments:

```text
historical comparator:
  cmcp-runtime==0.4.0
  agentrust-trace==0.10.0
  agent-manifest==0.12.0

current qualification:
  cmcp-runtime==0.5.0
  agentrust-trace==0.10.0
  agent-manifest==0.12.0
```

Relevant implementation surfaces:

```text
reference/agentmem_ref/memory/cmcp_external_evidence.py
reference/tests/test_cmcp_external_evidence.py
reference/run_cmcp_external_evidence_comparator.py
reference/run_cmcp_050_qualification.py
.github/workflows/cmcp-external-evidence.yml
```

The 0.5 qualification also verifies that the Agent Memory normalizer does not promote cMCP's compliance-domain or cross-boundary detail into Agent Memory access or lifecycle authority.

## Non-goals

- claiming production cMCP deployment;
- provisioning real TPM, SNP, TDX, or other hardware in CI;
- making cMCP a required Agent Memory gateway;
- importing cMCP claim schema as Agent Memory doctrine;
- treating cMCP policy as canonical Agent Memory policy;
- treating an Agent Manifest binding as PAMA authority;
- storing raw audit, tool, identity, compliance, or attestation payloads;
- claiming compatibility with future cMCP versions without another exact qualification.
