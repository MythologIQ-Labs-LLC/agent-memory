"""Immutable, verified Hindsight comparator embedding snapshot (#640 H1).

This is a benchmark-independent, explicit bootstrap step. Nothing downloads
during import, product startup, recall, or normal verification. Fetch is a
separate operator command and never runs as part of a scored lane.

The tokenizer/config artifact digests are captured exactly once from the
immutable model revision. The ONNX graph also has a precommitted SHA-256 that
must match before the snapshot can be frozen. Every opening re-verifies every
file, and a manifest cannot be silently regenerated over an existing snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "03415a4be176a1620747c692ed433219fabc3def"
ONNX_SHA256 = "ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665"
MODEL_DIMENSIONS = 384
SNAPSHOT_VERSION = "1.0.0"
MANIFEST_NAME = "snapshot-manifest.json"
ENV_DIR = "AGENT_MEMORY_HINDSIGHT_MODEL_DIR"
DEFAULT_DIR = Path.home() / ".cache" / "agent-memory" / "hindsight" / MODEL_REVISION
# Do not discover files from HEAD or wildcard-glob a mutable upstream branch.
ARTIFACTS = (
    "onnx/model.onnx",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "config.json",
)
MAX_ARTIFACT_BYTES = {
    "onnx/model.onnx": 800_000_000,
    "tokenizer.json": 12_000_000,
    "tokenizer_config.json": 2_000_000,
    "special_tokens_map.json": 2_000_000,
    "config.json": 2_000_000,
}


class SnapshotUnavailable(RuntimeError):
    """Pinned model snapshot is missing, drifted, or unverifiable."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_snapshot_dir(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    return Path(os.environ[ENV_DIR]) if os.environ.get(ENV_DIR) else DEFAULT_DIR


def artifact_url(relative: str) -> str:
    if relative not in ARTIFACTS:
        raise SnapshotUnavailable(f"unsupported Hindsight model artifact: {relative!r}")
    repo = urllib.parse.quote(MODEL_ID, safe="/")
    path = urllib.parse.quote(relative, safe="/")
    return f"https://huggingface.co/{repo}/resolve/{MODEL_REVISION}/{path}?download=true"


def _download_artifact(relative: str, dest: Path, limit: int) -> None:
    request = urllib.request.Request(
        artifact_url(relative), headers={"User-Agent": "agent-memory-hindsight-h1/1.0.0"}
    )
    written = 0
    with urllib.request.urlopen(request, timeout=60) as stream, dest.open("xb") as out:
        while block := stream.read(1 << 20):
            written += len(block)
            if written > limit:
                raise SnapshotUnavailable(f"artifact exceeds explicit size limit: {relative}")
            out.write(block)
    if not written:
        raise SnapshotUnavailable(f"empty model artifact: {relative}")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _assert_safe_root(root: Path) -> None:
    if root.is_symlink():
        raise SnapshotUnavailable("model snapshot root cannot be a symbolic link")


def verify_snapshot(root: Path) -> dict[str, Any]:
    """Validate identity, graph pin and each downloaded file before use."""

    _assert_safe_root(root)
    manifest_path = root / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise SnapshotUnavailable("snapshot manifest missing or symbolic")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotUnavailable("snapshot manifest unreadable") from exc

    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "model_id", "model_revision", "dimensions", "artifacts"
    }:
        raise SnapshotUnavailable("snapshot manifest shape changed")
    if (manifest["schema_version"] != SNAPSHOT_VERSION
            or manifest["model_id"] != MODEL_ID
            or manifest["model_revision"] != MODEL_REVISION
            or manifest["dimensions"] != MODEL_DIMENSIONS):
        raise SnapshotUnavailable("snapshot revision or shape drift")
    files = manifest["artifacts"]
    if not isinstance(files, dict) or set(files) != set(ARTIFACTS):
        raise SnapshotUnavailable("snapshot artifact set changed")

    for relative in ARTIFACTS:
        record = files[relative]
        if not isinstance(record, dict) or set(record) != {"sha256", "bytes"}:
            raise SnapshotUnavailable(f"snapshot file record malformed: {relative}")
        digest, size = record["sha256"], record["bytes"]
        if not (isinstance(digest, str) and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest)
                and type(size) is int and 0 < size <= MAX_ARTIFACT_BYTES[relative]):
            raise SnapshotUnavailable(f"invalid snapshot file identity: {relative}")
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise SnapshotUnavailable(f"missing or symbolic snapshot artifact: {relative}")
        if path.stat().st_size != size or _sha256_file(path) != digest:
            raise SnapshotUnavailable(f"snapshot file drift: {relative}")
    if files["onnx/model.onnx"]["sha256"] != ONNX_SHA256:
        raise SnapshotUnavailable("ONNX model violates immutable precommitted SHA-256")
    return manifest


def snapshot_identity(root: Path) -> dict[str, Any]:
    manifest = verify_snapshot(root)
    return {
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "dimensions": MODEL_DIMENSIONS,
        "manifest_sha256": hashlib.sha256(_canonical(manifest)).hexdigest(),
        "artifacts": manifest["artifacts"],
    }


def fetch_snapshot(
    root: Path,
    *,
    download: Callable[[str, Path, int], None] = _download_artifact,
) -> dict[str, Any]:
    """One explicit, atomic immutable-snapshot download. Never replace existing bytes."""

    _assert_safe_root(root)
    if root.exists():
        # Existing snapshots must verify. Never repair or re-download after
        # discovery of a mismatch, as that could change a scored identity.
        return snapshot_identity(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    if root.parent.is_symlink():
        raise SnapshotUnavailable("model snapshot parent cannot be a symbolic link")

    with tempfile.TemporaryDirectory(prefix="hindsight-staging-", dir=root.parent) as tmp:
        staging = Path(tmp)
        artifact_records: dict[str, dict[str, int | str]] = {}
        for relative in ARTIFACTS:
            dest = staging / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            download(relative, dest, MAX_ARTIFACT_BYTES[relative])
            if dest.is_symlink() or not dest.is_file():
                raise SnapshotUnavailable(f"downloaded artifact is missing or symbolic: {relative}")
            size = dest.stat().st_size
            if not 0 < size <= MAX_ARTIFACT_BYTES[relative]:
                raise SnapshotUnavailable(f"invalid artifact size: {relative}")
            digest = _sha256_file(dest)
            if relative == "onnx/model.onnx" and digest != ONNX_SHA256:
                raise SnapshotUnavailable("downloaded ONNX graph digest differs from frozen pin")
            artifact_records[relative] = {"sha256": digest, "bytes": size}

        manifest = {
            "schema_version": SNAPSHOT_VERSION,
            "model_id": MODEL_ID,
            "model_revision": MODEL_REVISION,
            "dimensions": MODEL_DIMENSIONS,
            "artifacts": artifact_records,
        }
        (staging / MANIFEST_NAME).write_bytes(_canonical(manifest) + b"\n")
        verify_snapshot(staging)
        # Refuse races/overwrites even when a second process populated root.
        if root.exists() or root.is_symlink():
            raise SnapshotUnavailable("snapshot target appeared during bootstrap")
        staging.rename(root)
    return snapshot_identity(root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("fetch", "verify", "identity"))
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args(argv)
    root = resolve_snapshot_dir(args.model_dir)
    if args.command == "fetch":
        identity = fetch_snapshot(root)
    else:
        identity = snapshot_identity(root)
    print(json.dumps(identity, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
