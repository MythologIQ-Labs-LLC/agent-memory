# Agent Memory Documentation

This directory is the canonical documentation map for the Agent Memory reference architecture.

The repository is intentionally layered. Start with the smallest path that answers your question, then follow links deeper. Reading all thirty-four numbered documents in numerical order is legal, but there are more humane options.

## Choose your path

| Reader | Start here | Then continue to |
|---|---|---|
| Researcher / theorist | [`20-memory-foundations-across-scales.md`](20-memory-foundations-across-scales.md) | `21`, `23`, `24` |
| Agent architect | [`01-layer-model.md`](01-layer-model.md) | `11`, `13`, `22`, `24` |
| Implementer | [`22-agentic-memory-theory-and-development.md`](22-agentic-memory-theory-and-development.md) | `02`-`10`, `26`-`32`, schemas and fixtures |
| Security / privacy reviewer | [`15-memory-threat-model.md`](15-memory-threat-model.md) | `16`, `19`, `28`, `29` |
| Evaluator / governance reviewer | [`06-conformance-test-plan.md`](06-conformance-test-plan.md) | `09`, `24`, `25`, audit records |
| Product / UX designer | [`11-component-architecture.md`](11-component-architecture.md) | `19`, `22`, `26`, correction/recall surfaces |
| ADR reviewer | [`adr/README.md`](adr/README.md) | ADR-001 through ADR-020 |

## 00-10: Canonical architecture spine

| # | Document | Purpose |
|---|---|---|
| 00 | [`00-glossary.md`](00-glossary.md) | Canonical vocabulary and term boundaries |
| 01 | [`01-layer-model.md`](01-layer-model.md) | Layer ownership, deterministic substrate, probabilistic epistemics, governance boundaries |
| 02 | [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md) | Memory states, proposal-versus-commit, promotion, dispute, correction, pruning |
| 03 | [`03-scoring-and-decay.md`](03-scoring-and-decay.md) | Saturation, decay, uncertainty, calibration, drift, threshold stability |
| 04 | [`04-governance-and-pama.md`](04-governance-and-pama.md) | Mutation authority and bounded consequence |
| 05 | [`05-repo-implementation-map.md`](05-repo-implementation-map.md) | Mapping of related systems into the architecture |
| 06 | [`06-conformance-test-plan.md`](06-conformance-test-plan.md) | Conformance Levels 0-6 and adversarial fixture requirements |
| 07 | [`07-integration-roadmap.md`](07-integration-roadmap.md) | Doctrine-to-implementation roadmap |
| 08 | [`08-source-material-index.md`](08-source-material-index.md) | Internal provenance and external evidence domains |
| 09 | [`09-calibration-protocol.md`](09-calibration-protocol.md) | Calibration, abstention, hysteresis, disagreement, drift |
| 10 | [`10-memory-unit-examples.md`](10-memory-unit-examples.md) | Concrete memory, uncertainty, authority, receipt, and scope examples |

## 11-19: Composition, security, trust, time, and privacy

| # | Document | Purpose |
|---|---|---|
| 11 | [`11-component-architecture.md`](11-component-architecture.md) | Component boundaries and control character |
| 12 | [`12-concept-segmentation-matrix.md`](12-concept-segmentation-matrix.md) | Where concepts belong and when they deserve promotion into doctrine |
| 13 | [`13-system-composition-boundaries.md`](13-system-composition-boundaries.md) | Typed handoffs and composition-specific failure modes |
| 14 | [`14-expanded-scope-recommendations.md`](14-expanded-scope-recommendations.md) | Controlled architecture expansion candidates |
| 15 | [`15-memory-threat-model.md`](15-memory-threat-model.md) | Poisoning, leakage, authority laundering, deletion residue, composition attacks |
| 16 | [`16-source-trust-and-reputation.md`](16-source-trust-and-reputation.md) | Source trust, independence, latent preference, reputation scope |
| 17 | [`17-conflict-resolution-engine.md`](17-conflict-resolution-engine.md) | Conflict interpretation and governed resolution consequences |
| 18 | [`18-temporal-causality-layer.md`](18-temporal-causality-layer.md) | Event time, valid time, supersession, causal uncertainty, prospective memory |
| 19 | [`19-privacy-and-sensitivity-classifier.md`](19-privacy-and-sensitivity-classifier.md) | Sensitivity, recall privacy, minimization, composition leakage, deletion fidelity |

## 20-25: Interdisciplinary theory and governed uncertainty

| # | Document | Purpose |
|---|---|---|
| 20 | [`20-memory-foundations-across-scales.md`](20-memory-foundations-across-scales.md) | Biological, cognitive, agentic, collective, inherited, and evolutionary-scale memory |
| 21 | [`21-forgetting-consolidation-and-memory-metabolism.md`](21-forgetting-consolidation-and-memory-metabolism.md) | Forgetting, consolidation, semanticization, deletion, and memory metabolism |
| 22 | [`22-agentic-memory-theory-and-development.md`](22-agentic-memory-theory-and-development.md) | Engineering doctrine, memory functions, write/read paths, development sequence |
| 23 | [`23-research-bibliography.md`](23-research-bibliography.md) | Dated evidence map across memory science and agent-memory research |
| 24 | [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md) | Deterministic substrate, probabilistic epistemics, bounded authority, doctrine challenges |
| 25 | [`25-governed-uncertainty-documentation-conformance-audit.md`](25-governed-uncertainty-documentation-conformance-audit.md) | GU-1 through GU-10 documentation-conformance rubric |

## 26-33: Executable and operational contracts

| # | Document | Purpose |
|---|---|---|
| 26 | [`26-governed-recall-planner.md`](26-governed-recall-planner.md) | Candidate retrieval versus governed context admission |
| 27 | [`27-schema-registry-and-type-evolution.md`](27-schema-registry-and-type-evolution.md) | Semantic schema compatibility and type evolution |
| 28 | [`28-retention-deletion-and-tombstones.md`](28-retention-deletion-and-tombstones.md) | Forgetting modes, deletion propagation, tombstones, verification |
| 29 | [`29-actor-scope-consent-and-tenancy.md`](29-actor-scope-consent-and-tenancy.md) | Principals, delegation, consent, purpose, tenancy, sharing scope |
| 30 | [`30-memory-observability-and-audit-events.md`](30-memory-observability-and-audit-events.md) | Structured memory events and reconstruction evidence |
| 31 | [`31-recovery-rollback-and-replay.md`](31-recovery-rollback-and-replay.md) | Recovery, compensation, state/version binding, replay semantics |
| 32 | [`32-memory-quality-metrics.md`](32-memory-quality-metrics.md) | Ongoing quality, safety, calibration, deletion, and outcome metrics |
| 33 | [`33-pama-decision-table.md`](33-pama-decision-table.md) | Mutation type and risk class to minimum authority outcome, with modifiers |

## Architecture Decision Records

See [`adr/README.md`](adr/README.md).

Current doctrine state:

```text
ADR-001 through ADR-019: Accepted
ADR-020: Proposed
```

ADR-020 remains Proposed because it explicitly requires real end-to-end runtime evidence, including repeated behavioral evidence for stochastic containment. Documentation, schemas, and structurally valid fixtures are necessary but not sufficient.

## Governed-uncertainty audit trail

The repository preserves baseline and post-remediation evidence rather than overwriting history with the pleasant fiction that the doctrine was always this coherent.

Audit records live in [`audits/governed-uncertainty/`](audits/governed-uncertainty/).

Start with:

- [`25-governed-uncertainty-documentation-conformance-audit.md`](25-governed-uncertainty-documentation-conformance-audit.md)
- [`audits/governed-uncertainty/02-implementation-and-conformance.md`](audits/governed-uncertainty/02-implementation-and-conformance.md)
- [`audits/governed-uncertainty/03-component-composition.md`](audits/governed-uncertainty/03-component-composition.md)
- [`audits/governed-uncertainty/04-threat-trust-conflict-causality-privacy.md`](audits/governed-uncertainty/04-threat-trust-conflict-causality-privacy.md)
- [`audits/governed-uncertainty/05-interdisciplinary-theory.md`](audits/governed-uncertainty/05-interdisciplinary-theory.md)
- [`audits/governed-uncertainty/06-adr-status-and-alignment.md`](audits/governed-uncertainty/06-adr-status-and-alignment.md)
- [`audits/governed-uncertainty/07b-machine-readable-evidence.md`](audits/governed-uncertainty/07b-machine-readable-evidence.md)
- [`audits/governed-uncertainty/07c-adr-evidence-acceptance.md`](audits/governed-uncertainty/07c-adr-evidence-acceptance.md)

## Machine-readable evidence

Schemas:

- [`../schemas/memory-unit.schema.json`](../schemas/memory-unit.schema.json)
- [`../schemas/conformance-report.schema.json`](../schemas/conformance-report.schema.json)
- [`../schemas/decision-receipt.schema.json`](../schemas/decision-receipt.schema.json)
- [`../schemas/memory-audit-event.schema.json`](../schemas/memory-audit-event.schema.json)

Conformance fixtures:

- [`../fixtures/`](../fixtures/)

Validation:

```bash
python -m pip install jsonschema
python scripts/validate_fixtures.py fixtures
python scripts/validate_schemas.py
```

Repository CI runs the same validation through [`../.github/workflows/validate-doctrine-evidence.yml`](../.github/workflows/validate-doctrine-evidence.yml).

## Evidence posture

Research may support, challenge, narrow, or reject an architectural idea.

Prefer freely inspectable research where practical, but do not let accessibility outrank evidence quality. Biological and cognitive research should be classified as native mechanism, functional analogy, engineering prescription, or open hypothesis before it is transferred into software doctrine.

The repository's job is not to collect citations until an idea looks inevitable. Its job is to make assumptions inspectable enough that good evidence can change them.
