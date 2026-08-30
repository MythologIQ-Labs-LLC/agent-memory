# Checkpoint Behavioral Assessment Profile

## Purpose

A memory checkpoint can be structurally valid and still make recall worse.

A correction can become harder to retrieve than the value it replaced. A durable anchor can disappear from ordinary recall. A high-relevance item from another scope can leak into the candidate set. Two states that should produce different recall can collapse into the same result.

This profile gives Agent Memory a bounded way to test those failures across a checkpoint transition.

It is an evidence profile. It does not approve a checkpoint, create standing permission, or replace PAMA, certification, recall admission, or deployment policy.

```text
checkpoint transition
  -> behavioral assessment
  -> evidence about retrieval behavior
  -> applicable conformance / certification requirement
  -> PAMA or deployment policy remains responsible for consequence
```

## Keep the questions separate

A useful assessment answers five different questions:

1. Was the declared assessment actually exercised against the state it names?
2. Did the required retrieval properties hold, fail, or remain unestablished?
3. Does the evidence apply to the exact checkpoint pair and retrieval path now under review?
4. Does the applicable evidence satisfy this particular conformance or certification requirement?
5. What happened historically, including earlier failures and later remediation?

Those answers should not be collapsed into one boolean.

## Behavioral result and evidence posture

The behavioral result is:

```text
verified
contradicted
inconclusive
```

`verified` means the required probes established the properties claimed by this profile. `contradicted` means a required probe observed behavior that violates the profile. `inconclusive` means the required property was not established. It is neither success nor demonstrated failure.

Evidence posture is recorded separately:

```text
exercised
unavailable
unsupported
not_exercised
```

An unavailable retriever can therefore make a required probe inconclusive without pretending the probe observed a behavioral contradiction.

## Applicability

Evidence applies only to the transition and retrieval path it actually exercised. The reference implementation binds:

```text
baseline checkpoint ref + state digest
candidate checkpoint ref + state digest
probe-suite digest
retriever component + version
retriever profile + version
material configuration digest
assessment profile + version
completion time
```

A consumer may also define an inclusive evidence window.

A successful assessment for a different checkpoint, suite, retriever profile, or material configuration remains valid evidence about that run. It simply cannot satisfy the current requirement. Missing or substituted evidence is not success.

## Reference decision tree

```text
assessment evidence presented
|
+-- no applicable assessment
|   -> requirement not satisfied
|
+-- applicable assessment exists
    |
    +-- required behavior was not exercised
    |   -> requirement not satisfied
    |
    +-- any applicable result is contradicted
    |   -> requirement not satisfied
    |
    +-- any applicable result is inconclusive
    |   -> requirement not satisfied
    |
    +-- all applicable results are verified
        -> this requirement is satisfied
        -> no authority is granted
```

The helper answers only whether this assessment requirement is satisfied. PAMA, certification, release policy, or another governed process decides what consequence follows.

## Probe set

### Correction precedence

After a correction, the current value must be retrievable and a superseded value must not outrank it for the bound query. Proving that the corrected record still exists somewhere in storage is not enough.

### Anchor preservation

A checkpoint transition must not silently remove or materially demote a declared durable anchor. The reference probe compares baseline and candidate rank using a declared maximum rank drop.

If the anchor is already missing from the baseline observation, the probe is inconclusive rather than inventing a baseline property it did not observe.

### Scope isolation

The bound query must not retrieve a forbidden logical memory or an item carrying a forbidden scope reference.

This is a negative confidentiality property. An empty result can verify that this probe observed no forbidden hit. It does not prove useful recall or liveness. Positive probes establish those properties separately.

### State-conditioned differentiation

Two deliberately different states and contexts must not collapse into the same retrieval result when the fixture expects different memory to be active.

The profile rejects a differentiation probe that uses the same context on both sides or declares identical expected sets.

## Repeated trials

The suite may run a probe more than once. Agent Memory does not require a probabilistic retriever to emit byte-identical ordering on every run. Instead, the required invariant is evaluated on every trial:

```text
any contradiction -> contradicted
no contradiction, but at least one inconclusive trial -> inconclusive
all trials establish the property -> verified
```

This keeps stochastic retrieval inside a deterministic evaluation rule without pretending randomness disappeared.

## State stability during assessment

The assessment must describe the state that was actually exercised.

The reference harness reads the baseline and candidate state digests before the first retrieval and again after the final retrieval. If either state does not match the declared precondition, or changes while the probes are running, artifact construction stops.

Binding retrieval evidence from state S1 to checkpoint state S2 is not valid simply because both belong to the same logical memory system.

## Conflicting and historical evidence

More than one assessment can apply to the same requirement. The reference rule is conservative: an applicable contradiction or inconclusive result keeps the requirement unsatisfied even if another applicable run verified the behavior. Conflicting evidence should be investigated, not resolved by selecting the pleasant result.

A later remediation normally creates a new candidate state. The failed assessment remains historical evidence for the old candidate while a verified assessment can become applicable to the remediated candidate.

```text
old candidate + contradicted assessment -> preserve history
new candidate + verified assessment -> may satisfy the new requirement
```

## Identity and minimized evidence

Retrieved items use a logical reference as the cross-observation identity. A version reference may be recorded as additional evidence, but a changed physical representation must not silently create a new logical memory.

The reference artifact records digests of bound retrieval observations instead of requiring raw memory content in the assessment record. Deployments that need richer evidence can retain it separately under normal privacy and custody rules.

Duplicate logical references or duplicate ranks in one observation are rejected because they make precedence and ordering claims ambiguous.

## Authority boundary

The assessment is intentionally unable to authorize anything.

```text
verified behavior != PAMA allow
verified behavior != certification
verified behavior != deployment approval
contradicted behavior != invalid historical evidence
```

A consuming policy may require verified assessment evidence before a consequential transition. That requirement is outside this profile. Provider confidence, retrieval score, component identity, or assessment result cannot widen the permitted action set by themselves.

## Relationship to Agent Memory

This profile implements existing boundaries rather than creating a second governance model:

- [`../06-conformance-test-plan.md`](../06-conformance-test-plan.md) separates discovery, admission, context surfacing, and downstream influence.
- [`../26-governed-recall-planner.md`](../26-governed-recall-planner.md) keeps retrieval separate from governed admission.
- [`../30-memory-observability-and-audit-events.md`](../30-memory-observability-and-audit-events.md) keeps evidence, authority, and consequence reconstructable.
- [`../32-memory-quality-metrics.md`](../32-memory-quality-metrics.md) keeps hard invariant failures separate from optimization metrics and warns against gaming safety by never retrieving anything.
- ADR-035 keeps provider signals non-authoritative inside the Cognitive Mesh.

The profile can later be mapped to external checkpoint-assessment formats for interoperability. Such a mapping must not import another system's approval model or make it a runtime dependency.

## Reference implementation

```text
reference/agentmem_ref/checkpoint_behavior.py
reference/tests/test_checkpoint_behavior.py
```

The tests cover the four positive invariants plus correction loss and outranking, anchor loss and demotion, forbidden-scope retrieval, state collapse, unavailable evidence, state changes during assessment, applicability mismatch, conflicting applicable assessments, optional diagnostic failures, and remediation without history deletion.

## Non-goals

This first slice does not define a universal production retriever API, replace existing conformance levels, make checkpoint assessment mandatory for every deployment, create a signing format, prove that no conflicting assessment was withheld, depend on AgentTrust or Agent Manifest at runtime, or authorize a checkpoint or downstream action.

The goal is narrower: make it harder to claim that memory state advanced safely when the retrieval behavior that gives that state practical meaning has regressed.
