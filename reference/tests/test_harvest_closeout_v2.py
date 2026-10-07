"""The harvest closeout is data; every row must still be true of the repository (#672).

``reference/fixtures/harvest-closeout-final-v2.json`` classifies every harvested mechanism as
shipped, tranche or declined. This test is a pure function of committed files: it checks the
vocabulary, that every v1 mechanism and every Jev-Mem id is covered exactly once, that cited
modules exist, that shipped evidence resolves to complete lane rows, workflows or paths, that
tranche rows carry an issue and a lane gate, and that the rc1 closeout manifest agrees.
"""

from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "reference"))

from run_rc1_evidence_closeout import build_manifest  # noqa: E402

V2 = REPO_ROOT / "reference" / "fixtures" / "harvest-closeout-final-v2.json"
V1 = REPO_ROOT / "reference" / "fixtures" / "harvest-closeout-final-v1.json"
JEV_MEM = REPO_ROOT / "docs" / "research-jev-mem-harvest.md"
INTEGRATIONS = REPO_ROOT / "reference" / "agentmem_ref" / "evaluation" / "integrations"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
POLICY = REPO_ROOT / "data" / "github-actions-workflow-policy.json"
REGISTRY = REPO_ROOT / "sources" / "source-registry.json"

# Phase 3 of docs/plan-672-tranche-5-harvests.md: tranche rows whose issue does not exist yet.
EXPECTED_UNASSIGNED: list[str] = []

SHIPPED_REACH = {"facade", "evaluation_only"}
TRANCHE_REACH = {"library_only", "harness_only", "absent"}
CLASSES = {"identity", "authority", "interop", "evaluation_discipline"}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ref_key(ref: dict | None) -> tuple | None:
    if ref is None:
        return None
    if "id" in ref:
        return ("jev-mem", ref["id"])
    return (ref["source"], ref["mechanism"])


def v1_keys() -> set[tuple]:
    return {(s["source"], m["mechanism"]) for s in load(V1)["sources"] for m in s["mechanisms"]}


def jev_mem_keys() -> set[tuple]:
    ids = re.findall(r"^\| (JH-\d\d) \|", JEV_MEM.read_text(encoding="utf-8"), flags=re.M)
    return {("jev-mem", item) for item in ids}


def coverage(fixture: dict) -> list[tuple]:
    keys = [ref_key(row["v1_ref"]) for row in fixture["rows"] if row["v1_ref"] is not None and not row.get("v1_ref_shared")]
    keys += [ref_key(item["v1_ref"]) for item in fixture["out_of_mechanism_scope"]]
    return keys


def evidence_resolves(item: dict) -> bool:
    if "integration" in item:
        history = load(INTEGRATIONS / item["integration"])["evidence_history"]
        return any(e.get("variant") == item["variant"] and e.get("status") == "complete" for e in history)
    if "workflow" in item:
        return (WORKFLOWS / item["workflow"]).exists() and item["workflow"] in load(POLICY)["workflows"]
    return (REPO_ROOT / item["path"]).exists()


def violations(fixture: dict) -> list[str]:
    """Every rule of the plan's LD1/LD2 as one list of offences; empty means the record holds."""
    found: list[str] = []
    ids = [row["row_id"] for row in fixture["rows"]]
    if len(ids) != len(set(ids)):
        found.append("duplicate row_id")
    for row in fixture["rows"]:
        found += row_violations(fixture, row)
    for item in fixture["out_of_mechanism_scope"]:
        if item["class"] not in CLASSES:
            found.append(f"{item['v1_ref']}: class {item['class']}")
    covered = coverage(fixture)
    expected = v1_keys() | jev_mem_keys()
    if sorted(covered) != sorted(expected):
        found.append(f"coverage: missing {sorted(expected - set(covered))}, extra {sorted(set(covered) - expected)}, duplicates {len(covered) - len(set(covered))}")
    return found


def row_violations(fixture: dict, row: dict) -> list[str]:
    found: list[str] = []
    rid = row["row_id"]
    if row["disposition"] not in fixture["dispositions"] or row["reachability"] not in fixture["reachability"]:
        found.append(f"{rid}: vocabulary")
    for module in row["modules"]:
        if not (REPO_ROOT / module).exists():
            found.append(f"{rid}: missing module {module}")
    if row["disposition"] == "shipped" and (row["reachability"] not in SHIPPED_REACH or not row["evidence"]):
        found.append(f"{rid}: shipped rows need facade/evaluation reachability and evidence")
    if row["disposition"] == "tranche" and (row["reachability"] not in TRANCHE_REACH or "tranche" not in row or not row.get("reason")):
        found.append(f"{rid}: tranche rows need library/harness/absent reachability, a tranche block and a reason")
    if row["disposition"] == "declined" and ("tranche" in row or not row.get("reason")):
        found.append(f"{rid}: declined rows need a reason and no tranche block")
    for item in row["evidence"]:
        if not evidence_resolves(item):
            found.append(f"{rid}: evidence does not resolve {item}")
    tranche = row.get("tranche")
    if tranche and (not tranche.get("lane_gate") or not tranche.get("order")):
        found.append(f"{rid}: tranche needs lane_gate and order")
    if tranche and not isinstance(tranche.get("issue"), int) and rid not in EXPECTED_UNASSIGNED:
        found.append(f"{rid}: tranche without an issue")
    return found


class HarvestCloseoutV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load(V2)

    def test_record_holds_against_the_repository(self) -> None:
        self.assertEqual(violations(self.fixture), [])

    def test_status_and_supersession(self) -> None:
        self.assertEqual(self.fixture["status"], "complete_mechanism_closeout")
        self.assertEqual(self.fixture["supersedes"]["artifact_id"], load(V1)["artifact_id"])
        self.assertTrue((REPO_ROOT / self.fixture["supersedes"]["path"]).exists())
        self.assertRegex(self.fixture["evaluated_against_agent_memory_revision"], r"^[0-9a-f]{40}$")

    def test_rc1_closeout_manifest_agrees(self) -> None:
        harvest = build_manifest("0" * 40)["harvest_closeout"]
        self.assertEqual(harvest["status"], self.fixture["status"])
        self.assertEqual(harvest["issue"], self.fixture["issue"])
        self.assertEqual(harvest["artifact"], "reference/fixtures/harvest-closeout-final-v2.json")

    def test_blocked_evidence_fails(self) -> None:
        broken = copy.deepcopy(self.fixture)
        shipped = next(row for row in broken["rows"] if row["disposition"] == "shipped" and any("integration" in e for e in row["evidence"]))
        shipped["evidence"] = [{"integration": "amb-precisionmembench-retrieval-v1.json", "variant": "lane:amb-precisionmembench-retrieval-v2:hindsight"}]
        self.assertTrue(any("does not resolve" in v for v in violations(broken)))

    def test_dropped_mechanism_fails_coverage(self) -> None:
        broken = copy.deepcopy(self.fixture)
        broken["out_of_mechanism_scope"].pop()
        self.assertTrue(any(v.startswith("coverage") for v in violations(broken)))

    def test_jev_mem_tranches_require_the_registry_record(self) -> None:
        needs_record = any(row.get("tranche") and (row["v1_ref"] or {}).get("doc") == "docs/research-jev-mem-harvest.md" for row in self.fixture["rows"])
        records = {record["source_id"]: record for record in load(REGISTRY)["sources"]}
        self.assertTrue(needs_record)
        self.assertIn("jev-mem", sorted(records))
        self.assertTrue(records["jev-mem"]["notice_required"])
        self.assertTrue(records["jev-mem"]["attribution_required"])


if __name__ == "__main__":
    unittest.main()
