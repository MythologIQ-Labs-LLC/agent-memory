# #757 — Single-state revocable candidate prototype (C01–C14, bounded slice)

**Date:** 2026-10-09. **Status:** evaluation-only implementation contract, fixed before code and tests.
**Stack:** on draft #765, itself stacked on #764/#763. The standalone hotfix #766 is not yet rebased into this branch.
**Prerequisite design:** `docs/plan-757-composite-trust-state-design-gate.md` from #764. These C01–C14 threat requirements continue to control this slice.

## Architectural scope

Current local evaluators can separately verify a signed registry, issuer policy, policy history, and write witnesses. An old policy can be self-pinned and show a local candidate after a later state revoked its key. Keys for the witness layer cannot be revoked. A bounded 32-item policy revocation tuple and a 64-event lineage are not sustainable as cumulative lifetime deny stores.

This slice introduces a **single, process-local, synthetic evaluation trust-state** with policy snapshot plus a segmented insert-only revocation journal. It uses one observed checkpoint for both issuer and all witness keys, then composes existing layers into a **read-only link-candidate receipt**. The composed result is bound to the exact checkpoint and can be invalidated when the checkpoint advances.

It does NOT authenticate a policy distributor, establish externally trusted freshness, prove semantic equivalence, implement durable/distributed CAS, accept a proposed link, or change memory. The original local evaluator APIs remain diagnostic and non-authoritative.

## Mechanism and declared constraints

- Genesis binds the entire canonical initial `IssuerPolicySnapshot`, profile/version, and an opaque ledger identity using domain-separated SHA256.
- Mutations are restricted to exact expected-head compare-and-swap under one process-local lock: `revoke_key`, `invalidate_schema_revision`, or `publish_policy`. Revocation is monotone and idempotent replays reject duplicates. Policy changes reuse the #764 transition validator and globally refuse nonadjacent revision identifiers.
- Journal events bind sequence, previous head, operation, exact tenant-scoped deny key or whole policy digest, and profile/version. Events accumulate in **individually bounded segments** (16 events each), without an arbitrary total lifetime revocation or event count cap; rollover itself cannot truncate prior commitments.
- Revoked keys have one tenant-scoped deny namespace shared by **schema issuers and actor/source witnesses**. Schema-revision invalidations are separately tenant-scoped.
- The state owns defensive copies of policy snapshots and events. Its immutable `TrustView` contains checkpoint plus independent frozen deny indexes.
- A composite operation obtains one `TrustView`, verifies caller-supplied expected checkpoint head and sequence, and evaluates exact proposal/schema/policy/witness evidence **against only that view**. A later in-process change detected before return refuses. Even if a change occurs just after return, receipt recheck against the new head refuses.
- The composed receipt binds the exact typed proposal, registry transcript/context, verified schema-issuer key digest, witness-role key digests, policy snapshot, checkpoint head, all component verdicts and their reasons.
- Any revoked input dependency or invalidated schema yields **refused** before an absent or unproven lower layer could yield `abstain`. Existing structural refusals dominate. Distinct canonical active properties are refused even if #766 has not been rebased; genuinely unmapped labels abstain.
- A standalone local positive does not imply a composite positive. A composite can be `mechanical_candidate` only when structural evidence is **not underdetermined**, schema, issuer, and witness validations are individually positive, no dependency revoked, and the expected head matches. It remains untrusted/non-authoritative.
- No query accepts or mutates memory, promotes identity, or asserts provenance independence. Receipt `recheck` is conservative: ANY change in trust head invalidates previous positive observations pending full recomputation.
- The journal prototype is in-memory, and its replay verification checks cryptographic internal consistency against caller-provided pins. It does not persist durable state or establish a trusted external current head.

## Before-code adversarial matrix for this exact slice

T01. A self-pinned old policy local candidate cannot become a composite candidate **when current state and expected current head are provided**. Current policy must be the sole policy used.
T02. One revoked schema-issuer key refuses a composite, despite still-valid old signatures; same for each of the four witness key positions.
T03. Deny always dominates a lower-layer `abstain`, including an unmapped property label.
T04. Candidate records bind exact proposal bytes, complete signed registry context, policy digest, checkpoint and witness signature/key material; changing any input alters the receipt digest or refuses.
T05. A structural `refused` refuses; an `underdetermined` abstains and keeps the reasons even when signatures verify.
T06. An explicitly different signed canonical property refuses. An unknown label abstains.
T07. All positive and negative receipts explicitly keep `issuer_authorized=false`, `principal_authenticated=false`, `identity_verified=false`, `origin_independence_verified=false`, `can_supersede=false`, `mutates_memory=false`, `authority_effect=none` and `currentness=not_established`.
T08. 80+ distinct revocations across multiple 16-event pages can be issued, read and verified without policy's 32-element deny cap or lineage's 64-event cap blocking another revocation.
T09. Event reordering, omission, corrupt payload/head, duplicate denial and stale expected-head append all fail closed; restart is explicitly unsupported until durability exists.
T10. An old receipt is invalid after any new policy/deny checkpoint. A new receipt re-evaluates current keys and refuses explicitly denied inputs.
T11. Replay from the same initial snapshot is deterministic; forged self-rehashed history and forged pins are mechanically possible but still not authenticated.
T12. No guessed property synonym, R6 or #732 frozen fixtures, inference calls or provider credentials.
T13. All statuses and exact-head tests are included in an independent adversarial review before merge.
T14. Input mutation, subclass-equality abuse, concurrent head changes and malformed roles cannot upgrade a verdict.

## Important remaining failure modes

This *does not fully close D2*: a caller who controls the trust state **and** supplies its own expected head can still stage an old-but-self-consistent state. Only authenticated external head distribution/persistence can cure that.

This *addresses the specific D3 saturation mechanism for local key/schema denial*, not general production capacity. The in-memory index and number of pages still grow with the number of events, and schema/grant declaration payloads remain bounded. An external persistent, epoch-proof-based design and restart/distributed-fork recovery still require a separate gate.

False-link correction here means only conservative **candidate invalidation** at state advancement. It does not perform an accepted-link reversal, semantic repair, or memory mutation. Those actions do not exist.

**Merge gate:** exact-head full CI, independent unseen falsification, rebase after earlier reviewed stack and #766, and explicit acknowledgement of remaining external trust assumptions. Keep #757 open.
