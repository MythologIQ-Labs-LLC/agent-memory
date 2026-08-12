# P7 Governed Interchange Evidence

## Purpose

Exercise the Agent Memory Profile 6 seam without defining a transport standard or making any upstream submission.

The question is deliberately narrow:

> Can one governed system export memory to another without losing ownership, provenance, lifecycle, sensitivity, scope provenance, or the requirement for receiver-local authorization?

This slice is local reference evidence only. External projects are not modified, asked to adopt the contract, or treated as implementation dependencies.

## Executed contract

The reference path under `reference/agentmem_ref/interchange.py` enforces:

1. sender export requires a schema-valid memory and a **committed governed boundary-crossing receipt**;
2. the crossing receipt must bind the exported memory id;
3. cross-system export requires explicit ownership and source isolation-domain bindings;
4. sender-side authorization travels with the bundle as evidence, not as receiver permission;
5. the receiver must evaluate a local `scope_expansion` proposal through its own PAMA path;
6. an ownership conflict fails closed before admission;
7. successful import preserves stable identity, lifecycle state, provenance, sensitivity, and owner;
8. successful import binds the receiving isolation domain while retaining source-domain provenance;
9. the imported memory records the **receiver's** authority envelope, not the sender's authority refs.

The companion fixture `fixtures/cross-system-authority-conflict.json` makes the missing authority-conflict case from `docs/35-interoperability-profiles.md` permanent in the conformance corpus.

## Evidence boundary

This demonstrates a local executable interoperability contract. It does **not** claim:

- a universal interchange wire format;
- Profile 6 conformance for the entire reference adapter;
- automatic trust of imported memory;
- transfer of ownership, certification, or mutation authority;
- deletion propagation to an actual remote deployment;
- production transport security;
- upstream acceptance by Agent Manifest, TRACE/cMCP, Mem0, Graphiti, AgenTrust, or any other project.

The sender's `allow` means only that the sender authorized its own export. The receiver still owns its admission and consequence decision.

## Validation

`reference/tests/test_interchange.py` covers:

- refusal to export without a committed sender crossing;
- refusal to inherit sender authority at the receiver;
- fail-closed ownership conflict;
- successful locally authorized import with semantic preservation and receiving-domain rebinding.

Repository CI runs these tests through the existing reference governed-adapter validation path together with fixture/schema/doctrine validation.

## Next P7 slice

The next meaningful P7 work is deletion/correction continuity across the exchange boundary: prove that an exported copy retains enough source identity and lifecycle linkage for a later correction, supersession, revocation, or deletion obligation to be recognized and governed by the receiver without granting the sender unilateral mutation authority over the receiver's store.
