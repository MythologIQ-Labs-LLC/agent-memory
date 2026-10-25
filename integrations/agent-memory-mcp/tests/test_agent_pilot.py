"""The pilot harness's host-side logic, without a model: authority, checks, parsing, redaction.

Passing these says nothing about agent behavior; the pilot receipts are that evidence.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("agent_pilot", Path(__file__).resolve().parents[1] / "pilot" / "agent_pilot.py")
assert spec and spec.loader
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
SCENARIO = json.loads(pilot.SCENARIO.read_text(encoding="utf-8"))
LIFECYCLE = ("AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY", "AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF", "AGENT_MEMORY_MCP_CORRECTION_RECORD")


class AuthorityTests(unittest.TestCase):
    def test_lifecycle_authority_only_in_the_sessions_that_name_it(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            for session in SCENARIO["sessions"]:
                env, host = pilot.session_host(SCENARIO, session, run, run / "store" / "root")
                granted = {k for k in LIFECYCLE if k in env}
                marked = set((session.get("host") or {}))
                with self.subTest(session=session["id"]):
                    if "forget_grant" in marked:
                        self.assertEqual(granted, set(LIFECYCLE[:2]))
                    elif "correction_record" in marked:
                        self.assertEqual(granted, {LIFECYCLE[2]})
                        self.assertEqual(oct(Path(env[LIFECYCLE[2]]).stat().st_mode & 0o777), "0o600")
                    else:
                        self.assertEqual(granted, set())
                        self.assertIsNone(host["lifecycle_authority"])
                    self.assertEqual(env["AGENT_MEMORY_MCP_ACTOR"], pilot.ACTOR)

    def test_tool_arguments_cannot_carry_authority(self):
        # The five tools take only key/text/question/max_items/experimental_selectivity.
        import server  # noqa: F401  (server.py, on sys.path through the harness import)
        import inspect
        for name in pilot.TOOLS:
            params = set(inspect.signature(getattr(server, name)).parameters)
            self.assertLessEqual(params, {"key", "text", "question", "max_items", "experimental_selectivity"}, name)

    def test_evidence_contract_separates_derived_conclusions_from_stored_facts(self):
        # S06 in all three pilot runs moved a schedule comparison under "From memory".
        # This regression checks the agent-facing instruction, not model adherence.
        contract = pilot.CONTRACT.read_text(encoding="utf-8")
        self.assertIn("Comparisons or conclusions drawn from one or several memories", contract)
        self.assertIn("even if they seem obvious", contract)
        self.assertIn("Under `From memory`, report the original facts separately.", contract)
        self.assertIn("`Inference (not stated in memory):`", contract)

    def test_the_host_scrubs_its_own_memory_environment_before_starting_the_agent(self):
        self.assertTrue(all(k.startswith(pilot.HOST_ONLY) for k in LIFECYCLE))


class EvaluationTests(unittest.TestCase):
    calls = [{"tool": "memory_forget", "input": {"key": "memory:pilot:compost"}, "is_error": False,
              "body": {"committed": False, "status": "host_authorization_required"}},
             {"tool": "memory_find", "input": {"question": "q"}, "is_error": False,
              "body": {"evidence": [{"memory_ref": "memory:pilot:compost", "state": "resolved", "content": "C."}]}}]
    state = {"memory:pilot:compost": {"lookup_status": "found", "facts": [("f1", "C.")], "key_state_version": 1}}

    def ev(self, check, after=None):
        evidence = pilot.delivered(self.calls)
        return pilot.evaluate(check, self.calls, evidence, self.state, after or self.state)

    def test_checks(self):
        self.assertTrue(self.ev({"tool_result": {"tool": "memory_forget", "field": "committed", "equals": False}}))
        self.assertTrue(self.ev({"tool_not_called": "memory_remember"}))
        self.assertTrue(self.ev({"delivered_key": "memory:pilot:compost"}))
        self.assertFalse(self.ev({"not_delivered_key": "memory:pilot:compost"}))
        self.assertTrue(self.ev({"logical_unchanged": ["memory:pilot:compost"]}))
        changed = {"memory:pilot:compost": {"lookup_status": "found", "facts": [("f2", "D.")], "key_state_version": 2}}
        self.assertFalse(self.ev({"logical_unchanged": ["memory:pilot:compost"]}, changed))
        self.assertFalse(self.ev({"tool_result": {"tool": "memory_correct", "field": "committed", "equals": False}}))
        with self.assertRaises(ValueError):
            self.ev({"made_up": 1})


class TranscriptTests(unittest.TestCase):
    def test_tool_calls_are_joined_to_their_structured_results(self):
        events = [{"type": "system", "subtype": "init", "model": "m", "tools": ["mcp__agent-memory__memory_get"]},
                  {"type": "assistant", "message": {"content": [
                      {"type": "tool_use", "id": "t1", "name": "mcp__agent-memory__memory_get", "input": {"key": "memory:a"}}]}},
                  {"type": "user", "message": {"content": [
                      {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": json.dumps({"lookup_status": "found"})}]}]}},
                  {"type": "result", "result": "Final.", "num_turns": 2, "total_cost_usd": 0.1, "is_error": False}]
        record = pilot.transcript(events)
        self.assertEqual(record["tool_calls"], [{"tool": "memory_get", "input": {"key": "memory:a"}, "is_error": False,
                                                 "body": {"lookup_status": "found"}, "raw": None}])
        self.assertEqual(record["final_text"], "Final.")

    def test_stream_receipts_keep_only_the_conversation_and_a_minimal_init(self):
        events = [{"type": "system", "subtype": "init", "model": "m", "tools": ["t"], "scratchpad_path": "/tmp/x",
                   "messaging_socket_path": "/tmp/cc-socks/1.sock", "plugins": [{"name": "p"}]},
                  {"type": "rate_limit_event", "x": 1}, {"type": "assistant", "message": {}},
                  {"type": "system", "subtype": "post_turn_summary"}, {"type": "result", "result": "r"}]
        kept = pilot.conversation_events(events)
        self.assertEqual([e["type"] for e in kept], ["system", "assistant", "result"])
        self.assertNotIn("scratchpad_path", kept[0])
        self.assertNotIn("plugins", kept[0])
        self.assertEqual(pilot.redact({"s": "/tmp/cc-socks/1.sock"}, Path("/nowhere")), {"s": "<TMP>"})

    def test_receipts_are_redacted(self):
        run = Path("/tmp/pilot-run-x")
        self.assertEqual(pilot.redact({"p": "/tmp/pilot-run-x/store/root", "h": str(Path.home()) + "/x"}, run),
                         {"p": "<RUN>/store/root", "h": "<HOME>/x"})


if __name__ == "__main__":
    unittest.main()
