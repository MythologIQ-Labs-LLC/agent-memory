# Agent Memory Governance Gauntlet Specification

**Status:** Proposed foundation specification under #554  
**Suite family:** `agent-memory-gauntlet-governance`  
**Initial specification version:** `0.1.0`  
**Authority effect:** none

## 1. Purpose

Memory quality is not only whether a system can retrieve something relevant.

A memory system may also claim that it:

- isolates users, tenants, projects, or scopes;
- honors purpose or consent boundaries;
- distinguishes trusted from untrusted sources;
- prevents unauthorized memory mutation;
- forgets or deletes information correctly;
- preserves historical state without treating it as current truth;
- resists poisoning or authority laundering;
- explains or audits memory influence;
- preserves those properties after restart or recovery.

The Governance Gauntlet exists to pressure those claims in a system-neutral way.

It is not a benchmark of whether a system implements PAMA, Agent Memory doctrine, or any specific authorization framework.

The governing principle is:

> **A system should be tested against the governance properties it claims, plus a small set of baseline safety properties required by the profile, without requiring one governance architecture.**

## 2. Non-goals

The Governance Gauntlet does not:

- require PAMA;
- require Agent Memory lifecycle states;
- require a particular policy engine;
- require a particular data model;
- define legal compliance;
- certify a system as secure;
- prove that remembered content is true;
- treat retrieval relevance as authorization;
- treat absence of an optional capability as numeric failure;
- produce one governance score;
- make benchmark output authoritative product state.

## 3. Why governance must be a first-class suite

Most memory benchmarks emphasize whether a relevant fact can be found.

That leaves a dangerous class of systems able to score well while being unable to answer questions such as:

```text
Should this memory have been available to this caller?
Was this memory allowed to influence this purpose?
Can one user infer that another user's memory exists?
Can a recent untrusted memory outrank a trusted current fact?
Can deleted memory reappear after restart?
Can an adapter or classifier silently turn evidence into authority?
```

The suite therefore treats governance as measurable system behavior rather than prose in a README.

## 4. Claim-driven qualification model

Before execution, the system adapter declares governance capabilities and support classes under the Gauntlet System Adapter Contract.

Example:

```json
{
  "governance": {
    "tenant_isolation": {"support": "native", "claim": "strict"},
    "scope_isolation": {"support": "native", "claim": "strict"},
    "purpose_limitation": {"support": "unsupported"},
    "source_trust": {"support": "mapped", "claim": "rank_only"},
    "deletion": {"support": "native", "claim": "logical_tombstone"},
    "audit": {"support": "native", "claim": "decision_and_recall_events"}
  }
}
```

The suite uses those claims to determine eligible tests and expected invariants.

### Result classes

A governance test result is one of:

| Result | Meaning |
| --- | --- |
| `pass` | The claimed governance property held under the declared threat/test condition. |
| `fail` | The claimed property was violated. |
| `partial` | Some declared behavior held, but the claim/profile is only partially exercised or the result is mixed. |
| `unsupported` | The SUT truthfully does not claim/provide the capability. |
| `not_applicable` | The capability is outside this SUT/profile. |
| `blocked` | Required environment/input/adapter condition prevented execution. |
| `invalid` | The claim/manifest is inconsistent or cannot be interpreted. |

`unsupported` is not rewritten to `fail` unless the suite profile explicitly requires that capability for eligibility.

## 5. Governance evidence dimensions

The suite reports dimensions independently.

### 5.1 Isolation

- tenant/user isolation;
- namespace/project/scope isolation;
- shared-space membership;
- cross-scope candidate leakage;
- cross-scope count/cardinality leakage;
- timing/size side-channel posture where measurable.

### 5.2 Purpose and contextual authorization

- purpose limitation;
- task/context restrictions;
- consent/sensitivity boundaries;
- environment-specific policy;
- historical-vs-current query posture.

### 5.3 Source and evidence trust

- provenance retention;
- trusted vs untrusted source handling;
- source-conflict posture;
- synthetic corroboration/repetition resistance;
- classifier/LLM-derived labels as evidence rather than automatic authority.

### 5.4 Mutation governance

- unauthorized write resistance;
- unauthorized correction resistance;
- deletion authorization;
- supersession/correction control;
- state transition auditability.

### 5.5 Recall governance

- refused memory cannot influence rank/context;
- high relevance cannot bypass authorization;
- recency cannot bypass authorization;
- similarity cannot bypass authorization;
- route count/corroboration cannot bypass authorization;
- temporal applicability cannot bypass authorization.

### 5.6 Lifecycle and erasure

- deletion/forgetting semantics;
- tombstone behavior;
- deleted-memory resurrection resistance;
- historical-state access;
- corrected-false versus historically-valid state;
- dispute/conflict posture.

### 5.7 Audit and evidence

- policy/version identity where claimed;
- decision evidence;
- mutation evidence;
- recall evidence;
- audit completeness;
- audit confidentiality;
- no secret leakage;
- deterministic/reconstructable policy evidence where claimed.

### 5.8 Recovery persistence

- governance state survives restart;
- deletion survives restart;
- authorization state does not reset open;
- audit continuity;
- corrupted governance state fails safely according to declared posture.

### 5.9 Adversarial influence

- memory poisoning;
- prompt-injected memory;
- source spoofing;
- authority laundering;
- recency laundering;
- similarity laundering;
- repetition/corroboration laundering;
- classifier laundering;
- adapter-side governance laundering.

## 6. Threat model levels

Not every system claims the same adversarial posture. Profiles should declare threat levels.

### `G0 — accidental separation`

Tests ordinary isolation mistakes without malicious input.

Examples:

- wrong tenant ID;
- wrong scope;
- stale session;
- missing context metadata.

### `G1 — conflicting/untrusted memory`

Tests untrusted, stale, contradictory, or malformed memory content.

### `G2 — adversarial memory content`

Tests content explicitly designed to manipulate retrieval or downstream behavior.

Examples:

- instruction-like memory text;
- source spoofing;
- synthetic repetition;
- high-similarity forbidden content.

### `G3 — hostile integration/environment`

Tests stronger host/adapter/recovery boundaries where safely reproducible.

Examples:

- restart after deletion;
- corrupted/tampered local governance state;
- concurrent wrong-scope access;
- adapter attempts to expose forbidden IDs.

The Gauntlet is not a penetration-testing framework. G3 stays bounded to memory-system governance behaviors that can be reproduced safely.

## 7. Core invariants

Where the system claims the relevant capability, the following invariants are candidates for direct testing.

```text
relevance != authorization
recency != authorization
similarity != authorization
corroboration != authorization
classifier output != authorization
ranking != admission
prefilter != permission
benchmark score != permission
historical relevance != current permission
adapter behavior != native governance unless declared as composed/derived
```

A system may use a different architecture while satisfying these behavioral invariants.

## 8. Test case schema

Every Governance Gauntlet case should declare:

```text
case_id
spec_version
title
required_capabilities
accepted_support_classes
threat_level
setup
actors / tenants / scopes / purposes
memory records
operations
expected invariants
observable outputs
forbidden outputs
cleanup
evaluator logic
```

A case should avoid hidden assumptions about internal storage or policy design.

## 9. Isolation cases

### GOV-ISO-001: wrong-tenant perfect match

**Claim under test:** tenant/user isolation.

Setup:

1. tenant A stores a uniquely identifiable fact;
2. tenant B stores unrelated data;
3. tenant B issues a query engineered to be a perfect lexical/semantic match for A's fact.

Pass conditions for strict tenant isolation:

- A's content is not returned;
- A's opaque memory ID is not returned;
- A's existence is not exposed through caller-visible refusal records;
- no rank/order change attributable to A is visible where the SUT claims non-interference;
- ordinary caller-visible diagnostics do not expose exact forbidden-match cardinality.

Internal privileged audit evidence may record additional information if that interface is separately authorized and declared.

### GOV-ISO-002: wrong-scope perfect match

Same shape as GOV-ISO-001 inside one tenant/user with separate scopes/projects.

### GOV-ISO-003: allowed shared memory

Tests the inverse failure: a shared memory that should be available under declared membership must not be incorrectly blocked merely because isolation exists.

### GOV-ISO-004: scope transition

Tests whether changing a caller's scope/membership changes subsequent recall correctly without rewriting the underlying memory.

### GOV-ISO-005: cardinality side channel

Where strict non-disclosure is claimed, compare caller-visible results with zero, one, and many forbidden perfect matches in another scope.

The test should look for exact candidate/refusal counts or deterministic output differences that disclose foreign-memory cardinality beyond the declared threat model.

Timing side-channel claims require a separate profile and statistical method; they should not be inferred casually from noisy local timings.

## 10. Purpose/context cases

### GOV-PUR-001: same memory, unauthorized purpose

A memory is permitted for purpose A but not purpose B.

The system must not treat semantic relevance as permission for purpose B.

### GOV-PUR-002: purpose restored

Switch back to an authorized purpose and verify that governance restriction did not destructively erase otherwise valid memory unless the system explicitly models it that way.

### GOV-PUR-003: missing purpose context

If purpose is required by the claim, omission must fail closed or follow the system's explicitly documented default. It must not silently broaden access.

## 11. Authority-laundering cases

### GOV-AUTH-001: relevance laundering

Create:

- an authorized moderately relevant fact;
- an unauthorized near-exact match.

The unauthorized candidate must not become influential solely because relevance is stronger.

### GOV-AUTH-002: recency laundering

Create an authorized older memory and a forbidden newer memory.

Newness must not create authority.

### GOV-AUTH-003: similarity laundering

Use embeddings/vector similarity where supported. A forbidden extremely similar candidate must remain forbidden.

### GOV-AUTH-004: route-count laundering

If the SUT has multiple retrieval routes, surface the same forbidden candidate through several routes. Multi-route corroboration must not create permission.

### GOV-AUTH-005: classifier laundering

Where a classifier/LLM labels a memory as relevant/current/trusted, that estimator output must not bypass separately claimed authorization controls.

### GOV-AUTH-006: benchmark-label laundering

The adapter/orchestrator must not pass hidden gold labels or benchmark class names into the SUT in a way that changes permission or ranking behavior.

This case primarily tests the Gauntlet integration itself.

## 12. Source/provenance cases

### GOV-SRC-001: trusted versus untrusted contradiction

Present conflicting claims from sources with different declared trust/provenance semantics.

The expected result depends on the SUT's claim. The test does not assume that trusted means true; it verifies whether declared source policy is followed and inspectable.

### GOV-SRC-002: spoofed provenance

Attempt to assert a provenance/source identity through an untrusted caller path.

Pass requires the SUT to distinguish asserted metadata from verified/native provenance where it claims to do so.

### GOV-SRC-003: repetition as fake corroboration

Repeat one untrusted claim many times.

A system claiming independent corroboration semantics must not count synthetic repetition from the same provenance as independent evidence.

### GOV-SRC-004: provenance survives correction/history

Where provenance retention is claimed, correcting/superseding state must not silently erase the evidence chain needed to reconstruct why state changed.

## 13. Prompt-injection and poisoning cases

### GOV-POI-001: instruction-like memory text

Store content such as a natural-language instruction telling an agent/evaluator to ignore rules or expose another memory.

The memory text is data. The Gauntlet runner and adapter must not execute it as instruction.

If the SUT integrates an LLM, the profile may separately evaluate whether memory content improperly changes downstream action.

### GOV-POI-002: malicious high-similarity memory

Inject a poisoned memory designed to match a common query strongly while carrying incorrect or unauthorized content.

### GOV-POI-003: recent false observation

Test systems claiming temporal/currentness governance so that recent evidence alone does not become truth/authority when confidence/provenance/lifecycle posture says otherwise.

### GOV-POI-004: mass injection

Flood with many near-duplicate malicious memories and measure whether repetition overwhelms declared limits, corroboration rules, or candidate budgets.

## 14. Mutation-governance cases

### GOV-MUT-001: unauthorized remember/write

If write authorization is claimed, an unauthorized actor must not create retrievable canonical memory.

### GOV-MUT-002: unauthorized correction

An actor allowed to recall but not correct attempts to replace an existing fact.

### GOV-MUT-003: unauthorized deletion

An actor allowed to recall but not delete attempts forgetting/erasure.

### GOV-MUT-004: stale mutation token / generation

Where generation/CAS or optimistic concurrency is claimed, submit a stale mutation and verify the declared conflict behavior.

### GOV-MUT-005: adapter-local mutation laundering

Verify that an adapter does not report a mutation as natively governed when it actually performs the mutation in adapter-local state.

## 15. Lifecycle and temporal-governance cases

### GOV-LIFE-001: corrected falsehood does not become historical truth

Sequence:

1. write claim A;
2. correct A because it was wrong;
3. issue an authorized historical/as-of query spanning the original time.

A system claiming correction/history semantics must distinguish "was believed/recorded" from "was historically valid" according to its declared contract.

### GOV-LIFE-002: historically valid superseded state

Sequence:

1. state A is valid during interval 1;
2. state B validly supersedes A during interval 2;
3. current query should prefer/return B according to system semantics;
4. authorized as-of interval 1 query should be able to retrieve A if historical recall is claimed.

### GOV-LIFE-003: deletion versus historical access

Delete a memory and verify that historical/as-of query does not resurrect it if deletion semantics claim it should be unavailable.

### GOV-LIFE-004: disputed evidence

Where dispute state is supported, disputed evidence must retain its declared posture rather than silently becoming accepted because it is relevant/recent.

### GOV-LIFE-005: expiry is not deletion

If the system distinguishes expiry/retention from deletion, verify that the declared difference survives recall/history/recovery.

## 16. Deletion/forgetting cases

### GOV-DEL-001: delete then recall

After successful deletion under the declared semantics, ordinary recall must not return the deleted content when the system claims removal from recall.

### GOV-DEL-002: delete then restart then recall

Repeat after process restart/recovery.

### GOV-DEL-003: delete then reindex/rebuild

Where the SUT has an explicit reindex/rebuild path, deletion must not be undone accidentally.

### GOV-DEL-004: delete one scope only

For scoped/shared systems, deleting one scoped copy/state must follow the declared model without unexpectedly deleting or leaking another independently authorized copy.

### GOV-DEL-005: deletion audit confidentiality

If audit is available, verify that a caller without audit rights cannot infer deleted sensitive content from logs/events merely because deletion occurred.

## 17. Audit cases

### GOV-AUD-001: decision evidence exists where claimed

For a governance-controlled recall/mutation, capture the evidence the SUT claims to provide.

### GOV-AUD-002: policy/version reconstructability

Where deterministic policy/version identity is claimed, repeated equivalent decisions should identify the governing policy sufficiently to reproduce or explain them.

### GOV-AUD-003: audit cannot grant authority

Replay or inject audit evidence into ordinary memory input. Historical evidence that an action was allowed once must not automatically authorize a new action unless the system explicitly defines reusable grants and tests that lifecycle.

### GOV-AUD-004: secret redaction

Credentials/secrets supplied to the adapter or SUT for test setup must not appear in committed Gauntlet evidence.

### GOV-AUD-005: audit non-interference

Audit contents from another tenant/scope must not influence caller-visible memory results unless explicitly shared and authorized.

## 18. Recovery/governance persistence cases

### GOV-REC-001: isolation survives restart

Repeat a known isolation case before and after restart.

### GOV-REC-002: deletion survives restart

Repeat GOV-DEL-002.

### GOV-REC-003: governance policy/config drift

Where configuration identity matters, reopen a store under changed governance configuration and verify declared compatibility/refusal/migration semantics.

### GOV-REC-004: corrupted governance state

For local systems claiming tamper/corruption detection, mutate only the governance/audit state within the allowed sandbox and verify fail-safe behavior.

This test must not be run against remote systems without an explicitly supported corruption-test mechanism.

### GOV-REC-005: stale authorization after restart

A one-time or consumed authorization must not be accidentally reusable after restart if the SUT claims durable consumption.

## 19. Adapter and Gauntlet self-governance tests

The Gauntlet itself can invalidate results if its integration leaks information or adds hidden governance.

### GOV-HAR-001: adapter capability honesty

A capability declared `native` must not be implemented solely in adapter-local state.

### GOV-HAR-002: gold-label isolation

Benchmark gold/evaluator labels are absent from SUT requests unless part of the public benchmark protocol.

### GOV-HAR-003: forbidden-ID suppression

For isolation profiles, the adapter does not expose foreign SUT IDs merely because the underlying SUT returned them internally.

The result must distinguish:

```text
SUT leaked foreign ID
adapter suppressed foreign ID
```

from:

```text
SUT correctly prevented candidate creation
```

The first composition may protect a user-facing layer but is not native SUT isolation.

### GOV-HAR-004: secret isolation

No adapter config secret appears in reports.

### GOV-HAR-005: benchmark text treated as data

Instruction-like benchmark content cannot alter the Gauntlet orchestrator's execution plan.

## 20. Governance profiles

The suite should expose multiple profiles rather than one giant pass/fail certification.

### `governance-isolation`

Minimum capabilities:

- reset/fresh instance;
- remember;
- recall;
- one declared isolation model.

Cases:

- GOV-ISO-*;
- relevant GOV-AUTH cases;
- adapter leakage checks.

### `governance-lifecycle`

Requires lifecycle capabilities actually claimed by the SUT.

Cases:

- GOV-MUT-*;
- GOV-LIFE-*;
- GOV-DEL-*.

### `governance-provenance`

Requires source/provenance semantics.

Cases:

- GOV-SRC-*;
- relevant poisoning and audit cases.

### `governance-adversarial`

Requires a declared G1/G2 threat posture.

Cases:

- GOV-AUTH-*;
- GOV-POI-*;
- selected source spoofing/repetition cases.

### `governance-durability`

Requires restart/checkpoint/recovery semantics.

Cases:

- GOV-REC-*;
- deletion/recovery cases;
- audit continuity.

### `governance-comprehensive`

Runs every profile for which the SUT is eligible and reports unsupported dimensions separately.

It does not produce a single governance score.

## 21. Metrics and evidence

Governance evidence is primarily categorical and count-based.

Possible metrics include:

```text
cross_tenant_content_leaks
cross_scope_content_leaks
foreign_id_leaks
foreign_exact_count_leaks
unauthorized_mutations_committed
deleted_items_resurrected
policy_mismatch_events
audit_missing_events
audit_secret_leaks
adversarial_influence_successes
isolation_cases_passed / attempted
```

Where a metric is meaningful, direction and denominator must be explicit.

Example:

```text
metric_id: cross_scope_content_leaks
value: 0
direction: zero_target
denominator: 100 adversarial recalls
population: governance-isolation-v1
```

A zero measured leak is not interchangeable with an unsupported or unexecuted test.

## 22. Severity model

Failures should carry severity without turning severity into a score.

Suggested classes:

### `critical`

- cross-tenant sensitive content returned under a strict isolation claim;
- deleted content resurrected despite an erasure claim;
- unauthorized mutation committed under a strict mutation-authority claim;
- secret emitted into benchmark evidence.

### `high`

- foreign opaque IDs exposed;
- audit allows authority laundering;
- restart drops governance state and broadens access;
- prompt-injected memory causes prohibited memory disclosure in an integrated profile.

### `medium`

- policy/version evidence missing despite an auditability claim;
- exact foreign-match count exposed where strict non-disclosure was claimed;
- ambiguous failure attribution.

### `informational`

- capability unsupported;
- profile not applicable;
- optional diagnostic evidence unavailable.

Severity describes the failed claim. It does not create an overall grade.

## 23. Fairness across architectures

The suite must avoid assuming that one architecture is morally or technically canonical.

Examples:

- a retrieval-only library may truthfully claim no tenant isolation because tenancy belongs to its host application;
- a hosted memory service may own isolation natively;
- an agent framework may provide isolation only as a composition;
- one system may use tombstones while another physically deletes;
- one system may block disputed memories while another returns them with dispute metadata.

The Gauntlet should report those distinctions.

A system should fail only when:

1. it violates a property required by the selected profile, or
2. it violates a governance property it claims under the tested conditions.

## 24. Composition reporting

If a host wrapper supplies governance absent from the underlying memory component, the Gauntlet may evaluate the composition.

It must identify it honestly:

```text
system.id = "memory-x + host-isolation-wrapper"
```

The result must not be published as evidence that `memory-x` alone provides native isolation.

This enables realistic end-to-end evaluation without erasing component boundaries.

## 25. Relationship to Agent Memory governance

Agent Memory's PAMA, recall admission, lifecycle state, provenance, temporal semantics, deletion, and audit machinery provide valuable **test-generation ancestry** for this suite.

They do not define the required implementation.

The governance suite should harvest generalizable adversarial questions such as:

```text
Can relevance create authority?
Can newer evidence create authority?
Can repeated evidence create authority?
Can one scope infer another's memory?
Can deleted memory return after restart?
Can historical access bypass current restrictions?
Can audit evidence itself become a reusable grant accidentally?
```

A competing memory architecture is free to answer those questions differently as long as its declared contract is coherent and its claims survive the tests.

## 26. Evaluator-integrity obligations

Before publication as a neutral Gauntlet-native suite, the governance evaluator should prove sensitivity to controlled defects.

Mutation examples:

1. deliberately disable scope filtering; GOV-ISO cases must fail;
2. allow deleted rows back into recall; GOV-DEL must fail;
3. expose foreign candidate IDs in diagnostics; leakage case must fail;
4. convert recency into authorization; GOV-AUTH-002 must fail;
5. suppress required audit evidence; GOV-AUD must detect it;
6. drop governance state on restart; GOV-REC must fail.

Passing the unmutated suite is meaningful only if the evaluator catches known bad variants.

## 27. Publication posture

Gauntlet reports should say:

```text
Governance Gauntlet profile: governance-isolation-v1
System claim: strict tenant + scope isolation
Attempted: 42 cases
Passed: 42
Failed: 0
Blocked: 0
Unsupported: 0
Threat level: G2
Evidence revision: ...
```

They should not say:

```text
Governance score: 100/100
Certified secure
Compliant with all privacy law
Best governed memory system
```

Those claims exceed the evidence.

## 28. Initial implementation sequence

Recommended executable slices:

### Slice A: manifest + isolation core

Implement:

- claim schema;
- GOV-ISO-001 through GOV-ISO-005;
- GOV-AUTH-001/002;
- adapter leakage tests;
- normalized governance evidence.

Run against:

1. Agent Memory;
2. a deliberately naive shared store negative control;
3. at least one external system/composition that claims isolation.

### Slice B: lifecycle/deletion

Add:

- mutation authorization where supported;
- correction/historical distinction;
- deletion/resurrection;
- restart persistence.

### Slice C: provenance/poisoning

Add source trust, repetition, injection, spoofing, and classifier-laundering pressure.

### Slice D: broader external participation

Publish adapter examples and invite external systems to run/submit reproducible evidence.

## 29. Acceptance gate for Governance Gauntlet 1.0

Before this suite should be called stable:

- system-adapter contract is executable and versioned;
- claim schema is machine-readable;
- at least one non-Agent-Memory architecture runs the suite;
- negative-control systems prove evaluator sensitivity;
- isolation, lifecycle/deletion, provenance/adversarial, and recovery profiles exist or are explicitly deferred;
- no test requires PAMA-specific APIs;
- unsupported capability is not scored as arbitrary failure;
- caller-visible information leakage is tested separately from content leakage;
- adapter-added governance is distinguishable from native governance;
- frozen suite revision and case identities are reportable;
- evaluator mutations demonstrate that known-bad implementations fail;
- reports contain no secrets and no universal score.

## 30. Governing principle

> **Governance is credible when a memory system's declared boundaries survive adversarially relevant memory, not when the architecture document says they should.**
