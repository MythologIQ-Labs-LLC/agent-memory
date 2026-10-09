# #757 — Design gate for unified candidate trust state (D2, D3)

**Date:** 2026-10-08. **Status:** REQUIRED DESIGN CORRECTION, not implemented or merge-qualified.

## Failure evidence and non-goals

Independent 31-hypothesis/46-case adversarial review reported:

- **D2:** a well-formed old policy, evaluated with its own equally old pin, still yields a positive *mechanical candidate* after a later policy revokes the signing key. A separate `verify_policy_lineage` operation is not compositional protection.
- **D3:** `IssuerPolicySnapshot.MAX_REVOKED=32` and `PolicyLineage.MAX_TRANSITIONS=64` stop all safe policy advancement at saturation. At that point the next compromised key cannot be revoked. Raising caps only defers the failure.
- **Witness gap:** keys that sign actor/source observations have no revocation input.
- **D5 (fixed separately in #765):** semantic underdetermination must stay visible through all layers.
- **Correction gap:** candidate records must remain reviewable and invalidatable after provenance/identity assertions are disputed.

These are **mechanical correctness defects**, not proof of runtime exploitation: there is no link-acceptance or mutation API. The current system only produces evaluation-only results and does not authenticate externally supplied trust pins.

## Intended single composition boundary

A future `qualify_link_candidate_at_trust_state` API must be the **sole positive candidate producing composition surface** for these layered results. The existing low-level qualification APIs remain diagnostics, explicitly marked `unbound_local_observation`; no downstream consumer may treat a standalone candidate as a current admissible link.

Inputs to the composition boundary:

1. The *same exact* `ProposedIdentityLink`, in canonical typed bytes, across every subevaluation.
2. A **single immutable, versioned trust-state checkpoint** supplied through a defined external anchor interface: policy ref, generation/epoch, sequence, head digest, policy snapshot digest, revocation-state root, trusted-source reference and explicit freshness status.
3. Replay/inclusion proof for the exact policy snapshot at that checkpoint. No check may use a different policy revision, registry digest, issuer key, witness key, or head.
4. The signed schema crosswalk, the policy grant, and all four source/actor witnesses, with their *exact* digests/roles/claimed principals bound to the proposed link record.
5. Both issuer-signing keys and source/actor witness key material must be checked against the **same deny state**, with deny taking precedence over any missing/unknown evidence.
6. The structural preflight status/reasons must be carried intact, with `refused > underdetermined/abstain > mechanically plausible` precedence. No silent upgrade.
7. The resulting bounded, read-only candidate receipt has a canonical digest and dependency set, and every recomputation against a newer trust-state checkpoint can invalidate prior candidates.

All external anchors remain **mechanically caller-supplied** in this evaluation phase. Any `checkpoint_match` claim MUST NOT be named `trusted_currentness` until a separately authenticated distributor/trust root exists.

## Preregistered future composition falsifiers, C01–C14

- **C01:** Existing old self-pinned policy cannot yield a *composite* positive candidate when composed against a distinct supplied newer head with the key revoked.
- **C02:** An unbound low-level `policy_matched_candidate` is never a substitute for C01.
- **C03:** A composite receipt binds the same proposal identity, both exact write revisions, registry digest, policy snapshot digest, lineage checkpoint and witness set. Changing any element changes or invalidates the receipt.
- **C04:** Revocation applies equally to schema issuer and all four witness signer keys. One revoked dependency refuses the composite even when every signature remains valid.
- **C05:** Explicitly denied keys and schema revisions refuse even if a lower evaluator abstains.
- **C06:** Recomputing a candidate at a new trust-state head can invalidate a previously plausible candidate, with a durable rejection reason; old receipts cannot claim continuing currentness.
- **C07:** Underlying schema dissimilarity is a refusal; unmapped labels and unproven subject/property identity abstain.
- **C08:** The evaluator never grants semantic verification, principal authentication, source independence, supersession or memory mutation.
- **C09:** A single actor owning four witness keys cannot obtain verified origin independence.
- **C10:** Every deny-state representation has safe, provable extension semantics beyond one bounded batch; saturation cannot silently allow a compromised key.
- **C11:** New deny events are appended to bounded independently committed segments/pages; an independently pinned next-epoch checkpoint binds the previous state and the complete cumulative deny semantics.
- **C12:** Any missing deny membership/non-membership proof, old anchor, incorrect ancestry, fork or unsupported epoch migration must refuse/abstain without positive candidate.
- **C13:** The implementation never treats signatures or a self-supplied root as external authority.
- **C14:** False links can be flagged, withdrawn, disputed and retrospectively invalidated with reasoned provenance, without rewriting previously emitted evidence or mutating canonical memory.

## Capacity-safe revocation model: design requirements

A bounded snapshot cannot contain an unbounded global revocation set. Prefer **separately versioned, append-only deny events**, partitioned by tenant/purpose and issuer vs witness role, with **bounded pages and explicit epoch transitions**. Each epoch checkpoint commits to the complete effective prior deny state and a verified continuation; epoch rollover must be an explicit, auditable operation, not truncation or forgetful compaction. Retain monotone lifetime denial semantics for keys until separately governed recovery/rotation is designed.

Verification can be bounded by exact proof size and a pinned checkpoint root, but any sparse/Merkle absence proof or compacted summary must be verified independently, and no candidate may pass based on an unverified purported absence from the deny set.

One implementation could use a sparse Merkle set with insert-only deny keys, plus chained checkpoint epochs. **This is not yet an approved cryptographic format or production design.** Alternatives (bounded segmented logs with anchored monotone snapshots) must be assessed for deterministic replay, fork recovery, storage and proof-of-absence soundness before implementation. Never conflate independent local checksum verification with a trusted checkpoint authority.

Avoid infinite historical replay at query time. Prefer explicit, persistently anchored head, evidence for current revocation state, and a deterministic candidate-bound proof.

## Correction and acceptance sequence

1. First independently qualify repairs D1/D4/D5/D6/D7/D8 and the distinct-schema main hotfix.
2. Keep #764 at **FAIL** until C01, C04, C10–C12 have executable evidence.
3. Prototype the new trust-state + deny composition **in evaluation only**, with synthetic examples where local subcalls pass but the composite refuses.
4. Independently adversarially review trust-state distribution, page/epoch rollover, fail-closed proof checks, witness revocation and candidate expiry.
5. Only after proving these mechanics, design an externally authorized trust root and actual provenance/correction workflows.
6. Do not assert readiness of baseline v7, do not consume R6/#732 frozen inputs and do not touch runtime.

**Status boundary:** This document identifies a necessary architecture and preregisters negative outcomes, but it is not evidence that D2/D3 are resolved.
