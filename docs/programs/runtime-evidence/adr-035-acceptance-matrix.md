# ADR-035 Acceptance Evidence Matrix

Status: **acceptance review active; one material evidence gap remains**

ADR-035 remains **Proposed**.

This matrix evaluates the acceptance requirements in [`../../adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md`](../../adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md) against current repository evidence. It is deliberately stricter than asking whether a document, fixture, or first-party project merely exists.

## Decision rule

```text
documented architecture
  != implemented mechanism
  != provider-native integration
  != capability qualification
  != doctrine acceptance
```

A requirement is marked `satisfied` only at the boundary the ADR actually names. `partial` means useful evidence exists but a material part of the claimed seam is not yet exercised directly.

## Matrix

| # | ADR-035 acceptance requirement | Status | Evidence / remaining boundary |
|---|---|---|---|
| 1 | Cognitive Mesh boundary documented without creating a universal implementation-specific ontology | **satisfied** | ADR-035 defines the mesh contract; `reference/agentmem_ref/cognitive_mesh.py` keeps `object_type` and `module_role` open rather than imposing a closed provider ontology; `docs/01-layer-model.md` explicitly states the mesh is not a ninth memory layer or universal database schema. |
| 2 | Three-plane architecture integrated consistently into canonical documentation | **satisfied in integration slice** | `docs/11-component-architecture.md`, `docs/01-layer-model.md`, and `docs/13-system-composition-boundaries.md` distinguish the three-plane topology from layer/component/capability taxonomies and preserve existing authority boundaries. This row becomes repository-main evidence only after the integration slice merges. |
| 3 | EvolveAI mapped to Cognitive Metabolism without falsely promoting unqualified capabilities | **satisfied** | ADR-035 and component/layer docs make the role mapping architectural only. Existing EvolveAI qualification remains capability/version scoped; native qualification evidence explicitly records limits such as MockEngine embedding quality, provider-native Shadow verdict not being Agent Memory authority, and incomplete transitive forgetting. |
| 4 | CodeGenome mapped to Code Reality Graph without promoting its ontology to universal memory semantics | **satisfied** | ADR-035 and composition docs constrain CodeGenome to the code-domain Reality Graph role and explicitly prohibit treating its ontology as the universal Cognitive Mesh ontology. Existing CodeGenome maturity remains independently capability scoped. |
| 5 | Module identity, component identity, and capability identity remain distinct and consistent with ADR-033 | **satisfied** | ADR-033 remains Accepted and controlling. ADR-035, the layer model, and composition docs preserve `module identity != component identity != capability identity`. |
| 6 | At least one end-to-end reference path demonstrates Cognitive Mesh identity -> Evidence/Provenance -> Cognitive Metabolism or Reality Graph processing -> candidate cognitive change -> PAMA -> commit/refusal -> governed recall -> active cognition | **partial** | #338 proves the complete Agent Memory path from a typed provider-labelled signal through PAMA, durable consequence/refusal, governed recall, and active cognition. Separately, EvolveAI has pinned native workload evidence for lifecycle orchestration and REM synthesis. The remaining gap is a direct adapter seam in which actual provider-native EvolveAI or CodeGenome output is normalized into the Cognitive Mesh `CognitiveSignal` path and carried through the governed consequence/recall loop. A provider name on a fixture is not treated as provider-native processing. |
| 7 | Adversarial path proves learned reinforcement, graph confidence, prediction confidence, or provider-native verdict cannot independently grant durable/action authority | **satisfied** | #338 focused tests and deterministic evidence show confidence `0.01` and `1.0` receive the same review-required crystallization outcome; CodeGenome-labelled graph confidence `1.0` cannot commit; predictive confidence `1.0` plus provider `PASS` cannot grant A4 action authority. |
| 8 | Module replacement or absence fails explicitly without corrupting canonical cognitive identity | **satisfied at reference boundary** | #338 proves missing provider -> `CognitiveModuleUnavailable` with zero writes, then explicit replacement commits while preserving the logical `MeshObject.object_ref` independently of the new physical fact UUID. Restart-persistent provider mapping is not claimed because the ADR requirement does not require that stronger boundary. |
| 9 | Conformance documentation distinguishes architectural acceptance from implementation maturity | **satisfied** | ADR status semantics, ADR-033 capability maturity, `docs/programs/runtime-evidence/cognitive-mesh.md`, and this matrix explicitly separate doctrine, reference evidence, native provider integration, and capability qualification. |

## Current acceptance result

```text
requirements satisfied:          7
satisfied in integration slice:  1
partial:                         1
blocking acceptance gap:         requirement 6
```

After this documentation slice merges, documentation consistency is no longer the acceptance blocker.

The remaining blocker is **native provider-to-mesh integration evidence**.

## Required next evidence slice

The smallest sufficient next slice is not another cognitive subsystem. It is an adapter boundary that consumes already-evidenced first-party provider output and emits a typed Cognitive Mesh signal.

Preferred first path: EvolveAI Cognitive Metabolism.

```text
pinned EvolveAI native workload output
  -> versioned EvolveAI Cognitive Metabolism adapter
  -> CognitiveSignal
       module_role=cognitive_metabolism
       source_component=evolveai
       signal_type=<declared metabolic proposal>
       estimator/provider refs preserved
       evidence refs preserved
       uncertainty/provider verdict preserved where present
  -> CognitiveMeshRuntime.apply_signal(...)
  -> PAMA
  -> governed durable commit or refusal
  -> governed recall
  -> active cognition
```

The adapter must prove:

1. source EvolveAI commit/version is pinned and reconstructable;
2. the selected native observation is actually produced by the provider workload, not recreated as an Agent Memory fixture;
3. normalized signal semantics are explicit;
4. provider confidence/verdict remains evidence only;
5. provider output cannot bypass PAMA;
6. logical mesh identity remains independent of provider storage identity;
7. raw provider evidence is retained alongside normalization;
8. the resulting evidence does **not** promote unrelated EvolveAI capabilities.

A CodeGenome Reality Graph adapter can follow the same pattern, but both providers are not required to accept ADR-035 if one genuinely native end-to-end path satisfies requirement 6 and the second mapping remains truthfully bounded.

## Promotion rule

ADR-035 should move to `Accepted` only after:

```text
this integration documentation is on main
+
native provider-to-Cognitive-Mesh evidence is green at an exact commit
+
requirement 6 is changed from partial to satisfied
+
repository doctrine validation passes
```

The acceptance change should be a separate, explicit promotion commit/PR. Evidence completion must not silently mutate ADR status.
