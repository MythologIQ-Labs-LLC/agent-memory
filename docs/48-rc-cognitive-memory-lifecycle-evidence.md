# RC Cognitive-Memory Lifecycle Evidence

Status: executable RC1 product-composition evidence for #479 under umbrella #410.

## Why this exists

Agent Memory's individual governance, retrieval, lifecycle, and restart mechanisms already had focused evidence. RC-6 asks a different question: does the supported developer-facing product path actually compose those mechanisms into one coherent memory lifecycle?

The scenario therefore enters through `AgentMemory.open()` and stays on that public RC surface for every product operation.

```text
open
-> remember multiple logical memories
-> generate retrieval candidates
-> governed final admission
-> attempt correction without qualified evidence
-> observe review/park outcome
-> correct with qualified evidence
-> preserve superseded history
-> close/restart
-> recover corrected current state
-> governed prune/forget
-> preserve tombstone/history while removing current influence
-> close/restart again
-> recover currentness, tombstone, history, and configuration binding
```

## Evidence artifact

Runner:

`reference/run_rc_cognitive_memory_scenario.py`

Focused tests:

`reference/tests/test_rc_cognitive_memory_scenario.py`

The runner requires an exact 40-hex Agent Memory revision and emits deterministic JSON. Its report is divided into independent surfaces:

```text
quality
  candidate/admitted sets
  route provenance
  post-correction and post-forgetting recall observations

governance
  seed mutation outcomes
  correction review and qualified commit
  prune/forget outcome
  wrong-scope refusal
  confidence non-authority comparison

runtime_recovery
  configuration digest
  SQLite durability/substrate profile
  restart recovery state
  currentness posture

history
  current fact identity
  state version
  tombstone state
  reconstructable event count/types
```

No aggregate health score is emitted.

## Product claims bounded by the scenario

A passing exact-head artifact demonstrates, for the RC local single-host profile, that:

- a developer can open Agent Memory without manually constructing internal PAMA objects;
- low-risk memory retention still returns the governed decision/receipt path;
- candidate generation remains separate from final governed admission;
- retrieval route provenance remains inspectable;
- a correction that lacks qualified evidence does not silently commit;
- the same correction can commit when existing qualification evidence satisfies the normal governance path;
- the prior value is no longer current after correction, while history remains reconstructable;
- corrected current state survives close/reopen recovery;
- governed pruning removes current influence without pretending that history never existed;
- tombstone/history state survives a second restart;
- wrong-scope relevance cannot become admitted context;
- confidence does not widen permitted mutation authority;
- the same runtime configuration digest remains bound across restarts.

## Important boundaries

This scenario is not the SWE-ContextBench external benchmark. It does not answer how Agent Memory compares with Jev or another system on an external retrieval corpus. #467 owns that evidence lane.

It also does not establish distributed SQLite behavior, production 1.0 readiness, answer-generation quality, physical deletion completion, or learned retrieval control.

Pruning is intentionally exercised as the default facade forgetting path because it is reversible and preserves history. Mandatory permanent deletion remains a separate higher-risk lifecycle obligation with its own evidence requirements.

## Run locally

```bash
PYTHONPATH=reference python reference/run_rc_cognitive_memory_scenario.py \
  --agent-memory-revision 0123456789abcdef0123456789abcdef01234567 \
  --output rc-cognitive-memory-scenario.json
```

The SQLite Production Substrate workflow executes this scenario on the exact PR head and uploads the resulting artifact beside the existing substrate qualification evidence. The scenario must pass as a whole, while its quality, governance, and recovery observations remain independently inspectable.
