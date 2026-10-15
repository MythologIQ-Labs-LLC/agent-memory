"""AML Cycle 2 service against the real Agent Memory runtime (no mocks of the memory system).

Run from the repository root:
    PYTHONPATH=reference:integrations/aml-cycle2/src python -m unittest discover -s integrations/aml-cycle2/tests
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from aml_agent_memory import contract, smoke, store
from aml_agent_memory.server import AMLServer

KEY = "test-key-0123456789abcdef"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _call(base: str, method: str, path: str, body=None, headers=None):
    request = urllib.request.Request(
        base + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method,
        headers={"Content-Type": "application/json", **(headers if headers is not None else {"Authorization": f"Bearer {KEY}"})},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def _add_body(user: str, request_id: str, count: int, word: str = "lantern") -> dict:
    return {
        "request_id": request_id,
        "user_id": user,
        "session_id": f"session:{request_id}",
        "messages": [{"role": "user", "timestamp": 1704067200000 + i, "content": f"note {i} about the {word}"} for i in range(count)],
    }


class InProcessServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = store.MemoryStore(self.tmp.name, max_open=2)
        self.server = AMLServer(("127.0.0.1", 0), self.store, KEY)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.addCleanup(self._stop)

    def _stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.tmp.cleanup()

    def test_published_contract_smoke_passes(self):
        report = smoke.run(smoke.Client(self.base, KEY))
        failed = [item for item in report["checks"] if not item["passed"]]
        self.assertEqual(failed, [])
        self.assertGreaterEqual(report["passed"], 21)

    def test_every_documented_auth_scheme_is_accepted_and_others_refused(self):
        body = {"query": "x", "user_id": "u", "top_k": 1}
        for headers, expected in (
            ({"Authorization": f"Bearer {KEY}"}, 200),
            ({"Authorization": f"Token {KEY}"}, 200),
            ({"X-Api-Key": KEY}, 200),
            ({"Authorization": f"Basic {KEY}"}, 401),
            ({"Authorization": "Bearer "}, 401),
            ({}, 401),
        ):
            with self.subTest(headers=headers):
                self.assertEqual(_call(self.base, "POST", "/search", body, headers)[0], expected)

    def test_strict_validation_without_coercion(self):
        good = _add_body("u", "r", 1)
        for mutate in (
            lambda b: b.pop("session_id"),
            lambda b: b.update(user_id="  "),
            lambda b: b["messages"][0].pop("role"),
            lambda b: b["messages"][0].update(timestamp="1704067200000"),
            lambda b: b["messages"][0].update(timestamp=1.5),
            lambda b: b["messages"][0].update(content=""),
        ):
            body = json.loads(json.dumps(good))
            mutate(body)
            with self.subTest(body=body):
                self.assertEqual(_call(self.base, "POST", "/add", body)[0], 422)
        for top_k in ("100", 100.0, True, -1, None):
            with self.subTest(top_k=top_k):
                self.assertEqual(_call(self.base, "POST", "/search", {"query": "q", "user_id": "u", "top_k": top_k})[0], 422)
        body = dict(good, metadata={"ignored": True})
        self.assertEqual(_call(self.base, "POST", "/add", body)[0], 200)

    def test_concurrent_users_are_isolated_and_complete(self):
        users = [f"user-{i}" for i in range(8)]

        def work(index: int):
            user = users[index]
            word = f"token{index}x"
            for chunk in range(3):
                status, _ = _call(self.base, "POST", "/add", _add_body(user, f"r{chunk}", 10, word))
                assert status == 200, status
            return _call(self.base, "POST", "/search", {"query": f"the {word}", "user_id": user, "top_k": 100})

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(work, range(8)))
        for index, (status, payload) in enumerate(results):
            self.assertEqual(status, 200)
            contents = [item["content"] for item in payload["data"]]
            self.assertEqual(len(contents), 30)
            self.assertTrue(all(f"token{index}x" in text for text in contents))
        # max_open=2 forced handle eviction and reopen throughout; data survived it.
        self.assertLessEqual(sum(user.is_open for user in self.store._users.values()), 2)

    def test_crash_after_fact_commit_before_ledger_record_resumes_without_duplicates(self):
        body = _add_body("crash-user", "req-1", 6)
        real_remember = store.AgentMemory.remember
        calls = {"n": 0}

        def crash_on_third(self_, *args, **kwargs):
            outcome = real_remember(self_, *args, **kwargs)
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("simulated crash after commit, before the ledger recorded it")
            return outcome

        with mock.patch.object(store.AgentMemory, "remember", crash_on_third):
            status, payload = _call(self.base, "POST", "/add", body)
        self.assertEqual((status, payload["detail"]["reason"]), (500, "internal_error"))
        # Only ledger-acknowledged facts are visible before the retry.
        status, payload = _call(self.base, "POST", "/search", {"query": "the lantern", "user_id": "crash-user", "top_k": 100})
        self.assertEqual(len(payload["data"]), 2)
        status, payload = _call(self.base, "POST", "/add", body)
        self.assertEqual(status, 200)
        status, payload = _call(self.base, "POST", "/search", {"query": "the lantern", "user_id": "crash-user", "top_k": 100})
        contents = sorted(item["content"] for item in payload["data"])
        self.assertEqual(len(contents), 6)
        self.assertEqual(len(set(contents)), 6)
        # The runtime holds exactly six facts: the crashed write was adopted, not repeated.
        user = self.store._user("crash-user", create=False)
        with user.lock:
            memory, _ = user._open()
            self.assertEqual(len(memory.recall("the lantern")["admitted"]), 6)


class ProcessRestartTests(unittest.TestCase):
    """Real server processes: graceful restart and SIGKILL after acknowledged writes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.process = None
        self.addCleanup(self._kill)

    def _start(self):
        env = dict(os.environ, AML_MEMORY_KEY=KEY, PYTHONPATH=os.pathsep.join(
            [str(REPO_ROOT / "reference"), str(REPO_ROOT / "integrations" / "aml-cycle2" / "src")]))
        self.process = subprocess.Popen(
            [sys.executable, "-m", "aml_agent_memory", "--data-dir", self.tmp.name, "--port", str(self.port)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if _call(self.base, "GET", "/health", headers={})[0] == 200:
                    return
            except OSError:
                time.sleep(0.1)
        raise AssertionError("service did not become healthy")

    def _kill(self):
        if self.process is not None and self.process.poll() is None:
            self.process.kill()
            self.process.wait()

    def _search(self):
        status, payload = _call(self.base, "POST", "/search", {"query": "the lantern", "user_id": "durable", "top_k": 100})
        self.assertEqual(status, 200)
        return sorted((item["id"], item["content"]) for item in payload["data"])

    def test_acknowledged_writes_survive_sigterm_and_sigkill_and_replay_stays_idempotent(self):
        self._start()
        body = _add_body("durable", "req-a", 20)
        self.assertEqual(_call(self.base, "POST", "/add", body)[0], 200)
        before = self._search()
        self.assertEqual(len(before), 20)

        self.process.send_signal(signal.SIGTERM)
        self.assertEqual(self.process.wait(timeout=30), 0)
        self._start()
        self.assertEqual(self._search(), before)

        self.assertEqual(_call(self.base, "POST", "/add", _add_body("durable", "req-b", 5))[0], 200)
        after_b = self._search()
        self.assertEqual(len(after_b), 25)
        self.process.kill()  # SIGKILL: no shutdown path runs
        self.process.wait()
        self._start()
        self.assertEqual(self._search(), after_b)
        status, payload = _call(self.base, "POST", "/add", body)
        self.assertEqual((status, payload["request_id"]), (200, "req-a"))
        self.assertEqual(self._search(), after_b)
        self.assertEqual(_call(self.base, "POST", "/add", dict(body, session_id="other"))[0], 409)

    def test_service_refuses_to_start_without_a_key(self):
        env = dict(os.environ, AML_MEMORY_KEY="", PYTHONPATH=str(REPO_ROOT / "reference") + os.pathsep + str(REPO_ROOT / "integrations" / "aml-cycle2" / "src"))
        result = subprocess.run([sys.executable, "-m", "aml_agent_memory", "--data-dir", self.tmp.name], env=env, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("memory system key", result.stderr)


class ContractUnitTests(unittest.TestCase):
    def test_digest_ignores_ids_and_changes_with_payload(self):
        add = contract.validate_add(_add_body("u", "r", 2))
        same = contract.validate_add(dict(_add_body("v", "s", 2), session_id="session:r"))
        self.assertEqual(contract.add_payload_digest(add), contract.add_payload_digest(same))
        other = contract.validate_add(_add_body("u", "r", 3))
        self.assertNotEqual(contract.add_payload_digest(add), contract.add_payload_digest(other))

    def test_top_k_is_clamped_not_refused_above_the_maximum(self):
        self.assertEqual(contract.validate_search({"query": "q", "user_id": "u", "top_k": 10**6})["top_k"], contract.MAX_TOP_K)

    def test_memory_text_carries_timestamp_and_role(self):
        self.assertEqual(store.memory_text({"role": "user", "content": "hi", "timestamp": 1704067200000}), "[2024-01-01T00:00:00Z] user: hi")
        self.assertEqual(store.memory_text({"role": "assistant", "content": "ok", "timestamp": None}), "assistant: ok")


if __name__ == "__main__":
    unittest.main()
