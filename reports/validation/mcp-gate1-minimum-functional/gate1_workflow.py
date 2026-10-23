"""Gate 1 proof: the Agent Memory MCP server as a genuine stdio subprocess, driven by the official
MCP Python client, against a fresh isolated SQLite store. Records every request and response.

usage: gate1_workflow.py <repo> <out_dir>
"""
from __future__ import annotations

import asyncio, json, os, platform, sqlite3, subprocess, sys, tempfile, time
import importlib.metadata as md
from pathlib import Path

from mcp import Client, StdioServerParameters

repo, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
out.mkdir(parents=True, exist_ok=True)
SERVER = repo / "integrations/agent-memory-mcp/server.py"
transcript: list[dict] = []
checks: list[tuple[str, bool, str]] = []


def body(result):
    return result.structured_content


def record(step, tool, args, result, extra=None):
    entry = {"step": step, "request": {"tool": tool, "arguments": args},
             "response": {"is_error": result.is_error, "structured_content": result.structured_content,
                          "content": [c.model_dump(mode="json") for c in result.content]}}
    if extra:
        entry.update(extra)
    transcript.append(entry)
    return entry


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))


def params(root, scope, tenant="tenant:gate1", actor="agent:gate1-harness"):
    env = {"AGENT_MEMORY_MCP_ROOT": str(root), "AGENT_MEMORY_MCP_TENANT": tenant,
           "AGENT_MEMORY_MCP_ACTOR": actor, "AGENT_MEMORY_MCP_SCOPE": scope,
           "PATH": os.environ.get("PATH", "")}
    return StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)


def live_server_pids():
    out_ = subprocess.run(["pgrep", "-f", str(SERVER)], capture_output=True, text=True)
    return [int(p) for p in out_.stdout.split() if p.strip()]


def sqlite_evidence(root: Path) -> dict:
    files = sorted(p for p in root.rglob("*") if p.is_file())
    info = {"files": [{"path": str(p.relative_to(root)), "bytes": p.stat().st_size} for p in files], "tables": {}}
    for db in [p for p in files if p.suffix in (".sqlite", ".db", ".sqlite3")]:
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            tables = [r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]
            counts = {}
            for t in tables:
                counts[t] = con.execute(f'select count(*) from "{t}"').fetchone()[0]
            info["tables"][str(db.relative_to(root))] = counts
            con.close()
        except Exception as exc:  # evidence only; never part of the product path
            info["tables"][str(db.relative_to(root))] = f"unreadable: {type(exc).__name__}"
    return info


async def main():
    with tempfile.TemporaryDirectory(prefix="gate1-") as temp:
        root = Path(temp) / "agent-memory-store"
        key, text = "memory:owner:preferred_editor", "The owner writes Python in Neovim with the pyright language server."
        question = "Which editor and language server does the owner use for Python?"

        # ---- session 1: handshake, discovery, save, get, find
        async with Client(params(root, "project:gate1")) as client:
            init = client.initialize_result if hasattr(client, "initialize_result") else None
            server_info = getattr(init, "server_info", None) or getattr(init, "serverInfo", None)
            protocol = getattr(init, "protocol_version", None) or getattr(init, "protocolVersion", None)
            transcript.append({"step": "1 handshake", "initialize_result": {
                "server": server_info.model_dump(mode="json") if server_info is not None else repr(init)[:300],
                "protocol_version": protocol}})
            tools = await client.list_tools()
            names = {t.name for t in tools.tools}
            transcript.append({"step": "1 discovery", "tools": [
                {"name": t.name, "input_schema": t.input_schema, "output_schema": getattr(t, "output_schema", None)} for t in tools.tools]})
            check("1 handshake + three tools discovered", names == {"memory_remember", "memory_get", "memory_find"}, str(names))
            pids1 = live_server_pids(); check("1 server runs as a child process", len(pids1) >= 1, str(pids1))
            schemas_ok = all(not ({"tenant", "scope", "actor", "root"} & set((t.input_schema or {}).get("properties", {}))) for t in tools.tools)
            check("1 no tool exposes tenant/scope/actor/root parameters", schemas_ok)

            r = await client.call_tool("memory_remember", {"key": key, "text": text}); record("2 save", "memory_remember", {"key": key, "text": text}, r)
            check("2 memory_remember committed=true", not r.is_error and body(r)["committed"] is True, repr(body(r))[:200])
            fact_ref = body(r)["fact_ref"] if body(r) else None

            r = await client.call_tool("memory_get", {"key": key}); record("3 exact get", "memory_get", {"key": key}, r)
            ev = (body(r) or {}).get("evidence", [])
            check("3 memory_get returns the exact memory by key", not r.is_error and body(r)["lookup_status"] == "found" and len(ev) == 1 and ev[0]["content"] == text and ev[0]["memory_ref"] == key and ev[0]["fact_ref"] == fact_ref, repr(body(r))[:300])
            check("3 evidence is labelled untrusted and no answer generated", ev and ev[0]["trust"] == "untrusted_memory_text" and body(r)["answer_generated"] is False)

            r = await client.call_tool("memory_find", {"question": question, "max_items": 5}); record("4 find", "memory_find", {"question": question, "max_items": 5}, r)
            found = [e for e in (body(r) or {}).get("evidence", []) if e["content"] == text]
            check("4 memory_find surfaces the memory for a natural-language question", not r.is_error and len(found) == 1, repr(body(r))[:300])
        time.sleep(0.5)
        pids_after = live_server_pids()
        transcript.append({"step": "5 terminate", "server_pids_during_session_1": pids1, "server_pids_after_close": pids_after})
        check("5 server process terminated on client close", pids_after == [], str(pids_after))
        store_after_1 = sqlite_evidence(root)
        transcript.append({"step": "5 sqlite store after session 1", **store_after_1})
        check("5 SQLite store exists on disk after the process ended", any(f["path"].endswith((".sqlite", ".sqlite3", ".db")) and f["bytes"] > 0 for f in store_after_1["files"]), str(store_after_1["files"])[:300])

        # ---- session 2: fresh process, same store
        async with Client(params(root, "project:gate1")) as client:
            pids2 = live_server_pids()
            check("6 fresh server process launched (new pid)", pids2 and set(pids2).isdisjoint(set(pids1)), f"{pids1} -> {pids2}")
            r = await client.call_tool("memory_get", {"key": key}); record("7 get after restart", "memory_get", {"key": key}, r, {"server_pids": pids2})
            ev = (body(r) or {}).get("evidence", [])
            check("7 original memory retrieved by a fresh process", not r.is_error and body(r)["lookup_status"] == "found" and len(ev) == 1 and ev[0]["content"] == text and ev[0]["fact_ref"] == fact_ref, repr(body(r))[:300])

            # 8a wrong key (near miss) in the same scope
            r = await client.call_tool("memory_get", {"key": "memory:owner:preferred_editors"}); record("8 wrong key", "memory_get", {"key": "memory:owner:preferred_editors"}, r)
            check("8 wrong (near-miss) key refused: not_found_or_unavailable, no content", not r.is_error and body(r)["lookup_status"] == "not_found_or_unavailable" and body(r)["evidence"] == [] and "Neovim" not in json.dumps(body(r)), repr(body(r))[:300])
            r = await client.call_tool("memory_get", {"key": "memory:never-written"}); record("8 absent key", "memory_get", {"key": "memory:never-written"}, r)
            check("8 never-written key refused: not_found_or_unavailable", not r.is_error and body(r)["lookup_status"] == "not_found_or_unavailable" and body(r)["evidence"] == [])

            # 8b conflicting key: a second explicit write under the same key with a different value
            conflict_text = "The owner writes Python in VS Code."
            r = await client.call_tool("memory_remember", {"key": key, "text": conflict_text}); record("8 conflicting write", "memory_remember", {"key": key, "text": conflict_text}, r)
            second = body(r) or {}
            r2 = await client.call_tool("memory_get", {"key": key}); record("8 get after conflicting write", "memory_get", {"key": key}, r2)
            g = body(r2) or {}
            rf = await client.call_tool("memory_find", {"question": "Which editor does the owner use for Python?", "max_items": 5}); record("8 find after conflicting write", "memory_find", {"question": "Which editor does the owner use for Python?", "max_items": 5}, rf)
            found_texts = [e["content"] for e in (body(rf) or {}).get("evidence", [])]
            if second.get("committed") is True and g.get("lookup_status") == "found":
                # real runtime semantics: the second write moves the key's head; the earlier fact
                # stays current and findable, so the bridge must mark which value is the head
                check("8 conflicting key: get serves exactly the head (latest write) and reports key_versions=2 with earlier versions recallable",
                      not r2.is_error and len(g["evidence"]) == 1 and g["evidence"][0]["content"] == conflict_text and g["evidence"][0]["latest_for_key"] is True and g.get("key_versions") == 2 and g.get("earlier_versions_remain_recallable") is True, repr(g)[:300])
                fe = {e["content"]: e for e in (body(rf) or {}).get("evidence", [])}
                check("8 conflicting key: find marks the head latest_for_key=true, the earlier value latest_for_key=false, and lists the key as conflicting",
                      fe.get(conflict_text, {}).get("latest_for_key") is True and (text not in fe or fe[text].get("latest_for_key") is False) and (text not in fe or key in (body(rf) or {}).get("conflicting_keys", [])), repr(fe)[:300])
            elif second.get("committed") is True:
                check("8 conflicting key: two current facts under one key -> ambiguous_multiple_versions, no content",
                      not r2.is_error and g.get("lookup_status") == "ambiguous_multiple_versions" and g.get("evidence") == [], repr(g)[:300])
            else:
                check("8 conflicting key: second write refused with a visible refusal and get still returns the original",
                      second.get("refusal") is not None and g.get("lookup_status") == "found" and g["evidence"][0]["content"] == text, repr(second)[:200] + repr(g)[:200])
            transcript.append({"step": "8 conflicting-key disposition", "second_write_committed": second.get("committed"), "lookup_status_after": g.get("lookup_status"), "served_after": [e["content"] for e in g.get("evidence", [])], "find_after": found_texts})

            # 9 expected failures inside a configured server are MCP tool errors, not success
            for name, tool, args in (("9 empty key", "memory_get", {"key": "   "}),
                                     ("9 max_items out of range", "memory_find", {"question": "editor", "max_items": 10000}),
                                     ("9 oversize text", "memory_remember", {"key": "memory:big", "text": "x" * 4001})):
                r = await client.call_tool(tool, args); record(name, tool, {k: (v if len(str(v)) < 80 else f"<{len(str(v))} chars>") for k, v in args.items()}, r)
                check(f"{name} -> MCP tool error (is_error=True, no structured success)", r.is_error and r.structured_content is None and "Traceback" not in json.dumps([c.model_dump(mode="json") for c in r.content]), repr(r.content)[:200])
            try:
                r = await client.call_tool("memory_delete_everything", {}); record("9 unknown tool", "memory_delete_everything", {}, r)
                check("9 unknown tool name -> MCP error", r.is_error, repr(r.content)[:200])
            except Exception as exc:
                transcript.append({"step": "9 unknown tool", "request": {"tool": "memory_delete_everything"}, "response": {"exception": type(exc).__name__, "message": str(exc)[:200]}})
                check("9 unknown tool name -> MCP error", True, type(exc).__name__)

        # ---- session 3: another trusted scope on the same store and tenant
        async with Client(params(root, "project:other-team")) as client:
            r = await client.call_tool("memory_get", {"key": key}); record("8 cross-scope get", "memory_get", {"key": key}, r, {"scope": "project:other-team"})
            check("8 other scope cannot read the key: not_found_or_unavailable, no content", not r.is_error and body(r)["lookup_status"] == "not_found_or_unavailable" and body(r)["evidence"] == [] and "Neovim" not in json.dumps(body(r)), repr(body(r))[:300])
            r = await client.call_tool("memory_find", {"question": question, "max_items": 5}); record("8 cross-scope find", "memory_find", {"question": question, "max_items": 5}, r, {"scope": "project:other-team"})
            check("8 other scope cannot find the content: empty evidence", not r.is_error and body(r)["evidence"] == [] and "Neovim" not in json.dumps(body(r)), repr(body(r))[:300])
        # ---- session 4: another tenant on the same store root
        async with Client(params(root, "project:gate1", tenant="tenant:stranger")) as client:
            r = await client.call_tool("memory_get", {"key": key}); record("8 cross-tenant get", "memory_get", {"key": key}, r, {"tenant": "tenant:stranger"})
            check("8 other tenant cannot read the key (error or empty, never the content)", "Neovim" not in json.dumps([c.model_dump(mode="json") for c in r.content]) and (r.is_error or body(r)["evidence"] == []), repr(r.content)[:300])

        # ---- 9 misconfigured host: missing environment -> tool error, not success
        bad = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env={"PATH": os.environ.get("PATH", "")})
        async with Client(bad) as client:
            r = await client.call_tool("memory_find", {"question": "editor"}); record("9 missing host configuration", "memory_find", {"question": "editor"}, r, {"env": "none"})
            check("9 missing host configuration -> MCP tool error naming host configuration, no traceback", r.is_error and "host configuration" in json.dumps([c.model_dump(mode="json") for c in r.content]).lower() and "Traceback" not in json.dumps([c.model_dump(mode="json") for c in r.content]), repr(r.content)[:200])

        store_final = sqlite_evidence(root)
        transcript.append({"step": "final sqlite store", **store_final})
        time.sleep(0.5)
        check("final: no server process left running", live_server_pids() == [], str(live_server_pids()))

    report = {
        "kind": "gate1_minimum_functional_product_real_stdio_mcp_workflow",
        "repo_head": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
        "server_blob": subprocess.check_output(["git", "-C", str(repo), "hash-object", str(SERVER)], text=True).strip(),
        "bridge_blob": subprocess.check_output(["git", "-C", str(repo), "hash-object", str(repo / "integrations/agent-memory-mcp/bridge.py")], text=True).strip(),
        "python": sys.version, "platform": platform.platform(),
        "packages": {n: md.version(n) for n in ("mcp", "agent-memory-reference", "pydantic", "anyio")},
        "checks": [{"name": n, "ok": ok, "detail": d if not ok else ""} for n, ok, d in checks],
        "passed": sum(1 for _, ok, _ in checks if ok), "total": len(checks),
        "transcript": transcript,
    }
    (out / "gate1-workflow.json").write_text(json.dumps(report, indent=2, sort_keys=False, default=str) + "\n")
    print(f"\n{report['passed']}/{report['total']} checks passed")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
