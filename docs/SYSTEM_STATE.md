# System State

**Last reconciled:** 2026-10-13  
**Evidence boundary:** `main` `3eebb6d54e2a218c4fd10cf53c52acac8384c3e6`  
**Purpose:** concise revision-bound projection of implemented capability and remaining qualification. This file is not a competing implementation, roadmap, ADR, or benchmark authority.

## Product objective and boundary

Agent Memory aims to provide governed, hierarchical and **heterogeneous multi-system memory composition**, using the right representation for the task: canonical structured/relational state; lexical/semantic RAG; typed relation/graph and GraphRAG-style context; episodic, procedural and temporal memory; and inspectable Markdown/filesystem projections where justified. **Design intent is not runtime qualification.** Read the original composition contract in [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636) and the active North Star in [#668](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668).

## Implemented versus qualified (as of this SHA)

| Surface | Evidence-backed current posture | Authoritative source |
|---|---|---|
| Public Python API | `AgentMemory` facade exists; consumer contract **1.6.0**. Its declared extractor and proposition additions default off | [API contract](../reference/agentmem_ref/api/contract.py), [facade](../reference/agentmem_ref/api/surface.py) |
| Canonical storage | **SQLite single-host** RC-qualified; reference in-memory/checkpoint path; Graphiti adapter experimental and not canonical-equivalent | [Substrate inventory](43-substrate-inventory-and-maturity.md), closed [#427](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/427) |
| Retrieval and memory types | Native lexical/identity/provenance routes, governed admission, typed temporal/relation capability, procedural and other bounded memory surfaces; semantic/vector support is explicitly opt-in where configured | [Substrate inventory](43-substrate-inventory-and-maturity.md), [runtime](../reference/agentmem_ref/runtime/), [memory](../reference/agentmem_ref/memory/) |
| Heterogeneous multi-substrate production profile | **Not qualified.** PostgreSQL and Markdown canonical stores, distributed durability and full GraphRAG composition must not be represented as shipped | [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636), [substrate inventory](43-substrate-inventory-and-maturity.md) |
| Runtime Baseline | **v6** is the latest published baseline in the register at this boundary; newer candidate work must be evaluated as its own revision | [Baseline register](../reports/runtime/baseline-register.json), [succession contract](67-runtime-baseline-succession.md) |
| Package and optional dependencies | `agent-memory-reference` **0.2.0**; `agent-manifest==0.12.0` and `agentrust-trace==0.10.0` optional comparator pins; #440 closed | [pyproject.toml](../pyproject.toml), [#440](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/440) |
| Benchmark position | Frozen same-harness retrieval evidence exists; external cohort breadth, end-to-end utility and current release maturity still require qualification | [Dashboard](../reports/benchmarks/dashboard/current.md), [#789](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/789) |

**Release posture:** bounded RC/evidence phase, **not production 1.0**, distributed qualification, or demonstrated universal multi-memory superiority. Feature existence, runtime integration, benchmark result and production acceptance are different claims.

## Execution pointers (live issue/PR state takes precedence)

- [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410): integrated runtime, release correctness and limitation ownership.
- [#635](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/635): Gauntlet and revision-bound baseline convergence.
- [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636): heterogenous memory-composition experiments and lifecycle across projections. Its broad pre-activation gate is **under sequencing review**; do not silently treat it as lifted.
- [#668](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668): product/runtime/evaluation North Star; safety and evidence controls retained.
- [#797](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/797): documentation consolidation, overlapping current-state source correction, draft [PR #798](https://github.com/MythologIQ-Labs-LLC/agent-memory/pull/798).

## How to update this page

Update this compact projection only after checking exact code, runtime/substrate qualifications, baseline register and live issues against a pinned SHA. Keep detailed implementation histories and old measurements in their originating docs or historical commits rather than reproducing them here. For governance tiers use [GOVERNANCE_INDEX.md](GOVERNANCE_INDEX.md); for the current work queue use [BACKLOG.md](BACKLOG.md); for ADR authority use [the ADR index](adr/README.md). 
