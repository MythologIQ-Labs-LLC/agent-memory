# Agent Memory Benchmark Coverage Atlas

**Status:** Proposed foundation artifact under #554  
**Purpose:** Map what the memory benchmark portfolio actually tests, expose blind spots, and govern admission of new benchmarks or creation of Gauntlet-native gap suites.  
**Authority effect:** none

## 1. Why an Atlas exists

A benchmark portfolio can become large while remaining narrow.

Ten benchmarks that all measure retrieval from long conversations do not provide comprehensive memory-system evidence merely because the spreadsheet has ten rows.

The Coverage Atlas therefore treats benchmarks as evidence sources against a capability map.

The governing question is not:

> How many benchmarks do we run?

It is:

> Which important memory-system claims are directly pressured by independent evidence, which are only partially or indirectly exercised, and which remain white space?

The Atlas also prevents the inverse problem: creating Agent Memory-native benchmarks merely because the runtime has an interesting feature.

```text
feature exists
    !=
field-wide benchmark gap exists
```

A Gauntlet-native benchmark is justified only after a material coverage gap is demonstrated.

## 2. Relationship to the Gauntlet

```text
external benchmark landscape
        |
        v
qualification / admission
        |
        v
Coverage Atlas
        |
        +--> qualified external benchmark profiles
        +--> blocked / rejected / watchlist candidates
        +--> demonstrated capability gaps
        |
        v
Agent Memory Gauntlet suites
```

The Atlas is descriptive and evidence-governance infrastructure. It does not rank memory systems.

## 3. Coverage-state vocabulary

Each benchmark x capability cell uses one of these states.

| Symbol | State | Meaning |
| --- | --- | --- |
| `●` | direct | The benchmark explicitly and materially measures the capability. |
| `◐` | partial | The capability is materially exercised, but only a subset or proxy is measured. |
| `△` | indirect | The capability may affect results, but the benchmark does not isolate or score it as a first-class property. |
| `○` | not covered | The benchmark does not meaningfully test the capability. |
| `?` | unqualified | Coverage has not yet been verified against the exact public protocol/corpus/evaluator. |
| `⊘` | not applicable | The capability is outside the benchmark's intended scope. |
| `B` | blocked | Qualification or execution is blocked by missing corpus/provenance/rights/runtime requirements. |

These states are not scores.

## 4. Benchmark provenance classes

Every benchmark profile must declare one provenance class.

### `external_independent`

Designed and published independently of Agent Memory/MythologIQ.

This is the strongest class for independent efficacy evidence when protocol fidelity is preserved.

### `external_adapted`

An independent benchmark executed through an Agent Memory Gauntlet adapter/profile.

The task and evaluator remain external; the integration is ours.

Most executable public Gauntlet profiles will live here.

### `gauntlet_native_gap`

A system-neutral benchmark designed within the Agent Memory project specifically because the Coverage Atlas demonstrated an important gap not adequately served by viable external benchmarks.

This is valid falsification and coverage evidence, but it is not independent evidence that Agent Memory's runtime is superior.

### `agent_memory_conformance`

A fixture/suite designed to test an Agent Memory architecture, contract, invariant, or implementation claim.

It is not a neutral comparative benchmark unless independently generalized and requalified.

### `baseline_or_probe`

A deterministic baseline, mutation probe, evaluator-integrity probe, or instrumentation profile used to interpret benchmark behavior rather than represent a memory product.

## 5. Benchmark admission states

A benchmark candidate moves through explicit states.

```text
discovered
  -> qualification_pending
  -> qualified / rejected / blocked / watchlist
  -> adapter_ready
  -> evidence_complete / evidence_partial
```

Definitions:

- `discovered`: known candidate, no protocol judgment yet;
- `qualification_pending`: active evidence review;
- `qualified`: suitable for at least one declared Gauntlet profile;
- `rejected`: unsuitable, with reason retained;
- `blocked`: potentially suitable but required input/provenance/rights/tooling unavailable;
- `watchlist`: interesting but insufficiently mature/distinct to justify integration now;
- `adapter_ready`: executable through a bounded profile;
- `evidence_complete`: declared profile has frozen reconstructable evidence;
- `evidence_partial`: some required variants/dimensions remain incomplete.

A popular benchmark is not automatically qualified.

## 6. Benchmark admission criteria

A candidate should be admitted only when it adds defensible pressure.

### Required qualification questions

1. **What claim does it actually measure?**
   - retrieval;
   - answer generation;
   - state maintenance;
   - currentness;
   - task completion;
   - personalization;
   - governance;
   - some combination.

2. **Can the exact input be reconstructed or frozen?**

3. **Are source rights and redistribution/use conditions understood?**

4. **Can the evaluator be reproduced?**

5. **Does evaluation require a model judge? If so, is model/provider/version/configuration bound?**

6. **Can the benchmark be run against more than one system without architecture-specific privilege?**

7. **Does the benchmark add a distinct capability pressure compared with already-qualified profiles?**

8. **Can a no-memory or simple baseline be meaningfully defined where relevant?**

9. **Does the protocol leak gold labels or privileged metadata to the system under test?**

10. **Can failures be attributed between benchmark adapter, system adapter, evaluator, and SUT?**

11. **Is cost bounded enough to reproduce or is a clearly declared bounded profile possible?**

12. **Does the benchmark conflate memory quality with unrelated model quality in a way that cannot be separated?**

A benchmark may still be useful if answer generation is intentionally part of the task, but it must not be presented as pure memory retrieval evidence.

## 7. Capability taxonomy

The Atlas uses a broader capability taxonomy than the first common Memory Evaluation reporting dimensions.

The common run schema may continue to normalize to high-level dimensions such as retrieval/currentness/governance/efficiency while the Atlas tracks finer-grained coverage.

### A. Ingestion and representation

- observation ingestion;
- structured metadata ingestion;
- provenance/source retention;
- explicit temporal metadata;
- entity identity;
- relation/graph representation;
- multimodal ingestion;
- high-volume ingestion.

### B. Retrieval and relevance

- lexical retrieval;
- semantic/vector retrieval;
- exact identity retrieval;
- graph/relational retrieval;
- multi-hop retrieval;
- hybrid/composed retrieval;
- top-k ranking quality;
- relevance thresholding / abstention;
- implicit recall;
- structured timeline/transition recall.

### C. Temporal memory

- current-state recall;
- knowledge updates;
- as-of recall;
- historical recall;
- valid-time intervals;
- event-time vs transaction-time separation;
- temporary exceptions;
- prospective memory;
- event-relative reasoning;
- stale-vs-current conflict.

### D. Lifecycle and metabolism

- correction;
- supersession;
- contradiction/dispute;
- selective forgetting;
- deletion semantics;
- retention/expiry;
- reinforcement;
- decay/half-life;
- consolidation;
- crystallization/stabilization;
- pruning;
- reactivation after decay;
- lifecycle history/provenance.

### E. Governance and safety

- tenant isolation;
- scope isolation;
- purpose limitation;
- source/provenance trust;
- consent/sensitivity boundaries;
- recall admission policy;
- mutation authority;
- authority laundering resistance;
- prompt-injected memory resistance;
- poisoning resistance;
- deletion resurrection resistance;
- caller-visible leakage;
- audit completeness;
- audit confidentiality;
- policy/version reproducibility.

### F. Operational durability

- restart/recovery;
- checkpoint integrity;
- tamper detection;
- deterministic replay;
- cross-thread use;
- concurrency correctness;
- multi-writer behavior;
- storage scaling;
- write scaling;
- recall scaling;
- memory/storage footprint;
- latency;
- cost.

### G. Cognition and task utility

- factual QA from memory;
- reflective/summarizing memory;
- temporal reasoning;
- causal reasoning;
- personalization;
- recommendation;
- planning support;
- memory-to-action/tool use;
- task success;
- cross-session adaptation;
- continual learning;
- transfer;
- catastrophic forgetting/interference.

### H. Multi-source / multi-agent / multimodal

- cross-document memory;
- email/document/conversation synthesis;
- multi-agent memory sharing;
- source-specific conflict;
- multimodal memory;
- cross-modal retrieval;
- shared-memory governance.

### I. Evaluator quality

- perturbation sensitivity;
- gold omission sensitivity;
- distractor sensitivity;
- metric reproducibility;
- judge stability;
- contamination/leakage posture;
- deterministic replay of evaluator;
- profile comparability checks.

## 8. Currently registered executable external profiles

The repository's current evaluation registry contains these formal external profiles.

| Profile | Status | Primary pressure |
| --- | --- | --- |
| SWE-ContextBench Lite external retrieval | blocked on exact frozen projection/provenance | prior-experience retrieval, ranking, reproducibility |
| LongMemEval_S full | complete | multi-session retrieval, knowledge-update currentness, efficiency |
| LongMemEval_M | not run | longer-horizon / larger workload extension |
| LongMemEval upstream model-judged QA | not run | answer-generation + memory use |
| AgentMemBench / MemDialogue v2 operational | complete | retrieval, currentness/conflict, isolation, deletion, concurrency, scale |
| AgentMemBench upstream LLM-judged retrieval | not run | upstream judged retrieval protocol |
| AgentMemBench M6 portability | not run | model portability |

This table is registry truth, not a statement that no other internal benchmark harness exists.

## 9. Current registered-profile coverage matrix

This matrix intentionally reflects the **registered external profiles**, not every repository-local conformance harness.

Legend: `● direct`, `◐ partial`, `△ indirect`, `○ not covered`, `B blocked`.

| Capability | SWE ContextBench Lite | LongMemEval_S | AgentMemBench/MemDialogue |
| --- | :---: | :---: | :---: |
| general retrieval | B | ● | ● |
| ranking quality | B | ● | ● |
| multi-session memory | ○ | ● | ◐ |
| multi-hop/relational recall | ◐ | ◐ | ○ |
| current-state / knowledge update | ○ | ● | ● |
| as-of historical recall | ○ | ◐ | ○ |
| explicit validity intervals | ○ | ○ | ○ |
| prospective memory | ○ | ○ | ○ |
| correction semantics | ○ | △ | ◐ |
| independent-write conflict | ○ | ◐ | ● |
| deletion | ○ | ○ | ● |
| tenant/scope isolation | ◐ | △ | ● |
| authority/governance laundering | ○ | ○ | ○ |
| poisoning resistance | ○ | ○ | ○ |
| audit quality/confidentiality | ○ | ○ | ◐ |
| concurrency correctness | ○ | ○ | ● |
| restart/recovery | ○ | ○ | ○ |
| tamper detection | ○ | ○ | ○ |
| scaling | ○ | ◐ | ● |
| memory-to-action utility | ○ | ○ | ○ |
| multimodal memory | ○ | ○ | ○ |
| metabolism/decay | ○ | ○ | ○ |
| consolidation/pruning | ○ | ○ | ○ |
| continual learning/transfer | ○ | ○ | ◐ |
| evaluator integrity | ◐ | ● | ● |
| reproducibility identity | ● | ● | ● |

This matrix is deliberately conservative. A capability is not marked direct merely because it can influence the final score.

## 10. Candidate benchmark landscape

The following candidates have been identified as potentially useful distinct pressure sources. They remain **unqualified in this Atlas until an exact protocol/revision/license/corpus/evaluator review is recorded**.

| Candidate | Tentative distinct pressure | Atlas state |
| --- | --- | --- |
| LoCoMo | long conversational histories, multi-hop/temporal QA, summarization | `?` qualification required |
| MemoryAgentBench | retrieval, test-time learning, long-range understanding, conflict resolution | `?` |
| MemBench | factual/reflective memory, participation/observation, efficiency/capacity | `?` |
| Memora / FAMA | obsolete-memory pressure, reasoning/recommendation over evolving memory | `?` |
| Ground Truth First | validity intervals, as-of questions, provenance/source channels, temporal changes | `?` active/high priority |
| RHELM | evolving profiles, multi-source memory, misleading/current-state queries | `?` active/high priority |
| Mem2ActBench | whether remembered information improves tool/action behavior | `?` |
| PerMemBench | personalized memory selection/storage policy over long histories | `?` |
| AgentMemoryBench | continual online learning, transfer, forgetting/interference | `?` |
| AMA-Bench | memory from long agent trajectories/task histories | `?` |
| Mem-Gallery | multimodal conversational long-term memory | `?` |

No claim in this table should be converted into a registered profile until qualification completes.

## 11. Preliminary portfolio gaps

Even before the candidate landscape is fully qualified, the registered-profile matrix exposes clear gaps.

### 11.1 Governance as a first-class memory property

External benchmarks currently provide little direct pressure on:

- authority laundering;
- purpose limitation;
- source-rights/provenance trust;
- consent/sensitivity restrictions;
- mutation authorization;
- audit confidentiality;
- deleted-memory resurrection;
- history visibility under current-vs-historical permissions;
- isolation side channels.

This is the highest-priority candidate for a Gauntlet-native neutral suite if no viable external benchmark covers it adequately.

### 11.2 Memory metabolism

Current external profiles do not directly test trajectories involving:

```text
weak observation
  -> reinforcement
  -> saturation
  -> time decay
  -> contradiction pressure
  -> consolidation
  -> pruning
  -> later reactivation
```

Internal Agent Memory metabolism benchmarks exist, but they are conformance/architecture evidence, not neutral external comparison.

### 11.3 Durability and integrity

External memory benchmarks rarely isolate:

- process crash/restart;
- checkpoint durability;
- tamper detection;
- journal/state integrity;
- deterministic recovery;
- recovery under evolving configuration.

This is a memory-system property, not merely a database implementation concern.

### 11.4 Prospective memory

Remembering an intended future action or condition-triggered commitment is materially different from retrieving past evidence and appears underserved.

### 11.5 Historical truth versus corrected falsehood

The portfolio needs to distinguish:

```text
historically valid, later superseded
!=
incorrect claim, later corrected
```

Both are old state. Only one should be presented as historically true.

### 11.6 Causal and relational durability

Multi-hop QA partially pressures relationships, but durable causal memory and relation maintenance through correction/currentness are weakly isolated.

### 11.7 Memory-to-action utility

Retrieval quality is not equivalent to downstream usefulness.

The portfolio needs evidence that memory improves decisions/actions without unauthorized or stale memory causing harmful behavior.

### 11.8 Multimodal memory

The current Agent Memory benchmark portfolio is predominantly text-oriented.

### 11.9 Shared/multi-agent governance

Few benchmarks pressure shared memory where different agents have different rights, purposes, sources, or trust levels.

## 12. Rule for creating a Gauntlet-native benchmark

Agent Memory should author a neutral benchmark only when all of the following are true.

1. The capability is material to general-purpose agent memory, not merely an Agent Memory implementation feature.
2. The Atlas shows it is not directly and adequately covered by viable qualified external benchmarks.
3. Candidate external benchmarks have been reviewed for extension/adaptation before creating a new suite.
4. The task can be expressed without requiring Agent Memory-specific APIs or doctrine.
5. At least one plausible competing architecture could perform well using a different implementation strategy.
6. The protocol can be frozen before optimizing Agent Memory against it.
7. Baselines and failure controls can be defined.
8. Metrics can distinguish unsupported, failed, blocked, and not-applicable behavior.
9. The benchmark can produce evidence that makes Agent Memory look bad.
10. The benchmark's provenance will remain `gauntlet_native_gap`, never independent external evidence.

If condition 9 is false, the proposed benchmark is marketing, not evaluation.

## 13. Gauntlet-native benchmark development discipline

A native gap suite should follow this sequence.

```text
Atlas gap recorded
   -> neutral problem statement
   -> external review of nearby benchmarks
   -> benchmark design
   -> freeze ontology / generator / seeds / metrics
   -> implement trivial + adversarial baselines
   -> validate evaluator integrity
   -> only then run Agent Memory
   -> invite/implement external system adapters
   -> publish failures and limitations
```

The benchmark should not be tuned after seeing Agent Memory's failures unless a version bump creates a new frozen benchmark generation and the change is justified independently.

## 14. Suggested Gauntlet suite groupings

Suites are orchestration views, not aggregate scores.

### `core-retrieval`

Potentially combines:

- LongMemEval bounded retrieval;
- qualified conversational/long-horizon benchmark;
- exact/semantic/relational retrieval cases;
- abstention where supported.

### `temporal`

Potentially combines:

- knowledge update/currentness;
- validity interval/as-of benchmark;
- historical vs corrected-state cases;
- prospective memory when qualified.

### `governance`

Own Gauntlet governance specification plus any qualified external provenance/security benchmark.

### `operations`

- concurrency;
- scale;
- restart/recovery;
- tamper/integrity;
- storage/latency/cost where comparable.

### `lifecycle`

- correction;
- conflict;
- deletion;
- forgetting;
- consolidation/metabolism if neutral coverage exists.

### `agent-utility`

- memory-to-action;
- planning/recommendation;
- downstream task success.

### `multimodal`

Only after a qualified multimodal memory benchmark exists.

### `comprehensive`

Runs all eligible profiles and reports a coverage map.

It must not convert the portfolio into one scalar.

## 15. Coverage reporting for a system

A system's Gauntlet report should distinguish **system capability coverage** from **benchmark score**.

Example:

```text
System: example-memory 2.4.1

Eligible suites:
  core-retrieval       4/4 profiles eligible
  temporal             2/4 eligible
  governance           1/5 eligible
  operations           2/3 eligible

Capability posture:
  retrieval            measured
  currentness          measured
  historical recall    partial
  deletion             unsupported
  tenant isolation     unsupported
  recovery             measured
  multimodal           not measured

Evidence provenance:
  independent external       3 runs
  adapted external           3 profiles
  Gauntlet-native gap        2 runs
  conformance                0
```

A system should be allowed to be excellent within a narrower declared scope.

## 16. Atlas maintenance rules

1. Every registered benchmark profile should have an Atlas row/entry.
2. Every qualification/rejection should record the exact source revision reviewed.
3. Coverage cells should be conservative and evidence-linked.
4. A benchmark version may change coverage; coverage belongs to a profile/revision, not merely a brand name.
5. Benchmark-native metrics remain native even when an Atlas capability maps to them.
6. The Atlas should be updated when a benchmark exposes a product defect or a previously unrecognized dimension.
7. New capability columns require a short definition and rationale.
8. No capability should be added merely to make one system look differentiated.
9. `○ not covered` is useful information, not a criticism of the benchmark.
10. The Atlas itself should be versioned when the capability taxonomy changes materially.

## 17. Near-term qualification priority

Given the currently observed gaps, the next qualification sequence should favor **distinct pressure**, not benchmark popularity.

Proposed order:

1. a validity-interval/as-of temporal benchmark (Ground Truth First candidate first);
2. a dynamic multi-source/evolving-profile benchmark (RHELM candidate);
3. a memory-to-action benchmark;
4. a continual-learning/interference benchmark;
5. a multimodal memory benchmark;
6. other conversational benchmarks only when they add measurable pressure beyond LongMemEval/LoCoMo-like coverage.

This ordering is provisional and should change if qualification reveals poor reproducibility, licensing, evaluator integrity, or task fit.

## 18. Relationship to the existing common evidence dimensions

The current normalized vocabulary includes:

```text
retrieval
currentness
reasoning
governance
efficiency
evaluator_integrity
reproducibility
```

The Atlas is intentionally more detailed.

Example:

```text
Atlas:
  tenant isolation
  scope isolation
  purpose limitation
  authority laundering
  deletion resurrection

Normalized common dimension:
  governance
```

The Atlas answers **what was pressured**.

The common evidence contract answers **how eligible observations are represented and compared**.

Neither requires an overall score.

## 19. Governing principle

> **Comprehensiveness is coverage across meaningful memory capabilities, not the number of benchmark names in the repository.**
