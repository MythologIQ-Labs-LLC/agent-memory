"""Unit checks for the thin MCP/AgentMemory adapter, no sandbox network."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
import stat
from types import SimpleNamespace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bridge import HostConfig, LocalMemoryBridge


class FakeMemory:
    calls: list

    def __init__(self, calls):
        self.calls = calls

    def remember(self, key, text, **kwargs):
        self.calls.append(("remember", key, text, kwargs))
        return {"committed": True, "fact_uuid": "fact:qualified-1", "stage": "commit"}

    def forget(self, key, **kwargs):
        self.calls.append(("forget", key, kwargs))
        # Shaped like the real facade result (AgentMemory.forget, contract 1.8.0).
        return {"committed": True, "outcome": "allow_with_ledger", "stage": "forget",
                "receipt": {"receipt_id": "ref-0009", "requested_action": "pruning",
                            "selected_action": "pruning", "before_state": "v1", "after_state": "v2"}}

    def correct(self, key, text, **kwargs):
        self.calls.append(("correct", key, text, kwargs))
        # Shaped like the real facade result (AgentMemory.correct, contract 1.8.0).
        return {"committed": True, "outcome": "allow_with_ledger", "stage": "commit",
                "fact_uuid": "fact:corrected-2",
                "receipt": {"receipt_id": "ref-0011", "requested_action": "correction",
                            "selected_action": "correction"}}

    def recall_context(self, question, **kwargs):
        self.calls.append(("recall_context", question, kwargs))
        return {
            "status": "complete",
            "items": [
                {
                    "state": "resolved",
                    "content": "Our editor is Neovim.",
                    "fact_ref": "fact:qualified-1",
                    "provenance": {"memory_ref": "memory:editor", "currentness": "current_state"},
                },
                {"state": "omitted_selection", "fact_ref": "fact:distractor",
                 "reason": "subject_mismatch"},
            ],
            "selection": {"assessment": "evidence_delivered"},
        }


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.closes = []
        self.config = HostConfig(Path("/tmp/agent-mcp-test"), "tenant:a", "agent:local", "project:local")

        @contextmanager
        def opener(path, **kwargs):
            self.calls.append(("open", path, kwargs))
            try:
                yield FakeMemory(self.calls)
            finally:
                self.closes.append("closed")

        self.bridge = LocalMemoryBridge(self.config, opener)

    def test_save_calls_real_facade_contract_and_closes(self):
        result = self.bridge.remember("memory:editor", "Our editor is Neovim.")
        self.assertEqual(result["fact_ref"], "fact:qualified-1")
        self.assertTrue(result["committed"])
        self.assertIn(("remember", "memory:editor", "Our editor is Neovim.",
                       {"source_ref": "mcp:agent-observation"}), self.calls)
        self.assertEqual(self.closes, ["closed"])
        opened = self.calls[0]
        self.assertEqual(opened[2]["tenant"], "tenant:a")
        self.assertEqual(opened[2]["scope"], "project:local")

    def test_refused_write_is_not_reported_as_remembered(self):
        refusal = {
            "committed": False,
            "fact_uuid": None,
            "stage": "commit",
            "outcome": "refuse",
            "refusal": "governed_write_refused",
        }
        with patch.object(FakeMemory, "remember", return_value=refusal):
            outcome = self.bridge.remember("memory:refused", "Unverified assertion.")
        self.assertFalse(outcome["committed"])
        self.assertIsNone(outcome["fact_ref"])
        self.assertEqual(outcome["refusal"], "governed_write_refused")
        self.assertEqual(self.closes, ["closed"])

    def test_find_returns_bounded_untrusted_evidence_not_a_generated_answer(self):
        result = self.bridge.find("preferred editor", max_items=3)
        self.assertEqual(result["evidence_count"], 1)
        self.assertFalse(result["answer_generated"])
        self.assertFalse(result["answerability_verified"])
        self.assertEqual(result["evidence_assessment"], "unverified")
        self.assertEqual(result["evidence_assessment_reason"], "answer_entailment_not_checked")
        self.assertEqual(result["evidence"][0]["trust"], "untrusted_memory_text")
        self.assertEqual(result["unavailable"][0]["reason"], "subject_mismatch")
        args = [v for v in self.calls if v[0] == "recall_context"][0][2]
        self.assertEqual(args["consumer_profile"], "all_returned")
        self.assertEqual(args["max_items"], 3)
        self.assertEqual(self.closes, ["closed"])

    def test_find_reports_insufficient_evidence_without_discarding_results(self):
        # Unavailable, partial and unattributed contents cannot justify answering.
        # This is an evidence-availability guard, NOT a semantic answer checker.
        cases = (
            {"status": "empty", "items": []},
            {"status": "partial", "items": [
                {"fact_ref": "fact:partial", "state": "truncated",
                 "content": "Some incomplete text",
                 "provenance": {"memory_ref": "memory:partial"}},
            ]},
            {"status": "complete", "items": [
                {"fact_ref": "fact:no-provenance", "state": "resolved",
                 "content": "Unattributed text", "provenance": {}},
            ]},
        )
        for package in cases:
            with self.subTest(package=package["status"]), patch.object(
                FakeMemory, "recall_context", return_value=package
            ):
                result = self.bridge.find("What is the unknown access code?")
                self.assertEqual(result["evidence_assessment"], "insufficient_evidence")
                self.assertEqual(result["evidence_assessment_reason"],
                                 "no_complete_attributed_evidence")
                self.assertFalse(result["answerability_verified"])
                self.assertEqual(result["profile"], "all_returned")
                self.assertEqual(result["evidence_count"], len(result["evidence"]))
                self.assertEqual(
                    [e["state"] for e in result["evidence"]],
                    [i["state"] for i in package["items"] if i["state"] in ("resolved", "truncated")],
                )

    def test_find_old_key_generation_alone_is_insufficient_but_still_visible(self):
        # A stale fact can be recalled even when the runtime history says
        # another generation is the current key head. Do not upgrade it to
        # potential answer support or silently suppress the evidence.
        package = {
            "status": "complete",
            "items": [{
                "state": "resolved", "content": "The editor is Vim.",
                "fact_ref": "fact:previous",
                "provenance": {"memory_ref": "memory:editor"},
            }],
        }
        history = {"history": {"current_fact_uuid": "fact:current", "state_version": 3}}
        with patch.object(FakeMemory, "recall_context", return_value=package), \
                patch.object(FakeMemory, "history", return_value=history, create=True):
            result = self.bridge.find("Which editor is current?")
        self.assertEqual(result["evidence_assessment"], "insufficient_evidence")
        self.assertEqual(result["evidence_assessment_reason"], "only_non_head_evidence")
        self.assertEqual(result["profile"], "all_returned")
        self.assertEqual(result["non_head_keys"], ["memory:editor"])
        self.assertEqual(result["evidence"][0]["content"], "The editor is Vim.")
        self.assertIs(result["evidence"][0]["latest_for_key"], False)
        self.assertFalse(result["answerability_verified"])

    def test_selectivity_is_explicit_opt_in(self):
        self.bridge.find("preferred editor", experimental_selectivity=True)
        args = [v for v in self.calls if v[0] == "recall_context"][0][2]
        self.assertEqual(args["consumer_profile"], "evidence_qualified")

    def test_exact_key_uses_governed_logical_memory_ref(self):
        self.bridge.get("memory:editor")
        args = [v for v in self.calls if v[0] == "recall_context"][0][2]
        self.assertEqual(args["logical_memory_refs"], ("memory:editor",))
        self.assertEqual(args["max_items"], 8)

    def test_exact_get_does_not_launder_similar_but_wrong_memory(self):
        # Governed recall is a multi-route candidate source. Even when
        # logical_memory_refs contains the requested key, the wrapper must
        # verify actual source provenance and not return an adjacent fact.
        def wrong_fact(self_, query, **kwargs):
            return {
                "status": "complete",
                "items": [
                    {"fact_ref": "fact:other", "state": "resolved",
                     "content": "The editor is Vim.",
                     "provenance": {"memory_ref": "memory:other",
                                    "source_ref": "mcp:agent-observation"}},
                    {"fact_ref": "fact:withheld", "state": "unresolved",
                     "reason": "withheld"},
                ],
            }

        with patch.object(FakeMemory, "recall_context", wrong_fact):
            response = self.bridge.get("memory:editor")
        self.assertEqual(response["lookup_status"], "not_found_or_unavailable")
        self.assertEqual(response["evidence"], [])
        self.assertEqual(response["evidence_count"], 0)
        self.assertEqual(response["unavailable"], [])
        self.assertNotIn("Vim", repr(response))
        self.assertNotIn("fact:other", repr(response))

    def test_exact_get_returns_only_correct_key_in_mixed_results(self):
        def mixed(self_, query, **kwargs):
            return {
                "status": "complete",
                "items": [
                    {"fact_ref": "fact:other", "state": "resolved",
                     "content": "Vim", "provenance": {"memory_ref": "memory:other"}},
                    {"fact_ref": "fact:matching", "state": "resolved",
                     "content": "Neovim", "provenance": {"memory_ref": "memory:editor"}},
                ],
            }

        with patch.object(FakeMemory, "recall_context", mixed):
            response = self.bridge.get("memory:editor")
        self.assertEqual(response["lookup_status"], "found")
        self.assertEqual([item["content"] for item in response["evidence"]], ["Neovim"])
        self.assertNotIn("Vim", repr(response))

    def test_exact_get_refuses_conflicting_versions_instead_of_guessing(self):
        def duplicate_versions(self_, query, **kwargs):
            return {
                "status": "complete",
                "items": [
                    {"fact_ref": "fact:old", "state": "resolved",
                     "content": "The preferred editor is Vim.",
                     "provenance": {"memory_ref": "memory:editor"}},
                    {"fact_ref": "fact:new", "state": "resolved",
                     "content": "The preferred editor is Neovim.",
                     "provenance": {"memory_ref": "memory:editor"}},
                ],
            }

        with patch.object(FakeMemory, "recall_context", duplicate_versions):
            response = self.bridge.get("memory:editor")
        self.assertEqual(response["lookup_status"], "ambiguous_multiple_versions")
        self.assertEqual(response["evidence_count"], 0)
        self.assertEqual(response["evidence"], [])
        self.assertNotIn("Vim", repr(response))
        self.assertNotIn("Neovim", repr(response))

    def test_invalid_request_never_opens_store(self):
        for bad in ("", " ", "x" * 161):
            with self.subTest(bad=bad[:3]), self.assertRaises(ValueError):
                self.bridge.get(bad)
        with self.assertRaises(ValueError):
            self.bridge.find("query", max_items=True)
        with self.assertRaises(ValueError):
            self.bridge.remember("memory:ok", "x" * 4001)
        self.assertFalse(self.calls)

    def test_forget_is_disabled_without_exact_host_grant_and_never_opens_store(self):
        for env in ({}, {
            "AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY": "memory:editor",
        }, {
            "AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY": "memory:other",
            "AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF": "host-record:approved",
        }):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                result = self.bridge.forget("memory:editor")
                self.assertFalse(result["committed"])
                self.assertEqual(result["status"], "host_authorization_required")
                self.assertEqual(result["refusal"], "host_authorization_required")
        self.assertEqual(self.calls, [])
        self.assertEqual(self.closes, [])

    def test_forget_uses_only_public_facade_with_host_owned_evidence_ref(self):
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY": "memory:editor",
            "AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF": "host-record:approved",
        }, clear=True):
            result = self.bridge.forget("memory:editor")
        self.assertTrue(result["committed"])
        self.assertEqual(result["status"], "forgotten")
        self.assertIs(result["permanent"], False)
        self.assertIn(("forget", "memory:editor",
                       {"permanent": False, "evidence_refs": ("host-record:approved",)}), self.calls)
        self.assertEqual(self.closes, ["closed"])

    def test_forget_preserves_runtime_refusal_without_claiming_success(self):
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY": "memory:editor",
            "AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF": "host-record:approved",
        }, clear=True), patch.object(FakeMemory, "forget", return_value={
            "committed": False, "outcome": "require_review", "refusal": "insufficient_evidence",
        }):
            result = self.bridge.forget("memory:editor")
        self.assertFalse(result["committed"])
        self.assertEqual(result["status"], "not_committed")
        self.assertEqual(result["outcome"], "require_review")
        self.assertEqual(result["refusal"], "insufficient_evidence")

    def test_forget_reports_the_committed_operation_and_receipt(self):
        # A host auditing the alpha must see which governed action committed, not only "allowed".
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY": "memory:editor",
            "AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF": "host-record:approved",
        }, clear=True):
            result = self.bridge.forget("memory:editor")
        self.assertEqual(result["operation"], "pruning")
        self.assertEqual(result["receipt_id"], "ref-0009")

    def test_forget_commit_of_another_action_is_not_reported_as_forgotten(self):
        # committed=true alone is not deletion: only a committed pruning is a tombstone.
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY": "memory:editor",
            "AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF": "host-record:approved",
        }, clear=True), patch.object(FakeMemory, "forget", return_value={
            "committed": True, "outcome": "allow_with_ledger",
            "receipt": {"receipt_id": "ref-0010", "requested_action": "pruning", "selected_action": "defer"},
        }):
            result = self.bridge.forget("memory:editor")
        self.assertFalse(result["committed"])
        self.assertEqual(result["status"], "not_committed")
        self.assertEqual(result["operation"], "defer")

    # ---- memory_correct: authority is an operator-written correction record named by the host

    def _record(self, directory, key="memory:editor", text="Our editor is Helix.", **extra):
        path = Path(directory) / "correction.json"
        path.write_text(json.dumps({"key": key, "text": text, **extra}))
        return path

    def test_correct_without_host_record_refuses_and_never_opens_store(self):
        with patch.dict(os.environ, {}, clear=True):
            result = self.bridge.correct("memory:editor", "Our editor is Helix.")
        self.assertFalse(result["committed"])
        self.assertEqual(result["status"], "host_authorization_required")
        self.assertEqual(self.calls, [])

    def test_correct_record_for_another_key_or_text_refuses_and_never_opens_store(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self._record(temp)
            with patch.dict(os.environ, {"AGENT_MEMORY_MCP_CORRECTION_RECORD": str(record)}, clear=True):
                other_key = self.bridge.correct("memory:shell", "Our editor is Helix.")
                other_text = self.bridge.correct("memory:editor", "Our editor is Emacs.")
        for result in (other_key, other_text):
            self.assertFalse(result["committed"])
            self.assertEqual(result["status"], "host_authorization_required")
        self.assertEqual(self.calls, [])

    def test_correct_refuses_a_symlinked_relative_or_malformed_record(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self._record(temp)
            link = Path(temp) / "link.json"
            link.symlink_to(record)
            malformed = Path(temp) / "malformed.json"
            malformed.write_text("not json")
            for value in (str(link), "correction.json", str(malformed), str(Path(temp) / "missing.json")):
                with self.subTest(record=value), patch.dict(os.environ, {"AGENT_MEMORY_MCP_CORRECTION_RECORD": value}, clear=True):
                    result = self.bridge.correct("memory:editor", "Our editor is Helix.")
                    self.assertFalse(result["committed"])
                    self.assertEqual(result["status"], "host_authorization_required")
        self.assertEqual(self.calls, [])

    def test_correct_presents_artifact_bound_evidence_with_a_host_registered_verifier(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self._record(temp)
            digest = hashlib.sha256(record.read_bytes()).hexdigest()
            with patch.dict(os.environ, {"AGENT_MEMORY_MCP_CORRECTION_RECORD": str(record)}, clear=True):
                result = self.bridge.correct("memory:editor", "Our editor is Helix.")
            self.assertTrue(result["committed"])
            self.assertEqual(result["status"], "corrected")
            self.assertEqual((result["operation"], result["receipt_id"], result["fact_ref"]),
                             ("correction", "ref-0011", "fact:corrected-2"))
            opened = [c for c in self.calls if c[0] == "open"][0][2]
            registry = opened["verifier_registry"]
            call = [c for c in self.calls if c[0] == "correct"][0]
            self.assertEqual(call[1:3], ("memory:editor", "Our editor is Helix."))
            # No caller-chosen risk, overrides, attestation or review flags reach the facade.
            self.assertEqual(set(call[3]), {"evidence"})
            (item,) = call[3]["evidence"]
            self.assertEqual(item.digest, digest)
            self.assertIn(item.verifier, registry)
            verifier = registry.as_mapping()[item.verifier]
            self.assertTrue(verifier(item))
            # The registered verifier re-reads the record: an edited record no longer verifies.
            record.write_text(json.dumps({"key": "memory:editor", "text": "Our editor is Emacs."}))
            self.assertFalse(verifier(item))

    def test_correct_preserves_a_parked_review_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self._record(temp)
            with patch.dict(os.environ, {"AGENT_MEMORY_MCP_CORRECTION_RECORD": str(record)}, clear=True), \
                    patch.object(FakeMemory, "correct", return_value={
                        "committed": False, "outcome": "require_review",
                        "refusal": "review_requires_qualified_evidence"}):
                result = self.bridge.correct("memory:editor", "Our editor is Helix.")
        self.assertFalse(result["committed"])
        self.assertEqual(result["status"], "not_committed")
        self.assertEqual(result["outcome"], "require_review")
        self.assertIsNone(result["fact_ref"])

    def test_correct_commit_of_another_action_is_not_reported_as_corrected(self):
        with tempfile.TemporaryDirectory() as temp:
            record = self._record(temp)
            with patch.dict(os.environ, {"AGENT_MEMORY_MCP_CORRECTION_RECORD": str(record)}, clear=True), \
                    patch.object(FakeMemory, "correct", return_value={
                        "committed": True, "outcome": "allow_with_ledger", "fact_uuid": "fact:x",
                        "receipt": {"receipt_id": "ref-0012", "selected_action": "defer"}}):
                result = self.bridge.correct("memory:editor", "Our editor is Helix.")
        self.assertFalse(result["committed"])
        self.assertEqual(result["status"], "not_committed")
        self.assertIsNone(result["fact_ref"])

    def test_forget_rejects_invalid_target_before_reading_host_grant(self):
        with self.assertRaises(ValueError):
            self.bridge.forget(" ")
        self.assertEqual(self.calls, [])

    def test_missing_host_claims_fail_closed(self):
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_ROOT": "/tmp/agent-memory-dev",
            "AGENT_MEMORY_MCP_TENANT": "tenant:a",
            "AGENT_MEMORY_MCP_ACTOR": "agent:local",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "SCOPE"):
                HostConfig.from_environment()

    def test_relative_root_rejected(self):
        with patch.dict(os.environ, {
            "AGENT_MEMORY_MCP_ROOT": "./relative",
            "AGENT_MEMORY_MCP_TENANT": "tenant:a",
            "AGENT_MEMORY_MCP_ACTOR": "agent:local",
            "AGENT_MEMORY_MCP_SCOPE": "project:local",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "absolute"):
                HostConfig.from_environment()

    def test_symlinked_root_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real"
            real.mkdir()
            link = Path(temporary) / "link"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlink privilege unavailable: {error}")
            with patch.dict(os.environ, {
                "AGENT_MEMORY_MCP_ROOT": str(link),
                "AGENT_MEMORY_MCP_TENANT": "tenant:a",
                "AGENT_MEMORY_MCP_ACTOR": "agent:local",
                "AGENT_MEMORY_MCP_SCOPE": "project:local",
            }, clear=True):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    HostConfig.from_environment()

    def test_symlinked_parent_rejected_when_final_store_root_does_not_exist(self):
        # A nested path under a link is NOT itself a symlink. The previous
        # check of root.is_symlink() was therefore insufficient.
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real"
            real.mkdir()
            link = Path(temporary) / "link"
            try:
                link.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlink privilege unavailable: {error}")
            nested = link / "new-store"
            self.assertFalse(nested.is_symlink())
            self.assertFalse(nested.exists())
            with patch.dict(os.environ, {
                "AGENT_MEMORY_MCP_ROOT": str(nested),
                "AGENT_MEMORY_MCP_TENANT": "tenant:a",
                "AGENT_MEMORY_MCP_ACTOR": "agent:local",
                "AGENT_MEMORY_MCP_SCOPE": "project:local",
            }, clear=True):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    HostConfig.from_environment()
            self.assertFalse((real / "new-store").exists())

    def test_reparse_attribute_rejected_without_is_junction(self):
        # Simulate the Windows FILE_ATTRIBUTE_REPARSE_POINT bit on a machine
        # that may not be running Windows. Python 3.11 has no is_junction().
        with tempfile.TemporaryDirectory() as temporary:
            suspicious = Path(temporary) / "reparse" / "store"
            original_lstat = Path.lstat

            def lstat_with_reparse(component, *args, **kwargs):
                if component == suspicious.parent:
                    return SimpleNamespace(
                        st_mode=stat.S_IFDIR,
                        st_file_attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400),
                    )
                return original_lstat(component, *args, **kwargs)

            with patch.object(Path, "lstat", lstat_with_reparse), patch.dict(os.environ, {
                "AGENT_MEMORY_MCP_ROOT": str(suspicious),
                "AGENT_MEMORY_MCP_TENANT": "tenant:a",
                "AGENT_MEMORY_MCP_ACTOR": "agent:local",
                "AGENT_MEMORY_MCP_SCOPE": "project:local",
            }, clear=True):
                with self.assertRaisesRegex(ValueError, "junction"):
                    HostConfig.from_environment()

    def test_parent_traversal_rejected_even_in_absolute_store_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            raw_root = str(Path(temporary) / "temp" / ".." / "new-store")
            with patch.dict(os.environ, {
                "AGENT_MEMORY_MCP_ROOT": raw_root,
                "AGENT_MEMORY_MCP_TENANT": "tenant:a",
                "AGENT_MEMORY_MCP_ACTOR": "agent:local",
                "AGENT_MEMORY_MCP_SCOPE": "project:local",
            }, clear=True):
                with self.assertRaisesRegex(ValueError, "parent traversal"):
                    HostConfig.from_environment()


if __name__ == "__main__":
    unittest.main()
