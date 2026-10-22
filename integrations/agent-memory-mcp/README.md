# Agent Memory: minimum local MCP consumer

**Development candidate, not production-qualified.** A real agent harness can call three
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

- memory_remember(key, text): explicit persisted write with
  source_ref=mcp:agent-observation; no automatic conversation ingestion.
- memory_get(key): governed exact-key recall. No direct database access.
- memory_find(question, max_items=5, experimental_selectivity=False):
  governed recall_context within bounded delivery budgets, defaulting to
  all_returned. The experimental #819 selector must be opted into deliberately.

The bridge does not expose correction/forget without qualified lifecycle
evidence, does not grant action authority, and makes no claim of accurate
no-answer calibration. An external model used by the agent harness may
receive retrieved memory text, so use test data and a trusted harness.

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
