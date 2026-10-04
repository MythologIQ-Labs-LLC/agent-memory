# Gauntlet External Contestant v1 Evidence

Status: immutable semantic sample for issue #637  
Evidence class: `baseline_or_probe`  
Authority effect: none

This directory freezes the first credential-free, public-instructions-only execution of the Agent Memory Gauntlet external-contestant path that also passed an independent semantic replay.

It is **not** an external memory-quality benchmark and must not be used as market-comparison evidence. The three-query retrieval probe qualifies the public adapter/orchestration path, evidence normalization, capability negotiation, consent boundaries, and reproducibility contract.

## Frozen identities

- repository source revision: `2b387a1bdbdc410196c5fa6d71406cc5303206f2`
- example system source: `git-blob:ca41e1bb3ab249340f8d03dbd1738511ee3ce44e`
- example adapter source: `git-blob:ca41e1bb3ab249340f8d03dbd1738511ee3ce44e`
- profile: `gauntlet-orchestration-retrieval-probe-v1`
- workflow run: `37211802764`
- workflow artifact: `11305974770`
- artifact digest: `sha256:82b1264401f2a42aec3b24241efcaff87875098cca32a76028a0a636bf0e02e3`
- Python: `3.12.14`

The committed `golden-evidence.json` is a semantic projection of the run rather than the raw timing-bearing artifact. It preserves the manifest, native retrieval observations, normalized non-efficiency evidence, capability negotiation, coverage, limitations, and authority posture. Execution UUIDs, wall/operation timing, timestamps, and artifact paths/hashes derived from those execution-specific values are deliberately not treated as semantic identity.

Two independent executions were required to have distinct valid run IDs while producing identical stable semantics. Future dogfood runs are checked both against one another and against this committed sample.

Raw workflow artifacts remain provenance evidence and are referenced here by exact run/artifact identifiers and digest; they are not the repository source of truth for the semantic golden package.
