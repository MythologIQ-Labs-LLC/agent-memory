from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_json_v2_migration_preflight import (  # noqa: E402
    MigrationPreflightError,
    compute_candidate_commitments,
    compute_governance_v2,
    compute_substrate_v2,
)


def _substrate_state() -> dict:
    return {
        "schema_version": "1.0.0",
        "relation_schema_version": "1.0.0",
        "id_counter": 7,
        "episodes": [
            {
                "uuid": "episode:1",
                "content": "source observation",
                "source_description": "qualification",
                "valid_at": "2026-09-29T00:00:00Z",
                "group_id": "tenant-acme",
            }
        ],
        "facts": [
            {
                "uuid": "fact:1",
                "fact_text": "deploy window is Thursday",
                "group_id": "tenant-acme",
                "episode_uuids": ["episode:1"],
                "valid_at": None,
                "invalid_at": None,
                "created_at": None,
                "expired_at": None,
                "attributes": {"priority": 1, "ratio": 0.25},
            }
        ],
        "relations": [
            {
                "relation_id": "relation:1",
                "source_uuid": "fact:1",
                "target_uuid": "fact:1",
                "relation_type": "supports",
                "group_id": "tenant-acme",
                "evidence_refs": ["episode:1"],
                "retrieval_weight": 0.75,
                "valid_at": None,
                "invalid_at": None,
                "created_at": None,
                "expired_at": None,
                "attributes": {"route": "qualification"},
            }
        ],
    }


def _governance_state() -> tuple[dict, dict, dict]:
    maps = {
        "current_fact_by_memory": {"memory:deploy-window": "fact:1"},
        "fact_memory": {"fact:1": "memory:deploy-window"},
        "fact_scope": {"fact:1": "tenant-acme"},
        "state_version": {"memory:deploy-window": 1},
        "tombstones": {},
    }
    logs = {
        "events": [
            {
                "event_type": "memory.retain",
                "fact_uuid": "fact:1",
                "authority_effect": "none",
            }
        ]
    }
    residual = {
        "tenant": "tenant-acme",
        "adapter": {
            "checkpoint_owner": "governed_memory_adapter",
            "selector_mode": "deterministic",
            "clock_tick": 2,
            "id_counter": 7,
            "disputed": [],
            "shared_domain_members": {},
            "rejected_values": [],
            "rejected_values_descriptor": {"schema_version": "1.0.0"},
            "containment_violations": [],
            "extension_state": {
                "qualification": {"score": 0.5, "status": "current"}
            },
        },
        "visibility_snapshots": {},
    }
    return maps, logs, residual


class CanonicalJsonV2MigrationPreflightTests(unittest.TestCase):
    def test_candidate_commitments_are_deterministic_and_side_effect_free(self):
        substrate = _substrate_state()
        maps, logs, residual = _governance_state()
        before = copy.deepcopy((substrate, maps, logs, residual))

        first = compute_candidate_commitments(
            substrate_state=substrate,
            governance_maps=maps,
            governance_logs=logs,
            governance_residual=residual,
        )
        second = compute_candidate_commitments(
            substrate_state=substrate,
            governance_maps=maps,
            governance_logs=logs,
            governance_residual=residual,
        )

        self.assertEqual(first, second)
        self.assertTrue(first.substrate_commitment.startswith("bmerkle-v2:"))
        self.assertTrue(first.governance_commitment.startswith("gsect-v2:"))
        self.assertTrue(first.logical_state_digest.startswith("sha256:"))
        self.assertEqual((substrate, maps, logs, residual), before)

    def test_substrate_root_changes_when_any_committed_row_layer_changes(self):
        state = _substrate_state()
        baseline = compute_substrate_v2(
            episodes=state["episodes"],
            facts=state["facts"],
            relations=state["relations"],
            schema_version=state["schema_version"],
            relation_schema_version=state["relation_schema_version"],
            id_counter=state["id_counter"],
        )

        mutations = []
        changed_episode = copy.deepcopy(state)
        changed_episode["episodes"][0]["content"] = "changed source"
        mutations.append(changed_episode)
        changed_fact = copy.deepcopy(state)
        changed_fact["facts"][0]["attributes"]["ratio"] = 0.5
        mutations.append(changed_fact)
        changed_relation = copy.deepcopy(state)
        changed_relation["relations"][0]["retrieval_weight"] = 0.5
        mutations.append(changed_relation)
        changed_counter = copy.deepcopy(state)
        changed_counter["id_counter"] = 8
        mutations.append(changed_counter)

        for candidate in mutations:
            with self.subTest(candidate=candidate):
                actual = compute_substrate_v2(
                    episodes=candidate["episodes"],
                    facts=candidate["facts"],
                    relations=candidate["relations"],
                    schema_version=candidate["schema_version"],
                    relation_schema_version=candidate["relation_schema_version"],
                    id_counter=candidate["id_counter"],
                )
                self.assertNotEqual(actual, baseline)

    def test_governance_root_changes_for_map_log_and_residual_mutations(self):
        maps, logs, residual = _governance_state()
        baseline = compute_governance_v2(maps=maps, logs=logs, residual=residual)

        changed_map = copy.deepcopy(maps)
        changed_map["state_version"]["memory:deploy-window"] = 2
        self.assertNotEqual(
            compute_governance_v2(maps=changed_map, logs=logs, residual=residual),
            baseline,
        )

        changed_log = copy.deepcopy(logs)
        changed_log["events"].append({"event_type": "memory.recall", "authority_effect": "none"})
        self.assertNotEqual(
            compute_governance_v2(maps=maps, logs=changed_log, residual=residual),
            baseline,
        )

        changed_residual = copy.deepcopy(residual)
        changed_residual["adapter"]["extension_state"]["qualification"]["status"] = "changed"
        self.assertNotEqual(
            compute_governance_v2(maps=maps, logs=logs, residual=changed_residual),
            baseline,
        )

    def test_nonfinite_fact_attribute_refuses_before_commitment(self):
        substrate = _substrate_state()
        substrate["facts"][0]["attributes"]["bad"] = math.nan
        maps, logs, residual = _governance_state()
        with self.assertRaises(MigrationPreflightError) as caught:
            compute_candidate_commitments(
                substrate_state=substrate,
                governance_maps=maps,
                governance_logs=logs,
                governance_residual=residual,
            )
        self.assertEqual(caught.exception.reason, "candidate_value_domain_invalid")

    def test_nonfinite_relation_attribute_refuses_before_commitment(self):
        substrate = _substrate_state()
        substrate["relations"][0]["attributes"]["bad"] = math.inf
        maps, logs, residual = _governance_state()
        with self.assertRaises(MigrationPreflightError) as caught:
            compute_candidate_commitments(
                substrate_state=substrate,
                governance_maps=maps,
                governance_logs=logs,
                governance_residual=residual,
            )
        self.assertEqual(caught.exception.reason, "candidate_value_domain_invalid")

    def test_nonfinite_extension_state_refuses_before_commitment(self):
        substrate = _substrate_state()
        maps, logs, residual = _governance_state()
        residual["adapter"]["extension_state"]["qualification"]["bad"] = -math.inf
        with self.assertRaises(MigrationPreflightError) as caught:
            compute_candidate_commitments(
                substrate_state=substrate,
                governance_maps=maps,
                governance_logs=logs,
                governance_residual=residual,
            )
        self.assertEqual(caught.exception.reason, "candidate_value_domain_invalid")

    def test_candidate_root_is_not_v1_root_with_a_new_prefix(self):
        state = _substrate_state()
        candidate = compute_substrate_v2(
            episodes=state["episodes"],
            facts=state["facts"],
            relations=state["relations"],
            schema_version=state["schema_version"],
            relation_schema_version=state["relation_schema_version"],
            id_counter=state["id_counter"],
        )
        self.assertTrue(candidate.startswith("bmerkle-v2:"))
        self.assertEqual(len(candidate.split(":", 1)[1]), 64)


if __name__ == "__main__":
    unittest.main()
