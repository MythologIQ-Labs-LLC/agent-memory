# Cumulative v6 to v8 alternative declaration (#776 / #777)

**DRAFT ONLY. DO NOT REGISTER, MERGE OR PUBLISH.**

This alternative resolves a structural problem with the chained `777-contract-1-7-v8-alternative.DRAFT.json`: v6 remains the published baseline, so the current checker expects a direct v6-to-successor declaration, not an unimplemented v7-to-v8 chain.

The schema-compatible JSON in [`reports/runtime/proposals/777-cumulative-v6-to-v8-alternative.DRAFT.json`](../reports/runtime/proposals/777-cumulative-v6-to-v8-alternative.DRAFT.json) describes the **cumulative protected source delta** of this exact branch relative to the published v6 source commit `b08cd844b319f400a1e515950efc6157d9ed106b`.

- Enumerates **exactly 10 protected paths**: the eight preserved v7 changes with the integrated #776/#777 adapter and recall-control blobs substituted, plus `api/contract.py` and `api/surface.py`.
- Every pinned blob was fetched from the current integration branch. The adapter is `6567bdd695c81a0f3f08c4b72b3ce70ce7d33263`.
- Declares only the public-contract identity delta 1.6.0 to 1.7.0; the frozen v7 declaration had no additional identity deltas.
- Omits all six updated `schemas/*.json` entries because they are **not in the protected runtime boundary**, but retains them as contract compatibility artifacts for independent review.
- Carries v7's five required replays and gauntlet requirement, adds new deletion/redaction/public-contract evidence requirements, and names **future v8 lane IDs**, which have **not** been created or executed.

This is a **mechanically constructed proposal, not an accepted baseline-equivalence PASS**. Independent reviewer must validate declaration schema, source-tree comparison, lineage/identity constraints, dependency assumptions, lane/evidence existence, and all unchanged comparator rows against the exact combined commit.

**Disqualifiers for activation:**
1. v7 is still registered as the declared successor to v6. Do not edit the active register without a sanctioned publication/succession decision.
2. Frozen v7 workflow artifacts are not evidence for a new protected source SHA; new v8 lane/replay evidence is unavailable.
3. The #777 changes are not independently executed on this new combined SHA. The previous cloud scratch trial is ancestry evidence only.
4. The separate #773/#774/#769 protected runtime experiments are not included. Future inclusion requires one re-computed cumulative tree and a fresh declaration, not manual copy/paste of old accepted blobs.

Read [integration plan](plan-776-777-integrated-public-privacy-successor.md) and #776/#777 issue threads for exact tests and threat boundaries. Run all validation **in Claude Code cloud/local**, never GitHub CI without explicit budget authorization.
