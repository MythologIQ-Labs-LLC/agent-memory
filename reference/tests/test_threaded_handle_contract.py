"""#530: one AgentMemory handle is safe to call from worker threads.

Runtime-owned serialization must preserve single-writer SQLite generations,
generation/CAS behavior, atomic canonical + governance publication, rollback
restoration, and restart recovery.
"""

from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402

TENANT = "tenant:threads"
SCOPE = "project:threads"


def _open(root) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:threads", scope=SCOPE, purpose="thread contract")


def _generation(memory: AgentMemory) -> int:
    return memory.runtime.durable_runtime.base.recovery_evidence.generation


class ThreadedHandleContract(unittest.TestCase):
    def test_write_and_recall_from_a_non_creator_thread(self):
        with tempfile.TemporaryDirectory() as root, _open(root) as memory:
            with ThreadPoolExecutor(max_workers=1) as pool:
                written = pool.submit(memory.remember, "memory:worker", "The worker codename is Alder.").result()
                recalled = pool.submit(memory.recall, "What is the worker codename?").result()
            self.assertTrue(written["committed"])
            self.assertEqual(recalled["admitted"], [written["fact_uuid"]])

    def test_concurrent_writers_and_readers_serialize_into_contiguous_generations(self):
        writes, readers = 160, 40
        with tempfile.TemporaryDirectory() as root:
            with _open(root) as memory:
                start = _generation(memory)

                def write(index):
                    return memory.remember(f"memory:concurrent:{index:03d}", f"Concurrent token TOKEN{index:03d} is stored.")

                def read(index):
                    return memory.recall(f"Which concurrent token TOKEN{index:03d} is stored?")

                with ThreadPoolExecutor(max_workers=16) as pool:
                    futures = [pool.submit(write, index) for index in range(writes)]
                    futures += [pool.submit(read, index) for index in range(readers)]
                    results = [future.result() for future in futures]
                self.assertTrue(all(result["committed"] for result in results[:writes]))
                self.assertEqual(len({result["fact_uuid"] for result in results[:writes]}), writes)
                # Every operation (write or governed read) is exactly one generation.
                self.assertEqual(_generation(memory), start + writes + readers)
                for index in range(writes):
                    self.assertIsNotNone(memory.runtime.adapter.current_fact_uuid(f"memory:concurrent:{index:03d}"))
                final = _generation(memory)
            with _open(root) as recovered:  # full journal/state verification on recovery
                self.assertEqual(_generation(recovered), final)
                admitted = recovered.recall("Concurrent token TOKEN007 is stored")["admitted"]
                self.assertIn(recovered.runtime.adapter.current_fact_uuid("memory:concurrent:007"), admitted)

    def test_operations_never_interleave(self):
        with tempfile.TemporaryDirectory() as root, _open(root) as memory:
            base = memory.runtime.durable_runtime.base
            original = base._persist_unlocked
            active = {"now": 0, "max": 0}
            guard = threading.Lock()

            def probe():
                with guard:
                    active["now"] += 1
                    active["max"] = max(active["max"], active["now"])
                try:
                    threading.Event().wait(0.001)
                    return original()
                finally:
                    with guard:
                        active["now"] -= 1

            base._persist_unlocked = probe
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda i: memory.remember(f"memory:probe:{i}", f"probe fact {i}"), range(64)))
            self.assertEqual(active["max"], 1)

    def test_failed_operation_in_one_thread_does_not_strand_partial_state(self):
        with tempfile.TemporaryDirectory() as root:
            with _open(root) as memory:
                adapter = memory.runtime.durable_runtime.base.adapter
                original = adapter.commit_proposal

                def sometimes_fail(proposal, fact_text, *args, **kwargs):
                    outcome = original(proposal, fact_text, *args, **kwargs)
                    if "POISON" in fact_text:
                        raise RuntimeError("injected failure after in-memory governance mutation")
                    return outcome

                adapter.commit_proposal = sometimes_fail

                def write(index):
                    text = f"POISON fact {index}" if index % 5 == 0 else f"healthy fact {index}"
                    try:
                        return memory.remember(f"memory:mixed:{index:02d}", text)
                    except RuntimeError:
                        return None

                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(write, range(40)))
                adapter.commit_proposal = original
                failed = [index for index, result in enumerate(results) if result is None]
                self.assertEqual(failed, list(range(0, 40, 5)))
                for index in range(40):
                    current = memory.runtime.adapter.current_fact_uuid(f"memory:mixed:{index:02d}")
                    if index in failed:
                        self.assertIsNone(current, index)  # governance restored; nothing published
                    else:
                        self.assertIsNotNone(current, index)
                final = _generation(memory)
                self.assertTrue(memory.remember("memory:after", "healthy after failures")["committed"])
                final += 1
            with _open(root) as recovered:
                self.assertEqual(_generation(recovered), final)
                for index in failed:
                    self.assertIsNone(recovered.runtime.adapter.current_fact_uuid(f"memory:mixed:{index:02d}"))

    def test_use_after_close_from_worker_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as root:
            memory = _open(root)
            memory.close()
            with ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaisesRegex(RuntimeError, "closed"):
                    pool.submit(memory.remember, "memory:late", "too late").result()

    def test_lock_is_one_runtime_owned_boundary(self):
        with tempfile.TemporaryDirectory() as root, _open(root) as memory:
            base = memory.runtime.durable_runtime.base
            self.assertIs(memory._serialization_lock, base.serialization_lock)
            self.assertIs(memory.runtime.serialization_lock, base.serialization_lock)
            self.assertIs(memory.runtime.durable_runtime.serialization_lock, base.serialization_lock)


if __name__ == "__main__":
    unittest.main()
