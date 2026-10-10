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

The `configuration_digest` follows the basis the v5 and v6 records state
(`qualification_evidence.public_gauntlet_baseline_qualification.configuration_digest_basis`):
SHA-256 over canonical JSON (sorted keys, compact separators) of the adapter's frozen
identity, which is `runtime_profile`, `public_contract`, `frozen_runtime_revision`,
`tenant`, `actor`, `scope` and `purpose`. It is a reproducible **configuration
identifier**, not a signature or an authorization. The adapter blob is pinned separately
in `adapter.revision`. The independent validation found that the first candidate used a
different field set, and corrected it (D1).

**Imported-runtime guard (D2).** At start-up the adapter checks two things: that the
imported `agentmem_ref` is this checkout's `reference/agentmem_ref`, and that its tracked
files equal `FROZEN_RUNTIME_REVISION`, with nothing untracked. Otherwise it refuses every
operation with `runtime_identity_unverified`, rather than producing evidence labelled
with a revision it did not run. Each response carries the computed `runtime_identity`
under `adapter_evidence`. The process under test computes this itself, so it is an
integrity check, not attestation.

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
