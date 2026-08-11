# Security and Privacy

Persistent memory creates attack surfaces that do not exist in a stateless exchange. A memory can look harmless when written and become dangerous later when another context retrieves, combines, trusts, or acts on it.

## Threat model at a glance

Agent Memory explicitly considers:

- direct memory poisoning
- sleeper memory poisoning
- hallucination permanence
- recursive self-citation
- authority laundering through summaries or trusted tools
- provenance stripping
- cross-tenant or cross-scope leakage
- sensitive-memory extraction
- unsafe multi-memory composition
- stale authorization or expired delegation
- stochastic policy bypass
- estimator manipulation and calibration drift
- malicious correction
- irreversible deletion abuse
- deletion residue in derived state

## Write-time safety is not lifetime safety

A retained item can become unsafe when:

- its original scope changes
- a delegation expires
- a new memory creates a dangerous combination
- a summary loses provenance
- a model begins to trust a poisoned source
- an old policy is replayed after policy state changed
- a deletion request fails to propagate into derived artifacts

That is why Agent Memory places security checks across storage, recall, composition, mutation, sharing, and deletion.

## Privacy is contextual

Sensitivity may be explicit or inferred. When inferred, uncertainty must remain visible.

```text
unknown sensitivity != non-sensitive
```

Privacy decisions should consider:

- actor
- tenant
- scope
- purpose
- consent
- delegation
- sensitivity
- downstream disclosure
- derived state

Relevance cannot create access permission.

## Provenance and authority laundering

A summary, trusted tool, or higher-reputation intermediary must not silently transform low-authority content into high-authority content.

The system should preserve origin and derivation so downstream decisions can distinguish:

```text
source reliability
from
source authority
from
derived confidence
from
permission to act
```

## Deletion residue

Deletion is not complete merely because the canonical record disappeared. Controlled derived artifacts may include:

- embeddings
- search indexes
- summaries
- graph edges
- caches
- exported state
- consolidated memories

The system must state what it can actually purge and what remains outside its control.

## Security reporting

Do not publish exploit details or sensitive proof-of-concept memory in public issues. Follow the repository security policy and use private vulnerability reporting when available.

Security policy: https://github.com/MythologIQ-Labs-LLC/agent-memory/security/policy

## Canonical sources

- Threat model: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/15-memory-threat-model.md
- Source trust: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/16-source-trust-and-reputation.md
- Privacy and sensitivity: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/19-privacy-and-sensitivity-classifier.md
- Scope, consent, tenancy: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/29-actor-scope-consent-and-tenancy.md
- Retention and deletion: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/28-retention-deletion-and-tombstones.md

## Next

- **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)** for deletion semantics
- **[Conformance and Evidence](Conformance-and-Evidence)** for adversarial proof
