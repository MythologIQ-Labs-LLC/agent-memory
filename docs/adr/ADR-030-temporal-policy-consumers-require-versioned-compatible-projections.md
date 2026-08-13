# ADR-030: Temporal Policy Consumers Require Versioned Compatible Projections

## Status

Proposed

## Context

Agent Memory increasingly interacts with systems that consume current or historical context to make policy decisions. Existing architecture already separates canonical memory from a vendor-neutral Governance Context Projection and separates Agent Memory PAMA decisions from optional external policy decisions.

That separation is necessary but not sufficient when memory semantics evolve.

Agent Memory allows application/domain schemas, currentness, scope, corrections, derivations, and projections to change over time. External policy systems also bind evaluation to schemas, policy artifacts, event models, and runtime capabilities.

A projection can therefore remain syntactically valid while becoming semantically stale for the consumer that evaluates it.

Examples include:

- Agent Memory discovers a new domain type or changes the meaning of an existing field while a Cedar/Dogwood action schema remains unchanged;
- a previously valid historical approval remains in a temporal trace after the approving authority is revoked;
- a target temporal engine is configured with a shorter history window than the memory question requires;
- a target event schema no longer provides the isolation semantics assumed by the projection;
- a Cedarling pushed-data value is shadowed by higher-precedence inline request context;
- the target policy store/schema changes after the projection or external decision was produced.

Cedar's own schema guidance makes this class of risk explicit: a changed schema can invalidate previously validated policies, and policies that error during authorization may not contribute to the decision. Cedarling likewise requires dynamic context fields to be declared in the Cedar schema rather than accepting arbitrary untyped data.

Dogwood adds another dimension. Its temporal policies evaluate a stateful event history under a service/event schema and Cedar action schema. Its public event model supports custom event kinds, bounded temporal windows, provider context, and optional pin-based key-local semantics. A historical event can remain matchable even when Agent Memory would no longer consider that event current authority or current context.

The repository already has the pieces needed to solve most of this problem:

- ADR-014: schema registry and type evolution;
- ADR-029: Governance Context Projection is derived context, not authority;
- progressive domain-schema discovery and governed domain-schema mutation;
- derivation currentness evaluation;
- External Enforcement Decision Projection and exact `input_identity` binding;
- monotonic external policy composition proved against real OPA and Cedar.

What is missing is an explicit compatibility/currentness boundary between an evolving semantic projection and the exact target policy/temporal contract.

## Decision candidate

Adopt a **versioned policy-projection compatibility boundary**.

A memory-derived projection MUST NOT be treated as current consequential input to an external policy or temporal consumer merely because it can be serialized into that consumer's request format.

Before consequential use, the implementation must establish a compatibility/currentness evaluation binding the projection to the target schema, policy identity, relevant capabilities, and isolation assumptions.

```text
canonical Agent Memory
        |
        v
versioned governed projection
        |
        v
projection compatibility/currentness evaluation
        |
        +--> current -> consumer adapter/evaluation
        |
        +--> migration_required
        |    incompatible
        |    unknown
        |        -> not current consequential input
        |
        v
external decision evidence
        |
        v
existing monotonic composition
```

The compatibility evaluation is evidence about the projection/consumer relationship. It has no authority effect of its own.

## Core invariant

> **A policy consumer may rely on a memory-derived projection as current only when the projection is bound to and compatible with the exact semantic contract under which that consumer evaluates it.**

Serialization success is not semantic compatibility.

```text
valid JSON != compatible policy input
historical event match != current authority
schema similarity != schema compatibility
consumer cache != canonical memory
policy ALLOW != approval or execution
```

## Ownership model

### Agent Memory core owns

- canonical memory identity and retained history;
- provenance and derivation;
- event time and valid/current time distinctions;
- lifecycle, correction, supersession, dispute, revocation, and deletion semantics;
- scope/isolation semantics;
- domain-schema identity/evolution where represented;
- PAMA memory-specific mutation/downstream-authority decisions;
- currentness evidence for memory/derived state.

### Projection layer owns

- selecting the smallest consumer-relevant representation;
- preserving source/root references and derivation identity;
- declaring projection profile/version;
- binding structured currentness/scope/schema evidence needed by the consumer contract;
- minimization and sensitivity handling;
- reconstructability from canonical state plus declared derivation logic.

The projection remains derived state and is not the sole authoritative copy.

### Compatibility/currentness layer owns

- comparing the projection's semantic assumptions with the exact target contract;
- binding target schema/policy/capability/isolation identity;
- returning one bounded compatibility state;
- preserving reason/evidence refs;
- triggering revalidation/migration obligations without self-authorizing those consequences.

It does not perform domain-schema migration merely because migration is required.

### Consumer adapter owns

- Dogwood/Cedar/Cedarling/other API vocabulary;
- target event/action/entity/context mapping;
- consumer version/source compatibility;
- target policy/event schema parsing and validation;
- consumer-specific failure behavior that is at least as strict as the generic boundary;
- evidence extraction from consumer decisions/logs.

Consumer-specific fields do not enter canonical Agent Memory merely because the adapter needs them.

## Compatibility evaluation

A generic evaluation should bind, where applicable:

```text
evaluation_id
projection_ref
projection_profile
projection_version
projection_digest
source_memory_refs
source_domain_schema_ref
source_domain_schema_digest
source_currentness_ref
source_currentness_status
consumer_kind
consumer_version_or_source_pin
target_action_schema_digest
target_event_schema_digest
target_policy_store_or_artifact_ref
target_policy_digest_or_version
required_temporal_horizon
target_temporal_horizon
isolation_strategy
isolation_evidence_refs
compatibility_status
reason_codes
evidence_refs
evaluated_at
authority_effect = none
```

Not every consumer needs every field. Omitted target dimensions must be explicitly inapplicable rather than silently unknown where the distinction matters.

## Compatibility states

### `current`

All compatibility dimensions required by the declared profile are established for the exact projection and target contract.

This means only:

> the projection may be supplied as current input under this compatibility contract.

It does not mean the memory is true, admitted, authorized, certified, or safe to execute.

### `migration_required`

A known semantic/schema change means the target projection/schema/policy must be evolved and revalidated before the projection can be treated as current.

This state creates an obligation to route any migration through normal schema/PAMA governance. It does not authorize the migration.

### `incompatible`

A concrete contradiction prevents the projection from satisfying the target contract, for example:

- required field/type cannot be represented;
- target temporal horizon is too short;
- target isolation model cannot satisfy the source scope;
- target schema/action/event identity conflicts with the projection;
- target policy artifact is not the expected one.

### `unknown`

Required evidence is absent or insufficient to establish compatibility.

```text
unknown != current
```

Consequential use that requires current compatibility must fail safe or route to review/revalidation according to the surrounding policy.

## Historical evidence remains immutable

Compatibility is append-only currentness evidence, not a mutable truth field on the historical projection.

```text
T1 projection P under schema S1
 -> evaluation E1 = current

T2 source schema becomes S2
 -> P remains historical projection evidence
 -> evaluation E2 = migration_required

T3 rebuilt projection P2 targets S2-compatible consumer schema
 -> P2 has new identity
 -> evaluation E3 may be current
```

E2 does not rewrite P or E1. It records that the old projection is no longer current for the later target state.

This inherits the historical/current split from the Derivation Currentness profile.

## Temporal-event projection is not canonical history

A temporal consumer such as Dogwood may maintain a stateful trace containing events projected from Agent Memory.

That trace is a consumer-specific derived representation.

```text
canonical Agent Memory history
!= Dogwood temporal trace
!= Cedarling pushed-data cache
!= policy decision log
```

A consumer may persist, partition, compact, or rebuild its trace according to its own implementation contract. Agent Memory deletion/correction/currentness claims remain governed by Agent Memory's canonical and known-derived-state semantics.

A surviving consumer trace may therefore constitute residue that must be considered for deletion/retention obligations, but it cannot become the authority that defines canonical memory truth.

## Historical event versus current policy fact

Where useful, an adapter should distinguish:

```text
historical event projection
```

from:

```text
current provider/context projection
```

Example:

- history: a human approved action X at T1;
- current fact: that approval authority is now revoked at T2.

A temporal engine may need both to answer a policy question correctly. Replaying T1 alone must not imply current authority at T2.

The exact representation remains adapter/profile-specific. The invariant is that currentness cannot be inferred from historical presence.

## Temporal capability binding

A temporal query's required horizon is part of semantic compatibility.

If the memory question requires a window larger than the target temporal system can evaluate, the result is a capability mismatch.

```text
required horizon > target horizon
-> incompatible
```

It is not negative evidence that no relevant event occurred.

## Isolation binding

Target isolation assumptions must be explicit.

For Dogwood, the public event-schema contract exposes one example: universal symmetric pins can provide key-local semantics and a partition guarantee, while partial/asymmetric pins may silently retain global-trace semantics.

An adapter that claims temporal isolation must validate the actual target event schema or provide an independently stronger host-partition guarantee.

```text
pin exists
!= partition guarantee
```

Agent Memory scope/isolation cannot be widened because the target engine is capable of seeing a broader trace.

## Cedar / Cedarling schema evolution

Cedar schema changes represent authorization-model changes and can require policy revalidation.

Therefore a compatibility profile for Cedar-family consumers must not mark a changed target/source schema relationship current solely because the request can still be constructed.

For Cedarling dynamic context data:

- pushed fields remain constrained by the declared Cedar schema;
- TTL/expiry is consumer cache behavior, not Agent Memory currentness by itself;
- inline request values can shadow pushed Agent Memory values;
- decision evidence must bind to the values actually evaluated, not merely those previously pushed.

Policy-store identity/version, Cedar schema digest, and decision diagnostics are useful adapter evidence. They do not become standing Agent Memory authority.

## External decisions remain monotonic

This ADR does not alter the existing external-policy composition lattice.

A compatible projection enables evaluation. It does not give the consumer permission to widen PAMA.

```text
PAMA deny + external allow -> deny
PAMA review + external allow -> review
PAMA allow + external deny -> deny
```

A Dogwood temporal match, Cedar ALLOW, or Cedarling ALLOW is policy-decision evidence.

It is not:

- human approval;
- reusable grant;
- enforcement witness;
- execution evidence;
- memory truth;
- certification.

## Dogwood public-source maturity boundary

The first Dogwood comparator is pinned to public commit:

`c6237c88099b3f492ecc5fcee42df06a19224b97`

The public repository is Apache-2.0, presents a reference interpreter, currently has no published releases, and its current mainline is explicitly synchronized as a sanitized snapshot from an internal source without internal git history.

Therefore:

1. the public contract may be used as exact-source evidence;
2. unpublished/internal behavior remains unknown;
3. an Agent Memory adapter must not depend on guessed future/internal features;
4. a later public source change requires comparator revalidation before compatibility evidence is reused.

This maturity boundary protects both projects from accidental architectural overclaiming.

## Relationship to ADR-029

ADR-029 answers:

> What is a Governance Context Projection allowed to be?

ADR-030 answers:

> When may a versioned projection be treated as semantically current input for the exact consumer evaluating it?

ADR-030 depends on ADR-029's anti-authority-laundering boundary but is independently falsifiable.

```text
ADR-029:
projection != authority

ADR-030:
projection serializes successfully != projection is current/compatible for target
```

## Relationship to ADR-014

ADR-014 establishes schema/type evolution as governance.

ADR-030 carries that obligation across an interoperability boundary. A consumer's convenience does not erase migration/versioning requirements.

A compatibility evaluation may report `migration_required`. The migration itself remains governed by ADR-014, domain-schema mutation semantics, PAMA, and the relevant adapter/profile contract.

## Relationship to derivation currentness

ADR-030 reuses the same evidence discipline:

```text
historical record remains immutable
+
new evidence evaluates current applicability
```

Projection compatibility should not create a competing mutable current-truth model.

## Acceptance evidence required

ADR-030 MUST remain Proposed until executable evidence demonstrates at least:

1. source/domain-schema drift prevents an old projection from remaining `current`;
2. source currentness `unknown` or `revalidation_required` cannot become current policy input by default;
3. historical projection identity remains stable when later compatibility changes;
4. rebuilding after schema migration creates a new projection identity rather than rewriting history;
5. target schema/policy identity drift is detected;
6. temporal horizon mismatch is represented as capability incompatibility rather than negative memory evidence;
7. isolation claims require explicit target isolation evidence;
8. a Dogwood partial-pin case cannot masquerade as a partition guarantee;
9. external ALLOW cannot loosen PAMA;
10. consumer-specific fields remain outside canonical memory;
11. at least one exact-pinned real Dogwood public-source comparator uses the generic seam without requiring Dogwood semantics in core;
12. decision evidence remains separate from enforcement/execution evidence;
13. a Cedar/Cedarling schema-drift scenario demonstrates the policy-revalidation obligation;
14. policy-generated outcomes remain distinguishable from independent human adjudication/reusable authority.

## Rejected alternatives

### Export canonical memory directly to each policy consumer

Rejected. It couples consumers to internal memory complexity, leaks unnecessary content, and makes schema evolution harder to govern.

### Treat successful serialization as compatibility

Rejected. A syntactically valid request can still carry stale meanings, wrong types, insufficient temporal capability, or incorrect isolation assumptions.

### Make Dogwood's temporal event store the canonical Agent Memory event log

Rejected. Dogwood's trace serves temporal policy evaluation. Agent Memory retains broader lifecycle, provenance, currentness, correction, scope, deletion, and authority responsibilities.

### Copy Dogwood/Cedar/Cedarling schema concepts into canonical memory

Rejected. Consumer semantics remain behind adapters unless repeated evidence exposes a genuinely general memory primitive.

### Automatically migrate policy schemas whenever Agent Memory's domain schema changes

Rejected. Migration is consequential state change and must cross normal schema/PAMA governance.

### Treat policy DENY as failure and policy ALLOW as authority

Rejected. A valid policy denial is a decision. An allow is not human approval, reusable authority, or execution evidence.

## Initial implementation

The first evidence slice should be Python-first and provider-neutral:

1. `policy-projection-compatibility` JSON Schema;
2. deterministic reference evaluator;
3. adversarial fixtures covering source drift, target drift, currentness, horizon, isolation, and stale consumer versions;
4. a focused evidence report;
5. an optional Dogwood adapter/comparator pinned to exact public source;
6. no Dogwood/Cedar/Cedarling core dependency;
7. wiki/visual documentation after executable evidence establishes the boundary.

## Related

- #67
- #255
- ADR-014
- ADR-021
- ADR-028
- ADR-029
- `docs/profiles/governance-context-projection-profile.md`
- `docs/profiles/external-enforcement-decision-profile.md`
- `docs/profiles/derivation-currentness-profile.md`
- `docs/explorations/memory-architectures/progressive-domain-schema-discovery.md`
- `docs/research/temporal-policy-semantic-mediation.md`
