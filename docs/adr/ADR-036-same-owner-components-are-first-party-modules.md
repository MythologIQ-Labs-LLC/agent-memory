# ADR-036: Same-Owner Components Are First-Party Modules, Not Attributed Providers

## Status

Accepted

Supersedes the reuse posture recorded for same-owner components in [`08-source-material-index.md`](../08-source-material-index.md). Refines, and does not weaken, the role mappings in [ADR-035](ADR-035-agent-memory-is-a-governed-cognitive-framework.md) and [`39-implementation-ownership-map.md`](../39-implementation-ownership-map.md).

## Context

Agent Memory owns its architectural contracts. [ADR-035](ADR-035-agent-memory-is-a-governed-cognitive-framework.md) names implementation candidates for several of them, and earlier versions of [`39-implementation-ownership-map.md`](../39-implementation-ownership-map.md) recorded ownership splits such as *"Reality Graphs | Agent Memory contract; CodeGenome candidate implementation"*.

Several of those candidates are owned by the same party that owns Agent Memory. `MythologIQ-Labs-LLC` owns CodeGenome, EvolveAI, GG-CORE/COREFORGE, FailSafe, and Agent Memory itself.

The documentation previously treated some same-owner systems with the caution owed to third-party sources. [`08-source-material-index.md`](../08-source-material-index.md) recorded independent-synthesis and notice language for CodeGenome and EvolveAI even though the same copyright holder controls the repositories. Boundary tables also placed them alongside genuinely external providers.

That framing produced two concrete misreadings:

1. **"X implements Y" read as "Y belongs to X."** A reader encountering "CodeGenome is the initial first-party implementation of the Code Reality Graph" could conclude that the Code Reality Graph was external to Agent Memory rather than an Agent Memory capability with implementation ancestry in CodeGenome.
2. **Reuse treated as constrained when it is not.** A license grant governs licensees; it does not prevent the common owner from moving or adapting its own work between repositories.

A third misreading became visible later:

3. **"First-party module candidate" read as "permanent runtime dependency."** The fact that EvolveAI, CodeGenome, or COREFORGE contains a useful implementation does not mean Agent Memory should forever call that repository at runtime. For generic memory capabilities, the preferred end state is native Agent Memory ownership after the useful mechanism has been inspected, validated, and absorbed.

The owner has determined that same-owner components may be adopted wholesale, without restriction, and referenced within Agent Memory as Agent Memory modules.

## Decision

**A component owned by the same party as Agent Memory is a first-party module candidate, not an attributed provider.**

Concretely:

1. **Adoption is unrestricted.** Code, structure, design, fixtures, algorithms, and other owned implementation material from a same-owner component may be adopted into Agent Memory. No independent-synthesis preference, notice ceremony, or provider-bound reuse posture applies between repositories with a common owner.

2. **Naming is Agent Memory's.** Once adopted, generic work is named for the Agent Memory contract it implements, not for the repository it came from. CodeGenome-derived generic graph/retrieval work becomes Agent Memory functionality. EvolveAI-derived lifecycle/metabolism work becomes Agent Memory functionality. Origin remains available through lineage records where useful.

3. **The test is ownership, not license.** A same-owner component qualifies for this first-party adoption rule because the copyright holder controls both works. This does not change third-party obligations embedded inside either repository.

4. **Lineage remains recorded; attribution obligation does not.** [`40-aligned-projects-and-intellectual-lineage.md`](../40-aligned-projects-and-intellectual-lineage.md) and [`08-source-material-index.md`](../08-source-material-index.md) continue to record where ideas and mechanisms came from because provenance has engineering value. That is lineage, not a requirement to expose the originating repository as the runtime module name.

5. **First-party ancestry does not imply permanent runtime dependency.** For generic memory capabilities, the preferred architecture is:

```text
same-owner prior implementation
    -> inspect / validate / harvest
    -> native Agent Memory implementation
    -> downstream products consume Agent Memory
```

An ancestor repository may remain independently useful, but Agent Memory must not require it at runtime merely because the mechanism was first built there.

6. **Specialized domain sources may remain external to the native core.** A same-owner system may continue to produce domain-specific observations after its generic mechanisms have been absorbed. CodeGenome is the important example: it may remain an excellent code-intelligence/reality producer while Agent Memory owns generic graph, vector, causal, provenance, and retrieval machinery.

7. **Product runtimes should reverse the dependency when Agent Memory reaches capability parity.** COREFORGE historically contains/emulates several generic memory mechanisms. The desired direction is for COREFORGE to consume Agent Memory for those generic capabilities while retaining product-specific UX, inference adapters, packaging, caches, encryption, and orchestration as appropriate.

### Scope

**Covered and mapped by the owner:**

| Component | Agent Memory relationship / destination |
|---|---|
| CodeGenome | first-party implementation ancestry; generic graph/vector/retrieval/evaluation mechanisms may be absorbed into Agent Memory; CodeGenome may remain a code-domain observation source |
| EvolveAI | first-party implementation ancestry; lifecycle, metabolism, vector, temporal, consolidation, pruning, and failure-memory mechanisms may be absorbed into native Agent Memory modules |
| COREFORGE Vault / Neurospace | first-party product/runtime ancestry; useful generic memory mechanics may be absorbed, with COREFORGE becoming a downstream Agent Memory consumer for those capabilities |
| FailSafe / Arbiter | same-owner governance/evidence ancestry or peer depending on the bounded surface; does not become PAMA's semantic owner |
| GG-CORE | same-owner compute substrate; no generic memory ownership follows from common ownership |

**Explicitly not covered.** This ADR changes nothing for genuinely third-party components. UOR Framework, Graphiti, Hindsight, MemOS, and other third-party systems retain their own source-rights posture and qualify through the appropriate external interoperability/provider path with `authority_effect: none` where applicable.

## Runtime ownership consequence

This ADR now makes the runtime consequence explicit because the older language was too easy to misread.

For generic memory machinery:

```text
implementation ancestry
    != runtime service boundary

useful mechanism in EvolveAI / CodeGenome / COREFORGE
    != Agent Memory must call that repo forever
```

Agent Memory owns and should natively implement, as capability maturity permits:

- semantic/vector retrieval;
- exact/lexical/relational/temporal/graph retrieval;
- lifecycle/metabolism;
- decay/reinforcement/consolidation/pruning;
- provenance/currentness/correction/forgetting semantics;
- context-assembly semantics;
- PAMA and recall admission;
- continuous memory evaluation and regression evidence.

The migration may be incremental. During transition, a same-owner repository can still act as a test oracle, migration source, compatibility seam, or specialized producer. That temporary seam does not redefine the destination architecture.

## CodeGenome boundary

The Code Reality Graph distinction requires special care.

Agent Memory owns the generic Reality Graph framework and memory machinery. CodeGenome may continue to own the specialized problem of observing and modeling code reality in its own product/domain.

Valid continuing shape:

```text
CodeGenome code-domain observations / evidence
    -> Agent Memory Reality Graph / memory machinery
```

Not the intended generic dependency:

```text
Agent Memory graph/vector/retrieval machinery
    -> requires CodeGenome runtime
```

This preserves specialization without outsourcing Agent Memory's fundamentals.

## EvolveAI boundary

EvolveAI remains valuable implementation ancestry and a behavioral test oracle for vector retrieval, temporal graph behavior, tier routing, decay, reinforcement, consolidation, pruning, REM-style synthesis, crystallization proposals, restart behavior, and negative/failure-memory concepts.

Once those generic mechanisms are absorbed, they are Agent Memory capabilities and should not retain an EvolveAI-shaped runtime boundary unless a deployment has a separate, explicit reason to choose one.

## COREFORGE boundary

COREFORGE historically contains a product-level memory implementation with Vault/Neurospace, context brokerage, memory domains, graph recall, mutation/lineage mechanics, and provider composition.

That code is valuable ancestry. The end-state dependency direction is:

```text
Agent Memory
    -> consumed by COREFORGE
```

rather than treating COREFORGE Vault as the permanent canonical memory container for Agent Memory.

## Consequences

**Positive.**

- Generic memory capabilities have one coherent ownership destination.
- Useful first-party work can be harvested without artificial provider boundaries.
- CodeGenome can remain excellent at code intelligence without becoming Agent Memory's generic graph/vector runtime.
- COREFORGE can simplify over time by delegating generic memory capability to Agent Memory.
- The two common misreadings become structurally harder: ownership and maturity remain separate, while ancestry no longer looks like permanent service topology.
- Qualification machinery remains focused on genuinely external components and interoperability claims.

**Costs, accepted.**

- Native absorption requires migration work, tests, and regression evidence. Renaming a mechanism is not absorption.
- Some historical provider/profile modules may become migration or evidence-only surfaces and eventually need deprecation.
- Downstream products may temporarily carry duplicate memory machinery while Agent Memory reaches parity and proves the replacement.
- If ownership of any covered component changes, source-rights and classification must be revisited.

**Neutral.**

- Provider-neutral code that also serves genuinely external systems may remain provider-neutral. For example, a module that handles both same-owner CodeGenome evidence and third-party Graphify evidence does not become invalid merely because CodeGenome's generic mechanisms are now treated as first-party ancestry.
- A specialized system can remain independently maintained even after Agent Memory absorbs broadly useful mechanisms from it.

## Maturity rule

Common ownership does not prove capability quality.

```text
same owner
    != implemented
    != runtime wired
    != evidence proven
    != production mature
```

After absorption, maturity is earned through native Agent Memory tests, runtime evidence, restart/currentness/deletion/scope behavior, benchmarks where appropriate, and the repository's normal evidence discipline.

## Related

- [ADR-035](ADR-035-agent-memory-is-a-governed-cognitive-framework.md) - role mappings and the contracts Agent Memory owns
- [`05-repo-implementation-map.md`](../05-repo-implementation-map.md) - implementation ancestry and relationship map
- [`39-implementation-ownership-map.md`](../39-implementation-ownership-map.md) - canonical ownership and current native posture
- [`40-aligned-projects-and-intellectual-lineage.md`](../40-aligned-projects-and-intellectual-lineage.md) - lineage and external alignment
- [`43-substrate-inventory-and-maturity.md`](../43-substrate-inventory-and-maturity.md) - concrete runtime/substrate maturity
- [`SOURCE_RIGHTS_POLICY.md`](../SOURCE_RIGHTS_POLICY.md) - reuse posture for genuinely external sources
- Issue #455 - ownership reconciliation
- Issue #456 - first native semantic/vector retrieval harvest slice
