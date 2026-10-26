# Agent Memory: minimum local MCP consumer

**Development candidate, not production-qualified.** The qualified Gate 1 head exposes three
MCP tools against the Agent Memory SQLite facade: explicit save, exact logical-key recall,
and bounded question retrieval. This is not a separate database or an answer-generation engine.

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

- memory_remember(key, text, create_only=False): explicit persisted write with
  source_ref=mcp:agent-observation; no automatic conversation ingestion.
  `create_only=True` performs a scope-filtered public-history precondition
  before writing. A live head, tombstone, nonzero/ambiguous state or failed
  history read returns `committed=false`, `stage=precondition`,
  `refusal=key_exists_or_unavailable`, without echoing memory content or
  writing a second fact. A verified absent key can be written only through
  the existing governed `AgentMemory.remember` policy; passing this
  precondition grants no memory authority. The opt-in guard is **not**
  cross-process atomic: the trusted host must serialize concurrent writers,
  and it does not guarantee a globally unique logical key. When updating an
  existing fact, use the separate governed correction workflow and honor a
  `require_review` outcome rather than silently issuing another remember.
  Default `create_only=False` preserves the frozen Gate 1 write behavior.
- memory_get(key): governed recall plus **strict provenance-key verification**.
  The model receives only facts whose resolved memory_ref exactly matches
  the requested key. A missing/withheld/out-of-budget key returns
  lookup_status=not_found_or_unavailable, **not** a guessed nearby memory and
  not proof that the key never existed. If several governed facts resolve under
  the same logical key, returns lookup_status=ambiguous_multiple_versions
  without guessing which one supersedes the others. For one candidate, the
  public history must independently confirm that its fact_ref is the live head
  and the delivery state must be fully resolved; stale or unverifiable heads
  return lookup_status=head_unverified_or_changed, and truncated content
  returns lookup_status=incomplete_evidence. In these failure states the
  bridge returns no memory text, no successful get, and no state counter.
  The consumer-specific delivery_assessment is no_verified_exact_head; only
  a confirmed complete head yields verified_exact_head_delivered. An upstream
  selection_assessment cannot override this exact-key refusal.
  This deliberately treats unverified and stale evidence identically.
  No direct database access.
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
- memory_find(question, max_items=5, experimental_selectivity=False,
  verified_key_heads_only=False): governed recall_context within bounded delivery
  budgets, defaulting to all_returned. The experimental #819 selector must
  be opted into deliberately. The separate opt-in `verified_key_heads_only`
  checks the public history of each delivered logical key and returns only
  fully resolved facts that are confirmed current key heads. Old generations,
  unknown/unverifiable heads, missing key provenance, and truncated texts are
  dropped. The filter reports `filtered_count`, with no stale text or filtered
  key references in its evidence/non-head-key output; unresolved package
  references and reasons are also withheld from strict-mode results. It does **not** refill the
  retrieval budget, verify the semantic relevance or temporal truth of a
  remaining fact, prove a key does not exist, generate an answer, or certify
  that the evidence is sufficient. It can lose a required fact and may
  legitimately produce empty results even when relevant data exists. This
  option is a model-facing safety constraint, **not** a qualified Gate 2
  retrieval-quality improvement. Both options remain disabled by default.
  Supplying a nonboolean value for either option is an error.

The Gate 1 bridge does not expose correction/whole-key forgetting without qualified lifecycle
evidence, does not grant action authority, and makes no claim of accurate
no-answer calibration. An external model used by the agent harness may
receive retrieved memory text, so use test data and a trusted harness.

## Experimental governed lifecycle: head-only tombstone

The development branch `product/mcp-governed-tombstone-no-ci` adds
`memory_tombstone_head(key, expected_fact_ref)`. This is **not** a generic
`memory_forget` or whole-key deletion operation. It calls the public
`AgentMemory.history` and `AgentMemory.forget(permanent=False)` APIs only.

The host must explicitly set this extra environment variable:

    AGENT_MEMORY_MCP_ALLOW_HEAD_TOMBSTONE=enabled

Absent that exact value, the tool refuses **before opening the store**.
The model cannot set this variable through MCP tool arguments. For a legitimate
request, first call `memory_get(key)` under the same trusted host scope and
supply its authorized current `fact_ref` as `expected_fact_ref`. The bridge
checks the public, scope-filtered current head against that reference. Missing,
foreign, revoked and stale references return the same
`status=unavailable_or_changed` with `committed=false`. If eligible, the
runtime alone decides whether the governed prune commits; policy refusal is
reported as `governed_refusal` with `committed=false`.

The success label is **`head_tombstoned`**, intentionally not `forgotten`.
The operation cannot prove that older independently current facts, derived
representations or previously exported text have been removed. Earlier writes
under the same key can still be returned by `memory_find`. It does not
perform permanent erasure or validate that every earlier generation is gone.
The precondition is also **not atomic across separate writer processes**:
a host must serialize all writes to this development store. Do not use this
tool as a cross-process compare-and-swap or privacy-erasure guarantee.

This additional preview tool does not change the frozen Gate 1 proof or
qualify Gate 2. The original Gate 1 transcript and tool list remain immutable
historical evidence for the three-tool head. Run the new tests explicitly:

    .venv/bin/python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_head_tombstone.py" -v
    .venv/bin/python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_real_mcp.py" -v

Acceptance still requires a clean checkout, the official MCP SDK, a genuine
stdio/reconnect test, authorization negatives, and independent deletion
regression evidence. Until those pass, this is a development candidate only.

## Experimental governed correction: explicit current-head replacement

This development branch also adds
`memory_correct_head(key, expected_fact_ref, replacement_text, replacement_kind)`.
It does **not** issue a second `memory_remember`, because that would leave the
old current-state fact potentially discoverable. Correction uses the
runtime's public `AgentMemory.correct` API and preserves all existing PAMA
approval and refusal rules. A policy refusal stays a refusal. When PAMA specifically requests review or
external verification, the tool reports `review_required=true` and
`next_step=host_governance_review`; it does **not** generate approval
evidence, bypass the decision, or disclose internal refusal details.

The trusted MCP host must set:

    AGENT_MEMORY_MCP_ALLOW_HEAD_CORRECTION=enabled

Without that exact host-side value, the tool refuses before opening the
runtime. The model cannot change this setting through the tool call. Use an
authorized `memory_get(key)` result as the source of `expected_fact_ref`.
Missing, forbidden and stale heads yield the identical
`status=unavailable_or_changed`; an unchanged authorized head may yield
`governed_correction_committed` or `governed_refusal`, depending on the
runtime's existing policy decision. Do not supply a fallback ordinary
`memory_remember` after a correction refusal.

`replacement_kind` must be either `error_correction` (previous assertion
was wrong) or `state_change` (previous state was historically true). The
choice is explicit, never inferred by this bridge. Host/operator consent to
enable mutation and serialized writer ownership are prerequisites; this is not
a cross-process compare-and-swap, and it is not an authorization mechanism.
No privileged verification or external attestation is synthesized by the tool.

To exercise the new tests:

    .venv/bin/python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_head_tombstone.py" -v
    .venv/bin/python -m unittest discover -s integrations/agent-memory-mcp/tests -p "test_real_mcp.py" -v

An exact-head real-SDK run and independent scope/deletion/correction review are
still required. Both lifecycle tools are unqualified development candidates.
An older fact written independently under the same logical key may remain
discoverable even after a head correction or head tombstone. No whole-key
erasure guarantee or production support is implied.

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
