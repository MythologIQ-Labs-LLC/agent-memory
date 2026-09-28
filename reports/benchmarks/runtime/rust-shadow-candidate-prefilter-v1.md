# Rust shadow candidate-prefilter qualification v1

Status: **CANDIDATE / CI NOT YET OBSERVED**  
Owner: #602  
Ancestry: #591 identity-first candidate materialization

## Scope

This slice shadows only the pre-materialization candidate-discovery contract:

```text
identity/text projection
  -> selected group filter
  -> caller-supplied identity eligibility
  -> lexical overlap
  -> score desc / uuid ordering
  -> materialize survivors
```

It does **not** shadow or replace full fact eligibility, canonical admission, currentness, tombstone handling, dispute handling, routing authority, or PAMA consequence rules.

Frozen oracle:

`reference/fixtures/runtime-kernel/candidate-prefilter-v1.tsv`

The vectors cover:

- wrong-group exclusion;
- identity-ineligible exclusion;
- exact score ties ordered by UUID;
- duplicate query terms collapsing to set semantics;
- empty/fully stripped queries producing no candidates;
- current edge-punctuation behavior;
- exact IEEE-754 score-bit parity.

## Acceptance rule

PASS requires Python to reproduce the frozen candidate identities/order/score bits first, followed by exact Rust reproduction of the same vectors.

A PASS qualifies only this deterministic prefilter primitive. It does not authorize Rust to perform final visibility/admission decisions.

```text
identity prefilter != permission
candidate generation != recall admission
faster filtering != wider visibility
```
