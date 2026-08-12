# P7 Governed Interchange Evidence

## Purpose

Exercise the Agent Memory Profile 6 seam without defining a transport standard or making any upstream submission.

The local evidence now asks two questions:

1. can one governed system export memory to another without losing ownership, provenance, lifecycle, sensitivity, scope provenance, or receiver-local authorization;
2. can later source correction, supersession, revocation, or deletion obligations remain visible without turning the sender into a remote mutation authority over the receiver?

External projects are not modified, asked to adopt the contract, or treated as implementation dependencies.

## V1: governed export and import

The reference path under `reference/agentmem_ref/interchange.py` enforces:

1. sender export requires a schema-valid memory and a **committed governed boundary-crossing receipt**;
2. the crossing receipt must bind the exported memory id;
3. cross-system export requires explicit ownership and source isolation-domain bindings;
4. sender-side authorization travels with the bundle as evidence, not as receiver permission;
5. the receiver evaluates a local `scope_expansion` proposal through its own PAMA path;
6. an ownership conflict fails closed before admission;
7. successful import preserves stable identity, lifecycle state, provenance, sensitivity, and owner;
8. successful import binds the receiving isolation domain while retaining source-domain provenance;
9. the imported memory records the **receiver's** authority envelope, not the sender's authority refs.

The companion fixture `fixtures/cross-system-authority-conflict.json` makes the missing authority-conflict case from `docs/35-interoperability-profiles.md` permanent in the conformance corpus.

## V2: lifecycle-obligation continuity

A successful import now also emits a local `InterchangeLink` binding the imported memory to:

- source system;
- receiver system;
- source crossing receipt;
- source isolation domains;
- receiver isolation domain.

A later `SourceLifecycleNotice` may report correction, supersession, revocation, or deletion. The notice is **evidence of a source-side lifecycle change**, not permission to mutate receiver state.

The receiver therefore:

1. verifies memory identity and the linked source system;
2. requires source evidence references;
3. maps deletion to a local `permanent_deletion` consequence and other lifecycle changes to local `correction`;
4. evaluates that consequence under the receiver's current PAMA policy and authority;
5. leaves local memory untouched while review or verification is still required;
6. only after receiver-local authorization schedules a local correction or deletion workflow.

Even an authorized notice handler does not directly purge or rewrite the local memory object in this slice. It schedules the local consequence so the existing correction/deletion machinery remains authoritative for actual mutation and forgetting completeness.

## Evidence boundary

This demonstrates local executable interoperability behavior. It does **not** claim:

- a universal interchange wire format;
- Profile 6 conformance for the entire reference adapter;
- automatic trust of imported memory;
- transfer of ownership, certification, mutation, correction, or deletion authority;
- proof that remote deletion automatically satisfies local forgetting completeness;
- production transport security;
- upstream acceptance by Agent Manifest, TRACE/cMCP, Mem0, Graphiti, AgenTrust, or any other project.

The sender's `allow` authorizes the sender's own export. A later sender notice makes an obligation visible. The receiver still owns every local admission and consequence decision.

## Validation

`reference/tests/test_interchange.py` covers:

- refusal to export without a committed sender crossing;
- refusal to inherit sender authority at the receiver;
- fail-closed ownership conflict;
- successful locally authorized import with semantic preservation and receiving-domain rebinding;
- deletion notice held pending local governance;
- locally authorized deletion notice scheduling a local deletion workflow without silently deleting state;
- correction notice requiring receiver-local correction authority;
- rejection of lifecycle notices from an unlinked source system.

Repository CI runs these tests through the existing reference governed-adapter validation path together with fixture/schema/doctrine validation.

## Remaining P7 work

The strongest remaining Profile 6 gap is end-to-end **actual correction/deletion propagation evidence** across two concrete local stores, including receipt linkage and deletion-residue accounting on the receiving side. That work must reuse the existing canonical correction and deletion-completeness machinery rather than creating a special interoperability shortcut.
