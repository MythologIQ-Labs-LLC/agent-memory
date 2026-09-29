# #609 canonical serialization surface inventory method

Status: **candidate-discovery evidence / manual classification required**  
Owner: #609  
Related decision candidate: ADR-040

## Purpose

Inventory repository Python call sites that participate in recognizable canonical/stable JSON serialization families before any migration is designed.

The scanner is intentionally conservative about what it claims. It identifies:

- `json.dumps` / `_json.dumps` calls with literal `sort_keys=True` as `python_sorted_json`;
- direct `rfc8785.dumps` calls as `rfc8785_jcs`.

It does not infer that every match is cryptographic identity, persistence, or migration-critical.

The second family matters because Agent Memory already uses RFC 8785/JCS intentionally in several identity/evidence surfaces. Those existing JCS contracts must not be silently reinterpreted merely because #609 introduces a new persistence canonicalization profile.

## Scan roots

- `reference/`
- `scripts/`
- `reports/benchmarks/replays/`

## Recorded fields

For each candidate:

- serializer family;
- path and source line;
- lexical scope;
- `separators` argument when relevant and statically literal;
- `ensure_ascii` behavior when relevant and statically visible;
- `allow_nan` behavior when relevant and statically visible;
- short source excerpt;
- non-normative risk hint based on location.

The output also records parsed Python files, parse errors, candidate count, serializer-family counts, risk-hint counts, and a SHA-256 digest of the normalized candidate rows.

## What the scanner does not prove

A match is not automatically a migration target.

```text
stable JSON call site != persisted integrity identity
existing JCS identity != candidate persistence-v2 identity
path-based risk hint != governance classification
same helper shape != same compatibility obligation
```

The scanner may still miss custom serializers or dynamically aliased serializer calls. Manual architecture review remains required.

## Required follow-up classification

Each discovered candidate must eventually be classified as one of:

- persisted integrity identity;
- restart/checkpoint identity;
- configuration binding;
- API/receipt digest;
- governance/evidence identity already bound to JCS;
- benchmark/evidence-only utility;
- non-normative convenience serialization;
- other, with rationale.

For migration-relevant classes, review must additionally record:

- current serializer family;
- reachable value domain;
- float/non-finite reachability;
- recorded scheme/version if any;
- whether legacy verification must remain supported;
- whether changing canonical bytes would change an externally referenced identifier.

The inventory is evidence for ADR-040/#609. It cannot accept the ADR or change runtime bytes by itself.
