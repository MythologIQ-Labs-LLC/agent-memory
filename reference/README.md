# Reference Governed Adapter

A minimal, executable demonstration that the governed path in
[`../docs/programs/runtime-evidence/README.md`](../docs/programs/runtime-evidence/README.md)
can be implemented over a temporal-graph substrate that provides no governance of its own, plus the P4.5 portable evidence, external-checkpoint correlation, and TRACE/cMCP action-evidence boundaries.

## What this is not

Read this section before citing anything in this directory.

- **Not a conformance claim.** The emitted report states conformance level 0 and says why. The doctrine fixture corpus *is* now driven through the adapter's authority enforcement, but doc 06 levels are cumulative and this adapter implements neither decay nor calibrated saturation, so levels 2 and 3 are unmet however well enforcement does. Nothing here substantiates a level, a profile, or ADR-020.
- **Not a reference implementation of Agent Memory.** It implements the narrow slices needed to exercise governance paths and portable evidence, and nothing else.
- **Not an endorsement of any substrate or trust infrastructure.** The model reproduces one mapped substrate's verified semantics so the tests have something realistic to push against. The Ed25519 profile proves an evidence boundary, not a universal PKI. Agent Manifest, TRACE, and cMCP are pinned external comparators/interoperability surfaces, not doctrine dependencies.

## What it does demonstrate

Several things, at different evidential weight.

**Against a real substrate (runtime evidence).** Seven governance paths execute against `graphiti-core` 0.29.3 backed by an embedded graph database, with no LLM, no embedder, no API key and no server. Facts are written through the substrate's no-LLM direct-write path, superseded, pruned, physically deleted, and refused across partitions, all under the authority gate.

**Against a substrate model (precondition).** Twelve further paths run against an in-memory model, covering cases the live binding does not reach: stale authorization, self-approval, undeclared derived residue, and version-drift separation.

**Against the doctrine fixture corpus.** All 26 repository fixtures are driven through the adapter's own enforcement rule, 18 of which declare an authority envelope. This matters because the corpus was authored to describe doctrine, not to satisfy this implementation, so agreement between them is evidence rather than a suite agreeing with itself. The checker is mutation-tested in `tests/test_fixture_corpus.py`: four deliberately corrupted envelopes must be detected, because a conformance check that cannot fail is decoration.

**Against the P4.5a portable-evidence contract.** A content-free projection of a canonical decision receipt is signed with Ed25519 and verified using only the configured public trust key. The verifier independently checks receipt, runtime-action, policy, authority-state, temporal, and isolation-domain bindings while preserving governance disposition, runtime execution, and lifecycle satisfaction as separate outcomes. Adversarial vectors exercise tampering, replay, stale authority, wrong domains, key rotation, revocation timing, detached receipt verification, and valid deletion with residual lifecycle state.

**Against the P4.5b Agent Manifest comparator.** CI installs `agent-manifest==0.11.0`, pinned to release commit `98cead8e8809e3302dc388ca869882d15b812b7f`, and executes its own v0.2 memory checkpoint/delta implementation. Agent Memory content-addresses the checkpoint tuple and binds it through the canonical receipt and P4.5a state references. The executed upstream log appends a real `DEL`; the resulting accepted checkpoint is exercised once with lifecycle `residual` and once with lifecycle `satisfied`, proving checkpoint integrity does not manufacture forgetting. Because a checkpoint root alone does not disclose the appended operation class, the portable correlation artifact deliberately carries signed Agent Memory `memory_action` rather than an unproven Agent Manifest `operation_kind` claim.

**Against the P4.5c TRACE/cMCP action-evidence surface.** The reference adapter wraps P4.5a evidence in the existing six-field cMCP `external_execution_evidence` envelope, hashes the detached payload with RFC 8785/JCS, and preserves `linked_call_id` as a separate audit identity from Agent Memory `action_ref`. Local vectors exercise TRACE-style receipt outcomes, wrong-call and wrong-action replay, payload/signature tampering, missing trust, domain mismatch, and lifecycle separation. A second CI path creates an isolated environment with `cmcp-runtime==0.4.0` and calls the released `cmcp_verify.verify_audit_bundle()` verifier against the emitted envelope.

The common point is that the governance layer is load-bearing. The substrate model is deliberately permissive in exactly the ways the mapping verified: identity is opaque rather than content-derived, the partition filter defaults to unfiltered, deletion is physical with no tombstone, and **no operation checks authority**. Several tests assert both halves: that the substrate *would* misbehave, and that the adapter refuses anyway. A test that only checked the adapter would not prove the governance was doing any work.

## Layout

```text
reference/
  agentmem_ref/
    substrate.py                     port + permissive in-memory temporal graph
    policy.py                        PAMA evaluation: base table, class floors, modifiers
    receipts.py                      schema-conformant decisions, receipts, audit events
    adapter.py                       the governed path
    fixture_conformance.py           drives the doctrine corpus through enforcement
    projections.py                   tier-3 declarations and the freshness relation
    residue.py                       deletion residue partition and independent sweep
    projection_governance.py         governed correction, purge, and rebuild
    portable_evidence.py             P4.5a Ed25519 portable issuer/verifier
    agent_manifest_correlation.py    P4.5b checkpoint correlation boundary
    trace_action_evidence.py         P4.5c TRACE/cMCP external action evidence
    (selectors live in adapter.py: deterministic and seeded stochastic)
  agentmem_ref/graphiti_driver.py     binding to a real temporal knowledge graph
  tests/                              model, real-substrate, and interoperability paths
  run_trace_cmcp_comparator.py        isolated released cMCP verifier execution
  run_conformance.py
```

Schema validation uses `jsonschema`. P4.5a Ed25519 signing and public-key verification use `cryptography`, added under the explicit dependency-justification rule in `../CONTRIBUTING.md`. P4.5b uses `agent-manifest==0.11.0` as a test-only comparator and does not import it from production reference modules. P4.5c uses `agentrust-trace==0.8.0` plus `rfc8785==0.1.4` for the TRACE/JCS contract and runs `cmcp-runtime==0.4.0` in an isolated comparator environment. CI pins the main validation profile to `jsonschema==4.26.0`, `cryptography==50.0.0`, `agent-manifest==0.11.0`, `agentrust-trace==0.8.0`, and `rfc8785==0.1.4`. The low-cost fixture, doctrine-boundary, and link validators remain standard-library only.

## Running it

```bash
# reference model and interoperability paths
python -m pip install \
  jsonschema==4.26.0 \
  cryptography==50.0.0 \
  agent-manifest==0.11.0 \
  agentrust-trace==0.8.0 \
  rfc8785==0.1.4
python -m unittest discover -s reference/tests -t reference

# TRACE/cMCP comparator in a dependency-isolated environment
python -m venv /tmp/agent-memory-p45c-cmcp
/tmp/agent-memory-p45c-cmcp/bin/python -m pip install \
  cmcp-runtime==0.4.0 \
  agentrust-trace==0.8.0 \
  agent-manifest==0.11.0 \
  rfc8785==0.1.4
PYTHONPATH=reference \
  /tmp/agent-memory-p45c-cmcp/bin/python reference/run_trace_cmcp_comparator.py

# stochastic containment sweep with an explicit trial count
python reference/run_conformance.py --trials 500

# add the real substrate; the substrate tests skip cleanly without it
pip install graphiti-core kuzu
python -m unittest discover -s reference/tests -t reference
python reference/run_conformance.py
```

Runs are deterministic where the contract requires determinism: identifiers are counter-based and the clock is injected, so repeated governed-adapter runs produce identical receipts and identical reports. Stochastic selection is seeded per trial, so it varies across trials and reproduces exactly for a given seed. Ed25519 signatures are deterministic for a fixed private key and canonical payload. P4.5b and P4.5c pin external package versions and upstream release commits so comparator drift is explicit rather than accidental.

## The governed path

```text
evidence -> proposal -> authority envelope -> permitted action set
         -> selected action -> substrate mutation -> decision receipt
         -> retrieval candidate -> governed admission -> active context
```

The adapter supplies what the substrate cannot: an authority gate before every write, always-explicit scope filtering, external lifecycle state, tombstones, and receipts. Artifacts are emitted against schemas already canonical in this repository rather than shapes invented beside the implementation: `pama-decision`, `decision-receipt`, `memory-audit-event`, `conformance-report`, P4.5a `portable-governance-evidence`, P4.5b `agent-manifest-memory-correlation`, and P4.5c `trace-action-evidence-bundle`.

## Paths exercised

| Path | Holds |
|---|---|
| positive commit and reconstruction | full chain executes; receipt reconstructs estimate, authority, selection, consequence; events causally linked |
| high-confidence false promotion | confidence 0.99 and 0.01 produce an identical envelope; confidence has no route to authority |
| cross-tenant relevance | substrate returns the foreign record unfiltered; adapter never reaches that default |
| prohibited action selectability | a governance-class mutation is absent from the permitted set and cannot be selected |
| stale authorization | authority resolved against an older state does not commit |
| self-approval of authority | blocked, with no permitted actions at all |
| unresolved actor authority | fails closed |
| superseded memory | remains a candidate, refused for current use, not erased |
| irreversible deletion | cannot commit autonomously; the substrate would have executed it |
| pruning | tombstones and removes from recall while content stays recoverable |
| undeclared derived residue | a projection nobody declared is detected after removal |
| version drift | policy version and estimator versions stay separable in the receipt |
| fixture corpus | all 26 doctrine fixtures pass envelope enforcement; the checker is mutation-tested |
| stochastic containment | hundreds of sampled trials never escape the permitted set, and the selector demonstrably varies |
| hostile selector | a selector returning a prohibited action is contained by the adapter and the violation recorded |
| derived-state freshness | stale and residual are computed from a recorded basis, never set by a flag |
| correction propagation | dependents go stale; content-bearing projections supersede without erasing the prior version |
| transitive purge | the whole derivation closure is reached, and a deliberate one-hop purge is caught by the sweep |
| undeclared residue | the four-way partition holds, with the undeclared cell empty as a hard gate |
| rebuild authority | estimator-mediated rebuild is refused without an authority decision; deterministic reproducible rebuild is categorical |
| portable receipt binding | Ed25519 evidence binds the canonical receipt reference, action, policy, authority state, time, and optional isolation domains |
| portable negative outcomes | authentic denial, unauthorized execution, and residual lifecycle state remain distinct machine-readable outcomes |
| portable replay and trust failures | wrong action/domain/state, signature tampering, unknown issuer, rotation, and revocation timing are exercised |
| Agent Manifest normative root | the pinned upstream implementation reproduces the v0.2 KV memory-root vector |
| Agent Manifest deletion-vector correlation | the upstream verifier accepts an RFC 9162 checkpoint built from a log whose appended test operation is `DEL`; canonical receipt and portable state refs bind the checkpoint |
| DEL versus forgetting | that accepted checkpoint remains compatible with either residual or satisfied Agent Memory lifecycle evidence |
| external negative checkpoint outcome | invalid consistency proof yields upstream `drift` while the correlation remains a valid record of a rejected delta |
| TRACE/cMCP envelope compatibility | emitted evidence uses the existing six-field external-execution envelope and the released cMCP verifier accepts it |
| TRACE call replay | released cMCP verifier rejects a receipt whose `linked_call_id` does not match the audit call |
| Agent Memory action replay | local verifier separately rejects a detached action reference that does not match the P4.5a signed `action_ref` |
| TRACE negative action outcome | a correctly bound external `rejected` receipt remains valid negative evidence rather than malformed evidence |
| TRACE versus lifecycle | accepted action evidence remains compatible with both residual and satisfied Agent Memory lifecycle evidence |
| TRACE trust failure | local TRACE-style classification reports unknown issuer as unverified; configured cMCP external-key verification fails closed on the same missing trust anchor |

## Known limitations

Stated rather than left to be discovered:

1. Corpus coverage is envelope enforcement, not full scenario execution: decay, calibrated saturation, retrieval ranking, and most lifecycle transitions are outside this adapter and are declared as exemptions in the report rather than silently skipped.
2. Retrieval ranking is lexical overlap, not the substrate's hybrid search, because hybrid ranking needs an embedder. Recall quality is not measured.
3. The policy implements the subset of the decision table these paths need, not the whole table.
4. The substrate binding uses an embedded backend that is deprecated upstream, chosen because it needs no server. No governance behavior under test depends on the backend choice.
5. Node topology is simplified to one edge per fact. This exercises governance invariants, not knowledge modelling.
6. Derived-state governance operates on an adapter-owned sidecar. The design spike names this as the obvious home for substrates that cannot store a projection declaration, and notes that it reintroduces the consistency problem one level up. That trade is accepted here rather than solved.
7. Residue is measured over declared projections. State that was never declared is outside the sweep's reach by construction, which is why the declaration surface is the load-bearing part rather than the traversal.
8. The P4.5a trust profile assumes configured Ed25519 public trust keys. Production key custody, trust discovery, certificates, and external revocation infrastructure remain outside this slice.
9. P4.5b intentionally imports Agent Manifest private checkpoint modules only in its pinned comparator tests because the upstream implementation issue and specification surface those exact functions. This is not a stable production API commitment and is isolated from Agent Memory runtime code.
10. An Agent Manifest checkpoint root proves the bound log state but does not independently reveal the semantic class of a new operation. P4.5b demonstrates a real upstream `DEL` through executed test input; a compact content-free third-party proof of operation class would require additional upstream operation/inclusion evidence and is not invented here.
11. P4.5c binds Agent Memory action evidence into TRACE/cMCP receipt infrastructure; it does not prove a physical or business outcome occurred and does not make TRACE a PAMA interpreter.
12. The released cMCP 0.4.0 dependency graph is intentionally isolated from the main evidence environment because its AGT dependency line resolves a lower cryptography range. This is comparator containment, not a production dependency recommendation.
13. P4.5c does not demonstrate hardware attestation of the Agent Memory process, production trust-anchor discovery, or upstream Community/Verified integration acceptance.
