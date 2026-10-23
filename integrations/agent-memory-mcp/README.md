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

### Stage C: host-side evidence insufficiency (BLOCKED; optional answer-support check)

`memory_find` adds `evidence_assessment`, `evidence_assessment_reason` and an `answer_support`
block. It never changes retrieval, the default `all_returned` profile or the delivered
evidence. Retrieval relevance is not answer support: a populated store returns plausible
memories for almost any question.

| assessment / reason | meaning |
|---|---|
| `insufficient_evidence` / `no_complete_attributed_evidence` | no resolved, attributed, nonempty item was delivered |
| `insufficient_evidence` / `only_non_head_evidence` | every complete item is a known non-head key generation (still disclosed) |
| `insufficient_evidence` / `no_answer_span_in_current_evidence` | original method: no answer span in any current, complete item, alone or together |
| `insufficient_evidence` / `no_supported_answer_in_current_evidence` | successor method: no current, complete item (or all of them together) both names the question's subjects and answers it |
| `unverified` / `answer_span_candidate_not_verified`, `supported_answer_candidate_not_verified` | support found; **not** verification |
| `unverified` / `answer_entailment_not_checked` | the host has not enabled a check (the previous behavior) |
| `unverified` / `answer_support_check_unavailable` | enabled but the model failed to load or run; nothing is claimed either way |

Nothing in this slice reports evidence as verified, and `answerability_verified` stays false.

**Optional answer-support check (host-enabled, off by default).** `answer_support.py` holds two
pinned methods. The host chooses one by the model directory it names in
`AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR`, and each directory layout matches exactly one pin set.
Both methods:
- use the existing optional `semantic` extra (onnxruntime, tokenizers, numpy): no new
  package, no LLM and no network at run time;
- pin every file by sha256;
- read only items that are resolved, attributed, nonempty and not known to be non-head.

- `extractive-qa-null-comparison/1.0.0` (the original, experimental): `optimum/roberta-base-squad2`.
  A span counts when it beats the model's own null answer (the Hugging Face pipeline defaults,
  margin 0). It does not check subjects.
- `answerability-subject-grounded/1.0.0` (the successor, experimental). It separates *subject
  applicability* from *answerability*, and the `answer_support` block reports each step:
  - subject applicability (deterministic): every capitalised name the question uses after its
    first word must occur in the item, compared with the runtime's own fold;
  - answerability (`cross-encoder/qnli-electra-base`): the item answers the question when the
    model's logit is above 0. No extractable span is needed;
  - support means both, for one item or for all current items read together.

Fetch and enable:

    pip install -e ".[semantic]" -c reference/requirements-semantic.txt
    python integrations/agent-memory-mcp/answer_support.py fetch answerability /abs/path/support-model   # or: extractive
    AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR=/abs/path/support-model   # in the MCP server environment

Footprint and cost, measured on one CPU thread:

| | Original | Successor |
|---|---|---|
| Model files | 498 MB | 439 MB |
| Resident memory | about 1.5 GB | about 1.3 GB |
| Load time | about 2.5 s | about 1.9 s |
| `memory_find` median | about 290 ms | about 370 ms |

Without a check, `memory_find` takes about 35 ms.

The MCP server tells the model to abstain from answering from memory on
`insufficient_evidence`. Prompt instructions are not proof that an actual agent obeys them, so
a real-agent Stage D pilot remains mandatory.

**Evidence.** `stage_c_gate.py` runs the development cohort. `stage_c_adversarial.py` runs any
cohort through real stdio MCP over governed SQLite. It applies a correction, a same-key rewrite
and a forget through the real tools, restarts the server, and runs one arm with the check
disabled plus one arm per `--support-model-dir`, all at the same retrieval budget
(`max_items=5`). Labels are joined after the MCP calls and are never tool arguments.

Receipts:
- `reports/validation/mcp-stage-c/`: the original method;
- `reports/validation/mcp-stage-c2/`: the successor.

**Stage C remains BLOCKED (NO-GO).** The second held-out cohort
(`quality_cases_holdout2.json`) was frozen before the successor was designed. The successor was
then frozen and run once.

| Arm | False abstentions | Unanswerable abstained (needs 15) |
|---|---|---|
| Disabled | 0 | 0/20 |
| Original | 0 | 14/20 |
| Successor | 0 | **9/20** |

In every arm, 18 of 20 answerable questions had their required memories delivered (A02 and A08
are retrieval misses). Every arm was stable across restart, and the delivered evidence was
identical in all of them.

Post-hoc analysis, not qualification:
- 7 of the successor's 11 misses came only from reading all five memories together. The
  classifier is trained on single sentences, and a name found anywhere in the joined text does
  not tie the answer to that name.
- The other misses, and 4 of the original's 6, are memories that answer a related question
  with the wrong kind of value: a model name for a serial number, "by text message" for a phone
  number, "the fifth of the month" for a time of day.
- Neither method checks the expected answer type. Holdout 1 was used for failure analysis and
  is development data now.

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
