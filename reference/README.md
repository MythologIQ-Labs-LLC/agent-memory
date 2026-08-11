# Reference Governed Adapter

A minimal, executable demonstration that the governed path in
[`../docs/programs/runtime-evidence/README.md`](../docs/programs/runtime-evidence/README.md)
can be implemented over a temporal-graph substrate that provides no governance of its own.

## What this is not

Read this section before citing anything in this directory.

- **Not a conformance claim.** The emitted report states conformance level 0 and says why. The doctrine fixture corpus *is* now driven through the adapter's authority enforcement, but doc 06 levels are cumulative and this adapter implements neither decay nor calibrated saturation, so levels 2 and 3 are unmet however well enforcement does. Nothing here substantiates a level, a profile, or ADR-020.
- **Not a reference implementation of Agent Memory.** It implements the narrow slice needed to exercise governance paths, and nothing else.
- **Not an endorsement of any substrate.** The model reproduces one mapped substrate's verified semantics so the tests have something realistic to push against.

## What it does demonstrate

Two things, at different evidential weight.

**Against a real substrate (runtime evidence).** Seven governance paths execute against `graphiti-core` 0.29.3 backed by an embedded graph database, with no LLM, no embedder, no API key and no server. Facts are written through the substrate's no-LLM direct-write path, superseded, pruned, physically deleted, and refused across partitions, all under the authority gate.

**Against a substrate model (precondition).** Twelve further paths run against an in-memory model, covering cases the live binding does not reach — stale authorization, self-approval, undeclared derived residue, and version-drift separation.

**Against the doctrine fixture corpus.** All 25 repository fixtures are driven through the adapter's own enforcement rule, 17 of which declare an authority envelope. This matters because the corpus was authored to describe doctrine, not to satisfy this implementation, so agreement between them is evidence rather than a suite agreeing with itself. The checker is mutation-tested in `tests/test_fixture_corpus.py`: four deliberately corrupted envelopes must be detected, because a conformance check that cannot fail is decoration.

The common point is that the governance layer is load-bearing. The substrate model is deliberately permissive in exactly the ways the mapping verified: identity is opaque rather than content-derived, the partition filter defaults to unfiltered, deletion is physical with no tombstone, and **no operation checks authority**. Several tests assert both halves — that the substrate *would* misbehave, and that the adapter refuses anyway. A test that only checked the adapter would not prove the governance was doing any work.

## Layout

```text
reference/
  agentmem_ref/
    substrate.py    port + permissive in-memory temporal graph
    policy.py       PAMA evaluation: base table, class floors, modifiers
    receipts.py     schema-conformant decisions, receipts, audit events
    adapter.py      the governed path
    fixture_conformance.py  drives the doctrine corpus through enforcement
    projections.py          tier-3 declarations and the freshness relation
    residue.py              deletion residue partition and independent sweep
    projection_governance.py governed correction, purge, and rebuild
    (selectors live in adapter.py: deterministic and seeded stochastic)
  agentmem_ref/graphiti_driver.py   binding to a real temporal knowledge graph
  tests/            model paths and real-substrate paths
  run_conformance.py
```

Everything is standard-library except schema validation, which uses `jsonschema` under the dependency policy in `../CONTRIBUTING.md`.

## Running it

```bash
# model paths only; standard library plus jsonschema
python -m unittest discover -s reference/tests -t reference

# stochastic containment sweep with an explicit trial count
python reference/run_conformance.py --trials 500

# add the real substrate; the substrate tests skip cleanly without it
pip install graphiti-core kuzu
python -m unittest discover -s reference/tests -t reference
python reference/run_conformance.py
```

Runs are deterministic: identifiers are counter-based and the clock is injected, so repeated runs produce identical receipts and identical reports. Stochastic selection is seeded per trial, so it varies across trials and reproduces exactly for a given seed.

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
| fixture corpus | all 25 doctrine fixtures pass envelope enforcement; the checker is mutation-tested |
| stochastic containment | hundreds of sampled trials never escape the permitted set, and the selector demonstrably varies |
| hostile selector | a selector returning a prohibited action is contained by the adapter and the violation recorded |
| derived-state freshness | stale and residual are computed from a recorded basis, never set by a flag |
| correction propagation | dependents go stale; content-bearing projections supersede without erasing the prior version |
| transitive purge | the whole derivation closure is reached, and a deliberate one-hop purge is caught by the sweep |
| undeclared residue | the four-way partition holds, with the undeclared cell empty as a hard gate |
| rebuild authority | estimator-mediated rebuild is refused without an authority decision; deterministic reproducible rebuild is categorical |

## Known limitations

Stated rather than left to be discovered:

1. Corpus coverage is envelope enforcement, not full scenario execution: decay, calibrated saturation, retrieval ranking, and most lifecycle transitions are outside this adapter and are declared as exemptions in the report rather than silently skipped.
2. Retrieval ranking is lexical overlap, not the substrate's hybrid search, because hybrid ranking needs an embedder. Recall quality is not measured.
3. The policy implements the subset of the decision table these paths need, not the whole table.
4. The substrate binding uses an embedded backend that is deprecated upstream, chosen because it needs no server. No governance behavior under test depends on the backend choice.
5. Node topology is simplified to one edge per fact. This exercises governance invariants, not knowledge modelling.
6. Derived-state governance operates on an adapter-owned sidecar. The design spike names this as the obvious home for substrates that cannot store a projection declaration, and notes that it reintroduces the consistency problem one level up. That trade is accepted here rather than solved.
7. Residue is measured over declared projections. State that was never declared is outside the sweep's reach by construction, which is why the declaration surface is the load-bearing part rather than the traversal.
