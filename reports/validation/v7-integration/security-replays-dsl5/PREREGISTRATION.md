# Successor security replays on the supported scope-distinct store (DSL/5): preregistration

Frozen before first execution. First authored at `4d807b89`; revised after the independent pre-execution review (`PREEXECUTION_REVIEW.md`) and re-authored at base `9eb72391`, still unexecuted.

| Successor | Supersedes | Cases | Changed or new |
|---|---|---|---|
| `cross-scope-write-authority-denial-v4` | `-v3` (DSL/2) | 17 | 14 (W1, W2 (disposition), W3, W4, W4b, W6, W7, W7c, W8b, W8; new W1h, W2h, W7c-h, W8-h) |
| `deleted-lineage-generations-and-restart-v4` | `-v3` (DSL/2) | 11 | 3 (L3, L4; new L3-h) |
| `public-tombstone-redaction-and-observer-separation-v4` | `-v3` (DSL/2) | 8 | 3 (R3 (disposition), R6b, R5) |
| `evidence-reference-authorization-v2` | `-v1` (DSL/3) | 16 | 6 (E6, E6a, E6r (dispositions); new E6-h, E6a-h, E6r-h) |

- **Runner:** `reference/run_786_security_replays_dsl5.py`. It subclasses the byte-frozen DSL/1–3 runners, which are not
  edited. Every handle is opened through the public `AgentMemory.open(..., store_profile="scope_distinct_v1")`.
  Host-level steps and canonical probes name the acting handle's canonical memory, or another project's memory when
  `ref_scope` says so. Canonical keys are mapped back to public keys before comparison: a key of another project
  reads as `<project>key`, so a leak remains detectable.
- **Author:** `reference/fixtures/786-security-replays/author_fixtures_dsl5.py`. It records every change with its
  clause and reason. Rules M1 (version tokens on own-namespace commits), R1 (record what no clause decides) and H1
  (canonical gate exercised at the host layer) are stated in its docstring.
- **Facade W4.** Any override that changes the handle's identity is expected to raise `ValueError`. The 1.8.0
  malformed-scope message is expected unchanged and checked first.
- **Pre-execution review.** A separate reviewer compares every expectation with its cited clause before first
  execution: `PREEXECUTION_REVIEW.md`. Findings are applied before execution, and only as a recorded change to the
  author script.
- **After first execution:** no fixture edit. A wrong expectation is a finding and needs a superseding generation.

`scope-safe-graph-discovery-v2` (DSL/4) is single-project and passes unchanged on the default profile. It is
re-recorded with its own frozen runner, not superseded.
