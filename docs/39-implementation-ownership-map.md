# Implementation Ownership Map

## Purpose

[`05-repo-implementation-map.md`](05-repo-implementation-map.md) records how related systems contribute implementation ancestry, domain evidence, optional interoperability, verification, or downstream consumption.

This document answers the ownership question directly:

> **Who owns the generic memory capability after useful prior work is harvested?**

The answer is Agent Memory.

```text
implementation ancestry
    !=
permanent runtime ownership

proven mechanism in another first-party repo
    -> inspect / validate / harvest
    -> native Agent Memory implementation
```

The exhaustive known-source harvest closeout is recorded in:

```text
docs/52-harvest-closeout-final.md
reference/fixtures/harvest-closeout-final-v1.json
```

Those artifacts supersede the earlier wave-1 and wave-2 harvest summaries as the current closeout view.

## Ownership vocabulary

```text
native-owned
    Agent Memory owns the generic contract and implementation surface.

ancestry
    prior work contains useful implementation mechanisms or evidence.

specialized-domain-source
    a system may continue producing domain-specific observations or projections.

optional-peer
    a system may provide identity, verification, evidence, or enforcement without owning memory semantics.

downstream-consumer
    a product consumes Agent Memory while retaining product-specific concerns.

implemented
    native executable Agent Memory implementation exists.

bounded
    implementation exists and is qualified for a stated profile without implying universal production maturity.
```

Maturity and ownership remain separate. Declaring Agent Memory the owner does not erase evidence limits.

## Canonical ownership map

| Component | Canonical owner | Implementation ancestry / peers | Continuing specialized consumers or sources | Current posture |
|---|---|---|---|---|
| Identity contract | **Agent Memory** | UOR lineage; CodeGenome identity patterns | any runtime or domain module | native-owned; optional exact-identity interoperability |
| Evidence and provenance | **Agent Memory** | CodeGenome provenance; COREFORGE lineage; external trust/evidence peers | all memory types and downstream products | native-owned and implemented |
| Semantic / exact / relational retrieval | **Agent Memory** | EvolveAI and CodeGenome retrieval ancestry | downstream products | native-owned and implemented |
| Semantic/vector retrieval | **Agent Memory** | EvolveAI vector retrieval; CodeGenome embedding/kNN ancestry | domain sources may supply observations | native-owned and implemented through #456 / #458 |
| Temporal / entity / causal graph traversal | **Agent Memory** | EvolveAI temporal graph; CodeGenome traversal/overlays | CodeGenome may supply code-domain graph observations | native-owned and implemented through #461 / #462 |
| Reality Graph framework | **Agent Memory** | CodeGenome implementation ancestry | specialized domain graph sources | native-owned; generic relation behavior is Agent Memory responsibility |
| Lifecycle / Cognitive Metabolism | **Agent Memory** | EvolveAI decay, reinforcement, consolidation and prune pressure; COREFORGE lifecycle ancestry | downstream products | native-owned and implemented through #463 / #464 |
| Saturation / decay / reinforcement | **Agent Memory** | EvolveAI CMHL-style mechanisms and experiments | memory modules | native-owned; governed native metabolism implemented |
| **PAMA** | **Agent Memory** | same-owner enforcement lessons; external policy peers | every mutating component | **native-owned and implemented** |
| Certification / review evidence | **Agent Memory contract** | optional verification/enforcement peers | governance consumers | native-owned contract; peer evidence remains bounded |
| Runtime memory space | **Agent Memory** | COREFORGE Vault/Neurospace ancestry | COREFORGE, Cortera, TARA, agents | native-owned; bounded canonical runtimes/substrates qualified |
| Context assembly semantics | **Agent Memory** | COREFORGE broker/packet ancestry | downstream presentation/orchestration | native-owned; composed retrieval plus developer facade and end-to-end lifecycle implemented through #478 / #480 |
| Correction / dispute / supersession | **Agent Memory** | prior product workflows as ancestry | all consumers | native-owned and implemented |
| Durable decision memory | **Agent Memory** | product implementations may consume profile | decision-oriented products/agents | native-owned profile |
| Negative / failure memory | **Agent Memory** | EvolveAI ShadowGenome concepts | downstream risk/planning consumers | native-owned and implemented through #473 |
| Continuous memory evaluation | **Agent Memory** | CodeGenome experiment-loop ancestry; UOR/PrismPM mutation-detection lessons | CI/release/benchmark consumers | native-owned; continuous regression, comparison harness and evaluator mutation probes implemented |
| Conformance | **Agent Memory** | PrismPM and Foundry as external verification pressure | every implementation | native-owned evidence discipline; external verification remains optional |

## PAMA ownership

PAMA's canonical semantics and runtime implementation are Agent Memory responsibilities.

Canonical sources include:

- [`pama/README.md`](pama/README.md)
- [`04-governance-and-pama.md`](04-governance-and-pama.md)
- [`33-pama-decision-table.md`](33-pama-decision-table.md)
- [`ADR-004`](adr/ADR-004-pama-controls-mutation-authority.md)

A downstream product or enforcement peer may host additional controls, but no external product becomes PAMA's semantic owner.

A PAMA boundary must preserve at least:

```text
M0-M5 target class
lifecycle strength
requested operation
A0-A5 downstream authority
actor and charter
scope and reversibility
evidence and uncertainty
policy version
permitted / prohibited outcomes
selected action
committed consequence receipt
```

PAMA must remain distinguishable from relevance, similarity, confidence, saturation, storage success, or implementation convenience.

## First-party absorption rule

Same-owner ancestry is not a permanent service dependency.

```text
same-owner component has useful generic mechanism
    -> Agent Memory may adopt it directly
    -> native Agent Memory module owns the resulting generic capability
    -> originating repo need not remain installed or invoked at runtime
```

Lineage remains valuable. Cross-repository runtime dependency is not the destination by default.

## EvolveAI disposition

EvolveAI remains implementation ancestry and behavioral/test pressure for capabilities including vector representation/retrieval, temporal behavior, lifecycle/metabolism, consolidation, pruning pressure, exact recall, negative/failure memory, and restart behavior.

The generic end-state owner of those capabilities is Agent Memory.

An EvolveAI estimator may still be useful in experiments or optional specialized deployments. Its score or proposal cannot become memory authority merely because the mechanism originated in first-party code.

## CodeGenome disposition

CodeGenome has two distinct relationships.

### Implementation ancestry

Generic graph traversal, relation propagation, retrieval pressure, provenance lessons, and continuous experiment/regression discipline have been evaluated and either absorbed or explicitly rejected where inappropriate.

### Specialized domain evidence source

CodeGenome may continue to produce code-domain observations, structural relationships, impact evidence, or code-specific projections.

```text
CodeGenome observes code reality
    -> Agent Memory ingests/evaluates domain evidence
```

This does not mean Agent Memory must call CodeGenome for generic graph memory, vector retrieval, causal traversal, or evaluation.

## COREFORGE Vault / Neurospace disposition

COREFORGE contains valuable product-level memory ancestry, including historical code for lifecycle storage, memory domains, source/reference objects, context brokers, graph recall, RAG/context assembly, mutation gating, lineage, and provider composition.

The older transition map treated that code as a candidate owner for Runtime Memory Space and Context Assembly. That is no longer the desired dependency direction.

```text
historical:
COREFORGE contains/emulates generic memory machinery

end state:
Agent Memory owns generic memory machinery
COREFORGE consumes Agent Memory
```

COREFORGE may continue to own product-specific concerns such as UI, inference adapters, local application orchestration, encrypted product packaging, or caches.

## UOR disposition

UOR remains optional exact-identity/interoperability lineage and a source of useful verification pressure.

Agent Memory owns the identity boundary and may use UOR-derived or UOR-compatible mechanisms where useful.

```text
UOR/exact reference
    !=
memory lifecycle
    !=
retrieval authority
    !=
PAMA
```

The reviewed UOR ecosystem now has explicit dispositions in the final harvest matrix:

- UOR Framework and `uor-addr`: optional identity interoperability;
- `uor-r4`: predictive geometry not adopted, keyed-rebinding/currentness benchmark lesson absorbed;
- `uor-foundry`: generic authority/evidence-honesty lessons absorbed, broader release machinery specialized;
- `uor-jcs-nfc`: canonicalization profile not adopted from the provisional RC5 source, mutation-sensitivity lesson absorbed into benchmark integrity probes;
- `uor-matmul`: no generic memory gap identified.

See [`ADR-001`](adr/ADR-001-uor-is-identity-not-memory.md).

## PrismPM disposition

PrismPM has now been reviewed as a verification/conformance peer rather than left as a candidate placeholder.

Exact reviewed revision:

```text
73d041a46a4e15127e7fdef1dc16a8d592c5ccd3
```

Useful generic lessons:

- authority/source bindings remain distinct from executable verification oracles;
- locked resolution refuses drift rather than guessing compatibility;
- positive and negative corpora plus mutation pressure should expose stale, bypassed, changed, or trivially passing verification.

Agent Memory already owns the first two boundaries through source qualification, runtime configuration, estimator evidence and PAMA. The mutation-detection lesson is now absorbed through [`51-benchmark-integrity-mutation-probes.md`](51-benchmark-integrity-mutation-probes.md).

PrismPM's complete release graph, self-rebuild, compiler, deployment and publication machinery remains specialized release engineering. It is not ordinary recall machinery and does not become a memory semantic owner.

## External governance / trust peer disposition

Microsoft Agent Governance Toolkit remains optional enforcement/policy interoperability.

AgentTrust TRACE remains optional action/trust evidence with file-class source-rights preserved. TRACE evidence is not memory authority.

Agent Manifest remains optional deployment/checkpoint evidence. Qualified checkpoint acceptance does not substitute for Agent Memory-owned semantic binding of memory operations.

cMCP remains optional call-boundary evidence. Historical 0.4.0 evidence is retained and 0.5.0 is separately qualified. Neither release becomes a runtime owner or authority source for generic memory semantics.

## Harvest closeout

Issue #470's known-source harvest is complete at the snapshot recorded by:

```text
reference/fixtures/harvest-closeout-final-v1.json
```

The closeout means:

1. every materially useful generic mechanism identified in the reviewed source set is absorbed or has an explicit disposition;
2. every non-adoption has a technical, evidence, scope, specialization, or source-state reason;
3. generic memory does not depend at runtime on EvolveAI, CodeGenome, or COREFORGE;
4. optional peers do not gain recall-admission or mutation authority;
5. future upstream changes create new bounded reviews instead of keeping this historical harvest permanently open.

## Benchmark integrity lesson

The final harvest produced one new generic evaluation mechanism:

```text
reference/run_benchmark_integrity_mutants.py
```

It verifies that controlled benchmark failures actually alter expected retrieval metrics. The current probes cover admitted noise, missing gold edges, candidate/admission collapse, ranking damage, and final-admission refusal.

```text
mutation probe pass
    !=
retrieval efficacy
    !=
external comparability
    !=
memory authority
```

Real-world benchmark work continues independently under #467, #388, and #408.

## Historical inspection record

**2026-08-11.** EvolveAI, CodeGenome, GG-CORE, and COREFORGE were inspected at pinned revisions. That inspection established real implementation ancestry:

- COREFORGE Vault/Neurospace existed as code with lifecycle storage, mutation gates, context assembly, graph/RAG behavior, references, lineage, and provider seams.
- EvolveAI and CodeGenome were consumed inside COREFORGE through memory-provider interfaces.
- GG-CORE was a compute dependency rather than a memory successor.

Those findings remain valid evidence about historical implementation state. They no longer establish end-state ownership.

## Native implementation evidence rule

Once a mechanism is absorbed, maturity is earned as ordinary Agent Memory implementation evidence rather than same-owner provider qualification.

A native capability should be able to show, as applicable:

1. the Agent Memory contract it implements;
2. source ancestry when materially useful for reconstruction;
3. focused positive and adversarial tests;
4. currentness and correction behavior;
5. deletion/residue behavior;
6. scope/isolation behavior;
7. restart/rebuild behavior;
8. estimator/version bindings where probabilistic representation is involved;
9. authority effect;
10. benchmark/regression evidence appropriate to the capability.

Ownership is not maturity. A native module can still be experimental, bounded, or wrong.

## Current execution direction

The generic harvest sequence is complete through native retrieval, graph traversal, metabolism, negative/failure memory, continuous regression, and benchmark-integrity pressure.

The next development direction is no longer to preserve ancestry service seams. It is to improve empirical quality and cognitive classification while keeping the native ownership boundary intact.

```text
native memory substrate and governance
    -> broader real-world benchmarking
    -> governed cognitive-classification provider seam
    -> downstream product adoption
```

## Doctrine

Ownership is a governance and architecture fact, not merely a deployment fact.

Agent Memory defines and implements its generic memory capabilities. A related repository can contribute excellent prior art, specialized observations, or optional peer functionality without remaining the canonical runtime owner.

Code that proves a useful mechanism is valuable ancestry. The destination is a coherent Agent Memory system, not a permanent museum of internal service boundaries.
