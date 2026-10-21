# #644 v7 public Gauntlet contestant: staged, not qualified

**Owning issue:** #644. **Status:** UNQUALIFIED TRANSITION PROBE.

The v7 contestant reuses the public-facade-only v6 protocol and dispatch implementation
on a distinct namespace; it does not copy a v6 baseline or claim that v7 is published.

- Manifest: `examples/gauntlet/agent-memory-runtime-baseline-v7.json`
- Stdio adapter: `examples/gauntlet/agent_memory_runtime_baseline_v7_stdio.py`
- Current candidate pin (not yet Gauntlet-qualified): `2ad4cf23d366fc784a486b0245550230e64bfa25`, protected runtime tree `f9b5ff9e79a54ef053ce89eb975256b63e211714`, declaration blob `7de94f11d7d521f07d2fe22317662ac6f92f89fa`
- Adapter Git blob is pinned independently in the manifest. The candidate adapter declares the provisional public contract `1.8.0`; this is not a contract-acceptance decision.
- Previous unqualified candidate pin `16a248b1e28f455fbf19217114175f0c20df2a01` is superseded for this transition probe, not retroactively qualified.
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
imported `agentmem_ref` is this checkout's `reference/agentmem_ref`, and that its runtime
files equal `FROZEN_RUNTIME_REVISION`, with nothing untracked. "Runtime files" means the
Runtime Baseline source boundary, which excludes `reference/agentmem_ref/evaluation/**`;
the adapter process imports none of that directory. Lane records committed there (#770)
therefore do not trip the guard. Otherwise it refuses every
operation with `runtime_identity_unverified`, rather than producing evidence labelled
with a revision it did not run. Each response carries the computed `runtime_identity`
under `adapter_evidence`. The process under test computes this itself, so it is an
integrity check, not attestation.


**2026-10-21 pending qualification:** This candidate-only re-pin changes the adapter/manifest identity so the fail-closed runtime guard may qualify the repaired tree. Its source and configuration digest have not been independently executed in a complete checkout; the two manifest and identity test modules, `test_644_v7_gauntlet_contestant.py` and `test_644_v7_gauntlet_identity.py`, plus the CLI adapter validation and external-process 3-query probe must run locally. A public Gauntlet result is NOT supplied by this edit. The runtime source guard must not be weakened or bypassed, and no accepted v6 evidence/register bytes change.

**2026-10-21 executed (candidate only, not acceptance):** at branch head `97368d67` the two test modules (6/6), the CLI
adapter validation and the external-process three-query probe were executed in an isolated full-history checkout with
no installed `agentmem_ref`: `status complete`, `sample_count 3`, `exact_top1 1.0`, adapter `runtime_identity`
`verified: true` against `2ad4cf23` / tree `f9b5ff9e`; a seven-arm tamper and foreign-import matrix refused every
non-identical runtime (`runtime_identity_unverified`, probe `blocked`). Evidence: `reports/validation/644-v7-gauntlet-2ad4cf23/`.
This is the probe gate's shape for the contestant, not Runtime Baseline v7 acceptance, security sign-off or contract `1.8.0` acceptance.

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
