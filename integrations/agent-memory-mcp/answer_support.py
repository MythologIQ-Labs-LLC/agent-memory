"""Optional host-side answer-support check for ``memory_find`` (Stage C).

Retrieval relevance is not answer support: a populated store returns plausible memories for
almost any question. This module asks a narrower question of the evidence ``memory_find``
already delivered: does any current, complete item contain a span that an extractive
question-answering model trained with unanswerable questions would give as an answer?

* Model: ``optimum/roberta-base-squad2`` at a pinned revision, the ONNX export of
  ``deepset/roberta-base-squad2`` (SQuAD 2.0, CC-BY-4.0). SQuAD 2.0 trains the model to prefer
  a null answer when the passage does not answer the question, so the abstention boundary is
  the model's own, not a threshold fitted to this repository's cases.
* Decision rule (fixed before any Stage C cohort was evaluated): the Hugging Face
  question-answering pipeline with ``handle_impossible_answer=True`` and its default windowing
  (``max_seq_len=384``, ``doc_stride=128``, ``max_answer_len=15``). Per window, logits outside
  the context (except the ``<s>`` null position) are masked and soft-maxed. The null score is
  ``p_start[<s>] * p_end[<s>]``, minimised over windows, and a span ``p_start[s] * p_end[e]``
  (``s <= e < s + 15``, both in the context) is found when it beats that null score. The margin
  is 0.
* Its result is *never* verification. A found span keeps the assessment ``unverified``: an
  extractive model can pick a wrong span, and does not check who the memory is about. Only the
  absence of any span in all current, complete evidence makes it ``insufficient_evidence``.

Only the trusted host enables it, by naming a local model directory in
``AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR``. Without that, ``memory_find`` behaves as before
(``unverified``, ``answer_entailment_not_checked``). It uses the packages of the existing
optional extra ``semantic`` (onnxruntime, tokenizers, numpy), no new dependency and no LLM.
Every model file is pinned by sha256, and the ONNX graph is loaded from the same bytes that
were hashed. No network I/O happens on load or check; ``fetch`` is an explicit command.

usage: python answer_support.py fetch DIR
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import urllib.request
from typing import Any, Sequence

ENV_DIR = "AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR"
MODEL_ID = "optimum/roberta-base-squad2"
MODEL_REVISION = "db07770d7fa024df076e60947b445b0b3290f8eb"
METHOD = "extractive-qa-null-comparison/1.0.0"
MODEL_REF = f"{MODEL_ID}@{MODEL_REVISION[:7]}"
# path -> (sha256, size in bytes)
PINNED_FILES: dict[str, tuple[str, int]] = {
    "model.onnx": ("204a84036a76ec7dafad3a4613f9425316b0308d77ad88326795fef6eb64b718", 496305990),
    "tokenizer.json": ("fb35154b5c214e4235de078bfd0890777e06bce973689112c1d06a9157ed0288", 2108540),
    "config.json": ("963a7cc92d3d661821cfbeb87a6e1be54ec9081ef9f9780306275fbe57605a0e", 728),
}
MAX_SEQ_LEN = 384
DOC_STRIDE = 128
MAX_ANSWER_LEN = 15
_CLS, _SEP = 0, 2


class SupportCheckUnavailable(RuntimeError):
    """The optional packages or the pinned, verified model files are not available."""


def _verified_bytes(model_dir: Path, relative: str) -> bytes:
    path = model_dir / relative
    if path.is_symlink() or not path.is_file():
        raise SupportCheckUnavailable(f"support model file missing or not a regular file: {relative}")
    data = path.read_bytes()
    expected, size = PINNED_FILES[relative]
    if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
        raise SupportCheckUnavailable(f"support model file digest mismatch: {relative}")
    return data


class AnswerSupport:
    """Loads the pinned model once; ``spans_found`` checks each text against one question."""

    def __init__(self, model_dir: Path):
        if not model_dir.is_absolute():
            raise SupportCheckUnavailable("support model directory must be an absolute path")
        try:
            import numpy
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise SupportCheckUnavailable("optional extra 'semantic' is not installed") from exc
        model = _verified_bytes(model_dir, "model.onnx")
        tokenizer = _verified_bytes(model_dir, "tokenizer.json")
        _verified_bytes(model_dir, "config.json")
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_BASIC
        self._np = numpy
        self._session = onnxruntime.InferenceSession(model, options, providers=["CPUExecutionProvider"])
        self._tokenizer = Tokenizer.from_str(tokenizer.decode("utf-8"))
        self._tokenizer.no_truncation()
        self._tokenizer.no_padding()

    def _ids(self, text: str) -> list[int]:
        return self._tokenizer.encode(text, add_special_tokens=False).ids

    def span_found(self, question: str, context: str) -> bool:
        np = self._np
        question_ids = self._ids(question.lstrip())[: MAX_SEQ_LEN // 2]
        context_ids = self._ids(context)
        if not context_ids:
            return False
        room = MAX_SEQ_LEN - len(question_ids) - 4
        offset = len(question_ids) + 3
        best_span, min_null = 0.0, float("inf")
        start = 0
        while True:
            window = context_ids[start:start + room]
            ids = [_CLS, *question_ids, _SEP, _SEP, *window, _SEP]
            feed = {"input_ids": np.array([ids], dtype=np.int64),
                    "attention_mask": np.ones((1, len(ids)), dtype=np.int64)}
            start_logits, end_logits = (out[0].astype(np.float64) for out in self._session.run(None, feed))
            allowed = np.zeros(len(ids), dtype=bool)
            allowed[0] = True
            allowed[offset:offset + len(window)] = True
            p_start, p_end = (self._softmax(np.where(allowed, logits, -np.inf)) for logits in (start_logits, end_logits))
            min_null = min(min_null, float(p_start[0] * p_end[0]))
            context_start = p_start[offset:offset + len(window)]
            context_end = p_end[offset:offset + len(window)]
            scores = np.triu(np.tril(np.outer(context_start, context_end), MAX_ANSWER_LEN - 1))
            best_span = max(best_span, float(scores.max()))
            if start + room >= len(context_ids):
                break
            start += room - DOC_STRIDE
        return best_span > min_null

    def _softmax(self, logits):
        np = self._np
        shifted = np.exp(logits - np.max(logits))
        return shifted / shifted.sum()

    def check(self, question: str, contexts: Sequence[str]) -> dict[str, Any]:
        """Each text alone, then all of them together in delivery order (a cross-item answer)."""
        per_item = [self.span_found(question, text) for text in contexts]
        joint = any(per_item) or (len(contexts) > 1 and self.span_found(question, "\n".join(contexts)))
        return {"per_item": per_item, "joint": joint}


_LOADED: dict[str, AnswerSupport] = {}


def from_environment() -> AnswerSupport | None:
    """``None`` when the host has not enabled the check; raises when enabled but unusable."""
    raw = os.environ.get(ENV_DIR, "")
    if not raw:
        return None
    if raw not in _LOADED:
        _LOADED[raw] = AnswerSupport(Path(raw))
    return _LOADED[raw]


def fetch(model_dir: Path) -> None:
    """Explicit download of the pinned files from the Hugging Face hub, verified before use."""
    model_dir.mkdir(parents=True, exist_ok=True)
    for relative, (_digest, size) in PINNED_FILES.items():
        target = model_dir / relative
        if target.is_file():
            try:
                _verified_bytes(model_dir, relative)
                continue
            except SupportCheckUnavailable:
                pass
        url = f"https://huggingface.co/{MODEL_ID}/resolve/{MODEL_REVISION}/{relative}"
        with urllib.request.urlopen(url) as response, tempfile.NamedTemporaryFile(dir=model_dir, delete=False) as part:
            while chunk := response.read(1 << 20):
                part.write(chunk)
                if part.tell() > size:
                    raise SupportCheckUnavailable(f"download larger than pinned size: {relative}")
        os.replace(part.name, target)
        _verified_bytes(model_dir, relative)
    print(f"{MODEL_REF} verified in {model_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "fetch":
        raise SystemExit(__doc__.rsplit("usage: ", 1)[1])
    fetch(Path(sys.argv[2]).resolve())
