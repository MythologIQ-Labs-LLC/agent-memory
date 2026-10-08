# Cryptographic ancestry review: proposition identity and governed recall

**Review date:** 2026-10-08  
**Status:** Design input for [#757](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/757), **not** an accepted v7 mechanism or a new external dependency.  
**Related:** #732, #597, #596, #470, #232, #263, #265, #487, #152, #180, #690, #719.  
**Runtime impact:** none. **Evaluation/benchmark impact:** none.

## Decision in one paragraph

There is **no sound cryptographic shortcut from a verified content address to semantic proposition identity**. A canonical digest answers *are these the same canonical bytes/structured representation?*, a signature answers *did a holder of this key commit to these bytes?*, a trusted issuer claim answers *who is authorized to make that assertion?*, and a memory relation answers *do these independently described facts concern the same entity, property, scope, and applicable time?*. These are different questions. UOR-ADDR and PrismPM can help us construct a **verifiable identity-evidence spine** after a proposed link has independently defensible meaning, but neither makes paraphrases semantically equivalent by cryptography. TRACE and AGT provide valuable proof, verification, and policy-boundary lessons; they must not become Agent Memory's mutation or recall authority.

The immediate **#757 design target** is a reproducible, revocable and non-authoritative *identity-link evidence proposal*, not a hash-derived merge, lexical alias table or automatic cross-write supersession.

## Exact inspected repositories and source rights

Current upstream observations are separate from Agent Memory's accepted historical qualification pins. **No third-party code, conformance data, schema, text or fixture is copied by this review.**

| Project | Observed upstream main revision | Observed source rights | Existing Agent Memory status |
| --- | --- | --- | --- |
| [UOR-Foundation/uor-addr](https://github.com/UOR-Foundation/uor-addr) | `165b51e3e2113ee5d032730cde709335d4fe9b60` | Apache-2.0 (root `LICENSE`) | Optional v0.2.0 JSON content-address profile pinned to historical `d78f82f26034880e91b1d54c21900a33ab73f695`; cross-language and no-authority tests from #232. Do not silently upgrade the pin to main. |
| [UOR-Foundation/PrismPM](https://github.com/UOR-Foundation/PrismPM) | `09f8b916023cbb7db945b8e8267eebba25965f26` | Workspace `license = "MIT OR Apache-2.0"`; present `LICENSE-MIT` and `LICENSE-APACHE`. Check each vendored/dependency subtree separately before copying any file. | Previously reviewed at `73d041a46a4e15127e7fdef1dc16a8d592c5ccd3` under #470; evaluator mutation-pressure lesson already native. Current release docs describe 0.3.0 SDK, formal compilation and independent verification. |
| [agentrust-io/trace-spec](https://github.com/agentrust-io/trace-spec) | `4c775298fd71a34d89f887397ea23bd6149ccb5b` | **Mixed:** normative spec/schema Community Specification License 1.0; SDK/source/tests/examples/workflows Apache-2.0; other docs CC BY 4.0; historical v0.1 spec CC BY 4.0. Attribution and spec-conformance implications must be assessed per file. | Optional external-evidence interop. Agent Memory qualified `agentrust-trace==0.10.0` from `3a561d84d752794b9afa994ce16ed35c24ac0acb` (#440/#487), not an automatic qualification of current upstream. |
| [microsoft/agent-governance-toolkit](https://github.com/microsoft/agent-governance-toolkit) | `17595e649abdfa703962c2f8c241826f68318109` | MIT root LICENSE, subject to retaining copyright/license notices if reused. Check package-level and third-party files individually. | Optional policy/enforcement peer, historically reviewed at `e0574c1eb44a9b02f106e2b4c63fc60ec3c017ce`. AGT remains *not* Agent Memory's memory authority. |

**License posture:** independently implement general concepts using our own expression and tests where sensible; MIT/Apache-2.0 code reuse is generally viable with relevant license/notice obligations, but **permission to copy is not a technical decision to copy**. Never place TRACE normative text, schema, or distinctive conformance prose inside Apache-licensed Agent Memory without separate review of its Community Specification License 1.0 obligations. Do not flatten mixed licenses into a single SPDX label. This is an engineering review of published terms, not a legal opinion.

## What has already been harvested

| Mechanism | Current native or qualified home | Assessment |
| --- | --- | --- |
| UOR-style exact canonical content reference | `reference/agentmem_ref/memory/uor_content_reference.py`, `docs/profiles/uor-addr-content-reference-profile.md`; cross-language compatibility #232 | **Already qualified as optional interop**. Content digest must not replace the logical memory ID, source/tenant/scope context, proposition identity or lifecycle state. |
| Temporal commitment and signer proof | `reference/agentmem_ref/memory/temporal_commitment.py`, `temporal_trust.py`, ADR-031, `schemas/temporal-commitment.schema.json` | **Already native as evidence**. RFC 8785 canonical JSON, SHA-256 content identities, Ed25519 attestation, previous-event/sequence commitments, external witness evaluation and signer-trust checks keep content integrity distinct from wall-clock/currentness/trust/authority. |
| PrismPM independently verified replay and negative pressure | `reference/run_benchmark_integrity_mutants.py`, `docs/51-benchmark-integrity-mutation-probes.md`; #470 | **Already harvested** as evaluator sensitivity, not a proof of semantic correctness. Old and new verification gates must resist trivially passing tests and deliberately broken variants. |
| TRACE signed portable evidence and verifiers | `reference/agentmem_ref/memory/external_evidence.py`; TRACE/cMCP comparator and source-rights fixtures; #180/#440/#487 | **Already present as optional evidence normalization**. Valid signature alone does not prove an event occurred correctly, memory is current, a policy is correct, a key remains trusted, or a memory can be admitted. |
| AGT policy/identity/audit separation | Governance projection, recall policy and PAMA, #152/#180, external enforcement interoperability | **Already established**. External runtime policy/enforcement can be stricter, never a back door to weaken recall/isolation, lifecycle or memory-specific authorization. No AGT runtime dependency necessary. |
| Persistent mutation consistency | Restart-safe transactional checkpoint generations and journal-tail validation under Agent Memory substrate | **Already substantially implemented**. Avoid creating a second ledger or global principal authority just to keep proposition-link records. |

These equivalences are *capability categories*, not claims that Agent Memory has imported entire peer implementations or their conformance certifications.

## New or sharpened lessons for #757

### 1. Separate four identities, plus the governing decision

A cross-write update should explicitly distinguish:

1. **Logical memory identity:** a stable first-party record ID, not tied to content, name, or signature.
2. **Canonical content/revision identity:** digest of a *versioned typed payload and canonicalization profile* (UOR-ADDR lesson); immutable and byte-verifiable, but not a semantic equivalence verdict.
3. **Proposition/slot identity:** a justified, scoped claim that an entity/property in one write is the same property in another write; not merely equal display strings, value, or candidate link.
4. **Evidence producer/issuer identity:** signer/public key and separately verified principal/source trust, including key validity, scope and revocation (TRACE/PrismPM/AGT lesson).
5. **Governed state transition:** the *only* mechanism that may apply supersession, correction, withdrawal or active-recall admission, using existing Agent Memory authority; none of 1–4 alone authorizes this.

### 2. Binding evidence can be independently replayed, but cannot create semantic proof

A **proposed**, unratified `proposition-identity-evidence/v0` could eventually carry:

- separate IDs and source revisions for both candidate facts, immutable typed-extraction profile/version, optional independently verified canonical digests;
- actor, tenant, scope, source, time, cardinality and proposition descriptions on **both** sides;
- typed identity-basis kinds distinguishing explicit authoritative caller declarations, independent source/schema guarantees, evidence-only candidate links, inferred similarity, and unknown;
- origin of each supporting signal with **independence/conflict flags**, so two claims from one extraction response do not masquerade as corroboration;
- exact expected prior revision/head, proposed predecessor edges and stale-head/fork handling;
- signature/issuer/trust/revocation/freshness **as optional verification context**, not a semantic merge confidence converted to permission;
- separate decision posture `proposed | unverified | disputed | rejected | authorized_by_existing_memory_governance`; no automatic `same_property=true` because a digest or signature validates;
- replay/refusal reason and `authority_effect=none` until accepted via existing lifecycle/PAMA and appropriate source rights.

**This is a research checklist, not a schema, API or migration order.** It must survive independent adversarial review, privacy/egress design, baseline succession and an alternate design comparison before implementation.

### 3. PrismPM's newer journal lessons warrant specific challenge cases

The currently inspected PrismPM `CONFORMANCE.md` DK-08 through DK-14 includes bound identity keys and content addresses, *stale-head/partial-write rejection*, *authenticated replay*, and an **atomic commit bound to the current head**, while keeping modeled preparation distinct from authentication and authorization.

Agent Memory has related transactional and revision guarantees already, but #757 should prove those invariants **for newly proposed proposition-equivalence links**:

- A validly signed historical alias cannot override a newer explicit correction, tombstone, revocation, or scope change.
- Two distinct proposals against the same expected head must not both silently become canonical under concurrent admission.
- A stale reader may verify the old signed bytes without treating its identity-link or recall eligibility as current.
- An invalid link must not poison a transitive alias closure after replay, restart, consolidation or rebuild.
- Replaying a legitimately accepted link must not infer approval for a **different** identity pair or revised target.
- A successful verifier should remain able to detect deliberately corrupted head, candidate ID, source binding, key, or previous edge.

These are **memory semantics** and integrity tests, not PrismPM toolchain adoption, and none require copying PrismPM code.

### 4. TRACE's limitations are important negative cases

Upstream TRACE `LIMITATIONS.md` explicitly distinguishes signed receipts from trustworthy execution, and documents replay/freshness, key compromise and revocation checks. For Agent Memory:

- **Signature valid, signer unknown/revoked**: keep historical evidence verifiable, but fail applicable *trust/currentness* and do not promote identity equivalence.
- **Signature fresh, claim false**: truth and source trust remain independently evaluated.
- **Signature valid, receipt replayed out of context**: reject or abstain on scope, audience/purpose, expected head and freshness.
- **Same signer issued two incompatible slot equivalences**: record conflict instead of picking a higher-confidence identity edge.
- **No independent root of trust**: do not self-certify a key merely because a document embeds it.
- **Offline-only non-revocation unverifiable**: preserve `unknown`, do not emit a fully trusted status.

TRACE describes runtime action records, not semantic memory equivalence. Optional future evidence interop must not claim TRACE v0.2 conformity without its own exact-profile qualification.

### 5. Governance Toolkit's most relevant recall lesson

A memory retrieved with a correct content digest or signature is still subject to **memory-specific recall admission** and host policy. The memory engine owns its scope/consent/lifecycle/PAMA boundaries; a host or AGT-style enforcement peer owns its tool/runtime powers. A stricter external denial stays strict, and a permissive external allow does not override restricted memory. No identity proof should confer read permission, tool execution, exporter access, or correction rights. Inspect external context aggregation and derived-sensitivity ratcheting as possible *future* bounded recall-pressure tests, but only if existing Agent Memory controls prove a concrete gap.

## Evidence-driven prioritization

**P0, already in scope #757:** Independently authored, frozen proposition-equivalence challenge rules, explicit non-circular identity criteria, refusal/abstention semantics, collision and adversarial lineage cases. This is the new real general-memory issue exposed by #756.

**P1, design-dependent:** Versioned, tamper-evident link proposal and head-consistency receipts that reuse native canonical/evidence and transactional primitives; implement only if an accepted identity mechanism needs them. Do not introduce mandatory UOR, PrismPM, TRACE or AGT dependencies.

**P2, conditional interoperability:** Optional UOR content labels or TRACE receipts for exporting evidence after the native identity relation is accepted. Keep historical version pins until a *new* interoperable conformance test passes.

**Do not do:** Change Runtime Baseline v6, add case-based aliases to G12, insert hash equality as a substitute for semantics, pass through upstream policy decisions as memory authority, import PrismPM's generated compiler/runtime, silently update TRACE to a new SDK, or migrate the memory core to Rust because these peers use it.

## Review conclusion

**The prior harvest was real, not merely listed.** Core digest, signing, replay, revocation/trust and governance boundaries are already in Agent Memory, and PrismPM mutation-sensitive verification has been absorbed. The new value is in using these proven *evidence disciplines* to make #757's future cross-write identity claims durable and falsifiable while preserving the distinction between verification and truth. **No new third-party runtime component is justified at this stage.**

## Anchors

- Historical closeout: `docs/52-harvest-closeout-final.md`; `reference/fixtures/harvest-closeout-final-v1.json`; #470, #487, #489.
- Native equivalence: `reference/agentmem_ref/memory/temporal_commitment.py`, `temporal_trust.py`, `uor_content_reference.py`; `docs/profiles/temporal-commitment-evidence-profile.md`.
- New upstream review (2026-10-08): [UOR-ADDR conformance](https://github.com/UOR-Foundation/uor-addr/blob/165b51e3e2113ee5d032730cde709335d4fe9b60/CONFORMANCE.md); [PrismPM conformance](https://github.com/UOR-Foundation/PrismPM/blob/09f8b916023cbb7db945b8e8267eebba25965f26/CONFORMANCE.md); [TRACE rights](https://github.com/agentrust-io/trace-spec/blob/4c775298fd71a34d89f887397ea23bd6149ccb5b/LICENSE) and [limitations](https://github.com/agentrust-io/trace-spec/blob/4c775298fd71a34d89f887397ea23bd6149ccb5b/LIMITATIONS.md); [AGT license](https://github.com/microsoft/agent-governance-toolkit/blob/17595e649abdfa703962c2f8c241826f68318109/LICENSE).
