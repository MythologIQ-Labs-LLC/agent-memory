"""Example v7 deployment-host gate, separate from the protected runtime.

Not part of the accepted AgentMemory API. A real host must authenticate and bind
the principal before constructing HostIdentity, provision stores under its own
trusted OS account, keep the enrollment registry private, and serialize creation.
A standalone example is NOT evidence that a consumer has adopted the policy.

The v7 default facade permits operational access to legacy stores. Status
'fresh' alone does not prove a store was created after the #809 repair, so
the host must also possess its own independent first-provisioning receipt.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Iterator

from agentmem_ref import AgentMemory

ENROLLMENT_SCHEMA = "v7-host-fresh-enrollment/1"


class HostAdmissionRefused(RuntimeError):
    """Store or host authority was not qualified for this restricted profile."""


@dataclass(frozen=True)
class HostIdentity:
    """Claims supplied by an authenticated embedding host, never request data."""

    tenant: str
    actor_id: str
    scope: str
    purpose: str = "qualified v7 local consumer"

    def __post_init__(self) -> None:
        if not all(
            isinstance(v, str) and v.strip()
            for v in (self.tenant, self.actor_id, self.scope, self.purpose)
        ):
            raise HostAdmissionRefused("host identity and scope must be nonempty")


def _trusted_registry(registry: str | Path) -> Path:
    # This profile is not qualified on Windows; do not silently assume the
    # meaning of Windows ACLs from POSIX uid and mode checks.
    if os.name != "posix":
        raise HostAdmissionRefused("host enrollment not qualified on this OS")
    raw = Path(registry).expanduser().absolute()
    if raw.is_symlink():
        raise HostAdmissionRefused("enrollment registry cannot be a symlink")
    try:
        path = raw.resolve(strict=True)
        info = path.stat()
    except OSError as exc:
        raise HostAdmissionRefused("enrollment registry is unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise HostAdmissionRefused("enrollment registry must be host-owned and private (0700)")
    return path


def _root_path(root: str | Path, registry: Path) -> Path:
    raw = Path(root).expanduser().absolute()
    if raw.is_symlink():
        raise HostAdmissionRefused("state root cannot be a symlink")
    path = raw.resolve(strict=False)
    if path == registry or registry in path.parents or path in registry.parents:
        raise HostAdmissionRefused("host enrollment and runtime state must be separate")
    return path


def _state_identity(root: Path) -> tuple[int, int]:
    if root.is_symlink():
        raise HostAdmissionRefused("state root was replaced by a symlink")
    try:
        info = root.stat()
    except OSError as exc:
        raise HostAdmissionRefused("registered state root is missing") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise HostAdmissionRefused("state root must be a private host-owned directory")
    return info.st_dev, info.st_ino


def _receipt_path(registry: Path, root: Path) -> Path:
    name = hashlib.sha256(os.fsencode(str(root))).hexdigest()
    return registry / (name + ".json")


def _fresh_only(memory: AgentMemory) -> None:
    posture = memory.legacy_upgrade_status()
    if (
        not isinstance(posture, dict)
        or posture.get("status") != "fresh"
        or type(posture.get("legacy_facts")) is not int
        or posture["legacy_facts"] != 0
        or posture.get("record") is not None
    ):
        raise HostAdmissionRefused("v7 consumer requires an unupgraded, zero-legacy fresh store")


def provision_new_root(
    root: str | Path, *, registry: str | Path, identity: HostIdentity,
) -> Path:
    """Enroll only a root the trusted host creates from absence.

    Never retrofit a receipt onto an existing store. Failed opens or incomplete
    generation commits leave no receipt: inspect and handle the orphan manually.
    """
    host_registry = _trusted_registry(registry)
    path = _root_path(root, host_registry)
    receipt_path = _receipt_path(host_registry, path)
    if receipt_path.exists() or receipt_path.is_symlink():
        raise HostAdmissionRefused("root already has an enrollment or conflicting marker")
    if path.exists() or path.is_symlink():
        raise HostAdmissionRefused("existing roots cannot be enrolled as fresh")
    parent = path.parent
    try:
        parent_info = parent.stat()
    except OSError as exc:
        raise HostAdmissionRefused("state parent is unavailable") from exc
    if (
        not stat.S_ISDIR(parent_info.st_mode)
        or parent_info.st_uid != os.getuid()
        or parent_info.st_mode & 0o022
    ):
        raise HostAdmissionRefused("state parent must be trusted and not group/world writable")
    path.mkdir(mode=0o700, exist_ok=False)
    with AgentMemory.open(
        path, tenant=identity.tenant, actor_id=identity.actor_id,
        scope=identity.scope, purpose=identity.purpose,
    ) as memory:
        _fresh_only(memory)
    device, inode = _state_identity(path)
    receipt = {
        "schema": ENROLLMENT_SCHEMA,
        "root": str(path),
        "device": device,
        "inode": inode,
        "tenant": identity.tenant,
        "scope": identity.scope,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(receipt_path, flags, 0o600)
    except FileExistsError as exc:
        raise HostAdmissionRefused("host enrollment already exists") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write((json.dumps(receipt, sort_keys=True) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        receipt_path.unlink(missing_ok=True)
        raise
    return receipt_path


@contextmanager
def open_registered_root(
    root: str | Path, *, registry: str | Path, identity: HostIdentity,
) -> Iterator[AgentMemory]:
    """No operational handle leaves this host boundary without both proofs."""
    host_registry = _trusted_registry(registry)
    path = _root_path(root, host_registry)
    device, inode = _state_identity(path)
    receipt_path = _receipt_path(host_registry, path)
    if receipt_path.is_symlink():
        raise HostAdmissionRefused("enrollment receipt cannot be a symlink")
    try:
        record = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HostAdmissionRefused("host provisioning receipt is missing or invalid") from exc
    if (
        not isinstance(record, dict)
        or record.get("schema") != ENROLLMENT_SCHEMA
        or record.get("root") != str(path)
        or type(record.get("device")) is not int
        or type(record.get("inode")) is not int
        or (record["device"], record["inode"]) != (device, inode)
        or record.get("tenant") != identity.tenant
        or record.get("scope") != identity.scope
    ):
        raise HostAdmissionRefused("host enrollment does not match root and authenticated scope")
    memory = AgentMemory.open(
        path, tenant=identity.tenant, actor_id=identity.actor_id,
        scope=identity.scope, purpose=identity.purpose,
    )
    try:
        _fresh_only(memory)
        if _state_identity(path) != (device, inode):
            raise HostAdmissionRefused("state root changed during activation")
        yield memory
    finally:
        memory.close()
