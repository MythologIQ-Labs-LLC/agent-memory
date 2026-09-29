# #609 canonicalization consequence classification

Status: **manual classification v1 / evidence for ADR-040**  
Inventory head: `e81929188883efc17df195fc5b728a156b7a82f9`  
Inventory workflow: `36488817670`  
Artifact: `10999749990`  
Artifact ZIP SHA-256: `11a90d42460d097c762ede69049b8049faab6d643030b3722ecf266a9b00ed96`  
Normalized candidate-row SHA-256: `b66e2e6fdfd79fc75eb54578aa7677e41f64faad8001c9264635c56b339f8d22`

## Inventory result

The expanded AST inventory found **219** canonicalization call sites in the scanned Python roots:

- `python_sorted_json`: **202**
- `rfc8785_jcs`: **17**
- parse errors: **0**

Only **7** Python-sorted-JSON sites fell into the scanner's runtime/persistence risk bucket. The risk hint was only a discovery aid; the consequence classifications below are manual.

## Consequence map for the seven runtime/persistence candidates

| surface | consequence class | current float/non-finite reachability | v2 consequence |
| --- | --- | --- | --- |
| `reference/agentmem_ref/state/sqlite_substrate.py::_canonical_bytes` | **persisted integrity identity** | **PROVEN YES**. `TypedRelation.retrieval_weight` is a finite float and typed-relation rows feed `_row_hash`, bucket commitments, restart verification and tamper evidence. | **Primary #609 migration target.** Legacy bytes must remain verifiable under their original scheme; new language-neutral commitments need an explicit versioned scheme. |
| `reference/agentmem_ref/runtime/restart_runtime.py::_canonical_bytes` | **restart/checkpoint identity + durable JSON writer** | **NOT PROVEN ABSENT.** Journal material itself is mostly generation/digest strings, but the helper is also used by durable checkpoint JSON and the recovered governance/runtime envelope can contain extensible mappings. | Must not silently change. Classify each written envelope before v2 promotion; legacy checkpoint verification remains mandatory. |
| `reference/agentmem_ref/runtime/sqlite_runtime.py::_canonical_bytes` | **SQLite runtime journal/integrity identity** | Direct journal-record material is currently integer/string digest metadata; no float-bearing field has been demonstrated in the journal record itself. It transitively binds substrate commitments that are float-sensitive. | Preserve legacy journal verification. Scheme versioning must make the substrate commitment algorithm unambiguous rather than reinterpret existing `sha256:` records. |
| `reference/agentmem_ref/runtime/configured_restart.py::_canonical_bytes` | **configuration-bound restart identity** | Current `RuntimeConfigurationPlan.to_dict()` is strings, booleans, lists and nested typed route records; no float field is present in the typed plan shape reviewed for this classification. | Compatibility-significant but not currently the source of the float defect. Keep explicit scheme identity; do not migrate merely for uniformity. |
| `reference/agentmem_ref/runtime/runtime_config.py::_canonical_bytes` | **raw configuration identity** | **NOT YET PROVEN ABSENT.** `configuration_digest()` accepts a generic mapping even though the resolved plan is currently non-floating. A schema/call-boundary reachability test is required before declaring the domain float-free. | Freeze the accepted configuration value domain before any cross-language digest claim. If floats are unreachable, retain current bytes under a named legacy profile or migrate only through an explicit version transition. |
| `reference/agentmem_ref/memory/checkpoint_migration.py::_canonical_bytes` | **migration plan/execution identity + migration-state writer** | Current `MigrationPlan` fields are strings, integers and string sequences; no float-bearing field is present in the reviewed typed plan. | Migration machinery must be able to describe canonicalization-version transitions, but its own identity must not be rewritten incidentally. Verify old plan/execution records before any recommit. |
| `reference/agentmem_ref/api/surface.py::_canonical_bytes` | **API/reference digest helper** | Generic helper accepts arbitrary objects. Observed public-surface use includes text-derived content refs; complete float reachability is **not established** by the inventory alone. | Do not make this helper the universal v2 switch. Classify call sites by consequence. Persisted refs created by the API retain their original identity semantics unless separately migrated. |

## Existing RFC 8785 / JCS family

The expanded inventory also found **17 direct `rfc8785.dumps(...)` call sites**. They include identity/evidence surfaces such as:

- approval evidence;
- reusable grants;
- contextual recall projections;
- MCP and A2A interaction evidence;
- external / cMCP / Agent Manifest evidence;
- enforcement evidence/composition;
- runtime trace correlation;
- security findings;
- temporal commitments;
- trace/action evidence.

These are **not** automatically #609 migration targets. Their use of RFC 8785 is already an explicit canonicalization choice and often participates in security- or evidence-sensitive identity.

The repository therefore already has multiple legitimate canonicalization domains:

```text
canonicalization scheme
    is part of
identity / compatibility contract
```

A new persistence profile must not silently replace existing JCS-bound identities merely to make the repository use one serializer.

## Architecture conclusion from the inventory

The original shorthand, "replace repeated stable JSON with one language-neutral serializer," is too broad.

The safer architecture is:

```text
existing JCS-bound identity/evidence domains
    -> remain JCS-bound unless separately versioned/migrated

legacy Python-sorted-JSON domains
    -> preserve legacy verification
    -> classify by consequence and reachable value domain

float-bearing persisted integrity domain
    -> agent-memory canonical persistence v2 candidate
    -> explicit scheme/version transition
    -> verified logical state only
    -> Python/Rust exact-byte qualification before promotion
```

The minimum v2 target is therefore the **persisted integrity/restart chain whose canonical bytes are currently Python-shaped**, not every canonical JSON digest in the repository.

## Remaining #609 evidence before ADR ruling

1. Freeze accepted numeric vectors for finite binary64 values, exact integers, negative zero, exponent thresholds and subnormals.
2. Freeze NaN/Infinity refusal vectors.
3. Add an explicit reachability test for raw runtime configuration values.
4. Classify restart-runtime durable envelopes for float/non-finite reachability rather than relying on helper-level inference.
5. Define named legacy and v2 scheme identifiers, including substrate row/bucket/root commitments and restart bindings.
6. Prove verify-old-before-recommit migration, rollback/failure atomicity, tamper refusal and scheme-confusion refusal.
7. Run independent Python and Rust candidate implementations against the frozen vectors before accepting the architecture.

## Governance

```text
same JSON meaning != same canonical bytes
same helper shape != same identity domain
existing JCS identity != v2 migration target
new serializer != permission to reinterpret old commitments
cross-language parity != migration authority
```

This classification changes no runtime bytes, digest schemes, memory authority, ranking, admission, lifecycle or ADR status.
