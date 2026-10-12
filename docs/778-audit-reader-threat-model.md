# #778 Authenticated deletion-provenance audit reader: threat model (research, no implementation)

**Status:** research and ADR input only. **No audit endpoint is implemented or approved.** This document is based on the source at #777 contract-1.7 candidate `ada418c` / qualification `174d7f8`.

## 1. What exists today (ground truth from the source)

| Mechanism | Trust level | Evidence |
|---|---|---|
| `AgentMemory.open(tenant=, actor_id=, scope=, purpose=)` | **Caller-asserted strings.** The handle's "principal" is whatever the caller passes. | `api/surface.py` `_domain_refs()` returns `(tenant, scope)` |
| `RecallContext.principal_ref`, `project_ref`, `purpose` | Caller-asserted. They scope admission but authenticate nothing. | `api/contract.py` `recall_context_from_envelope` |
| `policy.ExternalVerification` | Caller-constructed. The docstring's "Honest limit" says an actor who can build a Proposal can build one. | `core/policy.py` |
| `verifier_registry` passed at `open()` | **Host-configured.** This is the only existing trust boundary the caller cannot forge through the API. | `ConfiguredCompositionRuntime.create(..., verifier_registry=)` |
| Internal audit records (tombstones with `deleted_fact_uuids`, adapter `events`, stored write semantics, canonical recall) | Reachable in-process through `memory.runtime.adapter` and `_canonical_*`. | Python offers no privacy; anything in-process with the handle can read them. |

**Consequence:** within one Python process, *any* code holding an `AgentMemory` can read internal records today. #777's projection protects the **API contract**, not a process boundary. An audit reader therefore only makes sense **behind a host process boundary** (service or IPC), where the ordinary caller never holds the runtime object.

## 2. Assets
- **A1:** the existence of a deleted generation, and its identifiers, timestamps and lineage topology.
- **A2:** retained (pruned) deleted content and its write semantics.
- **A3:** derivation links (`episode_uuids`) into deleted generations.
- **A4:** audit-access records themselves (who looked at what).
- **A5:** cross-tenant and cross-project existence.

## 3. Actors
| Actor | Can do |
|---|---|
| Ordinary caller | Holds a scoped handle and controls request JSON and handle-open strings |
| Compromised or curious agent | Same as an ordinary caller, with arbitrary query patterns and timing |
| Host operator | Configures the runtime and holds the process |
| Auditor | Holds a host-issued grant |
| Other tenant or project caller | Same as an ordinary caller, in another scope |

## 4. Threats and required controls
| # | Threat (STRIDE) | Control required before any implementation |
|---|---|---|
| T1 | **Spoofing:** caller sets `principal_ref="auditor"`, a role string or a debug flag | Authorization only from a **host-attested grant**. The grant is verified by a host-configured verifier, in the same pattern as `verifier_registry`: a key or verifier the caller cannot register. Request-JSON principals and roles are never sufficient. With no host verifier configured, **every audit call refuses** with the same error as an invalid grant. |
| T2 | **Elevation via ordinary recall** (a recall permission treated as audit) | A separate operation and handle type. Grants are bound to {tenant, project, generation scope, purpose, expiry, nonce}. Recall code paths never consult audit grants. |
| T3 | **Replay or theft of a grant** | Short expiry, per-request nonce, and binding to the host principal and purpose. Single-use for permanent-erasure evidence. A revocation list is checked at each call (`runtime/shared_revocation.py` is a precedent to evaluate). |
| T4 | **Information disclosure via errors, counts or timing** (existence oracle) | Unauthorized, out-of-scope and nonexistent requests return **byte-identical** refusals. Timing must be bounded: a constant-shape refusal path with no lookup before authorization succeeds. Required tests: cross-tenant, cross-project, restart and ID-reuse indistinguishability (#778 item 6). |
| T5 | **ID reuse:** a grant for re-created `memory:x` reads older deleted generations | Scope a grant by **generation** (fact identity plus deletion record), as in the #774×#776 lineage design, never by memory id. |
| T6 | **Reconstruction of permanently erased content** | Audit returns, for erased generations: deletion record metadata only (time, mode, policy, actor) and **no content, hashes or derived semantics** of erased facts. Erased bytes are already gone (SQLite `secure_delete`, verified). The audit must not keep its own copy. |
| T7 | **Content disclosure for pruned generations** | Default to the **minimum disclosure tier**: identifiers, deletion metadata and counts. A content tier requires a separate purpose and legal basis and is recorded. Never routed through recall ranking. |
| T8 | **Repudiation:** audit reads leave no record | Every audit decision (allow or deny) is written to an append-only audit-access log, bound to the host principal, grant id, scope, policy version and decision. That log is itself audit-tier: **never visible to ordinary handles**, and its existence must not leak through history or counts (no recursive leak). |
| T9 | **Tampering:** a caller edits the tombstone or audit stores | Already governance-protected (tombstones checkpointed, restart verified). Add integrity of the access log, e.g. a hash chain, as is done for receipts. |
| T10 | **Denial of service:** unbounded audit scans | Bounded queries (per-generation lookups), pagination and limits. Measure separately (#778 item 8). Never trade governance for speed. |
| T11 | **In-process bypass:** `memory.runtime.adapter._tombstones` | Cannot be closed in-process. Deploy the audit reader only in a host service whose callers never get the runtime object. Document `_canonical_*` as test and evaluation only, and consider gating it behind an evaluation-only construction flag. |

## 5. Proposed shape (for the ADR; not implemented)
- `AuditGrant` (host-signed): `{grant_id, host_principal, tenant, project, scope: [generation refs], purpose, tier: "metadata"|"content", not_after, nonce}`.
- `AuditReader(runtime, host_verifier)`: a separate object constructed only by the host. Its methods take a grant and return an **independently versioned** `audit-response` schema (`audit_contract_version` 0.1.0), never a public 1.7 result.
- Decision order: verify the grant (no data access) → check revocation → resolve the scope to generation identities under canonical admission scope → check the tier against the deletion mode → read → write the access record → respond.
- Refusal shape: one constant document for every refusal cause.

## 6. Test plan (to write first, before implementation)
1. A forged or unsigned grant, a role in request JSON, a debug flag, or a guessed fact UUID each produce an identical refusal.
2. A cross-tenant and cross-project grant on an existing vs a nonexistent generation gives identical refusals, and timing stays within bounds.
3. ID reuse: a grant for generation 2 cannot read generation 1.
4. Permanent erasure: metadata only; no content or hash recoverable.
5. Revocation takes effect immediately, including after restart.
6. Access log: recorded for allow and deny, and invisible to ordinary `history`, `recall` and counts.
7. #777 public projection noninterference: ordinary outputs stay byte-identical with and without an audit reader configured.

## 7. Gate
- **No implementation until** the host authentication boundary is explicit. That needs (a) a deployment model where ordinary callers do not hold the runtime, and (b) a host verifier for grants.
- **Until then:** **BLOCKED**. Records stay internal only.
