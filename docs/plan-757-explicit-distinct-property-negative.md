# #757 — Explicit negative schema identity must refuse

**Preregistered before code, 2026-10-08.**
**Base:** `main` at `3eebb6d54e2a218c4fd10cf53c52acac8384c3e6`. This is an independent hotfix of a defect already on main, separate from draft stack #763–#765.

## Defect

`qualify_property_link` currently treats two *mapped, signed, active* labels declared as different canonical property identities as `abstain`, exactly as it treats an unmapped label. This loses information: an explicit, scope-matching schema disagreement is **negative evidence** for a proposed same-property link, not merely absence of evidence. Still no actual trust-root authentication exists.

## Preconditions and falsifiers

K01. Verified signed registry, correctly scoped proposal, two **distinct mapped active canonical properties** must return `refused` and reason `schema_declares_different_properties`.

K02. Truly *unmapped* label remains `abstain` with `schema_label_unmapped`; do not hallucinate an alias.

K03. A disputed/revoked/retired mapped property remains non-positive, and does not accidentally turn into a declared distinct-active-property refusal.

K04. A valid explicit shared canonical property remains a `schema_candidate`, with no issuer authority, semantic verification, supersession or mutation.

K05. Structural, signature, scope and subject refusals keep their existing precedence.

K06. Positive and negative result receipts still preserve `issuer_authorized=false`, `identity_verified=false`, `can_supersede=false`, `authority_effect=none`, `mutates_memory=false`. Caller-supplied pins do not authenticate the schema owner.

K07. No inference, production runtime changes, baseline-v7 promotion, R6/#732 holdout consumption or controller changes.

## Acceptance

Implement the smallest precise classification fix and independent synthetic tests on the main-based hotfix branch. Run exact-head CI and seek independent adversarial qualification before merge. Do not silently infer trust from a signature. #757 remains open.
