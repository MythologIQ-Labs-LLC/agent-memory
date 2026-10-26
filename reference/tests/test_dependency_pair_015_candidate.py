"""Offline #826 preflight contract tests. They do NOT qualify the real SDK pair."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_dependency_pair_015_candidate import require_exact_versions, probe_manifest_delta


class FakeCheckpoint:
    @classmethod
    def from_ops(cls, ops, representation, **kwargs):
        return SimpleNamespace(tree_size=len(ops), ops=list(ops))


class FakeTree:
    def consistency_proof(self, size):
        return [b"synthetic-proof"]


def fake_tree(ops, representation):
    return FakeTree()


def correct_verifier(prev, new, ops, proof, *, representation, now):
    assert representation == "kv"
    assert isinstance(now, datetime)
    correct = (ops == new.ops[len(prev.ops):] and proof == [b"synthetic-proof"])
    return SimpleNamespace(accepted=correct, reason="accepted" if correct else "drift")


class MigrationCandidateTests(unittest.TestCase):
    def test_exact_pair_rejects_drift(self):
        expected = {"agent-manifest": "0.15.0", "agentrust-trace": "0.11.0"}
        self.assertEqual(require_exact_versions(lambda name: expected[name]), expected)
        with self.assertRaisesRegex(RuntimeError, "unqualified dependency pair"):
            require_exact_versions(lambda name: {
                "agent-manifest": "0.12.0", "agentrust-trace": "0.11.0",
            }[name])

    def test_probe_checks_accepted_append_and_four_negative_cases(self):
        result = probe_manifest_delta(FakeCheckpoint, fake_tree, correct_verifier)
        self.assertEqual(result["valid_append"], "accepted")
        self.assertEqual(len(result["negative_controls"]), 4)
        self.assertFalse(result["operation_metadata_outside_leaf_encoder_authenticated"])

    def test_probe_fails_if_wrong_appended_bytes_are_accepted(self):
        def bad_verify(prev, new, ops, proof, *, representation, now):
            return SimpleNamespace(accepted=True, reason="accepted")
        with self.assertRaisesRegex(AssertionError, "did not reject"):
            probe_manifest_delta(FakeCheckpoint, fake_tree, bad_verify)

    def test_probe_fails_if_valid_append_refused(self):
        def bad_verify(prev, new, ops, proof, *, representation, now):
            return SimpleNamespace(accepted=False, reason="drift")
        with self.assertRaisesRegex(AssertionError, "rejected the valid"):
            probe_manifest_delta(FakeCheckpoint, fake_tree, bad_verify)

    def test_probe_passes_keyword_representation_to_new_api(self):
        calls = []
        def capture(prev, new, ops, proof, *, representation, now):
            calls.append((ops, representation))
            return correct_verifier(prev, new, ops, proof, representation=representation, now=now)
        probe_manifest_delta(FakeCheckpoint, fake_tree, capture)
        self.assertEqual(len(calls), 5)
        self.assertTrue(all(rep == "kv" for _, rep in calls))


if __name__ == "__main__":
    unittest.main()
