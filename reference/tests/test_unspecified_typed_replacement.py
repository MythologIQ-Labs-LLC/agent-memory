"""#819 longitudinal lane: opt-in typed-replacement default for unspecified-intent recall.

``AgentMemory.open(..., unspecified_intent_currentness="typed_replacement")`` lets a recall
with no temporal cue use the #671/#732 cross-fact evidence, typed relations only, under the
unchanged guards G2-G13. Off by default; explicit-current, historical and inferred recalls are
unchanged; the replaced fact stays admitted, returned and labelled; nothing is mutated.
"""

from __future__ import annotations

import tempfile
import unittest

from agentmem_ref import AgentMemory
from agentmem_ref.runtime import cross_fact_currentness as cf

TENANT = "tenant:typed-replacement"
SCOPE = "project:typed-replacement"
ACTOR = "agent:typed-replacement"
QUERY = "What diet does the user follow?"
VOLATILE = frozenset({"decision_id", "evaluated_at"})


def _prop(value, assertion="state", **kw):
    return {"subject": "user", "attribute": "diet", "value": value, "assertion": assertion, "cardinality": "single", **kw}


def _strip(value):
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


class TypedReplacementDefault(unittest.TestCase):
    def setUp(self):
        self._dirs = []

    def tearDown(self):
        for directory in self._dirs:
            directory.cleanup()

    def _open(self, root, mode=None, scope=SCOPE):
        kwargs = {} if mode is None else {"unspecified_intent_currentness": mode}
        return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="typed replacement", **kwargs)

    def _store(self, *, new_kwargs=None, new_prop=None, new_text="The user is now vegan", old_kwargs=None):
        directory = tempfile.TemporaryDirectory()
        self._dirs.append(directory)
        memory = self._open(directory.name)
        old = memory.remember("s1:diet", "The user is vegetarian", proposition=_prop("vegetarian"), **(old_kwargs or {}))
        memory.remember("s1:cuisine", "The user enjoys Thai food")
        new = memory.remember("s2:diet", new_text,
                              proposition=new_prop or _prop("vegan", "change", replaces_value="vegetarian"),
                              **(new_kwargs or {}))
        memory.close()
        return directory.name, old["fact_uuid"], new["fact_uuid"]

    def _recall(self, root, mode, query=QUERY, **kwargs):
        memory = self._open(root, mode)
        try:
            return memory.recall(query, budget=5, **kwargs), memory.semantic_proposals(), memory.history("s1:diet")
        finally:
            memory.close()

    def test_off_by_default_keeps_baseline_ordering(self):
        root, old, new = self._store()
        default, _, _ = self._recall(root, None)
        off, _, _ = self._recall(root, "off")
        self.assertEqual(_strip(default), _strip(off))
        self.assertEqual(default["returned"][0], old)
        self.assertNotIn("cross_fact_activation", default["admissions"][old]["ranking_evidence"])

    def test_opt_in_labels_and_demotes_but_keeps_replaced_fact(self):
        root, old, new = self._store()
        result, proposals, history = self._recall(root, "typed_replacement")
        _, proposals_off, history_off = self._recall(root, "off")
        self.assertIn(old, result["admitted"])
        self.assertIn(old, result["returned"])
        self.assertLess(result["returned"].index(new), result["returned"].index(old))
        self.assertEqual(result["returned"][-1], old)
        evidence = result["admissions"][old]["ranking_evidence"]
        self.assertEqual(evidence["temporal_applicability"], cf.CROSS_FACT_LABEL)
        self.assertEqual(evidence["cross_fact_activation"], cf.UNSPECIFIED_TYPED_ACTIVATION)
        self.assertEqual(evidence["cross_fact_limitation"][0]["source_fact_uuid"], new)
        self.assertEqual(evidence["query_temporal_intent"]["mode"], "atemporal_or_unspecified")
        self.assertEqual(result["admissions"][new]["ranking_evidence"]["temporal_applicability"], "not_evaluated")
        # Nothing applied or mutated: the proposal stays open, history is unchanged.
        self.assertEqual([p["status"] for p in proposals], ["open"])
        self.assertEqual(proposals, proposals_off)
        self.assertEqual(_strip(history), _strip(history_off))

    def test_explicit_current_and_historical_and_inferred_are_unchanged(self):
        root, old, new = self._store()
        for query, kwargs in ((QUERY, {"temporal_intent": {"mode": "current"}}),
                              (QUERY, {"temporal_intent": {"mode": "historical"}}),
                              ("What diet did the user follow before?", {}),
                              ("What diet will the user follow now?", {})):
            on, _, _ = self._recall(root, "typed_replacement", query, **kwargs)
            off, _, _ = self._recall(root, "off", query, **kwargs)
            self.assertEqual(_strip(on), _strip(off), query)
            for admission in on["admissions"].values():
                self.assertNotIn("cross_fact_activation", admission.get("ranking_evidence") or {})

    def test_interpreted_text_relation_does_not_activate(self):
        directory = tempfile.TemporaryDirectory()
        self._dirs.append(directory)
        memory = self._open(directory.name)
        old = memory.remember("s1:home", "The user lives in Denver.")["fact_uuid"]
        memory.remember("s2:home", "The user has moved and now lives in Boston.")
        memory.close()
        current, _, _ = self._recall(directory.name, "typed_replacement", "Where does the user live?",
                                     temporal_intent={"mode": "current"})
        self.assertEqual(current["admissions"][old]["ranking_evidence"]["temporal_applicability"], cf.CROSS_FACT_LABEL)
        unspecified, _, _ = self._recall(directory.name, "typed_replacement", "Where does the user live?")
        evidence = unspecified["admissions"][old]["ranking_evidence"]
        self.assertNotEqual(evidence["temporal_applicability"], cf.CROSS_FACT_LABEL)
        self.assertEqual(evidence["cross_fact_refusal_reason"], "unspecified_intent_requires_typed_relation")
        self.assertEqual(unspecified["returned"][0], old)

    def test_existing_guards_still_refuse(self):
        cases = {
            "hedged": {"new_prop": _prop("vegan", "change", replaces_value="vegetarian", flags={"hedged": True}),
                       "new_text": "The user might become vegan"},
            "other_source": {"new_kwargs": {"source_ref": "user:dana"}},
            "attributed": {"new_prop": _prop("vegan", "change", replaces_value="vegetarian",
                                             flags={"attributed_to_other": True}),
                           "new_text": "Dana says the user is now vegan"},
            "declared_window": {"old_kwargs": {"valid_from": "2025-01-01T00:00:00Z"}},
        }
        for name, kwargs in cases.items():
            root, old, new = self._store(**kwargs)
            on, _, _ = self._recall(root, "typed_replacement")
            evidence = on["admissions"][old]["ranking_evidence"]
            self.assertNotEqual(evidence["temporal_applicability"], cf.CROSS_FACT_LABEL, name)
            self.assertNotIn("cross_fact_activation", evidence, name)

    def test_unknown_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                self._open(root, "always_current")


if __name__ == "__main__":
    unittest.main()
