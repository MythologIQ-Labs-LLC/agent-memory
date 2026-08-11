# Runtime Evidence Program

## Purpose

Move Agent Memory from a **doctrine-validated** reference architecture to an **implementation-evidenced** one.

Everything in the doctrine tree is currently supported by internal coherence: schemas that validate, fixtures that are structurally sound, ADRs that agree with the documents they govern. That is necessary and it is not proof. This program exists to test whether the architecture's boundaries survive real substrates, real workloads, adversarial cases, portability pressure, observability requirements, and cost.

> ADR-020 remains Proposed until runtime evidence, not prose, earns acceptance.

The live backlog and workstream detail are tracked in the program issue. This document is the durable in-repo statement of the program's rules: what counts as evidence, how comparators are used, and what the program is not allowed to do.

## What counts as runtime evidence

A claim becomes runtime evidence only when all of the following hold:

```text
executed        the path ran against a real substrate, not a diagram
pinned          substrate version, adapter version, policy version,
                estimator version, and fixture version are all recorded
reproducible    another operator can re-run it and get the same verdict
                (invariants, not identical stochastic outputs)
negative-tested the run includes paths that must fail, and they failed
reconstructable a receipt reconstructs estimate, authority, selection,
                and consequence after the fact
```

Evidence that omits the negative paths is a demo. Evidence that cannot be re-run is an anecdote. Both are welcome in a discussion and neither moves an ADR.

P4.5a is intentionally a **substrate-independent interoperability precondition** rather than a claim that another runtime substrate has been exercised. Its job is to make the portable evidence boundary executable and adversarially testable before correlation to Agent Manifest, TRACE, or another external runtime surface.

## Comparator discipline

External systems enter this program to answer one architectural question each, and are barred from becoming something else:

| Comparator | Its one job | Not allowed to become |
|---|---|---|
| Temporal graph substrate | first adapter target for time, provenance, and retrieval | doctrine authority |
| Production memory layer | adversarial comparator for accumulation, correction, deletion | replacement architecture |
| Lifecycle-contract and portability work | interoperability and interchange pressure | automatic standard |
| Governance and lifecycle-security benchmarks | access control, forgetting, Write to Execute to Forget stress | the sole quality metric |
| Task and long-horizon benchmarks | whether memory improves future action | a recall-only leaderboard |
| Telemetry conventions | observability interoperability | licence to emit memory content |
| Systems characterization | cost, latency, and scaling pressure | an authority signal |

Two standing rules follow from this table. A missing guarantee in an external system is a **classified gap**, not a bug, unless that system claims the guarantee. And a behavior observed in one product does not become Agent Memory doctrine without independent justification, otherwise the architecture is just the union of whatever shipped recently.

## Evidence rules for imported material

```text
portable        != trusted
imported        != admitted
interoperable   != authorized
benchmarked     != governed
```

Anything arriving from an external substrate, bundle, or benchmark enters normal Agent Memory evidence, scope, sensitivity, lifecycle, and authority handling on arrival. Adapters make decisions portable; they do not make them pre-approved.

## Scoring rule

No universal memory score. Program results are reported as the scorecard defined in [`../../32-memory-quality-metrics.md`](../../32-memory-quality-metrics.md): hard invariant gates first (disqualifying, un-averageable), then trap-class rates, then optimization and outcome metrics, with segment breakdowns. A benchmark aggregate that hides a cross-scope admission or a blocked-action escape is not a result, it is a press release.

## Layout

```text
docs/programs/runtime-evidence/     program material (this directory)
reference/                          executable adapters, policies, receipts, tests
```

Program material uses grouped paths rather than extending the canonical document numbering. Existing canonical document numbers are never reused.

Documents are added when their slice is ready to execute, not in advance. A directory of speculative placeholders would be its own small monument to unearned confidence.

| Document | Slice | Status |
|---|---|---|
| [`graphiti-conformance.md`](graphiti-conformance.md) | first substrate capability mapping | documentation-verified, with key findings confirmed by execution |
| [`../../../reference/README.md`](../../../reference/README.md) | minimal governed adapter | bound and executed against a real substrate |
| [`canonical-and-derived-state.md`](canonical-and-derived-state.md) | canonical memory versus derived projections | design spike executed: all seven evidence-bar items run in CI |
| [`portable-governance-evidence.md`](portable-governance-evidence.md) | P4.5a portable governance evidence core | executable substrate-independent Ed25519 issuer/verifier and adversarial vectors |

## Preconditions

Before runtime evidence from a first-party implementation is treated as dispositive:

1. the repository evidence floor is closed (versioned fixtures, validated audit traces, quality gates, doctrine traceability);
2. doctrine-to-implementation identity is established for any implementation used as evidence, earned through a concrete responsibility or conformance surface rather than asserted;
3. the exact implementation, policy, estimator, fixture, and evidence bundle versions are reproducible.

External comparators do not require precondition 2. A comparator is measured, not adopted.

## Non-goals

This program does not authorize replacing Agent Memory with any external system, vendor lock-in, treating emerging drafts as adopted standards, importing external schemas without semantic review, inventing a universal memory score, averaging critical governance failures into a passing aggregate, weakening scope, privacy, correction, or deletion semantics for implementation convenience, declaring governance runtime-proven because a schema validates, or accepting ADR-020 because a demonstration was persuasive once.

## Governing principle

> Agent Memory is judged by what retained state is allowed to change in future behavior, under what authority, with what evidence, and whether the consequence can be reconstructed and undone or forgotten when required.

Retrieval quality matters. Governance is why this repository exists.
