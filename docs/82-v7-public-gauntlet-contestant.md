# #644 v7 public Gauntlet contestant: staged, not qualified

**Owning issue:** #644. **Status:** UNQUALIFIED TRANSITION PROBE.

The v7 contestant reuses the public-facade-only v6 protocol and dispatch implementation
on a distinct namespace; it does not copy a v6 baseline or claim that v7 is published.

- Manifest: `examples/gauntlet/agent-memory-runtime-baseline-v7.json`
- Stdio adapter: `examples/gauntlet/agent_memory_runtime_baseline_v7_stdio.py`
- Tested v7 runtime implementation: `16a248b1e28f455fbf19217114175f0c20df2a01`
- Adapter Git blob is pinned independently in the manifest.
- The manifest's `system.revision` names the tested runtime implementation, **not**
  the manifest/adapter preparation commits and not a published baseline.

The `configuration_digest` is SHA-256 over canonical JSON (sort keys,
compact separators) of these exact string fields: `adapter_blob`, `runtime_commit`,
`tenant`, `scope`, `public_contract`, and `transport`. The values are the
pinned adapter Git blob, the above runtime commit, `tenant:gauntlet-runtime-baseline-v7`,
`scope:gauntlet-runtime-baseline-v7`, `1.6.0`, and `stdio`. This digest is
a reproducible **configuration identifier**, not signature or authorization.

## Candidate-only validation commands

From repository root, with an environment pinned to the tested runtime and the
public `agentmem_ref` module from this checkout:

```shell
agent-memory gauntlet validate-adapter examples/gauntlet/agent-memory-runtime-baseline-v7.json
agent-memory gauntlet run \
  --system examples/gauntlet/agent-memory-runtime-baseline-v7.json \
  --profile gauntlet-orchestration-retrieval-probe-v1 \
  --allow-external-process --allow-destructive-reset
```

**Do not** call the result v7 qualification without proving loaded module and runtime
source identity; the stdio adapter's revision constant is a declaration, not an
independent source attestation. A v7 gauntlet run needs an independently recorded
result, exact execution identity, import-provenance checks, and the appropriate
workflow/release gate before accepted publication evidence exists.

The v6 baseline register must remain unchanged. Replays 104/104 are locally PASS
but need independent acceptance; workflow-imported AMB/LongMemEval evidence, F6
policy, and F7/F12 decisions remain open. A passing 3/3 probe proves only the
narrow public-gauntlet sample, not general retrieval quality or adaptive stopping.
