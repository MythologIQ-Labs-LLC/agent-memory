# #757 — Replayable proposition-link evidence journal, qualification-only

**2026-10-08.** Preregistered design before implementation.
**Scope:** `reference/agentmem_ref/evaluation` only. No protected
runtime, baseline-v7, semantic merge, persistent API, memory lifecycle
action, R6/benchmark score, or inferred currentness.

## Capability goal

The preflight under PR #759 distinguishes structural refusal,
underdetermination, and structurally plausible-but-unverified links, but
does not model the *history* of a proposal. A future identity mechanism
must make it possible to inspect the exact pair of memory revisions and
claims submitted, challenge a proposed relationship, detect stale
updates and accidental forks, and replay that history reproducibly.

This slice implements an **unsigned, in-memory, append-only diagnostic
journal**, accepting only evaluation proposals that are not structurally
refused. `proposed` means **unverified pending review**, never an accepted
semantic relationship. Only `withdrawn` and `disputed` resolutions are
supported; **no accept/approve/apply** event exists.

## Registered invariants (J01–J14)

| ID | Requirement |
| --- | --- |
| J01 | A journal event binds a fixed stream, position, prior head, event kind, proposal content digest and full claim/revision context using a versioned canonical JSON contract. |
| J02 | The initial head is a deterministic domain-separated genesis; append needs exact expected current head and rejects stale writers. |
| J03 | A structural preflight refusal is rejected and must leave the journal unchanged. Undertermined and structurally plausible statuses remain **unverified**. |
| J04 | Only already-proposed content digests can be disputed or withdrawn; repeat resolutions and duplicate proposals refuse without mutation. |
| J05 | No transitive identity expansion, inferred alias, arbitrary new owner authority, or mutation of canonical memories. |
| J06 | Immutable event receipts and replay recompute hashes, sequence, previous-head chain, full proposal digest, status, and evidence; corrupt bytes or modified fields fail. |
| J07 | A journal cannot be replayed under a different stream identity. |
| J08 | Two writers starting from the same head cannot both extend one process-local journal; acceptance order is serialized using a lock. |
| J09 | Replaying different valid event orders cannot assert semantic equivalence or accept a withdrawn relationship. |
| J10 | Changing property, actor, tenant, scope, cardinality, value, evidence claims, expected source head, or proposal identity changes its digest. |
| J11 | Same bytes/digest, signature-looking evidence or consistent labels are **not** authenticated issuers, verified ontology, or same-property proof. |
| J12 | Historical audit receipts stay inspectable after a withdrawal/dispute; no deletion of previous proposal evidence. |
| J13 | All results contain explicit `authority_effect=none`, `identity_verified=false`, `can_supersede=false`, and `mutates_memory=false`. |
| J14 | Journal records are bounded; record deserialization/replay rejects wrong types, missing fields, forged digests and unsupported contract versions. |

### Adversarial trials fixed before writing evaluator

Opaque, not English benchmark texts: forked expected head, reordered
messages, wrong stream, sequence gaps, truncated history, tampered
proposal subject, changed claimed evidence, swapped old/new fact,
malformed cardinality, stale revision, repeated proposal or resolution,
resolution of nonexistent proposal, replay after withdrawal/dispute,
and same-value/cross-tenant refusal. Repeat deterministic replay, verify
no state changes on failed appends, and show identical export/replay.

## Limits of a passing qualification

This is a **tamper-evident local hash chain, not tamper-proof storage**.
Anyone able to rewrite every event can rehash the chain. Without an
independently pinned checkpoint, trusted signing root and a durable
multi-writer storage protocol, hashes prove only *internal consistency*.
The journal is not persistent across restarts and has no tenant authentication.
A caller-supplied source reference or signature claim is never independently
verified by this implementation.

A structurally plausible proposal does not prove same property.
The journal records evidence *about a disputed candidate*, not memory
truth or even applicability. No accept event, semantic relation edge,
currentness update, or permission is possible here.

A future first-party runtime mechanism must separately pass:
ontology/issuer design review, trusted source authentication, correction/
revocation and head-consistency semantics, independently authored general
recall challenges, baseline-v7 succession, and approved protected-runtime
gates coordinated with #644/#731 and #732.

This slice reuses only native Python standard-library hashing/JSON and
the existing evaluation-only `proposition_link_preflight` contract.
It does not embed UOR-ADDR, PrismPM, TRACE or AGT dependencies.
