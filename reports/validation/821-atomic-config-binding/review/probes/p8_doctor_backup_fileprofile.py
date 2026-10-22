"""P8: doctor / posture output (success and failure), doctor writes nothing, backup_to restores,
and the file-checkpoint profile (RestartSafeRuntime + ConfigBoundRestartRuntime) is unchanged."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _common as C  # noqa: E402

REF = C.ref()
from agentmem_ref.runtime import doctor  # noqa: E402


def ds(report):
    keys = ("status", "configuration_binding_present", "configuration_binding_scheme")
    return {k: report["durable_state"].get(k) for k in keys} | {"recovery": report["recovery"].get("status"),
                                                                 "reason": report["recovery"].get("failure_reason") or report["recovery"].get("reason")}


def main():
    root = C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:x", "The deploy window is Thursday.")
    before = C.tables_digest(root), sorted(p.name for p in root.iterdir() if "sqlite3-" not in p.name)
    posture = m.posture()
    print("posture() durable_state:", json.dumps({k: posture["posture"]["durable_state"].get(k) for k in
                                                  ("status", "configuration_binding_present", "configuration_binding_scheme")}))
    m.close()
    rep = doctor.diagnose(root / "runtime-config.json", state_dir=root)
    print("doctor ok:", ds(rep))
    print("doctor/posture wrote nothing (tables + non-WAL files):", (C.tables_digest(root), sorted(p.name for p in root.iterdir() if "sqlite3-" not in p.name)) == before)
    if C.has_row_protocol():
        c = sqlite3.connect(C.db(root)); c.execute(f"UPDATE {C.TABLE} SET payload_json='{{bad'"); c.commit(); c.close()
        rep = doctor.diagnose(root / "runtime-config.json", state_dir=root)
        print("doctor on tampered row:", ds(rep), "| full recovery block:", json.dumps(rep["recovery"])[:300])

    # backup_to
    root = C.tmp() / "s"
    m = C.open_mem(root)
    m.remember("memory:x", "The deploy window is Thursday.")
    dest = C.tmp() / "restored"
    m.runtime.durable_runtime.base.backup_to(dest / "agent-memory.sqlite3")
    m.close()
    shutil.copy2(root / "runtime-config.json", dest / "runtime-config.json")
    print("backup_to (db only) + config, open:", C.try_open(dest))

    # file-checkpoint profile
    from agentmem_ref.runtime.configured_restart import ConfigBoundRestartRuntime
    from agentmem_ref.runtime.runtime_behavior import validate_runtime_behavior_contract
    value = doctor.load_configuration_value(root / "runtime-config.json")
    plan = validate_runtime_behavior_contract(value, qualification_bindings=doctor.load_qualification_bindings(None))
    froot = C.tmp() / "file-profile"
    rt = ConfigBoundRestartRuntime.create(froot, tenant="tenant:file", plan=plan)
    rt.checkpoint()
    names = sorted(p.name for p in froot.iterdir())
    binding = json.loads((froot / "configuration-binding.json").read_text())
    print("file profile files:", names)
    print("file profile binding keys:", sorted(binding), "base keys:", sorted(binding["base"]), "gen:", binding["base"]["generation"])
    rec = ConfigBoundRestartRuntime.recover(froot, plan=plan)
    print("file profile recover:", rec.recovery_evidence.recovery_posture, rec.recovery_evidence.base_generation)
    b = dict(binding); b["base"] = dict(binding["base"]); b["base"]["generation"] = 99
    (froot / "configuration-binding.json").write_text(json.dumps(b))
    try:
        ConfigBoundRestartRuntime.recover(froot, plan=plan); print("file profile tampered: ACCEPTED")
    except Exception as e:  # noqa
        print("file profile tampered:", type(e).__name__, e)
    print("binding sha (structure):", hashlib.sha256(json.dumps(sorted(binding)).encode()).hexdigest()[:12])


if __name__ == "__main__":
    main()
