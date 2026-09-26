# Agent Memory Gauntlet: external benchmark qualification first pass

**Date:** 2026-09-26  
**Owner:** #560  
**Parent:** #554  
**Evidence posture:** research / qualification only  
**Authority effect:** none

This document records the first systematic qualification pass over external memory benchmarks proposed for the Agent Memory Gauntlet.

It does **not** mean that every benchmark listed here is integrated, protocol-comparable, or suitable for leaderboard claims. Qualification decides whether a benchmark adds useful pressure, whether its artifacts can be reproduced, and what constraints must be satisfied before an adapter or execution profile is added.

The controlling rule is:

```text
benchmark exists
    !=
benchmark deserves a Gauntlet integration
```

A benchmark earns integration priority when it adds at least one of:

1. materially distinct capability pressure;
2. stronger independent evidence on a weakly supported dimension;
3. evaluator or adversarial diversity;
4. ecosystem comparability worth its execution cost.

## 1. Qualification states

This pass uses the following states.

| State | Meaning |
|---|---|
| `admit-high` | Strong distinct pressure, usable artifacts, worth implementing an adapter/profile soon. |
| `admit-medium` | Useful independent evidence, but lower urgency, significant overlap, or higher execution cost. |
| `qualify-further` | Promising, but source rights, exact protocol, evaluator, or artifact identity must be resolved first. |
| `blocked` | Important candidate, but a material required artifact/input is currently unavailable. |
| `registered-existing` | Already qualified elsewhere in this repository; reuse that evidence instead of duplicating it. |

An admission recommendation is not a claim that Agent Memory will perform well on the benchmark.

## 2. Current portfolio baseline

Before this pass, the formal registry already had bounded profiles for:

- SWE-ContextBench Lite, currently blocked on exact external corpus/provenance;
- LongMemEval_S, complete;
- LongMemEval_M, not yet run;
- AgentMemBench / MemDialogue deterministic upstream-default re-expression, complete;
- selected not-run upstream judge/portability lanes.

The portfolio is therefore already strong on text retrieval, knowledge updates/currentness pressure, isolation/deletion/concurrency/scale, and deterministic evidence reconstruction.

The most important remaining external-coverage needs are:

- continual online learning and transfer;
- selective forgetting beyond simple deletion;
- explicit remembering-versus-obsolete-memory pressure;
- long agent trajectories rather than dialogue only;
- memory-to-action / interdependent task execution;
- personalization and selective storage;
- multimodal memory;
- broader reflective memory/capacity pressure;
- independent governance evidence remains weak across the public benchmark ecosystem.

## 3. Candidate summary

| Benchmark | Frozen source reviewed | Primary distinct pressure | First-pass status |
|---|---|---|---|
| LoCoMo | `snap-research/locomo@3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376` | very-long conversational QA + event summarization | `admit-medium` |
| MemoryAgentBench | `HUST-AI-HYZ/MemoryAgentBench@538026089d1a8a8eff05121d0db89b388f360eba` | accurate retrieval, test-time learning, long-range understanding, conflict resolution | `admit-high` |
| MemBench | `import-myself/Membench@f66d8d1028d3f68627d00f77a967b93fbb8694b6` | factual vs reflective memory; participation vs observation; effectiveness/efficiency/capacity | `admit-medium` |
| Memora / FAMA | `geniesinc/Memora@a6493188efc836d6511ed5e4163fe3ba87da30ff` | remembering + reasoning + recommending with explicit forgetting-aware scoring | `admit-high` |
| Ground Truth First | existing repo qualification in `docs/59-orthogonal-temporal-gauntlet-qualification.md` | validity intervals, as-of/current temporal applicability | `blocked` |
| Microsoft RHELM | existing repo qualification in `docs/59-orthogonal-temporal-gauntlet-qualification.md` | heterogeneous longitudinal retrieval / misleading queries | `registered-existing` |
| Mem2ActBench | `Cantaloupe-M/Mem2ActBench@b00726940b5abbe9bd324bdd7a2cb272f5c62a29` | memory-grounded tool/action parameterization | `qualify-further` |
| PerMemBench | `yeonjun-in/PerMemBench@3b7454ba70e93b3dcbb8a19bef663e59a024c626` | personalized selective storage under budgets and long user histories | `qualify-further` |
| AgentMemoryBench | `solomoon313/AgentMemoryBench@9dfda8dede15bf16518524e4614ed89344795413` | continual online memory, transfer, forgetting, system + personal memory | `admit-high` |
| AMA-Bench | `AMA-Bench/AMA-Bench@ddfd319e0be33424288c13806f1eafc63e625b59` | long agent-environment trajectories, evidence retrieval, causality/objective information | `admit-high` |
| Mem-Gallery | `YuanchenBei/Mem-Gallery@a93959e1e978a6a7d77798ae92c2ffe41c538c62` | multimodal long-term conversational memory | `admit-high` |
| MemoryArena | `ZexueHe/MemoryArena@6cd9de14b71915e39ac742a20dc33785e14b6aab` | memory-guided action in interdependent multi-session agentic tasks | `admit-medium` |

MemoryArena was not in the original #560 queue, but it is included because it adds a capability class that the queue otherwise underserves.

---

## 4. LoCoMo

**Canonical source reviewed**

- repository: `snap-research/locomo`
- revision: `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`
- paper: *Evaluating Very Long-Term Conversational Memory of LLM Agents* (ACL 2024)
- repository includes data, QA/event-summarization evaluation code, and prompt/evaluation assets.

**Rights posture**

The repository license file is Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). This is materially more restrictive than MIT/Apache and must be preserved in any cached/mirrored dataset or redistributed fixture posture.

**What it measures well**

- very long conversational history;
- single-hop and multi-hop QA pressure;
- temporal/event reasoning within dialogue;
- event summarization;
- long-context retrieval and reasoning under realistic conversation structure.

**Overlap**

There is meaningful overlap with LongMemEval, MemoryAgentBench, RHELM, and the LoCoMo-derived dialogue components used by other suites. Running LoCoMo still has ecosystem-comparability value, but it is no longer the best answer to every long-term-memory question.

**Recommendation: `admit-medium`**

Add a protocol-faithful profile if execution cost is reasonable, primarily for ecosystem comparability and event-summarization/multi-hop pressure. Do not treat it as the primary temporal/currentness or governance benchmark.

---

## 5. MemoryAgentBench

**Canonical source reviewed**

- repository: `HUST-AI-HYZ/MemoryAgentBench`
- revision: `538026089d1a8a8eff05121d0db89b388f360eba`
- paper: *Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions* (ICLR 2026)
- released Hugging Face dataset exists (`ai-hyz/MemoryAgentBench`).
- code license: MIT at the frozen revision.

**Core competencies**

1. Accurate Retrieval;
2. Test-Time Learning;
3. Long-Range Understanding;
4. Conflict Resolution.

The repository reformulates multiple long-context datasets into incremental multi-turn interaction and adds EventQA and FactConsolidation. Deterministic exact-match lanes exist for multiple subsets, while LongMemEval/InfBench lanes may require judge-style evaluation.

**Unique pressure relative to current portfolio**

- test-time learning is underrepresented today;
- conflict resolution is broader than simple latest-fact retrieval;
- long-range understanding stresses composition rather than only candidate recall;
- incremental ingestion better reflects a live memory system than static long-context reading.

**Protocol risk**

Some components inherit data/protocol semantics from other upstream datasets. The Gauntlet adapter should preserve subset identity and must not collapse heterogeneous metrics into one universal score.

**Recommendation: `admit-high`**

This should be one of the next external integrations. Prefer deterministic subsets first, then separately qualify any LLM-judge lanes.

---

## 6. MemBench

**Canonical source reviewed**

- repository: `import-myself/Membench`
- revision: `f66d8d1028d3f68627d00f77a967b93fbb8694b6`
- paper: *MemBench: Towards More Comprehensive Evaluation on the Memory of LLM-based Agents* (ACL Findings 2025)
- repository README currently advertises MIT licensing; first pass did not locate a separately reviewed canonical license file, so license-file verification remains required before vendoring or redistribution.

**Distinct design**

- factual memory versus reflective memory;
- participation versus observation interaction scenarios;
- effectiveness, efficiency, and capacity;
- long/noisy histories and large-context stress.

**Unique pressure**

The reflective-memory and observation dimensions are useful because many retrieval benchmarks effectively test only factual memory supplied through first-person interaction.

**Overlap**

Efficiency/capacity and long-history retrieval overlap with AgentMemBench, LongMemEval, and synthetic scale evidence. Its value is primarily scenario/memory-level diversity.

**Recommendation: `admit-medium`**

Worth integrating after the higher-priority distinct suites. Verify explicit code/data licensing and exact downloadable dataset identity first.

---

## 7. Memora / FAMA

**Canonical source reviewed**

- repository: `geniesinc/Memora`
- revision: `a6493188efc836d6511ed5e4163fe3ba87da30ff`
- paper: *From Recall to Forgetting: Benchmarking Long-Term Memory for Personalized Agents* (ACL 2026)
- code/data repository states Apache-2.0.
- released dataset and evaluation code are present.

**Primary contribution**

Memora evaluates remembering, reasoning, and recommending across weekly/monthly/quarterly horizons while explicitly crediting both information that should remain available and information that should have been forgotten or invalidated. Its FAMA score combines presence and forgetting-aware behavior.

**Evaluator integrity note**

The frozen source includes a 2026 correction for a previously silent multi-judge import/fallback defect. The repaired implementation can hard-fail via strict judge mode instead of silently degrading from the published multi-judge protocol. The Gauntlet profile must pin this repaired revision or later and must expose judge identity/configuration.

**Unique pressure**

- forgetting-aware answer quality;
- obsolete/removed information pressure;
- personalized long-horizon recommending/reasoning, not retrieval only;
- explicit evaluator-integrity lesson relevant to the Gauntlet's fail-closed doctrine.

**Recommendation: `admit-high`**

Prioritize a deterministic/core lane where possible and keep FAMA subcomponents visible. Do not reduce remembering and forgetting into a single opaque portfolio score even if the native benchmark emits FAMA.

---

## 8. Ground Truth First

**Prior qualification**

Reuse `docs/59-orthogonal-temporal-gauntlet-qualification.md` rather than duplicating the ADR-039 work.

The prior pass found the Veracium repository/library but did not locate the benchmark generator, corpus, or question set required for the claimed validity-interval/as-of evaluation. The paper was not available through that session's permitted source path.

**Why it still matters**

This remains one of the strongest conceptual candidates for explicit validity intervals and as-of temporal applicability, exactly where ADR-039 still lacks independent external evidence.

**Recommendation: `blocked`**

Do not manufacture a corpus from the paper description. Integrate only after the exact released benchmark artifacts and source-rights posture are available.

---

## 9. Microsoft RHELM

**Prior qualification**

Reuse `docs/59-orthogonal-temporal-gauntlet-qualification.md`.

Frozen prior evidence:

- `microsoft/RHELM@5e170da` (MIT);
- Hugging Face dataset revision `d0e8e0c` (CC BY 4.0);
- deterministic evidence-recall lane is runnable without an API;
- 1,305 questions, but only 17 carried a high-confidence `current` cue in the prior analysis;
- no per-fact validity interval or explicit as-of class was found.

**Unique pressure**

Heterogeneous longitudinal sources and misleading queries remain useful. It is better viewed as longitudinal evidence/retrieval pressure than as decisive ADR-039 validity evidence.

**Recommendation: `registered-existing`**

Add an executable Gauntlet profile when bandwidth permits, but do not use it as the missing independent validity/as-of gate for ADR-039.

---

## 10. Mem2ActBench

**Canonical source reviewed**

- repository: `Cantaloupe-M/Mem2ActBench`
- revision: `b00726940b5abbe9bd324bdd7a2cb272f5c62a29`
- repository includes conversation construction, conflict/fact extraction, QA/tool-call construction, normalization code, a checked-in benchmark dataset tree, BFCL-derived formatted conversations, and an English paper PDF.
- no explicit top-level license file was observed in the frozen root listing during this pass.

**Distinct pressure**

Mem2ActBench pushes memory beyond answer retrieval into memory-grounded action/tool construction. Parameters may need to be explicitly or inferentially grounded in remembered evidence, and the benchmark contains source-grounding machinery.

**Why it matters**

This tests the important transition:

```text
memory retrieved
    ->
memory correctly influences an action
```

That is a materially different question from whether a gold passage appeared in top-k.

**Risks / blockers**

- explicit redistribution/use license must be verified;
- evaluator uses model-assisted construction/verification in portions of the pipeline;
- BFCL-derived data and generated artifacts require source-rights review;
- protocol-faithful execution is more involved than a simple retrieval adapter.

**Recommendation: `qualify-further`**

High conceptual value, but do not integrate until license/data-use and frozen protocol inputs are explicit. If cleared, it should become a high-value memory-to-action profile rather than a retrieval profile.

---

## 11. PerMemBench

**Canonical source reviewed**

- repository: `yeonjun-in/PerMemBench`
- revision: `3b7454ba70e93b3dcbb8a19bef663e59a024c626`
- paper: *Personalize-then-Store: Benchmarking and Learning Personalized Memory for Long-horizon Agents* (`arXiv:2605.25535`)
- repository contains the benchmark-generation pipeline, Mem0 experiments, storage-gating baselines, retention evaluation, and a released benchmark ZIP.
- no top-level license file was found at the frozen revision during this pass.

**Distinct pressure**

- personalized memory policy rather than universal storage policy;
- long-horizon versus transient session discrimination;
- multi-year and multi-domain user histories;
- storage-budget pressure;
- selective memory formation/gating rather than recall alone;
- behavioral pattern shifts over time.

**Why it matters**

The Gauntlet currently has much stronger evidence about retrieval after memory exists than about whether a system chose the right experiences to retain under constrained capacity. PerMemBench directly pressures that gap.

**Risks / blockers**

- explicit code/data license and redistribution posture must be established;
- the reference implementation is coupled to Mem0/gating experiments, so a system-neutral adapter contract needs careful design;
- generation/evaluation can be API-heavy, though the released dataset may permit a bounded frozen lane.

**Recommendation: `qualify-further`**

Keep high in the queue. Resolve licensing and define a frozen dataset-only system-neutral lane before integration.

---

## 12. AgentMemoryBench

**Canonical source reviewed**

- repository: `solomoon313/AgentMemoryBench`
- revision: `9dfda8dede15bf16518524e4614ed89344795413`
- repository license: MIT.
- benchmark describes five evaluation modes and six interactive tasks spanning code-grounded, embodied, web-grounded, and dialogue-grounded settings.

**Core pressure**

- continual online learning;
- transfer;
- forgetting;
- streaming updates;
- both system/task memory and personal/user memory;
- interactive environments rather than dialogue alone.

**Unique value**

This is one of the clearest independent tests of memory as a continual-learning system. It pressures whether retained experience improves later behavior, whether knowledge transfers, and whether old information interferes.

**Comparability caution**

Task metrics are heterogeneous. The Gauntlet must preserve task/mode-specific metrics rather than publish one universal AgentMemoryBench score.

**Recommendation: `admit-high`**

Prioritize after or alongside MemoryAgentBench. The two overlap in naming but not in purpose: MemoryAgentBench focuses four memory competencies through incremental interactions; AgentMemoryBench focuses continual online learning/transfer/forgetting across interactive tasks.

---

## 13. AMA-Bench

**Canonical source reviewed**

- repository: `AMA-Bench/AMA-Bench`
- revision: `ddfd319e0be33424288c13806f1eafc63e625b59`
- paper: *AMA-Bench: Evaluating Long-Horizon Memory for Agentic Applications* (ICML 2026)
- repository license: MIT.
- official dataset is released on Hugging Face.

**Distinct design**

AMA-Bench evaluates memory construction and retrieval from long **agent-environment trajectories**, including machine-generated action/observation history rather than only human dialogue. It provides real-world trajectories and synthetic trajectories that can scale to arbitrary horizons.

The native interface separates:

```text
memory_construction(trajectory)
memory_retrieve(memory, question)
```

**Unique pressure**

- long agentic trajectories;
- objective/tool/environment information;
- causal evidence;
- retrieval from machine-generated histories;
- synthetic horizon scaling;
- open-ended and multiple-choice QA.

**Evaluator dependence**

The default open-ended lane uses generation plus an LLM judge. Rule-based/synthetic or other deterministic subsets should be qualified separately where available.

**Recommendation: `admit-high`**

This fills a major dialogue-centric blind spot in the current portfolio. Implement a bounded deterministic/reconstructable lane first if one can be isolated, then qualify open-ended judge lanes separately.

---

## 14. Mem-Gallery

**Canonical source reviewed**

- repository: `YuanchenBei/Mem-Gallery`
- revision: `a93959e1e978a6a7d77798ae92c2ffe41c538c62`
- paper: *Mem-Gallery: Benchmarking Multimodal Long-Term Conversational Memory for MLLM Agents* (ACL 2026 main)
- repository license: MIT.
- complete multimodal conversations and evaluation QAs are released through Hugging Face according to the project documentation.

**Functional dimensions**

The benchmark evaluates multimodal memory extraction/test-time adaptation, memory reasoning, and memory knowledge management. The released framework includes visual-centric search, answer refusal, conflict detection, multimodal retrieval/encoders, and multiple memory architectures.

**Unique pressure**

This is the clearest candidate for a major current white space: Agent Memory's external portfolio is overwhelmingly text-based. Even if the production runtime does not yet claim multimodal support, the Gauntlet should represent the dimension truthfully rather than quietly define memory as text because that is convenient.

**Cost / environment**

Native execution expects modern multimodal model infrastructure, CUDA-class environments, and potentially model/API judging. A profile may therefore initially be `not_applicable` for text-only contestants while remaining a valid Gauntlet dimension.

**Recommendation: `admit-high`**

Qualify data rights and a smallest protocol-faithful slice, then integrate. Do not force text-only systems to fail a modality they do not claim; report unsupported/not-applicable according to the capability contract.

---

## 15. MemoryArena

**Discovered during this pass**

- repository: `ZexueHe/MemoryArena`
- revision: `6cd9de14b71915e39ac742a20dc33785e14b6aab`
- paper: *MemoryArena: Benchmarking Agent Memory in Interdependent Multi-Session Agentic Tasks* (`arXiv:2602.16313`)
- the reviewed repository describes itself as a preview implementation and integrates shopping, travel planning, web search, formal reasoning, and multiple memory-system backends.
- an explicit license file was not established in this first pass, so rights must be confirmed before integration.

**Distinct pressure**

Unlike recall-centric suites, MemoryArena evaluates whether memory from earlier sessions changes the quality of actions in later interdependent tasks. The agent acts in an environment, receives observations/rewards, stores experiences, and must use them later.

**Why it matters**

This is a strong independent challenge to the assumption that retrieval metrics predict useful agent memory. A system may look excellent on long-context QA while failing when memory has to guide subsequent action.

**Execution cost / complexity**

This is an environment-heavy benchmark with multiple external APIs/services and per-environment setup. It is correspondingly more expensive and less suitable as a default fast Gauntlet suite.

**Recommendation: `admit-medium`**

Keep as a high-value extended/action suite after license and protocol stabilization. It should not block the core Gauntlet alpha, but it fills a crucial capability dimension.

---

## 16. First-pass admission order

The qualification pass does **not** recommend implementing all candidates simultaneously.

Recommended next integration order:

### Tier A: next adapters/profiles

1. **MemoryAgentBench** - broad deterministic competency pressure and conflict/test-time-learning value.
2. **Memora / FAMA** - independent forgetting/obsolete-memory pressure and strong evaluator-integrity relevance.
3. **AMA-Bench** - agent-trajectory and causal/objective-memory pressure outside dialogue.
4. **AgentMemoryBench** - continual online learning, transfer, and forgetting across interactive tasks.
5. **Mem-Gallery** - multimodal coverage, initially capability-negotiated rather than mandatory.

### Tier B: useful extensions

6. **LoCoMo** - ecosystem comparability and event/multi-hop pressure.
7. **MemBench** - reflective/observational/capacity diversity.
8. **RHELM** - heterogeneous longitudinal retrieval.
9. **MemoryArena** - extended memory-to-action suite after rights/environment stabilization.

### Tier C: resolve qualification blockers

10. **Mem2ActBench** - verify license/data rights and freeze an action-grounding protocol.
11. **PerMemBench** - verify license and define system-neutral personalized storage lane.
12. **Ground Truth First** - locate the actual released generator/corpus/questions before any implementation.

## 17. Coverage implications

After this first pass, the external ecosystem can plausibly cover many more dimensions than the current registered suite, but important gaps remain.

### Strongly coverable externally

- factual retrieval;
- long-horizon dialogue;
- conflict resolution / knowledge updates;
- test-time learning;
- long-range understanding;
- forgetting/obsolete information;
- reflective memory;
- storage capacity/efficiency;
- personalization/selective storage;
- continual online learning;
- transfer/interference;
- agent-trajectory memory;
- memory-guided action;
- multimodal conversational memory.

### Still weak or fragmented externally

#### Governance and authority

The public benchmark field still does not provide a comprehensive neutral suite for:

- tenant/scope/purpose isolation;
- identifier/cardinality leakage;
- authority laundering through relevance/recency/similarity/classification;
- audit confidentiality;
- governance persistence across restart;
- provenance assertions versus verified provenance;
- correction/supersession/dispute semantics under policy.

The Gauntlet-native Governance Alpha exists specifically because this remains a demonstrated ecosystem gap.

#### Runtime durability / integrity

Public suites rarely test:

- crash/restart recovery;
- tamper detection;
- checkpoint/journal integrity;
- concurrent handle behavior;
- deterministic recovery identity;
- migration compatibility.

This remains a likely justified Gauntlet-native operational gap suite.

#### Memory metabolism trajectories

External suites test forgetting and updates, but coverage remains weak for the full trajectory of:

```text
weak observation
-> reinforcement
-> saturation/consolidation
-> time decay
-> contradictory evidence
-> renewed evidence
-> pruning pressure
-> later recall
```

Do not create a metabolism benchmark solely because Agent Memory implements metabolism. The gap should first be tested against the newly admitted external suites to determine whether their protocols can be adapted without distortion.

#### Prospective / conditional memory

Remembering to surface or act on information when a future condition becomes true remains poorly covered by the identified external benchmarks.

#### Explicit temporal validity / as-of state

Ground Truth First remains conceptually strong here but blocked on artifacts. RHELM and the other qualified suites do not fully replace explicit validity-interval/as-of testing.

## 18. Gauntlet-native benchmark creation gate

This first pass strengthens the rule that Agent Memory should **not** respond to every uncovered box by writing its own benchmark.

Before proposing a native gap benchmark:

1. document the uncovered Atlas dimension;
2. show that qualified external suites do not directly test it;
3. determine whether an admitted external protocol can be extended without changing its meaning;
4. define a system-neutral task ontology before running Agent Memory;
5. freeze generator/input/seed/metrics before using the benchmark for product claims;
6. include trivial/reference baselines;
7. make it possible for Agent Memory to fail;
8. label results `gauntlet_native_gap`, never independent external evidence.

## 19. Immediate actions from this qualification pass

Recommended follow-up issues, in order:

1. implement a **MemoryAgentBench deterministic competency profile**;
2. implement a **Memora/FAMA qualification adapter** with strict evaluator identity and separated remembering/forgetting dimensions;
3. qualify the smallest deterministic/reconstructable **AMA-Bench** lane;
4. qualify an **AgentMemoryBench continual-learning** subset with task metrics preserved separately;
5. qualify **Mem-Gallery** dataset/data-rights and modality negotiation before execution;
6. open a source-rights clarification item for **Mem2ActBench** and **PerMemBench** instead of silently assuming permission;
7. periodically recheck **Ground Truth First** artifact availability;
8. keep **MemoryArena** as an extended action-suite candidate rather than a core-alpha dependency.

## 20. Controlling conclusions

The Agent Memory Gauntlet should be comprehensive by **coverage**, not by benchmark count.

The qualified external landscape is now broad enough that Agent Memory should resist inventing custom retrieval, continual-learning, multimodal, personalized-storage, or memory-to-action benchmarks merely to fill its repository.

The strongest demonstrated spaces for Gauntlet-native work remain governance/authority, runtime durability/integrity, and potentially prospective/metabolic memory if future external qualification still leaves those dimensions materially uncovered.

Finally:

```text
external benchmark pressure
    -> evidence
    -> architecture/product learning

not

external benchmark pressure
    -> benchmark-specific runtime behavior
```

A benchmark enters the Gauntlet to challenge memory systems. It does not get to rewrite them merely by existing.
