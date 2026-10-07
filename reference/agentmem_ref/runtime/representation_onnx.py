"""Pinned local ONNX sentence-embedding provider for the semantic vector route (#669).

Owner ruling ``decision-embedding-dependency``: a production local representation
provider, pinned and versioned, behind the existing ``VectorRepresentationProvider``
abstraction, shipped as the optional extra ``semantic`` rather than a base dependency.

Model: ``sentence-transformers/multi-qa-MiniLM-L6-cos-v1`` at revision ``b207367``.
This is the same model and revision the same-harness Mem0 row uses. Every model file
is pinned by sha256 and re-verified whenever a provider is constructed. The pooling
(mean over the attention mask) and the L2 normalization are asserted from the pinned
``modules.json`` and ``1_Pooling/config.json``. Truncation is set to the pinned
``sentence_bert_config.json`` ``max_seq_length`` (512), overriding the tokenizer
file's own 250. Output vectors are canonicalised to float32.

Determinism: one ONNX Runtime CPU session with one intra-op and one inter-op thread
and basic graph optimization. The ``config_digest`` binds every file digest, every
numerics setting and the ``onnxruntime``, ``tokenizers`` and ``numpy`` versions, so
a numerics-relevant change is a new representation identity rather than silent
drift. Bit-identity is claimed per library versions and CPU instruction set.

No network I/O happens on open, recall or restart. ``fetch`` is an explicit command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .representation_cache import float32_canonical
from .vector_retrieval import VectorRepresentationSpec

MODEL_ID = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
MODEL_REVISION = "b207367332321f8e44f96e224ef15bc607f4dbf0"
REPRESENTATION_REF = f"{MODEL_ID}@{MODEL_REVISION[:7]}"
REPRESENTATION_VERSION = "onnx-mean-l2-f32/1.0.0"
DIMENSIONS = 384
MAX_SEQ_LENGTH = 512
ENV_DIR = "AGENT_MEMORY_REPRESENTATION_DIR"
DEFAULT_DIR = Path.home() / ".cache" / "agent-memory" / "representations" / "multi-qa-MiniLM-L6-cos-v1-b207367"

# path -> (sha256, size in bytes)
PINNED_FILES: dict[str, tuple[str, int]] = {
    "onnx/model.onnx": ("826501e8460f6e1a83fa30a9b173f051100abda5559e1352efc0e3fe3136afc2", 90405214),
    "tokenizer.json": ("7fa9272f7ef1ebd1666bb3bfd9d4707660ff0076ca9d1671cd9a9c6e18e03331", 466247),
    "config.json": ("953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41", 612),
    "modules.json": ("84e40c8e006c9b1d6c122e02cba9b02458120b5fb0c87b746c41e0207cf642cf", None),
    "1_Pooling/config.json": ("4be450dde3b0273bb9787637cfbd28fe04a7ba6ab9d36ac48e92b11e350ffc23", None),
    "sentence_bert_config.json": ("ec8e29d6dcb61b611b7d3fdd2982c4524e6ad985959fa7194eacfb655a8d0d51", None),
}
NUMERICS = {
    "pooling": "mean_over_attention_mask",
    "normalize": "l2",
    "truncation_max_length": MAX_SEQ_LENGTH,
    "padding": "none_single_text",
    "graph_optimization_level": "ORT_ENABLE_BASIC",
    "intra_op_num_threads": 1,
    "inter_op_num_threads": 1,
    "execution_provider": "CPUExecutionProvider",
    "output_canonicalisation": "float32",
}
_MAX_DOWNLOAD_OVERHEAD = 1.01
_SMALL_FILE_CAP = 1_048_576


class RepresentationUnavailable(RuntimeError):
    """The optional extra or the pinned, verified model files are not available."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_model_dir(model_dir: str | Path | None = None) -> Path:
    if model_dir is not None:
        return Path(model_dir)
    env = os.environ.get(ENV_DIR)
    return Path(env) if env else DEFAULT_DIR


def verify_model_dir(model_dir: Path) -> dict[str, str]:
    """Every pinned file present, a regular file, and matching its digest; raises otherwise."""

    observed: dict[str, str] = {}
    for relative, (expected, _size) in PINNED_FILES.items():
        path = model_dir / relative
        if path.is_symlink() or not path.is_file():
            raise RepresentationUnavailable(f"model file missing or not a regular file: {path}")
        digest = _sha256_file(path)
        if digest != expected:
            raise RepresentationUnavailable(f"model file digest mismatch for {relative}: {digest}")
        observed[relative] = digest
    modules = json.loads((model_dir / "modules.json").read_text(encoding="utf-8"))
    kinds = [item.get("type") for item in modules]
    pooling = json.loads((model_dir / "1_Pooling" / "config.json").read_text(encoding="utf-8"))
    sbert = json.loads((model_dir / "sentence_bert_config.json").read_text(encoding="utf-8"))
    if (kinds != ["sentence_transformers.models.Transformer", "sentence_transformers.models.Pooling",
                  "sentence_transformers.models.Normalize"]
            or not pooling.get("pooling_mode_mean_tokens")
            or pooling.get("word_embedding_dimension") != DIMENSIONS
            or sbert.get("max_seq_length") != MAX_SEQ_LENGTH):
        raise RepresentationUnavailable("pinned model configuration does not assert mean pooling + normalize at 384/512")
    return observed


def _library_versions() -> dict[str, str]:
    from importlib import metadata

    versions = {}
    for name in ("onnxruntime", "tokenizers", "numpy"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError as exc:
            raise RepresentationUnavailable(f"optional extra 'semantic' is not installed: {name}") from exc
    return versions


def config_digest(versions: dict[str, str]) -> str:
    material = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "representation_version": REPRESENTATION_VERSION,
        "files": {path: digest for path, (digest, _size) in sorted(PINNED_FILES.items())},
        "numerics": NUMERICS,
        "dimensions": DIMENSIONS,
        "libraries": versions,
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _Session:
    session: Any
    tokenizer: Any
    input_names: tuple[str, ...]
    numpy: Any


class OnnxSentenceEmbeddingProvider:
    """``VectorRepresentationProvider`` over the pinned ONNX export; similarity is evidence only."""

    def __init__(self, model_dir: str | Path | None = None) -> None:
        directory = resolve_model_dir(model_dir)
        versions = _library_versions()
        verify_model_dir(directory)
        try:
            import numpy
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as exc:  # pragma: no cover - guarded by _library_versions
            raise RepresentationUnavailable("optional extra 'semantic' is not installed") from exc
        tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        tokenizer.enable_truncation(max_length=MAX_SEQ_LENGTH)
        tokenizer.no_padding()
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_BASIC
        session = onnxruntime.InferenceSession(
            str(directory / "onnx" / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )
        self._state = _Session(session, tokenizer, tuple(item.name for item in session.get_inputs()), numpy)
        self.model_dir = directory
        self.library_versions = versions
        self._spec = VectorRepresentationSpec(
            representation_ref=REPRESENTATION_REF,
            representation_version=REPRESENTATION_VERSION,
            config_digest=config_digest(versions),
            dimensions=DIMENSIONS,
            deterministic_rebuild=True,
        )

    @property
    def spec(self) -> VectorRepresentationSpec:
        return self._spec

    def embed(self, text: str) -> tuple[float, ...]:
        np = self._state.numpy
        encoding = self._state.tokenizer.encode(text)
        ids = np.asarray([encoding.ids], dtype=np.int64)
        mask = np.asarray([encoding.attention_mask], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        if "token_type_ids" in self._state.input_names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        hidden = self._state.session.run(None, feeds)[0]
        weights = mask[..., None].astype(hidden.dtype)
        pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
        norm = np.linalg.norm(pooled, axis=1, keepdims=True)
        normalized = pooled / np.clip(norm, 1e-12, None)
        return float32_canonical(normalized[0].tolist())


# Explicit acquisition --------------------------------------------------------------


def fetch(target: Path) -> dict[str, str]:
    """Download exactly the pinned files at the pinned revision; verify before rename."""

    if target.is_symlink():
        raise RepresentationUnavailable(f"refusing a symlinked target directory: {target}")
    target.mkdir(parents=True, exist_ok=True)
    fetched = {}
    for relative, (expected, size) in PINNED_FILES.items():
        destination = target / relative
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            raise RepresentationUnavailable(f"refusing a non-regular destination: {destination}")
        if destination.is_file() and _sha256_file(destination) == expected:
            fetched[relative] = "present"
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        cap = int(size * _MAX_DOWNLOAD_OVERHEAD) if size else _SMALL_FILE_CAP
        url = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{relative}"
        handle, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".fetch-")
        try:
            digest, received = hashlib.sha256(), 0
            with os.fdopen(handle, "wb") as out, urllib.request.urlopen(url, timeout=120) as response:
                for chunk in iter(lambda: response.read(1 << 20), b""):
                    received += len(chunk)
                    if received > cap:
                        raise RepresentationUnavailable(f"download exceeds the pinned size cap: {relative}")
                    digest.update(chunk)
                    out.write(chunk)
            if digest.hexdigest() != expected:
                raise RepresentationUnavailable(f"downloaded digest mismatch for {relative}")
            os.replace(temporary, destination)
            fetched[relative] = "fetched"
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    verify_model_dir(target)
    return fetched


def main(argv: list[str] | None = None) -> int:
    """``fetch`` only. Store verification is ``AgentMemory.verify_semantic_store()`` (api layer)."""

    parser = argparse.ArgumentParser(description="Pinned ONNX representation provider (#669)")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch_parser = commands.add_parser("fetch", help="download the pinned model files (explicit network use)")
    fetch_parser.add_argument("--dir", type=Path)
    args = parser.parse_args(argv)
    target = resolve_model_dir(args.dir)
    print(json.dumps({"dir": str(target), "files": fetch(target)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
