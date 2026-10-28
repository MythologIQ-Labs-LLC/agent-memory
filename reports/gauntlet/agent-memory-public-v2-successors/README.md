# v2 public-facade Gauntlet successors: local pre-publication evidence (#786)

`local-qualification.json` is produced by `PYTHONPATH=reference python reference/run_gauntlet_v2_successor_evidence.py` at the commit it names (`executed_at_head`). It is **local, pre-publication evidence**, not publication evidence and not a score: Runtime Baseline v7 publication (docs/67 Steps B1/B2) binds the workflow runs at the published revision, which must reproduce these outcomes.

For each successor the runner:

- validates the manifest, and checks the adapter (and stdio wrapper) revision against `git hash-object` of the source;
- checks that the manifest's runtime pin has the same protected surface as the executing head;
- checks that `supersedes` names the exact bytes of the v1 manifest it replaces;
- for the durability successor, checks that the declared `configuration_digest` equals the digest of a live `scope_distinct_v1` store's posture;
- runs the profile twice for real and requires both runs to complete with identical outcomes, recording the manifest's identity.

The v1 contestants (`fixtures/gauntlet/agent-memory-public-durability-adapter.json`, `...-governance-adapter.json`) and their historical results are untouched. Their sha256 values are recorded under `historical_v1_untouched`. They are retired only by the governed v7 publication.

| successor | profile | outcome |
|---|---|---|
| `agent-memory-public-durability-adapter-v2` (stdio) | `durability-recovery-alpha-v1` | REC, DEL, DET, ISO pass with sufficient evidence; COR and CHK unsupported |
| `agent-memory-public-governance-adapter-v2` (in process) | `governance-isolation-deletion-alpha-v1` | ISO-002 and DEL-001 pass; DEL-002 blocked; cross-tenant, authority and source cases unsupported, as in v1 |

`reference/tests/test_gauntlet_contestant_successors.py` refuses the record if a manifest changed after it was produced, or if the protected runtime moved.
