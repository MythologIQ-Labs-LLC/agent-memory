"""#772: the JSON checkpoint store validates its generation journal in O(appended) work
per checkpoint while keeping the full-walk verdict.

Finding: `JsonRuntimeStateStore._current_manifest_and_journal` re-read and re-digested every
journal record on every checkpoint, so a store built through the governed write path cost
O(generations) per write and grew quadratically (the "superlinear retain" of #772 reproduces
on `ConfiguredCompositionRuntime`, not on the qualified SQLite profile). The warm path now
re-hashes the already walked prefix and chains only the appended records. These tests pin
(1) the cost bound and (2) that every tampering, truncation and torn-write verdict is the
same one a cold recovery reaches.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref.runtime import restart_runtime
from agentmem_ref.runtime.restart_runtime import (
    RestartSafeRuntime,
    RuntimeCheckpointConflict,
    RuntimeRecoveryError,
)
from tests.test_transactional_checkpoint_generations import _profile

JOURNAL = "runtime-generation-journal.jsonl"


class _CountingWalk:
    """Wrap the chain walk and record how many records each call validated."""

    def __init__(self):
        self.calls: list[int] = []
        self._real = restart_runtime._validate_generation_journal

    def __call__(self, records, **kw):
        records = list(records)
        self.calls.append(len(records))
        return self._real(records, **kw)


class JournalValidationScaling(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = _profile()
        self.journal = self.root / JOURNAL

    def _runtime(self):
        return RestartSafeRuntime.create(self.root, tenant="tenant-acme", profile=self.profile)

    def _rows(self):
        return [json.loads(row) for row in self.journal.read_text(encoding="utf-8").splitlines()]

    def _write_rows(self, rows, *, trailing_newline=True):
        text = "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
        self.journal.write_text(text + ("\n" if trailing_newline else ""), encoding="utf-8")

    def test_warm_checkpoints_do_not_rewalk_the_journal(self):
        runtime = self._runtime()
        counting = _CountingWalk()
        with mock.patch.object(restart_runtime, "_validate_generation_journal", counting):
            for _ in range(60):
                runtime.checkpoint()
        self.assertEqual(len(self._rows()), 61)
        # the first checkpoint after creation walks the one record `create` appended before
        # any cache existed; every later warm checkpoint parses and chains nothing
        self.assertLessEqual(counting.calls[0], 1, counting.calls)
        self.assertEqual(set(counting.calls[1:]), {0}, counting.calls)
        # and a cold recovery still walks the whole chain once
        counting.calls.clear()
        with mock.patch.object(restart_runtime, "_validate_generation_journal", counting):
            RestartSafeRuntime.recover(self.root, profile=self.profile)
        self.assertEqual(counting.calls, [61])

    def test_total_validation_work_is_linear_in_checkpoints(self):
        runtime = self._runtime()
        counting = _CountingWalk()
        with mock.patch.object(restart_runtime, "_validate_generation_journal", counting):
            for _ in range(200):
                runtime.checkpoint()
        # a full re-walk per checkpoint would sum to 200*201/2 = 20100
        self.assertLessEqual(sum(counting.calls), 2 * 200)

    def test_another_writers_append_is_validated_on_the_warm_path(self):
        writer_a = self._runtime()
        writer_a.checkpoint()  # a's cache is warm at generation 2
        writer_b = RestartSafeRuntime.recover(self.root, profile=self.profile)
        self.assertEqual(writer_b.checkpoint().generation, 3)
        counting = _CountingWalk()
        with mock.patch.object(restart_runtime, "_validate_generation_journal", counting):
            with self.assertRaisesRegex(RuntimeCheckpointConflict, "generation conflict"):
                writer_a.checkpoint()
        # a chained exactly b's one appended record, rather than re-walking the chain
        self.assertEqual(counting.calls, [1])
        # a corrupt record appended by another process is still reported, with its line number
        self.journal.write_bytes(self.journal.read_bytes() + b"{not json\n")
        with self.assertRaisesRegex(RuntimeRecoveryError, "corrupt at record 4"):
            writer_a.checkpoint()
        with self.assertRaisesRegex(RuntimeRecoveryError, "corrupt at record 4"):
            RestartSafeRuntime.recover(self.root, profile=self.profile)

    def test_every_prefix_edit_reaches_the_cold_verdict(self):
        """Each mutation is applied under a warm instance; the warm checkpoint and a cold
        recovery must raise the same error, or both succeed."""

        def digest_tamper(rows):
            rows[1]["record_digest"] = "sha256:" + "0" * 64
            return rows

        def generation_tamper(rows):
            rows[1]["generation"] = 7
            return rows

        def swap(rows):
            rows[1], rows[2] = rows[2], rows[1]
            return rows

        def truncate(rows):
            return rows[:-1]

        def forge_append(rows):
            forged = dict(rows[-1])
            forged["generation"] = rows[-1]["generation"] + 1
            return rows + [forged]

        def replace_prefix_same_length(rows):
            # same byte length, different content: the hash comparison must catch it
            digest = rows[0]["record_digest"]
            rows[0]["record_digest"] = digest[:-1] + ("0" if digest[-1] != "0" else "1")
            return rows

        def blank_line_inserted(rows):
            return rows  # handled below with raw bytes

        cases = {
            "digest_tamper": digest_tamper,
            "generation_tamper": generation_tamper,
            "swap": swap,
            "truncate": truncate,
            "forge_append": forge_append,
            "replace_prefix_same_length": replace_prefix_same_length,
        }
        for name, mutate in cases.items():
            with self.subTest(mutation=name):
                temp = tempfile.TemporaryDirectory()
                self.addCleanup(temp.cleanup)
                self.root = Path(temp.name)
                self.journal = self.root / JOURNAL
                runtime = self._runtime()
                for _ in range(4):
                    runtime.checkpoint()  # warm cache, generation 5
                self._write_rows(mutate(self._rows()))
                warm = cold = None
                try:
                    runtime.checkpoint()
                except RuntimeRecoveryError as exc:
                    warm = (type(exc).__name__, str(exc))
                try:
                    RestartSafeRuntime.recover(self.root, profile=self.profile)
                except RuntimeRecoveryError as exc:
                    cold = (type(exc).__name__, str(exc))
                self.assertIsNotNone(cold, name)
                self.assertEqual(warm, cold, name)

    def test_prefix_without_trailing_newline_falls_back_to_the_full_walk(self):
        runtime = self._runtime()
        for _ in range(3):
            runtime.checkpoint()
        self._write_rows(self._rows(), trailing_newline=False)
        counting = _CountingWalk()
        with mock.patch.object(restart_runtime, "_validate_generation_journal", counting):
            evidence = runtime.checkpoint()  # the full walk accepts the same records
        self.assertEqual(evidence.generation, 5)
        self.assertEqual(counting.calls, [4])
        # the append joined the unterminated line; both paths now report the same corruption
        with self.assertRaisesRegex(RuntimeRecoveryError, "corrupt at record 4"):
            runtime.checkpoint()
        with self.assertRaisesRegex(RuntimeRecoveryError, "corrupt at record 4"):
            RestartSafeRuntime.recover(self.root, profile=self.profile)

    def test_rows_between_checkpoints_are_unchanged_by_the_cache(self):
        runtime = self._runtime()
        before = self._rows()
        for _ in range(5):
            runtime.checkpoint()
        after = self._rows()
        self.assertEqual(after[: len(before)], before)
        self.assertEqual([row["generation"] for row in after], list(range(1, 7)))
        recovered = RestartSafeRuntime.recover(self.root, profile=self.profile)
        self.assertEqual(recovered.recovery_evidence.generation, 6)


if __name__ == "__main__":
    unittest.main()


class WarmPathNumbersRecordsLikeTheColdWalk(JournalValidationScaling):
    """Independent review finding (P2): with blank or whitespace-only lines in the walked
    prefix, a tampered appended record must be reported with the same record index as a cold
    recovery (records number the chain; lines number parser errors)."""

    def _forge(self):
        rows = self._rows()
        forged = dict(rows[-1], generation=rows[-1]["generation"] + 1,
                      previous_record_digest=rows[-1]["record_digest"], record_digest="sha256:" + "0" * 64)
        with self.journal.open("ab") as handle:
            handle.write(json.dumps(forged, sort_keys=True, separators=(",", ":")).encode() + b"\n")

    def _rows(self):
        return [json.loads(row) for row in self.journal.read_text(encoding="utf-8").splitlines() if row.strip()]

    def _verdicts(self, runtime):
        warm = cold = None
        try:
            runtime.checkpoint()
        except RuntimeRecoveryError as exc:
            warm = str(exc)
        try:
            RestartSafeRuntime.recover(self.root, profile=self.profile)
        except RuntimeRecoveryError as exc:
            cold = str(exc)
        return warm, cold

    def test_blank_line_in_prefix_then_forged_record(self):
        runtime = self._runtime()
        runtime.checkpoint()
        with self.journal.open("ab") as handle:
            handle.write(b"\n")
        runtime.checkpoint()  # the warm path now carries the blank line in its prefix
        self._forge()
        warm, cold = self._verdicts(runtime)
        self.assertIsNotNone(cold)
        self.assertEqual(warm, cold)
        self.assertIn("record 4 digest mismatch", cold)

    def test_whitespace_lines_in_prefix_then_forged_record(self):
        runtime = self._runtime()
        with self.journal.open("ab") as handle:
            handle.write(b"   \n\n")
        runtime.checkpoint()
        self._forge()
        warm, cold = self._verdicts(runtime)
        self.assertIsNotNone(cold)
        self.assertEqual(warm, cold)
        self.assertIn("record 3 digest mismatch", cold)

    def test_blank_prefix_then_corrupt_line_keeps_line_numbering(self):
        runtime = self._runtime()
        with self.journal.open("ab") as handle:
            handle.write(b"\n")
        runtime.checkpoint()
        with self.journal.open("ab") as handle:
            handle.write(b"{not json\n")
        warm, cold = self._verdicts(runtime)
        self.assertEqual(warm, cold)
        self.assertIn("corrupt at record 4", cold)
