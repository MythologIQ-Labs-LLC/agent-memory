"""The -v5 same-harness lanes and their harness fields (#671 C9; docs/plan-671-evidence-v5.md E1-E4, E8, A1-A7).

Each -v5 lane equals its accepted -v4 lane field for field except exactly the E4 differences
(with the A7 wording): lane-level fields, the v5 runtime-baseline posture in every Agent Memory
row that has one, the control's display name, the deferred shadow rows (E3), the rewritten
LongMemEval semantic reason (E3), and per lane the runner (LongMemEval) or bridge 0.4.0 (AMB)
pins and the cross-fact identity/artifact requirements. The harness tests pin the E2 fields:
the runner's per-question ``cross_fact`` record and its mechanism-off recompute, the bridge's
``cross-fact.jsonl`` sidecar (agent-memory only), the importers' refusals, the E1 attribution
script, and A4's no-effect property of the extra read.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from agentmem_ref import AgentMemory
from agentmem_ref.evaluation.registry import get_integration
from agentmem_ref.evaluation.same_harness_lane import get_lane, lane_digest, resolve_lane, validate_lane
from agentmem_ref.runtime import runtime_composition

from tests.test_same_harness_lanes_v3 import POSTURE, SEMANTIC_KEY, _as_frozen, _flat

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCE = REPO_ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

import cross_fact_mechanism_off as cfm  # noqa: E402

V5_DECLARATION = "reports/runtime/baseline-v5-declaration.json"
SHADOW_REASON = ("deferred at freeze (plan-671-evidence-v5 E3): measured at -v4 (jh-14 shipped); "
                 "the next controller measurement belongs to T-controller-2's lanes")
LME_SEMANTIC_REASON = ("deferred at freeze (plan-671-evidence-v5 E3): the semantic route is unchanged since -v3, where its "
                       "ordering effect was measured (plan-669-lanes-v3 D2); ranking policy 3.3.0 adds only explicit-current "
                       "cross-fact applicability, which never reads similarity; the next measurement belongs to #673's lanes")
DENVER = "The user lives in Denver."
BOSTON = "The user has moved and now lives in Boston."
CURRENT_QUERY = "Where does the user currently live?"
PLAIN_QUERY = "Where does the user live?"


def _blob(path: str) -> str:
    return subprocess.run(["git", "hash-object", str(REPO_ROOT / path)], capture_output=True, text=True, check=True).stdout.strip()


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = _load("run_longmemeval", REFERENCE / "run_longmemeval.py")
LME_IMPORT = _load("import_longmemeval_lane_evidence", REPO_ROOT / "scripts" / "import_longmemeval_lane_evidence.py")
AMB_IMPORT = _load("import_amb_lane_evidence", REPO_ROOT / "scripts" / "import_amb_lane_evidence.py")
ATTRIBUTION = _load("check_cross_fact_attribution", REPO_ROOT / "scripts" / "check_cross_fact_attribution.py")

# frozen_on is listed by E4 but equals -v4's date (both froze on 2026-10-07), so it shows no difference.
LANE_LEVEL = {"/lane_id", "/owning_issue", "/description", "/freeze_rationale", "/comparability/notes",
              "/comparability/not_comparable_to"}


# =========================================================================== lane files (E3, E4)
class _V5LaneMixin:
    lane_id: str
    v4_id: str
    control_key: str
    shadow_key: str
    blob_path: str
    extra_differences: set[str]
    workflow_path: str

    def _lane(self) -> dict:
        return get_lane(self.lane_id)

    def _v4(self) -> dict:
        return get_lane(self.v4_id)

    def test_lane_validates_resolves_and_is_frozen_before_any_score(self):
        lane = validate_lane(self._lane())
        resolve_lane(lane)
        self.assertEqual(lane["status"], "accepted")  # accepted at META_LEDGER Entry #109
        self.assertIs(lane["frozen_before_any_score"], True)
        self.assertEqual(lane["owning_issue"], 671)
        self.assertEqual(lane["frozen_on"], "2026-10-07")

    def test_differs_from_v4_by_exactly_the_e4_list(self):
        v4, v5 = _flat(_as_frozen(self._v4())), _flat(_as_frozen(self._lane()))
        changed = {path for path in set(v4) | set(v5) if v4.get(path, "<absent>") != v5.get(path, "<absent>")}
        allowed = (
            LANE_LEVEL
            | {f"/systems/{self.control_key}{suffix}" for suffix in POSTURE | {"/display_name"}}
            | {f"/systems/{self.shadow_key}{suffix}" for suffix in POSTURE | {"/status", "/status_reason", "/adapter/revision_rule"}}
            | self.extra_differences
        )
        self.assertEqual(changed, allowed)

    def test_rows_findings_and_statuses_follow_e4(self):
        v4, lane = self._v4(), _as_frozen(self._lane())
        self.assertEqual(lane["findings"], [item for item in v4["findings"] if not item.startswith("accepted rows ")])  # IA1
        self.assertEqual(len(lane["findings"]), len(v4["findings"]) - 1)
        before = {row["provider_key"]: row for row in v4["systems"]}
        self.assertEqual([row["provider_key"] for row in lane["systems"]], list(before))
        for row in lane["systems"]:
            key = row["provider_key"]
            if key == self.shadow_key:
                self.assertEqual((row["status"], row["status_reason"]), ("deferred", SHADOW_REASON))
            elif before[key]["status"] == "accepted":
                self.assertEqual(row["status"], "frozen", key)
                self.assertNotIn("status_reason", row)
            else:
                self.assertEqual(row["status"], "deferred", key)

    def test_accepted_rows_are_bound_to_evidence_executed_under_the_v5_transition(self):
        # plan-671-evidence-v5 E7 step 6: every executed row is accepted and bound by its
        # evidence_history entries; deferred rows are recorded as blocked. Acceptance adds only
        # statuses, status_reasons and one findings note, so undoing them gives the executed digest.
        lane = self._lane()
        self.assertEqual(lane["status"], "accepted")
        integration = get_integration(lane["benchmark_integration"])
        history = {entry["variant"]: entry for entry in integration["evidence_history"]}
        for row in lane["systems"]:
            prefix = f"lane:{self.lane_id}:{row['provider_key']}"
            variants = [variant for variant in history if variant == prefix or variant.startswith(prefix + ":")]
            if row["status"] == "deferred":
                self.assertEqual([history[v]["status"] for v in variants], ["blocked"], row["row_id"])
                continue
            self.assertEqual(row["status"], "accepted", row["row_id"])
            self.assertEqual(len(variants), self.planes_per_row, row["row_id"])
            for variant in variants:
                entry = history[variant]
                self.assertEqual(entry["status"], "complete")
                self.assertIn(variant, row["status_reason"])
                record = json.loads((REPO_ROOT / entry["report"]).read_text(encoding="utf-8"))
                self.assertEqual(record["row"]["provider_key"], row["provider_key"])
                binding = record["system"]["runtime_baseline"]
                self.assertEqual(binding["state"], "TRANSITION")
                self.assertEqual(binding["declared_successor"], "agent-memory-runtime-baseline-v5")
                self.assertEqual(record["lane_digest_at_execution"], lane_digest(_as_frozen(lane)))
                self.assertEqual(record["lane_digest_at_execution"], record["execution"]["lane_digest_sha256"])
                # as at -v4: the LongMemEval entries name their normalized manifests; AMB entries do not
                self.assertEqual(bool(entry.get("normalized_reports")), self.planes_per_row == 2, variant)
                for path in entry.get("normalized_reports", []):
                    self.assertTrue((REPO_ROOT / path).is_file(), path)
        self.assertTrue(any("0 UNATTRIBUTED" in item for item in lane["findings"]))

    def test_control_runs_the_facade_default_under_the_v5_transition(self):
        lane = self._lane()
        control = next(row for row in lane["systems"] if row["role"] == "control")
        self.assertEqual(control["provider_key"], self.control_key)
        configuration = control["configuration"]
        self.assertNotIn("recall_control", configuration)
        self.assertNotIn("semantic_retrieval", configuration)
        self.assertEqual(control["display_name"], "Agent Memory (public facade, declared transition to Runtime Baseline v5)")
        expected = {
            "predecessor": "agent-memory-runtime-baseline-v4",
            "declared_successor": "agent-memory-runtime-baseline-v5",
            "declaration": V5_DECLARATION,
            "declaration_blob": _blob(V5_DECLARATION),
            "checker_state_required": ["PASS", "TRANSITION"],
        }
        carrying = [row for row in lane["systems"] if "runtime_baseline_posture" in (row.get("configuration") or {})]
        self.assertEqual({row["provider_key"] for row in carrying}, self.posture_rows)
        for row in carrying:
            self.assertEqual(row["configuration"]["runtime_baseline_posture"], expected, row["provider_key"])
        declaration = json.loads((REPO_ROOT / V5_DECLARATION).read_text(encoding="utf-8"))
        self.assertIn({"kind": "lane", "ref": self.lane_id}, declaration["acceptance_evidence_required"])

    def test_comparability_states_causal_attribution_not_equality(self):
        lane = self._lane()
        first = lane["comparability"]["not_comparable_to"][0]
        self.assertTrue(first.startswith(f"{self.v4_id} rows for the same system"))
        self.assertIn("causally attributed (plan-671-evidence-v5 E1", first)
        self.assertIn("not equality", first)
        notes = lane["comparability"]["notes"]
        self.assertFalse(any("plan-644-lanes-v4 L1" in note or "row is the control's system" in note for note in notes))
        self.assertIn("plan-671-evidence-v5 E1 causal attribution rule", notes[-2])
        rationale = " ".join(lane["freeze_rationale"])
        for phrase in ("small, possibly zero", "scripts/check_cross_fact_attribution.py", "reported, never gated", "jh-14 shipped"):
            self.assertIn(phrase, rationale)

    def test_the_v4_blob_is_gone_and_the_new_blob_is_pinned(self):
        lane = self._lane()
        old = self._v4()["harness"]["source_blobs"][self.blob_path]
        new = lane["harness"]["source_blobs"][self.blob_path]
        self.assertNotIn(old, json.dumps(lane))
        self.assertEqual(new, _blob(self.blob_path))  # frozen: the pin is HEAD's blob until runs bind it
        before = {row["provider_key"]: row for row in self._v4()["systems"]}
        rewritten = [row for row in lane["systems"] if old in (before[row["provider_key"]]["adapter"].get("revision_rule") or "")]
        self.assertIn(self.control_key, {row["provider_key"] for row in rewritten})
        for row in rewritten:
            self.assertEqual(row["adapter"]["revision_rule"], before[row["provider_key"]]["adapter"]["revision_rule"].replace(old, new).replace(
                "bridge_version 0.3.0", "bridge_version 0.4.0"), row["provider_key"])

    def test_workflow_offers_and_defaults_to_this_lane(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        self.assertIn(f"- {self.lane_id}", workflow)
        self.assertIn(f"- {self.v4_id}", workflow)
        self.assertIn(f'default: "{self.lane_id}"', workflow)
        self.assertIn('lane["status"] == "frozen"', workflow)  # an accepted lane is refused


class LongMemEvalParityV5LaneTests(_V5LaneMixin, unittest.TestCase):
    planes_per_row = 2
    lane_id = "longmemeval-s-retrieval-parity-v5"
    v4_id = "longmemeval-s-retrieval-parity-v4"
    control_key = "agent_memory"
    shadow_key = "agent_memory_shadow"
    blob_path = "reference/run_longmemeval.py"
    posture_rows = {"agent_memory", "agent_memory_shadow", SEMANTIC_KEY}
    workflow_path = ".github/workflows/longmemeval-competitive.yml"
    extra_differences = {
        "/harness/source_blobs/reference/run_longmemeval.py",
        "/evaluator/scorer",
        "/systems/agent_memory/adapter/revision_rule",
        "/systems/lexical_overlap/source/revision",
        f"/systems/{SEMANTIC_KEY}/adapter/revision_rule",
        f"/systems/{SEMANTIC_KEY}/status_reason",
        *{f"/systems/{SEMANTIC_KEY}{suffix}" for suffix in POSTURE},
        "/execution/environment/dispatch_unit",
        "/execution/execution_identity_requirements",
    }

    def test_runner_blob_replaced_in_every_occurrence(self):
        lane = self._lane()
        new = lane["harness"]["source_blobs"]["reference/run_longmemeval.py"]
        self.assertIn(new, lane["evaluator"]["scorer"])
        self.assertEqual(next(row for row in lane["systems"] if row["role"] == "baseline")["source"]["revision"], new)
        for key in ("agent_memory", "agent_memory_shadow", SEMANTIC_KEY):
            row = next(row for row in lane["systems"] if row["provider_key"] == key)
            self.assertIn(new, row["adapter"]["revision_rule"], key)

    def test_semantic_row_takes_the_e3_reason_and_keeps_its_declaration(self):
        lane = self._lane()
        row = next(row for row in lane["systems"] if row["provider_key"] == SEMANTIC_KEY)
        v4_row = next(row for row in self._v4()["systems"] if row["provider_key"] == SEMANTIC_KEY)
        self.assertEqual((row["status"], row["status_reason"]), ("deferred", LME_SEMANTIC_REASON))
        self.assertNotIn("3.2.0", row["status_reason"])
        self.assertEqual(row["configuration"]["semantic_representation"], v4_row["configuration"]["semantic_representation"])
        self.assertEqual(row["display_name"], v4_row["display_name"])

    def test_dispatch_unit_and_identity_requirements(self):
        lane, v4 = self._lane(), self._v4()
        dispatch = lane["execution"]["environment"]["dispatch_unit"]
        self.assertIn("lane_id longmemeval-s-retrieval-parity-v5", dispatch)
        self.assertIn("{agent_memory, lexical_overlap, mem0_explicit}", dispatch)
        self.assertNotIn("shadow", dispatch)
        old, new = v4["execution"]["execution_identity_requirements"], lane["execution"]["execution_identity_requirements"]
        expected = []
        for line in old:
            if line.startswith("agent_memory_shadow:"):
                continue  # E4: the -v4 shadow line is removed
            if line.startswith("execution.agent_memory_configuration =="):
                # A7: only the agent_memory_shadow clause is dropped; recall_control: off stays
                line = line.replace(" or the same with recall_control: shadow (agent_memory_shadow)", "")
                self.assertIn("recall_control: off}", line)
            expected.append(line)
        self.assertEqual(new[:-1], expected)
        self.assertEqual(len(new), len(old))
        self.assertTrue(new[-1].startswith("every error-free agent_memory question carries a cross_fact record"))
        self.assertTrue(new[-1].endswith("no other row carries one"))


class AmbPrecisionMemBenchV5LaneTests(_V5LaneMixin, unittest.TestCase):
    planes_per_row = 1
    lane_id = "amb-precisionmembench-retrieval-v5"
    v4_id = "amb-precisionmembench-retrieval-v4"
    control_key = "agent-memory"
    shadow_key = "agent-memory-shadow"
    blob_path = "reference/amb_agent_memory_bridge.py"
    posture_rows = {"agent-memory", "agent-memory-shadow"}  # A7: the AMB semantic row carries none
    workflow_path = ".github/workflows/amb-competitive.yml"
    extra_differences = {
        "/harness/source_blobs/reference/amb_agent_memory_bridge.py",
        "/systems/agent-memory/adapter/revision_rule",
        "/execution/execution_identity_requirements",
        "/execution/artifact_requirements",
    }

    def test_bridge_0_4_0_is_pinned_and_the_semantic_row_is_unchanged(self):
        import amb_agent_memory_bridge as bridge

        lane = self._lane()
        self.assertEqual(bridge.BRIDGE_VERSION, "0.4.0")
        self.assertNotIn("0.3.0", json.dumps(lane))
        for key in ("agent-memory", "agent-memory-shadow"):
            row = next(row for row in lane["systems"] if row["provider_key"] == key)
            self.assertIn("bridge_version 0.4.0", row["adapter"]["revision_rule"])
        row = next(row for row in lane["systems"] if row["provider_key"] == SEMANTIC_KEY)
        self.assertEqual(row, next(row for row in self._v4()["systems"] if row["provider_key"] == SEMANTIC_KEY))
        self.assertNotIn("runtime_baseline_posture", row["configuration"])

    def test_sidecar_lines_are_replaced_not_appended(self):
        lane, v4 = self._lane(), self._v4()
        for field, old_marker, new_start in (
            ("artifact_requirements", "written by bridge 0.3.0", "cross-fact.jsonl, written by bridge 0.4.0, on the agent-memory row only"),
            ("execution_identity_requirements", "every other row's artifact carries no sidecar",
             "the agent-memory row's artifact carries cross-fact.jsonl with exactly one joined record per non-blank-query case"),
        ):
            old, new = v4["execution"][field], lane["execution"][field]
            self.assertEqual(len(old), len(new), field)
            index = next(i for i, line in enumerate(old) if old_marker in line)
            self.assertEqual(new[:index] + new[index + 1:], old[:index] + old[index + 1:], field)
            self.assertTrue(new[index].startswith(new_start), field)
        self.assertTrue(lane["execution"]["execution_identity_requirements"][-1].endswith("every other row's artifact carries neither sidecar"))
        self.assertFalse(any("recall-control.jsonl" in line for line in lane["execution"]["artifact_requirements"]))

    def test_workflow_sets_the_cross_fact_sidecar_for_agent_memory_only(self):
        workflow = (REPO_ROOT / self.workflow_path).read_text(encoding="utf-8")
        block = 'if [ "${{ inputs.memory }}" = "agent-memory" ]; then'
        self.assertEqual(workflow.count(block), 1)
        self.assertIn('export AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR="$RUNNER_TEMP/amb-output/cross-fact.jsonl"', workflow.split(block)[1].split("fi\n")[0])
        self.assertEqual(workflow.count("AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR"), 1)


# =========================================================================== mechanism off (E2, A4)
class MechanismOffTests(unittest.TestCase):
    def _store(self) -> tuple[AgentMemory, dict[str, str]]:
        memory = AgentMemory.open(tempfile.mkdtemp(), tenant="tenant:v5", actor_id="agent:v5", scope="benchmark:v5", purpose="v5 lane test")
        names = {memory.remember("memory:denver", DENVER)["fact_uuid"]: "denver",
                 memory.remember("memory:boston", BOSTON)["fact_uuid"]: "boston"}
        return memory, names

    def test_the_report_and_the_lanes_share_one_definition(self):
        sys.path.insert(0, str(REFERENCE / "tests"))
        report = _load("run_cross_fact_currentness_report", REFERENCE / "run_cross_fact_currentness_report.py")
        self.assertIs(report.mechanism, cfm.mechanism)
        runtime_tree = REFERENCE / "agentmem_ref"
        for path in runtime_tree.rglob("*.py"):
            self.assertNotIn("cross_fact_mechanism_off", path.read_text(encoding="utf-8"), path)

    def test_off_restores_the_live_policy_even_on_error(self):
        live = runtime_composition.MULTI_ROUTE_RANKING_POLICY
        with self.assertRaises(RuntimeError):
            with cfm.mechanism("off"):
                self.assertIsInstance(runtime_composition.MULTI_ROUTE_RANKING_POLICY, cfm.LegacyRankingPolicy)
                raise RuntimeError("boom")
        self.assertIs(runtime_composition.MULTI_ROUTE_RANKING_POLICY, live)
        with cfm.mechanism("on"):
            self.assertIs(runtime_composition.MULTI_ROUTE_RANKING_POLICY, live)
        with self.assertRaises(ValueError):
            with cfm.mechanism("maybe"):
                pass
        self.assertIs(runtime_composition.MULTI_ROUTE_RANKING_POLICY, live)
        self.assertIn("3.2.0", json.dumps(cfm.LegacyRankingPolicy(live).identity()))
        self.assertNotIn("3.3.0", json.dumps(cfm.LegacyRankingPolicy(live).identity()))

    def test_a_limited_pair_reorders_and_the_extra_read_changes_no_later_recall(self):
        memory, names = self._store()
        try:
            first = memory.recall(CURRENT_QUERY, budget=50)
            with cfm.mechanism("off"):
                off = memory.recall(CURRENT_QUERY, budget=50)
            again = memory.recall(CURRENT_QUERY, budget=50)
        finally:
            memory.close()
        self.assertEqual([names[ref] for ref in first["returned"]], ["boston", "denver"])
        self.assertEqual([names[ref] for ref in off["returned"]], ["denver", "boston"])
        self.assertEqual([names[ref] for ref in cfm.limited_refs(first)], ["denver"])
        self.assertEqual(cfm.limited_refs(off), [])
        self.assertEqual(again["returned"], first["returned"])
        self.assertEqual(again["admitted"], first["admitted"])
        for ref in first["admitted"]:
            self.assertEqual(again["admissions"][ref]["ranking_evidence"], first["admissions"][ref]["ranking_evidence"])


# =========================================================================== runner (E2)
def _lme_fixture(path: Path, question: str) -> Path:
    rows = [{
        "question_id": "v5_cross_fact_pair",
        "question_type": "knowledge-update",
        "question": question,
        "answer": "Boston",
        "question_date": "2026/09/01 (Tue) 10:00",
        "haystack_session_ids": ["v5_denver", "answer_v5_boston", "v5_filler"],
        "haystack_dates": ["2026/08/01 (Sat) 09:00", "2026/08/20 (Thu) 09:00", "2026/08/21 (Fri) 09:00"],
        "haystack_sessions": [
            [{"role": "user", "content": DENVER}],
            [{"role": "user", "content": BOSTON, "has_answer": True}],
            [{"role": "user", "content": "Lunch today was tomato soup."}],
        ],
        "answer_session_ids": ["answer_v5_boston"],
    }]
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


class RunnerCrossFactRecordTests(unittest.TestCase):
    def setUp(self):
        RUNNER.configure_agent_memory(budget=50)
        self.addCleanup(RUNNER.configure_agent_memory)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)

    def _run(self, question: str, backends=("agent_memory", "lexical_overlap")) -> dict:
        fixture = _lme_fixture(Path(self.temporary.name) / "fixture.json", question)
        return RUNNER.run(fixture, corpus_class="synthetic", backends=backends)

    def test_limited_pair_records_the_limitation_and_the_mechanism_off_ranking(self):
        live = runtime_composition.MULTI_ROUTE_RANKING_POLICY
        report = self._run(CURRENT_QUERY)
        self.assertIs(runtime_composition.MULTI_ROUTE_RANKING_POLICY, live)
        for plane, ids in (("session", ("v5_denver", "answer_v5_boston")), ("turn", ("v5_denver_1", "answer_v5_boston_1"))):
            native = report["planes"][plane]["backends"]["agent_memory"]
            row = native["rows"][0]
            denver, boston = ids
            self.assertEqual(row["ranked_top"][:2], [boston, denver], plane)
            record = row["cross_fact"]
            self.assertEqual(set(record), {"limited_count", "limited_item_ids", "refusal_counts", "ranked_top_mechanism_off"})
            self.assertEqual((record["limited_count"], record["limited_item_ids"]), (1, [denver]))
            self.assertEqual(record["ranked_top_mechanism_off"][:2], [denver, boston])
            self.assertEqual(sorted(record["ranked_top_mechanism_off"]), sorted(row["ranked_top"]))
            self.assertEqual(native["cross_fact_summary"], {
                "questions_with_record": 1, "questions_with_limited": 1, "limited_total": 1,
                "refusal_counts": record["refusal_counts"], "authority_effect": "none",
            })
            lexical = report["planes"][plane]["backends"]["lexical_overlap"]
            self.assertNotIn("cross_fact_summary", lexical)
            self.assertNotIn("cross_fact", lexical["rows"][0])

    def test_unlimited_question_records_null_mechanism_off_and_runs_no_extra_read(self):
        with mock.patch.object(RUNNER, "mechanism", wraps=RUNNER.mechanism) as wrapped:
            report = self._run(PLAIN_QUERY, backends=("agent_memory",))
        wrapped.assert_not_called()
        for plane in ("session", "turn"):
            native = report["planes"][plane]["backends"]["agent_memory"]
            record = native["rows"][0]["cross_fact"]
            self.assertEqual((record["limited_count"], record["limited_item_ids"], record["ranked_top_mechanism_off"]), (0, [], None))
            self.assertEqual(native["cross_fact_summary"]["questions_with_limited"], 0)

    def test_on_output_is_identical_whether_or_not_the_off_read_ran(self):
        with_off = self._run(CURRENT_QUERY, backends=("agent_memory",))
        with mock.patch.object(RUNNER, "limited_refs", return_value=[]):
            without_off = self._run(CURRENT_QUERY, backends=("agent_memory",))
        for plane in ("session", "turn"):
            a = with_off["planes"][plane]["backends"]["agent_memory"]["rows"][0]
            b = without_off["planes"][plane]["backends"]["agent_memory"]["rows"][0]
            for key in ("ranked_top", "metrics", "latest_gold_first", "candidate_count", "admitted_count", "refusal_reasons", "return_policy"):
                self.assertEqual(a[key], b[key], (plane, key))
            self.assertIsNotNone(a["cross_fact"]["ranked_top_mechanism_off"])
            self.assertIsNone(b["cross_fact"]["ranked_top_mechanism_off"])

    def test_the_off_read_is_outside_the_timed_span(self):
        clock = iter(range(1000))
        calls: list[str] = []
        real_recall = AgentMemory.recall

        def recall(memory, *args, **kwargs):
            calls.append("recall_off" if isinstance(runtime_composition.MULTI_ROUTE_RANKING_POLICY, cfm.LegacyRankingPolicy) else "recall_on")
            return real_recall(memory, *args, **kwargs)

        def tick():
            calls.append("clock")
            return float(next(clock))

        with mock.patch.object(AgentMemory, "recall", recall), mock.patch.object(RUNNER.time, "perf_counter", tick):
            items = [{"id": "a", "text": DENVER, "date": ""}, {"id": "b", "text": BOSTON, "date": ""}]
            outcome = RUNNER._agent_memory(CURRENT_QUERY, items, 0, {})
        self.assertEqual(outcome["cross_fact"]["limited_item_ids"], ["a"])
        # ingest start, ingest end/recall start, recall end; the off read comes after the last tick
        self.assertEqual(calls, ["clock", "clock", "clock", "recall_on", "clock", "recall_off"])

    def test_error_rows_carry_no_record(self):
        def boom(*args, **kwargs):
            raise RuntimeError("synthetic failure")

        with mock.patch.dict(RUNNER.RETRIEVERS, {"agent_memory": boom}):
            report = self._run(CURRENT_QUERY, backends=("agent_memory",))
        native = report["planes"]["session"]["backends"]["agent_memory"]
        self.assertIsNotNone(native["rows"][0]["runtime_error"])
        self.assertNotIn("cross_fact", native["rows"][0])
        self.assertEqual(native["cross_fact_summary"]["questions_with_record"], 0)


# =========================================================================== bridge (E2, A4)
@dataclass
class FakeDocument:
    id: str
    content: str
    user_id: str | None = None
    messages: list | None = None
    timestamp: str | None = None
    context: str | None = None
    source_ids: list | None = None
    tags: list | None = None


def _fake_amb_modules() -> tuple[dict, dict]:
    memory_bench = types.ModuleType("memory_bench")
    memory = types.ModuleType("memory_bench.memory")
    base = types.ModuleType("memory_bench.memory.base")
    models = types.ModuleType("memory_bench.models")
    memory.REGISTRY = {}
    base.MemoryProvider = type("FakeMemoryProvider", (), {})
    models.Document = FakeDocument
    modules = {"memory_bench": memory_bench, "memory_bench.memory": memory, "memory_bench.memory.base": base, "memory_bench.models": models}
    return modules, memory.REGISTRY


class BridgeCrossFactSidecarTests(unittest.TestCase):
    DOCUMENTS = [
        FakeDocument(id="doc:denver", content=DENVER, user_id="user:v5"),
        FakeDocument(id="doc:boston", content=BOSTON, user_id="user:v5"),
        FakeDocument(id="doc:soup", content="Lunch today was tomato soup.", user_id="user:v5"),
    ]

    def setUp(self):
        import amb_agent_memory_bridge as bridge

        self.bridge = bridge
        modules, self.registry = _fake_amb_modules()
        patcher = mock.patch.dict(sys.modules, modules)
        patcher.start()
        self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ, {})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(bridge.CROSS_FACT_SIDECAR_ENV, None)
        os.environ.pop(bridge.SIDECAR_ENV, None)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.control_type = bridge.install_amb_agent_memory_provider(self.root, agent_memory_revision="5" * 40)

    def _provider(self, name: str, key: str | None = None):
        provider = (self.registry[key] if key else self.control_type)()
        provider.prepare(self.root / name)
        provider.ingest(list(self.DOCUMENTS))
        return provider

    def test_agent_memory_writes_one_cross_fact_record_per_call_when_set(self):
        sidecar = self.root / "out" / "cross-fact.jsonl"
        os.environ[self.bridge.CROSS_FACT_SIDECAR_ENV] = str(sidecar)
        provider = self._provider("control")
        self.assertFalse(sidecar.exists())  # ingest writes nothing
        found, raw = provider.retrieve(CURRENT_QUERY, k=5, user_id="user:v5")
        plain, _ = provider.retrieve(PLAIN_QUERY, k=5, user_id="user:v5")
        self.assertEqual([item.id for item in found][:2], ["doc:boston", "doc:denver"])
        self.assertEqual(raw["bridge_version"], "0.4.0")
        lines = [json.loads(line) for line in sidecar.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertEqual(set(line), set(AMB_IMPORT.CROSS_FACT_RECORD_FIELDS))
        first, second = lines
        self.assertEqual((first["call_index"], second["call_index"]), (0, 1))
        self.assertEqual(first["scope"], self.bridge._scope("user:v5"))
        self.assertEqual(first["query_sha256"], hashlib.sha256(CURRENT_QUERY.encode("utf-8")).hexdigest())
        self.assertEqual(first["budget"], 5)
        self.assertEqual((first["limited_count"], first["limited_document_ids"]), (1, ["doc:denver"]))
        self.assertEqual(first["returned_document_ids"], [item.id for item in found])
        self.assertEqual(first["returned_document_ids_mechanism_off"][:2], ["doc:denver", "doc:boston"])
        self.assertEqual((second["limited_count"], second["returned_document_ids_mechanism_off"]), (0, None))
        self.assertEqual(second["returned_document_ids"], [item.id for item in plain])

    def test_agent_memory_without_the_variable_retrieves_identically_and_writes_nothing(self):
        sidecar = self.root / "out" / "cross-fact.jsonl"
        os.environ[self.bridge.CROSS_FACT_SIDECAR_ENV] = str(sidecar)
        with_sidecar = self._provider("with")
        expected = [[item.id for item in with_sidecar.retrieve(query, k=5, user_id="user:v5")[0]] for query in (CURRENT_QUERY, PLAIN_QUERY)]
        del os.environ[self.bridge.CROSS_FACT_SIDECAR_ENV]
        sidecar.unlink()
        without = self._provider("without")
        found = [[item.id for item in without.retrieve(query, k=5, user_id="user:v5")[0]] for query in (CURRENT_QUERY, PLAIN_QUERY)]
        self.assertEqual(found, expected)
        self.assertFalse(sidecar.exists())

    def test_shadow_provider_keeps_its_v4_behaviour_and_never_writes_the_cross_fact_sidecar(self):
        cross_fact = self.root / "out" / "cross-fact.jsonl"
        recall_control = self.root / "out" / "recall-control.jsonl"
        os.environ[self.bridge.CROSS_FACT_SIDECAR_ENV] = str(cross_fact)
        os.environ[self.bridge.SIDECAR_ENV] = str(recall_control)
        shadow = self._provider("shadow", self.bridge.AMB_SHADOW_PROVIDER_KEY)
        found, raw = shadow.retrieve(CURRENT_QUERY, k=5, user_id="user:v5")
        self.assertEqual(raw["provider"], self.bridge.AMB_SHADOW_PROVIDER_KEY)
        self.assertEqual([item.id for item in found][:2], ["doc:boston", "doc:denver"])
        self.assertFalse(cross_fact.exists())
        lines = recall_control.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(set(json.loads(lines[0])), {"call_index", "scope", "query_sha256", "budget", "recall_control"})
        del os.environ[self.bridge.SIDECAR_ENV]
        with self.assertRaisesRegex(RuntimeError, self.bridge.SIDECAR_ENV):
            shadow.retrieve(CURRENT_QUERY, k=5, user_id="user:v5")

    def test_the_off_read_in_the_durable_store_changes_no_later_recall(self):
        # A4: the off read writes a journal and a governance row to the benchmark store; a later
        # recall on a different query is identical with and without it.
        later = "What did the user have for lunch today?"
        os.environ[self.bridge.CROSS_FACT_SIDECAR_ENV] = str(self.root / "out" / "cross-fact.jsonl")
        with_off = self._provider("with-off")
        with_first, _ = with_off.retrieve(CURRENT_QUERY, k=5, user_id="user:v5")
        with_later, with_raw = with_off.retrieve(later, k=5, user_id="user:v5")
        records = [json.loads(line) for line in (self.root / "out" / "cross-fact.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertIsNotNone(records[0]["returned_document_ids_mechanism_off"])  # the off read ran
        del os.environ[self.bridge.CROSS_FACT_SIDECAR_ENV]
        plain = self._provider("plain")
        plain_first, _ = plain.retrieve(CURRENT_QUERY, k=5, user_id="user:v5")
        plain_later, plain_raw = plain.retrieve(later, k=5, user_id="user:v5")
        self.assertEqual([item.id for item in with_first], [item.id for item in plain_first])
        self.assertEqual([item.id for item in with_later], [item.id for item in plain_later])
        for key in ("candidate_count", "admitted_count", "returned_count", "return_policy", "unmapped_admitted"):
            self.assertEqual(with_raw[key], plain_raw[key], key)


# =========================================================================== importers (E2)
LME_V5_LANE_FILE = "reference/agentmem_ref/evaluation/lanes/longmemeval-s-retrieval-parity-v5.json"
AMB_V5_LANE_FILE = "reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v5.json"
AMB_V4_LANE_FILE = "reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v4.json"
AMB_V4_CONTROL = REPO_ROOT / "reports/benchmarks/amb/amb-precisionmembench-retrieval-v4/agent-memory-f5a79d230a31"
LME_V4_ROOT = REPO_ROOT / "reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v4"


class LongMemEvalImporterCrossFactTests(unittest.TestCase):
    def setUp(self):
        from tests import test_import_longmemeval_lane_evidence as helpers

        self.helpers = helpers
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.runs = Path(self.temporary.name) / "runs"
        self.output = Path(self.temporary.name) / "out"
        self.lane = json.loads((REPO_ROOT / LME_V5_LANE_FILE).read_text(encoding="utf-8"))
        posture = next(row for row in self.lane["systems"] if row["role"] == "control")["configuration"]["runtime_baseline_posture"]
        self.bound = {"runtime_baseline_state": "TRANSITION", "runtime_baseline_line": "Runtime Baseline equivalence: TRANSITION; ...",
                      "declaration_blob": posture["declaration_blob"]}

    def _report(self, backend: str, *, records: bool = True, summary: bool = True, error_index: int | None = None, mutate=None) -> dict:
        external = self.helpers._mem0_external(self.lane) if backend == "mem0_explicit" else None
        built = self.helpers._report(self.lane, backend, "session", external=external)
        built["execution"]["agent_memory_configuration"] = {"temporal_metadata": "none", "ranking_variant": "default", "budget": "50",
                                                             "semantic_retrieval": "off", "recall_control": "off"}
        native = built["planes"]["session"]["backends"][backend]
        if error_index is not None:
            native["rows"][error_index]["runtime_error"] = "RuntimeError: synthetic"
        if records:
            for index, row in enumerate(native["rows"]):
                if row["runtime_error"] is None:
                    limited = 1 if index == 3 else 0
                    row["cross_fact"] = {"limited_count": limited, "limited_item_ids": ["x"] if limited else [], "refusal_counts": {},
                                         "ranked_top_mechanism_off": ["x", f"answer_{index}", "y"] if limited else None}
        if mutate is not None:
            mutate(native)
        if summary and records:
            carrying = [row["cross_fact"] for row in native["rows"] if "cross_fact" in row]
            native["cross_fact_summary"] = RUNNER.cross_fact_summary(carrying)
        return built

    def _import(self, run_id: str, backend: str, report: dict) -> Path:
        self.helpers._write_artifact(self.runs, run_id, backend, "session", report=report, identity_overrides=self.bound, lane_file=LME_V5_LANE_FILE)
        artifact = next((self.runs / run_id).iterdir())
        return LME_IMPORT.import_artifact(run_id, artifact, repo_root=REPO_ROOT, output_root=self.output, fetch=False, lane_at_head=True)

    def test_control_with_records_imports_and_binds_the_summary(self):
        record = json.loads((self._import("8001", "agent_memory", self._report("agent_memory", error_index=7)) / "evidence.json").read_text())
        self.assertEqual(record["system"]["cross_fact_summary"]["questions_with_limited"], 1)
        self.assertEqual(record["system"]["cross_fact_summary"]["questions_with_record"], self.lane["dataset"]["query_count"] - 1)
        self.assertEqual(record["system"]["runtime_baseline"]["declared_successor"], "agent-memory-runtime-baseline-v5")
        lexical = json.loads((self._import("8002", "lexical_overlap", self._report("lexical_overlap", records=False)) / "evidence.json").read_text())
        self.assertIsNone(lexical["system"]["cross_fact_summary"])
        self.assertEqual(LME_IMPORT.lane_generation(self.lane), 5)
        self.assertEqual(LME_IMPORT.lane_generation({"lane_id": "longmemeval-s-retrieval-parity"}), 1)

    def test_refusals(self):
        def drop_one(native):
            del native["rows"][5]["cross_fact"]

        def error_with_record(native):
            native["rows"][7]["cross_fact"] = {"limited_count": 0, "limited_item_ids": [], "refusal_counts": {}, "ranked_top_mechanism_off": None}

        def off_missing(native):
            native["rows"][3]["cross_fact"]["ranked_top_mechanism_off"] = None

        def off_on_unlimited(native):
            native["rows"][4]["cross_fact"]["ranked_top_mechanism_off"] = ["x"]

        def extra_field(native):
            native["rows"][4]["cross_fact"]["note"] = "x"

        cases = [
            ("8101", "agent_memory", self._report("agent_memory", records=False), "lacks a cross_fact record"),
            ("8102", "agent_memory", self._report("agent_memory", mutate=drop_one), "lacks a cross_fact record"),
            ("8103", "agent_memory", self._report("agent_memory", error_index=7, mutate=error_with_record), "runtime error and a cross_fact record"),
            ("8104", "agent_memory", self._report("agent_memory", mutate=off_missing), "null exactly when limited_count is 0"),
            ("8105", "agent_memory", self._report("agent_memory", mutate=off_on_unlimited), "null exactly when limited_count is 0"),
            ("8106", "agent_memory", self._report("agent_memory", summary=False), "cross_fact_summary"),
            ("8107", "agent_memory", self._report("agent_memory", mutate=extra_field), "lacks a cross_fact record"),
            ("8108", "lexical_overlap", self._report("lexical_overlap"), "carries cross_fact records it does not declare"),
            ("8109", "mem0_explicit", self._report("mem0_explicit"), "carries cross_fact records it does not declare"),
        ]
        for run_id, backend, report, message in cases:
            with self.subTest(run_id=run_id), self.assertRaisesRegex(LME_IMPORT.ImportError_, message):
                self._import(run_id, backend, report)

    def test_earlier_generations_refuse_a_cross_fact_record(self):
        v4 = json.loads((REPO_ROOT / "reference/agentmem_ref/evaluation/lanes/longmemeval-s-retrieval-parity-v4.json").read_text(encoding="utf-8"))
        row = next(item for item in v4["systems"] if item["provider_key"] == "agent_memory")
        native = {"rows": [{"question_id": "q", "runtime_error": None, "cross_fact": {}}]}
        with self.assertRaisesRegex(LME_IMPORT.ImportError_, "does not declare"):
            LME_IMPORT.check_cross_fact(native, v4, row)
        self.assertIsNone(LME_IMPORT.check_cross_fact({"rows": [{"question_id": "q", "runtime_error": None}]}, v4, row))


class AmbImporterCrossFactTests(unittest.TestCase):
    def setUp(self):
        from tests import test_import_amb_lane_evidence as helpers

        self.helpers = helpers
        self.results = json.loads((AMB_V4_CONTROL / "single-turn.json").read_text(encoding="utf-8"))["results"]
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def _bound(self, lane_file: str) -> dict:
        lane = json.loads((REPO_ROOT / lane_file).read_text(encoding="utf-8"))
        posture = next(row for row in lane["systems"] if row["role"] == "control")["configuration"]["runtime_baseline_posture"]
        return {
            "bridge_blobs": {path: blob for path, blob in lane["harness"]["source_blobs"].items() if path.startswith("reference/")},
            "lane_digest_sha256": AMB_IMPORT.lane_digest(AMB_IMPORT.validate_lane(lane)),
            "runtime_baseline_state": "TRANSITION",
            "runtime_baseline_line": "Runtime Baseline equivalence: TRANSITION; ...",
            "declaration_blob": posture["declaration_blob"],
        }

    def _lines(self, results=None) -> list[dict]:
        asked = [case for case in (results or self.results) if (case.get("query") or "").strip()]
        lines = []
        for index, case in enumerate(asked):
            limited = 1 if index == 2 else 0
            ids = [f"doc:{index}:a", f"doc:{index}:b"]
            lines.append({"call_index": index, "scope": f"amb:scope:{case['query_id']}",
                          "query_sha256": hashlib.sha256(case["query"].encode("utf-8")).hexdigest(), "budget": 20,
                          "limited_count": limited, "limited_document_ids": ids[1:] if limited else [],
                          "refusal_counts": {"no_open_proposal": 1} if index == 5 else {}, "returned_document_ids": ids,
                          "returned_document_ids_mechanism_off": ids[::-1] if limited else None})
        return lines

    def _run(self, run_id: str, memory: str, lane_file: str, sidecar: list[dict] | None, *, tamper: bool = False) -> Path:
        runs = self.base / run_id / "runs"
        artifact = self.helpers._write_artifact(runs, run_id, memory, "f" * 40, results=self.results,
                                                identity_overrides=self._bound(lane_file), lane_file=lane_file)
        if sidecar is not None:
            payload = "".join(json.dumps(line, sort_keys=True) + "\n" for line in sidecar).encode("utf-8")
            (artifact / "cross-fact.jsonl").write_bytes(payload)
            digest = "0" * 64 if tamper else hashlib.sha256(payload).hexdigest()
            with (artifact / "sha256.txt").open("a", encoding="utf-8") as handle:
                handle.write(f"{digest}  ./cross-fact.jsonl\n")
        out = self.base / run_id / "out"
        with redirect_stdout(io.StringIO()):
            AMB_IMPORT.main(["--runs-dir", str(runs), "--output-root", str(out), "--no-fetch", "--lane-at-head"])
        return next((out / json.loads((REPO_ROOT / lane_file).read_text())["lane_id"]).iterdir())

    def test_v5_control_joins_the_sidecar(self):
        destination = self._run("9001", "agent-memory", AMB_V5_LANE_FILE, self._lines())
        record = json.loads((destination / "evidence.json").read_text(encoding="utf-8"))
        joined = record["cross_fact_sidecar"]
        self.assertEqual((joined["records"], joined["no_recall_executed_cases"]), (73, 4))
        self.assertEqual((joined["cases_with_limited"], joined["limited_total"]), (1, 1))
        self.assertEqual(joined["refusal_counts"], {"no_open_proposal": 1})
        self.assertEqual(joined["sha256"], hashlib.sha256((destination / "cross-fact.jsonl").read_bytes()).hexdigest())
        self.assertEqual(record["files"]["cross-fact.jsonl"], joined["sha256"])
        self.assertIsNone(record["recall_control_sidecar"])
        self.assertEqual(record["system"]["runtime_baseline"]["declared_successor"], "agent-memory-runtime-baseline-v5")
        bm25 = json.loads((self._run("9002", "bm25", AMB_V5_LANE_FILE, None) / "evidence.json").read_text(encoding="utf-8"))
        self.assertIsNone(bm25["cross_fact_sidecar"])

    def test_refusals(self):
        lines = self._lines()
        dup = copy.deepcopy(lines)
        dup.append({**dup[-1], "call_index": len(dup)})
        swapped = copy.deepcopy(lines)
        swapped[5]["query_sha256"], swapped[6]["query_sha256"] = swapped[6]["query_sha256"], swapped[5]["query_sha256"]
        off_missing = copy.deepcopy(lines)
        off_missing[2]["returned_document_ids_mechanism_off"] = None
        off_unlimited = copy.deepcopy(lines)
        off_unlimited[0]["returned_document_ids_mechanism_off"] = ["x"]
        extra = copy.deepcopy(lines)
        extra[0]["recall_control"] = {}
        miscounted = copy.deepcopy(lines)
        miscounted[2]["limited_document_ids"] = []
        cases = [
            ("9101", "agent-memory", AMB_V5_LANE_FILE, None, False, "lacks cross-fact.jsonl"),
            ("9102", "agent-memory", AMB_V5_LANE_FILE, lines[:-1], False, "72 records for 73"),
            ("9103", "agent-memory", AMB_V5_LANE_FILE, dup, False, "adjacent duplicate"),
            ("9104", "agent-memory", AMB_V5_LANE_FILE, [lines[1], lines[0], *lines[2:]], False, "not contiguous"),
            ("9105", "agent-memory", AMB_V5_LANE_FILE, swapped, False, "does not match case"),
            ("9106", "agent-memory", AMB_V5_LANE_FILE, off_missing, False, "null exactly when limited_count is 0"),
            ("9107", "agent-memory", AMB_V5_LANE_FILE, off_unlimited, False, "null exactly when limited_count is 0"),
            ("9108", "agent-memory", AMB_V5_LANE_FILE, extra, False, "exactly the bridge 0.4.0 fields"),
            ("9109", "agent-memory", AMB_V5_LANE_FILE, miscounted, False, "limited_count is malformed"),
            ("9110", "agent-memory", AMB_V5_LANE_FILE, lines, True, "!= inventory"),
            ("9111", "bm25", AMB_V5_LANE_FILE, lines, False, "does not declare cross-fact.jsonl"),
            ("9112", "mem0-explicit", AMB_V5_LANE_FILE, lines, False, "does not declare cross-fact.jsonl"),
            ("9113", "agent-memory", AMB_V4_LANE_FILE, lines, False, "does not declare cross-fact.jsonl"),
        ]
        for run_id, memory, lane_file, sidecar, tamper, message in cases:
            with self.subTest(run_id=run_id), self.assertRaisesRegex(AMB_IMPORT.ImportError_, message):
                self._run(run_id, memory, lane_file, sidecar, tamper=tamper)

    def test_a_blank_query_case_that_shows_a_retrieval_is_refused(self):
        results = copy.deepcopy(self.results)
        blank = next(case for case in results if not (case.get("query") or "").strip())
        blank["meta"]["retrieved_count"] = 1
        with self.assertRaisesRegex(AMB_IMPORT.ImportError_, "shows a retrieval"):
            AMB_IMPORT.join_cross_fact_sidecar([json.dumps(line) for line in self._lines(results)], results)


# =========================================================================== attribution (E1, A5)
class AttributionRendererTests(unittest.TestCase):
    def test_every_committed_v4_amb_context_re_renders_byte_for_byte(self):
        directories = sorted(path for path in (REPO_ROOT / "reports/benchmarks/amb/amb-precisionmembench-retrieval-v4").iterdir() if path.is_dir())
        self.assertEqual(len(directories), 4)
        for directory in directories:
            results = json.loads((directory / "single-turn.json").read_text(encoding="utf-8"))["results"]
            self.assertEqual(len(results), 77, directory.name)
            for case in results:
                documents = ATTRIBUTION.parse_retrieval_context(case["context"])
                self.assertEqual(ATTRIBUTION.render_retrieval_context(documents), case["context"], case["query_id"])

    def test_renderer_matches_the_frozen_lines(self):
        documents = [{"id": "b-1", "source_ids": ["b-1"], "content": "first\n\nwith a blank line"},
                     {"id": "b-2", "source_ids": [], "content": "second"}]
        self.assertEqual(ATTRIBUTION.render_retrieval_context(documents),
                         "## Retrieved memories (2)\n\n1. [b-1] ← b-1\nfirst\n\nwith a blank line\n\n2. [b-2]\nsecond")
        self.assertEqual(ATTRIBUTION.render_retrieval_context([]), "## Retrieved memories (0)")
        self.assertEqual(ATTRIBUTION.parse_retrieval_context(ATTRIBUTION.render_retrieval_context(documents)), documents)


class LongMemEvalAttributionTests(unittest.TestCase):
    @staticmethod
    def _row(question: str, ranked: list[str], *, record=None, error=None, recall=1.0, question_type="multi-session") -> dict:
        row = {"question_id": question, "question_type": question_type, "ranked_top": ranked,
               "metrics": {"recall_all@5": recall, "ndcg_any@5": recall}, "runtime_error": error}
        if record is not None:
            row["cross_fact"] = record
        return row

    @staticmethod
    def _record(limited: int, off=None) -> dict:
        return {"limited_count": limited, "limited_item_ids": ["x"] * limited, "refusal_counts": {}, "ranked_top_mechanism_off": off}

    def test_each_verdict(self):
        v4 = [self._row(f"q{i}", ["a", "b"]) for i in range(8)]
        v4[4] = self._row("q4", [], error="RuntimeError: x", recall=0.0)
        v4[5] = self._row("q5", [], error="RuntimeError: x", recall=0.0)
        v5 = [
            self._row("q0", ["a", "b"], record=self._record(0)),
            self._row("q1", ["b", "a"], record=self._record(1, ["a", "b"]), recall=0.5, question_type="knowledge-update"),
            self._row("q2", ["b", "a"], record=self._record(0), recall=0.5),
            self._row("q3", ["b", "a"], record=self._record(1, ["b", "a"]), recall=0.5),
            self._row("q4", [], error="RuntimeError: x", recall=0.0),
            self._row("q5", [], record=self._record(0), error="RuntimeError: x", recall=0.0),
            self._row("q6", ["a", "b"]),
            self._row("q7", ["a", "b"], record=self._record(1, ["c"])),
        ]
        verdicts = {item["id"]: item for item in ATTRIBUTION.attribute_longmemeval_rows(v4, v5, "session")}
        self.assertEqual({key: item["verdict"] for key, item in verdicts.items()}, {
            "q0": "EQUAL", "q1": "ATTRIBUTED", "q2": "UNATTRIBUTED", "q3": "UNATTRIBUTED",
            "q4": "EQUAL", "q5": "UNATTRIBUTED", "q6": "UNATTRIBUTED", "q7": "EQUAL",
        })
        self.assertEqual(verdicts["q1"]["direction"], "down")
        with self.assertRaises(ATTRIBUTION.AttributionError):
            ATTRIBUTION.attribute_longmemeval_rows(v4, v5[:-1], "session")

    def _v5_tree(self, root: Path, edit=None) -> Path:
        lane = root / "longmemeval-s-retrieval-parity-v5"
        for plane in ("session", "turn"):
            source = next(LME_V4_ROOT.glob(f"agent_memory-{plane}-*"))
            target = lane / f"agent_memory-{plane}-v5v5v5v5v5v5"
            target.mkdir(parents=True)
            (target / "evidence.json").write_bytes((source / "evidence.json").read_bytes())
            with gzip.open(source / "report.rows.json.gz") as handle:
                rows = json.loads(handle.read())
            for row in rows[plane]["agent_memory"]:
                if row["runtime_error"] is None:
                    row["cross_fact"] = self._record(0)
            if edit is not None:
                edit(plane, rows[plane]["agent_memory"])
            with gzip.open(target / "report.rows.json.gz", "wb") as handle:
                handle.write(json.dumps(rows).encode("utf-8"))
        return lane

    def _main(self, v5: Path) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = ATTRIBUTION.main(["--benchmark", "longmemeval", "--v4-dir", str(LME_V4_ROOT), "--v5-dir", str(v5)])
        return code, out.getvalue()

    def test_cli_over_the_committed_v4_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, output = self._main(self._v5_tree(Path(temporary) / "equal"))
            self.assertEqual(code, 0)
            self.assertEqual(output.count("EQUAL\t"), 1000)

            def attributed(plane, rows):
                if plane == "turn":
                    row = next(row for row in rows if len(row["ranked_top"]) > 1)
                    original = list(row["ranked_top"])
                    row["ranked_top"] = original[::-1]
                    row["cross_fact"] = self._record(1, original)

            code, output = self._main(self._v5_tree(Path(temporary) / "attributed", attributed))
            self.assertEqual(code, 0)
            self.assertEqual(output.count("ATTRIBUTED\t"), 1)

            def unattributed(plane, rows):
                if plane == "session":
                    row = next(row for row in rows if len(row["ranked_top"]) > 1)
                    row["ranked_top"] = row["ranked_top"][::-1]

            code, output = self._main(self._v5_tree(Path(temporary) / "unattributed", unattributed))
            self.assertEqual(code, 1)
            self.assertEqual(output.count("UNATTRIBUTED\t"), 1)
            code, _ = self._main(Path(temporary) / "missing")
            self.assertEqual(code, 2)


class AmbAttributionTests(unittest.TestCase):
    def setUp(self):
        self.v4 = json.loads((AMB_V4_CONTROL / "single-turn.json").read_text(encoding="utf-8"))

    @staticmethod
    def _lines(results: list[dict], records: dict[str, dict] | None = None) -> list[str]:
        asked = [case for case in results if (case.get("query") or "").strip()]
        lines = []
        for index, case in enumerate(asked):
            record = {"call_index": index, "query_sha256": hashlib.sha256(case["query"].encode("utf-8")).hexdigest(),
                      "limited_count": 0, "returned_document_ids_mechanism_off": None}
            record.update((records or {}).get(case["query_id"], {}))
            lines.append(json.dumps(record))
        return lines

    def test_each_verdict_and_the_cli(self):
        v4 = self.v4["results"]
        v5 = copy.deepcopy(v4)
        multi = [case for case in v5 if case["meta"].get("retrieved_count", 0) >= 2 and case["query"].strip()]
        blank = next(case for case in v5 if not case["query"].strip())
        attributed, wrong_off, no_limit = multi[0], multi[1], multi[2]
        records = {}
        for case in (attributed, wrong_off, no_limit):
            documents = ATTRIBUTION.parse_retrieval_context(case["context"])
            ids = [item["id"] for item in documents]
            case["context"] = ATTRIBUTION.render_retrieval_context(documents[::-1])
            records[case["query_id"]] = {"limited_count": 1, "returned_document_ids_mechanism_off": ids}
        records[wrong_off["query_id"]]["returned_document_ids_mechanism_off"] = records[wrong_off["query_id"]]["returned_document_ids_mechanism_off"][::-1]
        records[no_limit["query_id"]] = {"limited_count": 0, "returned_document_ids_mechanism_off": None}
        verdicts = {item["id"]: item["verdict"] for item in ATTRIBUTION.attribute_amb_cases(v4, v5, self._lines(v5, records))}
        self.assertEqual(verdicts.pop(attributed["query_id"]), "ATTRIBUTED")
        self.assertEqual(verdicts.pop(wrong_off["query_id"]), "UNATTRIBUTED")
        self.assertEqual(verdicts.pop(no_limit["query_id"]), "UNATTRIBUTED")
        self.assertEqual(set(verdicts.values()), {"EQUAL"})
        self.assertEqual(len(verdicts), 74)

        blank_changed = copy.deepcopy(v4)
        next(case for case in blank_changed if not case["query"].strip())["meta"]["retrieved_count"] = 3
        verdicts = {item["id"]: item["verdict"] for item in ATTRIBUTION.attribute_amb_cases(v4, blank_changed, self._lines(blank_changed))}
        self.assertEqual(verdicts[blank["query_id"]], "UNATTRIBUTED")
        with self.assertRaises(ATTRIBUTION.AttributionError):
            ATTRIBUTION.attribute_amb_cases(v4, v5, self._lines(v5)[:-1])

        with tempfile.TemporaryDirectory() as temporary:
            only_attributed = copy.deepcopy(v4)
            next(case for case in only_attributed if case["query_id"] == attributed["query_id"])["context"] = attributed["context"]
            for name, results, lines, expected in (
                ("equal", v4, self._lines(v4), 0),
                ("attributed", only_attributed, self._lines(only_attributed, {attributed["query_id"]: records[attributed["query_id"]]}), 0),
                ("unattributed", v5, self._lines(v5, records), 1),
            ):
                directory = Path(temporary) / name / "agent-memory-5555aaaa5555"
                directory.mkdir(parents=True)
                (directory / "single-turn.json").write_text(json.dumps({**self.v4, "results": results}), encoding="utf-8")
                (directory / "cross-fact.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
                with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
                    code = ATTRIBUTION.main(["--benchmark", "amb", "--v4-dir", str(AMB_V4_CONTROL.parent), "--v5-dir", str(directory.parent)])
                self.assertEqual(code, expected, name)
                self.assertIn('"authority_effect": "none"', out.getvalue())


if __name__ == "__main__":
    unittest.main()
