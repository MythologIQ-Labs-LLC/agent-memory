# #757 — Explicit signed property registry qualification (J27–J41)

**Preregistered: 2026-10-08, before implementation.**
**Area:** evaluation-only schema-backed cross-write identity candidate qualification.
**Not:** production v7, learned semantic synonym inference, accepted identity merge, PAMA approval, or a scored #732 benchmark.

## Actual memory problem

Independent write-time interpretations may use different property identifiers for the SAME real-world property. String comparison alone cannot link them. Conversely, shared labels across unrelated subjects, contexts or schemas cannot prove identity. We need an independently managed **versioned property ontology** that can declare explicit label-to-property equivalence without relying on the same extractor call that generated the proposed change.

## Candidate contract

An exact, bounded, versioned property-registry manifest describes:
- tenant, scope, purpose, schema ID, schema revision, and an externally managed issuer key reference;
- canonical property identities with enumerated **exact label references**, optionally multiple labels for one property;
- each property's state: active, disputed, retired or revoked;
- unique labels across property identities; no transitive/implicit alias expansion;
- canonical, deterministic serialization and a **domain-separated detached Ed25519 signature**, using Agent Memory's existing temporal signing primitives.

The caller provides a public key and externally pinned *key-material digest*, expected issuer key reference and exact schema revision, tenant, scope, purpose, and schema ID. The verifier checks these distinct boundaries but cannot authenticate the independent configuration channel or decide whether a property ontology is truthful. No automatic trust comes from an embedded key or the registry's claims.

A proposed cross-write pair is eligible for a **schema-backed property-identity candidate** ONLY if both supplied property labels appear under exactly one active canonical property identity in the same validated/pinned manifest, both subjects match **exactly**, and the existing structural preflight does not refuse the update. Otherwise abstain/refuse. A candidate is NOT a final same-property verdict. Source, actor, provenance, cardinality, transaction head and applicability remain separate gates.

## Preregistered safety claims

| ID | Invariant |
| --- | --- |
| J27 | No string similarity, stemming, model cue, value equality, or benchmark-specific alias lookup. Only explicit author-maintained mappings count. |
| J28 | Every alias belongs to exactly one property; alias collisions, duplicate canonical properties and malformed shapes are refused. |
| J29 | Manifests and signatures bind schema ID, revision, tenant, scope, purpose, all alias bindings and property states. |
| J30 | Verification requires separately expected schema identity/version/scope and independently pinned public key material and issuer key reference. |
| J31 | Mismatched key, signature, pin, scope, revision, schema ID or protocol version produces NO linked candidate. |
| J32 | Revoked, disputed or retired property definition cannot authorize a current candidate; past audit history remains external. |
| J33 | Equal property labels and values on different subjects do not establish identity continuity. |
| J34 | Differently named labels mapped to one canonical property MAY produce a *candidate*, but `identity_verified=false` and `can_supersede=false` remain invariant. |
| J35 | Missing labels, labels in different canonical properties, or missing independently configured registry abstain; no fallback lexical heuristic. |
| J36 | Cross-tenant, scope/purpose, unresolved lifecycle or multi/coexistent cardinality never becomes an exclusive state change through this registry. |
| J37 | Property registry authenticity DOES NOT establish issuer *organizational authorization*, source/actor trust, event truth, property semantic correctness, currentness or permission. |
| J38 | One claimed signature, hash chain or ontology statement cannot retrospectively prove independently extracted fact identity. |
| J39 | Determinism, bounded input counts, exact types, stable canonical order, no surprise Unicode or mutable collection state. |
| J40 | No runtime, baseline, PAMA, memory or benchmark mutation; evaluation-only receipt is immutable and non-authoritative. |
| J41 | Forged but consistently re-signed schema + attacker-owned pin may appear cryptographically valid. The untrusted pin channel must remain explicit in any result. |

## Independent negative controls, fixed before code

Author synthetic opaque schema/property IDs separate from #732/MESA and the 212 deliberate slot-drift examples. Test: different labels within one schema property; unrelated property with same value; same label in different subjects; label collision; unknown/absent label; swapped aliases to different properties; revoked/disputed property; wrong schema version, scope, tenant and key; tampered manifest, forged key, pinned wrong key; cross-source and actor claims; inexact/Unicode labels; generic structural refusal; self-issued signed but attacker-pinned registry; repeatability; no state changes. No new score thresholds.

## Alternative and end-state tradeoff

An explicitly authored registry supplies **deterministic semantic IDs when upstream schema ownership exists**. It cannot solve free-form language or legacy data lacking those IDs without an authorized external property-resolution process. That is a legitimate partial capability, not a hidden case-based synonym rule. The remaining options are separately verified crosswalk issuers, explicit owner-assisted correction, and provider-assisted *untrusted proposals*. The default remains abstention.

If this qualification passes, it only validates a schema-backed **candidate mechanism**. Next steps require a trusted configuration/root distribution contract, revocation and registry migration, independent adversarial design review, resolved source/actor/subject identity, and a versioned baseline successor before production. The frozen R6 holdout must not become development data.
