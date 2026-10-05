# Contributor Architecture: Runtime, Memory Evaluation, and the Gauntlet

Status: canonical contributor contract (v1) under #652; describes the implementation that exists on `main`  
Authority effect: none

Read this page first if you are bringing **a memory system** or **a benchmark** to this repository. It explains the three subsystems, the two contributor paths, exactly which files and commands each path touches, and how every evidence state propagates. Everything below is backed by code, schemas, tests, and CI on the current tree; where something is deliberately not implemented, the page says so.

```text
Agent Memory Runtime
    |
    | public memory behavior (AgentMemory facade)
    v
Memory Evaluation
    |
    | measurement / evidence contracts
    v
Agent Memory Gauntlet
```

## 1. Three subsystems, three ownerships

| Subsystem | Owns | Must not | Code |
| --- | --- | --- | --- |
| **Runtime** | remember, recall, correct, forget, history, posture, persistence, governed admission, lifecycle, currentness, memory semantics | depend on benchmark datasets, scores, adapters, Gauntlet outcomes, or evaluator policy | `reference/agentmem_ref/` except `evaluation/` |
| **Memory Evaluation** | benchmark identity, input identity, common result/evidence envelope, benchmark-native result preservation, validation, fail-closed comparison, benchmark integration descriptors and registry, evaluator-integrity evidence, reproducibility/provenance | runtime authority, recall admission, mutation permission, a universal memory score | `reference/agentmem_ref/evaluation/contract.py`, `benchmark_integration.py`, `registry.py`, `normalize.py`, `cli.py` |
| **Gauntlet** | system adapter contract, capability negotiation, external-process/in-process transport, qualification profiles, destructive-operation consent, orchestration, failure attribution, qualification evidence | benchmark-native semantics, runtime truth, a universal benchmark protocol | `reference/agentmem_ref/evaluation/gauntlet_*.py` |

The runtime never imports the evaluation package. The installed `agent-memory` console routes `benchmark ...` and `gauntlet ...` to the evaluation package and everything else to the runtime CLI; `test_runtime_import_remains_independent_from_evaluation` and the package-layout tests enforce the direction.

Invariants that every contract on this page preserves:

```text
benchmark score != truth / authority / recall admission / mutation permission
candidate retrieval != governed recall admission
ranking != truth
adapter translation != native capability      derived != native      mapped != native
unsupported != failed       unsupported != zero
blocked != failed           blocked != zero          not_applicable != zero
published vendor result != same-harness result
benchmark registry presence != benchmark qualification
evaluator-integrity pass != system efficacy
proposal != application     interpretation != authority     classifier confidence != permission
```

There is no universal memory-health scalar anywhere in the repository, and no contract on this page accepts one.

## 2. Which path are you on?

```text
I have a MEMORY SYSTEM and want it measured
    -> section 3: system-author path
       (adapter manifest -> operation envelopes -> negotiation -> profile -> evidence)

I have a BENCHMARK and want it integrated without distorting its protocol
    -> section 4: benchmark-author path
       (descriptor -> native runner -> native evidence -> optional normalization
        -> evaluator-integrity controls -> optional Gauntlet profile binding)
```

The two paths are different and stay different. They meet at exactly one place: a benchmark integration whose descriptor declares `gauntlet.relationship = bound_profile` can be run by any system that implements the Gauntlet adapter contract.

## 3. System-author path

```text
external memory system
  -> system adapter manifest            schemas/gauntlet-system-adapter.schema.json
  -> operation envelopes                schemas/gauntlet-operation-envelope.schema.json
  -> capability negotiation             agentmem_ref.evaluation.gauntlet_contract
  -> applicable Gauntlet profile        agent-memory gauntlet list | inspect
  -> benchmark/profile-native evidence  <run>/native-results.json
  -> normalized evidence                <run>/normalized-run.json  (memory-benchmark-run schema)
  -> coverage / unsupported / blocked   <run>/qualification.json
```

The canonical executable proof is the external stdio contestant from #637: `examples/gauntlet/minimal_stdio_adapter.py` with `examples/gauntlet/minimal-stdio-adapter.json`. It imports nothing from this repository. Follow [`GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md) step by step; the CI workflow `gauntlet-external-contestant-dogfood.yml` executes those exact commands on every change.

Commands:

```bash
agent-memory gauntlet list
agent-memory gauntlet inspect <profile-id>
agent-memory gauntlet validate-adapter ./my-adapter.json      # never executes the adapter
agent-memory gauntlet run --system ./my-adapter.json --profile <profile-id> \
    --allow-external-process [--allow-destructive-reset | --allow-destructive-operations] \
    --output-dir ./gauntlet-runs
```

What a manifest declares, and what each declaration is: see [`GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md) (support classes, operation vocabulary, isolation, fairness) and [`GAUNTLET_ORCHESTRATION.md`](GAUNTLET_ORCHESTRATION.md) (transports, consent, evidence layout, failure attribution).

Profiles a system can enter today (`agent-memory gauntlet list`):

| Profile | Kind | Bound benchmark integration | What it pressures |
| --- | --- | --- | --- |
| `gauntlet-orchestration-retrieval-probe-v1` | `baseline_or_probe` | none | transport, negotiation, evidence plumbing |
| `golden-keyed-retrieval-v1` | `baseline_or_probe` | `golden-keyed-retrieval-v1` | the benchmark-author contract end to end |
| `governance-isolation-deletion-alpha-v1` | `gauntlet_native_gap` | none | tenant/scope isolation, deletion, authority laundering |
| `durability-recovery-alpha-v1` | `gauntlet_native_gap` | none | reopen recovery, durable deletion, deterministic recovery, scope isolation |

Every profile carries `benchmark_integration` explicitly: `None` for a Gauntlet-native suite or probe, or the id of a committed descriptor. The registry test refuses a profile that presents itself as external evidence without a bound descriptor.

## 4. Benchmark-author path

```text
benchmark source
  -> source/license qualification        descriptor.source_rights
  -> exact revision                      descriptor.benchmark.source_revision (+ rule)
  -> exact input/dataset identity        descriptor.input_contract
  -> benchmark-native runner/adapter     descriptor.native_protocol.runner
  -> native metric/artifact semantics    descriptor.native_protocol
  -> optional mappings into dimensions   descriptor.normalization.mappings
  -> evaluator-integrity pressure        descriptor.evaluator_integrity
  -> optional Gauntlet profile binding   descriptor.gauntlet
```

### 4.1 The descriptor

A benchmark integration is described by one JSON file validated against `schemas/memory-benchmark-integration.schema.json` (`contract_family: agent-memory-benchmark-integration`, `contract_version: 1.0.0`). It describes an **integration**, not a result. Results use the separate `schemas/memory-benchmark-run.schema.json`.

Committed descriptors live in `reference/agentmem_ref/evaluation/integrations/` and are the only source of the benchmark registry; `agent-memory benchmark list` is a projection of them, so an identity recorded in a descriptor is never restated by hand in Python.

The descriptor is intentionally not a universal execution protocol. `native_protocol.runner.kind` is one of:

- `repository_script`: a benchmark-native script with its own arguments (LongMemEval, AgentMemBench, SWE-ContextBench);
- `module_callable`: a Python entry point;
- `gauntlet_profile_runner`: a `runner(session, run_id=, namespace=)` callable that speaks only operation envelopes and can therefore be executed against any Gauntlet adapter.

A truthful descriptor pointing at a heterogeneous runner is the contract. LongMemEval is not AgentMemBench; SWE-ContextBench is not a durability suite; a model-judged QA lane is not retrieval recall. The descriptor records those differences instead of erasing them.

### 4.2 What validation enforces (without executing anything)

`agent-memory benchmark validate-integration <descriptor>` and `validate_integration()` enforce, beyond the schema:

- an explicit contract-version compatibility policy (major must match, minor must not exceed the supported minor; anything else is refused);
- `external_independent` / `external_adapted` benchmarks must name an upstream repository and URL, and `baseline_or_probe` benchmarks may not claim one;
- `source_revision = "unbound"` only with `source_revision_rule = manifest_bound`;
- committed inputs (`input_may_be_absent_before_execution = false`) must carry `known_input_sha256` and `committed_input_path`;
- placeholder digests (a repeated character, the digest of zero bytes, non-hex) are refused everywhere a digest may appear;
- a judge model that is required contradicts `credential_free` and must record its identity;
- every common dimension is either mapped (with the native evidence path that supplies it) or listed under `unmapped_dimensions` with a reason; mappings without a normalizer are refused as invented evidence;
- executed evidence rows (`complete` / `partial`) must carry an exact `input_sha256`, `system_revision`, `report`, and a `report_binding` that says where in the report those identities live; `blocked` rows must carry a blocker; `not_run` rows may carry no report or digest;
- `admission_state` must agree with the evidence history;
- a `bound_profile` relationship requires a profile id, a `gauntlet_profile_runner`, and the operation-envelope invocation surface.

Validation imports neither the runner, nor the normalizer, nor the integrity controls (`test_validation_does_not_execute_benchmark_code`). A malformed descriptor is refused with exit status 2 and a JSON refusal that still carries `authority_effect: none`.

### 4.3 Commands

```bash
agent-memory benchmark list                                     # descriptor projections
agent-memory benchmark inspect <integration-id>                 # one committed descriptor + resolved Gauntlet relationship + evidence binding
agent-memory benchmark validate-integration ./my-benchmark.json # fail-closed, no execution
agent-memory benchmark validate ./result.json                   # memory-benchmark-run manifest
agent-memory benchmark compare ./a.json ./b.json                # fail-closed comparison, no overall score
```

All commands accept `--json`; JSON reports are keyed for automation and every one carries `authority_effect: none` and, for integrations, `executed: false`.

### 4.4 The golden example

`golden-keyed-retrieval-v1` is the executable proof of the whole benchmark-author path, small enough for ordinary CI:

| Requirement | Where it is satisfied |
| --- | --- |
| exact integration identity | `integrations/golden-keyed-retrieval-v1.json`; the runner reads identity from the descriptor and restates nothing |
| exact frozen input identity | `reference/fixtures/benchmarks/golden-keyed-retrieval/v1.json`, digest-bound; a mismatch is attributed to `benchmark_input` before any operation |
| neutral system invocation | only `describe` / `reset` / `remember` / `recall` operation envelopes through an `AdapterSession` |
| native results retained | `native-results.json`: rows, recalled ids, full transcript; the normalized run embeds them unchanged |
| common evidence normalization | `mapped_metric_observations()` builds metrics only from declared `normalization.mappings`; an absent native path yields `not_measured`, never a value |
| reproducible artifacts | the standard Gauntlet run directory |
| evaluator-integrity control | `reference/run_golden_benchmark_integrity.py`: `gold_omission`, `rank_inversion`, `identity_corruption` must be detected and `unrelated_record_omission` must not be |
| failure attribution | Gauntlet failure sources; a contestant with nothing to lose (`no-memory`) does **not** qualify the evaluator |
| no Agent Memory shortcuts | the module never imports the runtime; it runs the lexical baseline, the no-memory baseline, and the external stdio contestant identically |

Its provenance class is `baseline_or_probe`, its committed evidence is the deterministic integrity-controls report, and the scorecard portfolio deliberately excludes it. It demonstrates the contract; it is not validation of any memory system.

### 4.5 Adding your benchmark

1. Write the descriptor (copy the golden one for a Gauntlet-bound runner, or the LongMemEval one for a benchmark-native script).
2. `agent-memory benchmark validate-integration ./my-benchmark.json`.
3. Implement the runner the descriptor names. Keep the benchmark's own metrics, exclusions, denominators, and failure semantics. Hash the raw input bytes you actually read and record the selection identity.
4. If you normalize, implement the normalizer the descriptor names and map only observations whose meaning is stable within one frozen input and task profile. Keep everything native under `native_results`.
5. Add the evaluator-integrity controls the descriptor declares and make sure at least one of them can fail.
6. Commit the descriptor under `reference/agentmem_ref/evaluation/integrations/`; the registry tests will check its evidence bindings and its Gauntlet relationship.
7. Record executed evidence as `evidence_history` rows bound to committed reports by exact digest and revision.

## 5. Evidence and provenance classes

Every benchmark integration declares one provenance class, and every Gauntlet profile declares the same vocabulary as its `kind`:

| Class | Meaning | Independent evidence? |
| --- | --- | --- |
| `external_independent` | designed and published independently; executed with its own harness | yes, when protocol fidelity is preserved |
| `external_adapted` | independent benchmark executed through a repository runner/adapter | yes, with the adaptation visible |
| `gauntlet_native_gap` | system-neutral suite authored here because the Coverage Atlas showed a gap | no; coverage/falsification evidence |
| `agent_memory_conformance` | fixture for an Agent Memory contract or invariant | no |
| `baseline_or_probe` | deterministic baseline, probe, or contributor demonstration | no |

Registration never changes class. `check_profile_binding()` refuses a profile whose `kind` differs from the bound descriptor's `provenance_class` in either direction, the orchestrator refuses a runner that declares a different `profile_kind` than the registered profile, and a profile without a bound descriptor may only be `baseline_or_probe`, `gauntlet_native_gap`, or `agent_memory_conformance`. Published vendor numbers are `published_reference` on the dashboard and never enter a same-harness row.

## 6. State decision tree

Use this tree when deciding how an observation is recorded. It applies at capability negotiation, at execution, and in the normalized evidence.

```text
Was the capability/operation claimed by the system at all?
├─ no  -> unsupported          (negotiation outcome / case outcome; never a number)
└─ yes
   Could the harness exercise it in this environment?
   ├─ no  -> blocked            (missing input, consent, credential, transport, process; never a number)
   └─ yes
      Is the dimension/metric meaningful for this benchmark or system?
      ├─ no  -> not_applicable   (e.g. governance for a no-memory arm; never a number)
      └─ yes
         Was it exercised?
         ├─ no  -> not_measured  (declared with a reason)
         └─ yes
            Did the operation itself complete validly?
            ├─ no  -> failed with attribution
            │         (benchmark_input | benchmark_adapter | orchestrator |
            │          system_adapter | system_under_test | expected_refusal)
            └─ yes
               Were all required measurements obtained?
               ├─ no  -> partial     (measured metrics plus explicit misses)
               └─ yes -> measured    (a value; zero is a real zero, e.g. no-memory exact_top1 = 0.0)

Which support class carried the capability?
├─ native   -> the system implements it
├─ mapped   -> bounded interface translation to an equivalent native capability
└─ derived  -> adapter/composition contributed materially; evidence of the composition, not the system
```

`measured zero` is a value with a denominator and population. `unsupported`, `blocked`, and `not_applicable` carry no value, so they can never be averaged into one. A behavioral `fail` with `sufficient` evidence (the durability lossy-recovery control) is a measured finding about the system; an `unsupported` case with `sufficient` evidence is a statement about scope.

## 7. Trust boundaries

- **External processes.** A `stdio` manifest contains an executable startup command. `validate-adapter` never runs it; `run` requires `--allow-external-process`. `in_process` adapters are restricted to manifests marked `metadata.trusted_fixture = true` in this repository.
- **Destructive operations.** A profile declares which operations are destructive and which claimed capability activates them. A non-fixture adapter must declare `benchmark_isolation.strategy = disposable_instance`, and that declaration is evidence, not consent: `--allow-destructive-reset` covers a reset-only profile; anything that may also `forget` needs `--allow-destructive-operations`. Never point a destructive profile at real state.
- **Benchmark data is data.** Gold labels, question ids, and evaluator state never cross into system inputs unless the benchmark protocol defines them as inputs. Dataset text is never an instruction to the host.
- **Validation is inert.** Neither `benchmark validate-integration` nor `gauntlet validate-adapter` imports or executes anything a file names.

## 8. Runtime Baseline v1 source equivalence

Runtime Baseline v1 is frozen at a specific revision. `reports/runtime/baseline-v1-source-boundary.json` protects `pyproject.toml` and `reference/agentmem_ref/**` by default and excludes exactly one subtree, `reference/agentmem_ref/evaluation/**`, as non-runtime. New or unclassified package surfaces are runtime-bearing until a reviewed boundary revision says otherwise.

Consequences for contributors:

- evaluation-only work (descriptors, runners, normalizers, Gauntlet profiles, tests, docs) must leave `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` green;
- a benchmark need is never permission to change runtime behavior; if a runtime capability is genuinely missing, open a runtime issue rather than emulating the capability in an adapter;
- packaging metadata inside `pyproject.toml` is protected; descriptors are packaged through `MANIFEST.in`, which the boundary does not protect, and the contributor-contract workflow verifies that the built wheel carries them.

## 9. When does a benchmark get a Gauntlet profile?

`descriptor.gauntlet.relationship` is one of:

- `not_applicable`: the benchmark should remain benchmark-specific. Typical reasons: it binds Agent Memory internal runtime classes, its protocol needs more than the operation vocabulary, or its external evidence is blocked (SWE-ContextBench today).
- `eligible`: the protocol is expressible through operation envelopes, but no system-neutral runner exists yet (LongMemEval and AgentMemBench today; the same-harness comparator work under #640 is the natural trigger).
- `bound_profile`: a `gauntlet_profile_runner` exists and a Gauntlet profile of the same provenance class binds it back (the golden integration today).

A profile is justified only when the whole protocol survives the operation vocabulary without adapter-side semantics. Otherwise the benchmark keeps its native runner and the descriptor says so.

## 10. Same-harness comparators (#640)

A future Mem0 OSS or Hindsight row is one `evidence_history` entry on the relevant integration with its own `system_id`, exact `system_revision`, `input_sha256`, committed report, and `report_binding`, produced by a runner whose descriptor declares how external systems enter (`external_system_entry`). The contract therefore already has a place for it; what it does not do is let a published number stand in for a same-harness run.

## 11. Governed correction gap (from #571)

`DUR-COR-001` remains `unsupported` because the neutral operation contract cannot express review-gated, evidence-bearing mutation without embedding one system's governance model. The benchmark integration contract does not solve that; it records heterogeneous protocols truthfully and leaves the evidence-bearing operation envelope as a separate, system-neutral design question. Nothing on this page should be read as permission to supply Agent Memory-specific governance objects from an adapter.

## 12. Where the other documents fit

| Document | Role after #652 |
| --- | --- |
| [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md) | the common result contract and its semantics |
| [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md) | the `benchmark` CLI reference |
| [`GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md) | the adapter/manifest/operation specification |
| [`GAUNTLET_ORCHESTRATION.md`](GAUNTLET_ORCHESTRATION.md) | the executable orchestration layer and consent model |
| [`GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md) | the system-author quickstart |
| [`BENCHMARK_COVERAGE_ATLAS.md`](BENCHMARK_COVERAGE_ATLAS.md) | admission states, provenance classes, coverage mapping |
| [`../BENCHMARKS.md`](../BENCHMARKS.md) | the current portfolio and accepted evidence |

Those documents defer to this page where they overlap.
