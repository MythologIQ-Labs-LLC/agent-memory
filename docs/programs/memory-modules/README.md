# Memory Component Capability Program

This program turns Agent Memory's representation-neutral doctrine into configurable component/capability contracts, executable adapters, and version-bound qualification evidence.

## Core model

```text
component identity != capability identity

one component -> many capabilities
one capability -> many candidate implementations

configured capability != qualified capability
qualified old version != qualified new version
qualification evidence != authority
```

Capability roles such as graph, vector, GraphRAG, lifecycle, procedural memory, structural reasoning, storage, exact retrieval, multimodal memory, or learned representation are not mutually exclusive product classes.

## Current artifacts

- [`first-party-capability-inventory.md`](first-party-capability-inventory.md) — evidence-bounded EvolveAI and CodeGenome capability/maturity map.
- [`capability-vocabulary.md`](capability-vocabulary.md) — representation-neutral capability vocabulary.
- [`external-capability-frontier.md`](external-capability-frontier.md) — historical external-system mapping and gap classification.
- [`external-capability-frontier-refresh-2026-08-14.md`](external-capability-frontier-refresh-2026-08-14.md) — current release/license/capability refresh for the next qualification wave.
- [`implementation-lane-selection.md`](implementation-lane-selection.md) — why governed procedural/skill memory was selected as the first product-shaped fabric proof.
- [`component-adapter-qualification-contract.md`](component-adapter-qualification-contract.md) — #298 research conclusion defining declaration vs adapter invocation vs earned qualification evidence.
- [`component-qualification-runtime.md`](component-qualification-runtime.md) — executable #300 qualification schema, applicability binding, maturity progression, matched fixture, and real-provider CI behavior.
- [`../runtime-evidence/procedural-memory.md`](../runtime-evidence/procedural-memory.md) — executable #295 evidence for capability routing, governed skill lifecycle, action-authority separation, and metamemory refusal.

## Current doctrine decisions

- **ADR-033 Accepted:** capability identity/maturity is independent from component identity and overlapping implementations are composed or selected deterministically.
- **ADR-034 Accepted:** procedural/skill memory is governed retained state, not standing execution authority.
- **No new ADR for #298/#300:** version-bound adapter/qualification evidence is an implementation/conformance specialization of existing doctrine unless real adapters expose a doctrine-level contradiction.

## Executable capability fabric already earned

PR #297 implemented the reusable capability declaration and deterministic routing layer:

```text
machine-readable component capability declaration
        |
        v
minimum maturity + posture requirement
        |
        v
deterministic provider resolution
        |
        +-- no eligible provider -> explicit failure
        +-- ambiguous providers -> explicit failure
        +-- configured eligible preference -> deterministic selection
        |
        v
selected implementation
```

Selection never grants memory mutation or recall permission. Fallback cannot silently lower minimum maturity or required scope posture.

## Executable qualification layer now in implementation

PR #302 / issue #300 implements the next layer:

```text
selected capability implementation
  -> versioned adapter/result boundary
  -> raw provider result preserved
  -> provider-neutral factual normalization
  -> qualification profile checks
  -> exact applicability digest
  -> earned capability maturity
```

The machine-readable evidence surface is:

`schemas/component-capability-qualification.schema.json`

The reference runtime is:

- `reference/agentmem_ref/qualification.py`
- `reference/agentmem_ref/code_graph_qualification.py`
- `reference/run_component_qualification.py`

Qualification applicability binds exact component, implementation, capability, adapter, profile, fixture, and material runtime/configuration identity. Version/configuration drift does not silently inherit prior qualification.

The maturity model now distinguishes:

```text
maturity_before
profile_maturity_ceiling
earned_maturity
```

This allows real evidence to advance a capability from `runtime_wired` to `evidence_proven` while preventing a bounded profile from accidentally claiming `reference_qualified`.

The load-bearing separations remain:

```text
selected component != authorized consequence
component result != canonical Agent Memory state
component success != capability conformance
maturity claim != executable proof
adapter normalization != evidence laundering
qualification != standing authority
```

## Governed procedural-memory reference slice

The first concrete product workload is already merged:

```text
procedure proposal
  -> PAMA-governed promotion
  -> durable scoped/versioned skill
  -> later-session retrieval candidate
  -> governed admission/activation
  -> plan influence
  -> separate runtime action proposal
  -> separate action governance
  -> separate execution evidence
```

The slice proves correction/supersession, exact-content approval binding, stale replay refusal, cross-project admission refusal, revocation/residue honesty, and metamemory self-authorization refusal.

## First deterministic portability proof

The first common qualification profile uses two real local code-graph providers:

```text
CodeGenome
Graphify
```

Current exact pins:

- CodeGenome `43a6b7147ec78ec5c616723fa1dd30f342174860`
- Graphify `v0.9.43` / `7281f27eac568f77f50910f59f84543458f5dfd1`

The CodeGenome qualification pin was deliberately advanced after the adversarial fixture exposed another file-identity defect in semantic resolution. CodeGenome #12 / PR #13 fixed file-scoped symbol and caller-span resolution and merged as `43a6b7147ec78ec5c616723fa1dd30f342174860`.

The matched fixture is deliberately adversarial:

```text
v1 main.rs
  leaf              line 1
  middle            line 5
  top               line 9

v1 decoy.rs
  middle            line 5
  decoy_leaf        line 12

v2 main.rs
  middle            line 5
  top               line 9
  replacement_leaf  line 13
```

The duplicate `middle` line forces file-bound target identity. The distinct leaf lines expose decoy contamination and stale v1 relationships.

The first currentness proof uses an explicit full rebuild between v1 and v2. It does not pretend incremental update semantics have been proven.

The Graphify normalizer reads the provider's native NetworkX node-link `links` collection. The matched result intentionally contains no scalar winner and cannot promote unrelated capabilities.

## Qualification maturity interpretation

```text
declared
implemented
runtime_wired
evidence_proven
reference_qualified
```

`evidence_proven` means an exact-version qualification record reproduced the claimed capability behavior against an explicit workload/fixture.

`reference_qualified` additionally requires the complete applicable Agent Memory conformance profile, including all required negative paths. It is capability-specific, version-specific, adapter/profile-specific, and not a repository-wide badge.

The first CodeGenome/Graphify code-graph profile is capped at `evidence_proven` until the broader failure/fallback profile is implemented and passes.

## Work tracking

- #274 — capability-oriented memory component program
- #275 — initial adversarial first-party/external comparison, completed
- #280 — broader component/capability runtime contract and routing fabric, open
- #287 — machine-readable capability maturity declarations, completed by PR #297
- #290 — capability-based routing and overlap resolution, completed by PR #297
- #292 — EvolveAI capability qualification, open
- #293 — broader CodeGenome capability qualification, open
- #295 — governed procedural/skill memory reference vertical slice, completed by PR #297
- #298 — executable component adapter and version-bound qualification research, completed
- #300 — common adapter + qualification harness and first real two-provider proof, implementation active in PR #302
- #282 — restart-safe runtime and end-to-end acceptance harness

## First-party pressure

### EvolveAI

Current planning pin:

`7cd42412ceed2ab638249a1517b2a6dac46f1312`

Open EvolveAI #19 means L3 live removal currently lacks an explicit delete/tombstone operation in the hash-chain ledger. Until repaired and re-qualified:

```text
live L3 removal
!= reconstructable audited delete
!= complete Agent Memory forgetting
```

This caps strong deletion/audit/persistence qualification claims.

### CodeGenome

Current qualification pin:

`43a6b7147ec78ec5c616723fa1dd30f342174860`

The initial #275 file-identity and traversal-direction defects were repaired before qualification. PR #302 then exposed a remaining semantic-resolver collision, which was repaired by CodeGenome #12 / PR #13 before the qualification pin advanced. These are permanent executable regression requirements rather than historical bug-tracker trivia.

## Current portfolio conclusion

No new proprietary memory subsystem is justified by the current gap analysis.

EvolveAI and CodeGenome remain broad multi-capability first-party subsystem candidates. Their overlapping graph/vector capabilities should be qualified and composed by capability, not split merely to remove implementation overlap.

The external frontier is diverse enough that a shared adapter/qualification boundary is more defensible than one shared storage ontology.

## Safeguards

```text
component != authority
capability != authority
declared capability != runtime capability
configured capability != qualified capability
provider success != Agent Memory conformance
retrieval score != recall permission
graph reachability != permission
first-party ownership != conformance
procedural memory != execution permission
approval for X != approval for modified Y
metamemory proposal != configuration authority
old qualification != new-version qualification
matched capability result != universal product winner
```

New proprietary subsystems should be created only after capability inventory and executable external comparison establish a real gap that cannot be cleanly satisfied by extending EvolveAI or CodeGenome, composing existing components, implementing generic semantics in Agent Memory core, or adopting/wrapping an external implementation.
