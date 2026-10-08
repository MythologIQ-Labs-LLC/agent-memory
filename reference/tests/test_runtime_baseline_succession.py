"""Runtime Baseline succession (#674): register, declaration, checker and validator on a throwaway repository."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agentmem_ref._paths import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_runtime_baseline_equivalence as checker  # noqa: E402
import declare_runtime_baseline_changes as declare  # noqa: E402
import render_runtime_baseline as renderer  # noqa: E402
import validate_runtime_baseline_source as validator  # noqa: E402
from runtime_baseline_identity import (  # noqa: E402
    IDENTITY_SOURCES,
    IdentitySource,
    read_identities,
    record_value,
)

CONTRACT_FILE = "reference/agentmem_ref/api/contract.py"
RANKING_FILE = "reference/agentmem_ref/runtime/temporal_order_constraints.py"
OTHER_FILE = "reference/agentmem_ref/state/other.py"
EVALUATION_FILE = "reference/agentmem_ref/evaluation/probe.py"
SOURCES = (
    IdentitySource("identity.public_contract_version", CONTRACT_FILE, "constant", "CONTRACT_VERSION"),
    IdentitySource("identity.ranking.active_policy_version", RANKING_FILE, "constant", "POLICY_VERSION"),
)
V1 = "agent-memory-runtime-baseline-v1"
V2 = "agent-memory-runtime-baseline-v2"
REGISTER = "reports/runtime/baseline-register.json"
DECLARATION = "reports/runtime/baseline-v2-declaration.json"
SCHEMA = "schemas/runtime-baseline-declaration.schema.json"
V1_REAL_PUBLISHED = "c3a1bdf19bafca720a6513661cad3f08127659a5"
PENDING = {"status": "pending", "profile_id": "gauntlet-orchestration-retrieval-probe-v1", "transport": "stdio"}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def blob(root: Path, path: str) -> str:
    return git(root, "hash-object", path)


class Repo:
    """A miniature repository with one protected surface and one published baseline."""

    def __init__(self, root: Path) -> None:
        self.root = root
        git(root, "init", "-q")
        git(root, "config", "user.email", "test@example.invalid")
        git(root, "config", "user.name", "test")
        git(root, "config", "commit.gpgsign", "false")
        # No background maintenance: an auto-gc spawned by a commit can still be writing under
        # .git while the TemporaryDirectory is removed (observed as "Directory not empty" in CI).
        git(root, "config", "gc.auto", "0")
        git(root, "config", "maintenance.auto", "false")

    def write(self, path: str, content: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def write_json(self, path: str, data: dict) -> None:
        self.write(path, json.dumps(data, indent=2) + "\n")

    def read_json(self, path: str) -> dict:
        return json.loads((self.root / path).read_text(encoding="utf-8"))

    def commit(self, message: str) -> str:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", message)
        return git(self.root, "rev-parse", "HEAD")

    def freeze_source(self, contract: str = "1.3.0", policy: str = "3.1.2") -> str:
        self.write(CONTRACT_FILE, f'CONTRACT_VERSION = "{contract}"\n')
        self.write(RANKING_FILE, f'POLICY_VERSION = "{policy}"\n')
        self.write(OTHER_FILE, "STATE = 1\n")
        self.write(EVALUATION_FILE, "PROBE = 1\n")
        self.write("pyproject.toml", '[project]\nname = "mini"\nversion = "0.1.0"\n')
        shutil.copy(REPO_ROOT / SCHEMA, self.root / SCHEMA) if (self.root / SCHEMA).parent.exists() else None
        if not (self.root / SCHEMA).exists():
            (self.root / SCHEMA).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO_ROOT / SCHEMA, self.root / SCHEMA)
        return self.commit("freeze source")

    def record(self, baseline_id: str, frozen: str, *, contract: str = "1.3.0", policy: str = "3.1.2") -> dict:
        return {
            "schema_version": 1,
            "baseline_id": baseline_id,
            "status": "rc1_qualified_with_explicit_limitations",
            "production_1_0": False,
            "authority_effect": "none",
            "runtime_revision": {"commit": frozen, "baseline_issue": 638},
            "identity": {"public_contract_version": contract, "ranking": {"active_policy_version": policy}},
            "dogfood": {
                "public_gauntlet_issue": 637,
                "status": "completed",
                "merge_pr": 649,
                "merge_commit": frozen,
                "evidence_class": "baseline_or_probe",
                "authority_effect": "none",
            },
        }

    def boundary(self, baseline_id: str, frozen: str) -> dict:
        return {
            "schema_version": 1,
            "boundary_id": f"{baseline_id}-source-boundary",
            "baseline_id": baseline_id,
            "frozen_revision": frozen,
            "baseline_mutation": False,
            "authority_effect": "none",
            "protected_paths": ["pyproject.toml", "reference/agentmem_ref"],
            "excluded_non_runtime_paths": [
                {"pathspec": ":(exclude)reference/agentmem_ref/evaluation/**", "path": "reference/agentmem_ref/evaluation"}
            ],
        }

    def publish(self, baseline_id: str, frozen: str, **record_kw) -> dict:
        """Step B1: write record, boundary, pending qualification, manifest and adapter; return the entry."""

        label = baseline_id.rsplit("-", 1)[1]
        record_path = f"reports/runtime/baseline-{label}.json"
        boundary_path = f"reports/runtime/baseline-{label}-source-boundary.json"
        qualification_path = f"reports/runtime/baseline-{label}-qualification.json"
        manifest_path = f"examples/gauntlet/{baseline_id}.json"
        adapter_path = f"examples/gauntlet/{label}_stdio.py"
        self.write_json(record_path, self.record(baseline_id, frozen, **record_kw))
        self.write_json(boundary_path, self.boundary(baseline_id, frozen))
        self.write_json(qualification_path, PENDING)
        self.write(adapter_path, f'FROZEN_RUNTIME_REVISION = "{frozen}"\n')
        self.write_json(
            manifest_path,
            {
                "system": {"revision": f"git-commit:{frozen}"},
                "adapter": {"revision": f"git-blob:{blob(self.root, adapter_path)}"},
                "transport": {"kind": "stdio", "startup": ["python", adapter_path]},
                "metadata": {"baseline_id": baseline_id},
            },
        )
        return {
            "baseline_id": baseline_id,
            "record": record_path,
            "record_blob": blob(self.root, record_path),
            "source_boundary": boundary_path,
            "source_boundary_blob": blob(self.root, boundary_path),
            "public_gauntlet_manifest": manifest_path,
            "qualification": {"path": qualification_path, "pointer": "", "blob": blob(self.root, qualification_path)},
            "published_commit": None,
        }

    def bind_qualification(self, entry: dict, frozen: str, verified_head: str) -> dict:
        """Step B2: the qualification file becomes complete; the entry pins its blob and the publication commit."""

        manifest = self.read_json(entry["public_gauntlet_manifest"])
        adapter_path = manifest["transport"]["startup"][-1]
        self.write_json(
            entry["qualification"]["path"],
            {
                **PENDING,
                "status": "complete",
                "evidence_class": "baseline_or_probe",
                "authority_effect": "none",
                "workflow_run": 1,
                "artifact_id": 1,
                "artifact_digest": "sha256:" + "0" * 64,
                "verified_head": verified_head,
                "manifest": entry["public_gauntlet_manifest"],
                "adapter_source": adapter_path,
                "system_revision": f"git-commit:{frozen}",
                "adapter_revision": f"git-blob:{blob(self.root, adapter_path)}",
                "sample_count": 3,
                "exact_top1": 1.0,
            },
        )
        bound = dict(entry, published_commit=verified_head)
        bound["qualification"] = dict(entry["qualification"], blob=blob(self.root, entry["qualification"]["path"]))
        return bound

    def make_pending(self, entry: dict) -> dict:
        self.write_json(entry["qualification"]["path"], PENDING)
        pending = dict(entry)
        pending["qualification"] = dict(entry["qualification"], blob=blob(self.root, entry["qualification"]["path"]))
        return pending

    def write_register(self, entries: list[dict], declared: dict | None = None) -> None:
        self.write_json(
            REGISTER,
            {
                "schema_version": 1,
                "register_id": "mini-register",
                "baselines": entries,
                "declared_successor": declared,
            },
        )

    def declaration(self, changes: list[dict], deltas: list[dict] | None = None, pyproject: dict | None = None) -> dict:
        return {
            "schema_version": 1,
            "baseline_id": V2,
            "predecessor_baseline_id": V1,
            "issue": 673,
            "declared_changes": changes,
            "identity_deltas": deltas if deltas is not None else [],
            "pyproject_change": pyproject,
            "acceptance_evidence_required": [{"kind": "public_gauntlet", "ref": "gauntlet-orchestration-retrieval-probe-v1"}],
        }


class SuccessionTestCase(unittest.TestCase):
    """Build: frozen source -> published v1 (record/boundary committed) -> register pinned to that commit."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repo(Path(self.tmp.name))
        self.frozen = self.repo.freeze_source()
        pending_entry = self.repo.publish(V1, self.frozen)
        self.repo.write_register([pending_entry])
        self.published = self.repo.commit("publish v1 (B1, pending)")
        self.entry = self.repo.bind_qualification(pending_entry, self.frozen, self.published)
        self.repo.write_register([self.entry])
        self.repo.commit("bind v1 qualification (B2)")

    def check(self, candidate: str = "HEAD", **kw) -> checker.Outcome:
        return checker.check(self.repo.root, REGISTER, candidate, identity_sources=SOURCES, **kw)

    def validate(self) -> list[str]:
        return validator.validate_register(self.repo.root, REGISTER, "HEAD", SOURCES)

    def declare(self, changes: list[dict], **kw) -> None:
        self.repo.write_json(DECLARATION, self.repo.declaration(changes, **kw))
        self.repo.write_register([self.entry], {"baseline_id": V2, "declaration": DECLARATION})

    def edit_policy(self, version: str = "3.2.0") -> None:
        self.repo.write(RANKING_FILE, f'POLICY_VERSION = "{version}"\n')

    def declared(self, *paths: str) -> list[dict]:
        return [{"path": path, "blob": blob(self.repo.root, path)} for path in paths]


class CheckerOutcomes(SuccessionTestCase):
    def test_pass_when_only_evaluation_changes(self) -> None:
        self.repo.write(EVALUATION_FILE, "PROBE = 2\n")
        self.repo.commit("evaluation only")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_PASS)
        self.assertTrue(outcome.message.startswith(f"Runtime Baseline equivalence: PASS; baseline={V1}; frozen={self.frozen}"))

    def test_fail_without_declaration(self) -> None:
        self.edit_policy()
        self.repo.commit("undeclared runtime change")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertIn(self.frozen, outcome.message)
        self.assertIn("declares no successor", outcome.message)
        self.assertIn(RANKING_FILE, outcome.message)

    def test_transition_with_honest_declaration(self) -> None:
        self.edit_policy()
        self.declare(self.declared(RANKING_FILE), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.commit("declared tranche")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_TRANSITION, outcome.message)
        self.assertIn(f"declared_successor={V2} (issue #673)", outcome.message)
        self.assertIn(f"protected surface = frozen {self.frozen} + 1 declared blobs", outcome.message)
        self.assertIn("deltas=identity.ranking.active_policy_version 3.1.2->3.2.0", outcome.message)

    def test_pinned_only_refuses_transition(self) -> None:
        self.edit_policy()
        self.declare(self.declared(RANKING_FILE), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.commit("declared tranche")
        outcome = self.check(pinned_only=True)
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertEqual(outcome.message, f"candidate HEAD is in a declared transition to {V2}; this check requires a pinned baseline")

    def test_fail_when_undeclared_protected_file_changes(self) -> None:
        self.edit_policy()
        self.repo.write(OTHER_FILE, "STATE = 2\n")
        self.declare(self.declared(RANKING_FILE), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.commit("one file undeclared")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith(f"undeclared protected change: {OTHER_FILE}"), outcome.message)

    def test_fail_when_declared_blob_differs(self) -> None:
        self.edit_policy()
        self.declare(self.declared(RANKING_FILE), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.write(RANKING_FILE, 'POLICY_VERSION = "3.2.0"\nEXTRA = True\n')
        self.repo.commit("second edit after pinning")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith(f"declared blob mismatch for {RANKING_FILE}: declared "), outcome.message)

    def test_fail_when_declared_change_is_absent(self) -> None:
        self.edit_policy()
        changes = self.declared(RANKING_FILE) + [{"path": OTHER_FILE, "blob": blob(self.repo.root, OTHER_FILE)}]
        self.declare(changes, deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.commit("declares an unchanged file")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith(f"declared change absent from candidate: {OTHER_FILE}"), outcome.message)

    def test_fail_when_declared_to_is_not_in_candidate(self) -> None:
        self.edit_policy("3.1.3")
        self.declare(self.declared(RANKING_FILE), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.commit("declared to differs")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith("declared delta identity.ranking.active_policy_version: candidate value is '3.1.3', declaration says to='3.2.0'"), outcome.message)

    def test_fail_when_declared_from_is_not_in_frozen(self) -> None:
        self.edit_policy()
        self.declare(self.declared(RANKING_FILE), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.1", "to": "3.2.0"}])
        self.repo.commit("declared from differs")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith("declared delta identity.ranking.active_policy_version: predecessor value is '3.1.2', declaration says from='3.1.1'"), outcome.message)

    def test_fail_when_undeclared_identity_changes(self) -> None:
        self.edit_policy()
        self.repo.write(CONTRACT_FILE, 'CONTRACT_VERSION = "1.4.0"\n')
        self.declare(self.declared(RANKING_FILE, CONTRACT_FILE), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.commit("contract bumped inside a declared blob")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith("undeclared identity identity.public_contract_version changed: frozen='1.3.0', candidate='1.4.0'"), outcome.message)

    def test_fail_when_pyproject_declared_without_reason(self) -> None:
        self.edit_policy()
        self.repo.write("pyproject.toml", '[project]\nname = "mini"\nversion = "0.1.0"\ndependencies = ["x"]\n')
        self.declare(self.declared(RANKING_FILE, "pyproject.toml"), deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        self.repo.commit("pyproject without reason")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith("pyproject.toml declared without pyproject_change"), outcome.message)

    def test_transition_with_declared_pyproject_change(self) -> None:
        self.edit_policy()
        self.repo.write("pyproject.toml", '[project]\nname = "mini"\nversion = "0.1.0"\ndependencies = ["x"]\n')
        self.declare(
            self.declared(RANKING_FILE, "pyproject.toml"),
            deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}],
            pyproject={"reason": "embedding provider pin"},
        )
        self.repo.commit("pyproject with reason")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_TRANSITION, outcome.message)
        self.assertIn("+ 2 declared blobs", outcome.message)

    def test_fail_when_predecessor_is_not_current(self) -> None:
        self.edit_policy()
        declaration = self.repo.declaration(self.declared(RANKING_FILE), [{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        declaration["predecessor_baseline_id"] = "agent-memory-runtime-baseline-v0"
        self.repo.write_json(DECLARATION, declaration)
        self.repo.write_register([self.entry], {"baseline_id": V2, "declaration": DECLARATION})
        self.repo.commit("wrong predecessor")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith(f"declared successor {V2} names predecessor agent-memory-runtime-baseline-v0 but the current baseline is {V1}"), outcome.message)

    def test_fail_when_current_is_pending(self) -> None:
        pending = dict(self.repo.make_pending(self.entry), published_commit=None)
        self.edit_policy()
        self.repo.write_json(DECLARATION, self.repo.declaration(self.declared(RANKING_FILE), [{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}]))
        self.repo.write_register([pending], {"baseline_id": V2, "declaration": DECLARATION})
        self.repo.commit("declaration while pending")
        outcome = self.check()
        self.assertEqual(outcome.state, checker.STATE_FAIL)
        self.assertTrue(outcome.message.startswith(f"declared successor {V2} cannot open while {V1} qualification is pending or unpinned"), outcome.message)

    def test_declare_script_writes_blobs(self) -> None:
        self.edit_policy()
        self.repo.write(OTHER_FILE, "STATE = 2\n")
        self.declare([{"path": "placeholder", "blob": None}], deltas=[{"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}])
        changes = declare.rewrite(self.repo.root, DECLARATION, REGISTER)
        self.assertEqual([item["path"] for item in changes], [RANKING_FILE, OTHER_FILE])
        self.assertEqual(changes, self.declared(RANKING_FILE, OTHER_FILE))
        self.assertEqual(declare.rewrite(self.repo.root, DECLARATION, REGISTER), changes)
        self.repo.commit("declared by the helper")
        self.assertEqual(self.check().state, checker.STATE_TRANSITION)

    def test_main_prints_message_and_exit_code(self) -> None:
        self.assertEqual(checker.main(["--root", str(self.repo.root), "--candidate", "HEAD"]), 0)
        self.edit_policy()
        self.repo.commit("undeclared")
        with self.assertRaises(SystemExit) as caught:
            checker.main(["--root", str(self.repo.root), "--candidate", "HEAD"])
        self.assertIn("declares no successor", str(caught.exception))


class RegisterValidator(SuccessionTestCase):
    def test_complete_entry_validates(self) -> None:
        summary = self.validate()[0]
        self.assertEqual(summary.split(";")[0], f"{V1} identities match frozen revision {self.frozen}")
        self.assertIn("public baseline qualification is bound at workflow 1", summary)

    def test_register_refuses_record_blob_drift(self) -> None:
        record = self.repo.read_json(self.entry["record"])
        record["status"] = "edited"
        self.repo.write_json(self.entry["record"], record)
        with self.assertRaises(SystemExit) as caught:
            self.validate()
        self.assertIn(f"{V1} record blob mismatch", str(caught.exception))

    def test_register_refuses_published_commit_with_other_bytes(self) -> None:
        record = self.repo.read_json(self.entry["record"])
        record["status"] = "edited after publication"
        self.repo.write_json(self.entry["record"], record)
        drifted = dict(self.entry, record_blob=blob(self.repo.root, self.entry["record"]))
        self.repo.write_register([drifted])
        with self.assertRaises(SystemExit) as caught:
            self.validate()
        self.assertIn(f"{V1} record blob at published commit mismatch", str(caught.exception))

    def test_register_refuses_published_commit_off_first_parent(self) -> None:
        git(self.repo.root, "checkout", "-q", "-b", "side")
        self.repo.write(EVALUATION_FILE, "PROBE = 3\n")
        side = self.repo.commit("side work")
        git(self.repo.root, "checkout", "-q", "-")
        git(self.repo.root, "merge", "-q", "--no-ff", "-m", "merge side", "side")
        self.repo.write_register([dict(self.entry, published_commit=side)])
        self.repo.commit("pin to side commit")
        with self.assertRaises(SystemExit) as caught:
            self.validate()
        self.assertIn("is not on the first-parent history of HEAD", str(caught.exception))

    def test_register_allows_pending_last_entry_without_published_commit(self) -> None:
        pending = dict(self.repo.make_pending(self.entry), published_commit=None)
        self.repo.write_register([pending])
        self.assertIn("public baseline qualification is pending", self.validate()[0])

    def test_register_refuses_pending_non_last_entry(self) -> None:
        first = dict(self.repo.make_pending(self.entry), published_commit=None)
        second = self.repo.publish(V2, self.frozen)
        self.repo.write_register([first, second])
        with self.assertRaises(SystemExit) as caught:
            self.validate()
        self.assertIn("only the last register entry may carry a pending qualification", str(caught.exception))

    def test_register_refuses_complete_entry_without_published_commit(self) -> None:
        self.repo.write_register([dict(self.entry, published_commit=None)])
        with self.assertRaises(SystemExit) as caught:
            self.validate()
        self.assertIn("a complete qualification requires published_commit", str(caught.exception))

    def test_register_refuses_open_declaration_with_wrong_from(self) -> None:
        self.repo.write_json(DECLARATION, self.repo.declaration([{"path": RANKING_FILE, "blob": "0" * 40}], [{"identity_path": "identity.ranking.active_policy_version", "from": "9.9.9", "to": "3.2.0"}]))
        self.repo.write_register([self.entry], {"baseline_id": V2, "declaration": DECLARATION})
        with self.assertRaises(SystemExit) as caught:
            self.validate()
        self.assertIn("predecessor value is '3.1.2', declaration says from='9.9.9'", str(caught.exception))

    def test_identity_helpers(self) -> None:
        values = read_identities(self.repo.root, self.frozen, SOURCES)
        self.assertEqual(values, {"identity.public_contract_version": "1.3.0", "identity.ranking.active_policy_version": "3.1.2"})
        self.assertEqual(record_value({"read_semantics": {"candidate_routes": ["a", "b", "c", "d"]}}, "read_semantics.candidate_routes.3"), "d")
        with self.assertRaises(SystemExit):
            record_value({"identity": {}}, "identity.missing")


V2_FROZEN = "488d64aadb16ba4b0c474af95d67e96e970e4dfc"
V2_B1_HEAD = "8e1211e0a7882904b6cb32e028e68381c248686a"
V2_PUBLISHED = "a5c6de316abb04f03ea1402c19d6b5c7fdf132e9"
V3 = "agent-memory-runtime-baseline-v3"
V3_FROZEN = "aede8fdec879121491ce06f31d475a4986b7a286"
V3_DECLARATION = "reports/runtime/baseline-v3-declaration.json"
V3_B1_HEAD = "57ad872868683ba6ce73574c3eb90bc1f95063d2"
V3_PUBLISHED = "2e73375d473f3d6f2894dd14b7cfc19a6f228f8e"
V4 = "agent-memory-runtime-baseline-v4"
V4_FROZEN = "729a6c8fc7dd12a28baa8934123c7d367adc84e5"
V4_DECLARATION = "reports/runtime/baseline-v4-declaration.json"
V4_B1_HEAD = "8a89f9442ff61b1fc7e4705a07084ffdfa3e5bba"
V4_PUBLISHED = "2501f0ff76dda65b626f22e6905c06fa1bd504a7"
V5 = "agent-memory-runtime-baseline-v5"
V5_FROZEN = "74c8683e33f2b716577138e5b4c750a9ae670966"
V5_DECLARATION = "reports/runtime/baseline-v5-declaration.json"
V5_B1_HEAD = "ee5578b37c547a1a98e4fe6f49f2e4276ad239c8"
V5_PUBLISHED = "0110f8efdb6a6d577aaf8630c17721b3813479b0"
V6 = "agent-memory-runtime-baseline-v6"
V6_FROZEN = "e98e6e7b776aa2dd680e84f3ed4773ad2afa4ae1"
V6_DECLARATION = "reports/runtime/baseline-v6-declaration.json"


class RealRepository(unittest.TestCase):
    """The committed register pins Runtime Baseline v1 exactly and carries v2 as the current entry; both renderings are byte-identical."""

    @staticmethod
    def _entry(register: dict, baseline_id: str) -> dict:
        return next(item for item in register["baselines"] if item["baseline_id"] == baseline_id)

    def test_register_pins_v1_bytes(self) -> None:
        register = checker.load_register(REPO_ROOT, REGISTER)
        entry = self._entry(register, V1)
        self.assertEqual(entry["baseline_id"], V1)
        self.assertEqual(blob(REPO_ROOT, entry["record"]), entry["record_blob"])
        self.assertEqual(blob(REPO_ROOT, entry["source_boundary"]), entry["source_boundary_blob"])
        self.assertEqual(entry["qualification"]["path"], entry["record"])
        self.assertEqual(entry["qualification"]["blob"], entry["record_blob"])
        self.assertEqual(entry["published_commit"], V1_REAL_PUBLISHED)
        available = subprocess.run(
            ["git", "cat-file", "-e", f"{V1_REAL_PUBLISHED}^{{commit}}"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
        )
        if available.returncode != 0:
            self.skipTest("the v1 publication commit is not available in this checkout")
        self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V1_REAL_PUBLISHED}:{entry['record']}"), entry["record_blob"])
        self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V1_REAL_PUBLISHED}:{entry['source_boundary']}"), entry["source_boundary_blob"])
        self.assertTrue(validator.first_parent_ancestor(REPO_ROOT, "HEAD", V1_REAL_PUBLISHED))

    def test_identity_table_covers_the_v1_record(self) -> None:
        record = json.loads((REPO_ROOT / "reports/runtime/baseline-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(len(IDENTITY_SOURCES), 26)
        for source in IDENTITY_SOURCES:
            record_value(record, source.identity_path)

    def test_v1_rendering_is_byte_identical(self) -> None:
        register = checker.load_register(REPO_ROOT, REGISTER)
        output, rendered = renderer.render_entry(REPO_ROOT, self._entry(register, V1))
        self.assertEqual(output, REPO_ROOT / "reports/runtime/baseline-v1.md")
        self.assertEqual(rendered, output.read_text(encoding="utf-8"))

    def test_register_pins_v2_after_its_b2(self) -> None:
        # docs/67 Steps B1 and B2: v2 is blob-pinned in the working tree, its companion
        # qualification bound and its publication commit pinned. v3 succeeds it (#669).
        register = checker.load_register(REPO_ROOT, REGISTER)
        self.assertEqual([item["baseline_id"] for item in register["baselines"]][:2], [V1, V2])
        entry = self._entry(register, V2)
        self.assertEqual(entry["record"], "reports/runtime/baseline-v2.json")
        self.assertEqual(blob(REPO_ROOT, entry["record"]), entry["record_blob"])
        self.assertEqual(blob(REPO_ROOT, entry["source_boundary"]), entry["source_boundary_blob"])
        self.assertEqual(entry["qualification"]["path"], "reports/runtime/baseline-v2-qualification.json")
        self.assertEqual(entry["qualification"]["pointer"], "")
        self.assertEqual(blob(REPO_ROOT, entry["qualification"]["path"]), entry["qualification"]["blob"])
        qualification = json.loads((REPO_ROOT / entry["qualification"]["path"]).read_text(encoding="utf-8"))
        # docs/67 Step B2: the companion file is complete and the entry pins the B1 merge commit.
        self.assertEqual(qualification["status"], "complete")
        self.assertEqual(qualification["verified_head"], V2_B1_HEAD)
        self.assertEqual(qualification["workflow_run"], 37548446965)
        self.assertEqual(qualification["system_revision"], f"git-commit:{V2_FROZEN}")
        self.assertEqual(qualification["sample_count"], 3)
        self.assertEqual(qualification["exact_top1"], 1.0)
        self.assertEqual(entry["published_commit"], V2_PUBLISHED)
        available = subprocess.run(["git", "cat-file", "-e", f"{V2_PUBLISHED}^{{commit}}"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if available.returncode == 0:
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V2_PUBLISHED}:{entry['record']}"), entry["record_blob"])
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V2_PUBLISHED}:{entry['source_boundary']}"), entry["source_boundary_blob"])
            self.assertTrue(validator.first_parent_ancestor(REPO_ROOT, "HEAD", V2_PUBLISHED))
        record = json.loads((REPO_ROOT / entry["record"]).read_text(encoding="utf-8"))
        boundary = json.loads((REPO_ROOT / entry["source_boundary"]).read_text(encoding="utf-8"))
        self.assertEqual(record["runtime_revision"]["commit"], V2_FROZEN)
        self.assertEqual(boundary["frozen_revision"], V2_FROZEN)
        self.assertEqual(record["identity"]["public_contract_version"], "1.4.0")
        declaration = json.loads((REPO_ROOT / DECLARATION).read_text(encoding="utf-8"))
        self.assertEqual(record["predecessor"]["baseline_id"], V1)
        self.assertEqual(record["predecessor"]["identity_deltas"], declaration["identity_deltas"])
        self.assertEqual(record["predecessor"]["declared_changes"], declaration["declared_changes"])
        self.assertEqual(record["predecessor"]["declaration_blob"], blob(REPO_ROOT, DECLARATION))
        self.assertNotIn("required_before_issue_638_close", record["dogfood"])
        self.assertEqual(record["dogfood"]["merge_commit"], "10898c0edf4fa7093a0bbeda1b2cb8062469e843")
        rows = record["qualification_evidence"]["successor_lane_acceptance"]["rows"]
        self.assertEqual(len(rows), 9)
        self.assertEqual({row["checker_state"] for row in rows}, {"TRANSITION"})
        manifest = json.loads((REPO_ROOT / entry["public_gauntlet_manifest"]).read_text(encoding="utf-8"))
        adapter = manifest["transport"]["startup"][-1]
        self.assertEqual(adapter, "examples/gauntlet/agent_memory_runtime_baseline_v2_stdio.py")
        self.assertEqual(manifest["system"]["revision"], f"git-commit:{V2_FROZEN}")
        self.assertEqual(manifest["adapter"]["revision"], f"git-blob:{blob(REPO_ROOT, adapter)}")
        self.assertEqual(manifest["metadata"]["baseline_id"], V2)
        source = (REPO_ROOT / adapter).read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V2_FROZEN}"', source)
        self.assertIn('PUBLIC_CONTRACT_VERSION = "1.4.0"', source)
        v1_source = (REPO_ROOT / "examples/gauntlet/agent_memory_runtime_baseline_stdio.py").read_text(encoding="utf-8")
        self.assertIn('PUBLIC_CONTRACT_VERSION = "1.3.0"', v1_source, "the v1 adapter keeps its constants")

    def test_v2_rendering_is_byte_identical(self) -> None:
        register = checker.load_register(REPO_ROOT, REGISTER)
        output, rendered = renderer.render_entry(REPO_ROOT, self._entry(register, V2))
        self.assertEqual(output, REPO_ROOT / "reports/runtime/baseline-v2.md")
        self.assertEqual(rendered, output.read_text(encoding="utf-8"))
        self.assertIn("public Gauntlet path: **complete** via `stdio`", rendered)

    def test_register_pins_v3_after_its_b2(self) -> None:
        # docs/67 Steps B1 and B2 for #669: v3 is blob-pinned in the working tree, its companion
        # qualification bound and its publication commit pinned. v4 succeeds it (#644).
        register = checker.load_register(REPO_ROOT, REGISTER)
        self.assertEqual([item["baseline_id"] for item in register["baselines"]][:3], [V1, V2, V3])
        entry = self._entry(register, V3)
        self.assertEqual(entry["record"], "reports/runtime/baseline-v3.json")
        self.assertEqual(blob(REPO_ROOT, entry["record"]), entry["record_blob"])
        self.assertEqual(blob(REPO_ROOT, entry["source_boundary"]), entry["source_boundary_blob"])
        self.assertEqual(entry["qualification"]["path"], "reports/runtime/baseline-v3-qualification.json")
        self.assertEqual(entry["qualification"]["pointer"], "")
        self.assertEqual(blob(REPO_ROOT, entry["qualification"]["path"]), entry["qualification"]["blob"])
        qualification = json.loads((REPO_ROOT / entry["qualification"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(qualification["status"], "complete")
        self.assertEqual(qualification["verified_head"], V3_B1_HEAD)
        self.assertEqual(qualification["workflow_run"], 37615387248)
        self.assertEqual(qualification["system_revision"], f"git-commit:{V3_FROZEN}")
        self.assertEqual(qualification["sample_count"], 3)
        self.assertEqual(qualification["exact_top1"], 1.0)
        self.assertEqual(entry["published_commit"], V3_PUBLISHED)
        available = subprocess.run(["git", "cat-file", "-e", f"{V3_PUBLISHED}^{{commit}}"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if available.returncode == 0:
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V3_PUBLISHED}:{entry['record']}"), entry["record_blob"])
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V3_PUBLISHED}:{entry['source_boundary']}"), entry["source_boundary_blob"])
            self.assertTrue(validator.first_parent_ancestor(REPO_ROOT, "HEAD", V3_PUBLISHED))
        record = json.loads((REPO_ROOT / entry["record"]).read_text(encoding="utf-8"))
        boundary = json.loads((REPO_ROOT / entry["source_boundary"]).read_text(encoding="utf-8"))
        self.assertEqual(record["runtime_revision"]["commit"], V3_FROZEN)
        self.assertEqual(boundary["frozen_revision"], V3_FROZEN)
        self.assertEqual(record["identity"]["ranking"]["active_policy_version"], "3.2.0")
        self.assertEqual(record["read_semantics"]["semantic_route"]["facade_default"], "off")
        declaration = json.loads((REPO_ROOT / V3_DECLARATION).read_text(encoding="utf-8"))
        self.assertEqual(record["predecessor"]["baseline_id"], V2)
        self.assertEqual(record["predecessor"]["identity_deltas"], declaration["identity_deltas"])
        self.assertEqual(record["predecessor"]["declared_changes"], declaration["declared_changes"])
        self.assertEqual(record["predecessor"]["pyproject_change"], declaration["pyproject_change"])
        self.assertEqual(record["predecessor"]["declaration_blob"], blob(REPO_ROOT, V3_DECLARATION))
        acceptance = record["qualification_evidence"]["successor_lane_acceptance"]
        self.assertEqual(acceptance["declaration_blob"], blob(REPO_ROOT, V3_DECLARATION))
        rows = acceptance["rows"]
        self.assertEqual(len(rows), 11)
        self.assertEqual({row["checker_state"] for row in rows}, {"TRANSITION"})
        self.assertIn("lane:longmemeval-s-retrieval-parity-v3:agent_memory_semantic:session", {row["evidence_id"] for row in rows})
        manifest = json.loads((REPO_ROOT / entry["public_gauntlet_manifest"]).read_text(encoding="utf-8"))
        adapter = manifest["transport"]["startup"][-1]
        self.assertEqual(adapter, "examples/gauntlet/agent_memory_runtime_baseline_v3_stdio.py")
        self.assertEqual(manifest["system"]["revision"], f"git-commit:{V3_FROZEN}")
        self.assertEqual(manifest["adapter"]["revision"], f"git-blob:{blob(REPO_ROOT, adapter)}")
        self.assertEqual(manifest["metadata"]["baseline_id"], V3)
        source = (REPO_ROOT / adapter).read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V3_FROZEN}"', source)
        self.assertIn('PUBLIC_CONTRACT_VERSION = "1.4.0"', source)
        v2_source = (REPO_ROOT / "examples/gauntlet/agent_memory_runtime_baseline_v2_stdio.py").read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V2_FROZEN}"', v2_source, "the v2 adapter keeps its constants")

    def test_v3_rendering_is_byte_identical(self) -> None:
        register = checker.load_register(REPO_ROOT, REGISTER)
        output, rendered = renderer.render_entry(REPO_ROOT, self._entry(register, V3))
        self.assertEqual(output, REPO_ROOT / "reports/runtime/baseline-v3.md")
        self.assertEqual(rendered, output.read_text(encoding="utf-8"))
        self.assertIn("public Gauntlet path: **complete** via `stdio`", rendered)

    def test_register_pins_v4_after_its_b2(self) -> None:
        # docs/67 Steps B1 and B2 for #644: v4 is blob-pinned in the working tree, its companion
        # qualification bound and its publication commit pinned. v5 succeeds it (#671).
        register = checker.load_register(REPO_ROOT, REGISTER)
        self.assertEqual([item["baseline_id"] for item in register["baselines"]][:4], [V1, V2, V3, V4])
        entry = self._entry(register, V4)
        self.assertEqual(entry["record"], "reports/runtime/baseline-v4.json")
        self.assertEqual(blob(REPO_ROOT, entry["record"]), entry["record_blob"])
        self.assertEqual(blob(REPO_ROOT, entry["source_boundary"]), entry["source_boundary_blob"])
        self.assertEqual(entry["qualification"]["path"], "reports/runtime/baseline-v4-qualification.json")
        self.assertEqual(entry["qualification"]["pointer"], "")
        self.assertEqual(blob(REPO_ROOT, entry["qualification"]["path"]), entry["qualification"]["blob"])
        qualification = json.loads((REPO_ROOT / entry["qualification"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(qualification["status"], "complete")
        self.assertEqual(qualification["verified_head"], V4_B1_HEAD)
        self.assertEqual(qualification["workflow_run"], 37671546394)
        self.assertEqual(qualification["system_revision"], f"git-commit:{V4_FROZEN}")
        self.assertEqual(qualification["sample_count"], 3)
        self.assertEqual(qualification["exact_top1"], 1.0)
        self.assertEqual(entry["published_commit"], V4_PUBLISHED)
        available = subprocess.run(["git", "cat-file", "-e", f"{V4_PUBLISHED}^{{commit}}"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if available.returncode == 0:
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V4_PUBLISHED}:{entry['record']}"), entry["record_blob"])
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V4_PUBLISHED}:{entry['source_boundary']}"), entry["source_boundary_blob"])
            self.assertTrue(validator.first_parent_ancestor(REPO_ROOT, "HEAD", V4_PUBLISHED))
        record = json.loads((REPO_ROOT / entry["record"]).read_text(encoding="utf-8"))
        boundary = json.loads((REPO_ROOT / entry["source_boundary"]).read_text(encoding="utf-8"))
        self.assertEqual(record["runtime_revision"]["commit"], V4_FROZEN)
        self.assertEqual(boundary["frozen_revision"], V4_FROZEN)
        self.assertEqual(record["identity"]["public_contract_version"], "1.5.0")
        self.assertEqual(record["identity"]["ranking"]["active_policy_version"], "3.2.0")
        self.assertEqual(record["read_semantics"]["recall_control"]["facade_default"], "off")
        self.assertEqual(record["read_semantics"]["recall_control"]["authority_effect"], "none")
        # docs/CONTRIBUTOR_ARCHITECTURE.md section 8: the inherited native_qualified drift is corrected
        self.assertEqual(record["capabilities"]["typed_relations_graph_traversal"], "harness_only")
        self.assertEqual(record["capabilities"]["memory_metabolism"], "harness_only")
        self.assertEqual(record["capabilities"]["controlled_recall"], "shadow_only")
        declaration = json.loads((REPO_ROOT / V4_DECLARATION).read_text(encoding="utf-8"))
        self.assertEqual(record["predecessor"]["baseline_id"], V3)
        self.assertEqual(record["predecessor"]["identity_deltas"], declaration["identity_deltas"])
        self.assertEqual(record["predecessor"]["declared_changes"], declaration["declared_changes"])
        self.assertEqual(record["predecessor"]["pyproject_change"], declaration["pyproject_change"])
        self.assertEqual(record["predecessor"]["declaration_blob"], blob(REPO_ROOT, V4_DECLARATION))
        acceptance = record["qualification_evidence"]["successor_lane_acceptance"]
        self.assertEqual(acceptance["declaration_blob"], blob(REPO_ROOT, V4_DECLARATION))
        rows = acceptance["rows"]
        self.assertEqual(len(rows), 12)
        self.assertEqual({row["checker_state"] for row in rows}, {"TRANSITION"})
        self.assertIn("lane:longmemeval-s-retrieval-parity-v4:agent_memory_shadow:session", {row["evidence_id"] for row in rows})
        self.assertIn("lane:amb-precisionmembench-retrieval-v4:agent-memory-shadow", {row["evidence_id"] for row in rows})
        for row in rows:
            self.assertTrue((REPO_ROOT / row["report"]).is_file(), row["report"])
        manifest = json.loads((REPO_ROOT / entry["public_gauntlet_manifest"]).read_text(encoding="utf-8"))
        adapter = manifest["transport"]["startup"][-1]
        self.assertEqual(adapter, "examples/gauntlet/agent_memory_runtime_baseline_v4_stdio.py")
        self.assertEqual(manifest["system"]["revision"], f"git-commit:{V4_FROZEN}")
        self.assertEqual(manifest["adapter"]["revision"], f"git-blob:{blob(REPO_ROOT, adapter)}")
        self.assertEqual(manifest["metadata"]["baseline_id"], V4)
        source = (REPO_ROOT / adapter).read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V4_FROZEN}"', source)
        self.assertIn('PUBLIC_CONTRACT_VERSION = "1.5.0"', source)
        v3_source = (REPO_ROOT / "examples/gauntlet/agent_memory_runtime_baseline_v3_stdio.py").read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V3_FROZEN}"', v3_source, "the v3 adapter keeps its constants")

    def test_v4_rendering_is_byte_identical(self) -> None:
        register = checker.load_register(REPO_ROOT, REGISTER)
        output, rendered = renderer.render_entry(REPO_ROOT, self._entry(register, V4))
        self.assertEqual(output, REPO_ROOT / "reports/runtime/baseline-v4.md")
        self.assertEqual(rendered, output.read_text(encoding="utf-8"))
        self.assertIn("public Gauntlet path: **complete** via `stdio`", rendered)

    def test_register_pins_v5_after_its_b2(self) -> None:
        # docs/67 Steps B1 and B2 for #671: v5 is blob-pinned in the working tree, its companion
        # qualification bound and its publication commit pinned. v6 succeeds it (#732).
        register = checker.load_register(REPO_ROOT, REGISTER)
        self.assertEqual([item["baseline_id"] for item in register["baselines"]][:5], [V1, V2, V3, V4, V5])
        entry = self._entry(register, V5)
        self.assertEqual(entry["record"], "reports/runtime/baseline-v5.json")
        self.assertEqual(blob(REPO_ROOT, entry["record"]), entry["record_blob"])
        self.assertEqual(blob(REPO_ROOT, entry["source_boundary"]), entry["source_boundary_blob"])
        self.assertEqual(entry["qualification"]["path"], "reports/runtime/baseline-v5-qualification.json")
        self.assertEqual(entry["qualification"]["pointer"], "")
        self.assertEqual(blob(REPO_ROOT, entry["qualification"]["path"]), entry["qualification"]["blob"])
        qualification = json.loads((REPO_ROOT / entry["qualification"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(qualification["status"], "complete")
        self.assertEqual(qualification["verified_head"], V5_B1_HEAD)
        self.assertEqual(qualification["workflow_run"], 37692139650)
        self.assertEqual(qualification["system_revision"], f"git-commit:{V5_FROZEN}")
        self.assertEqual(qualification["sample_count"], 3)
        self.assertEqual(qualification["exact_top1"], 1.0)
        self.assertEqual(entry["published_commit"], V5_PUBLISHED)
        available = subprocess.run(["git", "cat-file", "-e", f"{V5_PUBLISHED}^{{commit}}"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if available.returncode == 0:
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V5_PUBLISHED}:{entry['record']}"), entry["record_blob"])
            self.assertEqual(git(REPO_ROOT, "rev-parse", f"{V5_PUBLISHED}:{entry['source_boundary']}"), entry["source_boundary_blob"])
            self.assertTrue(validator.first_parent_ancestor(REPO_ROOT, "HEAD", V5_PUBLISHED))
        record = json.loads((REPO_ROOT / entry["record"]).read_text(encoding="utf-8"))
        boundary = json.loads((REPO_ROOT / entry["source_boundary"]).read_text(encoding="utf-8"))
        self.assertEqual(record["runtime_revision"]["commit"], V5_FROZEN)
        self.assertEqual(boundary["frozen_revision"], V5_FROZEN)
        self.assertEqual(record["identity"]["public_contract_version"], "1.5.0")
        self.assertEqual(record["identity"]["ranking"]["active_policy_version"], "3.3.0")
        cross_fact = record["read_semantics"]["cross_fact_currentness"]
        self.assertEqual(cross_fact["authority_effect"], "none")
        self.assertIn("explicit-current recall only", cross_fact["applies_to"])
        # owner posture 2026-10-07: MESA M4 is a regression floor; generalization is not measured
        limitation = next(item for item in record["known_limitations"] if item["id"] == "cross_fact_currentness_scope")
        self.assertEqual(limitation["issue"], 732)
        self.assertIn("not measured", limitation["evidence"])
        mesa = record["qualification_evidence"]["agentmembench_mesa_formal_v2"]
        self.assertEqual(mesa["m4_win_basis_counts"], {"currentness_mechanism": 250})
        self.assertTrue((REPO_ROOT / mesa["report"]).is_file())
        declaration = json.loads((REPO_ROOT / V5_DECLARATION).read_text(encoding="utf-8"))
        self.assertEqual(record["predecessor"]["baseline_id"], V4)
        self.assertEqual(record["predecessor"]["identity_deltas"], declaration["identity_deltas"])
        self.assertEqual(record["predecessor"]["declared_changes"], declaration["declared_changes"])
        self.assertEqual(record["predecessor"]["pyproject_change"], declaration["pyproject_change"])
        self.assertEqual(record["predecessor"]["declaration_blob"], blob(REPO_ROOT, V5_DECLARATION))
        acceptance = record["qualification_evidence"]["successor_lane_acceptance"]
        self.assertEqual(acceptance["declaration_blob"], blob(REPO_ROOT, V5_DECLARATION))
        rows = acceptance["rows"]
        self.assertEqual(len(rows), 9)
        self.assertEqual({row["checker_state"] for row in rows}, {"TRANSITION"})
        for row in rows:
            self.assertTrue((REPO_ROOT / row["report"]).is_file(), row["report"])
        manifest = json.loads((REPO_ROOT / entry["public_gauntlet_manifest"]).read_text(encoding="utf-8"))
        adapter = manifest["transport"]["startup"][-1]
        self.assertEqual(adapter, "examples/gauntlet/agent_memory_runtime_baseline_v5_stdio.py")
        self.assertEqual(manifest["system"]["revision"], f"git-commit:{V5_FROZEN}")
        self.assertEqual(manifest["adapter"]["revision"], f"git-blob:{blob(REPO_ROOT, adapter)}")
        self.assertEqual(manifest["metadata"]["baseline_id"], V5)
        source = (REPO_ROOT / adapter).read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V5_FROZEN}"', source)
        self.assertIn('PUBLIC_CONTRACT_VERSION = "1.5.0"', source)
        v4_source = (REPO_ROOT / "examples/gauntlet/agent_memory_runtime_baseline_v4_stdio.py").read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V4_FROZEN}"', v4_source, "the v4 adapter keeps its constants")

    def test_v5_rendering_is_byte_identical(self) -> None:
        register = checker.load_register(REPO_ROOT, REGISTER)
        output, rendered = renderer.render_entry(REPO_ROOT, self._entry(register, V5))
        self.assertEqual(output, REPO_ROOT / "reports/runtime/baseline-v5.md")
        self.assertEqual(rendered, output.read_text(encoding="utf-8"))
        self.assertIn("public Gauntlet path: **complete** via `stdio`", rendered)

    def test_register_carries_v6_as_the_current_entry(self) -> None:
        # docs/67 Step B1 for #732: v6 is the last entry, blob-pinned in the working tree, with
        # a pending companion qualification and no publication commit yet; no successor is declared.
        register = checker.load_register(REPO_ROOT, REGISTER)
        self.assertEqual([item["baseline_id"] for item in register["baselines"]], [V1, V2, V3, V4, V5, V6])
        self.assertIsNone(register["declared_successor"])
        entry = register["baselines"][-1]
        self.assertEqual(entry["record"], "reports/runtime/baseline-v6.json")
        self.assertEqual(blob(REPO_ROOT, entry["record"]), entry["record_blob"])
        self.assertEqual(blob(REPO_ROOT, entry["source_boundary"]), entry["source_boundary_blob"])
        self.assertEqual(entry["qualification"]["path"], "reports/runtime/baseline-v6-qualification.json")
        self.assertEqual(entry["qualification"]["pointer"], "")
        self.assertEqual(blob(REPO_ROOT, entry["qualification"]["path"]), entry["qualification"]["blob"])
        qualification = json.loads((REPO_ROOT / entry["qualification"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual(qualification["status"], "pending")
        self.assertIsNone(entry["published_commit"])
        record = json.loads((REPO_ROOT / entry["record"]).read_text(encoding="utf-8"))
        boundary = json.loads((REPO_ROOT / entry["source_boundary"]).read_text(encoding="utf-8"))
        self.assertEqual(record["runtime_revision"]["commit"], V6_FROZEN)
        self.assertEqual(record["runtime_revision"]["merge_pr"], 741)
        self.assertEqual(boundary["frozen_revision"], V6_FROZEN)
        self.assertEqual(record["identity"]["public_contract_version"], "1.6.0")
        self.assertEqual(record["identity"]["ranking"]["active_policy_version"], "3.4.0")
        cross_fact = record["read_semantics"]["cross_fact_currentness"]
        self.assertEqual(cross_fact["authority_effect"], "none")
        self.assertEqual(cross_fact["assertion_filter_version"], "6.1.0")
        self.assertIn("explicit-current recall only", cross_fact["applies_to"])
        contract = record["public_runtime_contract"]
        self.assertEqual(contract["proposition_extractor"]["facade_default"], "off (None)")
        for key in ("proposition", "proposition_extractor"):
            self.assertEqual(contract[key]["contract_version"], "1.6.0")
            self.assertEqual(contract[key]["authority_effect"], "none")
        # remediation advisory V1: v6 is published before holdout acceptance, so the typed proposition
        # and extractor path is unaccepted until R6, and a failed acceptance needs a v7 declaration
        limitation = next(item for item in record["known_limitations"] if item["id"] == "typed_proposition_extractor_unaccepted")
        self.assertEqual(limitation["issue"], 732)
        self.assertIn("UNACCEPTED until the docs/plan-732-remediation.md R6 acceptance", limitation["evidence"])
        self.assertIn("v7 declaration", limitation["evidence"])
        self.assertEqual(record["capabilities"]["typed_write_time_propositions"], "opt_in_unaccepted")
        self.assertIn("unaccepted", record["write_semantics"]["typed_proposition"]["acceptance"])
        self.assertTrue(any("UNACCEPTED" in note and "v7" in note for note in boundary["notes"]))
        scope = next(item for item in record["known_limitations"] if item["id"] == "cross_fact_currentness_scope")
        self.assertEqual(scope["issue"], 732)
        self.assertIn("not measured", scope["evidence"])
        mesa = record["qualification_evidence"]["agentmembench_mesa_formal_v3"]
        self.assertEqual(mesa["m4_win_basis_counts"], {"currentness_mechanism": 250})
        self.assertEqual(mesa["proposition_extractor"], "off")
        self.assertTrue((REPO_ROOT / mesa["report"]).is_file())
        self.assertTrue((REPO_ROOT / mesa["freeze"]).is_file())
        declaration = json.loads((REPO_ROOT / V6_DECLARATION).read_text(encoding="utf-8"))
        self.assertEqual(record["predecessor"]["baseline_id"], V5)
        self.assertEqual(record["predecessor"]["runtime_revision"], V5_FROZEN)
        self.assertEqual(record["predecessor"]["identity_deltas"], declaration["identity_deltas"])
        self.assertEqual(record["predecessor"]["declared_changes"], declaration["declared_changes"])
        self.assertEqual(record["predecessor"]["pyproject_change"], declaration["pyproject_change"])
        self.assertEqual(record["predecessor"]["declaration_blob"], blob(REPO_ROOT, V6_DECLARATION))
        acceptance = record["qualification_evidence"]["successor_lane_acceptance"]
        self.assertEqual(acceptance["declaration_blob"], blob(REPO_ROOT, V6_DECLARATION))
        rows = acceptance["rows"]
        self.assertEqual(len(rows), 9)
        self.assertEqual({row["checker_state"] for row in rows}, {"TRANSITION"})
        for row in rows:
            self.assertIn("-v6:", row["evidence_id"])
            self.assertTrue((REPO_ROOT / row["report"]).is_file(), row["report"])
        manifest = json.loads((REPO_ROOT / entry["public_gauntlet_manifest"]).read_text(encoding="utf-8"))
        adapter = manifest["transport"]["startup"][-1]
        self.assertEqual(adapter, "examples/gauntlet/agent_memory_runtime_baseline_v6_stdio.py")
        self.assertEqual(manifest["system"]["revision"], f"git-commit:{V6_FROZEN}")
        self.assertEqual(manifest["adapter"]["revision"], f"git-blob:{blob(REPO_ROOT, adapter)}")
        self.assertEqual(manifest["metadata"]["baseline_id"], V6)
        source = (REPO_ROOT / adapter).read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V6_FROZEN}"', source)
        self.assertIn('PUBLIC_CONTRACT_VERSION = "1.6.0"', source)
        # the manifest's configuration digest follows the recipe the record names, over the adapter's constants
        constants = {}
        for node in ast.parse(source).body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and len(node.targets) == 1:
                constants[getattr(node.targets[0], "id", "")] = node.value.value
        identity = {
            "runtime_profile": manifest["metadata"]["runtime_profile"],
            "public_contract": constants["PUBLIC_CONTRACT_VERSION"],
            "frozen_runtime_revision": constants["FROZEN_RUNTIME_REVISION"],
            "tenant": constants["TENANT"],
            "actor": constants["ACTOR"],
            "scope": constants["SCOPE"],
            "purpose": constants["PURPOSE"],
        }
        digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(manifest["system"]["configuration_digest"], f"sha256:{digest}")
        v5_source = (REPO_ROOT / "examples/gauntlet/agent_memory_runtime_baseline_v5_stdio.py").read_text(encoding="utf-8")
        self.assertIn(f'FROZEN_RUNTIME_REVISION = "{V5_FROZEN}"', v5_source, "the v5 adapter keeps its constants")
        self.assertIn('PUBLIC_CONTRACT_VERSION = "1.5.0"', v5_source, "the v5 adapter keeps its constants")

    def test_v6_rendering_is_byte_identical(self) -> None:
        register = checker.load_register(REPO_ROOT, REGISTER)
        output, rendered = renderer.render_entry(REPO_ROOT, register["baselines"][-1])
        self.assertEqual(output, REPO_ROOT / "reports/runtime/baseline-v6.md")
        self.assertEqual(rendered, output.read_text(encoding="utf-8"))
        self.assertIn("public Gauntlet path: **pending** via `stdio`", rendered)
        self.assertIn("**typed_proposition_extractor_unaccepted** (#732)", rendered)
        self.assertIn("Runtime Baseline v7 declaration", rendered)

    def test_contestant_workflows_retire_a_predecessor_pin_truthfully(self) -> None:
        # docs/67 Step B1: a contestant that pins a predecessor baseline is skipped with a notice,
        # never run as evidence for the current revision and never red forever.
        for workflow in (".github/workflows/agmi-agent-memory-qualification.yml", ".github/workflows/gauntlet-durability-recovery.yml"):
            text = (REPO_ROOT / workflow).read_text(encoding="utf-8")
            self.assertIn("id: contestant", text, workflow)
            self.assertIn("Retired contestant notice", text, workflow)
            self.assertIn("steps.classify.outputs.state == 'PASS' && steps.contestant.outputs.contestant == 'current'", text, workflow)
            self.assertNotIn("        if: steps.classify.outputs.state == 'PASS'\n", text, workflow)

    def test_workflows_carry_no_literal_v1_revision(self) -> None:
        workflows = [
            ".github/workflows/runtime-baseline.yml",
            ".github/workflows/agmi-agent-memory-qualification.yml",
            ".github/workflows/gauntlet-durability-recovery.yml",
        ]
        literals = ("f2aef57293b516e065cad5d0afea26ac7e3c28a9", "32783fad3c5cf50a9d712c8bcc0a023907ce9433", "agent-memory-runtime-baseline-v1")
        for workflow in workflows:
            text = (REPO_ROOT / workflow).read_text(encoding="utf-8")
            for line in text.splitlines():
                if line.lstrip().startswith("- '"):
                    continue
                for literal in literals:
                    self.assertNotIn(literal, line, f"{workflow}: {line.strip()}")
            self.assertEqual(text.count("--candidate HEAD"), 1, workflow)
            lines = text.splitlines()
            checker_line = next(i for i, line in enumerate(lines) if "--candidate HEAD" in line)
            classify = next(i for i in range(checker_line, -1, -1) if lines[i].strip() == "id: classify")
            install = next(i for i, line in enumerate(lines) if "pip install -e ." in line)
            self.assertLess(install, classify, workflow)


if __name__ == "__main__":
    unittest.main()
