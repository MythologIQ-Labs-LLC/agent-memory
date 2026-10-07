# ADR-042: Low-risk state-change proposals may be auto-applied only through a versioned PAMA profile

**Status**: Proposed  
**Issue**: #717  
**Originating ruling**: #671, owner ruling "Option A now; Option D next"  
**Related doctrine**: ADR-004, ADR-011, ADR-020, ADR-023, ADR-030, ADR-039  
**Related runtime work**: #550, #580, #584, #596, #597, #671

## Decision summary

Agent Memory may eventually support **automatic application of narrowly qualified state-change proposals**, but only when a versioned PAMA profile independently authorizes the lifecycle mutation.

Automatic application is not a shortcut around mutation authority.

The controlling separation is:

```text
interpretation
  != change evidence
  != proposal
  != PAMA authority
  != lifecycle application
```

The intended architecture is:

```text
typed state-change evidence
        |
        v
state-change proposal
        |
        v
auto-application eligibility profile
        |
        v
PAMA evaluation
        |
        +--> allow_with_ledger
        |       |
        |       v
        |   durable supersession
        |   + receipt
        |   + audit lineage
        |   + rollback/revocation path
        |
        +--> anything stricter
                |
                v
           proposal remains open
```

The first eligible profile, if implemented, MUST be deliberately narrow:

- same actor;
- same source;
- same scope / isolation domain;
- canonical proposition identity;
- explicitly single-valued replacement semantics;
- explicit state-change evidence;
- both facts live;
- neither fact disputed;
- no authority escalation;
- no scope expansion;
- versioned/revocable lifecycle change;
- low operational risk;
- target class and downstream authority within an explicitly approved autonomous envelope.

The first profile SHOULD be bounded to low-consequence state and A0/A1 downstream effects. M4, M5, A2+, governance, security, permission, entitlement, identity-bearing external state, policy mutation, decision overwrite, and action authority are outside the initial autonomous profile.

Unknown eligibility is ineligible.

A PAMA outcome stricter than `allow_with_ledger` leaves the proposal unapplied.

## Context

Agent Memory already has the correct conceptual separation between memory interpretation and durable authority.

ADR-004 makes PAMA the canonical mutation-authority boundary.

ADR-023 establishes that corrections preserve history through supersession rather than deletion.

ADR-039 keeps relevance, temporal applicability, and lifecycle authority distinct and explicitly rejects the proposition that a newer observation silently supersedes an older one.

The formal currentness work under #671 exposed a useful distinction.

### Option A

The owner approved Option A as the immediate currentness repair:

- use already-detected cross-fact state-change evidence;
- under explicit-current recall only;
- constrain applicability of the older fact;
- do not mutate lifecycle state;
- keep the proposal open.

That is a **read-path** mechanism.

### Option D

The owner separately approved Option D as the next architectural direction:

- a declared low-risk profile;
- governed automatic application of qualifying proposals;
- durable supersession;
- auditable receipts.

That is a **lifecycle** mechanism.

The two mechanisms solve related but different problems.

Option A lets recall answer a current-state question correctly before a durable lifecycle transition has been approved.

Option D asks whether some state transitions are sufficiently low-risk, well-typed, reversible, and authority-bounded that PAMA may approve their lifecycle application automatically.

Without this ADR, "automatic correction" could be implemented in several unsafe ways:

- newer write wins;
- high confidence grants mutation;
- same-slot conflict silently mutates history;
- repeated observations become authority;
- a benchmark-specific currentness fix applies corrections opportunistically;
- an estimator effectively approves its own proposal.

All are prohibited by existing doctrine.

## Decision

### 1. Automatic application is a PAMA outcome, not an interpreter capability

The component detecting a state change MAY emit:

- proposition identity;
- cardinality/replacement semantics;
- conflict/state-change evidence;
- confidence or uncertainty;
- a proposed lifecycle transition.

It MUST NOT apply the transition merely because its interpretation is strong.

The lifecycle application path MUST pass through PAMA or an equivalent authority mechanism that satisfies ADR-004.

```text
detector -> proposal
PAMA -> authority decision
lifecycle -> application
```

The detector and authority evaluator remain separately inspectable.

### 2. Eligibility is evaluated before PAMA and cannot weaken PAMA

An **auto-application eligibility profile** determines whether a proposal may even request autonomous application.

Eligibility is a conservative precondition.

It does not produce authority.

Passing eligibility means:

> this proposal is allowed to ask PAMA for autonomous application under this profile.

It does not mean:

> this proposal may be applied.

PAMA may always be stricter.

The effective result is therefore:

```text
eligible?
  no  -> remain proposal
  yes -> PAMA
            allow_with_ledger -> may apply
            anything else     -> remain proposal
```

### 3. The first profile is fail-closed

Every required eligibility field MUST be reconstructable.

A missing field is not interpreted as low risk.

The first profile MUST require at least:

#### Identity

- old fact id;
- new fact id;
- canonical proposition/slot identity;
- actor identity for both;
- source identity for both;
- scope/tenant/isolation identity for both.

#### Relationship

- explicit typed state-change evidence;
- a relation compatible with replacement;
- single-valued cardinality semantics or another explicitly declared replacement contract;
- no unresolved ambiguity that permits coexistence.

#### State

- old fact live at decision time;
- new fact live at decision time;
- old fact not disputed;
- new fact not disputed;
- no tombstone/retraction/revocation conflict;
- no hold that forbids the intended lifecycle transition.

#### Language / interpretation

- no hedge state that defeats replacement semantics;
- no untrusted-claim posture that defeats the profile;
- no unresolved quoted/hypothetical/request context.

#### Consequence

- no scope expansion;
- no downstream authority increase;
- no governance/security/policy mutation;
- reversible or versioned-revocable application;
- low operational risk under the declared profile.

If any predicate cannot be proven from committed evidence, the proposal remains unapplied.

### 4. Same actor and same source are required initially

The first profile MUST require:

```text
old.actor == new.actor
old.source == new.source
```

This is intentionally stricter than general conflict detection.

Two sources disagreeing about the same slot is evidence of conflict, not authority to let one overwrite the other.

Two actors writing different values may require review, conflict presentation, or another policy.

The first automatic profile does not resolve those cases.

A future ADR/profile MAY relax source/actor requirements only with separate evidence and authority analysis.

### 5. Initial target and authority classes are bounded

The first autonomous profile MUST exclude M4 and M5 target classes.

It SHOULD initially permit only low-consequence M1/M2 state, and only where the specific state is genuinely compatible with correction semantics.

The initial downstream authority ceiling MUST be no greater than A1.

```text
allowed candidate envelope:
  low risk
  reversible/versioned
  M1 or explicitly approved M2
  A0 or A1

excluded:
  M4
  M5
  A2
  A3
  A4
  A5
```

This is a starting envelope, not a claim that every M1/M2 transition is safe.

The versioned profile remains free to exclude individual domains/properties.

### 6. PAMA must return allow_with_ledger

For autonomous application, the PAMA decision MUST resolve to:

`allow_with_ledger`

A bare `allow` is not sufficient for this profile because durable lifecycle mutation requires a receipt.

The following outcomes do not auto-apply:

- `require_review`;
- `require_external_verification`;
- `block`;
- `abstain`;
- `quarantine`;
- `collect_more_evidence`.

They leave the proposal open.

The runtime MUST NOT automatically satisfy its own review requirement merely to make the transition proceed.

### 7. Correction semantics are preferred over a new mutation operation

The first implementation SHOULD use the existing PAMA `correction` operation if its semantics can faithfully represent the transition.

Do not add a new `supersession` PAMA operation merely for naming convenience.

A new operation is justified only if existing correction semantics cannot express the authority and receipt requirements without ambiguity.

If a new operation is introduced, the PAMA schema, decision table, tests, and compatibility rules MUST be versioned explicitly.

### 8. Application creates durable supersession, not destructive overwrite

An approved automatic transition MUST preserve history.

The old fact is not deleted simply because the new fact becomes current.

The application SHOULD create the same durable lifecycle structure expected from a governed correction:

- supersession/correction relation;
- old fact historical state;
- new fact current state where applicable;
- transaction/application time;
- proposal/decision references;
- receipt;
- audit event;
- rollback/revocation path.

Historical and as-of recall remain able to reconstruct the older state.

### 9. Every automatic application needs a reconstructable receipt

At minimum the receipt MUST bind:

- proposal id;
- old fact id;
- new fact id;
- proposition/slot identity;
- state-change evidence refs;
- auto-application profile id/version;
- actor/source/scope bindings;
- PAMA policy version;
- PAMA decision reference;
- mutation operation;
- transaction/application identity;
- supersession/correction relation;
- reversibility/rollback information.

A reader after restart must be able to answer:

1. what changed;
2. why it was eligible for autonomous handling;
3. which PAMA policy allowed it;
4. which evidence supported the proposal;
5. what authority ceiling applied;
6. how to reverse or revoke the transition where permitted.

### 10. Application is state-bound and race-safe

Eligibility and PAMA approval are not permanent capabilities attached to the proposal.

Application MUST verify that the state evaluated is still the state being mutated.

The implementation MUST refuse or re-evaluate when material state changes between:

```text
proposal
-> eligibility
-> PAMA decision
-> application
```

Examples:

- either fact becomes disputed;
- the new fact is retracted;
- a competing correction lands;
- the old fact is already superseded;
- scope changes;
- policy version changes;
- actor/source identity cannot be reconstructed;
- retention/legal hold changes;
- a relevant authority ceiling changes.

A stale allow decision MUST NOT be replayed against a materially different state.

### 11. Concurrency must fail closed

Two concurrent qualifying proposals for the same single-valued slot MUST NOT both auto-apply independently.

The application path MUST establish a deterministic or transactionally protected current-state expectation.

At minimum:

- proposal binds expected prior state;
- application checks that expectation;
- only one conflicting transition commits;
- losing/stale proposal remains visible and requires re-evaluation.

Automatic application must not turn a race into fabricated chronology.

### 12. Confidence and repetition never relax authority

The following never make an otherwise ineligible proposal eligible:

- high classifier confidence;
- high embedding similarity;
- repeated retrieval;
- repeated writing;
- benchmark success;
- model agreement;
- route count;
- recency;
- freshness alone.

They may be evidence where the profile allows them.

They do not grant mutation authority.

### 13. Option A and Option D remain independently observable

The read path MUST preserve the distinction between:

- temporary/query-conditioned applicability from Option A;
- durable lifecycle currentness from an applied Option D transition.

Ranking/recall evidence SHOULD be able to distinguish bases such as:

```text
interpreted_cross_fact
durable_supersession
declared_validity
governed_correction
```

A query answered correctly through Option A must not be reported as durable supersession.

If Option D later commits the lifecycle transition, subsequent reads may rely on the durable lifecycle state.

### 14. Automatic application is profile-specific

There is no global:

`auto_apply = true`

The authority is bound to a versioned profile that declares:

- eligible target classes;
- authority ceiling;
- allowed operations;
- property/relation requirements;
- actor/source requirements;
- risk ceiling;
- reversibility floor;
- dispute posture;
- scope rules;
- evidence requirements;
- policy version;
- application invariants.

Different deployments may enable no automatic profile at all.

The safe default is **disabled** until a profile is explicitly selected.

### 15. Benchmark performance cannot activate the feature

Benchmark evidence MAY qualify an implementation.

Benchmark results MUST NOT:

- switch automatic application on;
- expand its target classes;
- expand its authority ceiling;
- waive review;
- alter eligibility on benchmark-specific language.

The profile is architecture/policy.

Benchmarks test it.

They do not control it.

## Initial excluded cases

The initial profile MUST refuse autonomous application for at least:

### Multi-valued or coexistence-compatible state

Examples:

```text
Kevin likes coffee
Kevin likes tea
```

or any property whose cardinality permits simultaneous values.

### Cross-source disagreement

```text
source A: endpoint = X
source B: endpoint = Y
```

This is conflict evidence, not automatic correction.

### Cross-actor disagreement

Different actors asserting competing facts remain proposals/conflicts unless another authority profile governs them.

### Hedged or uncertain replacement

```text
I think the endpoint may now be X
```

does not qualify for the first profile.

### Sensitive or authority-bearing state

No autonomous profile for:

- credentials;
- access rights;
- permissions;
- entitlements;
- identity;
- legal status;
- compliance state;
- security policy;
- governance policy;
- action authority;
- external commitments carrying consequential authority.

### Scope expansion

A new write that would broaden a memory's visibility or influence is not a low-risk correction.

### Disputed state

A dispute is an escalation signal, not an auto-application opportunity.

### Destructive deletion

Supersession is not permanent deletion.

Deletion remains under its existing authority path.

## Required adversarial evidence before implementation acceptance

A future implementation plan MUST include negative controls for at least:

1. same-slot multi-valued facts;
2. same property but different scope;
3. same scope but different actor;
4. same actor but different source;
5. hedged new fact;
6. quoted/hypothetical new fact;
7. disputed new fact;
8. disputed old fact;
9. new fact retracted before application;
10. old fact already superseded before application;
11. conflicting simultaneous proposals;
12. stale PAMA decision;
13. changed PAMA policy version;
14. retention/hold conflict;
15. M4/M5 target;
16. A2+ downstream consequence;
17. permission/security/policy state;
18. ambiguous proposition identity;
19. unknown cardinality;
20. missing actor/source/scope;
21. high-confidence but ineligible proposal;
22. high-repetition but ineligible proposal;
23. restart and replay;
24. rollback/revocation.

## Required implementation evidence

A future implementation is not accepted merely because formal currentness improves.

It must separately demonstrate:

### Authority correctness

- zero autonomous applications outside the declared profile;
- zero review/external-verification bypasses;
- zero authority-ceiling expansion;
- reconstructable PAMA decision for every application.

### Lifecycle correctness

- durable supersession survives restart;
- history remains available;
- current-state projection reflects the applied transition;
- rollback/revocation remains possible where declared;
- concurrent conflicts fail closed.

### Read-path correctness

- Option A behavior remains independently explainable;
- durable and inferred applicability bases are distinguishable;
- historical/as-of queries are not broken by current-state lifecycle transitions.

### Negative controls

All ineligible/adversarial cases remain proposals, conflicts, review-required decisions, or refusals as appropriate.

### Efficacy

Currentness benchmarks MAY demonstrate user-visible benefit.

They are an outcome measure, not the authority proof.

## Versioning and activation

This ADR deliberately assigns no:

- Runtime Baseline number;
- ranking-policy version;
- public-contract version;
- PAMA schema version;
- auto-application profile version.

Those identities are chosen when an implementation plan is gated against the then-current repository.

The implementation MUST NOT be bundled retroactively into an already-declared runtime baseline.

Activation is explicit.

The first implementation SHOULD default to disabled until:

1. the profile is frozen;
2. the implementation passes authority/lifecycle negative controls;
3. the required runtime succession evidence is accepted.

## Interaction with ADR-039

ADR-039 governs query-conditioned applicability.

This ADR governs durable proposal application.

They compose as:

```text
before lifecycle application:
  Option A may constrain current recall
  via interpreted cross-fact evidence

after governed lifecycle application:
  durable supersession/correction state
  may become the stronger currentness basis
```

Neither ADR allows recency to become authority.

## Interaction with ADR-004 and PAMA

ADR-004 remains superior on mutation authority.

This ADR does not define a new governance authority.

It defines one profile for asking the existing authority system to approve low-risk lifecycle mutation automatically.

If the PAMA decision table or runtime cannot represent the necessary outcome safely, the correct response is to keep the proposal open, not to bypass PAMA.

## Interaction with ADR-023

Automatic application creates a correction/supersession history.

It does not erase the old fact.

Historical evidence and audit lineage survive.

## Consequences

### Positive

- allows a bounded path from detected change to durable lifecycle truth;
- avoids requiring external orchestration for every genuinely low-risk state correction;
- keeps authority inspectable;
- retains PAMA as the mutation boundary;
- makes automatic behavior auditable and reversible;
- separates current-query inference from durable state transition;
- prevents benchmark logic from becoming mutation logic.

### Costs

- requires explicit profile design;
- requires reliable actor/source/scope identity;
- requires transaction/state binding;
- requires concurrency handling;
- requires durable receipts;
- requires more negative testing than a simple `correct()` call;
- some apparently obvious changes will remain proposals because evidence is incomplete.

These costs are intentional.

## Rejected alternatives

### Newest write wins

Rejected.

Transaction order is not supersession authority.

### High confidence auto-applies

Rejected.

Confidence is not authority.

### Same slot always auto-corrects

Rejected.

Slots may be multi-valued, scoped, disputed, or sourced differently.

### Option A automatically becomes Option D

Rejected.

Read-path applicability is not lifecycle mutation.

### Auto-apply and log afterward

Rejected.

Audit after mutation does not substitute for authority before mutation.

### One global auto-apply flag

Rejected.

Consequence varies by target, scope, source, authority, and reversibility.

### Human approval for every transition

Rejected as the only architecture.

PAMA exists specifically to permit low-risk adaptation while concentrating review on consequence boundaries.

### Benchmark threshold unlocks auto-application

Rejected.

Benchmark efficacy is not mutation authority.

## Decision status

**Proposed.**

This ADR documents the architecture requested by the #671 owner ruling so implementation does not reach another undefined authority boundary.

It MUST remain Proposed while Option A is still being qualified.

Promotion to Accepted requires a separately gated implementation tranche demonstrating:

- authority correctness;
- lifecycle correctness;
- concurrency/state binding;
- negative controls;
- restart durability;
- rollback/revocation;
- explicit runtime succession evidence.

Until then, Agent Memory may emit proposals and use Option A read-path applicability, but it does not gain this automatic lifecycle application authority.
