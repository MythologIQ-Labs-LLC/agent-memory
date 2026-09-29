"""Write interpreter 1.1.0 (#598): scoped temporal aspect, beyond the frozen contract.

The frozen adversarial contract (``test_write_temporal_aspect_contract``) pins the
declines. These tests pin what the change must *not* do:

* 1.1.0 only withholds aspect relative to 1.0.0; it never introduces a regime;
* nothing outside ``markers.aspect`` changes (proposition, cardinality, change,
  coexistence, hedges, self-claims, self-validity, proposal eligibility);
* the scope diagnostic is not persisted, and 1.0.0 facts stay 1.0.0 across reopen;
* aspect remains evidence: it grants no currentness, authority, or validity window.

It also pins two refinements made after the contract froze, each traced to a #594
item that 1.0.0 classified correctly and a first 1.1.0 draft lost (ps1-048, ps1-138,
ps1-196, ps1-249): a subordinator scopes over its own comma segment only, and a
question sentence's declarative lead-in stays asserted.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402

EVIDENCE = ROOT / "reports" / "benchmarks" / "replays" / "598-write-time-temporal-aspect"
SAMPLE = ROOT / "reference" / "fixtures" / "benchmarks" / "proposition-semantics" / "sample-v1.json"
CONTRACT = ROOT / "reference" / "fixtures" / "runtime" / "write-temporal-aspect-v1.1-adversarial.json"
LEXICON_V1_0_0 = {
    "present": ("currently", "right now", "at the moment", "these days", "nowadays", "presently", "at present",
                "as of now", "now"),
    "prospective": ("planning to", "plan to", "going to", "intend to", "will", "next week", "next month",
                    "next year", "tomorrow", "upcoming", "soon"),
    "past_habitual": ("used to", "no longer", "not anymore", "previously", "formerly"),
}


def _regimes(out: dict) -> list[str]:
    return sorted((out.get("markers") or {}).get("aspect") or {})


def _non_aspect(out: dict) -> dict:
    out = json.loads(json.dumps(out))
    out.pop("aspect_scope", None)
    out.pop("interpreter", None)
    markers = out.get("markers") or {}
    markers.pop("aspect", None)
    if not markers:
        out.pop("markers", None)
    return out


def _texts() -> dict[str, str]:
    return {item["item_id"]: item["text"] for item in json.loads(SAMPLE.read_text(encoding="utf-8"))["items"]}


class ScopedAspectRefinementTests(unittest.TestCase):
    CASES = (
        # (text, regime, status, declined)
        ("Speaking of which, I've been collecting coins for about two months now.", "present", "resolved_write", []),
        ("I adopted a dog, which I now walk every morning.", None, "none", [["now", "subordinate_clause"]]),
        ("I'm thinking of getting a new bike soon, do you have any recommendations?", "prospective",
         "resolved_principal", []),
        ("I'm planning to run a marathon next month and I was wondering if you could help me train?",
         "prospective", "resolved_principal", []),
        ("Now that I have the keys, what's the process for changing the locks?", "present", "resolved_principal", []),
        ("Honestly, what are people reading these days?", None, "none", [["these days", "question_or_request"]]),
        ("It will rain tomorrow, won't it?", None, "none", [["will", "question_or_request"],
                                                           ["tomorrow", "question_or_request"],
                                                           ["will", "question_or_request"]]),  # won't -> will not
    )

    def test_refinements(self):
        for text, regime, status, declined in self.CASES:
            with self.subTest(text=text):
                out = ps.interpret_write(text)
                self.assertEqual(_regimes(out), [regime] if regime else [])
                self.assertEqual(out["aspect_scope"]["status"], status)
                self.assertEqual([[d["cue"], d["reason"]] for d in out["aspect_scope"].get("declined", [])], declined)

    def test_cue_lexicon_is_unchanged_from_1_0_0(self):
        self.assertEqual(ps._ASPECT_CUES, LEXICON_V1_0_0)

    def test_leftmost_longest_cue_is_reported_once(self):
        out = ps.interpret_write("Right now I'm reading Dune.")
        self.assertEqual(out["markers"]["aspect"], {"present": ["right now"]})


class NoCollateralChangeTests(unittest.TestCase):
    """Against the #594 accepted sample: only ``markers.aspect`` may change, and only by withholding."""

    @classmethod
    def setUpClass(cls):
        cls.texts = _texts()
        cls.drift = json.loads((EVIDENCE / "interpreter-drift-594-v1.0.0-vs-v1.1.0.json").read_text(encoding="utf-8"))
        cls.before = json.loads((EVIDENCE / "predictions-before-v1.0.0.json").read_text(encoding="utf-8"))

    def test_every_non_aspect_field_matches_interpreter_1_0_0(self):
        pinned = self.drift["v1_0_0_non_aspect_sha256_by_item"]
        self.assertEqual(set(pinned), set(self.texts))
        for item_id, text in sorted(self.texts.items()):
            digest = hashlib.sha256(json.dumps(_non_aspect(ps.interpret_write(text)), sort_keys=True,
                                               separators=(",", ":")).encode()).hexdigest()
            self.assertEqual(digest, pinned[item_id], item_id)

    def test_1_1_0_only_withholds_aspect(self):
        for item_id, text in sorted(self.texts.items()):
            with self.subTest(item=item_id):
                self.assertLessEqual(set(_regimes(ps.interpret_write(text))), set(self.before[item_id]["aspect_all"]))
                self.assertLessEqual(len(_regimes(ps.interpret_write(text))), 1)

    def test_aspect_never_touches_eligibility_or_validity(self):
        for text in ("I currently live in Denver.", "I used to live in Boston.", "I'm planning to move soon.",
                     "What's popular these days?", "I currently rent. I'm planning to buy soon."):
            with self.subTest(text=text):
                out = ps.interpret_write(text)
                self.assertEqual(out["authority_effect"], "none")
                self.assertEqual(out["self_validity"], {"status": "none"})
                self.assertNotIn("valid_from", json.dumps(out["aspect_scope"]))
                self.assertFalse(set(out.get("proposal_ineligible_reasons", ())) - {
                    "proposition_unknown", "proposition_ambiguous", "hedged"})


class PersistenceAndVersionTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.root = self._temp.name

    def tearDown(self):
        self._temp.cleanup()

    def _open(self) -> AgentMemory:
        return AgentMemory.open(self.root, tenant="tenant:aspect", actor_id="agent:aspect", scope="project:aspect",
                                purpose="aspect scope tests")

    def test_scope_diagnostic_is_not_persisted(self):
        out = ps.interpret_write("Can you tell me which bills are being debated right now?")
        self.assertIn("aspect_scope", out)
        stored = ps.persisted_form(out)
        self.assertNotIn("aspect_scope", stored)
        self.assertEqual(stored["version"], f"1.1.0/{ps.CLASSIFIER_VERSION}")
        self.assertNotIn("aspect_scope", ps.expanded_form(stored))

    def test_classifier_version_is_not_bumped(self):
        self.assertEqual((ps.INTERPRETER_VERSION, ps.CLASSIFIER_VERSION), ("1.1.0", "1.0.0"))

    def test_1_0_0_stored_form_is_never_reinterpreted(self):
        stored = {"version": "1.0.0/1.0.0", "markers": {"aspect": {"present": ["now", "right now"],
                                                                   "prospective": ["will"]}}}
        expanded = ps.expanded_form(stored)
        self.assertEqual(expanded["interpreter"]["version"], "1.0.0")
        self.assertEqual(expanded["markers"]["aspect"], stored["markers"]["aspect"])

    def test_1_0_0_facts_stay_1_0_0_across_reopen(self):
        text = "Can you tell me which bills are being debated right now? I will vote tomorrow."

        def legacy_aspect(pieces, principal):  # interpreter 1.0.0: whole-write cue match
            lowered = ps._norm(" ".join(piece for piece, _, _ in pieces))
            aspect = {name: sorted(c for c in cues if ps._contains(lowered, c)) for name, cues in ps._ASPECT_CUES.items()}
            return {name: cues for name, cues in aspect.items() if cues}, {}

        memory = self._open()
        with mock.patch.object(ps, "INTERPRETER_VERSION", "1.0.0"), mock.patch.object(ps, "_scoped_aspect", legacy_aspect):
            old = memory.remember("memory:bills:old", text)["fact_uuid"]
        new = memory.remember("memory:bills:new", text)["fact_uuid"]
        before = {uuid: memory.write_semantics(uuid) for uuid in (old, new)}
        memory.close()
        memory = self._open()
        try:
            after = {uuid: memory.write_semantics(uuid) for uuid in (old, new)}
        finally:
            memory.close()
        self.assertEqual(after, before)
        self.assertEqual(after[old]["interpreter"]["version"], "1.0.0")
        self.assertEqual(sorted(after[old]["markers"]["aspect"]), ["present", "prospective"])
        self.assertEqual(after[new]["interpreter"]["version"], "1.1.0")
        self.assertEqual(after[new]["markers"]["aspect"], {"prospective": ["tomorrow", "will"]})


class DeterminismTests(unittest.TestCase):
    def test_scope_is_identical_across_hash_seeds(self):
        texts = [case["text"] for case in json.loads(CONTRACT.read_text(encoding="utf-8"))["cases"]]
        texts += [text for text, *_ in ScopedAspectRefinementTests.CASES]
        child = textwrap.dedent("""
            import json, sys
            sys.path.insert(0, sys.argv[1])
            from agentmem_ref.runtime import proposition_semantics as ps
            print(json.dumps([ps.interpret_write(t) for t in json.loads(sys.argv[2])], sort_keys=True))
        """)
        runs = {
            seed: subprocess.run([sys.executable, "-c", child, str(ROOT / "reference"), json.dumps(texts)],
                                 env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True, text=True,
                                 check=True).stdout
            for seed in ("0", "1", "7")
        }
        self.assertEqual(len(set(runs.values())), 1)


if __name__ == "__main__":
    unittest.main()
