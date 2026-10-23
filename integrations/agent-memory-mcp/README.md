# Agent Memory: minimum local MCP consumer

**Development candidate, not production-qualified.** A real agent harness can call five
MCP tools against the Agent Memory SQLite facade: explicit save, exact logical-key recall,
bounded question retrieval, and two host-authorized lifecycle actions that are disabled by default:
reversible forgetting and governed correction. This is not a separate database or an answer-generation engine.

Unlike the existing Hermes observation-only provider, this is an actual read/write consumer.

## Preconditions

- Python 3.11+ and a fresh development virtual environment.
- Install this repository's reference package and official MCP Python SDK **v2**.
- Use a dedicated private, trusted local store in a single-user development profile.
- New/test store only. Do not point at pre-#809 or legacy production data, network mounts,
  multi-user directories, or existing deployed instances. Windows security is unqualified.
- Host provides actor/tenant/scope via its own environment, not model tool arguments.
  This MCP subprocess does not authenticate callers. The packaged optional legacy
  gate does not prove the date of first store creation.
- The host store root must be an absolute path without parent traversal, and no
  existing path component may be a symlink or Windows junction. This catches
  accidental or adversarial ancestor redirection that checking the last
  directory alone misses. It is **configuration preflight**, not protection
  against filesystem races, reparse-point substitutions, writable ancestors
  or a malicious local user. The host must provision private directory ACLs
  and a trustworthy canonical path outside untrusted writable locations.

## Install and test from the repository root

    python -m venv .venv
    .venv/bin/python -m pip install -e . "mcp>=2,<3"
    .venv/bin/python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_bridge.py" -v
    .venv/bin/python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_real_mcp.py" -v

On Windows substitute .venv\Scripts\python.exe. The second suite must call
the **real** MCP SDK client and Agent Memory SQLite runtime. Mock-only passing
tests are not acceptance evidence.

## Connect the agent harness as a stdio MCP subprocess

Executable:
    /absolute/path/to/.venv/bin/python

Arguments:
    /absolute/path/to/repo/integrations/agent-memory-mcp/server.py

Trusted host environment:
    AGENT_MEMORY_MCP_ROOT=/absolute/private/local/agent-memory-store
    AGENT_MEMORY_MCP_TENANT=tenant:local
    AGENT_MEMORY_MCP_ACTOR=agent:my-harness
    AGENT_MEMORY_MCP_SCOPE=project:local

After installing mcp[cli], try the MCP Inspector from the repository root:
    .venv/bin/mcp dev integrations/agent-memory-mcp/server.py

The server uses stdio. Stdout is protocol-only, with MCP v2 transport,
framing, and tool schemas provided by the official SDK.

## The one-session acceptance test

1. Call memory_remember with key memory:editor and text "I use Neovim for Python".
   Confirm committed=true. Refused write is not stored.
2. Call memory_get with key memory:editor. Verify exact evidence text is returned
   with trust=untrusted_memory_text, and no generated answer.
3. Call memory_find with question "What editor do I use for Python?" and inspect
   the bounded relevant evidence. Do not assume relevance is guaranteed.
4. Disconnect/reconnect the MCP client, then memory_get the same key again.
   Content must still be there after durable restart.
5. Challenge isolation with another trusted host scope. Never allow clients to
   supply tenant, actor, root or scope through tool parameters.

## Tool semantics

- memory_remember(key, text): explicit persisted write with
  source_ref=mcp:agent-observation; no automatic conversation ingestion.
- memory_get(key): governed recall plus **strict provenance-key verification**.
  The model receives only facts whose resolved memory_ref exactly matches
  the requested key. A missing/withheld/out-of-budget key returns
  lookup_status=not_found_or_unavailable, **not** a guessed nearby memory and
  not proof that the key never existed. If several governed facts resolve under
  the same logical key, returns lookup_status=ambiguous_multiple_versions
  without guessing which one supersedes the others. No direct database access.
  A second memory_remember under an existing key is **not a correction**: the runtime
  commits a new generation and moves the key's head, but the earlier fact stays a
  current-state fact. memory_get serves the head only and reports key_state_version
  (the runtime's governance state counter for the current generation, **not** a count of
  written versions: it resets after a governed deletion), earlier_generations_enumerated=false
  and a caveat; memory_find may still return the earlier text and marks every item
  latest_for_key=true/false (None when unknown) and lists non_head_keys: a
  **version-divergence signal** (at least one returned item is not its key's head), not a
  verified contradiction; identical re-writes qualify. The bridge does not compare values,
  does not correct or retire the earlier generation, and does not hide it. None of these
  fields is canonical history. Nothing is silently merged.
- memory_find(question, max_items=5, experimental_selectivity=False):
  governed recall_context within bounded delivery budgets, defaulting to
  all_returned. The experimental #819 selector must be opted into deliberately.
  With it, `profile` is `evidence_qualified`, `selection_policy_version` names the
  selector policy (`0.5.1`: a returned memory that shares no content term with the question
  is declined only when it is a single statement, or when the question names a subject by
  proper-noun possessive and the memory grounds a different one it never mentions; a longer
  memory without a shared term is otherwise delivered as uncertain, because a paraphrase
  shares no token and can still carry the answer), and every declined memory appears under
  `unavailable` with state `omitted_selection`, its reason (`no_query_term_evidence` /
  `subject_mismatch`), `absence_grounding` and the inspected subjects. Declined content is never read. The recall itself is identical in both profiles;
  `selection_assessment` is `evidence_delivered`, `undetermined`, `no_relevant_evidence`
  (every returned fact declined on a grounded basis: not proof that no memory exists) or
  `no_returned_candidates`.

The bridge does not expose correction without host-held qualified lifecycle
evidence, does not grant arbitrary deletion authority, and makes no claim of accurate
no-answer calibration. The reversible forgetting tool is host-bound, never permanent. An external model used by the agent harness may
receive retrieved memory text, so use test data and a trusted harness.

### Stage C: conservative host-side evidence insufficiency (unqualified slice)

`memory_find` now includes `evidence_assessment` and `evidence_assessment_reason` without
changing retrieval or the default `all_returned` profile. When it delivers **no complete,
attributed** item (resolved state, nonempty text, fact reference and logical memory reference),
the result is `insufficient_evidence` with reason `no_complete_attributed_evidence`.
Truncated or unattributed text remains visible but cannot pass this minimal guard.
If every otherwise-complete candidate is known through the runtime history to
be a **non-head key generation**, the result is also `insufficient_evidence`,
with reason `only_non_head_evidence`. The older text is **not removed** from
ordinary recall, and unknown head states are not treated as known stale.
When at least one complete candidate is not known to be non-head, the result
is **`unverified`**, not `sufficient`; its reason is
`answer_entailment_not_checked`. The existing
`answerability_verified=false` remains unchanged. An agent or host must not treat
`unverified` as permission to answer.

The MCP server also tells the model to abstain from answering from memory on
`insufficient_evidence`; `unverified` remains a warning to inspect support, not
an answerability approval. Prompt instructions alone are not proof that an
actual agent obeys them, so a real-agent Stage D pilot remains mandatory.

The populated-store acceptance gate validates the **entire fixed manifest**, its
source profile, retrieval evidence and post-retrieval gold labels; subset-only success,
relabeling or a replaced provider fails closed. Each receipt includes the SHA-256 of
the manifest used. Offline gate tests only validate admission, not MCP behavior.

The separate populated-store acceptance gate reuses the existing 18-record,
14-question `quality_cases_dev.json` cohort: 11 answerable controls and
three unanswerable controls whose retrieved context contains distractors.
It records the answerability metadata alongside full-evidence coverage and
**fails unless** the unanswerable controls are marked insufficient while all
11 required sources are still delivered. Labels are joined after MCP calls,
not passed to the tool. From the repo root, in the qualified venv, run:

    python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_stage_c_gate.py" -v
    python integrations/agent-memory-mcp/stage_c_gate.py --out /tmp/am-stage-c.json

A nonzero status from the second command is an expected **Stage C BLOCKED**
signal until detection works on a populated store; it is not evidence that
the earlier Gate 1 or Stage A/B lifecycle operations regressed. No measured
result from this new gate is claimed until a fresh real-MCP run is attached.

This guard is intentionally narrow. Unrelated, yet complete and attributed, recalled
memories can still produce `unverified` for a question with no answer. This slice
has **not** solved semantic insufficiency, calibrated abstention, or the populated-store
no-answer problem. The alpha acceptance workflow adds three real-MCP empty-scope
negative controls and one answerable control, but **Stage C remains BLOCKED** pending
populated-store negative tests and verified task-level abstention. Historical Gate 1 and
Stage A/B evidence are untouched.

## Internal alpha lifecycle slice: reversible, host-bound forgetting

`memory_forget(key)` is present in the alpha catalog but **disabled by
default**. For a single operator-authorized prune only, a trusted MCP host must
bind BOTH of these variables when starting the local server:

    AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY=memory:owner:the_exact_key
    AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF=host-record:<genuine-existing-operator-record-ref>

These claims are not supplied through MCP tool arguments. The target must
match **exactly**; a different key, missing approval or missing evidence reference
returns `committed=false`, `host_authorization_required` before opening the
store. No arbitrary target, risk class, approval reference, authority override
or `permanent=True` exists on the tool surface. On a correctly bound call,
the bridge invokes only `AgentMemory.forget(key, permanent=False,
evidence_refs=(host_ref,))`; the existing facade can still refuse/park the
action. Only `committed=true` means the governed tombstone was committed.
After operator use, remove the grant from the host environment and restart
the MCP subprocess. Do not place secrets in either variable.

**Security limitations:** A host environment value is **not** proof that a
human approved anything and the facade does not verify the provenance of an
arbitrary evidence-ref string cryptographically. A host operator is responsible
for maintaining a genuine record and provisioning the exact key. This mechanism
is suitable only for a **trusted single-user test deployment** with controlled
process environment and protected local directory. It is not general autonomous
agent deletion, authenticated operator approval, data erasure, or production
authorization. Deleted canonical generations and audit metadata are not
cryptographically shredded. The tool must not be enabled on an untrusted host.

The previous Gate 1 receipt and its original three-tool discovery test remain
historical evidence at their original commits. The alpha catalog adds a fourth
tool and must qualify independently: a working Gate 1 three-tool replay **does
not qualify the new forget tool**.

Acceptance for this first slice: save a fictional key, verify retrieval,
attempt forgetting with no grant (refused, still retrievable), attempt the
wrong key under an exact host grant (refused), forget the approved key through
the real MCP SDK (only if the public facade commits), then reconnect to prove
its content is no longer visible in `memory_get` or ordinary `memory_find`.
Cross-scope refusal and ordinary save/get/find must keep working.

## Internal alpha lifecycle slice: host-authorized governed correction

`memory_correct(key, text)` replaces the current value of one key, and it is **disabled by
default**. Correction is `REQUIRE_REVIEW` in the governance policy at every risk class. It
commits only with qualified, independent lifecycle evidence. Writing the same key again with
`memory_remember` is **not** a correction: the old value is not retired.

For one operator-authorized correction, the person running the host writes a small JSON
record outside the memory store and names it when starting the server:

    AGENT_MEMORY_MCP_CORRECTION_RECORD=/absolute/path/to/correction.json
    # correction.json: {"key": "memory:owner:the_exact_key", "text": "the exact corrected text", ...}

The bridge accepts the record only when all of these hold:
- it is an absolute path;
- it is a regular file, not a symlink;
- it is at most 16 KiB;
- it is a JSON object;
- its `key` and `text` equal the tool call's arguments exactly.

Otherwise the tool returns `committed=false`, `host_authorization_required` without opening the
store.

With a matching record, the bridge proceeds as follows:
1. It builds one artifact-bound `EvidenceItem` (the record's path and SHA-256).
2. It opens the store with a host-held `VerifierRegistry`, whose verifier re-reads that exact
   file and checks the digest and the key/text.
3. It calls only the public `AgentMemory.correct(key, text, evidence=(item,))`.

The facade's own policy decides the outcome. Only `status="corrected"` (`committed=true`,
`operation="correction"`) means the old value was retired. After that, `memory_get` and
`memory_find` serve the new value and its new `fact_ref`, and the old value is not current
evidence.

A refusal or a parked review is not a correction. The tool exposes no risk class, approval,
attestation or evidence argument. A high-risk correction would also need a human-confirmation
attestation, which this surface does not provide, so it stays parked. After use, remove the
variable and restart the subprocess.

**Security limitations:** the record is not authentication. Anyone who can write that file
and set the host environment can authorize a correction. The verifier proves only that the
file named by the host still holds the exact authorized key/text. It does not prove who wrote
it. This is suitable only for the same **trusted single-user test deployment** as forgetting.

The full internal alpha remains **BLOCKED** until meaningful insufficient-evidence/abstention
behavior works end to end, from the host's side, and a pilot (including Windows) passes. Do not
call these lifecycle slices a completed alpha.

## Two acceptance gates

**Gate 1, minimum functioning product:** One exact-head run with an actual
MCP client, real governed write, exact get, natural-language find, reconnect
and cross-scope negative test. Do not accept a mock-only demo.

**Gate 2, genuinely useful product:** On disjoint previously unseen tasks,
the agent can answer accurately using retrieved evidence and abstain on
unanswerable tasks, with substantive wins over an indexed SQLite FTS5 baseline
at equal budgets, without breaking scope or losing required evidence.

Until both gates pass, this is a developer preview, not production 1.0.
No GitHub Actions, merges, tags, accepted benchmark modification or release.

## Gate 2: real MCP evidence usefulness diagnostic (author-visible)

This is a deliberately **small development cohort**, not a blinded holdout,
qualified answer-generation benchmark or production-readiness score.

The committed test corpus is `quality_cases_dev.json`: 18 fictional records
with 14 queries (11 answerable by annotated source keys and 3 no-answer).
The probe calls **real** `memory_remember` and `memory_find` over the same
stdio MCP protocol proven in Gate 1, then runs an in-memory **SQLite FTS5**
(`unicode61` / `bm25` / simple OR-term query) over the exact text.

From the repository root in the venv from above:

    python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_quality_probe.py" -v
    python integrations/agent-memory-mcp/quality_probe.py --out /tmp/am-gate2-dev.json
    python integrations/agent-memory-mcp/quality_probe.py --selectivity --out /tmp/am-gate2-dev-selective.json

`--selectivity` calls `memory_find` with `experimental_selectivity=true` so both consumer
profiles are measured through the same real MCP path; the report records which was used
(`selectivity`) and, per question, the declined facts with their reasons (`mcp_omitted`).

`task_eval.py` (Gate 2 Phase 5) hands only the evidence `memory_find` delivered to a reader
(a deterministic extractive reader, or a pinned open ONNX SQuAD model) and joins gold afterwards;
its "correct" figure is a whole-token gold-phrase-match **proxy** with a negation guard, not
verified answer correctness, and required evidence is credited only for fully delivered text.

The output contains per-question returned keys and scored evidence,
not retrieved plaintext or made-up answers. It reports:

- Complete required-source coverage only when MCP delivers the **full**
  seeded text with verified source key. Raw key hits are separate: a
  truncated or missing-provenance item is not credited as full evidence.
- Unattributed, incomplete or unavailable context items and irrelevant
  source-key burden, including explicit forbidden-key incidences.
- Empty context on no-answer questions, separately from answer accuracy.
- Query p50/p95 for the actual MCP roundtrip versus indexed FTS5 search.

The 18 fictional texts are ASCII and short enough for the full text of
the largest five to fit the MCP character and token caps. The probe
refuses to score an expanded corpus if that assumption stops holding,
rather than letting the FTS5 arm silently gain a context-budget advantage.

**Interpretation:** The source labels are development annotations, not proof
that the text entails the answer. Empty context on an unanswerable question
is a context proxy, **not** proof an agent abstained; neither arm generates
answers in this probe. FTS5 doesn't pay Agent Memory governance/ingestion
costs, and its context text/token bounds are not identical, so timing and
cost are descriptive, not apples-to-apples. These facts are stated in the
JSON output rather than silently buried in a benchmark claim.

After executing this transparent diagnostic, freeze candidate changes and
run a **separate, previously unrevealed task set** with a real answer-generating
agent harness, blinded gold answers and an equal-capacity indexed baseline.
That later experiment must evaluate actual correct answers and justified
abstention, not merely whether a source identifier appeared.

Do not merge this development probe into the frozen baseline or interpret
any gain as #819 resolved. Prefer fixing demonstrated correctness defects
over adding more evaluation plumbing.
