# #609 canonicalization value-domain and scheme reachability

Status: **qualification method / no runtime mutation**  
Owner: #609  
Related: merged PR #615, ADR-040 candidate

## Question

Which currently relevant canonicalization domains can carry numeric values, and which recorded integrity schemes actually bind those bytes?

Helper-level similarity is insufficient evidence. The important boundary is:

```text
value domain
  -> canonicalization profile
  -> recorded commitment scheme
```

## Evidence states

#609 uses three reachability states:

```text
PROVEN ABSENT
  authoritative schema/type contract excludes the value class

PERMITTED BY CONTRACT
  current contract allows the value class, but retained reference state has not been shown to exercise it

PROVEN ACTIVE
  a current canonical retained field demonstrably exercises the value class
```

Only the third proves a byte-divergence hazard is exercised today. The second still creates a portability obligation for future conformant writers.

## Runtime configuration

`schemas/runtime-configuration.schema.json@1.0.0` is the authority for raw runtime configuration.

The qualification probe recursively fails if the schema contains a JSON Schema `number` or `integer` type.

Current result:

```text
numeric reachability: PROVEN ABSENT BY SCHEMA v1
```

Therefore `configuration_digest()` is compatibility-significant but is not implicated in the numeric canonicalization defect under schema v1. A future numeric schema version must re-qualify this result.

## `bmerkle-v1`: canonical substrate state

`bmerkle-v1` commits canonical `Episode`, `Fact`, and `TypedRelation` rows through the legacy Python sorted/compact JSON helper.

### `TypedRelation.retrieval_weight`

The field is explicitly `float`, finite, and bounded to `[0,1]`. It is part of `asdict(relation)` row material.

```text
numeric reachability: PROVEN ACTIVE
non-finite reachability: PROVEN ABSENT FOR retrieval_weight
```

This alone requires a successor commitment scheme if ADR-040 changes row canonicalization.

### `Fact.attributes` / `TypedRelation.attributes`

Both are plain unconstrained `dict` fields. Their decoded values are part of `asdict(fact)` / `asdict(relation)` and therefore enter row hashes.

No substrate type contract excludes finite floats or non-finite Python float values from these dictionaries.

```text
numeric reachability: PERMITTED BY CONTRACT
non-finite reachability: PERMITTED BY CONTRACT
```

This means NaN/Infinity refusal in ADR-040 is not merely defensive formatting hygiene. It closes an ambiguity in a current persisted-integrity value domain.

### Scheme consequence

```text
bmerkle-v1
  -> legacy Python canonical row bytes
  -> must remain legacy-verifiable

accepted v2 row canonicalization
  -> successor scheme required
```

The successor is provisionally referred to as `bmerkle-v2`; final naming belongs to implementation review.

## `gsect-v1`: governance sections and residual

`gsect-v1` commits:

- typed map sections through canonical JSON `value_json` plus entry hashes and bucket roots;
- event log values through canonical JSON and a hash chain;
- a governance residual through canonical JSON and a residual digest.

The governance residual includes `extension_state` exported by `restart_runtime.py`.

`GovernedMemoryAdapter.extension_state` is declared `dict[str, dict]`: an opaque JSON-able custody seam with no schema restriction excluding finite or non-finite floats.

Current result:

```text
numeric reachability: PERMITTED BY CONTRACT
non-finite reachability: PERMITTED BY CONTRACT
current active float instance: NOT PROVEN BY THIS QUALIFICATION
```

Because `gsect-v1` binds the exact residual JSON bytes, changing the canonicalization rule for that domain while keeping the name `gsect-v1` would silently change the meaning of an existing integrity scheme.

### Scheme consequence

If ADR-040 makes governance residual serialization use the v2 persistence profile, a successor governance scheme is required, provisionally `gsect-v2`.

Alternatively, an implementation may keep the entire `gsect-v1` domain on its legacy canonicalizer and introduce v2 only when a separately versioned governance scheme is selected. What is forbidden is changing `gsect-v1` bytes in place.

## Restart/checkpoint envelope

Restart state persists `extension_state` and binds the recorded substrate/governance digests. Its own legacy JSON representation is also Python sorted/compact JSON.

The significant portability boundary is therefore not simply the outer file bytes. It is that restart must resolve each recorded integrity identifier to the correct canonicalization/root contract and refuse mixed-scheme state.

Current result:

```text
restart extension numeric reachability: PERMITTED BY CONTRACT
scheme/canonicalizer binding required: YES
```

## Existing RFC 8785/JCS identities

Merged PR #615 found 17 direct JCS canonicalization sites across evidence/security identities.

They are separate identity domains and are not migrated by #609 merely because a new persistence profile exists.

```text
existing rfc8785 identity != bmerkle/gsect migration target
```

## Scheme map

| identity domain | current canonicalizer | numeric reachability | #609 consequence |
| --- | --- | --- | --- |
| raw runtime configuration digest | Python sorted JSON | **PROVEN ABSENT** by schema v1 | no numeric migration required under v1 |
| `bmerkle-v1` substrate rows | Python sorted JSON | **PROVEN ACTIVE** (`retrieval_weight`); attributes also permit numeric/non-finite | successor scheme required if v2 row bytes adopted |
| `gsect-v1` governance residual | Python sorted JSON | **PERMITTED BY CONTRACT** via `extension_state` | keep legacy bytes or use successor scheme; never reinterpret v1 |
| runtime journal metadata | Python sorted JSON | typed integer/string digest metadata in reviewed path | preserve legacy unless committed byte domain changes |
| configured-restart plan | Python sorted JSON | typed non-floating plan fields | compatibility-significant, not numeric-defect target |
| migration-plan identity | Python sorted JSON | typed non-floating plan fields | preserve identity; do not rewrite incidentally |
| direct JCS evidence/security identities | RFC 8785/JCS | domain-specific | remain JCS-bound unless separately versioned |

## Consequence for ADR-040

ADR-040 should define a **named persistence canonicalization profile plus explicit scheme registry**, not one repository-wide JSON serializer.

At minimum, acceptance evidence must demonstrate:

1. legacy `bmerkle-v1` verification remains exact;
2. any v2 substrate scheme resolves to the v2 canonicalizer and cannot be confused with v1;
3. `gsect-v1` remains byte-stable unless a separately named successor is introduced;
4. if a `gsect-v2` successor is introduced, extension-state residual vectors include finite and non-finite numeric cases;
5. runtime recovery rejects mixed or unknown scheme/canonicalizer combinations;
6. existing JCS-bound identities are untouched.

No serializer bytes, digest scheme, persistence state, memory authority, ranking, admission, lifecycle or ADR status are changed by this qualification.
