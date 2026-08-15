# DashClaw External-Verdict Provider Evidence

Status: **implementation evidence / #279 provider-side slice**

This document records the executable Agent Memory side of DashClaw's external-verdict v1 interoperability contract. It does not claim the final live cross-repository integration is complete.

## Evidence boundary

DashClaw contract:

```text
release: v5.24.0
commit:  2d8d59327096831dbe2e11daf147ca80afcba39d
wire:    external-verdict v1
```

The focused workflow fetches that exact source revision, verifies the exact tag, and preserves the upstream implementer guide with the Agent Memory workload evidence.

DashClaw v5.24.0 also resolves the domain-applicability question raised during #279. A configured provider can be scoped by exact `action_type` through DashClaw's host-side `EXTERNAL_VERDICT_ACTION_TYPES` setting. For this integration the intended scope is:

```text
agent_memory.mutation
```

Out-of-scope actions are not sent to Agent Memory. DashClaw records them as `not_applicable` locally rather than manufacturing an external `allow`. Its built-in `dashclaw.connection_test` intentionally bypasses that scope so the wire itself remains testable.

## Runtime shape

```text
DashClaw Decide
  |
  | external-verdict v1 request
  v
Agent Memory DashClaw adapter
  |
  +-- validate wire + exact memory-content binding
  +-- reconstruct trusted actor/tenant boundaries
  +-- evaluate existing PAMA policy
  |
  v
allow | escalate | deny
  |
  +-- decision projection only

later permitted/approved mutation
  |
  +-- exact approval/input binding where review is required
  +-- independent PAMA re-evaluation
  +-- current-state / stale-state check
  v
GovernedMemoryAdapter.commit_proposal
  |
  v
mutation + canonical receipt or refusal
```

The load-bearing separation is:

```text
DashClaw verdict != Agent Memory execution
DashClaw approval != standing Agent Memory authority
DashClaw input_identity != Agent Memory proposal digest
provider decision evidence != commit receipt
```

## Provider request and identity rules

The adapter accepts DashClaw's frozen v1 request fields:

```text
request_id
org_id
agent_id
action_type
declared_goal
act
input_identity
```

`input_identity` is owned by DashClaw and echoed byte-for-byte. Agent Memory does not attempt to reproduce DashClaw's canonicalization algorithm.

The mutation payload uses:

```text
act.kind = agent_memory.mutation
act.memory_value = exact retained value
act.proposal = bounded PAMA proposal inputs
```

The exact memory value is bound by:

```text
proposal.content_sha256 = sha256(memory_value)
```

A content mismatch is denied before PAMA evaluation, so a verdict for one value cannot be reused for another.

## Trusted binding boundary

DashClaw's top-level fields provide the trusted integration bindings:

```text
org_id   -> Agent Memory tenant/org binding
agent_id -> proposing actor binding
```

The nested `act.proposal` is not allowed to inject replacements for:

```text
actor_id
tenant_ref
approval_refs
review_satisfied
```

The adapter also binds the DashClaw org as `org:<org_id>` in the proposal's isolation domains and refuses a conflicting `org:` domain supplied by the act.

When `project_ref` is present, the current bounded envelope requires it to appear in both the bound and required isolation-domain sets. This keeps the project scope explicit rather than relying on a descriptive string elsewhere in the request.

## PAMA projection

The adapter uses the existing deterministic PAMA evaluator. It does not introduce a second policy language.

```text
PAMA allow                          -> DashClaw allow
PAMA allow_with_ledger              -> DashClaw allow
PAMA require_review                 -> DashClaw escalate
PAMA require_external_verification  -> DashClaw escalate
PAMA block                          -> DashClaw deny
```

No synthetic `warn` state is invented.

Provider evidence records the PAMA outcome/version, proposal/content bindings, and explicitly records:

```text
execution_evidence = false
```

It is bounded under DashClaw's 4096-character provider-evidence ceiling.

## Connection test

`dashclaw.connection_test` is handled explicitly and side-effect free.

A valid synthetic test receives a contract-valid `allow` response with the DashClaw identity echoed. No proposal is committed and no Agent Memory memory/receipt state is created.

A malformed top-level request that lacks the identity required for a valid echo receives a non-2xx HTTP response from the reference server. That is deliberate: fabricating a contract verdict without the required identity would be less honest than allowing DashClaw to apply its configured provider-unavailability posture.

## Approval and commit boundary

A DashClaw `escalate` is only a provider decision. It does not commit a mutation.

When PAMA requires review, the later Agent Memory commit seam requires separate approval evidence:

```text
approval_ref
approval_actor_id
approved_input_identity
```

The commit seam refuses when:

- approval evidence is missing;
- the approved DashClaw `input_identity` does not equal the exact mutation identity;
- the approving actor is the same agent that proposed the mutation.

After those checks, the proposal is passed through `GovernedMemoryAdapter.commit_proposal`, which independently re-evaluates PAMA and current state. A valid approval therefore cannot make a stale proposal current again.

## Executed workload

The deterministic workload is the #279 release-branch scenario.

### Initial promotion

```text
release_branch = release
operation = promotion
risk = low
state = v0
```

Expected and executed behavior:

```text
PAMA allow_with_ledger
-> provider allow
-> ordinary governed commit
-> receipt emitted
-> later governed recall admits current project memory
```

### Correction

```text
release_branch = main
operation = correction
risk = medium
state = v1
```

Expected and executed behavior:

```text
PAMA require_review
-> provider escalate
-> unapproved commit refused
-> wrong input_identity approval refused
-> self-approval refused
-> exact external approval accepted as evidence
-> Agent Memory independently revalidates
-> correction commits
-> old release value becomes superseded/event-invalid
-> main becomes current and recall-admissible
```

### Stale replay

Replaying the previously approved correction after state advances to `v2` produces:

```text
committed = false
refusal = stale_authorization
```

The approval remains authentic evidence but does not become standing authority over a changed state.

### Authority/scope attack

A critical `scope_expansion` targeting M5/A5 resolves to PAMA `block`, projects to DashClaw `deny`, and is refused by the bound commit seam before the substrate write log changes.

### Cross-project recall

The same-tenant substrate may still return matching candidates for a different project context. Governed admission rejects them, demonstrating again:

```text
candidate presence != recall permission
```

## Reference surfaces

Pure adapter:

`reference/agentmem_ref/dashclaw_external_verdict.py`

Reference HTTP entrypoint:

`reference/run_dashclaw_provider.py`

Deterministic workload:

`reference/run_dashclaw_external_verdict.py`

Adversarial tests:

`reference/tests/test_dashclaw_external_verdict.py`

Focused evidence workflow:

`.github/workflows/dashclaw-external-verdict.yml`

The HTTP entrypoint is intentionally a small standard-library server. DashClaw requires a public HTTPS provider URL, so a live integration must place this reference endpoint behind controlled public HTTPS or deploy an equivalent production-grade service. The reference server itself is not claimed as a production deployment architecture.

## Current limitations / remaining #279 work

This slice proves the provider contract and the stateful Agent Memory workload in the Agent Memory repository. It does **not** yet prove that the request traversed a live DashClaw guard over public HTTPS.

Still required before #279 closes:

- configure a live DashClaw v5.24+ org with provider scope `agent_memory.mutation`;
- run `dashclaw.connection_test` through DashClaw's production wire client;
- execute real `allow`, `escalate`, and `deny` through DashClaw's guard seam;
- capture DashClaw local/external/effective decision evidence and correlate it to the later Agent Memory proposal/receipt without collapsing their identities;
- exercise provider unavailable behavior through DashClaw and verify the configured posture is represented honestly;
- record the cross-repository integration result and any contract defects found.

This slice also proves only cross-session reuse within one governed runtime. It does not prove process-restart durability:

```text
cross-session reuse
!= process-restart durability
```

Restart-safe governance metadata remains #282.
