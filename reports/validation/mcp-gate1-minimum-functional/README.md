# Gate 1: Minimum Functional Product, Agent Memory as an MCP memory provider

**Verdict: Gate 1 PASSES at the commit recorded in `gate1-workflow.json` (`repo_head`), after two
corrections made on this branch.** This is the minimum-functioning-product gate only: a real
agent harness can save, exactly retrieve, find by question, survive a server restart, and is
refused across scopes, through the official MCP client over stdio. It says nothing about
retrieval quality (Gate 2).

Starting commit `8b346c09b2aad4061bc6bf78bc5c51766f7b0292`, branch
`product/mcp-minimum-memory-loop-no-ci` (contains the #819 head `b2b19a40`). No GitHub Actions, no
merge, no release, no frozen baseline touched; `[skip ci]` on every commit.

## 1. Environment (`logs/versions.txt`, `logs/pip-install.log`)

Fresh venv, `python -m pip install -e . "mcp>=2,<3"` succeeded with no blocker.

| component | version |
|---|---|
| Python | 3.12.3 (CPython), Linux |
| mcp (official SDK) | 2.3.0 (`mcp-types` 2.3.0) |
| agent-memory-reference | 0.2.0, editable from this checkout |
| pydantic / anyio | 2.14.1 / 4.15.1 |

## 2. Committed tests, exactly as the brief lists them

| suite | at `8b346c09` (unmodified) | after fixes |
|---|---|---|
| `test_bridge.py` (12 tests, fake runtime) | **12 OK** | 12 OK |
| `test_real_mcp.py` (5 tests, real SDK + real SQLite runtime) | **2 OK, 3 ERROR** | **6 OK** (one test added) |

Logs: `logs/test_bridge-8b346c09.log`, `logs/test_real_mcp-8b346c09-RED.log`,
`logs/test_real_mcp-after-fix.log`, `logs/test_bridge-final.log`, `logs/test_real_mcp-final.log`.
No skips in either suite.

**Failure 1 (3 errors).** Every tool result reached the client as text JSON with
`structured_content=None`, so `_result()` could not read `committed`. Cause: the three tools were
annotated `-> dict`. MCP SDK 2.x derives an output schema only from a parametrised mapping
(`dict[str, Any]`), a Pydantic model or a TypedDict; a bare `dict` has no type hints
(`func_metadata._create_output_model`, "Other class types" branch) so no output schema is
published and no structured content is sent. Fix: annotate the three tools `-> dict[str, Any]`
(`server.py`). After the fix `list_tools` publishes `output_schema {"type":"object",
"additionalProperties":true}` and results carry both text and structured content.

## 3. Real stdio workflow proof (`gate1_workflow.py`, `gate1-workflow.json`, `logs/gate1-workflow.log`)

Driver: official `mcp.Client(StdioServerParameters(command=<venv python>, args=[server.py],
env=<host identity>))`. The server is a genuine child process (pid recorded), the store is a fresh
temporary directory. 24 checks, **24/24 pass** at the final head; at the unmodified commit the same
driver passes handshake and discovery and crashes at step 2 on `structured_content=None`
(`logs/gate1-workflow-RED-8b346c09.log`).

| step | request | response (structured content, abridged) | result |
|---|---|---|---|
| 1 | initialize + `tools/list` | server `Agent Memory Local`; tools `memory_remember`, `memory_get`, `memory_find`; no tool exposes tenant/scope/actor/root | pass |
| 2 | `memory_remember {key: memory:owner:preferred_editor, text: "The owner writes Python in Neovim with the pyright language server."}` | `{committed: true, fact_ref: ref-0004, stage: commit, outcome: allow_with_ledger, refusal: null}` | pass |
| 3 | `memory_get {key}` | `lookup_status: found`, one item, exact text, `memory_ref == key`, `fact_ref == ref-0004`, `trust: untrusted_memory_text`, `answer_generated: false` | pass |
| 4 | `memory_find {question: "Which editor and language server does the owner use for Python?", max_items: 5}` | evidence contains the exact text, `profile: all_returned` | pass |
| 5 | client closes | server pid 751 gone; store on disk: `agent-memory.sqlite3` 319,488 B, `runtime-config.json`, `generation-witness.json` | pass |
| 6 | new `Client(...)` same store | new server pid | pass |
| 7 | `memory_get {key}` | `found`, same text, same `fact_ref ref-0004` | pass |
| 8 | `memory_get {key: memory:owner:preferred_editors}` (near miss) and `memory:never-written` | `not_found_or_unavailable`, `evidence: []`, no text leaked | pass |
| 8 | second `memory_remember` under the same key with a different value, then `memory_get` and `memory_find` | see section 4 | pass (after fix 2) |
| 8 | another scope `project:other-team`, same tenant and root: `memory_get` and `memory_find` | `not_found_or_unavailable` / empty evidence, no text leaked | pass |
| 8 | another tenant `tenant:stranger`, same root | MCP error (`Error executing tool memory_get`), no text leaked | pass |
| 9 | blank key, `max_items: 10000`, 4,001-char text | `is_error: true`, `"Invalid memory tool input or delivery limit"`, no structured success, no traceback | pass |
| 9 | unknown tool `memory_delete_everything` | `is_error: true`, `Unknown tool` | pass |
| 9 | server launched with no host environment | `is_error: true`, `"Agent Memory host configuration is missing or unsafe"`, no traceback in the result | pass |
| final | | no server process left | pass |

SQLite persistence evidence (read-only inspection, never through the product path): after the
whole run the store holds `facts: 2`, `substrate_write_log: 2`, `runtime_journal: 21`,
`governance_log: 26`, `runtime_configuration_binding: 1`, `runtime_state: 1`
(`agent-memory.sqlite3`, 356,352 B). The fresh process in step 6 recovered the same `fact_ref`.

## 4. Failure 2: conflicting key, found by the workflow and fixed

The README and the bridge test promised that conflicting values under one key never become an
exact answer (`ambiguous_multiple_versions`). Against the **real** runtime that path does not
trigger: a second `memory_remember` under an existing key commits a new generation and moves the
key's head (`history.state_version 2`, `probe_same_key_rewrite.py`), the exact route serves only
the head, so `memory_get` returned the newest value as `found`, while the earlier fact stays a
`current_state` fact that `memory_find` still returns. An agent received two contradictory
"current" statements for one key with no marker, and `memory_get` hid the conflict.

Fix (`bridge.py`, smallest change that keeps the loop working): after each read, the bridge calls
the public `history(key)` for every distinct `memory_ref` in the evidence and marks each item
`latest_for_key` (true / false / `None` when unknown) and `key_versions`; `memory_find` lists
`conflicting_keys`; `memory_get` reports `key_versions` and
`earlier_versions_remain_recallable`. Nothing is suppressed, merged or guessed; no write
semantics changed. README updated; `test_same_key_rewrite_is_visible_not_silently_merged` added
to the real-SDK suite. The driver verifies: `memory_get` serves exactly the head with
`key_versions: 2`; `memory_find` marks the head `latest_for_key: true`, the earlier value
`false`, and lists the key.

## 5. Remaining issues (not Gate 1 blockers)

- A second write under an existing key is still not a correction; the earlier generation remains
  a current-state fact in the runtime. The bridge exposes no `correct`/`forget` (needs lifecycle
  evidence), so an agent cannot retire a value, only mark it superseded by writing again.
- A tenant mismatch on a shared root surfaces as the SDK's generic `Error executing tool`
  (`RuntimeRecoveryError` logged with a traceback on the server's stderr). The client gets a
  proper MCP error and no content; a clearer `ToolError` message would help operators.
- `serverInfo.version` is empty; the `initialize` result is not exposed as an attribute by the
  2.3.0 client wrapper, so handshake evidence here is the advertised server name in result
  metadata plus `tools/list`.
- Single-user, trusted-host profile only: the server does not authenticate callers; host
  identity comes from environment variables. Windows not executed.
- Retrieval quality, no-answer calibration and the experimental selector are Gate 2 and were not
  evaluated here.

## 6. Files

`gate1_workflow.py` (driver), `gate1-workflow.json` (full transcript: every request, every
response, pids, store inspection, versions), `probe_same_key_rewrite.py`, `logs/`.
