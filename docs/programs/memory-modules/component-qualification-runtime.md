# Component Capability Qualification Runtime

Status: **Implementation evidence / #300**

Tracks: #300, #280, #293

## Purpose

This document describes the executable qualification surface implemented by PR #302. It is the runtime counterpart to [`component-adapter-qualification-contract.md`](component-adapter-qualification-contract.md).

The contract now has code behind it:

```text
component declaration
  != qualification evidence

provider-native output
  -> preserved raw artifact
  -> provider-neutral factual normalization
  -> profile checks
  -> version-bound qualification record
  -> earned capability maturity
```

Qualification remains evidence only. It grants no Agent Memory mutation, structural, recall-admission, or action authority.

## Machine-readable evidence surface

Schema:

`schemas/component-capability-qualification.schema.json`

Reference implementation:

`reference/agentmem_ref/qualification.py`

The qualification subject binds:

```text
component_id
component_version
exact implementation_ref
capability_id/version
adapter_id/version
qualification_profile_id/version
```

Runtime applicability additionally binds:

```text
configuration digest
fixture identity + digest
material dependency refs
runtime refs
```

The deterministic applicability digest is computed over the exact subject and runtime identity. A changed component, adapter, profile, fixture, dependency/runtime identity, or material configuration does not silently inherit prior qualification.

Silence is not compatibility.

## Maturity progression

A qualification record separates three values:

```text
maturity_before
profile_maturity_ceiling
earned_maturity
```

This matters because qualification exists to establish stronger evidence than was available before the run.

A provider at `runtime_wired` may therefore earn `evidence_proven` when the profile proves the required behavior. It may not exceed the profile ceiling.

`reference_qualified` requires an explicit `reference_qualified` profile ceiling, runtime-allowed source rights, and every profile-required check to pass.

The first code-graph profile is deliberately capped at:

`evidence_proven`

It does not yet prove every failure/fallback negative path required for full reference qualification.

## Provider-neutral adapter result

Reference type:

`AdapterResult`

It binds or preserves equivalents of:

```text
exact qualification subject
operation
runtime identity
input refs
raw provider artifact refs
normalized factual result refs
currentness posture
failure result
trace/correlation ref
```

Raw provider evidence is mandatory and is not replaced by normalization.

The adapter result exposes:

`authority_effect = none`

The qualification record repeats the same invariant.

## First capability profile

Profile:

`code-graph-traversal-currentness@1.0.0`

Providers:

- CodeGenome `43a6b7147ec78ec5c616723fa1dd30f342174860`
- Graphify `v0.9.43`, commit `7281f27eac568f77f50910f59f84543458f5dfd1`

The CodeGenome pin was deliberately advanced from the planning revision `d2578729a46d495369bd7613845002d50cf20f4c` after the qualification fixture exposed a remaining cross-file semantic-resolution collision. CodeGenome #12 / PR #13 repaired symbol and caller-span resolution so file identity remains part of semantic traversal, and merged as `43a6b7147ec78ec5c616723fa1dd30f342174860`. The qualification therefore binds the repaired merged revision rather than suppressing the negative result.

The workflow validates exact source refs before execution and verifies source-rights files from those exact revisions.

The profile normalizes only shared factual call-graph behavior. It does not force the providers to emit the same native schema. Graphify's NetworkX node-link evidence uses the native `links` collection; the normalizer preserves that shape and accepts `edges` only as a compatibility fallback.

## Adversarial fixture

Fixture root:

`reference/fixtures/component-qualification/`

The fixture intentionally separates target-file identity from line identity:

```text
v1 main.rs
  leaf              starts line 1
  middle            starts line 5
  top               starts line 9

v1 decoy.rs
  middle            starts line 5
  decoy_leaf        starts line 12

v2 main.rs
  middle            starts line 5
  top               starts line 9
  replacement_leaf  starts line 13
```

The duplicate `middle` start line means a provider cannot pass target resolution by line span alone. The distinct leaf line identities make decoy contamination and stale v1 edges observable.

## Currentness posture

The first profile uses an explicit **full rebuild** between v1 and v2.

That is intentional:

```text
full rebuild proven
!= incremental refresh proven
```

The evidence must establish:

- v1 `middle -> leaf` exists;
- v2 `middle -> replacement_leaf` exists;
- the v1 `middle -> leaf` relationship is not reported as current after the v2 rebuild;
- decoy-file relationships remain isolated;
- v1 raw artifacts remain preserved as historical evidence.

If either provider later exposes a supported incremental update path, that path needs its own qualification evidence rather than inheriting the full-rebuild result.

## No product winner

The matched result contains:

```text
both_passed: <boolean>
winner: null
authority_effect: none
unrelated_capabilities_promoted: []
```

This profile answers whether two materially different providers satisfy the same bounded capability checks. It does not declare a universal product winner.

Passing `code_graph_traversal` does not promote vector retrieval, GraphRAG, MCP, confidence fusion, procedural memory, lifecycle, or any other capability.

## CI surfaces

Focused contract CI:

`.github/workflows/component-qualification-foundation.yml`

Real-provider evidence CI:

`.github/workflows/component-qualification-evidence.yml`

The real-provider workflow:

1. runs schema/normalizer tests;
2. fetches exact CodeGenome source;
3. verifies CodeGenome source rights and builds the CLI;
4. executes v1 and v2 CodeGenome qualification queries;
5. fetches exact Graphify release source;
6. verifies Graphify release and Apache-2.0 source-rights posture;
7. executes v1 and v2 Graphify code-only extraction;
8. emits the version-bound qualification report;
9. validates currentness, maturity ceiling, and authority-none invariants;
10. uploads provider-native and normalized evidence artifacts.

Repository-wide doctrine validation remains independently required before merge.

## Remaining #300 work

This slice does not close #300 by itself.

Still required before the parent issue can be considered complete:

- explicit provider-unavailable/failure qualification behavior;
- explicit no-weaker-fallback evidence;
- final docs/runtime evidence synchronization at the accepted head;
- final exact-head focused and repository-wide validation;
- any additional negative paths needed to justify a stronger maturity ceiling.

The common harness should remain reusable for #293 and later EvolveAI/general-memory-system qualification work without importing provider-specific ontology into Agent Memory core.
