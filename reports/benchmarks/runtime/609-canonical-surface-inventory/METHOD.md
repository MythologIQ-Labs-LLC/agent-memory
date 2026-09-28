# #609 canonical serialization surface inventory method

Status: **candidate-discovery evidence / manual classification required**  
Owner: #609  
Related decision candidate: ADR-040

## Purpose

Inventory repository Python call sites that use stable JSON serialization patterns before any canonicalization migration is designed.

The scanner is intentionally conservative about what it claims. It identifies `json.dumps` / `_json.dumps` calls with literal `sort_keys=True` under selected repository roots. It does not infer that every match is cryptographic identity, persistence, or migration-critical.

## Scan roots

- `reference/`
- `scripts/`
- `reports/benchmarks/replays/`

## Recorded fields

For each candidate:

- path and source line;
- lexical scope;
- `separators` argument when statically literal;
- `ensure_ascii` behavior when statically visible;
- `allow_nan` behavior when statically visible;
- short source excerpt;
- non-normative risk hint based on location.

The output also records the number of parsed Python files, parse errors, candidate count, risk-hint counts, and a SHA-256 digest of the normalized candidate rows.

## What the scanner does not prove

A match is not automatically a migration target.

```text
stable JSON call site != persisted integrity identity
path-based risk hint != governance classification
same helper shape != same compatibility obligation
```

The scanner may also miss custom serializers or dynamically aliased JSON functions. Manual architecture review remains required.

## Required follow-up classification

Each discovered candidate must eventually be classified as one of:

- persisted integrity identity;
- restart/checkpoint identity;
- configuration binding;
- API/receipt digest;
- benchmark/evidence-only utility;
- non-normative convenience serialization;
- other, with rationale.

For migration-relevant classes, review must additionally record value-domain reachability, float/non-finite reachability, recorded scheme/version, and whether legacy verification must remain supported.

The inventory is evidence for ADR-040/#609. It cannot accept the ADR or change runtime bytes by itself.
