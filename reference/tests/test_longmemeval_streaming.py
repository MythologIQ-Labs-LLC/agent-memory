"""Streaming LongMemEval input (#568): bounded memory, identical protocol."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
FIXTURE = REFERENCE / "fixtures" / "benchmarks" / "longmemeval" / "synthetic.json"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))


def _module():
    spec = importlib.util.spec_from_file_location("run_longmemeval", REFERENCE / "run_longmemeval.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = _module()


def _legacy_load(path: Path) -> list[dict]:
    """The pre-#568 whole-file loader, kept verbatim as the equivalence oracle."""

    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError("LongMemEval input must be a non-empty JSON list")
    required = {
        "question_id", "question_type", "question", "answer", "question_date",
        "haystack_session_ids", "haystack_dates", "haystack_sessions", "answer_session_ids",
    }
    seen: set[str] = set()
    rows: list[dict] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"row {index} must be an object")
        missing = required.difference(raw)
        if missing:
            raise ValueError(f"row {index} missing fields: {sorted(missing)}")
        question_id = str(raw["question_id"])
        if question_id in seen:
            raise ValueError(f"row {index} duplicates question_id {question_id!r}")
        seen.add(question_id)
        session_ids = [str(item) for item in raw["haystack_session_ids"]]
        if not (len(session_ids) == len(raw["haystack_dates"]) == len(raw["haystack_sessions"])):
            raise ValueError(f"row {index} haystack arrays must have equal length")
        seen_sessions: dict[str, str] = {}
        for session_id, session in zip(session_ids, raw["haystack_sessions"]):
            content = json.dumps(session, sort_keys=True)
            if seen_sessions.setdefault(session_id, content) != content:
                raise ValueError(f"row {index} reuses session id {session_id!r} for different content")
        if not set(str(item) for item in raw["answer_session_ids"]).issubset(session_ids):
            raise ValueError(f"row {index} answer_session_ids must be present in haystack_session_ids")
        rows.append(dict(raw))
    return rows


def _rows() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _semantic(report: dict) -> dict:
    """Everything except wall-clock and process-resource fields."""

    report = json.loads(json.dumps(report))
    report.pop("execution")
    for plane in report["planes"].values():
        for backend in plane["backends"].values():
            backend.pop("timing", None)
            for row in backend["rows"]:
                row.pop("ingest_seconds", None)
                row.pop("recall_seconds", None)
    return report


class StreamingLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)

    def write(self, name: str, data: bytes | str) -> Path:
        path = Path(self._dir.name) / name
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        return path

    def stream(self, path: Path, chunk: int = 7) -> list[dict]:
        return list(M.iter_questions(M.InputStream(path, chunk_bytes=chunk)))

    def assert_both_fail(self, path: Path, pattern: str | None = None) -> None:
        with self.assertRaises(ValueError):
            _legacy_load(path)
        for chunk in (1, 3, 64, 1 << 20):
            with self.subTest(chunk=chunk):
                if pattern is None:
                    with self.assertRaises(ValueError):
                        self.stream(path, chunk)
                else:
                    with self.assertRaisesRegex(ValueError, pattern):
                        self.stream(path, chunk)

    # 1, 2, 9, 10: multi-question array, order, boundaries, equivalence with the old loader
    def test_equivalent_to_legacy_loader_for_every_chunk_size(self) -> None:
        expected = _legacy_load(FIXTURE)
        for chunk in (1, 2, 3, 5, 17, 256, 4096, 1 << 20):
            with self.subTest(chunk=chunk):
                self.assertEqual(self.stream(FIXTURE, chunk), expected)
        self.assertEqual(M._load(FIXTURE), expected)
        self.assertEqual([row["question_id"] for row in expected], [row["question_id"] for row in _rows()])

    def test_formatting_variants_parse_identically(self) -> None:
        rows = _rows()
        variants = {
            "compact": json.dumps(rows, separators=(",", ":")),
            "indented": json.dumps(rows, indent=4),
            "padded": " \n\t[\r\n " + " ,\n ".join(json.dumps(row) for row in rows) + "\n] \n\n",
        }
        for name, text in variants.items():
            path = self.write(f"{name}.json", text)
            with self.subTest(variant=name):
                self.assertEqual(self.stream(path, 5), _legacy_load(path))
                self.assertEqual(self.stream(path)[0]["question_id"], rows[0]["question_id"])
                self.assertEqual(self.stream(path)[-1]["question_id"], rows[-1]["question_id"])

    def test_single_question_array(self) -> None:
        path = self.write("one.json", json.dumps(_rows()[:1]))
        self.assertEqual(self.stream(path, 1), _legacy_load(path))

    # 4: raw-byte identity
    def test_digest_is_of_raw_source_bytes(self) -> None:
        text = json.dumps(_rows(), indent=1, ensure_ascii=False) + "\n\n"
        path = self.write("bytes.json", text)
        stream = M.InputStream(path, chunk_bytes=11)
        list(M.iter_questions(stream))
        self.assertEqual(stream.hexdigest(), hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(stream.bytes_read, path.stat().st_size)
        # the same questions serialized differently have a different identity
        other = self.write("other.json", json.dumps(_rows()))
        second = M.InputStream(other)
        list(M.iter_questions(second))
        self.assertNotEqual(second.hexdigest(), stream.hexdigest())

    def test_digest_unavailable_until_fully_consumed(self) -> None:
        stream = M.InputStream(FIXTURE)
        iterator = iter(stream)
        next(iterator)
        with self.assertRaises(ValueError):
            stream.hexdigest()

    def test_report_digest_matches_file_and_passes_agree(self) -> None:
        report = M.run(FIXTURE, corpus_class="synthetic", include_agent_memory=False)
        digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.assertEqual(report["input"]["sha256"], digest)
        self.assertEqual(report["input"]["size_bytes"], FIXTURE.stat().st_size)
        passes = report["execution"]["input_loading"]["passes"]
        self.assertEqual(len(passes), 1 + 2 * 2)  # scan + (session, turn) x (no_memory, lexical_overlap)
        self.assertTrue(all(item["sha256"] == digest for item in passes))
        self.assertEqual(report["execution"]["input_loading"]["resident_questions_max"], 1)

    def test_input_changed_between_passes_fails_closed(self) -> None:
        path = self.write("mutable.json", json.dumps(_rows()))
        original = M._scan

        def scan_then_mutate(target):
            result = original(target)
            rows = _rows()
            rows[0]["question"] = "changed after the scan"
            target.write_text(json.dumps(rows), encoding="utf-8")
            return result

        with mock.patch.object(M, "_scan", scan_then_mutate):
            with self.assertRaisesRegex(ValueError, "changed between passes"):
                M.run(path, corpus_class="synthetic", include_agent_memory=False)

    # 3: deterministic subset selection
    def test_subset_selection_matches_whole_file_selection(self) -> None:
        legacy = _legacy_load(FIXTURE)
        for size in (1, 2, 3, 5):
            for seed in ("longmemeval-subset-v1", "other"):
                expected, meta = M._subset(legacy, size=size, seed=seed)
                report = M.run(FIXTURE, corpus_class="synthetic", subset_size=size, subset_seed=seed, include_agent_memory=False)
                ids = [row["question_id"] for row in report["planes"]["session"]["backends"]["no_memory"]["rows"]]
                with self.subTest(size=size, seed=seed):
                    self.assertEqual(ids, [row["question_id"] for row in expected])
                    self.assertEqual(report["input"]["selection"]["size"], meta["size"])
                    self.assertEqual(report["input"]["question_count"], len(expected))
                    self.assertEqual(report["input"]["source_question_count"], len(legacy))
        prefix = M.run(FIXTURE, corpus_class="synthetic", max_questions=2, include_agent_memory=False)
        ids = [row["question_id"] for row in prefix["planes"]["turn"]["backends"]["lexical_overlap"]["rows"]]
        self.assertEqual(ids, [row["question_id"] for row in legacy[:2]])

    # 5: duplicate session ids
    def test_duplicate_session_ids_survive_chunk_boundaries(self) -> None:
        rows = _rows()
        first = rows[0]
        repeated = first["haystack_session_ids"][1]
        first["haystack_session_ids"].append(repeated)
        first["haystack_dates"].append("2026/08/20 (Thu) 09:00")
        first["haystack_sessions"].append(first["haystack_sessions"][1])
        # the same session id in a later question is independent of the first question
        other = rows[1]["haystack_session_ids"].index(
            next(value for value in rows[1]["haystack_session_ids"] if value not in rows[1]["answer_session_ids"])
        )
        rows[1]["haystack_session_ids"][other] = repeated
        path = self.write("dup.json", json.dumps(rows))
        legacy = _legacy_load(path)
        for chunk in (1, 13, 1 << 20):
            with self.subTest(chunk=chunk):
                streamed = self.stream(path, chunk)
                self.assertEqual(streamed, legacy)
                for granularity in ("session", "turn"):
                    self.assertEqual(M.corpus(streamed[0], granularity), M.corpus(legacy[0], granularity))
                ids = [item["id"] for item in M.corpus(streamed[0], "session")[0]]
                self.assertEqual(ids.count(repeated), 2)
                self.assertEqual(ids, [item["id"] for item in M.corpus(legacy[0], "session")[0]])
        report = M.run(path, corpus_class="synthetic", include_agent_memory=False)
        self.assertEqual(report["input"]["duplicate_session_id_question_count"], 1)
        rows[0]["haystack_sessions"][-1] = [{"role": "user", "content": "different content"}]
        conflict = self.write("conflict.json", json.dumps(rows))
        self.assert_both_fail(conflict, "different content")

    # 6: Unicode
    def test_non_ascii_text_split_across_chunks(self) -> None:
        rows = _rows()
        rows[0]["question"] = "Qué café prefiero? 東京 — naïve 🙂   end"
        rows[0]["haystack_sessions"][0][0]["content"] += " 🙂漢字ü"
        for ensure_ascii in (True, False):
            path = self.write(f"unicode-{ensure_ascii}.json", json.dumps(rows, ensure_ascii=ensure_ascii))
            for chunk in (1, 2, 3, 5):
                with self.subTest(ensure_ascii=ensure_ascii, chunk=chunk):
                    streamed = self.stream(path, chunk)
                    self.assertEqual(streamed, _legacy_load(path))
                    self.assertEqual(streamed[0]["question"], rows[0]["question"])

    def test_invalid_utf8_fails_closed(self) -> None:
        text = json.dumps(_rows(), ensure_ascii=False).encode("utf-8")
        bad = self.write("bad-utf8.json", text[:200] + b"\xff\xfe" + text[200:])
        self.assert_both_fail(bad)
        split = "[" + json.dumps(_rows()[0], ensure_ascii=False)[:-2]
        truncated = self.write("split-char.json", (split + '"é').encode("utf-8")[:-1])
        self.assert_both_fail(truncated)

    # 7: malformed / truncated
    def test_malformed_inputs_fail_closed(self) -> None:
        good = json.dumps(_rows())
        cases = {
            "truncated-mid-element": (good[: len(good) // 2], "malformed or truncated"),
            "truncated-after-element": (good[: good.index("}, {") + 1], "truncated"),
            "missing-close": (good[:-1], "truncated"),
            "trailing-comma": (good[:-1] + ",]", "malformed or truncated"),
            "missing-separator": ("[" + " ".join(json.dumps(row) for row in _rows()) + "]", "expected ','"),
            "trailing-content": (good + " []", "after the closing"),
            "trailing-garbage": (good + "x", "after the closing"),
            "second-document": (good + good, "after the closing"),
            "object-top-level": (json.dumps({"rows": _rows()}), "non-empty JSON list"),
            "empty-file": ("", "non-empty JSON list"),
            "whitespace-only": ("  \n", "non-empty JSON list"),
            "bom": ("﻿" + good, "byte-order mark"),
            "non-object-element": ("[" + json.dumps(_rows()[0]) + ", 3]", "row 1 must be an object"),
            "missing-field": (json.dumps([{k: v for k, v in _rows()[0].items() if k != "answer"}]), "missing fields"),
            "nan-garbage": ('[{"question_id": nope}]', "malformed or truncated"),
        }
        for name, (text, pattern) in cases.items():
            with self.subTest(case=name):
                self.assert_both_fail(self.write(f"{name}.json", text), pattern)

    def test_malformed_question_after_valid_ones_is_not_skipped(self) -> None:
        good = [json.dumps(row) for row in _rows()]
        text = "[" + ", ".join(good[:2]) + ', {"question_id": "broken", ' + ", ".join(good[2:]) + "]"
        path = self.write("broken-middle.json", text)
        self.assert_both_fail(path)
        with self.assertRaises(ValueError):
            M.run(path, corpus_class="synthetic", include_agent_memory=False)

    def test_oversized_element_is_refused(self) -> None:
        path = self.write("big.json", '[{"question_id": "' + "x" * 5000)
        with mock.patch.object(M, "MAX_QUESTION_CHARS", 1024):
            with self.assertRaisesRegex(ValueError, "exceeds"):
                self.stream(path, 64)

    # 8: empty array (invalid, as before)
    def test_empty_array_is_rejected_like_before(self) -> None:
        for text in ("[]", " [ \n ] ", "[]\n"):
            with self.subTest(text=text):
                self.assert_both_fail(self.write("empty.json", text), "non-empty JSON list")

    # 10: whole-report equivalence with the whole-file loader
    def test_report_semantics_identical_to_whole_file_loader(self) -> None:
        streamed = M.run(FIXTURE, corpus_class="synthetic")
        legacy_rows = _legacy_load(FIXTURE)
        # re-run the pre-#568 evaluation path over the whole-file rows
        planes = {
            granularity: {
                "backends": {
                    backend: M._evaluate_backend(legacy_rows, granularity, backend) for backend in M.BACKENDS
                }
            }
            for granularity in ("session", "turn")
        }
        self.assertEqual(_semantic({**streamed, "execution": None, "planes": planes})["planes"], _semantic(streamed)["planes"])
        self.assertEqual(streamed["input"]["question_count"], len(legacy_rows))
        self.assertEqual(
            streamed["input"]["selection"]["question_ids_sha256"],
            hashlib.sha256("\n".join(row["question_id"] for row in legacy_rows).encode("utf-8")).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
