# P8 Telemetry Interoperability Without Shadow Memory

## Purpose

Make Agent Memory operationally observable without copying governed memory into a less-governed telemetry backend.

Canonical audit events remain the reconstructable evidence surface. Telemetry is a deliberately lossy derived projection used for correlation, health, and operational analysis.

The governing risk is **shadow memory**: raw memory content, prompts, summaries, evidence payloads, identities, or authority context copied into logs/traces/metrics where retention, access, deletion, and lifecycle controls are weaker than the memory system they observe.

## V1 minimization profile

`reference/agentmem_ref/telemetry.py` projects schema-valid `memory-audit-event` records into `telemetry-projection.schema.json`.

The projection is strict allowlist, not denylist.

Allowed directly:

- event family and event schema version;
- component name;
- timestamp;
- booleans indicating whether payload, signal, or authority context existed;
- count of sensitivity labels, without the labels themselves.

Potentially identifying or cross-linkable values are emitted only as keyed HMAC-SHA256 references:

- event id;
- memory id;
- actor;
- principal;
- correlation and causation ids;
- policy version;
- receipt and ledger references.

The HMAC key is local configuration and is not emitted. Different telemetry domains may use different keys so opaque identifiers do not automatically become globally linkable pseudonyms.

Explicitly absent from the projection:

- `payload` contents;
- memory text or prompt content;
- raw actor/principal/memory identifiers;
- raw sensitivity labels;
- signal values and uncertainty bodies;
- estimator details;
- authority refs;
- permitted/prohibited/selected action names;
- raw receipt or ledger identifiers.

## Semantics

```text
canonical audit event  -> authoritative reconstruction evidence
telemetry projection   -> minimized operational correlation only
```

A valid telemetry span does not prove a memory mutation was authorized, correct, complete, or successfully forgotten. Operators must resolve the canonical receipt/audit path under normal access controls when deeper evidence is required.

Telemetry retention must be governed independently. Pseudonymization reduces disclosure risk but does not make telemetry non-sensitive or exempt it from retention/deletion policy.

## Interoperability posture

The V1 shape uses primitive span-style attributes that can be mapped into common observability systems, but this slice does not claim formal OpenTelemetry semantic-convention adoption or require an external telemetry SDK.

That separation is intentional. Agent Memory defines the privacy/governance contract first. A later adapter may map this content-free shape into a specific telemetry transport without weakening it.

## Validation

`reference/tests/test_telemetry.py` injects a canonical audit event containing deliberately sensitive:

- prompt and memory payloads;
- credential-like content;
- actor, principal, and memory identifiers;
- sensitivity labels;
- signal values and uncertainty notes;
- authority refs and action names;
- receipt and ledger ids.

The serialized telemetry projection must contain none of those raw values. Tests also verify stable same-key correlation, cross-key unlinkability, schema validity, and minimum HMAC key strength.

## Claim boundary

P8 V1 demonstrates a local privacy-minimized telemetry seam. It does not claim:

- that telemetry is anonymous;
- that a telemetry backend satisfies Agent Memory retention or deletion requirements automatically;
- that telemetry replaces canonical receipts or audit events;
- formal compliance with any external observability standard;
- production collector/exporter behavior;
- any upstream submission or external repository change.

## Next P8 slice

The next useful evidence is retention/deletion behavior for telemetry itself: prove that correlation references can support operational reconstruction while telemetry records do not outlive the policy that permits them, and that deleting memory does not leave content-bearing telemetry residue merely because the telemetry system was classified as "observability."
