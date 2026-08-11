# Contributing to Agent Memory

Agent Memory is a reference architecture and research-driven doctrine for governed agent memory systems.

Contributions are welcome when they sharpen a boundary, add evidence, expose a failure mode, improve a machine-readable contract, or challenge an architectural assumption constructively.

By intentionally submitting a contribution for inclusion in this repository, you agree that the contribution is submitted under the repository's [Apache License 2.0](LICENSE), unless a separate written agreement explicitly applies.

Participation is also subject to the repository [Code of Conduct](CODE_OF_CONDUCT.md). Repository decision rights and doctrine-change rules are described in [GOVERNANCE.md](GOVERNANCE.md). Security-sensitive findings should follow [SECURITY.md](SECURITY.md) rather than being disclosed through an ordinary public issue.

## Before contributing

Start with:

1. [`README.md`](README.md)
2. [`docs/README.md`](docs/README.md)
3. [`docs/00-glossary.md`](docs/00-glossary.md)
4. [`docs/24-determinism-probability-and-governed-uncertainty.md`](docs/24-determinism-probability-and-governed-uncertainty.md)
5. [`docs/adr/README.md`](docs/adr/README.md)
6. [`docs/SOURCE_RIGHTS_POLICY.md`](docs/SOURCE_RIGHTS_POLICY.md)
7. [`GOVERNANCE.md`](GOVERNANCE.md)

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

## Source and reuse rights

Evidence quality and reuse permission are separate questions.

Read [`docs/SOURCE_RIGHTS_POLICY.md`](docs/SOURCE_RIGHTS_POLICY.md) before introducing external text, code, diagrams, tables, figures, screenshots, or other expressive material.

The default rule is:

> **Public accessibility does not imply reuse permission. Citation does not imply a license.**

Contributors should prefer direct links and independent synthesis unless a stronger reuse basis is both necessary and verified.

Before merge:

- link the most specific lawful public source when one exists
- distinguish public, private, successor, and no-public-locator sources
- do not assume a repository license governs third-party issue comments or external attachments
- do not treat open access as an automatic reuse license
- do not copy code without a compatible verified license or explicit permission
- do not copy or closely redraw diagrams, tables, figures, or screenshots without a verified reuse basis
- preserve license text, notices, attribution, and modification notices when required
- register material reuse in [`sources/source-registry.json`](sources/source-registry.json)
- default unknown rights to `citation_only` or `independent_synthesis`

Contributor-originated provenance may be recorded when supported. Provenance statements should identify origin without overstating legal exclusivity over an idea, method, or short phrase.

CI validates the source registry against [`schemas/source-record.schema.json`](schemas/source-record.schema.json). Reuse-oriented records require a documented rights basis.

The repository's own Apache-2.0 license does **not** absorb or relicense third-party material merely because it is cited, linked, described, or referenced here.

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
- precise public provenance when lawful public sources exist
- original synthesis when reuse rights are unclear or unnecessary

For the root README, prefer stable static overview graphics or compact tables when GitHub's interactive Mermaid renderer harms legibility. Mermaid remains useful in detailed documentation where the source graph itself is part of the working artifact.

Avoid:

- reintroducing one universal memory score
- treating a vector database as the complete memory architecture
- claiming neuroscience equivalence without evidence
- presenting proposed doctrine as implemented reality
- silently deleting contradictory evidence from the research narrative
- copying protected expression merely because it is publicly readable
- presenting a related public project as the provenance source for a private canonical artifact

## Pull-request expectations

A pull request should state:

- what changed
- why the change is needed
- which doctrine/contracts are affected
- what evidence supports the change
- what validation was run
- what the change proves
- what remains unproven

Large research or runtime-evidence programs should be sliced into independently reviewable claims rather than merged as one heroic diff.

## Definition of done

A contribution is complete when:

1. the intended architectural or evidence change is explicit
2. affected doctrine is internally consistent
3. relevant links and indexes are updated
4. schemas/fixtures are updated when the contract changed
5. source rights and attribution obligations are resolved for any material reuse
6. validation passes
7. the PR clearly states what was proven and what remains unproven

A green validator proves the repository evidence is structurally coherent. It does not absolve runtime systems from reality, which remains stubbornly outside JSON Schema's jurisdiction.
