"""Per-user durable Agent Memory stores behind the AML Add/Search contract.

Isolation: every AML ``user_id`` gets its own Agent Memory runtime root (its own SQLite
database) under ``<data>/users/<sha256(user_id)>``. Search opens only that root, so a query
cannot reach another user's memory by construction, not by a filter.

Durability and idempotency: each user root also holds ``aml-ledger.sqlite3``, keyed by
``request_id``, recording the payload digest and, per message, the Agent Memory fact it
became. An Add marks its request pending in the ledger before writing anything, records each
fact as it commits, and marks the request committed last, then returns HTTP 200. A replay
of a committed request returns the same response without writing; a different payload under
the same ``(request_id, user_id)`` is a conflict; a replay of a request interrupted by a
crash resumes it, adopting any fact the runtime committed before the ledger recorded it
(``history(target_reference)``), so no message is stored twice.

Memory content is the message text, prefixed with its timestamp (when given) and role, and
is written through the public ``AgentMemory.remember`` path; Search is one
``AgentMemory.recall(query, budget=top_k)`` and returns the runtime's ranked ``returned``
prefix in order. Nothing here re-ranks, filters or truncates beyond the runtime's budget.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from agentmem_ref import AgentMemory

TENANT = "tenant:aml-cycle2"
ACTOR = "agent:aml-cycle2"
PURPOSE = "AML Cycle 2 evaluation memory"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    request_id TEXT PRIMARY KEY,
    payload_sha256 TEXT NOT NULL,
    session_id TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'committed')),
    received_at TEXT NOT NULL,
    committed_at TEXT
);
CREATE TABLE IF NOT EXISTS memories (
    fact_uuid TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests(request_id),
    message_index INTEGER NOT NULL,
    session_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (request_id, message_index)
);
"""


class IdempotencyConflict(Exception):
    """The request_id was already used for this user with a different payload."""


class WriteRefused(RuntimeError):
    """Agent Memory refused to commit a message."""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_from_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def user_key(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()


def memory_text(message: dict) -> str:
    prefix = f"[{_iso_from_ms(message['timestamp'])}] " if message.get("timestamp") is not None else ""
    return f"{prefix}{message['role']}: {message['content']}"


def target_reference(request_id: str, index: int) -> str:
    return "aml:msg:" + hashlib.sha256(f"{request_id}\x00{index}".encode("utf-8")).hexdigest()


class UserMemory:
    """One user's runtime handle and ledger; every operation holds ``self.lock``."""

    def __init__(self, root: Path, key: str) -> None:
        self.root = root
        self.key = key
        self.lock = threading.Lock()
        self._memory: AgentMemory | None = None
        self._ledger: sqlite3.Connection | None = None

    @property
    def is_open(self) -> bool:
        return self._memory is not None

    def _open(self) -> tuple[AgentMemory, sqlite3.Connection]:
        if self._memory is None:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            ledger = sqlite3.connect(self.root / "aml-ledger.sqlite3", check_same_thread=False, isolation_level=None)
            ledger.execute("PRAGMA journal_mode=WAL")
            ledger.execute("PRAGMA synchronous=FULL")
            ledger.execute("PRAGMA foreign_keys=ON")
            ledger.executescript(_SCHEMA)
            self._memory = AgentMemory.open(
                self.root / "runtime",
                tenant=TENANT,
                actor_id=ACTOR,
                scope="aml:user:" + self.key[:32],
                purpose=PURPOSE,
            )
            self._ledger = ledger
        assert self._ledger is not None
        return self._memory, self._ledger

    def close(self) -> None:
        if self._memory is not None:
            self._memory.close()
            self._memory = None
        if self._ledger is not None:
            self._ledger.close()
            self._ledger = None

    def add(self, add: dict, digest: str) -> bool:
        """Store one Add; return True when it was a replay of a committed request."""

        memory, ledger = self._open()
        row = ledger.execute(
            "SELECT payload_sha256, status FROM requests WHERE request_id = ?", (add["request_id"],)
        ).fetchone()
        resuming = False
        if row is not None:
            if row[0] != digest:
                raise IdempotencyConflict(add["request_id"])
            if row[1] == "committed":
                return True
            resuming = True
        else:
            ledger.execute(
                "INSERT INTO requests (request_id, payload_sha256, session_id, message_count, status, received_at)"
                " VALUES (?, ?, ?, ?, 'pending', ?)",
                (add["request_id"], digest, add["session_id"], len(add["messages"]), _now()),
            )
        for index, message in enumerate(add["messages"]):
            if resuming and ledger.execute(
                "SELECT 1 FROM memories WHERE request_id = ? AND message_index = ?", (add["request_id"], index)
            ).fetchone():
                continue
            reference = target_reference(add["request_id"], index)
            text = memory_text(message)
            fact_uuid = None
            if resuming:
                fact_uuid = memory.history(reference)["history"]["current_fact_uuid"]
            if fact_uuid is None:
                outcome = memory.remember(
                    reference,
                    text,
                    observed_at=None if message["timestamp"] is None else _iso_from_ms(message["timestamp"]),
                )
                if not outcome.get("committed") or not outcome.get("fact_uuid"):
                    raise WriteRefused(str(outcome.get("refusal") or outcome.get("outcome")))
                fact_uuid = str(outcome["fact_uuid"])
            created = _iso_from_ms(message["timestamp"]) if message["timestamp"] is not None else _now()
            ledger.execute(
                "INSERT INTO memories (fact_uuid, request_id, message_index, session_id, content, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (fact_uuid, add["request_id"], index, add["session_id"], text, created),
            )
        ledger.execute(
            "UPDATE requests SET status = 'committed', committed_at = ? WHERE request_id = ?",
            (_now(), add["request_id"]),
        )
        return False

    def search(self, query: str, top_k: int) -> list[dict]:
        if top_k == 0:
            return []
        memory, ledger = self._open()
        outcome = memory.recall(query, budget=top_k)
        items: list[dict] = []
        for fact_uuid in [str(value) for value in outcome.get("returned") or []][:top_k]:
            row = ledger.execute("SELECT content, created_at FROM memories WHERE fact_uuid = ?", (fact_uuid,)).fetchone()
            if row is None:
                # A fact the ledger never recorded belongs to an Add that has not returned 200;
                # it is not yet part of this user's acknowledged memory.
                continue
            rank = len(items) + 1
            items.append({"id": fact_uuid, "content": row[0], "score": round(1.0 / rank, 6), "created_at": row[1]})
        return items


class MemoryStore:
    """All users' stores; at most ``max_open`` runtime handles stay open (LRU).

    Runtime work is CPU-bound Python, so ``compute_slots`` (default 1) bounds how many
    operations run at once; further requests queue instead of thrashing the GIL. Measured
    on 4 vCPU, 8 users x 300 messages: 8 interleaved threads took 3x longer to Add and 9x
    longer to Search than the same work serialized. Lock order is always user, then compute.
    """

    def __init__(self, data_dir: str | Path, *, max_open: int = 64, compute_slots: int = 1) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.max_open = max(1, int(max_open))
        self._compute = threading.BoundedSemaphore(max(1, int(compute_slots)))
        self._guard = threading.Lock()
        self._users: dict[str, UserMemory] = {}
        self._open_order: OrderedDict[str, None] = OrderedDict()

    def _user_root(self, key: str) -> Path:
        return self.data_dir / "users" / key[:2] / key

    def _user(self, user_id: str, *, create: bool) -> UserMemory | None:
        key = user_key(user_id)
        with self._guard:
            user = self._users.get(key)
            if user is None:
                root = self._user_root(key)
                if not create and not root.exists():
                    return None
                user = self._users[key] = UserMemory(root, key)
            return user

    def _touch(self, user: UserMemory) -> None:
        with self._guard:
            self._open_order[user.key] = None
            self._open_order.move_to_end(user.key)
            evict = [key for key in self._open_order if key != user.key][: max(0, len(self._open_order) - self.max_open)]
            for key in evict:
                self._open_order.pop(key, None)
        for key in evict:
            victim = self._users[key]
            with victim.lock:
                victim.close()

    def add(self, add: dict, digest: str) -> bool:
        user = self._user(add["user_id"], create=True)
        assert user is not None
        with user.lock, self._compute:
            replayed = user.add(add, digest)
        self._touch(user)
        return replayed

    def search(self, user_id: str, query: str, top_k: int) -> list[dict]:
        user = self._user(user_id, create=False)
        if user is None:
            return []
        with user.lock, self._compute:
            items = user.search(query, top_k)
        self._touch(user)
        return items

    def close(self) -> None:
        with self._guard:
            users = list(self._users.values())
            self._open_order.clear()
        for user in users:
            with user.lock:
                user.close()
