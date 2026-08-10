# Durable Decision Memory Profile

## Purpose

This is the first entry in the profile family: doctrine applied to one high-value memory class. Decision memory serves Bicameral-style decision continuity, agent governance, product planning, and code evolution — and decisions are not ordinary facts. A fact is true or it is not. A decision was *made*: by someone, over alternatives, for reasons, within a scope, until superseded.

Treating decisions as facts produces the familiar failures: decisions relitigated because the rationale evaporated, superseded decisions enforced by agents that remembered the conclusion but not the retirement, and drift between what was decided and what is being done that nobody can date.

This profile defines the required shape, lifecycle handling, recall rules, and conformance surface for decision memory. It builds on the general doctrine and assumes it; nothing here relaxes a general rule.

## Required fields

A decision memory unit is a memory unit (per [`../../schemas/memory-unit.schema.json`](../../schemas/memory-unit.schema.json)) typed as a decision, additionally carrying:

```text
decision_id
decision_statement        # what was decided, as a commitment, not a description
rationale                 # why — required, not decorative
alternatives_considered   # options rejected, each with at least a one-line reason
decision_scope            # what the decision governs: systems, processes, time horizon
owner                     # accountable principal (role or person per doc 29)
approval_refs             # who agreed, with what authority
decided_at                # decision time, distinct from observation time (doc 18)
effective_from
review_by | effective_until
supersedes                # prior decision_id, when applicable
superseded_by             # set on retirement
status                    # proposed | active | superseded | reversed | expired
impacted_refs             # memories, components, policies the decision constrains
drift_signals             # optional: observations of divergence between decision and reality
```

Field invariants:

- **Rationale is required.** A decision without preserved rationale cannot be safely superseded, only contradicted. Implementations must reject decision memory whose rationale is empty.
- **Alternatives are preserved, not embarrassing.** Rejected options with reasons are what future re-evaluation runs on; losing them forces every revisit to start from zero.
- `owner` and `approval_refs` follow the actor and delegation rules of [`../29-actor-scope-consent-and-tenancy.md`](../29-actor-scope-consent-and-tenancy.md); a decision whose approving authority cannot be reconstructed is a claim, not a decision.

## Rationale and alternative preservation

- Rationale and alternatives are evidence-linked: they cite the sources considered at decision time, and those references survive summarization per the provenance rules of [`../04-governance-and-pama.md`](../04-governance-and-pama.md).
- Compression of old decisions (consolidation, summarization) may shorten the prose; it may not drop the alternative set, the approval refs, or the scope.
- The rationale is bound to the decision *as of `decided_at`*. Later evidence does not retroactively edit rationale; it accumulates as drift signals or supersession pressure.

## Supersession and drift

**Supersession** follows [`../18-temporal-causality-layer.md`](../18-temporal-causality-layer.md):

```text
new decision supersedes old  -> old.status = superseded, old.superseded_by set
                                old remains recallable as historical
                                agents enforcing old decision must observe retirement
reversal without replacement -> status = reversed, with rationale for reversal
expiry                       -> status = expired at effective_until / unactioned review_by
```

A superseded decision is never deleted by supersession — decision history is exactly the memory class whose past states stay load-bearing (audits, "why is the system like this," re-evaluation).

**Drift** is the gap between an active decision and observed reality:

- Detectors (agents, conformance runs, humans) may attach `drift_signals` — estimator outputs, with provenance and uncertainty per the evidence rules.
- Drift signals never auto-supersede. Material drift routes to the decision's owner for a governed outcome: reaffirm, revise (new decision superseding), or reverse. An estimator observing drift and "correcting" the decision itself is the confidence-becomes-authority failure with a paper trail.
- Unreviewed drift past `review_by` escalates per the review-budget rules of [`../37-memory-economics-and-budget-policy.md`](../37-memory-economics-and-budget-policy.md); the conservative interim state is that the decision stands but is flagged contested-by-drift in recall.

## Owner and approval metadata

- Ownership is a role or principal that survives personnel change; orphaned decisions (owner no longer resolvable) are flagged for re-ownership at next review, not silently ownerless.
- Approval strength scales with the decision's risk class per [`../33-pama-decision-table.md`](../33-pama-decision-table.md): a team convention needs less than a security boundary decision.
- Corrections to decision *records* (typos, mislinked evidence) are ordinary corrections per [`../38-human-correction-ux-contract.md`](../38-human-correction-ux-contract.md). Changing what was decided is never a correction; it is supersession or reversal by the owner's authority.

## Recall and certification rules

**Recall** (through [`../26-governed-recall-planner.md`](../26-governed-recall-planner.md)):

- An agent acting within a decision's scope gets the decision recalled with policy-grade completeness — the applicable-set rule of [`../36-policy-as-memory.md`](../36-policy-as-memory.md) applies: missing an active in-scope decision is a recall failure.
- Recall returns the decision with its status. Superseded and reversed decisions surface only as historical, never as current constraints; a drift-flagged decision surfaces with the flag.
- Rationale and alternatives are recallable on demand but need not be admitted into every context — the decision statement, scope, and status are the working set; the rest is one hop away with provenance intact.

**Certification**:

- An active decision constrains behavior, which makes it authority-adjacent: certification for decision memory verifies the *record* — statement matches approval, scope is defined, owner resolvable, supersession chain intact — not the decision's wisdom.
- Certified-active decisions are the only ones agents may treat as binding constraints. Uncertified decision records are candidate memory: recallable, flagged, non-binding.
- Certification revocation (broken supersession chain, unresolvable authority) demotes the decision to disputed per [`../31-recovery-rollback-and-replay.md`](../31-recovery-rollback-and-replay.md) — visible, contested, non-binding until repaired.

## Conformance fixture recommendations

| Case | Expectation |
|---|---|
| Superseded decision recalled as current | fails: agent within scope receives the superseding decision; old surfaces as historical only |
| Rationale-free decision write | rejected at write time |
| Drift signal auto-supersedes | fails: drift routes to owner; estimator cannot retire a decision |
| Decision enforced past expiry | fails: expired status blocks binding use; escalates to review |
| Alternative set lost in consolidation | fails: compression preserved statement but dropped alternatives/approvals |
| Approval chain unreconstructable | certification refused; decision non-binding — the [`../../fixtures/authority-laundering.json`](../../fixtures/authority-laundering.json) pattern applied to decisions |
| Conflicting active decisions in one scope | governed conflict per [`../17-conflict-resolution-engine.md`](../17-conflict-resolution-engine.md); strictest-applicable interim; no recency-wins |

A `superseded-decision-recall` fixture is the highest-value addition and should join the fixture backlog tracked in issue #43.

## Doctrine

A decision is memory with an owner, a reason, and an expiry on its certainty.

Store the conclusion and you have a fact that will rot. Store the commitment — rationale, alternatives, authority, scope, supersession — and the system can do the one thing decision memory exists for: change its mind on purpose, and know that it did.
