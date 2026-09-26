# Agent Memory Governance Gauntlet Alpha

Status: executable evaluator/fixture slice under issue #559; **#559 remains open**  
Suite family: `agent-memory-gauntlet-governance`  
Profile: `governance-isolation-deletion-alpha-v1`  
Specification version: `0.1.0`  
Evidence provenance: `gauntlet_native_gap`  
Authority effect: none

## Purpose

This is the first executable slice of the [Governance Gauntlet specification](GOVERNANCE_GAUNTLET_SPECIFICATION.md).

It tests **declared governance claims**, not PAMA conformance and not one preferred policy engine.
The alpha is intentionally synthetic and system-neutral. It exists to prove that governance
claims can be pressured through the same Gauntlet system-adapter contract while preserving
separate verdicts for content leakage, identifier leakage, cardinality leakage, deletion,
and authority laundering.

This slice does **not** complete #559 yet. The issue's completion gate requires one real
memory system to run under the same protocol. The canonical Agent Memory adapter is being
held until the public runtime contract stabilizes; the evaluator fixtures here are controls,
not substitutes for that gate.

## Run it

Repository fixture controls are trusted in-process fixtures and use disposable synthetic state:

```bash
agent-memory gauntlet run \
  --system fixtures/gauntlet/governance-strict-adapter.json \
  --profile governance-isolation-deletion-alpha-v1
```

For a non-fixture adapter, execution and destructive consent are separate decisions.
A `stdio` adapter requires `--allow-external-process`. If deletion is positively claimed,
the profile may issue both `reset` and `forget`, so it additionally requires:

```text
--allow-destructive-operations
```

The narrow `--allow-destructive-reset` compatibility flag remains sufficient only when
`reset` is the sole active destructive operation.

```text
manifest isolation claim != destructive-operation consent
claimed deletion != permission to delete an arbitrary namespace
```

The alpha still requires `benchmark_isolation.strategy=disposable_instance` before any
active destructive operation is permitted.

## Executed case registry

### Directly exercised when claimed

| Case | Claim | What the evaluator observes |
| --- | --- | --- |
| `GOV-ISO-001` | `tenant_isolation` | foreign content and opaque identifier leakage under a perfect wrong-tenant match |
| `GOV-ISO-002` | `scope_isolation` | foreign content and opaque identifier leakage under a perfect wrong-scope match |
| `GOV-ISO-005` | `foreign_cardinality_non_disclosure` | caller-visible output stability with 0, 1, and 5 foreign perfect matches |
| `GOV-DEL-001` | `deletion` + `forget` | pre-delete retrievability, successful forget, then content/ID non-resurrection in recall |
| `GOV-AUTH-002` | `tenant_isolation` | a newer forbidden memory cannot launder authority through recency |
| `GOV-AUTH-003` | `tenant_isolation` | a forbidden perfect match cannot launder authority through similarity |

### Intentionally blocked when claimed

These cases are registered now but do not invent fake evidence merely to appear complete:

| Case | Claim | Why blocked in alpha |
| --- | --- | --- |
| `GOV-DEL-002` | `durable_deletion` | restart/recovery lifecycle is not yet bound to the neutral Gauntlet orchestrator |
| `GOV-AUTH-004` | `route_authority_isolation` | neutral route-evidence injection contract not yet defined |
| `GOV-AUTH-005` | `classifier_authority_isolation` | neutral classifier-evidence injection contract not yet defined |
| `GOV-SRC-002` | `source_trust` | neutral verified-vs-asserted provenance injection contract not yet defined |

If these capabilities are not claimed, their native verdict is `unsupported`, not `fail`.

```text
unsupported != failed
blocked != failed
blocked != zero
```

## Evaluator controls

The repository includes three composed control fixtures.

### Strict fixture

`fixtures/gauntlet/governance-strict-adapter.json`

The fixture partitions memories by tenant and scope, does not expose foreign cardinality,
and supports deletion. Governance capabilities are declared `derived`, not `native`, because
the behavior exists in the composed evaluator fixture.

Expected directly exercised verdicts are `pass`.

### Leaky fixture

`fixtures/gauntlet/governance-leaky-adapter.json`

This is an explicit negative control. It claims tenant/scope isolation but its recall path
searches all synthetic tenants/scopes. The evaluator must report measured governance
`fail` verdicts while the Gauntlet **execution itself remains complete**.

```text
governance case failure != harness execution failure
```

### Cardinality-leak fixture

`fixtures/gauntlet/governance-count-leak-adapter.json`

This fixture correctly suppresses foreign content and identifiers but returns a caller-visible
candidate count computed across foreign state.

It should therefore produce:

```text
GOV-ISO-001  pass
GOV-ISO-002  pass
GOV-ISO-005  fail
```

This control exists specifically to prevent the evaluator from treating content isolation as
proof of non-disclosure.

## Deletion precondition

`GOV-DEL-001` does not allow a false deletion pass from a system that never stored/retrieved
the setup memory.

The evaluator first proves the target is retrievable. If that precondition is not established,
the case is `blocked` rather than `pass`.

Only after successful pre-delete recall does it issue `forget` and test post-delete recall.

## Native versus normalized evidence

The native result retains case-level verdicts:

```text
pass
fail
unsupported
blocked
invalid
```

The common Memory Evaluation contract has a smaller metric-state vocabulary, so the
normalization is intentionally conservative:

- `pass` / `fail` become measured descriptive booleans per case;
- native `unsupported` maps to common `not_applicable`, while remaining `unsupported` in native evidence;
- native `blocked` / `invalid` map to common blocked evidence;
- no aggregate governance score is emitted.

The governance dimension may therefore be `partial` when some claims are measured and
others are unsupported or blocked.

```text
normalized shape != erased native semantics
case verdicts != one governance health score
```

## Leakage classes remain separate

The alpha directly keeps these observations distinct:

```text
content leakage
identifier leakage
cardinality/count leakage
```

The broader specification additionally reserves metadata, audit, and bounded timing/side-channel
observations for later profiles. They must not be inferred casually from this slice.

## Evidence integrity

The case registry has a deterministic SHA-256 identity and is written into the normalized
reproducibility dimension. Every run retains:

```text
adapter manifest
native case evidence
normalized evidence
qualification evidence
```

The profile is explicitly `gauntlet_native_gap`. A pass is useful falsification/conformance
evidence, but it is not independent external proof that a memory runtime is superior.

## Remaining gate for #559

This evaluator/fixture slice is ready for a real memory system, but #559 remains open until
at least one real system is evaluated under the same claim protocol.

The intended next bridge is the canonical Agent Memory adapter once the active runtime-contract
work has converged. An external memory runtime may also satisfy this gate earlier if a truthful
adapter can be built without manufacturing governance properties.

Additional follow-on contracts are required before the alpha can honestly exercise:

- restart-persistent deletion;
- route-count authority laundering;
- classifier authority laundering;
- verified versus caller-asserted provenance.

Those gaps are recorded as blocked evidence when claimed rather than silently omitted.
