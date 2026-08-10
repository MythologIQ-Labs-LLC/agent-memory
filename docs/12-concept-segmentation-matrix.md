# Concept Segmentation Matrix

## Purpose

This matrix decides whether a concept belongs as:

1. a canonical doctrine concept
2. a component inside the larger architecture
3. an implementation detail inside a specific repo
4. a product or UX surface
5. a conformance concern

This prevents concept drift by forcing every idea to answer where it belongs before it becomes another half-remembered architecture ghost.

The matrix also prevents probabilistic estimation, authority, and committed state change from being collapsed into one concept simply because one implementation happens to place them in the same service.

## Placement rules

| Placement | Use when | Example |
|---|---|---|
| Doctrine concept | The idea affects all implementations | saturation is not truth |
| Component | The idea has distinct interfaces and failure modes | PAMA, lifecycle engine, certification gate |
| Implementation detail | The idea is repo-specific | EvolveAI REM synthesis implementation |
| Product surface | The idea affects user interaction | COREFORGE memory correction UI |
| Conformance concern | The idea must be tested across systems | access-spam trap class |

## Segmentation matrix

| Concept | Placement | Component | Canonical owner | Notes |
|---|---|---|---|---|
| UOR address | Component | Identity Substrate | UOR Framework | Stable identity, not memory policy |
| BLAKE3 content identity | Implementation plus component | Identity Substrate | UOR / CodeGenome | Used by multiple systems for deterministic identity |
| Memory unit | Doctrine concept | Lifecycle Engine | agent-memory doctrine | Shared object abstraction |
| Artifact | Doctrine concept | Identity and Evidence | agent-memory doctrine | Raw thing entering memory |
| Observation | Doctrine concept | Evidence and Provenance | agent-memory doctrine | Witnessed artifact or relation |
| Evidence bundle | Component | Evidence and Provenance | FailSafe, CodeGenome, runtime ledgers | Must survive summarization |
| Provenance | Doctrine concept | Evidence and Provenance | agent-memory doctrine | Required for durable transitions |
| Estimator provenance | Doctrine concept | Evidence and Provenance | agent-memory doctrine | Identifies model/method/version behind consequential estimates |
| Fiber | Doctrine concept | Saturation and Decay | agent-memory doctrine | Durability or relevance dimension |
| Saturation sigma | Component | Saturation and Decay | PRISM-style lifecycle consumer | Routing signal, not truth or permission |
| Decay | Component | Saturation and Decay | EvolveAI / lifecycle runtime | Reduces operational weight |
| CMHL | Implementation detail | Saturation and Decay | EvolveAI | Specific decay implementation |
| MTS | Implementation detail | Lifecycle routing | EvolveAI | Routing heuristic, not universal doctrine |
| Confidence fusion | Component | Reality Graphs / Evidence | CodeGenome | Evidence support, not permanence |
| Noisy-OR fusion | Implementation detail | Reality Graphs | CodeGenome | Specific confidence fusion method |
| Uncertainty representation | Doctrine concept | Evidence / Scoring / Governance handoff | agent-memory doctrine | Point estimates alone may hide consequential uncertainty |
| Calibration scope | Doctrine concept plus conformance | Conformance and Calibration Harness | agent-memory doctrine | Defines where an estimator claim is valid |
| Estimator disagreement | Conformance concern plus doctrine concept | Scoring / Evidence | agent-memory doctrine | Must remain visible when materially consequential |
| Abstention | Doctrine concept | Governance / Lifecycle | agent-memory doctrine | Legitimate outcome when uncertainty is too high |
| Hysteresis | Implementation pattern plus conformance concern | Lifecycle / Scoring | implementation-specific | Prevents estimator noise from creating state churn |
| Lifecycle state machine | Component | Lifecycle Engine | agent-memory doctrine | Shared state vocabulary |
| Transition proposal | Doctrine concept | Lifecycle Engine | agent-memory doctrine | May be probabilistic or learned; does not mutate state |
| Transition commit | Doctrine concept | Lifecycle Engine | agent-memory doctrine | Governed state mutation with receipt |
| Crystallization | Doctrine concept plus component | Certification and Crystallization Gate | agent-memory doctrine | Governed transition to durable state |
| Certification | Component | Certification and Crystallization Gate | governance layer | Confirmation record for durable transition |
| PAMA | Component | Governance and Mutation Authority | agent-memory doctrine / PAMA implementation | Permission to mutate, promote, prune, share, delete, or canonize |
| Mutation authority | Doctrine concept | Governance and Mutation Authority | PAMA | Capability and confidence are not authority |
| Authority envelope | Doctrine concept | Governance and Mutation Authority | agent-memory doctrine | Finite permitted / blocked / review-required consequence set |
| Permitted action set | Doctrine concept | Governance / planner handoff | agent-memory doctrine | Stochastic choice may occur only inside this set |
| Selection mode | Audit concept | Governance / planner handoff | agent-memory doctrine | deterministic, stochastic, human, or external selection |
| Decision receipt | Component contract | Governance / Lifecycle ledger | FailSafe / PAMA / runtime ledgers | Reconstructs estimate, policy, allowed actions, selection, and consequence |
| Policy version | Doctrine concept | Governance | agent-memory doctrine | Must remain distinguishable from estimator version |
| Estimator version | Doctrine concept | Evidence / Scoring | agent-memory doctrine | Needed for consequential inference replay and drift analysis |
| Neurospace | Component | Runtime Memory Space | COREFORGE | Operational agent memory space |
| Vault | Implementation plus component | Runtime Memory Space | COREFORGE | Local encrypted memory container |
| Recall admission | Doctrine concept plus component | Context Assembly Surface | agent-memory doctrine | Retrieval relevance does not override policy or scope |
| CodeGenome | Component | Reality Graphs | CodeGenome | Code reality graph, not general runtime memory |
| Shadow Genome | Component | Correction, Dispute, and Negative Memory | EvolveAI / FailSafe style systems | Stores failure patterns and negative constraints |
| Bicameral decision continuity | Product plus component | Reality Graphs / Durable Decision Memory | Bicameral | High-risk decision memory and drift detection |
| FailSafe evidence capture | Product plus component | Evidence and Governance | FailSafe | Enforcement and audit surface |
| Arbiter | Product component | Governance and Mutation Authority | COREFORGE | Runtime policy guardian |
| Context window assembly | Product surface | Context Assembly Surface | COREFORGE / agent runtime | Operational use, not canonical truth |
| Correction workflow | Product surface plus component | Correction and Dispute Surface | runtime implementation | Must preserve prior state |
| Calibration protocol | Conformance concern | Conformance and Calibration Harness | agent-memory doctrine | Determines estimator and threshold validity |
| Trap classes | Conformance concern | Conformance and Calibration Harness | agent-memory doctrine | Includes access-spam, confident falsehood, jitter, disagreement, scope traps |
| Composition failure | Conformance concern plus doctrine concept | Cross-component | agent-memory doctrine | Safe components may compose into unsafe behavior |
| Research challenge ledger | Doctrine maintenance concern | Research / governance | agent-memory doctrine | Preserves supporting and challenging evidence |

## Control-character classification

New concepts that influence memory should also be classified by control character:

```text
DETERMINISTIC_SUBSTRATE
exact identity, schema validity, committed ledger semantics

PROBABILISTIC_EPISTEMICS
confidence, relevance, trust, contradiction, classification, utility, prediction

GOVERNANCE_ENVELOPE
policy mapping from observations/estimates to permitted consequences

BOUNDED_SELECTION
choice among already-permitted actions

COMMITTED_CONSEQUENCE
actual state mutation, sharing, certification, archival, deletion, or scope change
```

A concept can span more than one class only when its internal boundaries remain explicit.

## Decision tree

Use this decision tree for new concepts.

```text
Does it affect every implementation?
  yes -> doctrine concept
  no -> continue

Does it have its own failure mode and interface?
  yes -> component
  no -> continue

Is it specific to one repo or runtime?
  yes -> implementation detail
  no -> continue

Is it visible to users or agents during operation?
  yes -> product surface
  no -> continue

Is it mainly used to prove behavior?
  yes -> conformance concern
  no -> open a doctrine issue before implementing
```

Then ask:

```text
Is this an estimate, an authority decision, an action selection, or a committed consequence?
```

If the answer is unclear, the concept is under-segmented.

## Boundary examples

### Saturation

Saturation is a component-level concept because it has its own failure modes:

- access-spam inflation
- false permanence
- overfit durability dimensions
- poor threshold calibration
- boundary instability
- out-of-scope calibration reuse

It is also a doctrine concept because every implementation must understand that saturation is routing, not truth or permission.

### PAMA

PAMA is a component because it owns a bounded decision:

```text
What consequences are allowed for this proposed memory transition under this policy and state snapshot?
```

It should not be embedded as an untyped helper inside each memory implementation. That would duplicate authority logic and make policy drift inevitable, because humans apparently enjoy creating three versions of the same mistake.

### Conflict classification versus conflict consequence

Conflict detection and ranking may be probabilistic:

```text
claim A likely contradicts claim B
source A appears more reliable
```

The consequence remains governed:

```text
dispute
split scope
request verification
correct
retain both
block canonical use
```

Do not require uncertain conflict interpretation to become deterministic merely to make the system easier to describe.

### CodeGenome

CodeGenome is a component inside the larger system, not the whole memory system.

It provides code reality evidence. Agent Memory decides how that evidence becomes operational memory or durable memory.

### Neurospace

Neurospace is runtime memory space.

It should consume canonical doctrine and enforce runtime boundaries, but it should not redefine identity, certification, or PAMA rules locally.

## Segmentation rule

If a concept controls a transition, it should be a component or explicit governance contract.

If a concept explains a cross-system boundary, it should be doctrine.

If a concept proves behavior, it should be conformance.

If a concept only exists inside one repo, keep it there until it proves it deserves promotion.

If a concept is probabilistic, do not make it authoritative by renaming the output.
