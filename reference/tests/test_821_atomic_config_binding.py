"""#821: a SQLite generation and its configuration binding commit as one transaction.

Before #821 the configuration binding of a SQLite config-bound store was a file written after
the SQLite COMMIT (``SQLiteConfigBoundRestartRuntime._bind_current_base``). A process that died
between the two left generation N+1 committed and the binding at N, and recovery failed closed
(``configuration binding does not match recovered base checkpoint: generation``). The preregistered
contract is ``reports/validation/821-atomic-config-binding/PREREGISTRATION.md``; each test names
the matrix row (M1..M21) or invariant (A1..A10) it checks.

Crash tests kill a real child process with ``os._exit`` (no ``finally``, no ``close()``). Every
byte-level assertion reads the store through an independent SQLite connection. Tests marked
FAIL-FIRST fail on the frozen #816 head ``d2fc9782``; the record of that run is
``reports/validation/821-atomic-config-binding/fail-first/``.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import doctor  # noqa: E402
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict, RuntimeRecoveryError  # noqa: E402
from agentmem_ref.state import sqlite_substrate  # noqa: E402
from agentmem_ref.state.sqlite_substrate import UngovernedDurableWrite  # noqa: E402

TENANT = "tenant:821"
SCOPE = "project:821"
REFERENCE = Path(__file__).resolve().parents[1]
FIXTURES = REFERENCE / "fixtures" / "821-legacy-stores"
LEGACY_TENANT = "tenant:821-legacy"
LEGACY_SCOPE = "project:821-legacy"
BINDING_TABLE = "runtime_configuration_binding"
CRASH = 77


def _db(root: Path) -> Path:
    return Path(root) / "agent-memory.sqlite3"


def _connect(root: Path) -> sqlite3.Connection:
    return sqlite3.connect(_db(root))


def _tables(root: Path, *, exclude: tuple[str, ...] = (), frozen: bool = False) -> dict[str, list]:
    """Every row of every table, through an independent connection (read-only for a fixture)."""

    connection = sqlite3.connect(f"file:{_db(root)}?mode=ro&immutable=1", uri=True) if frozen else _connect(root)
    with connection:
        names = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {
            name: sorted(map(tuple, connection.execute(f"SELECT * FROM {name}").fetchall()), key=repr)
            for name in names if name not in exclude
        }


def _state_generation(root: Path) -> int | None:
    with _connect(root) as connection:
        row = connection.execute(
            "SELECT json_extract(payload_json, '$.generation') FROM runtime_state WHERE singleton = 1").fetchone()
    return None if row is None else int(row[0])


def _row(root: Path) -> tuple[int, dict] | None:
    """The binding row (generation column, payload), or None if there is no table or no row."""

    with _connect(root) as connection:
        if connection.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (BINDING_TABLE,)).fetchone() is None:
            return None
        row = connection.execute(f"SELECT generation, payload_json FROM {BINDING_TABLE} WHERE singleton = 1").fetchone()
    return None if row is None else (int(row[0]), json.loads(row[1]))


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sealed(payload: dict) -> dict:
    """The payload with its record digest recomputed, as a self-consistent forgery would be."""

    material = {key: value for key, value in payload.items() if key != "record_digest"}
    return {**material, "record_digest": "sha256:" + hashlib.sha256(_canonical(material)).hexdigest()}


def _write_row(root: Path, generation: int, payload_json: str) -> None:
    with _connect(root) as connection:
        connection.execute(f"UPDATE {BINDING_TABLE} SET generation = ?, payload_json = ? WHERE singleton = 1",
                           (generation, payload_json))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


_CHILD = textwrap.dedent(
    """
    import os, sys
    sys.path.insert(0, sys.argv[1])
    from contextlib import contextmanager
    from agentmem_ref import AgentMemory
    from agentmem_ref.runtime import configured_restart as c
    from agentmem_ref.state import sqlite_substrate as s
    root, point, text = sys.argv[2], sys.argv[3], sys.argv[4]
    CRASH = %d

    def crash_inside_transaction_after(name):
        original = getattr(s.SQLiteTemporalGraph, name)
        def hook(self, *a, **k):
            original(self, *a, **k)
            os._exit(CRASH)
        setattr(s.SQLiteTemporalGraph, name, hook)

    def install():
        if point == "pre_commit":
            crash_inside_transaction_after("append_runtime_journal")
        elif point == "post_commit":
            original = s.SQLiteTemporalGraph.transaction
            @contextmanager
            def hook(self):
                with original(self):
                    yield
                os._exit(CRASH)
            s.SQLiteTemporalGraph.transaction = hook
        elif point == "mid_bind":
            if hasattr(s.SQLiteTemporalGraph, "write_runtime_configuration_binding"):
                crash_inside_transaction_after("write_runtime_configuration_binding")
            else:  # the file protocol: temp file written and fsynced, rename not done
                def hook(path, value):
                    with path.with_name(f".{path.name}.tmp").open("wb") as handle:
                        handle.write(c._canonical_bytes(value)); handle.flush(); os.fsync(handle.fileno())
                    os._exit(CRASH)
                c._atomic_json_write = hook

    opened = os.path.exists(os.path.join(root, "agent-memory.sqlite3"))
    if not opened:
        install()
    m = AgentMemory.open(root, tenant=%r, actor_id="agent:a", scope=%r, purpose="821")
    if opened:
        install()
        m.remember("memory:" + text, text)
    if point == "post_op":
        os._exit(CRASH)
    m.close()
    """
) % (CRASH, TENANT, SCOPE)


def _run_child(root: Path, point: str, text: str = "seed") -> int:
    done = subprocess.run([sys.executable, "-c", _CHILD, str(REFERENCE), str(root), point, text],
                          capture_output=True, text=True, timeout=120)
    if done.returncode not in (0, CRASH):
        raise AssertionError(f"child failed ({done.returncode}): {done.stderr[-2000:]}")
    return done.returncode


class _Store(unittest.TestCase):
    def setUp(self) -> None:
        self._folder = tempfile.TemporaryDirectory()
        self.root = Path(self._folder.name) / "store"

    def tearDown(self) -> None:
        self._folder.cleanup()

    def open(self, root: Path | None = None, *, tenant: str = TENANT, scope: str = SCOPE, actor: str = "agent:a") -> AgentMemory:
        memory = AgentMemory.open(root or self.root, tenant=tenant, actor_id=actor, scope=scope, purpose="821")
        self.addCleanup(memory.close)
        return memory

    def seeded(self) -> None:
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        memory.close()

    def assert_recovers_committed(self, expected_texts: set[str]) -> None:
        committed = _state_generation(self.root)
        memory = self.open(actor="agent:reader")
        durable = memory.runtime.durable_runtime
        self.assertEqual(durable.recovery_evidence.base_generation, committed)
        self.assertEqual(durable.base.recovery_evidence.generation, committed)
        with _connect(self.root) as connection:
            texts = {row[0] for row in connection.execute("SELECT fact_text FROM facts")}
        self.assertEqual(texts, expected_texts)
        memory.close()


class CrashWindow(_Store):
    """M1-M5: a real process killed at each boundary of one generation."""

    def seed_then_kill(self, point: str) -> int:
        self.assertEqual(_run_child(self.root, "none"), 0)
        self.assertEqual(_run_child(self.root, "none", "Thursday deploy"), 0)
        before = _state_generation(self.root)
        self.assertEqual(_run_child(self.root, point, "Lunch at noon"), CRASH)
        return before

    def test_m1_crash_before_commit_recovers_the_prior_generation(self):
        before = self.seed_then_kill("pre_commit")
        self.assertEqual(_state_generation(self.root), before)
        self.assert_recovers_committed({"Thursday deploy"})

    def test_m2_crash_immediately_after_commit_recovers_the_committed_generation(self):  # FAIL-FIRST
        before = self.seed_then_kill("post_commit")
        self.assertEqual(_state_generation(self.root), before + 1)
        bound = _row(self.root)
        self.assertIsNotNone(bound, "the committed generation carries its binding row")
        self.assertEqual(bound[0], before + 1)
        self.assert_recovers_committed({"Thursday deploy", "Lunch at noon"})

    def test_m3_crash_during_binding_publication_rolls_the_generation_back(self):  # FAIL-FIRST
        before = self.seed_then_kill("mid_bind")
        self.assertEqual(_state_generation(self.root), before)
        self.assertEqual(_row(self.root)[0], before)
        self.assert_recovers_committed({"Thursday deploy"})

    def test_m4_crash_after_the_operation_returned_recovers_it(self):
        before = self.seed_then_kill("post_op")
        self.assertEqual(_state_generation(self.root), before + 1)
        self.assert_recovers_committed({"Thursday deploy", "Lunch at noon"})

    def test_m5_crash_after_the_first_generation_commits_in_create(self):  # FAIL-FIRST
        self.assertEqual(_run_child(self.root, "post_commit"), CRASH)
        self.assertEqual(_state_generation(self.root), 1)
        self.assertFalse((self.root / "configuration-binding.json").exists())
        self.assertEqual(_row(self.root)[0], 1)
        self.assert_recovers_committed(set())

    def test_m18_kill_loop_always_reopens_to_the_last_committed_generation(self):  # FAIL-FIRST
        rng = random.Random(821)
        self.assertEqual(_run_child(self.root, "none"), 0)
        expected: set[str] = set()
        for cycle in range(10):
            point = rng.choice(["pre_commit", "post_commit", "mid_bind", "post_op", "none"])
            text = f"fact {cycle} {point}"
            with self.subTest(cycle=cycle, point=point):
                _run_child(self.root, point, text)
                if point in ("post_commit", "post_op", "none"):
                    expected.add(text)
                generation = _state_generation(self.root)
                self.assertEqual(_row(self.root)[0], generation)
                self.assert_recovers_committed(expected)


class BindingFailureRollsBack(_Store):
    """M6 / A9: a failure while publishing the binding publishes nothing at all."""

    def test_m6_exception_and_interrupt_in_binding_publication(self):  # FAIL-FIRST
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        for failure in (OSError("injected binding failure"), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                rows = _tables(self.root)
                governance = json.dumps(memory.runtime.adapter.export_checkpoint_state(), sort_keys=True, default=str)
                generation = memory.runtime.durable_runtime.base._observed_generation
                with mock.patch.object(sqlite_substrate.SQLiteTemporalGraph, "write_runtime_configuration_binding",
                                       side_effect=failure):
                    with self.assertRaises(type(failure)):
                        memory.remember("memory:y", "Lunch is at noon.")
                self.assertEqual(_tables(self.root), rows)
                self.assertEqual(json.dumps(memory.runtime.adapter.export_checkpoint_state(), sort_keys=True, default=str),
                                 governance)
                self.assertEqual(memory.runtime.durable_runtime.base._observed_generation, generation)
        self.assertTrue(memory.remember("memory:y", "Lunch is at noon.")["committed"])
        memory.close()
        self.assertEqual(len(self.open().recall("lunch noon")["returned"]), 1)

    def test_m6_a_failed_binding_keeps_no_uncommitted_visibility_snapshot(self):  # FAIL-FIRST
        memory = self.open()
        durable = memory.runtime.durable_runtime
        with mock.patch.object(sqlite_substrate.SQLiteTemporalGraph, "write_runtime_configuration_binding",
                               side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                durable.persist_visibility_snapshot("op:821", {"operation": {"required_projection_ids": []}})
        self.assertNotIn("op:821", durable.base.visibility_snapshots)
        memory.recall("anything")
        memory.close()
        self.assertNotIn("op:821", self.open().runtime.durable_runtime.base.visibility_snapshots)


class TamperedBindingsAreRefused(_Store):
    """M7-M11 / A2-A3: a present but unverifiable binding is refused, never repaired."""

    def refused(self, pattern: str) -> None:
        before = _tables(self.root)
        for attempt in (1, 2):  # refused again: the first refusal repaired nothing
            with self.subTest(attempt=attempt):
                with self.assertRaisesRegex(RuntimeRecoveryError, pattern):
                    AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")
                self.assertEqual(_tables(self.root), before)
        self.assertFalse((self.root / "configuration-binding.json").exists(), "no fallback file was written")

    def test_m7_tampered_rows(self):  # FAIL-FIRST
        self.seeded()
        generation, payload = _row(self.root)
        original = json.dumps(payload)
        cases = {
            "plan digest": (generation, _sealed({**payload, "plan_digest": "sha256:" + "1" * 64}),
                            "plan or qualification interpretation changed"),
            "configuration digest": (generation, _sealed({**payload, "configuration_digest": "sha256:" + "2" * 64}),
                                     "runtime configuration changed"),
            "persisted plan": (generation, _sealed({**payload, "plan": {**payload["plan"], "profile_id": "forged"}}),
                               "persisted runtime plan binding is corrupt"),
            "substrate digest": (generation, _sealed({**payload, "base": {**payload["base"], "substrate_digest": "sha256:" + "3" * 64}}),
                                 "does not match recovered base checkpoint: substrate_digest"),
            "journal tail": (generation, _sealed({**payload, "base": {**payload["base"], "journal_record_digest": "sha256:" + "4" * 64}}),
                             "does not match recovered base checkpoint: journal_record_digest"),
            "protocol": (generation, _sealed({**payload, "binding_protocol": "file_after_commit"}), "protocol"),
            "unsealed edit": (generation, {**payload, "plan_digest": "sha256:" + "5" * 64}, "corrupt"),
            "generation column": (generation + 1, payload, "corrupt"),
            "not json": (generation, "{not json", "corrupt"),
            "not an object": (generation, [1, 2], "corrupt"),
        }
        for name, (column, forged, pattern) in cases.items():
            with self.subTest(case=name):
                _write_row(self.root, column, forged if isinstance(forged, str) else json.dumps(forged))
                self.refused(pattern)
                _write_row(self.root, generation, original)
        self.open().close()  # the untouched row still recovers

    def test_m8_a_row_from_another_tenant_or_store_is_refused(self):  # FAIL-FIRST
        self.seeded()
        own = _row(self.root)
        other_root = Path(self._folder.name) / "other"
        for tenant, pattern in (("tenant:other", "another tenant"), (TENANT, "does not match recovered base checkpoint")):
            with self.subTest(tenant=tenant):
                if other_root.exists():
                    shutil.rmtree(other_root)
                other = self.open(other_root, tenant=tenant)
                other.remember("memory:x", "A different store entirely.")
                other.remember("memory:z", "Its generation matches ours.")
                other.close()
                foreign = _row(other_root)
                # align the generation so only identity, not position, differs
                _write_row(self.root, own[0], json.dumps(_sealed({**foreign[1], "base": {**foreign[1]["base"], "generation": own[0]}})))
                self.refused(pattern)
                _write_row(self.root, own[0], json.dumps(own[1]))

    def test_m9_a_replayed_older_row_is_refused(self):  # FAIL-FIRST
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        old = _row(self.root)
        memory.remember("memory:y", "Lunch is at noon.")
        memory.close()
        _write_row(self.root, old[0], json.dumps(old[1]))
        self.refused("stale or replayed")

    def test_m7_a_rebuilt_table_with_two_bindings_is_refused(self):  # added after the fail-first run
        self.seeded()
        generation, payload = _row(self.root)
        with _connect(self.root) as connection:
            connection.execute(f"DROP TABLE {BINDING_TABLE}")
            connection.execute(f"CREATE TABLE {BINDING_TABLE} (singleton INTEGER, generation INTEGER, payload_json TEXT)")
            for _ in range(2):
                connection.execute(f"INSERT INTO {BINDING_TABLE} VALUES (1, ?, ?)", (generation, json.dumps(payload)))
        self.refused("corrupt")

    def test_m10_a_deleted_row_is_refused(self):  # FAIL-FIRST (amended: M28)
        self.seeded()
        self.assertIsNotNone(_row(self.root))
        with _connect(self.root) as connection:
            connection.execute(f"DELETE FROM {BINDING_TABLE}")
        self.refused("SQLite configuration binding is corrupt: .* 0 bindings")

    def test_m10_a_dropped_table_is_refused(self):  # amendment 1, review N4
        self.seeded()
        with _connect(self.root) as connection:
            connection.execute(f"DROP TABLE {BINDING_TABLE}")
        self.refused("binding is missing although this store's generation witness")
        (self.root / "generation-witness.json").unlink()  # the residual: no witness, no table
        self.refused("required configuration-bound state missing")

    def test_m28_an_empty_table_never_reaches_a_verifying_legacy_file(self):  # amendment 1 (review F3)
        from agentmem_ref.runtime.configured_restart import ConfigBindingStore, binding_record

        self.seeded()
        _, payload = _row(self.root)
        memory = self.open()
        durable = memory.runtime.durable_runtime
        forged = binding_record(plan=durable.plan, base_evidence=durable.base.recovery_evidence)
        memory.close()
        self.assertEqual(forged["base"], {k: v for k, v in payload["base"].items() if k != "journal_record_digest"})
        ConfigBindingStore(self.root).path.write_bytes(_canonical(forged) + b"\n")
        with _connect(self.root) as connection:
            connection.execute(f"DELETE FROM {BINDING_TABLE}")
        before = _tables(self.root)
        with self.assertRaisesRegex(RuntimeRecoveryError, "corrupt"):
            AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")
        self.assertEqual(_tables(self.root), before)


class OwnershipAndStaleWriters(_Store):
    """M12-M13 / A5."""

    _OTHER = textwrap.dedent(
        """
        import sys
        sys.path.insert(0, sys.argv[1])
        from agentmem_ref import AgentMemory
        m = AgentMemory.open(sys.argv[2], tenant=sys.argv[3], actor_id="agent:b", scope=sys.argv[4], purpose="821")
        assert m.remember("memory:y", "Lunch is at noon.")["committed"]
        m.close()
        """
    )

    def test_m12_a_stale_handle_cannot_rebind_another_process_generation(self):  # FAIL-FIRST
        stale = self.open()
        stale.remember("memory:x", "The deploy window is Thursday.")
        subprocess.run([sys.executable, "-c", self._OTHER, str(REFERENCE), str(self.root), TENANT, SCOPE], check=True)
        published = _tables(self.root)
        self.assertEqual(_row(self.root)[0], _state_generation(self.root))
        with self.assertRaises(RuntimeCheckpointConflict):
            stale.recall("lunch")
        with self.assertRaises(RuntimeCheckpointConflict):
            stale.remember("memory:z", "Stale write.")
        self.assertEqual(_tables(self.root), published)
        stale.close()
        self.assertEqual(len(self.open(actor="agent:c").recall("lunch noon")["returned"]), 1)

    def test_m13_the_row_is_written_only_inside_the_owning_generation(self):  # FAIL-FIRST
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        substrate = memory.runtime.adapter.checkpoint_substrate()
        rows = _tables(self.root)
        with self.assertRaises(UngovernedDurableWrite):
            substrate.write_runtime_configuration_binding(99, {"forged": True})
        with self.assertRaises(UngovernedDurableWrite):
            with substrate.transaction():
                substrate.write_runtime_configuration_binding(99, {"forged": True})
        self.assertEqual(_tables(self.root), rows)
        self.assertTrue(memory.remember("memory:y", "Lunch is at noon.")["committed"])

    def test_a5_the_binder_refuses_a_row_that_does_not_bind_the_previous_generation(self):  # FAIL-FIRST
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        generation, payload = _row(self.root)
        _write_row(self.root, generation + 5, json.dumps(_sealed({**payload, "base": {**payload["base"], "generation": generation + 5}})))
        rows = _tables(self.root)
        with self.assertRaisesRegex(RuntimeCheckpointConflict, "configuration binding"):
            memory.remember("memory:y", "Lunch is at noon.")
        self.assertEqual(_tables(self.root), rows)


class LegacyStores(unittest.TestCase):
    """M14-M17, A4: byte-frozen stores written by the frozen #816 runtime (d2fc9782)."""

    def setUp(self) -> None:
        self._folder = tempfile.TemporaryDirectory()
        self.addCleanup(self._folder.cleanup)
        manifest = json.loads((FIXTURES / "MANIFEST.json").read_text())
        self.manifest = manifest
        for name, store in manifest["stores"].items():
            for file, digest in store["files"].items():
                self.assertEqual(_sha(FIXTURES / name / file), digest, f"fixture {name}/{file} changed")

    def copy(self, name: str) -> Path:
        root = Path(self._folder.name) / name
        shutil.copytree(FIXTURES / name, root)
        return root

    def open(self, root: Path) -> AgentMemory:
        memory = AgentMemory.open(root, tenant=LEGACY_TENANT, actor_id="agent:legacy", scope=LEGACY_SCOPE, purpose="821")
        self.addCleanup(memory.close)
        return memory

    def test_m14_a_coherent_legacy_store_migrates_inside_its_next_generation(self):  # FAIL-FIRST
        root = self.copy("coherent")
        legacy_file = _sha(root / "configuration-binding.json")
        memory = self.open(root)
        self.assertEqual(memory.runtime.durable_runtime.binding_scheme, "legacy_file")
        self.assertIsNone(_row(root), "recovery writes nothing")
        self.assertEqual(len(memory.recall("deploy window")["returned"]), 1)  # this publishes a generation
        generation = _state_generation(root)
        self.assertEqual(_row(root)[0], generation)
        self.assertEqual(memory.runtime.durable_runtime.binding_scheme, "sqlite_transaction")
        memory.close()
        self.assertEqual(_sha(root / "configuration-binding.json"), legacy_file, "the legacy file is never rewritten")
        reopened = self.open(root)
        self.assertEqual(reopened.runtime.durable_runtime.binding_scheme, "sqlite_transaction")
        self.assertEqual(len(reopened.recall("lunch noon")["returned"]), 1)

    def test_m11_a_migrated_store_refuses_without_its_row(self):  # FAIL-FIRST (renamed, amendment 1)
        root = self.copy("coherent")
        memory = self.open(root)
        memory.recall("deploy window")
        memory.close()
        with _connect(root) as connection:
            connection.execute(f"DELETE FROM {BINDING_TABLE}")
        # the table exists, so the row is required and the legacy file is not consulted (M28)
        with self.assertRaisesRegex(RuntimeRecoveryError, "SQLite configuration binding is corrupt"):
            self.open(root)
        with _connect(root) as connection:
            connection.execute(f"DROP TABLE {BINDING_TABLE}")
        # the witness of the migrating generation still requires the row (review N4)
        with self.assertRaisesRegex(RuntimeRecoveryError, "binding is missing although this store's generation witness"):
            self.open(root)
        (root / "generation-witness.json").unlink()
        # with the table and the witness gone (the residual of unkeyed local state) the legacy
        # file is reached, and it lags the committed generation
        with self.assertRaisesRegex(RuntimeRecoveryError, "does not match recovered base checkpoint: generation"):
            self.open(root)

    def test_a5_a_legacy_handle_binds_without_a_row_only_once(self):  # added after the fail-first run
        root = self.copy("coherent")
        memory = self.open(root)
        memory.recall("deploy window")  # generation 4 commits the first row
        with _connect(root) as connection:
            connection.execute(f"DROP TABLE {BINDING_TABLE}")
        rows = _tables(root)
        with self.assertRaisesRegex(RuntimeCheckpointConflict, "configuration binding for generation 4 is missing"):
            memory.recall("deploy window")
        self.assertEqual(_tables(root), rows)

    def test_m15_a_store_stranded_by_the_old_window_stays_refused(self):
        root = self.copy("stranded")
        self.assertEqual(self.manifest["stores"]["stranded"]["state_generation"], 3)
        self.assertEqual(self.manifest["stores"]["stranded"]["binding_file_generation"], 2)
        rows, legacy_file = _tables(root), _sha(root / "configuration-binding.json")
        for _ in (1, 2):
            with self.assertRaisesRegex(RuntimeRecoveryError, "does not match recovered base checkpoint: generation"):
                self.open(root)
        self.assertEqual(_tables(root), rows)
        self.assertEqual(_sha(root / "configuration-binding.json"), legacy_file)
        self.assertIsNone(_row(root))

    def test_m16_a_tampered_or_missing_legacy_file_stays_refused(self):
        for name, mutate, pattern in (
            ("configuration digest", lambda v: v.update(configuration_digest="sha256:" + "0" * 64), "runtime configuration changed"),
            ("base digest", lambda v: v["base"].update(substrate_digest="sha256:" + "0" * 64), "substrate_digest"),
            ("missing", None, "required configuration-bound state missing"),
        ):
            with self.subTest(case=name):
                root = self.copy("coherent")
                binding = root / "configuration-binding.json"
                if mutate is None:
                    binding.unlink()
                else:
                    value = json.loads(binding.read_text())
                    mutate(value)
                    binding.write_text(json.dumps(value))
                with self.assertRaisesRegex(RuntimeRecoveryError, pattern):
                    self.open(root)
                self.assertIsNone(_row(root))
                shutil.rmtree(root)

    def test_m17_a_changed_configuration_is_still_refused(self):
        for name in ("coherent",):
            root = self.copy(name)
            config = json.loads((root / "runtime-config.json").read_text())
            config["evidence"]["runtime_evidence_ref"] = "evidence://agent-memory/changed"
            (root / "runtime-config.json").write_text(json.dumps(config))
            rows = _tables(root)
            with self.assertRaises(RuntimeRecoveryError):
                self.open(root)
            self.assertEqual(_tables(root), rows)

    def test_a7_the_same_operations_publish_byte_identical_digests_and_journal(self):
        """A #821 runtime replaying the coherent fixture's writes publishes the same canonical,
        governance, runtime-state and journal rows as d2fc9782 did; only the binding moves."""

        root = Path(self._folder.name) / "replay"
        memory = AgentMemory.open(root, tenant=LEGACY_TENANT, actor_id="agent:legacy", scope=LEGACY_SCOPE,
                                  purpose="821 legacy fixture")
        memory.remember("memory:deploy", "The deploy window is Thursday.")
        memory.remember("memory:lunch", "Lunch is at noon.")
        memory.close()
        self.assertEqual(_tables(root, exclude=(BINDING_TABLE,)), _tables(FIXTURES / "coherent", frozen=True))
        self.assertFalse((root / "configuration-binding.json").exists())
        legacy = json.loads((FIXTURES / "coherent" / "configuration-binding.json").read_text())
        generation, row = _row(root)
        self.assertEqual(generation, legacy["base"]["generation"])
        for key in ("configuration_digest", "plan_digest", "plan", "required_projection_ids", "durability_profile"):
            self.assertEqual(row[key], legacy[key], key)
        self.assertEqual({k: v for k, v in row["base"].items() if k != "journal_record_digest"}, legacy["base"])


class CloseRecoveryAndDoctor(_Store):
    """M19-M20 / A6."""

    def test_m19_close_and_recovery_write_nothing(self):
        self.seeded()
        rows = _tables(self.root)
        files = sorted(p.name for p in self.root.iterdir() if not p.name.startswith("agent-memory.sqlite3-"))
        memory = self.open()
        memory.close()
        memory.close()
        self.assertEqual(_tables(self.root), rows)
        self.assertEqual(sorted(p.name for p in self.root.iterdir() if not p.name.startswith("agent-memory.sqlite3-")), files)

    def test_a_new_store_writes_no_binding_file(self):  # FAIL-FIRST
        self.seeded()
        self.assertFalse((self.root / "configuration-binding.json").exists())
        self.assertEqual(_row(self.root)[0], _state_generation(self.root))

    def test_m20_doctor_reports_the_in_transaction_binding(self):  # FAIL-FIRST
        self.seeded()
        report = doctor.diagnose(self.root / "runtime-config.json", state_dir=self.root)
        self.assertEqual(report["recovery"]["status"], "recovered")
        self.assertTrue(report["durable_state"]["configuration_binding_present"])
        self.assertEqual(report["durable_state"]["configuration_binding_scheme"], "sqlite_transaction")
        with _connect(self.root) as connection:
            connection.execute(f"DELETE FROM {BINDING_TABLE}")
        report = doctor.diagnose(self.root / "runtime-config.json", state_dir=self.root)
        self.assertEqual(report["recovery"]["status"], "failed_closed")



def _witness(root: Path) -> dict | None:
    path = Path(root) / "generation-witness.json"
    return json.loads(path.read_text()) if path.exists() else None


def _replace_database(root: Path, source: Path) -> None:
    for leftover in Path(root).glob("agent-memory.sqlite3*"):
        leftover.unlink()
    shutil.copy(source, _db(root))


class GenerationWitnessAmendment(_Store):
    """Amendment 1 (review F1, F2, F5, F6, F8b): M22-M27, M29, M30."""

    def snapshot_database(self) -> Path:
        copy = Path(self._folder.name) / f"snapshot-{_state_generation(self.root)}.sqlite3"
        shutil.copy(_db(self.root), copy)
        return copy

    def test_m22_a_lost_database_is_never_recreated(self):
        self.seeded()
        self.assertEqual(_witness(self.root)["generation"], _state_generation(self.root))
        for leftover in self.root.glob("agent-memory.sqlite3*"):
            leftover.unlink()
        with self.assertRaisesRegex(RuntimeRecoveryError, "generation witness exists without SQLite runtime database"):
            AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")
        self.assertFalse(_db(self.root).exists())
        from agentmem_ref.runtime.sqlite_runtime import SQLiteConfigBoundRestartRuntime

        with self.assertRaisesRegex(RuntimeRecoveryError, "generation witness exists"):
            SQLiteConfigBoundRestartRuntime.create(self.root, tenant=TENANT, plan=self._plan())
        self.assertFalse(_db(self.root).exists())
        report = doctor.diagnose(self.root / "runtime-config.json", state_dir=self.root)
        self.assertEqual(report["durable_state"]["status"], "incomplete")
        self.assertEqual(report["recovery"]["status"], "failed_closed")

    def _plan(self):
        from agentmem_ref.runtime.runtime_behavior import validate_runtime_behavior_contract

        return validate_runtime_behavior_contract(json.loads((self.root / "runtime-config.json").read_text()))

    def test_m23_a_database_rolled_back_to_an_older_copy_is_refused(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        memory.close()
        older = self.snapshot_database()
        memory = self.open()
        memory.remember("memory:y", "Lunch is at noon.")
        memory.close()
        _replace_database(self.root, older)
        rows = _tables(self.root)
        with self.assertRaisesRegex(RuntimeRecoveryError, "behind this store's generation witness"):
            AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")
        self.assertEqual(_tables(self.root), rows)

    def test_m24_another_store_database_is_refused(self):
        self.seeded()
        other_root = Path(self._folder.name) / "other"
        other = self.open(other_root)
        for index in range(3):
            other.remember(f"memory:{index}", f"Another store's fact {index}.")
        other.close()
        self.assertGreater(_state_generation(other_root), _witness(self.root)["generation"])
        _replace_database(self.root, _db(other_root))
        with self.assertRaisesRegex(RuntimeRecoveryError, "does not continue the history"):
            AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")

    def test_m25_a_lagging_witness_is_accepted(self):
        self.assertEqual(_run_child(self.root, "none"), 0)
        self.assertEqual(_run_child(self.root, "none", "Thursday deploy"), 0)
        before = _state_generation(self.root)
        self.assertEqual(_run_child(self.root, "post_commit", "Lunch at noon"), CRASH)
        self.assertEqual(_witness(self.root)["generation"], before)
        self.assertEqual(_state_generation(self.root), before + 1)
        self.assert_recovers_committed({"Thursday deploy", "Lunch at noon"})

    def test_m26_a_corrupt_witness_is_refused(self):
        self.seeded()
        for content in ("{not json", json.dumps({"schema": "other"}), json.dumps(
                {**_witness(self.root), "generation": "3"})):
            with self.subTest(content=content):
                (self.root / "generation-witness.json").write_text(content)
                with self.assertRaisesRegex(RuntimeRecoveryError, "generation witness is unreadable"):
                    AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")

    def test_m27_a_failed_witness_write_keeps_the_committed_generation(self):
        from agentmem_ref.runtime.sqlite_runtime import GenerationWitness

        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        durable = memory.runtime.durable_runtime
        before = _witness(self.root)
        with mock.patch.object(GenerationWitness, "record", side_effect=OSError("injected ENOSPC")):
            self.assertTrue(memory.remember("memory:y", "Lunch is at noon.")["committed"])
        self.assertFalse(durable.generation_witness_current)
        self.assertEqual(_witness(self.root), before)
        memory.recall("lunch")
        self.assertTrue(durable.generation_witness_current)
        self.assertEqual(_witness(self.root)["generation"], _state_generation(self.root))
        memory.close()
        self.assertEqual(len(self.open().recall("lunch noon")["returned"]), 1)

    def test_m29_a_row_rewritten_while_a_handle_is_open_is_refused(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        generation, payload = _row(self.root)
        forged = _sealed({**payload, "base": {**payload["base"], "substrate_digest": "sha256:" + "9" * 64}})
        _write_row(self.root, generation, json.dumps(forged))
        rows = _tables(self.root)
        with self.assertRaisesRegex(RuntimeCheckpointConflict, "changed under this handle.*substrate_digest"):
            memory.remember("memory:y", "Lunch is at noon.")
        self.assertEqual(_tables(self.root), rows)

    def test_m30_a_visibility_obligation_the_plan_does_not_require_rolls_back(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        base = memory.runtime.durable_runtime.base
        rows = _tables(self.root)
        with self.assertRaisesRegex(RuntimeRecoveryError, "not required by the recovered configuration"):
            base.persist_visibility_snapshot("op:foreign", {"operation": {"required_projection_ids": ["not-in-plan"]}})
        self.assertEqual(_tables(self.root), rows)
        self.assertNotIn("op:foreign", base.visibility_snapshots)
        memory.close()
        self.open().close()

    def test_n1_a_writer_committing_during_recovery_never_reads_as_a_rollback(self):
        """Review N1 (p13): a commit after the reader read the database. Read after it, the witness
        led the reader's database and the refusal told the operator to remove it. Read before it,
        the witness can only lag; what remains is the pre-existing F8a race (the binding is read
        outside the recovery snapshot), which refuses as stale and a reopen succeeds."""

        from agentmem_ref.runtime import sqlite_runtime

        self.seeded()
        writer = self.open(actor="agent:writer")
        original = sqlite_runtime.SQLiteRestartSafeRuntime.recover.__func__

        def recover_then_another_commit(cls, *args, **kwargs):
            base = original(cls, *args, **kwargs)
            writer.remember("memory:z", "Committed while the reader recovered.")
            return base

        with mock.patch.object(sqlite_runtime.SQLiteRestartSafeRuntime, "recover",
                               classmethod(recover_then_another_commit)):
            with self.assertRaises(RuntimeRecoveryError) as refused:
                AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:reader", scope=SCOPE, purpose="821")
        self.assertNotIn("witness", str(refused.exception))
        self.assertIn("stale or replayed", str(refused.exception))
        writer.close()
        self.open().close()

    def test_n2_a_failed_first_open_before_the_database_exists_leaves_nothing_refused(self):
        from agentmem_ref.state import sqlite_substrate as s

        with mock.patch.object(s.SQLiteTemporalGraph, "__init__", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")
        self.assertIsNone(_witness(self.root))
        self.open().close()

    def test_n3_an_unreadable_witness_is_refused_and_doctor_reports_it(self):
        self.seeded()
        witness = self.root / "generation-witness.json"
        witness.unlink()
        witness.mkdir()
        with self.assertRaisesRegex(RuntimeRecoveryError, "generation witness is unreadable"):
            AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")
        report = doctor.diagnose(self.root / "runtime-config.json", state_dir=self.root)
        self.assertEqual(report["recovery"]["status"], "failed_closed")

    def test_n3_an_interrupted_witness_write_reports_the_lag(self):
        from agentmem_ref.runtime.sqlite_runtime import GenerationWitness

        memory = self.open()
        with mock.patch.object(GenerationWitness, "record", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                memory.remember("memory:x", "The deploy window is Thursday.")
        self.assertFalse(memory.runtime.durable_runtime.generation_witness_current)

    def test_n5_the_refusal_names_the_deliberate_restore_step(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        memory.close()
        older = self.snapshot_database()
        memory = self.open()
        memory.remember("memory:y", "Lunch is at noon.")
        memory.close()
        _replace_database(self.root, older)
        with self.assertRaisesRegex(RuntimeRecoveryError, "remove generation-witness.json to accept it"):
            AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="821")
        (self.root / "generation-witness.json").unlink()  # the operator's deliberate restore
        self.assertEqual(len(self.open().recall("deploy window")["returned"]), 1)

    def test_f6_doctor_reports_an_unverified_row_on_failure(self):
        self.seeded()
        generation, payload = _row(self.root)
        _write_row(self.root, generation, json.dumps({**payload, "tenant": "forged"}))
        report = doctor.diagnose(self.root / "runtime-config.json", state_dir=self.root)
        self.assertEqual(report["recovery"]["status"], "failed_closed")
        self.assertTrue(report["durable_state"]["configuration_binding_present"])
        self.assertEqual(report["durable_state"]["configuration_binding_scheme"], "unverified")


# R-1 (independent integration review of d0d2a97c): two writer processes recording the witness at
# once. Faults are injected only at the OS boundary (open and rename of witness files), and the
# interleaving is forced with barrier files, not timing, so it is the same on every run.
_WITNESS_WRITER = textwrap.dedent(
    """
    import builtins, io, os, pathlib, sys, time
    sys.path.insert(0, sys.argv[1])
    from agentmem_ref import AgentMemory
    root, role, text, barrier = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
    CRASH = %d
    WITNESS = "generation-witness.json"

    def witness_temporary(path):
        name = os.path.basename(os.fspath(path))
        return name.startswith("." + WITNESS) and name.endswith(".tmp")

    def hold_rename_until_released():
        # A: its temporary is complete and fsynced; rename it only after B has run
        real = os.replace
        def replace(source, destination, *a, **k):
            if os.path.basename(os.fspath(destination)) == WITNESS:
                open(os.path.join(barrier, "a-holding"), "w").close()
                deadline = time.monotonic() + 60
                while not os.path.exists(os.path.join(barrier, "b-done")):
                    if time.monotonic() > deadline:
                        raise SystemExit("barrier timeout")
                    time.sleep(0.01)
            return real(source, destination, *a, **k)
        os.replace = replace

    def die_once_a_temporary_is_open_for_writing():
        # B: killed after opening its temporary for writing and before writing a byte
        # (equivalently, its write fails with ENOSPC)
        writing = os.O_WRONLY | os.O_RDWR
        real_os_open = os.open
        def os_open(path, flags, *a, **k):
            fd = real_os_open(path, flags, *a, **k)
            if flags & writing and witness_temporary(path):
                os._exit(CRASH)
            return fd
        os.open = os_open
        for owner, attribute in ((builtins, "open"), (io, "open"), (pathlib.Path, "open")):
            real = getattr(owner, attribute)
            def opened(*a, _real=real, **k):
                handle = _real(*a, **k)
                path = a[0] if a else k.get("file")
                mode = a[1] if len(a) > 1 else k.get("mode", "r")
                if any(m in mode for m in "wax+") and witness_temporary(path):
                    os._exit(CRASH)
                return handle
            setattr(owner, attribute, opened)

    memory = AgentMemory.open(root, tenant=%r, actor_id="agent:" + role, scope=%r, purpose="821")
    if role == "A":
        hold_rename_until_released()
    elif role == "B-killed":
        die_once_a_temporary_is_open_for_writing()
    memory.remember("memory:" + role, text)
    memory.close()
    """
) % (CRASH, TENANT, SCOPE)


class ConcurrentWitnessWriters(_Store):
    """R-1: the witness a writer publishes is only ever its own complete record."""

    def race(self, b_role: str) -> tuple[int, int]:
        barrier = Path(self._folder.name) / "barrier"
        barrier.mkdir()
        command = [sys.executable, "-c", _WITNESS_WRITER, str(REFERENCE), str(self.root)]
        a = subprocess.Popen(command + ["A", "Writer A committed this.", str(barrier)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 120
            while not (barrier / "a-holding").exists():
                if a.poll() is not None or time.monotonic() > deadline:
                    raise AssertionError(f"writer A never reached its rename: {a.communicate()[1][-2000:]}")
                time.sleep(0.01)
            b = subprocess.run(command + [b_role, "Writer B committed this.", str(barrier)],
                               capture_output=True, text=True, timeout=120)
        finally:
            (barrier / "b-done").touch()
            try:
                _, a_err = a.communicate(timeout=120)
            except subprocess.TimeoutExpired:
                a.kill()
                raise
        if a.returncode != 0:
            raise AssertionError(f"writer A failed ({a.returncode}): {a_err[-2000:]}")
        return a.returncode, b.returncode

    def test_r1_a_writer_killed_beside_another_never_publishes_an_empty_witness(self):  # FAIL-FIRST (R-1)
        self.seeded()
        _, b_code = self.race("B-killed")
        self.assertEqual(b_code, CRASH)
        # d0d2a97c: both writers used one temporary name, so A published the inode B had truncated
        self.assertNotEqual((self.root / "generation-witness.json").read_bytes(), b"", "an empty witness was published")
        self.assertLessEqual(_witness(self.root)["generation"], _state_generation(self.root))
        self.assert_recovers_committed(
            {"The deploy window is Thursday.", "Writer A committed this.", "Writer B committed this."})

    def test_r1_a_late_rename_lets_the_witness_lag_but_never_lead(self):
        """The documented residual: without a cross-process lock, A can rename its record after B
        recorded a newer generation, so the witness steps back. It still names a committed
        generation of this store's own history, so it can only lag; recovery accepts it."""

        self.seeded()
        _, b_code = self.race("B")
        self.assertEqual(b_code, 0)
        witness = _witness(self.root)
        committed = _state_generation(self.root)
        self.assertLess(witness["generation"], committed)  # A's older record landed last: a strict lag
        with _connect(self.root) as connection:
            journal = connection.execute(
                "SELECT payload_json FROM runtime_journal WHERE generation = ?", (witness["generation"],)).fetchone()
        self.assertEqual(json.loads(journal[0])["record_digest"], witness["journal_record_digest"])
        self.assert_recovers_committed(
            {"The deploy window is Thursday.", "Writer A committed this.", "Writer B committed this."})

    def test_r1_another_writer_temporary_is_never_opened_or_truncated(self):
        from agentmem_ref.runtime import sqlite_runtime

        self.seeded()
        taken = self.root / f".generation-witness.json.{os.getpid()}.{'0' * 16}.tmp"
        taken.write_bytes(b"another writer's half-written record")
        tokens = iter(["0" * 16, "1" * 16])
        memory = self.open()
        with mock.patch.object(sqlite_runtime.secrets, "token_hex", lambda _: next(tokens)):
            self.assertTrue(memory.remember("memory:y", "Lunch is at noon.")["committed"])
        self.assertEqual(taken.read_bytes(), b"another writer's half-written record")
        self.assertEqual(_witness(self.root)["generation"], _state_generation(self.root))
        self.assertEqual(sorted(p.name for p in self.root.glob(".generation-witness.json*")), [taken.name])

    def test_r1_a_failed_witness_write_removes_its_temporary(self):
        from agentmem_ref.runtime import sqlite_runtime

        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        before = _witness(self.root)
        real_replace = os.replace

        def replace(source, destination, *args, **kwargs):
            if Path(destination).name == "generation-witness.json":
                raise OSError(28, "injected ENOSPC")
            return real_replace(source, destination, *args, **kwargs)

        with mock.patch.object(sqlite_runtime.os, "replace", replace):
            self.assertTrue(memory.remember("memory:y", "Lunch is at noon.")["committed"])
        self.assertFalse(memory.runtime.durable_runtime.generation_witness_current)
        self.assertEqual(_witness(self.root), before)
        self.assertEqual(list(self.root.glob(".generation-witness.json*")), [])
        memory.close()
        self.assertEqual(len(self.open().recall("lunch noon")["returned"]), 1)

    def test_r1_a_temporary_that_cannot_be_wrapped_is_closed_and_removed(self):
        from agentmem_ref.runtime import sqlite_runtime

        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        before = _witness(self.root)
        with mock.patch.object(sqlite_runtime.os, "fdopen", side_effect=OSError(12, "injected")):
            self.assertTrue(memory.remember("memory:y", "Lunch is at noon.")["committed"])
        self.assertFalse(memory.runtime.durable_runtime.generation_witness_current)
        self.assertEqual(_witness(self.root), before)
        self.assertEqual(list(self.root.glob(".generation-witness.json*")), [])
        descriptors = Path("/proc/self/fd")
        if descriptors.is_dir():  # no descriptor still points at a witness temporary
            targets = []
            for entry in descriptors.iterdir():
                try:
                    targets.append(os.readlink(entry))
                except OSError:
                    pass
            self.assertEqual([t for t in targets if ".generation-witness.json." in t], [])

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_r1_the_witness_keeps_the_mode_open_wb_gave_it(self):
        previous = os.umask(0o027)
        try:
            self.seeded()
        finally:
            os.umask(previous)
        self.assertEqual((self.root / "generation-witness.json").stat().st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
