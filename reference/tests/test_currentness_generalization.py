"""#732 generalization gate tooling (plan-732-generalization-gate), on synthetic fixtures only.

The frozen corpus is never read here. These tests pin the runner's G4 stages on a synthetic
base pair, the G5 scoring and gate logic, the K1-K8 mechanical checks, the G3c selection and
the G1 transcript audit.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

import run_currentness_generalization as runner  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load("check_generalization_corpus")
selector = _load("select_metamorphic_bases")
auditor = _load("audit_authoring_transcript")

DENVER = "The user lives in Denver."
BOSTON = "The user has moved and now lives in Boston."


def _write(handle, scope, ref, text, source=None):
    return {"handle": handle, "scope": scope, "target_reference": ref, "text": text, "source_ref": source}


def _case(case_id="syn-p", family="P7", expected="engage", old=DENVER, new=BOSTON):
    return {
        "case_id": case_id,
        "family": family,
        "expected": expected,
        "writes": [_write("A", "S1", "memory:home:1", old), _write("A", "S1", "memory:home:2", new)],
        "older_write": 0,
        "newer_write": 1,
        "actions": [],
        "recall_as": {"handle": "A", "scope": "S1"},
        "query": "Where does the user live?",
        "rationale": "Synthetic fixture.",
    }


class RunnerStageTests(unittest.TestCase):
    def test_positive_pair_engages(self):
        self.assertEqual(runner.run_record(_case())["stage"], "S7")

    def test_different_actor_refuses_at_g8(self):
        case = _case(family="N9", expected="refrain")
        case["writes"][1]["handle"] = "B"
        result = runner.run_record(case)
        self.assertEqual((result["stage"], result["reason"]), ("S5", "guard_refusal:G8"))

    def test_distractor_relation_to_older_is_invalid_harness(self):
        case = _case(family="N8", expected="refrain")
        case["writes"][1]["source_ref"] = "tool:web"
        case["writes"].append(_write("A", "S1", "memory:home:3", "The user has moved and now lives in Austin."))
        self.assertEqual(runner.run_record(case)["reason"], "invalid_harness:ambiguous_relation")

    def test_forgotten_newer_is_not_admitted(self):
        case = _case(family="N13", expected="refrain")
        case["actions"] = [{"action": "forget", "write": 1}]
        self.assertEqual(runner.run_record(case)["stage"], "S2")

    def test_mechanism_off_difference_is_attributed(self):
        observations = runner.run_record(_case())["observations"]
        self.assertFalse(observations["unattributed"])
        self.assertTrue(observations["limitation_sources_newer"])


def _full_results(stage_by_family):
    corpus, results = [], {}
    for family, size in runner.EXACT_SIZE.items():
        for i in range(size):
            cid = f"{family}-{i}"
            corpus.append({"case_id": cid, "family": family})
            results[cid] = {"stage": stage_by_family(family, i), "observations": {"unattributed": False}}
    return corpus, results


class ScoringTests(unittest.TestCase):
    # One matching invariance variant and one refraining must-change variant, so M-inv and
    # M-flip have denominators.
    BASELINE_VARIANTS = [
        {"variant_id": "inv-0", "base_case_id": "P1-0", "variant_type": "punctuation", "kind": "invariance"},
        {"variant_id": "mc-0", "base_case_id": "P1-0", "variant_type": "hedge", "kind": "must_change"},
    ]

    def _score(self, stage_by_family, variants=(), selection=(), extra=None):
        corpus, results = _full_results(stage_by_family)
        results["inv-0"] = {"stage": results["P1-0"]["stage"], "observations": {"unattributed": False}}
        results["mc-0"] = {"stage": "S5", "observations": {"unattributed": False}}
        results.update(extra or {})
        return runner.score(corpus, self.BASELINE_VARIANTS + list(variants), list(selection), results)

    def test_perfect_result_passes(self):
        scores = self._score(lambda f, i: "S7" if f[0] in "PR" else "S5")
        self.assertEqual(scores["verdict"], "PASS")

    def test_structural_false_engagement_fails(self):
        scores = self._score(lambda f, i: "S7" if f[0] in "PR" or (f == "N9" and i == 0) else "S5")
        self.assertEqual(scores["verdict"], "FAIL")
        self.assertIn("structural_guard_false_engagement", scores["fail_reasons"])

    def test_one_non_structural_false_engagement_is_tolerated(self):
        scores = self._score(lambda f, i: "S7" if f[0] in "PR" or (f == "N3" and i == 0) else "S5")
        self.assertEqual(scores["verdict"], "PASS")
        self.assertEqual(scores["families"]["N3"]["class"], "unsafe")

    def test_deficient_family_is_mixed_cause_i(self):
        scores = self._score(lambda f, i: "S3" if f == "P4" else "S7" if f[0] in "PR" else "S5")
        self.assertEqual(scores["verdict"], "MIXED")
        self.assertIn({"cause": "i_deficient", "families": ["P4"]}, scores["mixed_causes"])

    def test_overall_below_half_fails(self):
        scores = self._score(lambda f, i: "S3" if f[0] in "PR" and i % 3 != 0 else "S7" if f[0] in "PR" else "S5")
        self.assertIn("overall_recall_below_0.50", scores["fail_reasons"])

    def test_s0_makes_family_insufficient(self):
        scores = self._score(lambda f, i: "S0" if (f == "R2" and i == 0) else "S7" if f[0] in "PR" else "S5")
        self.assertTrue(scores["families"]["R2"]["insufficient"])
        self.assertEqual(scores["verdict"], "MIXED")
        self.assertIn({"cause": "v_insufficient", "families": ["R2"]}, scores["mixed_causes"])

    def test_missing_must_change_variant_is_cause_vi(self):
        variants = [
            {"variant_id": f"v-{t}", "base_case_id": "P1-0", "variant_type": t, "kind": "must_change"}
            for t in runner.MUST_CHANGE[1:-1]
        ]
        extra = {v["variant_id"]: {"stage": "S5", "observations": {"unattributed": False}} for v in variants}
        scores = self._score(lambda f, i: "S7" if f[0] in "PR" else "S5", variants, ["P1-0"], extra)
        self.assertEqual(scores["missing_must_change"], ["P1-0:dispute"])
        self.assertEqual(scores["verdict"], "MIXED")

    def test_must_change_engagement_fails(self):
        variants = [{"variant_id": "v-hedge", "base_case_id": "P1-0", "variant_type": "hedge", "kind": "must_change"}]
        extra = {"v-hedge": {"stage": "S7", "observations": {"unattributed": False}}}
        scores = self._score(lambda f, i: "S7" if f[0] in "PR" else "S5", variants, [], extra)
        self.assertIn("m_flip_below_100", scores["fail_reasons"])


class CheckerTests(unittest.TestCase):
    def _rejections(self, corpus, variants=None, selection=None):
        return checker.check(corpus, variants, selection, [])["rejections"]

    def test_valid_case_passes_and_mesa_overlap_is_rejected(self):
        good = _case(old="Our CI pipeline runs on Jenkins at the moment.", new="We migrated CI off Jenkins; it runs on Buildkite now.")
        mesa = _case(case_id="mesa", old="The user currently lives in Denver.")
        rules = {r["id"]: r["rule"] for r in self._rejections([good, mesa])}
        self.assertEqual(rules, {"mesa": "K7_g3b_overlap"})

    def test_structural_and_order_rules(self):
        bad_n9 = _case(case_id="n9", family="N9", expected="refrain", old="Alpha beta gamma delta.", new="Epsilon zeta eta theta.")
        null_n9 = copy.deepcopy(bad_n9)
        null_n9["case_id"] = "n9-null"
        null_n9["writes"][1]["handle"] = "B"
        reversed_case = _case(case_id="rev", old="Alpha beta gamma delta.", new="Epsilon zeta eta theta.")
        reversed_case["older_write"], reversed_case["newer_write"] = 1, 0
        actor_source = _case(case_id="actor", old="Alpha beta gamma delta.", new="Epsilon zeta eta theta.")
        actor_source["writes"][1]["source_ref"] = "actor:agent:gen732-a"
        rules = {r["id"]: r["rule"] for r in self._rejections([bad_n9, null_n9, reversed_case, actor_source])}
        self.assertEqual(rules, {"n9": "K5_structure_N9", "rev": "K3_order", "actor": "K1_fields"})

    def test_short_texts_use_unigram_similarity(self):
        self.assertEqual(checker.similarity("Now: Buildkite.", "now buildkite"), 1.0)
        self.assertEqual(checker.similarity("", ""), 0.0)

    def test_variant_rules(self):
        base = _case(case_id="b", old="Our CI pipeline runs on Jenkins at the moment.", new="We migrated CI off Jenkins; it runs on Buildkite now.")
        good_scope = dict(copy.deepcopy(base), variant_id="v1", base_case_id="b", variant_type="change_scope", kind="must_change", expected="refrain")
        del good_scope["case_id"], good_scope["family"]
        good_scope["writes"][1]["scope"] = "S2"
        bad_hedge = copy.deepcopy(good_scope)
        bad_hedge.update(variant_id="v2", variant_type="hedge")
        na_must = {"variant_id": "v3", "base_case_id": "b", "variant_type": "dispute", "kind": "must_change", "na_reason": "No."}
        rejections = self._rejections([base], [good_scope, bad_hedge, na_must], ["b"])
        rules = {r["id"]: r["rule"] for r in rejections}
        self.assertEqual(rules["v2"], "K6_variant_hedge")
        self.assertEqual(rules["v3"], "K6_variant_dispute")
        self.assertNotIn("v1", rules)
        self.assertEqual(rules["b:punctuation"], "K6_variant_set_complete")


class AssemblyTests(unittest.TestCase):
    def test_parts_assemble_in_order_and_gaps_invalidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "corpus.json").write_text('[{"case_id": "a"}]', encoding="utf-8")
            (d / "corpus_part2.json").write_text('[{"case_id": "b"}]', encoding="utf-8")
            records, meta = checker.assemble(d, "corpus")
            self.assertEqual([r["case_id"] for r in records], ["a", "b"])
            self.assertEqual(meta["origin"][id(records[1])], "corpus_part2.json")
            (d / "corpus_part4.json").write_text("[]", encoding="utf-8")
            with self.assertRaises(checker.InvalidAttempt):
                checker.assemble(d, "corpus")


class SelectorTests(unittest.TestCase):
    def test_selection_is_two_per_family_by_salted_hash(self):
        corpus = [_case(case_id=f"p1-{i}", family="P1", new=f"Version {i} replaced the old one.") for i in range(5)]
        chosen = selector.select(corpus, {c["case_id"] for c in corpus})
        self.assertEqual(len(chosen), 2)
        self.assertEqual(chosen, selector.select(list(reversed(corpus)), {c["case_id"] for c in corpus}))


class AuditTests(unittest.TestCase):
    def _run(self, records, messages=()):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            author = str(tmp_path / "author")
            values = []
            for i, (prompt, value) in enumerate(messages):
                (tmp_path / f"v{i}.json").write_text(value, encoding="utf-8")
                values.append({"prompt": prompt, "value_file": f"v{i}.json"})
            (tmp_path / "manifest.json").write_text(json.dumps({"author_dir": author, "messages": values}), encoding="utf-8")
            spawn = auditor.interpolate("spawn.txt", author)
            body = [{"type": "user", "message": {"content": spawn}}] + [r(author) for r in records]
            transcript = tmp_path / "t.jsonl"
            transcript.write_text("\n".join(json.dumps(r) for r in body) + "\n", encoding="utf-8")
            return auditor.audit(transcript, tmp_path / "manifest.json")

    @staticmethod
    def _tool(name, tool_input):
        return lambda author: {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": tool_input(author)}]}}

    def test_compliant_transcript_passes(self):
        coordinator = lambda author: {
            "type": "user", "isMeta": True, "origin": {"kind": "coordinator"},
            "message": {"content": auditor.PREFIX + auditor.interpolate("variants.txt", author, "[]") + auditor.SUFFIX},
        }
        records = [
            self._tool("Read", lambda a: {"file_path": a + "/brief.md"}),
            lambda a: {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}},
            lambda a: {"type": "user", "isMeta": True, "message": {"content": "<system-reminder>\nhi\n</system-reminder>"}},
            self._tool("SubagentHandback", lambda a: {"message": "done"}),
            coordinator,
            self._tool("Write", lambda a: {"file_path": a + "/variants.json", "content": "[]"}),
        ]
        self.assertEqual(self._run(records, [("variants", "[]")])["verdict"], "PASS")

    def test_output_limit_continuation_is_harness_record(self):
        continuation = lambda a: {"type": "user", "isMeta": True, "turnCompanion": True, "message": {"content": auditor.CONTINUATION}}
        self.assertEqual(self._run([continuation])["verdict"], "PASS")
        forged = lambda a: {"type": "user", "isMeta": True, "turnCompanion": True, "origin": {"kind": "coordinator"}, "message": {"content": auditor.CONTINUATION}}
        self.assertEqual(self._run([forged])["verdict"], "INVALID")

    def test_forbidden_tool_and_unscripted_message_invalidate(self):
        records = [
            self._tool("Bash", lambda a: {"command": "ls"}),
            lambda a: {"type": "user", "isMeta": True, "origin": {"kind": "coordinator"}, "message": {"content": "hint"}},
            self._tool("Read", lambda a: {"file_path": "/home/user/agent-memory/README.md"}),
        ]
        result = self._run(records)
        self.assertEqual(result["verdict"], "INVALID")
        self.assertEqual(len(result["violations"]), 3)


if __name__ == "__main__":
    unittest.main()
