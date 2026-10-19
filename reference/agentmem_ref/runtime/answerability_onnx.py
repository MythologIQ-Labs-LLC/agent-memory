"""Pinned local ONNX answerability cross-encoder for semantic proposals (#819 C10).

C9-S showed that dense cosine, dense rank and topical overlap cannot tell a memory that answers
the question from a similar one that does not: every rule over them trades needed evidence for
precision. This provider adds one signal those features lack, a pair score from a cross-encoder
trained to judge whether a sentence answers a question (QNLI). Its logit has a query-independent
decision boundary (logit 0 is P(answers) = 0.5); cosine has none. The semantic route uses that
boundary unchanged (``ANSWERABILITY_LOGIT_FLOOR``); no threshold is fitted.

Model: ``cross-encoder/qnli-electra-base`` at revision ``c7dea87``, the fp32 ONNX export in the
model repository. Every model file is pinned by sha256 and re-verified whenever a provider is
constructed, and the configuration must assert a single-logit sequence-classification head.
Quantized exports are not used: on the development sets int8 lost most of the signal.

Determinism: one ONNX Runtime CPU session with basic graph optimization; ``intra_op_threads``
(default 1) is a numerics setting bound into ``config_digest`` with the file digests and the
``onnxruntime``, ``tokenizers`` and ``numpy`` versions. Pairs are scored in one padded batch in
the caller's order. Bit-identity is claimed per library versions, thread count and CPU
instruction set.

The score is candidate-proposal evidence only (``authority_effect="none"``): it never admits,
ranks or returns a fact by itself. No network I/O happens on open, recall or restart; ``fetch``
is an explicit command.
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
from typing import Any, Sequence

MODEL_ID = "cross-encoder/qnli-electra-base"
MODEL_REVISION = "c7dea87c98b2269a935686c31336e97e837cbbeb"
ANSWERABILITY_REF = f"{MODEL_ID}@{MODEL_REVISION[:7]}"
ANSWERABILITY_VERSION = "onnx-pair-logit-f32/1.0.0"
#: The model's own decision boundary, P(answers) = sigmoid(0) = 0.5.
ANSWERABILITY_LOGIT_FLOOR = 0.0
MAX_SEQ_LENGTH = 512
ENV_DIR = "AGENT_MEMORY_ANSWERABILITY_DIR"
DEFAULT_DIR = Path.home() / ".cache" / "agent-memory" / "answerability" / "qnli-electra-base-c7dea87"

# path -> (sha256, size in bytes)
PINNED_FILES: dict[str, tuple[str, int]] = {
    "onnx/model.onnx": ("595b37541289472b7b784ed2af05bcad6000991a2657aeee4f92f68b42ae61d9", 438212375),
    "tokenizer.json": ("d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66", 711396),
    "config.json": ("a5589b5e14c631ac3536e122b5327dc1a1e559633e02ef1b10748d15be08484d", 771),
}
NUMERICS = {
    "output": "logit_index_0",
    "truncation_max_length": MAX_SEQ_LENGTH,
    "truncation_strategy": "tokenizers_pair_longest_first",
    "padding": "batch_longest",
    "graph_optimization_level": "ORT_ENABLE_BASIC",
    "inter_op_num_threads": 1,
    "execution_provider": "CPUExecutionProvider",
    "output_canonicalisation": "float32",
}
_MAX_DOWNLOAD_OVERHEAD = 1.01


class AnswerabilityUnavailable(RuntimeError):
    """The optional extra or the pinned, verified answerability model files are not available."""


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
            raise AnswerabilityUnavailable(f"model file missing or not a regular file: {path}")
        digest = _sha256_file(path)
        if digest != expected:
            raise AnswerabilityUnavailable(f"model file digest mismatch for {relative}: {digest}")
        observed[relative] = digest
    config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    if (config.get("architectures") != ["ElectraForSequenceClassification"]
            or len(config.get("id2label") or {}) != 1
            or config.get("max_position_embeddings") != MAX_SEQ_LENGTH):
        raise AnswerabilityUnavailable("pinned model configuration does not assert a single-logit pair classifier at 512")
    return observed


def _library_versions() -> dict[str, str]:
    from importlib import metadata

    versions = {}
    for name in ("onnxruntime", "tokenizers", "numpy"):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError as exc:
            raise AnswerabilityUnavailable(f"optional extra 'semantic' is not installed: {name}") from exc
    return versions


def config_digest(versions: dict[str, str], intra_op_threads: int) -> str:
    material = {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "answerability_version": ANSWERABILITY_VERSION,
        "files": {path: digest for path, (digest, _size) in sorted(PINNED_FILES.items())},
        "numerics": dict(NUMERICS, intra_op_num_threads=intra_op_threads),
        "logit_floor": ANSWERABILITY_LOGIT_FLOOR,
        "libraries": versions,
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AnswerabilitySpec:
    answerability_ref: str
    answerability_version: str
    config_digest: str
    logit_floor: float
    authority_effect: str = "none"

    def to_dict(self) -> dict[str, object]:
        return {
            "answerability_ref": self.answerability_ref,
            "answerability_version": self.answerability_version,
            "config_digest": self.config_digest,
            "logit_floor": self.logit_floor,
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class _Session:
    session: Any
    tokenizer: Any
    input_names: tuple[str, ...]
    numpy: Any


class OnnxAnswerabilityScorer:
    """Pair logits ``(question, memory text)`` from the pinned QNLI cross-encoder; evidence only."""

    def __init__(self, model_dir: str | Path | None = None, *, intra_op_threads: int = 1) -> None:
        if not isinstance(intra_op_threads, int) or isinstance(intra_op_threads, bool) or intra_op_threads < 1:
            raise ValueError("intra_op_threads must be a positive integer")
        directory = resolve_model_dir(model_dir)
        versions = _library_versions()
        verify_model_dir(directory)
        try:
            import numpy
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as exc:  # pragma: no cover - guarded by _library_versions
            raise AnswerabilityUnavailable("optional extra 'semantic' is not installed") from exc
        tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        tokenizer.enable_truncation(max_length=MAX_SEQ_LENGTH)
        tokenizer.enable_padding()
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = intra_op_threads
        options.inter_op_num_threads = 1
        options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_BASIC
        session = onnxruntime.InferenceSession(
            str(directory / "onnx" / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )
        self._state = _Session(session, tokenizer, tuple(item.name for item in session.get_inputs()), numpy)
        self.model_dir = directory
        self.library_versions = versions
        self._spec = AnswerabilitySpec(
            answerability_ref=ANSWERABILITY_REF,
            answerability_version=ANSWERABILITY_VERSION,
            config_digest=config_digest(versions, intra_op_threads),
            logit_floor=ANSWERABILITY_LOGIT_FLOOR,
        )

    @property
    def spec(self) -> AnswerabilitySpec:
        return self._spec

    def score(self, question: str, texts: Sequence[str]) -> tuple[float, ...]:
        """One logit per text, in order; higher means the text more likely answers ``question``."""

        if not texts:
            return ()
        np = self._state.numpy
        encodings = self._state.tokenizer.encode_batch([(question, text) for text in texts])
        feeds = {
            "input_ids": np.asarray([item.ids for item in encodings], dtype=np.int64),
            "attention_mask": np.asarray([item.attention_mask for item in encodings], dtype=np.int64),
        }
        if "token_type_ids" in self._state.input_names:
            feeds["token_type_ids"] = np.asarray([item.type_ids for item in encodings], dtype=np.int64)
        logits = self._state.session.run(None, feeds)[0].reshape(len(texts), -1)[:, 0]
        return tuple(float(np.float32(value)) for value in logits)


# Explicit acquisition --------------------------------------------------------------


def fetch(target: Path) -> dict[str, str]:
    """Download exactly the pinned files at the pinned revision; verify before rename."""

    if target.is_symlink():
        raise AnswerabilityUnavailable(f"refusing a symlinked target directory: {target}")
    target.mkdir(parents=True, exist_ok=True)
    fetched = {}
    for relative, (expected, size) in PINNED_FILES.items():
        destination = target / relative
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            raise AnswerabilityUnavailable(f"refusing a non-regular destination: {destination}")
        if destination.is_file() and _sha256_file(destination) == expected:
            fetched[relative] = "present"
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        cap = int(size * _MAX_DOWNLOAD_OVERHEAD)
        url = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{relative}"
        handle, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".fetch-")
        try:
            digest, received = hashlib.sha256(), 0
            with os.fdopen(handle, "wb") as out, urllib.request.urlopen(url, timeout=120) as response:
                for chunk in iter(lambda: response.read(1 << 20), b""):
                    received += len(chunk)
                    if received > cap:
                        raise AnswerabilityUnavailable(f"download exceeds the pinned size cap: {relative}")
                    digest.update(chunk)
                    out.write(chunk)
            if digest.hexdigest() != expected:
                raise AnswerabilityUnavailable(f"downloaded digest mismatch for {relative}")
            os.replace(temporary, destination)
            fetched[relative] = "fetched"
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    verify_model_dir(target)
    return fetched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pinned ONNX answerability cross-encoder (#819 C10)")
    commands = parser.add_subparsers(dest="command", required=True)
    fetch_parser = commands.add_parser("fetch", help="download the pinned model files (explicit network use)")
    fetch_parser.add_argument("--dir", type=Path)
    args = parser.parse_args(argv)
    target = resolve_model_dir(args.dir)
    print(json.dumps({"dir": str(target), "files": fetch(target)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
