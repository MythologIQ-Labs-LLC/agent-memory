"""Installed-package consumer lifecycle and negative tests. Public facade only; no repository access.
Every step asserts its required outcome (negatives assert the refusal); a failed step is recorded and the process exits 1.
Usage: python consumer_lifecycle.py <root_dir> <out_json>"""
import json, os, shutil, sqlite3, subprocess, sys, traceback
from pathlib import Path
import agentmem_ref
from agentmem_ref import AgentMemory, policy
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.runtime.restart_runtime import RuntimeRecoveryError

ROOT = Path(sys.argv[1]); OUT = Path(sys.argv[2]); ROOT.mkdir(parents=True, exist_ok=True)
TENANT, SCOPE, ACTOR = "tenant:consumer", "project:alpha", "agent:consumer"
M1, M2 = "memory:release-branch", "memory:deploy-window"
R = {"python": sys.version.split()[0], "executable": sys.executable, "agentmem_ref": agentmem_ref.__file__, "cwd": os.getcwd(), "steps": []}

def step(name, fn):
    try:
        out = fn(); R["steps"].append({"step": name, "ok": True, "result": out}); print(f"OK   {name}: {json.dumps(out)[:300]}")
    except Exception as exc:  # record, never fabricate
        R["steps"].append({"step": name, "ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-800:]}); print(f"FAIL {name}: {type(exc).__name__}: {exc}")

def evidence(target):
    skill = pm.SkillArtifact(skill_id="skill:consumer-correction", version=1, purpose="correct retained memory", scope=SCOPE,
                             isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
                             procedure_markdown="# verify\nConfirm the correction against the current source.",
                             provenance_refs=("evidence:consumer-source",))
    return pm.evidence_for(skill)

def binding(m):
    return (m.posture().get("posture") or {}).get("durable_state", {}).get("configuration_binding_scheme")

def opn(root=ROOT, tenant=TENANT, scope=SCOPE):
    return AgentMemory.open(root, tenant=tenant, actor_id=ACTOR, scope=scope, purpose="consumer qualification")

state = {}
def s1():
    m = opn(); state["m"] = m
    r1 = m.remember(M1, "release branch release"); r2 = m.remember(M2, "deploy window is Tuesday")
    assert r1["committed"] and r2["committed"]; state["f1"], state["f2"] = r1["fact_uuid"], r2["fact_uuid"]
    rec = m.recall("release branch", logical_memory_refs=(M1,)); assert state["f1"] in rec["admitted"]
    assert m.contract_version == "1.8.0" and binding(m) == "sqlite_transaction" and m.history(M1)["history"]["state_version"] == 1
    return {"contract_version": m.contract_version, "stage": r1["stage"], "recall_stage": rec.get("stage"), "admitted": len(rec["admitted"]), "returned": len(rec.get("returned", [])),
            "history_version": m.history(M1)["history"]["state_version"], "posture_stage": m.posture().get("stage"), "binding": binding(m)}
step("open_remember_recall_history_posture", s1)
def s2():
    m = state["m"]; parked = m.correct(M1, "release branch main"); assert not parked["committed"]
    fixed = m.correct(M1, "release branch main", evidence=evidence(M1)); assert fixed["committed"]; state["f1b"] = fixed["fact_uuid"]
    rec = m.recall("release branch main", logical_memory_refs=(M1,))
    assert state["f1b"] in rec["admitted"] and state["f1"] not in rec["admitted"]
    return {"parked_outcome": parked["outcome"], "corrected_outcome": fixed["outcome"], "history_version": m.history(M1)["history"]["state_version"]}
step("correct_parks_without_evidence_commits_with_qualified_evidence", s2)
def s3():
    m = state["m"]; f = m.forget(M1, evidence=evidence(M1)); assert f["committed"]
    h = m.history(M1)["history"]; rec = m.recall("release branch main", logical_memory_refs=(M1,))
    assert h["tombstoned"] and h["current_fact_uuid"] is None and state["f1b"] not in rec["admitted"]
    leaked = state["f1b"] in json.dumps(m.history(M1)) or state["f1"] in json.dumps(m.history(M1))
    return {"forget_outcome": f["outcome"], "tombstoned": h["tombstoned"], "public_events": len(h["events"]), "deleted_ids_in_public_history": leaked, "admitted_after_forget": rec["admitted"]}
step("forget_reversible_tombstones_and_withholds", s3)
def s4():
    m = state["m"]; r = m.forget(M2, permanent=True); assert not r["committed"] and r["outcome"] in (policy.REQUIRE_REVIEW, policy.REQUIRE_EXTERNAL_VERIFICATION, policy.BLOCK)
    assert m.recall("deploy window", logical_memory_refs=(M2,))["admitted"] == [state["f2"]]
    return {"outcome": r["outcome"], "m2_still_current": True}
step("permanent_forget_without_evidence_refused", s4)
def s5():
    state["m"].close(); assert state["m"].closed
    m = opn(); state["m"] = m
    rec = m.recall("deploy window", logical_memory_refs=(M2,)); h = m.history(M1)["history"]
    rec1 = m.recall("release branch", logical_memory_refs=(M1,))
    assert state["f2"] in rec["admitted"] and h["tombstoned"] and rec1["admitted"] == [] and binding(m) == "sqlite_transaction"
    return {"m2_admitted_after_reopen": state["f2"] in rec["admitted"], "m1_tombstoned_after_reopen": h["tombstoned"], "m1_admitted_after_reopen": rec1["admitted"], "binding": binding(m)}
step("close_reopen_same_process", s5)
def s6():
    state["m"].close()
    code = f"""
import json; from agentmem_ref import AgentMemory
with AgentMemory.open({str(ROOT)!r}, tenant={TENANT!r}, actor_id={ACTOR!r}, scope={SCOPE!r}, purpose='restart') as m:
    print(json.dumps({{'m2': m.recall('deploy window', logical_memory_refs=({M2!r},))['admitted'], 'm1': m.recall('release branch', logical_memory_refs=({M1!r},))['admitted'],
                      'm1_tombstoned': m.history({M1!r})['history']['tombstoned'], 'posture': m.posture().get('stage'), 'binding': (m.posture().get('posture') or {{}}).get('durable_state', {{}}).get('configuration_binding_scheme')}}))
"""
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd="/tmp", env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"}, timeout=120)
    assert out.returncode == 0, out.stderr[-500:]
    d = json.loads(out.stdout.strip().splitlines()[-1]); assert d["m2"] == [state["f2"]] and d["m1"] == [] and d["m1_tombstoned"] and d["binding"] == "sqlite_transaction"
    return d
step("process_restart_recall_and_deletion_persist", s6)
def s7():
    # re-create the deleted logical id as a fresh generation; old content must not reappear
    m = opn(); state["m"] = m; r = m.remember(M1, "release branch v2 after deletion")
    rec = m.recall("release branch", logical_memory_refs=(M1,)); h = m.history(M1)["history"]
    old_reappears = state["f1"] in rec["admitted"] or state["f1b"] in rec["admitted"] or state["f1"] in rec.get("candidates", []) or state["f1b"] in rec.get("candidates", [])
    assert r["committed"] and r["fact_uuid"] in rec["admitted"] and not old_reappears and h["state_version"] == 1
    return {"recreate_committed": r["committed"], "new_admitted": r["fact_uuid"] in rec["admitted"], "old_generation_reappears": old_reappears, "history_version": h["state_version"], "tombstoned_flag_now": h["tombstoned"]}
step("recreate_deleted_id_old_content_does_not_reappear", s7)
def s8():
    state["m"].close()
    try:
        m = opn(tenant="tenant:other")
    except RuntimeRecoveryError as exc:
        return {"opened": False, "refused": f"RuntimeRecoveryError: {str(exc)[:160]}"}
    m.close()
    raise AssertionError("cross-tenant open of an existing state must be refused")
step("cross_tenant_open_same_state", s8)
def s9():
    m = opn(scope="project:beta"); state["m"] = m
    rec = m.recall("deploy window", logical_memory_refs=(M2,))
    c = m.correct(M2, "deploy window is Friday", evidence=evidence(M2))
    h = m.history(M2)
    assert rec["admitted"] == [] and not rec.get("candidates") and not c["committed"] and h["history"].get("current_fact_uuid") is None
    res = {"recall_stage": rec.get("stage"), "admitted": rec["admitted"], "candidates": rec.get("candidates"), "correct_committed": c["committed"], "correct_outcome": c.get("outcome"), "correct_refusal": str(c.get("refusal") or c.get("reason") or "")[:120], "history_visible_version": h["history"].get("state_version"), "history_current": h["history"].get("current_fact_uuid")}
    m.close(); m = opn(); state["m"] = m
    res["alpha_m2_still"] = m.recall("deploy window", logical_memory_refs=(M2,))["admitted"]; res["alpha_m2_version"] = m.history(M2)["history"]["state_version"]; m.close()
    assert res["alpha_m2_still"] == [state["f2"]] and res["alpha_m2_version"] == 1
    return res
step("cross_project_same_tenant_isolation", s9)
def s10():
    out = {}
    a = ROOT.parent / "neg-binding-only"; shutil.rmtree(a, ignore_errors=True); a.mkdir(); (a / "configuration-binding.json").write_text("{}\n")
    try: opn(a).close(); out["binding_only"] = "OPENED (unexpected)"
    except RuntimeRecoveryError as exc: out["binding_only"] = f"refused: {str(exc)[:120]}"
    out["binding_only_sqlite_created"] = (a / "agent-memory.sqlite3").exists()
    assert str(out["binding_only"]).startswith("refused") and not out["binding_only_sqlite_created"], out
    b = ROOT.parent / "neg-no-config"; shutil.rmtree(b, ignore_errors=True); shutil.copytree(ROOT, b); (b / "runtime-config.json").unlink()
    try: m = opn(b); out["config_removed"] = {"opened": True, "m2": m.recall("deploy window", logical_memory_refs=(M2,))["admitted"], "posture": m.posture().get("stage"), "binding": m.posture().get("configuration_binding_scheme")}; m.close()
    except Exception as exc: out["config_removed"] = f"refused: {type(exc).__name__}: {str(exc)[:120]}"
    import hashlib
    same = hashlib.sha256((ROOT / "runtime-config.json").read_bytes()).digest() == hashlib.sha256((b / "runtime-config.json").read_bytes()).digest()
    out["config_regenerated_identical"] = same
    assert isinstance(out["config_removed"], dict) and out["config_removed"]["m2"] == [state["f2"]] and same, out
    c = ROOT.parent / "neg-truncated-db"; shutil.rmtree(c, ignore_errors=True); shutil.copytree(ROOT, c); db = c / "agent-memory.sqlite3"
    with open(db, "r+b") as fh: fh.truncate(db.stat().st_size // 2)
    try: m = opn(c); out["truncated_db"] = {"opened": True, "m2": m.recall("deploy window", logical_memory_refs=(M2,))["admitted"]}; m.close()
    except Exception as exc: out["truncated_db"] = f"refused: {type(exc).__name__}: {str(exc)[:120]}"
    assert str(out["truncated_db"]).startswith("refused"), out
    d = ROOT.parent / "neg-witness-tampered"; shutil.rmtree(d, ignore_errors=True); shutil.copytree(ROOT, d); w = d / "generation-witness.json"
    if w.exists():
        j = json.loads(w.read_text()); j["tampered"] = True; w.write_text(json.dumps(j))
        try: m = opn(d); out["witness_tampered"] = {"opened": True, "posture": m.posture().get("stage"), "binding": m.posture().get("configuration_binding_scheme")}; m.close()
        except Exception as exc: out["witness_tampered"] = f"refused: {type(exc).__name__}: {str(exc)[:120]}"
    e = ROOT.parent / "neg-row-tampered"; shutil.rmtree(e, ignore_errors=True); shutil.copytree(ROOT, e)
    con = sqlite3.connect(e / "agent-memory.sqlite3"); tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    out["tables"] = tables[:12]
    tgt = next((t for t in tables if "fact" in t.lower()), None)
    if tgt:
        cols = [r[1] for r in con.execute(f"pragma table_info({tgt})")]; txt = next((c for c in cols if c in ("fact_text", "text", "content")), None)
        if txt:
            con.execute(f"update {tgt} set {txt}='TAMPERED deploy window is Monday' where {txt} like '%deploy window%'"); con.commit()
            out["row_tampered_rows"] = con.total_changes
    con.close()
    try: m = opn(e); rec = m.recall("deploy window", logical_memory_refs=(M2,)); out["row_tampered"] = {"opened": True, "admitted": rec["admitted"], "posture": m.posture().get("stage")}; m.close()
    except Exception as exc: out["row_tampered"] = f"refused: {type(exc).__name__}: {str(exc)[:160]}"
    assert out.get("row_tampered_rows") == 1 and str(out["row_tampered"]).startswith("refused"), out
    # witness file edits are recorded only: by #821 design the legacy file is not consulted while the binding table exists
    return out
step("interrupted_recovery_and_integrity_negatives", s10)
def s11():
    import importlib.resources
    prof = json.loads((importlib.resources.files("agentmem_ref") / "_profiles" / "rc1-local.json").read_text())
    from agentmem_ref import receipts
    src = getattr(receipts, "_SOURCE_SCHEMAS", None)
    res = {"profile_id": prof["runtime"]["profile_id"], "source_schemas_dir_exists": bool(src and Path(str(src)).exists()), "packaged_schemas": len(list((Path(agentmem_ref.__file__).parent / "_schemas").glob("*.json"))), "contract_version": __import__("agentmem_ref.api.contract", fromlist=["x"]).CONTRACT_VERSION}
    assert res["profile_id"] == "rc1-local-sqlite-composition" and res["packaged_schemas"] >= 70 and res["contract_version"] == "1.8.0", res
    return res
step("package_resources", s11)
m = opn(); rec = m.recall("deploy window", logical_memory_refs=(M2,)); R["final_state_ok"] = rec["admitted"] == [state.get("f2")]; m.close()
OUT.write_text(json.dumps(R, indent=1)); failed = [s["step"] for s in R["steps"] if not s["ok"]]
print("final_state_ok:", R["final_state_ok"], "| steps failed:", failed)
sys.exit(0 if R["final_state_ok"] and not failed else 1)
