"""#836 independent fail-first probe: opaque graph candidates versus visible discovery budget.

The expected behavior is a candidate contract question, not yet accepted doctrine:
a deleted/withheld graph neighbor must not displace an otherwise visible live
neighbor solely by consuming fan-out or final candidate slots. Canonical audit
may still retain the deleted candidate's refusal; public diagnostics must not
expose its identifier. Freeze this test before modifying protected runtime code.

Source-reviewed against cumulative candidate 07cd8692, declaration a78797cb.
No benchmark scores or accepted runtime claims arise from this probe.
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from agentmem_ref.recall_control import (
    ControlledRecallPlanner,
    GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever,
)
from tests.test_836_graph_exclusion_boundaries import _graph_plan
from tests.test_776_adversarial_review import KILN, _Store
from tests.test_runtime_composition import TENANT, _context
from tests.test_typed_graph_retrieval import _FixedController, _relation


class OpaqueGraphBudgetNoninterference(unittest.TestCase):
    def _run(self, *, include_hidden: bool, fanout: int, graph_limit: int):
        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        seed = h.chain(
            "studio", [("The pottery studio fires glazes on Fridays.", None)]
        )[0]
        visible = h.chain(
            "shelf", [("The glaze shelf holds test tiles.", None)]
        )[0]
        sub = h.adapter.checkpoint_substrate()
        sub.write_relation(replace(
            _relation("r-visible", seed, visible, weight=0.80), group_id=TENANT
        ))
        if include_hidden:
            # Higher score sorts first; deleted node must not confer traversal
            # reachability, spend visible budget or enter reported graph paths.
            sub.write_relation(replace(
                _relation("r-deleted", seed, old, weight=1.0), group_id=TENANT
            ))
        h.prune("kiln")
        context = _context()
        self.assertTrue(
            h.adapter.public_identifier_withheld(old, context),
            "precondition: deleted generation is withheld for this reader",
        )
        planner = ControlledRecallPlanner(
            h.adapter,
            controller=_FixedController(_graph_plan(graph_limit, 1)),
            graph_retriever=NativeTypedGraphCandidateRetriever(
                GraphTraversalSpec(max_depth=1, max_fanout=fanout)
            ),
        )
        result = planner.recall(
            "", context, logical_memory_refs=("memory:776r:studio",)
        )
        return old, visible, result

    def _check_visible(self, *, fanout: int, graph_limit: int):
        old_control, target_control, control = self._run(
            include_hidden=False, fanout=fanout, graph_limit=graph_limit
        )
        old_probed, target_probed, probed = self._run(
            include_hidden=True, fanout=fanout, graph_limit=graph_limit
        )
        self.assertIn(
            target_control, control.admitted,
            "control must prove visible neighbor is reachable at this budget",
        )
        self.assertEqual(
            target_control, target_probed,
            "store fixture identities must remain aligned across both arms",
        )
        self.assertIn(
            target_probed, probed.admitted,
            "withheld-neighbor presence must not starve the admitted live sibling",
        )
        self.assertNotIn(old_probed, probed.graph_candidate_hits)
        for hit in probed.graph_candidate_hits.values():
            self.assertNotIn(old_probed, hit.path_refs)
        self.assertNotIn(old_probed, probed.admitted)
        # Do not demand deletion of the canonical refusal: docs/44/#777
        # preserves admission's internal audit of the deleted generation.

    def test_opaque_node_must_not_spend_eligible_fanout_one(self):
        self._check_visible(fanout=1, graph_limit=2)

    def test_opaque_node_must_not_fill_only_canonical_candidate_slot(self):
        self._check_visible(fanout=2, graph_limit=1)


if __name__ == "__main__":
    unittest.main()
