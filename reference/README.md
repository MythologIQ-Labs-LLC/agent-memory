# Reference Governed Adapter

A minimal, executable demonstration that the governed path in
[`../docs/programs/runtime-evidence/README.md`](../docs/programs/runtime-evidence/README.md)
can be implemented over a temporal-graph substrate that provides no governance of its own.

## What this is not

Read this section before citing anything in this directory.

- **Not runtime evidence.** The paths execute against a substrate *model*, not a running substrate. Under the program's own evidence rules, evidence requires execution against a real substrate at a pinned version. This is a precondition slice, not the proof.
- **Not a conformance claim.** The emitted report states conformance level 0 and says why. Nothing here substantiates a level, a profile, or ADR-020.
- **Not a reference implementation of Agent Memory.** It implements the narrow slice needed to exercise governance paths, and nothing else.
- **Not an endorsement of any substrate.** The model reproduces one mapped substrate's verified semantics so the tests have something realistic to push against.

## What it does demonstrate

That the governance layer is load-bearing. The substrate model is deliberately permissive in exactly the ways the mapping verified: identity is opaque rather than content-derived, the partition filter defaults to unfiltered, deletion is physical with no tombstone, and **no operation checks authority**. Several tests assert both halves — that the substrate *would* misbehave, and that the adapter refuses anyway. A test that only checked the adapter would not prove the governance was doing any work.

## Layout

```text
reference/
  agentmem_ref/
    substrate.py    port + permissive in-memory temporal graph
    policy.py       PAMA evaluation: base table, class floors, modifiers
    receipts.py     schema-conformant decisions, receipts, audit events
    adapter.py      the governed path
  tests/            one positive path, eleven negative paths
  run_conformance.py
```

Everything is standard-library except schema validation, which uses `jsonschema` under the dependency policy in `../CONTRIBUTING.md`.

## Running it

```bash
python -m unittest discover -s reference/tests -t reference
python reference/run_conformance.py
```

Both are deterministic: identifiers are counter-based and the clock is injected, so repeated runs produce identical receipts and identical reports.

## The governed path

```text
evidence -> proposal -> authority envelope -> permitted action set
         -> selected action -> substrate mutation -> decision receipt
         -> retrieval candidate -> governed admission -> active context
```

The adapter supplies what the substrate cannot: an authority gate before every write, always-explicit scope filtering, external lifecycle state, tombstones, and receipts. Artifacts are emitted against schemas already canonical in this repository rather than shapes invented here — `pama-decision`, `decision-receipt`, `memory-audit-event`, and `conformance-report`.

## Paths exercised

| Path | Holds |
|---|---|
| positive commit and reconstruction | full chain executes; receipt reconstructs estimate, authority, selection, consequence; events causally linked |
| high-confidence false promotion | confidence 0.99 and 0.01 produce an identical envelope; confidence has no route to authority |
| cross-tenant relevance | substrate returns the foreign record unfiltered; adapter never reaches that default |
| prohibited action selectability | a governance-class mutation is absent from the permitted set and cannot be selected |
| stale authorization | authority resolved against an older state does not commit |
| self-approval of authority | blocked, with no permitted actions at all |
| unresolved actor authority | fails closed |
| superseded memory | remains a candidate, refused for current use, not erased |
| irreversible deletion | cannot commit autonomously; the substrate would have executed it |
| pruning | tombstones and removes from recall while content stays recoverable |
| undeclared derived residue | a projection nobody declared is detected after removal |
| version drift | policy version and estimator versions stay separable in the receipt |

## Known limitations

Stated rather than left to be discovered:

1. Approved permanent deletion is never exercised, because no review-satisfaction path is modelled. The physical-delete branch is reachable only through a proposal the gate refuses.
2. Retrieval ranking is lexical overlap. No recall quality or calibration claim is made or measurable here.
3. The policy implements the subset of the decision table these paths need, not the whole table.
4. Substrate binding is not implemented. The port exists; a driver mapping it to a real substrate's direct-write paths is the next slice, and is where runtime evidence begins.
