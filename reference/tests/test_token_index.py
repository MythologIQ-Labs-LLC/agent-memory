"""Derived lexical token index for SQLite candidate generation (#563).

    canonical facts -> derived token index -> matching canonical fact refs
        -> canonical candidate construction -> full governed admission -> ranking

The index is derived, rebuildable, and verified against the canonical facts table. It
is never canonical memory and never permission: it only avoids tokenizing and
materializing facts that share no token with the query. These tests prove that search
through the index is identical to the reference scan (same facts, scores, order, and
``eligible`` outcomes), that governed recall is identical end to end (candidates,
admissions, refusals, ranking), and that a missing, stale, foreign, or tampered index is
detected and rebuilt rather than trusted.
"""

from __future__ import annotations

import random
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.state.sqlite_substrate import (  # noqa: E402
    TOKEN_INDEX_SCHEME,
    SQLiteTemporalGraph,
    TokenIndexIntegrityError,
)
from agentmem_ref.state.substrate import UNFILTERED, Fact  # noqa: E402

WORDS = [
    "release", "plan", "Alder", "alder,", "deploy", "window", "Friday.", "friday", "budget?", "owner",
    "café", "東京", "API", "api", "v2", "rollback", "the", "a", "is", "!", "...", "notes;", "wiki:",
]
GROUPS = ["tenant:a", "tenant:b", "tenant:c"]


def _text(rng: random.Random) -> str:
    return " ".join(rng.choice(WORDS) for _ in range(rng.randint(1, 9)))


def _fact(index: int, rng: random.Random) -> Fact:
    return Fact(
        uuid=f"fact-{index:05d}-{rng.randint(0, 999):03d}",
        fact_text=_text(rng),
        group_id=rng.choice(GROUPS),
        episode_uuids=(f"episode-{index}",),
        valid_at="2026-09-01T00:00:00Z",
        created_at="2026-09-01T00:00:00Z",
        attributes={},
    )


class SubstrateIndexEquivalenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.path = Path(self._dir.name) / "store.sqlite3"

    def _populate(self, graph: SQLiteTemporalGraph, rng: random.Random, count: int) -> list[Fact]:
        facts = [_fact(index, rng) for index in range(count)]
        with graph.transaction():
            for fact in facts:
                graph.write_fact(fact)
        return facts

    def _assert_equivalent(self, graph: SQLiteTemporalGraph, rng: random.Random, queries: int = 60) -> None:
        self.assertEqual(graph.token_index_status in ("verified", "rebuilt"), True)
        self.assertTrue(graph.verify_token_index())
        filters = [UNFILTERED, [], ["tenant:a"], ["tenant:b", "tenant:c"], ["tenant:missing"]]
        for _ in range(queries):
            query = _text(rng)
            dropped = {fact.uuid for fact in graph.all_facts() if rng.random() < 0.3}
            seen_indexed: list[str] = []
            seen_scan: list[str] = []

            def eligible_for(seen):
                def eligible(fact):
                    seen.append(fact.uuid)
                    return fact.uuid not in dropped

                return eligible

            for group_ids in filters:
                with self.subTest(query=query, group_ids=group_ids):
                    self.assertEqual(graph.search(query, group_ids), graph.search_by_scan(query, group_ids))
                    indexed = graph.search(query, group_ids, eligible=eligible_for(seen_indexed))
                    scanned = graph.search_by_scan(query, group_ids, eligible=eligible_for(seen_scan))
                    self.assertEqual(indexed, scanned)
            # the index only removes predicate calls for facts with no shared token
            self.assertTrue(set(seen_indexed) <= set(seen_scan))
        self.assertEqual(graph.search("", UNFILTERED), graph.search_by_scan("", UNFILTERED))
        self.assertEqual(graph.search(" ... !", UNFILTERED), [])

    def test_search_is_identical_to_scan(self) -> None:
        rng = random.Random(563)
        graph = SQLiteTemporalGraph(self.path)
        self.addCleanup(graph.close)
        self.assertEqual(graph.token_index_status, "rebuilt")  # new store: empty index built
        self._populate(graph, rng, 400)
        self._assert_equivalent(graph, rng)

    def test_deletes_invalidations_and_reopen_stay_identical(self) -> None:
        rng = random.Random(1)
        graph = SQLiteTemporalGraph(self.path)
        facts = self._populate(graph, rng, 250)
        with graph.transaction():
            for fact in facts[::7]:
                graph.delete_fact(fact.uuid)
            for fact in facts[1::5]:
                graph.invalidate_fact(fact.uuid, "2026-09-02T00:00:00Z", "2026-09-02T00:00:00Z")
        self._assert_equivalent(graph, rng)
        graph.close()
        reopened = SQLiteTemporalGraph(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.token_index_status, "verified")
        self._assert_equivalent(reopened, rng)

    def test_rolled_back_writes_leave_no_index_rows(self) -> None:
        rng = random.Random(2)
        graph = SQLiteTemporalGraph(self.path)
        self.addCleanup(graph.close)
        self._populate(graph, rng, 50)
        with self.assertRaises(RuntimeError):
            with graph.transaction():
                graph.write_fact(_fact(9999, rng))
                graph.delete_fact(graph.all_facts()[0].uuid)
                raise RuntimeError("abort")
        self.assertTrue(graph.verify_token_index())
        self._assert_equivalent(graph, rng, queries=10)

    def test_index_is_not_part_of_canonical_state(self) -> None:
        rng = random.Random(3)
        graph = SQLiteTemporalGraph(self.path)
        self.addCleanup(graph.close)
        self._populate(graph, rng, 40)
        digest = graph.state_digest()
        bucketed = graph.recompute_bucketed_digest()
        graph._connection.execute("DELETE FROM fact_tokens")
        graph.rebuild_token_index()
        self.assertEqual(graph.state_digest(), digest)
        self.assertEqual(graph.recompute_bucketed_digest(), bucketed)


class IndexIntegrityTests(unittest.TestCase):
    """A missing, stale, foreign-scheme, or tampered index is rebuilt at open, never trusted."""

    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.path = Path(self._dir.name) / "store.sqlite3"
        rng = random.Random(7)
        graph = SQLiteTemporalGraph(self.path)
        with graph.transaction():
            for index in range(120):
                graph.write_fact(_fact(index, rng))
        self.first = graph.all_facts()[0]
        graph.close()

    def _tamper(self, *statements: tuple[str, tuple]) -> SQLiteTemporalGraph:
        connection = sqlite3.connect(self.path)
        for sql, parameters in statements:
            connection.execute(sql, parameters)
        connection.commit()
        connection.close()
        graph = SQLiteTemporalGraph(self.path)
        self.addCleanup(graph.close)
        return graph

    def _assert_rebuilt(self, graph: SQLiteTemporalGraph) -> None:
        self.assertEqual(graph.token_index_status, "rebuilt")
        self.assertTrue(graph.verify_token_index())
        for query in ("release plan", "alder", "東京 api", "friday window"):
            self.assertEqual(graph.search(query, ["tenant:a"]), graph.search_by_scan(query, ["tenant:a"]))

    def test_clean_store_is_verified_not_rebuilt(self) -> None:
        graph = SQLiteTemporalGraph(self.path)
        self.addCleanup(graph.close)
        self.assertEqual(graph.token_index_status, "verified")

    def test_missing_row_is_rebuilt(self) -> None:
        self._assert_rebuilt(self._tamper(("DELETE FROM fact_tokens WHERE uuid = ?", (self.first.uuid,))))

    def test_forged_row_is_rebuilt(self) -> None:
        self._assert_rebuilt(self._tamper(
            ("INSERT INTO fact_tokens(group_id, token, uuid) VALUES(?, ?, ?)", ("tenant:a", "secret", self.first.uuid)),
        ))

    def test_row_moved_to_another_partition_is_rebuilt(self) -> None:
        self._assert_rebuilt(self._tamper(
            ("UPDATE fact_tokens SET group_id = 'tenant:other' WHERE uuid = ?", (self.first.uuid,)),
        ))

    def test_stale_row_for_deleted_fact_is_rebuilt(self) -> None:
        self._assert_rebuilt(self._tamper(("DELETE FROM facts WHERE uuid = ?", (self.first.uuid,))))

    def test_edited_fact_text_is_rebuilt(self) -> None:
        self._assert_rebuilt(self._tamper(
            ("UPDATE facts SET fact_text = 'entirely different words' WHERE uuid = ?", (self.first.uuid,)),
        ))

    def test_missing_index_table_or_scheme_is_rebuilt(self) -> None:
        self._assert_rebuilt(self._tamper(("DROP TABLE fact_tokens", ())))

    def test_foreign_scheme_is_rebuilt(self) -> None:
        self._assert_rebuilt(self._tamper(
            ("UPDATE agent_memory_meta SET value = 'ftok-v0' WHERE key = 'token_index_scheme'", ()),
        ))
        self.assertEqual(TOKEN_INDEX_SCHEME, "ftok-v1")

    def test_row_for_absent_fact_after_open_fails_closed(self) -> None:
        graph = SQLiteTemporalGraph(self.path)
        self.addCleanup(graph.close)
        graph._connection.execute(
            "INSERT INTO fact_tokens(group_id, token, uuid) VALUES('tenant:a', 'release', 'fact-absent')"
        )
        with self.assertRaises(TokenIndexIntegrityError):
            graph.search("release", ["tenant:a"])


class GovernedRecallIdentityTests(unittest.TestCase):
    """End to end: the facade recall result is identical with the index and with the scan."""

    def _recall_both(self, root: str, scope: str, query: str, **kwargs) -> tuple[dict, dict]:
        """Recall through the index and through the scan, each on its own identical copy
        of the store, so deterministic identifiers line up."""

        results = []
        for label, patch in (("indexed", None), ("scanned", SQLiteTemporalGraph.search_by_scan)):
            copy = Path(tempfile.mkdtemp(prefix=f"token-index-{label}-"))
            self.addCleanup(shutil.rmtree, copy, True)
            shutil.copytree(root, copy, dirs_exist_ok=True)
            if patch is None:
                # the indexed path must never fall back to the scan
                context = mock.patch.object(
                    SQLiteTemporalGraph, "search_by_scan", side_effect=AssertionError("scan used on the indexed path")
                )
            else:
                context = mock.patch.object(SQLiteTemporalGraph, "search", patch)
            with context:
                with AgentMemory.open(copy, tenant="tenant:idx", actor_id="agent:idx", scope=scope, purpose="token index") as memory:
                    results.append(memory.recall(query, **kwargs))
        return results[0], results[1]

    @staticmethod
    def _semantic(result: dict) -> dict:
        return {
            "candidates": list(result["candidates"]),
            "admitted": list(result["admitted"]),
            "admissions": {
                ref: {key: value for key, value in decision.items() if key != "evaluated_at"}
                for ref, decision in result["admissions"].items()
            },
            "candidate_policy": result.get("candidate_policy"),
        }

    def test_candidates_admissions_refusals_and_ranking_identical(self) -> None:
        rng = random.Random(11)
        with tempfile.TemporaryDirectory() as root:
            scopes = ["project:own", "project:other", "project:third"]
            for scope in scopes:
                with AgentMemory.open(root, tenant="tenant:idx", actor_id="agent:idx", scope=scope, purpose="token index") as memory:
                    for index in range(40):
                        memory.remember(f"memory:{scope}:{index}", _text(rng))
            with AgentMemory.open(root, tenant="tenant:idx", actor_id="agent:idx", scope="project:own", purpose="token index") as memory:
                memory.forget("memory:project:own:3")
            for query in ("release plan", "alder friday window", "API rollback", "東京 café", "the a is", "unmatched-term"):
                for scope in scopes:
                    indexed, scanned = self._recall_both(root, scope, query)
                    with self.subTest(query=query, scope=scope):
                        self.assertEqual(self._semantic(indexed), self._semantic(scanned))


if __name__ == "__main__":
    unittest.main()
