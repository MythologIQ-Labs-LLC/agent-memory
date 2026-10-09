# #757 — Issuer-policy lineage, anti-rollback observations, and irreversible revocation (J57–J72)

**Date:** 2026-10-08. **Preregistered before the evaluator and tests.**

**Stack:** after the evaluation-only issuer-policy grant/revocation work in draft PR #763. This is not an independent issuer authentication service or a production baseline successor.

## Problem and bounded outcome

A consumer can validate a signed schema, a matching issuer-policy digest, and an explicit revoked key, but an adversary may replay an **older, internally valid policy snapshot** predating that revocation. Signatures and canonical hashes do not establish *latest state*. An evaluation-only lineage needs to refuse rollback against an **independently pinned expected head**, serialize competing in-process writers, preserve revocation evidence in every future snapshot, and distinguish mechanical consistency from external freshness.

This slice qualifies the behavior of a bounded, immutable sequence of complete `IssuerPolicySnapshot` records. It deliberately does **not** invent wall-clock authority, obtain trusted pins, apply policy to real memory, or accept new semantic-identity relations.

## Contract

A timeline starts from an externally supplied policy genesis snapshot. A domain-separated genesis digest binds its entire canonical policy digest, policy identity and profile/version. Each append carries an exact prior head, consecutive sequence, full next policy snapshot digest, and domain-separated event head. A caller attempting to append must provide the expected current head; comparison and update occur under a process-local lock.

A valid transition requires:
- The same policy identity, **new opaque policy revision ref**, strictly consecutive integer sequence, and exact previous head.
- Revoked key-digest sets and invalidated schema/revision sets can only **grow**, never shrink.
- Every old scope-specific issuer grant remains represented in the new snapshot. Active grants may become revoked; revoked grants cannot become active again at that scope.
- If an active grant changes issuer key reference or public-key digest, the previous key-material digest must be explicitly revoked in the next snapshot. A change in publisher is a *candidate key rotation*, not authorization.
- Existing grant scope references cannot be silently reassigned. New scopes may be added as candidate grants with no implied production authority.
- Explicitly revoked key digests or invalidated schema revisions never qualify as active when presented to #763's evaluator. The transition does not promote or approve anything.

Replay recomputes policy digests, sequence, prior heads, event heads and all transition constraints. The verifier may compare the resulting head, count and genesis against separately expected values. **All expected values are caller supplied and must come from a trusted external channel to convey freshness**. Passing replay without such a channel shows only internal consistency. A malicious publisher can construct an alternate fully consistent lineage and corresponding pins.

## Preregistered invariants

| ID | Safety property |
| --- | --- |
| J57 | Genesis binds profile/version, policy identity and the canonical full initial policy digest. |
| J58 | Every event binds its exact sequence, prior head, full policy digest and profile/version with domain separation. |
| J59 | Append requires exact expected current head and is serialized by an in-process lock. Stale competing writers cannot both append on one timeline. |
| J60 | Replay refuses reordered, missing, duplicated, edited, rehashed-inconsistently or cross-policy events. |
| J61 | All policy revision refs must change between successive snapshots; names themselves do not establish chronology. |
| J62 | Key revocations never disappear in subsequent snapshots. |
| J63 | Registry schema/revision invalidations never disappear in subsequent snapshots. |
| J64 | Existing grant scopes cannot be silently removed or changed to an unrecorded grant. |
| J65 | Revoked grant scopes cannot be reactivated. |
| J66 | Active grant key rotation requires explicit revocation of the prior key digest. No automatic authorization follows from the transition. |
| J67 | Replay checks exact types, bounded event count and canonical policy digests. |
| J68 | Verification compares **independently supplied** expected genesis/head/count, refusing an incorrect or stale pinned head. |
| J69 | Even passing independently supplied expected values cannot authenticate the channel delivering those values or establish reliable time. |
| J70 | A fully rehashed alternate history with attacker-controlled pins may pass mechanical verification. Its receipt still denies authority. |
| J71 | No code imports or writes the protected runtime, PAMA, #732 extractor, frozen benchmark, R6 or production storage. No inference/service/provider required. |
| J72 | All receipts report `authority_effect=none`, `issuer_authorized=false`, `identity_verified=false`, `can_supersede=false`, `mutates_memory=false`, `integration_state=evaluation_only`. |

## Independently specified adversarial families (before tests)

1. Baseline two-revision lineage with explicit key revocation and active-to-revoked transition.
2. Two writers using the same head; at most one append.
3. Unchanged policy revision, changed policy identity, wrong previous head and incorrect event count.
4. Lost revoked key, resurrected revoked grant, lost invalidated schema revision, removed grant without a tombstone, rekey without revoking former key.
5. Explicit key rotation with revocation; retain auditable transition but do not call the new issuer legitimate.
6. Modified event payload, wrong snapshot digest, reordering, truncation, substituted policy scope, substituted policy genesis.
7. Valid old prefix compared with an externally pinned current head, and a fully rewritten attacker-controlled lineage plus attacker-controlled pins.
8. Repeat deterministic replay and no state mutation on any refused append; deep immutability of receipts.

These tests are **structural qualification**, not a benchmark of semantic equivalence, production key security, external clock accuracy or general long-term recall. Use opaque identifiers rather than natural-language benchmark inputs. Do not derive new tuning thresholds from #732/R6 examples.

## Completion and deployment gates

Deliver only in `reference/agentmem_ref/evaluation/` and `reference/tests/`; index this document. Run exact-head CI and independent, unseen adversarial review. Keep the follow-on PR stacked against #763 until #763 is separately reviewed/merged. Do not merge or change production runtime as a side effect. Issue #757 remains open.

True production freshness would require independently authenticated, persistent, anti-rollback checkpoint distribution and authority policy, recovery/compromise procedures, tenant-scoped source/actor provenance, false-link correction, and an approved runtime-baseline successor. None is provided by this evaluation mechanism.
