# Public Gauntlet orchestration probe at this branch head

`gauntlet-orchestration-retrieval-probe-v1` run against a scratch contestant built from
`examples/gauntlet/agent_memory_runtime_baseline_v7_stdio.py` with `FROZEN_RUNTIME_REVISION`
set to `df6d9bed53c8e0199f2f53258e340561e9602886` and `PUBLIC_CONTRACT_VERSION` to `1.7.0` (adapter blob
`a1ff96c53aec75312682e20907f3a558c125178f`), and the v7 manifest re-pinned to that revision,
blob and recomputed configuration digest. The scratch files were not committed: the v7
contestant stays pinned to `16a248b` until a successor is sanctioned.

Command, from the repository root (the startup path in the manifest is root-relative; running
the CLI from `reference/` produces `adapter_eof` because the adapter process cannot start):

```
PYTHONPATH=reference python3 -m agentmem_ref.console gauntlet run \
  --system examples/gauntlet/agent-memory-runtime-candidate.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 \
  --output-dir <scratch> --allow-external-process --allow-destructive-reset --json
```

Result: status `complete`, `exact_top1` 1.0, `correct_top1` 3 of 3,
`authority_effect` none; the adapter's `runtime_identity` reported
`verified: true`, `same_checkout: true`, `matches_frozen_revision: true`. This is the publication
acceptance gate's shape for the probe, not authority and not a score.
