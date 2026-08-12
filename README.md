<p align="center">
  <img src="assets/brand/agent-memory-readme-banner.png" alt="Agent Memory: governed memory architecture for AI agents, shown with a layered memory stack, connected nodes, and a cyan inference spark." width="100%">
</p>

<div align="center">

# 01010001 Agent Memory

<p><sub><strong>Q Agent Memory</strong></sub></p>

### A reference architecture for governed memory in autonomous and agentic systems

From working memory to inherited state. From biological theory to executable conformance. From probabilistic inference to bounded authority.

[![Validate Doctrine Evidence](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml/badge.svg)](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml)
![Architecture](https://img.shields.io/badge/Architecture-Reference%20Architecture-334155)
[![ADRs](https://img.shields.io/badge/ADRs-Canonical%20Index-2563eb)](docs/adr/README.md)
![Conformance](https://img.shields.io/badge/Conformance-Level%206%20Spec-7c3aed)
[![Fixtures](https://img.shields.io/badge/Fixtures-Validated%20Corpus-0f766e)](fixtures/)
![Research](https://img.shields.io/badge/Research-Open%20Evidence-b45309)
[![License](https://img.shields.io/badge/License-Apache--2.0-0b7285)](LICENSE)

**[Documentation](docs/README.md)** · **[Wiki](https://github.com/MythologIQ-Labs-LLC/agent-memory/wiki)** · **[PAMA](docs/pama/README.md)** · **[Architecture decisions](docs/adr/README.md)** · **[Research map](docs/23-research-bibliography.md)** · **[Conformance](docs/06-conformance-test-plan.md)** · **[Contributing](CONTRIBUTING.md)** · **[Governance](GOVERNANCE.md)** · **[Security](SECURITY.md)**

</div>

---

> [!IMPORTANT]
> **Current maturity:** doctrine, schemas, fixtures, and the reference evidence paths are repository-validated at their declared boundaries. Architecture-decision status is maintained in the **[canonical ADR index](docs/adr/README.md)** rather than duplicated as a hand-maintained count here. Passing repository validation is not the same thing as proving a production memory system behaves correctly.

## The thesis

**Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

That makes memory much larger than retrieval.

A serious memory system must decide:

- what deserves to be encoded
- what should remain ephemeral
- what becomes durable
- what should be consolidated or generalized
- what must remain exact and historical
- what can be trusted, disputed, corrected, shared, or inherited
- what should be forgotten
- what uncertainty must remain visible
- what an agent is actually authorized to change

The core governed-uncertainty model is deliberately simple:

> **Probabilistic epistemics. Governed consequences.**
>
> **Uncertainty may propose. Authority constrains.**

The architecture does **not** require all memory behavior to be deterministic. It requires uncertain inference to remain separate from the authority to create durable consequences.

---

## Start here

You do not need to read the repository front to back. Human working memory has suffered enough.

| If you are... | Start with | Then read |
|---|---|---|
| **Researching memory theory** | [Memory foundations across scales](docs/20-memory-foundations-across-scales.md) | [Forgetting & consolidation](docs/21-forgetting-consolidation-and-memory-metabolism.md), [Research bibliography](docs/23-research-bibliography.md), [Governed uncertainty](docs/24-determinism-probability-and-governed-uncertainty.md) |
| **Designing an agent architecture** | [Layer model](docs/01-layer-model.md) | [Component architecture](docs/11-component-architecture.md), [Composition boundaries](docs/13-system-composition-boundaries.md), [Agentic memory theory](docs/22-agentic-memory-theory-and-development.md) |
| **Designing adaptive authority** | [PAMA foundation](docs/pama/README.md) | [Governance & PAMA](docs/04-governance-and-pama.md), [PAMA decision table](docs/33-pama-decision-table.md), [ADR-004](docs/adr/ADR-004-pama-controls-mutation-authority.md) |
| **Integrating governance consumers** | [Governance Context Projection](docs/profiles/governance-context-projection-profile.md) | [Adapter contracts](docs/34-adapter-contracts.md), [Integration roadmap](docs/07-integration-roadmap.md), [ADR index](docs/adr/README.md) |
| **Implementing a memory system** | [Agentic memory theory](docs/22-agentic-memory-theory-and-development.md) | [Lifecycle](docs/02-lifecycle-state-machine.md), [PAMA](docs/04-governance-and-pama.md), [Recall planner](docs/26-governed-recall-planner.md), [Schemas](schemas/) |
| **Reviewing security or privacy** | [Memory threat model](docs/15-memory-threat-model.md) | [Source trust](docs/16-source-trust-and-reputation.md), [Privacy](docs/19-privacy-and-sensitivity-classifier.md), [Retention & deletion](docs/28-retention-deletion-and-tombstones.md), [Scope & tenancy](docs/29-actor-scope-consent-and-tenancy.md), [Isolation domains](docs/41-memory-isolation-domains-and-governed-crossing.md) |
| **Evaluating conformance** | [Conformance test plan](docs/06-conformance-test-plan.md) | [Calibration](docs/09-calibration-protocol.md), [Audit rubric](docs/25-governed-uncertainty-documentation-conformance-audit.md), [Fixtures](fixtures/) |
| **Reviewing architecture decisions** | [ADR index](docs/adr/README.md) | Follow the current Accepted/Proposed/Superseded status in the index |
| **Tracing influences and aligned projects** | [Aligned projects & intellectual lineage](docs/40-aligned-projects-and-intellectual-lineage.md) | [Source material index](docs/08-source-material-index.md), [Source rights policy](docs/SOURCE_RIGHTS_POLICY.md) |
| **Contributing evidence or challenges** | [CONTRIBUTING.md](CONTRIBUTING.md) | [Evidence promotion policy](docs/policies/EVIDENCE_PROMOTION.md), [Claim/evidence template](docs/templates/claim-evidence-record.md), [Research bibliography](docs/23-research-bibliography.md) |

The complete document map is in **[docs/README.md](docs/README.md)**.

---

## Why this repository exists
