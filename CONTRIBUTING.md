# Contributing to Agent Memory

Agent Memory is a reference architecture and research-driven doctrine for governed agent memory systems.

Contributions are welcome when they sharpen a boundary, add evidence, expose a failure mode, improve a machine-readable contract, or challenge an architectural assumption constructively.

## Before contributing

Start with:

1. [`README.md`](README.md)
2. [`docs/README.md`](docs/README.md)
3. [`docs/00-glossary.md`](docs/00-glossary.md)
4. [`docs/24-determinism-probability-and-governed-uncertainty.md`](docs/24-determinism-probability-and-governed-uncertainty.md)
5. [`docs/adr/README.md`](docs/adr/README.md)

Then read the specific doctrine document your change affects.

## Contribution types

Useful contributions include:

- research that supports, challenges, or narrows a doctrine claim
- adversarial examples and failure modes
- new or improved conformance fixtures
- schema and interoperability improvements
- implementation mappings from real systems
- calibration data or benchmark results
- privacy/security threat cases
- corrections to biological or cognitive analogies
- documentation clarity and diagrams
- evidence that an accepted decision should be revised or superseded

## Evidence standard

Do not search only for sources that confirm the current architecture.

For consequential claims, identify where possible:

```text
supporting evidence
challenging evidence
boundary conditions
implementation evidence
conformance evidence
known uncertainty
```

Prefer freely inspectable research when practical:

- open-access journals
- PubMed Central and equivalent public archives
- lawful preprints
- open conference proceedings
- public technical reports
- open benchmark and dataset repositories
- standards and government publications

Accessibility is a preference, not a substitute for quality.

## Cross-domain memory claims

When transferring a concept from biological or cognitive memory into agent engineering, classify it as one of:

```text
MECHANISM
Demonstrated in the original substrate.

FUNCTIONAL ANALOGY
A similar problem or role appears in another substrate.

ENGINEERING PRESCRIPTION
A software requirement justified independently by agent evidence, governance, or operational risk.

OPEN HYPOTHESIS
A design candidate still requiring validation.
```

Do not turn analogy into mechanism merely because both systems use the word `memory`.

## Architecture rules

Preserve these distinctions unless your contribution explicitly argues for changing them:

```text
identity != memory
retrieval != memory
confidence != authority
trust != authority
relevance != permission
saturation != truth
utility != deletion authority
proposal != commit
historical truth != current truth
chronology != causality
```

The current governed-uncertainty model is:

```text
estimate / proposal
  -> governance envelope
  -> permitted action set
  -> selected action
  -> committed consequence
```

Probabilistic or learned behavior may exist inside that pipeline. It must not silently define its own authority.

## ADR changes

ADR status describes doctrine maturity, not implementation completeness.

See [`docs/adr/README.md`](docs/adr/README.md).

When proposing an ADR change:

- state the current decision
- identify the new evidence or failure mode
- explain compatibility impact
- identify affected docs, schemas, fixtures, and implementations
- add falsifiable acceptance or rejection criteria

A persuasive paragraph is not sufficient evidence to accept ADR-020.

## Schema changes

See [`docs/27-schema-registry-and-type-evolution.md`](docs/27-schema-registry-and-type-evolution.md).

Schema changes must consider semantic compatibility, not only JSON syntax.

If a field changes meaning, treat it as a semantic migration even when its JSON type stays the same.

## Fixture changes

Every conformance fixture should:

- isolate a meaningful failure mode
- declare expected behavior
- contain a valid memory unit
- declare governed-uncertainty invariants where applicable
- avoid claiming that structural fixture validity proves runtime behavior

Run:

```bash
python -m pip install jsonschema
python scripts/validate_fixtures.py fixtures
python scripts/validate_schemas.py
```

The repository workflow runs the same checks on pushes and pull requests.

## Documentation changes

Optimize for:

- explicit boundaries
- progressive disclosure
- correct internal links
- clear status and evidence language
- examples that distinguish estimates from authority
- diagrams that explain architecture rather than decorate it

Avoid:

- reintroducing one universal memory score
- treating a vector database as the complete memory architecture
- claiming neuroscience equivalence without evidence
- presenting proposed doctrine as implemented reality
- silently deleting contradictory evidence from the research narrative

## Definition of done

A contribution is complete when:

1. the intended architectural or evidence change is explicit
2. affected doctrine is internally consistent
3. relevant links and indexes are updated
4. schemas/fixtures are updated when the contract changed
5. validation passes
6. the PR clearly states what was proven and what remains unproven

A green validator proves the repository evidence is structurally coherent. It does not absolve runtime systems from reality, which remains stubbornly outside JSON Schema's jurisdiction.
