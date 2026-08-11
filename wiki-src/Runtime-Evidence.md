# Runtime Evidence

**[Conformance and Evidence](Conformance-and-Evidence)** describes the evidence ladder. This page records where Agent Memory actually stands on it.

The distinction this page exists to protect: a repository can validate perfectly and still have demonstrated nothing about runtime behavior. Everything below is labelled by what it genuinely establishes.

## The evidence bar

A claim counts as runtime evidence only when all five hold:

| Requirement | Meaning |
|---|---|
| **Executed** | the path ran against a real substrate, not a diagram |
| **Pinned** | substrate, adapter, policy, estimator, and fixture versions are recorded |
| **Reproducible** | another operator re-runs it and gets the same verdict |
| **Negative-tested** | the run includes paths that must fail, and they failed |
| **Reconstructable** | a receipt reconstructs estimate, authority, selection, and consequence |

Evidence that omits the negative paths is a demo. Evidence that cannot be re-run is an anecdote. Neither moves an Architecture Decision Record.

## What has been demonstrated

A reference governed adapter executes the full path — proposal, authority envelope, permitted action set, selected action, substrate mutation, decision receipt, retrieval, governed admission — and runs in continuous integration.

**Against a real temporal knowledge graph.** Seven governance paths execute against a live graph database with no language model, no embedder, no API key, and no server. This includes cross-partition refusal, supersession that marks rather than deletes, pruning that keeps content recoverable, and a physical delete.

**Against the doctrine fixture corpus.** All repository fixtures are driven through the adapter's own authority-enforcement rule. This matters because the fixtures were written to describe doctrine, not to satisfy the adapter, so agreement between them is evidence rather than a test suite agreeing with its author.

**Stochastic containment.** Hundreds of trials sample from the permitted action set. No trial ever selects outside the envelope, and a deliberately hostile selector that tries to take a prohibited action is contained by the adapter rather than trusted to behave.

## What that still does not prove

Stated plainly, because a partial result presented as a complete one is worse than no result:

- **No conformance level is claimed.** Levels are cumulative, and the reference adapter implements neither decay nor calibrated saturation, so levels 2 and 3 are unmet however well authority enforcement performs.
- Corpus coverage is **authority-envelope enforcement**, not full scenario execution. Decay, calibration, retrieval ranking, and most lifecycle mechanics sit outside this adapter.
- Retrieval uses lexical matching rather than hybrid search, so **recall quality is not measured** and no calibration claim is made.
- The substrate binding uses an embedded backend that is deprecated upstream, chosen because it needs no server. No governance behavior under test depends on that choice.
- The adapter is a **reference, not a product**: it implements the narrow slice needed to exercise governance, and nothing else.

## Why the tests are built to fail

Two habits distinguish this evidence from self-congratulation.

**The substrate model is permissive on purpose.** It reproduces the mapped substrate's verified behavior including its dangerous defaults: an unfiltered partition default, physical deletion with no tombstone, and no authority check anywhere. Several tests assert *both* that the substrate would misbehave and that the adapter refuses regardless. A test that only checked the adapter would not show the governance was doing any work.

**The checkers are mutation-tested.** Deliberately corrupted authority envelopes must be detected. A conformance check that cannot fail is decoration, so the corruptions are permanent tests: if a check quietly loses its teeth, that failure surfaces.

## What execution corrected

Running the binding revised three conclusions that source reading alone had reached, which is the practical argument for executing rather than describing:

1. The substrate library's top-level client constructs a model-provider client even when every operation in use is provider-free, so a governed adapter must bind at the driver level.
2. An empty partition signals absence by raising rather than returning an empty result.
3. Invalidated facts are still returned by partition queries, so an adapter that does not filter them would admit superseded facts as current. The separation between retrieval and admission turns out to be load-bearing against a specific real system, not only in principle.

## Where this leaves ADR-020

Closer, and not close enough. The proof bar in **[Architecture Decisions](Architecture-Decisions)** additionally expects concurrency behavior, deletion propagation measurement, and evidence gathered across a wider surface than one reference adapter. ADR-020 stays Proposed.

Deletion propagation is the slice now in progress, and it began by discovering that the requirement was not yet expressible. "This projection is stale with respect to canonical state" had no defined meaning here, which made it untestable rather than merely unproven. **[Canonical and Derived State](Canonical-and-Derived-State)** supplies the missing definitions and fixes the evidence bar in advance — deliberately including the parts a persuasive demonstration would skip. It is a design spike: no code, no fixtures, and no claim on this page's ledger until something executes.

## Canonical sources

- Runtime evidence program: https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/docs/programs/runtime-evidence
- Substrate capability mapping: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/programs/runtime-evidence/graphiti-conformance.md
- Canonical and derived state design spike: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/programs/runtime-evidence/canonical-and-derived-state.md
- Reference adapter: https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/reference
- Conformance test plan: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/06-conformance-test-plan.md

## Next

- **[Conformance and Evidence](Conformance-and-Evidence)** for the full evidence ladder and level definitions
- **[Implementation Guide](Implementation-Guide)** to map your own runtime
- **[Governed Uncertainty](Governed-Uncertainty)** for the doctrine these paths test
