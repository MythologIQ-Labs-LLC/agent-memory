# #757 — Proposition-link safety preflight, evaluation-only

**Status:** exploratory, preregistered structural falsification contract (2026-10-08).
**Governance:** #732 owner selected design-first; #757 is design-only. This is
**not** a v7 runtime declaration, executable same-property resolver, score,
holdout, external identity verifier, or trusted enforcement rule.
**Forbidden:** benchmark-specific phrase aliases, value-equality merges, public
facade changes, identity graph mutation, implicit runtime trust.

## The problem we are trying to solve

Two independent write operations can describe the same property without emitting
identical extraction labels. We need a future memory-native way to **justify**
identity continuity while protecting unrelated facts from false supersession.

Cryptographic digests prove canonical content equivalence, and signatures bind
claims to keys; neither establishes that two paraphrases concern the same property.
A claim that an evidence provider verified its own identity is still a claim.
The current R3 restriction on different typed slots remains the safe behavior until
an independently reviewed, trusted semantic-identity path exists.

## Prior commitments / test protocol (frozen before the evaluator code)

The *evaluation-only* probe introduced with this design may observe supplied
metadata to **refuse unsafe proposals** or **report insufficient proof**. It can
never output `verified_same_property`, grant recall, apply a relation, select
canonical identity, or mutate PAMA/lifecycle. Its output has no issuer
authentication and is not admissible as authoritative runtime evidence.

**Registered invariants:**

| ID | Independent falsification invariant |
| --- | --- |
| I01 | Tenant or scope/purpose mismatch must refuse proposed identity continuity; cross-tenant bytes, wording or claimed signatures are irrelevant. |
| I02 | Stale expected-head revision, same fact/revision on both ends, or inactive/disputed/retracted/tombstoned fact must refuse an automatic continuity update. |
| I03 | Multi-valued or unknown cardinality and explicit coexistence must not permit an exclusive supersession; unknown is not single. |
| I04 | Same textual value, normalized value, or content hash is never sufficient identity evidence; different values also do not demonstrate the same property. |
| I05 | Exactly matching caller-reported subject/property keys is merely a *candidate*. Different keys do not prove difference; they require an independently verified crosswalk or abstention. |
| I06 | Repetition of a link, replacement value and slot label within the same extractor invocation is circular evidence, not independent corroboration. |
| I07 | Multiple claimed sources/trace refs cannot prove independent issuance without an external verifier and trust-root/revocation resolution. |
| I08 | Signature validity, cryptographic address matching, high severity/confidence and recency cannot create semantic equivalence or memory mutation/recall authority. |
| I09 | Permuting evidence order, changing human-readable display names, adding duplicate evidence, and replacing values must not turn an unsafe candidate into an authorized link. |
| I10 | Results must explicitly separate structurally refused, underdetermined, and structurally plausible but unverified. All three retain `authority_effect=none`, `can_supersede=false`, and `identity_verified=false`. |
| I11 | An evidence claim with missing provenance is not independently checkable; fail to establish rather than assume proof. |
| I12 | Any cross-write result must be bounded and deterministic, avoid graph traversal, and have no side effects on memory state. |

## Independent adversarial input families (not benchmark training data)

All tests use opaque **typed record metadata**, not sentences from MESA, #732
measurement, #594, or the #756 oracle diagnostic. Inputs deliberately include
unrelated property keys carrying identical values, same property labels across
different subjects/tenants, separately labeled same properties, conflicting
source/actor claims, dual extractor observations from one call, distinct claimed
call IDs without signature verification, revoked/disputed states, stale heads,
coexistent/multi-valued properties and varied value digests. Fixtures are synthetic,
not sampled from the real #732 corpus and not presented as real-world prevalence.

Metamorphic transformations are specified *before* the probe implementation:
(1) permute claim order, (2) duplicate one origin trace, (3) rename a display
label, (4) vary value digests (including equality/low-entropy), (5) vary actor and
source provenance, (6) change a single known state to unknown/multi, (7) change
expected-head version, and (8) change tenant/scope/purpose. Distinguish
supersession refusal from semantic non-equivalence: refusing a potentially unsafe
update is not proving that two properties are different.

## Alternatives to compare before a real v7 design can pass review

A. **First-party explicitly scoped property registry.** Stable, versioned
canonical property IDs are provided by an independently authenticated caller or
domain schema. Advantages: deterministic cross-write identity and low marginal
inference cost. Problems: broad natural-language and legacy migrations cannot
guarantee common registries; authenticity and mutable property definitions must
be verified by an existing trust boundary. The memory engine must still enforce
scope, actor, source, cardinality and currentness.

B. **Proposed crosswalk/alias edges with signed evidence.** A separately
verified authority may declare equivalence between two versioned property IDs.
Advantages: legacy and distributed schema integration, revocation and
replayable provenance. Problems: false merges propagate, signer compromise,
transitive/cyclic aliases and staleness; verification proves issuer commitment,
not truth, and no edge can auto-apply an exclusive update.

C. **Independent model-assisted relation candidates.** Can propose a same-
property relation when schemas do not align. Advantages: possible broad natural
language coverage. Problems: egress, cost, uncertainty and potential evaluator
contamination. Multiple outputs from the same model call are not independent;
even cross-model agreement does not authorize mutation. Requires untrusted
proposal-only path and human/domain/authority confirmation before promotion.

D. **Conservative abstention and user-supplied explicit correction.** No new
identity inference. Advantages: prevents false overwrites and keeps existing
admission semantics. Problems: low recall of valid supersession, needs an
explicit repair/user workflow. This remains the safe fallback if proof is absent.

A/B/C can coexist as evidence routes **only if** the final governance contract
preserves D as the no-proof behavior.

## What passing these tests would mean

At most: structural falsifiers and non-authority outputs work for known
adversarial classes. It would **not** establish semantic recall improvement,
generality, independent source authenticity, proportion of real slot drift,
R6 acceptance, successful identity resolution, graph recovery, or a justified
runtime-v7 implementation. No benchmark metrics are computed.

Before *actual* runtime work: independent review of a design ADR, decision on
the ontology and evidence issuers, separate holdout generation/freeze,
revocation/identity-correction semantics, #644/#731 successor sequencing,
baseline-v6 off-path equality, full negative controls and genuine external
qualification. The identity safety preflight is **not** itself a verified
identity provider.

## Source history

See [cryptographic ancestry reconciliation](research/cryptographic-proposition-identity-ancestry-2026-10-08.md):
UOR-ADDR canonical IDs, PrismPM atomic head and replay, TRACE signed-evidence
limitations, AGT host-policy separation. Agent Memory already implements
canonical commitment, Ed25519 and scoped recall mechanisms as separate
subsystems. Those are not copied or invoked by this evaluation-only preflight.
