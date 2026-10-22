# #777 public redaction, contract 1.7.0 successor candidate

**Status:** STAGED ON ISOLATED BRANCH; NOT EXECUTED AT THIS SHA; NOT PUBLISHED.

## Owner's versioning decision

**Yes: the public-contract change must be recorded as version 1.7.0 in a
successor declaration.** Redacting deleted fact identifiers, refusal details
and historical diagnostics changes the externally visible API, even when
`public_projection` was initially an optional additive field.
Shipping a changed read contract while advertising frozen 1.6.0 would
mislead consumers.

This branch is based on #777 redaction candidate
`implementation/777-public-deleted-identifier-redaction-no-ci`
@ `dc51da05a3df743eee7de6f24b1286d96130c797`.

The new isolated candidate:
- updates `reference/agentmem_ref/api/contract.py` to `CONTRACT_VERSION=1.7.0`;
- extends six versioned API envelope schemas to accept 1.7.0 while
  retaining the previous 1.6.0 and earlier compatible versions;
- updates the existing public-contract compatibility test so 1.7 is
  CURRENT, while 1.8 requires migration;
- adds four dedicated contract 1.7 successor tests **before** the version
  change in `reference/tests/test_777_contract_1_7_successor.py`;
- stages the **draft-only**, exact Git-blob alternative successor at
  `reports/runtime/proposals/777-contract-1-7-v8-alternative.DRAFT.json`.
  It declares `identity.public_contract_version: 1.6.0 -> 1.7.0`.

No active register, frozen #770 lanes, v6/v7 declaration, benchmark
gold, default branch, PR, or Actions were modified.

## Important: competing post-v7 candidates

**DO NOT use this alternative draft as a merge-ready declaration.** The active
register still declares v7 as the successor to published v6. There is also
a distinct **#773** draft v8 variant, and separate protected source changes
under **#774** and **#776**.

The #777 redaction source was developed on the earlier #776 deletion
implementation at `5d90965` and has **not yet incorporated** the latest
reviewed #776 memo-cache staleness fix `bd16a7e` / source blob
`fe25923f70ae03830d1036ad959af62e25fd4b59`.

A future integrated successor MUST reconcile these sources and any overlap
of `runtime/adapter.py`, and prove no regression to transitive deleted
content refusal, cache invalidation and re-created memory IDs.
Do not independently approve conflicting v8 records.

## Audit policy: internal-only pending governed interface

No authorized public audit reader exists. Keep detailed deleted-lineage
audit records **internal only**. An ordinary public handle, its debug
flags, or guessed fact IDs do not confer audit rights. New audit access
requires a separate authorization design with authenticated principals,
purpose-limited scope, retention and revocation, and independent
noninterference controls. Do not expose private methods as the audit API.

## Explicit qualification

Run in a trusted, complete checkout without GitHub Actions:

```bash
python -m unittest discover -s reference/tests -t reference -p test_777_contract_1_7_successor.py
python -m unittest discover -s reference/tests -t reference -p test_api_contract.py
python -m unittest discover -s reference/tests -t reference -p 'test_777_*.py'
python -m unittest discover -s reference/tests -t reference
```

The protected-runtime freeze guards are expected to fail until a
**sanctioned, activated, independently verified** successor boundary
exists. Their failure is not permission to bypass them.

Run exact-SHA contract negotiation tests on 1.6 and 1.7 requests,
new 1.7 responses, older 1.0–1.6 compatible envelopes, schema validation
for all versioned stages and the public redaction/admission noninterference
suite. Measure public-visible fields, not only passing new tests.

Then execute the #776 repaired P0 security cases and the original AMB /
LongMemEval same-harness lanes on an **integrated** future branch with
a single candidate declaration, before any promotion.

**Evidence limit:** #777's 19/19 tests and five-corpus equality measurements
are from Claude's earlier reviewed 1.6.0 redaction code. They are
**not** measurements or acceptance of this contract-1.7.0 branch.
