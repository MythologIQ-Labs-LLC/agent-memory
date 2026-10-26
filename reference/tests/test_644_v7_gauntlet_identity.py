"""Independent reproducers for the #644 v7 Gauntlet contestant (validation of e3847942).

D1: the manifest's configuration_digest must follow the basis the v5 and v6 records state,
    sha256 over canonical JSON of the adapter's frozen identity: runtime_profile,
    public_contract, frozen_runtime_revision, tenant, actor, scope and purpose. v5 and v6
    reproduce under that basis; the v7 candidate used a different, ad hoc field set.
D2: the stdio adapter must not serve, and so must not produce evidence labelled with its
    frozen revision, when the imported agentmem_ref is not this checkout's runtime at that
    revision. Run as documented with a pre-existing editable install of another checkout,
    the candidate adapter imported a different runtime and still reported 16a248b.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "examples/gauntlet/agent-memory-runtime-baseline-v7.json"
ADAPTER = ROOT / "examples/gauntlet/agent_memory_runtime_baseline_v7_stdio.py"
BASIS = ("runtime_profile", "public_contract", "frozen_runtime_revision", "tenant", "actor", "scope", "purpose")


def frozen_identity(adapter: Path, runtime_profile: str) -> dict:
    source = adapter.read_text(encoding="utf-8")
    constant = lambda name: re.search(rf'^{name} = "([^"]*)"', source, re.M).group(1)  # noqa: E731
    return {"runtime_profile": runtime_profile, "public_contract": constant("PUBLIC_CONTRACT_VERSION"),
            "frozen_runtime_revision": constant("FROZEN_RUNTIME_REVISION"), "tenant": constant("TENANT"),
            "actor": constant("ACTOR"), "scope": constant("SCOPE"), "purpose": constant("PURPOSE")}


def digest(identity: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def ask(pythonpath: str, operation: str = "describe") -> dict:
    request = {"contract_family": "agent-memory-gauntlet-operation", "contract_version": "0.1.0",
               "direction": "request", "operation": operation, "request_id": "r1",
               "payload": {"namespace": "identity-probe"}}
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = pythonpath
    out = subprocess.run([sys.executable, str(ADAPTER.relative_to(ROOT))], cwd=ROOT, env=env, text=True,
                         input=json.dumps(request) + "\n", capture_output=True, timeout=120)
    return json.loads(out.stdout.strip().splitlines()[-1])


class ConfigurationDigestBasis(unittest.TestCase):
    def test_recorded_basis_reproduces_v5_and_v6(self):
        for version in ("v5", "v6"):
            manifest = json.loads((ROOT / f"examples/gauntlet/agent-memory-runtime-baseline-{version}.json").read_text())
            identity = frozen_identity(ROOT / manifest["transport"]["startup"][1], manifest["metadata"]["runtime_profile"])
            self.assertEqual(manifest["system"]["configuration_digest"], digest(identity), version)

    def test_v7_digest_follows_the_recorded_basis(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        identity = frozen_identity(ADAPTER, manifest["metadata"]["runtime_profile"])
        self.assertEqual(sorted(identity), sorted(BASIS))
        self.assertEqual(manifest["system"]["configuration_digest"], digest(identity))


class ImportedRuntimeIdentity(unittest.TestCase):
    def test_own_checkout_at_frozen_revision_is_served(self):
        reply = ask(str(ROOT / "reference"))
        self.assertEqual(reply["status"], "ok", reply)
        identity = reply["adapter_evidence"]["runtime_identity"]
        self.assertTrue(identity["verified"], identity)
        self.assertTrue(identity["same_checkout"])
        self.assertTrue(identity["matches_frozen_revision"])

    def test_foreign_runtime_is_refused_not_mislabelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(ROOT / "reference/agentmem_ref", Path(tmp) / "agentmem_ref",
                            ignore=shutil.ignore_patterns("__pycache__"))
            with open(Path(tmp) / "agentmem_ref/runtime/adapter.py", "a", encoding="utf-8") as handle:
                handle.write("\n# foreign runtime marker\n")
            for operation in ("describe", "health", "recall"):
                with self.subTest(operation=operation):
                    reply = ask(tmp, operation)
                    self.assertNotEqual(reply["status"], "ok", reply)
                    self.assertEqual(reply["error"]["code"], "runtime_identity_unverified")
                    self.assertFalse(reply["adapter_evidence"]["runtime_identity"]["verified"])


if __name__ == "__main__":
    unittest.main()
