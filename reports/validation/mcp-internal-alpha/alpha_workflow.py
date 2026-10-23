"""Internal-alpha Stage A proof: the four-tool Agent Memory MCP catalog (remember, get, find, forget)
as a genuine stdio subprocess, driven by the official MCP Python client, against a fresh isolated
SQLite store. Records every request and response. The historical three-tool Gate 1 evidence in
``../mcp-gate1-minimum-functional/`` is not touched; this qualifies the new catalog on its own.

Trusted single-user host only: the forget grant is two environment claims set by the host process
that launches the server (``AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY`` and
``AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF``). It is not authentication. A model cannot pass them as
tool arguments.

usage: alpha_workflow.py <repo> <out_dir>
"""
from __future__ import annotations

import asyncio, hashlib, json, os, platform, subprocess, sys, tempfile, time
import importlib.metadata as md
from pathlib import Path

from mcp import Client, StdioServerParameters

repo, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
SERVER = repo / "integrations/agent-memory-mcp/server.py"
TOOLS = {"memory_remember", "memory_get", "memory_find", "memory_forget"}
GRANT_KEY, GRANT_REF = "AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY", "AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF"
transcript: list[dict] = []
checks: list[tuple[str, bool, str]] = []
git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout.strip()
CLEAN_BEFORE = git("status", "--porcelain", "--untracked-files=no") == ""
print("repo head", git("rev-parse", "HEAD"), "tracked tree clean:", CLEAN_BEFORE)


def body(result):
    return result.structured_content or {}


def record(step, tool, args, result, extra=None):
    entry = {"step": step, "request": {"tool": tool, "arguments": args},
             "response": {"is_error": result.is_error, "structured_content": result.structured_content,
                          "content": [c.model_dump(mode="json") for c in result.content]}}
    entry.update(extra or {})
    transcript.append(entry)


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))


def params(root, scope, tenant="tenant:alpha", grant=None):
    env = {"AGENT_MEMORY_MCP_ROOT": str(root), "AGENT_MEMORY_MCP_TENANT": tenant,
           "AGENT_MEMORY_MCP_ACTOR": "agent:alpha-harness", "AGENT_MEMORY_MCP_SCOPE": scope,
           "PATH": os.environ.get("PATH", "")}
    if grant:
        env[GRANT_KEY], env[GRANT_REF] = grant
    return StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)


def store_digest(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def live_server_pids():
    found = subprocess.run(["pgrep", "-f", str(SERVER)], capture_output=True, text=True)
    return [int(p) for p in found.stdout.split() if p.strip()]


async def call(client, step, tool, args, **extra):
    r = await client.call_tool(tool, args)
    record(step, tool, args, r, extra)
    return r


def contents(r):
    return [e["content"] for e in body(r).get("evidence", [])]


async def main():
    with tempfile.TemporaryDirectory(prefix="alpha-") as temp:
        root = Path(temp) / "agent-memory-store"
        k_kiln, t_kiln = "memory:studio:kiln_cone", "The studio kiln fires bisque at cone 04 on Fridays."
        k_glaze, t_glaze = "memory:studio:glaze_supplier", "Glaze materials come from Harbourline Ceramics."
        q_kiln, q_glaze = "What cone does the studio kiln fire bisque at?", "Where do the glaze materials come from?"

        # ---- A1: discovery, save, get, find (no grant)
        async with Client(params(root, "project:alpha")) as client:
            tools = (await client.list_tools()).tools
            transcript.append({"step": "A1 discovery", "tools": [{"name": t.name, "input_schema": t.input_schema} for t in tools]})
            check("A1 exactly the four alpha tools are advertised", {t.name for t in tools} == TOOLS, str({t.name for t in tools}))
            props = {t.name: set((t.input_schema or {}).get("properties", {})) for t in tools}
            check("A1 no tool exposes tenant/scope/actor/root or an approval/evidence/permanence parameter",
                  not any(p & {"tenant", "scope", "actor", "root", "approval", "approved", "evidence_ref", "evidence_refs", "permanent", "overrides"} for p in props.values()), str(props))
            check("A1 memory_forget takes exactly one argument: key", props.get("memory_forget") == {"key"}, str(props.get("memory_forget")))
            refs = {}
            for k, t in ((k_kiln, t_kiln), (k_glaze, t_glaze)):
                r = await call(client, "A1 save", "memory_remember", {"key": k, "text": t})
                check(f"A1 save committed: {k}", not r.is_error and body(r).get("committed") is True, repr(body(r))[:200])
                refs[k] = body(r).get("fact_ref")
            r = await call(client, "A1 get", "memory_get", {"key": k_kiln})
            ev = body(r).get("evidence", [])
            check("A1 get returns the exact text and fact_ref", body(r).get("lookup_status") == "found" and len(ev) == 1 and ev[0]["content"] == t_kiln and ev[0]["fact_ref"] == refs[k_kiln], repr(body(r))[:300])
            r = await call(client, "A1 find", "memory_find", {"question": q_kiln, "max_items": 5})
            check("A1 find surfaces the memory for a natural-language question", t_kiln in contents(r), repr(contents(r))[:300])
            pids1 = live_server_pids()

        # ---- A2: restart (fresh process)
        async with Client(params(root, "project:alpha")) as client:
            pids2 = live_server_pids()
            check("A2 a fresh server process (new pid)", pids2 and set(pids2).isdisjoint(pids1), f"{pids1} -> {pids2}")
            r = await call(client, "A2 get after restart", "memory_get", {"key": k_kiln})
            ev = body(r).get("evidence", [])
            check("A2 the same fact is retrieved after restart", ev and ev[0]["content"] == t_kiln and ev[0]["fact_ref"] == refs[k_kiln], repr(body(r))[:300])

            # ---- A3: forget without a host grant refuses and changes nothing
            before = store_digest(root)
            r = await call(client, "A3 forget without host grant", "memory_forget", {"key": k_kiln})
            b = body(r)
            check("A3 no grant: committed=false, status host_authorization_required, not permanent",
                  not r.is_error and b.get("committed") is False and b.get("status") == "host_authorization_required" and b.get("permanent") is False, repr(b)[:300])
            check("A3 no grant: every store file is byte-identical afterwards", store_digest(root) == before)
            r = await call(client, "A3 get after refused forget", "memory_get", {"key": k_kiln})
            check("A3 no grant: the memory is still found with its fact_ref", body(r).get("lookup_status") == "found" and body(r)["evidence"][0]["fact_ref"] == refs[k_kiln], repr(body(r))[:300])

        # ---- A4: a grant for one key cannot be applied to another
        async with Client(params(root, "project:alpha", grant=(k_glaze, "operator-record:alpha-a4"))) as client:
            before = store_digest(root)
            r = await call(client, "A4 forget other key under a grant for glaze", "memory_forget", {"key": k_kiln}, grant_key=k_glaze)
            b = body(r)
            check("A4 wrong key: committed=false, host_authorization_required", not r.is_error and b.get("committed") is False and b.get("status") == "host_authorization_required", repr(b)[:300])
            check("A4 wrong key: every store file is byte-identical afterwards", store_digest(root) == before)
            r = await call(client, "A4 get kiln after wrong-key attempt", "memory_get", {"key": k_kiln})
            check("A4 wrong key: the kiln memory is still found", body(r).get("lookup_status") == "found", repr(body(r))[:200])
            r = await call(client, "A4 get glaze (granted key, not forgotten)", "memory_get", {"key": k_glaze})
            check("A4 the granted key itself is untouched until forget is called on it", body(r).get("lookup_status") == "found", repr(body(r))[:200])

        # ---- A5: authorized reversible forgetting through the governed public facade
        async with Client(params(root, "project:alpha", grant=(k_kiln, "operator-record:alpha-a5"))) as client:
            r = await call(client, "A5 authorized forget", "memory_forget", {"key": k_kiln}, grant_key=k_kiln)
            b = body(r)
            check("A5 authorized: committed=true, status forgotten, governed operation pruning with a receipt, not permanent",
                  not r.is_error and b.get("committed") is True and b.get("status") == "forgotten" and b.get("operation") == "pruning"
                  and isinstance(b.get("receipt_id"), str) and b.get("permanent") is False and b.get("refusal") is None, repr(b)[:300])
            transcript.append({"step": "A5 facade outcome", "outcome": b.get("outcome")})
            r = await call(client, "A5 get after forget", "memory_get", {"key": k_kiln})
            check("A5 get: the forgotten key is not_found_or_unavailable, no content", body(r).get("lookup_status") == "not_found_or_unavailable" and body(r).get("evidence") == [] and "cone 04" not in json.dumps(body(r)), repr(body(r))[:300])
            r = await call(client, "A5 find after forget", "memory_find", {"question": q_kiln, "max_items": 5})
            check("A5 find: the forgotten content is not delivered", "cone 04" not in json.dumps(body(r)), repr(contents(r))[:300])
            r = await call(client, "A5 forget again (already forgotten)", "memory_forget", {"key": k_kiln})
            check("A5 forgetting an already forgotten key does not commit again", body(r).get("committed") is False, repr(body(r))[:200])
            r = await call(client, "A5 other memory unaffected", "memory_get", {"key": k_glaze})
            check("A5 the other memory in the scope is unaffected", body(r).get("lookup_status") == "found" and body(r)["evidence"][0]["content"] == t_glaze, repr(body(r))[:200])

        # ---- A6: after restart the forgotten content stays invisible to ordinary retrieval
        async with Client(params(root, "project:alpha")) as client:
            r = await call(client, "A6 get after restart", "memory_get", {"key": k_kiln})
            check("A6 after restart: forgotten key not_found_or_unavailable, no content", body(r).get("lookup_status") == "not_found_or_unavailable" and "cone 04" not in json.dumps(body(r)), repr(body(r))[:300])
            r = await call(client, "A6 find after restart", "memory_find", {"question": q_kiln, "max_items": 8})
            check("A6 after restart: find never delivers the forgotten content", "cone 04" not in json.dumps(body(r)), repr(contents(r))[:300])
            r = await call(client, "A6 find other memory after restart", "memory_find", {"question": q_glaze, "max_items": 5})
            check("A6 after restart: the remaining memory is still findable", t_glaze in contents(r), repr(contents(r))[:300])

        # ---- A7: tenant and project isolation, including forget
        async with Client(params(root, "project:other-team", grant=(k_glaze, "operator-record:alpha-a7"))) as client:
            r = await call(client, "A7 other scope get", "memory_get", {"key": k_glaze}, scope="project:other-team")
            check("A7 other project: cannot read the key", body(r).get("lookup_status") == "not_found_or_unavailable" and "Harbourline" not in json.dumps(body(r)), repr(body(r))[:300])
            r = await call(client, "A7 other scope find", "memory_find", {"question": q_glaze, "max_items": 5}, scope="project:other-team")
            check("A7 other project: cannot find the content", body(r).get("evidence") == [] and "Harbourline" not in json.dumps(body(r)), repr(body(r))[:300])
            r = await call(client, "A7 other scope forget with a grant for the key", "memory_forget", {"key": k_glaze}, scope="project:other-team")
            check("A7 other project: a granted forget of another project's key does not commit", body(r).get("committed") is False, repr(body(r))[:300])
        async with Client(params(root, "project:alpha", tenant="tenant:stranger", grant=(k_glaze, "operator-record:alpha-a7t"))) as client:
            r = await call(client, "A7 other tenant get", "memory_get", {"key": k_glaze}, tenant="tenant:stranger")
            raw = json.dumps([c.model_dump(mode="json") for c in r.content])
            check("A7 other tenant: cannot read the key (error or empty, never the content)", "Harbourline" not in raw and (r.is_error or body(r).get("evidence") == []), raw[:300])
            r = await call(client, "A7 other tenant forget with a grant", "memory_forget", {"key": k_glaze}, tenant="tenant:stranger")
            raw = json.dumps([c.model_dump(mode="json") for c in r.content])
            check("A7 other tenant: a granted forget does not commit (error or committed=false)", r.is_error or body(r).get("committed") is False, raw[:300])
        async with Client(params(root, "project:alpha")) as client:
            r = await call(client, "A7 owner still has the glaze memory", "memory_get", {"key": k_glaze})
            check("A7 the owning project still has its memory after the foreign forget attempts", body(r).get("lookup_status") == "found" and body(r)["evidence"][0]["content"] == t_glaze, repr(body(r))[:200])

        time.sleep(0.5)
        check("final: no server process left running", live_server_pids() == [], str(live_server_pids()))

    report = {
        "kind": "internal_alpha_stage_a_four_tool_real_stdio_mcp_workflow",
        "trust_boundary": "trusted single-user host; forget grant = host environment claims, not authentication",
        "repo_head": git("rev-parse", "HEAD"),
        "server_blob": git("hash-object", str(SERVER)),
        "bridge_blob": git("hash-object", str(repo / "integrations/agent-memory-mcp/bridge.py")),
        "python": sys.version, "platform": platform.platform(),
        "packages": {n: md.version(n) for n in ("mcp", "agent-memory-reference", "pydantic", "anyio")},
        "checks": [{"name": n, "ok": ok, "detail": d if not ok else ""} for n, ok, d in checks],
        "passed": sum(1 for _, ok, _ in checks if ok), "total": len(checks),
        "tracked_tree_clean_before": CLEAN_BEFORE,
        "tracked_tree_clean_after": git("status", "--porcelain", "--untracked-files=no") == "",
        "transcript": transcript,
    }
    target = out / f"alpha-workflow-{report['repo_head'][:8]}.json"
    target.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print("transcript", target.name, "sha256", hashlib.sha256(target.read_bytes()).hexdigest())
    print(f"\n{report['passed']}/{report['total']} checks passed")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
