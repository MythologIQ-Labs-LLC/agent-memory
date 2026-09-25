# TRACE Source-Rights Reconciliation

Parent: #470

## Scope

This note reconciles the exact AgentTrust TRACE source used by Agent Memory's qualified external-evidence work with the upstream file-class licensing actually published at that revision.

Exact qualified source:

```text
repository: agentrust-io/trace-spec
source: 3a561d84d752794b9afa994ce16ed35c24ac0acb
package: agentrust-trace==0.10.0
```

## Exact upstream file-class rights

At the qualified source revision, the repository-level license map is intentionally mixed rather than representable by one repository-wide SPDX identifier.

| Material class | Upstream location / examples | License posture |
| --- | --- | --- |
| Normative specification material | `spec/`, normative schema `schema/trace-claim.json`, other material explicitly identified as Draft or Approved Specification | Community Specification License 1.0 |
| Source / SDK / tests / examples / workflows / reference code | `src/`, `tests/`, `examples/`, `.github/` | Apache License 2.0 unless a file states otherwise |
| Non-specification documentation | `README.md`, `CHANGELOG.md`, `docs/`, governance/process Markdown | CC BY 4.0 unless a file states otherwise |
| Historical `spec/trace-v0.1.md` | superseded normative publication | remains available under its prior CC BY 4.0 grant, with the upstream license history controlling |

Upstream also states that when a file combines specification text and source code, the specification portion remains under the Community Specification License and the source-code portion under Apache-2.0 unless the file says otherwise. If classification is disputed, the specification license controls for material that forms part of a Draft or Approved Specification.

## Agent Memory reuse posture

Agent Memory's current TRACE relationship does not require importing TRACE specification prose or making TRACE a runtime owner.

The safe current posture is:

```text
TRACE specification semantics
  -> cite / independently summarize unless a specific licensed reuse is deliberately registered

TRACE Apache-2.0 implementation material
  -> may be reused under Apache-2.0 obligations if a future bounded implementation actually needs it

TRACE non-spec documentation
  -> may be shared/adapted under CC BY 4.0 attribution obligations if a future bounded reuse actually needs it

TRACE verifier / evidence result
  -> external evidence only
  -> no Agent Memory authority
```

No direct TRACE material reuse is newly registered by this reconciliation. The current qualified Agent Memory path remains independent interoperability/evidence normalization.

## Why the old registry wording was stale

The existing source-registry entry correctly used `license_spdx: null`, but its prose described current specification material too broadly as generally Apache-2.0. That is no longer precise enough for the exact qualified source. Current normative specification material is governed by the Community Specification License 1.0, while Apache-2.0 is the implementation-code class and CC BY 4.0 is the non-spec documentation class.

The correct repository-level representation is therefore a mixed-license source record with `license_spdx: null` and explicit file-class rights, not a flattened Apache-2.0 label.

## Authority boundary

This reconciliation changes source-rights metadata only.

```text
license permission
!= evidence verification
!= semantic correctness
!= Agent Memory authority
```

TRACE remains an optional interoperability/evidence peer. PAMA, lifecycle authority, recall admission, and canonical memory ownership remain native Agent Memory responsibilities.
