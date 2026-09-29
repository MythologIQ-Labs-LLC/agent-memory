# #609 canonical JSON v2 vector adversarial review

Status: **REVIEWED CANDIDATE / NOT ACCEPTED DOCTRINE**  
Fixture: `reference/fixtures/runtime/canonical-json-v2-vectors-v1.json`  
Fixture status remains: `DRAFT_FROZEN_CANDIDATE_NOT_YET_ACCEPTED`

## Review objective

Challenge the candidate expected bytes before any Python or Rust v2 serializer is implemented.

The review intentionally treats the fixture as the proposed contract and asks whether its rules are internally coherent, preserve the intended legacy semantics, and avoid importing RFC 8785/JCS behavior beyond the stated numeric prior art.

## Independent cross-checks

### Finite binary64 base spelling

All 18 finite binary64 cases were reconstructed from their exact 64-bit patterns and cross-checked against ECMAScript `JSON.stringify(Number)` spelling, the finite-number behavior used as prior art by RFC 8785/JCS.

The Agent Memory candidate then applies only the two declared type-preservation rules:

1. binary64 negative zero -> `-0.0`;
2. if the base finite-float token contains neither `.` nor `e`, append `.0`.

**Result: 18/18 expected float tokens consistent with the stated rule.**

This cross-check is not a v2 serializer implementation and is not used as runtime code.

### Preserved Python string/object behavior

The string, escaping, Unicode, nested-object and code-point-key-order vectors were cross-checked against the legacy Python persistence serializer for the behavior ADR-040 explicitly proposes to preserve.

**Result: no discrepancy found.**

The non-BMP key-order vector deliberately differs from RFC 8785/JCS UTF-16 ordering. That divergence is intentional and visible in the fixture.

## Adversarial edge rulings

### 1. Should integer-valued floats collapse to integer bytes?

**Ruling: no. Keep type-preserving bytes.**

The legacy Python persistence serializer distinguishes `1` from `1.0`. Collapsing them during a migration would make canonicalization silently change logical type identity.

Therefore:

```text
1    -> 1
1.0  -> 1.0
```

The same rule explains `9007199254740992.0`.

### 2. `1e20` produces a long fixed token

ECMAScript's base spelling for binary64 `1e20` is `100000000000000000000`. The type-preservation rule therefore yields:

`100000000000000000000.0`

This is longer than exponent notation, but deterministic size efficiency is not allowed to override the frozen formatting rule. Special-casing this value would create another threshold contract.

**Ruling: keep.**

### 3. Should negative zero normalize to positive zero?

RFC 8785/JCS canonicalizes negative zero to `0`. Agent Memory's legacy Python bytes distinguish `-0.0`, and a finite binary64 value may carry the sign bit even when numerical comparison treats it as zero.

Normalizing it would widen the migration beyond the discovered host-formatting defect and could make historical bytes unrecoverable from logical typed state.

**Ruling: preserve `-0.0`.**

### 4. Exact integers beyond 2^53

ADR-040 is not an I-JSON/JCS value-domain adoption. Exact integers are preserved as mathematical integers and never routed through binary64.

**Ruling: keep 2^53±1 and large-integer vectors.**

### 5. Code-point ordering vs JCS UTF-16 ordering

Changing key ordering would affect every object containing a divergent non-BMP/BMP key pair even though #609 was discovered through numeric formatting.

**Ruling: preserve Unicode scalar/code-point ordering for this persistence profile. Existing JCS-bound identities remain separate JCS domains.**

### 6. Invalid Unicode, non-string keys and duplicate keys

These cases must refuse before commitment bytes. Accepting and normalizing them would make the canonicalizer responsible for resolving malformed or ambiguous input semantics.

**Ruling: keep refusal cases.**

## Conclusion

No vector byte was changed by this adversarial review.

The candidate is internally coherent enough to proceed to maintainer review, but it is **not accepted doctrine** and MUST NOT yet be used to implement or migrate production persistence.

Next gates remain:

1. complete reachability evidence (#617);
2. maintainer vector ruling;
3. only after acceptance, independently implement Python and Rust candidates against the frozen fixture;
4. scheme-aware migration/restart/tamper evidence;
5. ADR-040 ruling.

```text
reviewed candidate != accepted vector set
accepted vector set != accepted ADR
serializer parity != migration authority
```
