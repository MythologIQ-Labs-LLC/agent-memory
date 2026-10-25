"""Optional host-side answer-support check for ``memory_find`` (Stage C).

Retrieval relevance is not answer support: a populated store returns plausible memories for
almost any question. The bridge settles evidence availability and currentness first (only
resolved, attributed, nonempty items that are not a known non-head key generation reach this
module). This module then decides, for those items only, whether any of them supports answering
the question. It never changes, reorders or removes the delivered evidence, and it never makes
an answer or verifies one: a supported item stays ``unverified`` evidence.

Two pinned models exist. The host chooses one by the model directory it names in
``AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR``; each directory layout matches exactly one pin set. The
answerability model serves two method versions; the newest is the default and
``AGENT_MEMORY_MCP_SUPPORT_METHOD`` (host-set, never a tool argument) can pin the other.

``answerability-subject-grounded/1.1.0`` (cycle 3, the default) is 1.0.0 below with support
admitted *per memory only*: subject applicability and answerability must hold for the same
memory. Reading all current memories together still runs, but only as the unadmitted diagnostic
``joint_answering_unadmitted``; it can no longer turn a subject named in one memory into support
for an answer found in another. When no single memory is supported, a bounded two-memory check
keeps a distributed answer from being called absent: a memory that names every question subject
(the anchor; the question must name at least one subject) and another delivered memory sharing a
*name* with it (a capitalised word in
mid-sentence, not a question subject) form a ``cross_memory_candidates`` entry naming both facts
and the shared names. That is not support and no classifier is asked to bless the pair: a shared
name does not establish how the facts relate, so the assessment stays ``unverified``
(``cross_memory_relationship_not_established``) instead of claiming absence.

``answerability-subject-grounded/1.0.0`` (cycle 2) keeps three questions apart:

1. *Subject applicability* (deterministic). Every name the question uses (a capitalised word
   after its first word, possessive stripped, not a function word) must occur in the item,
   compared with the runtime's own fold (``agentmem_ref.api.context_selection``). A memory about
   Tobias cannot support an answer about Noor or Imogen, however well it answers "where is the
   kayak". A question that names nobody constrains nothing here.
2. *Answerability* (learned). ``cross-encoder/qnli-electra-base``, trained on GLUE QNLI to judge
   whether a passage answers a question, scores each item; it answers when the logit is above 0
   (sigmoid 0.5, the model's own boundary). It needs no extractable span, so an answer that
   takes a step of inference (``allergic to peanuts`` for ``which food can Noor not eat``) can
   count. Its QNLI negatives are sentences from the same paragraph that do not answer, which is
   the related-but-non-answering distractor a memory store produces.
3. *Support* is both, for one item; or, for an answer spread over items, both for all the
   current items read together (windowed at the model's 512-token limit, stride 128).

``extractive-qa-null-comparison/1.0.0`` (the original candidate) is unchanged and remains an
experimental option: ``optimum/roberta-base-squad2``, a span beats the model's null answer under
the Hugging Face pipeline defaults (``max_seq_len=384``, ``doc_stride=128``,
``max_answer_len=15``, margin 0). It does not check subjects.

Both use the existing optional extra ``semantic`` (onnxruntime, tokenizers, numpy): no new
dependency, no LLM, no network on load or check. Every model file is pinned by sha256 and the
ONNX graph is loaded from the same bytes that were hashed. ``fetch`` is an explicit command.

usage: python answer_support.py fetch {extractive|answerability} DIR
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import urllib.request
from typing import Any, Sequence

ENV_DIR = "AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR"
METHOD_ENV = "AGENT_MEMORY_MCP_SUPPORT_METHOD"


@dataclass(frozen=True)
class Spec:
    method: str
    model_id: str
    revision: str
    graph: str
    # path -> (sha256, size in bytes)
    files: dict[str, tuple[str, int]]

    @property
    def model_ref(self) -> str:
        return f"{self.model_id}@{self.revision[:7]}"


EXTRACTIVE = Spec(
    method="extractive-qa-null-comparison/1.0.0",
    model_id="optimum/roberta-base-squad2",
    revision="db07770d7fa024df076e60947b445b0b3290f8eb",
    graph="model.onnx",
    files={
        "model.onnx": ("204a84036a76ec7dafad3a4613f9425316b0308d77ad88326795fef6eb64b718", 496305990),
        "tokenizer.json": ("fb35154b5c214e4235de078bfd0890777e06bce973689112c1d06a9157ed0288", 2108540),
        "config.json": ("963a7cc92d3d661821cfbeb87a6e1be54ec9081ef9f9780306275fbe57605a0e", 728),
    },
)
ANSWERABILITY = Spec(
    method="answerability-subject-grounded/1.0.0",
    model_id="cross-encoder/qnli-electra-base",
    revision="c7dea87c98b2269a935686c31336e97e837cbbeb",
    graph="onnx/model.onnx",
    files={
        "onnx/model.onnx": ("595b37541289472b7b784ed2af05bcad6000991a2657aeee4f92f68b42ae61d9", 438212375),
        "tokenizer.json": ("d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66", 711396),
        "config.json": ("a5589b5e14c631ac3536e122b5327dc1a1e559633e02ef1b10748d15be08484d", 771),
    },
)
SPECS = (EXTRACTIVE, ANSWERABILITY)

# The original candidate's public names, kept for hosts and evidence that refer to them.
METHOD, MODEL_ID, MODEL_REVISION, MODEL_REF = (EXTRACTIVE.method, EXTRACTIVE.model_id,
                                               EXTRACTIVE.revision, EXTRACTIVE.model_ref)
PINNED_FILES = EXTRACTIVE.files
MAX_SEQ_LEN = 384
DOC_STRIDE = 128
MAX_ANSWER_LEN = 15
CLASSIFIER_MAX_LEN = 512
CLASSIFIER_STRIDE = 128


class SupportCheckUnavailable(RuntimeError):
    """The optional packages or the pinned, verified model files are not available."""


def _verified_bytes(model_dir: Path, relative: str, spec: Spec = EXTRACTIVE) -> bytes:
    path = model_dir / relative
    if path.is_symlink() or not path.is_file():
        raise SupportCheckUnavailable(f"support model file missing or not a regular file: {relative}")
    data = path.read_bytes()
    expected, size = spec.files[relative]
    if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
        raise SupportCheckUnavailable(f"support model file digest mismatch: {relative}")
    return data


def _runtime(model_dir: Path, spec: Spec) -> tuple[Any, Any, Any]:
    """numpy, a one-thread ONNX session over the verified graph bytes, and the verified tokenizer."""
    if not model_dir.is_absolute():
        raise SupportCheckUnavailable("support model directory must be an absolute path")
    try:
        import numpy
        import onnxruntime
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise SupportCheckUnavailable("optional extra 'semantic' is not installed") from exc
    graph = _verified_bytes(model_dir, spec.graph, spec)
    tokenizer = _verified_bytes(model_dir, "tokenizer.json", spec)
    _verified_bytes(model_dir, "config.json", spec)
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session = onnxruntime.InferenceSession(graph, options, providers=["CPUExecutionProvider"])
    loaded = Tokenizer.from_str(tokenizer.decode("utf-8"))
    loaded.no_truncation()
    loaded.no_padding()
    return numpy, session, loaded


def _windows(context_ids: list[int], room: int, stride: int) -> list[list[int]]:
    """Consecutive windows of ``room`` tokens, each overlapping the previous one by ``stride``."""
    windows, start = [], 0
    while True:
        windows.append(context_ids[start:start + room])
        if start + room >= len(context_ids):
            return windows
        start += room - stride


class AnswerSupport:
    """The original candidate: a SQuAD 2.0 span beating the model's null answer."""

    METHOD = EXTRACTIVE.method
    MODEL_REF = EXTRACTIVE.model_ref
    REASONS = ("no_answer_span_in_current_evidence", "answer_span_candidate_not_verified")

    def __init__(self, model_dir: Path):
        self._np, self._session, self._tokenizer = _runtime(model_dir, EXTRACTIVE)

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
        for window in _windows(context_ids, room, DOC_STRIDE):
            ids = [0, *question_ids, 2, 2, *window, 2]
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


def named_subjects(question: str) -> frozenset[str]:
    """Folded names the question uses: capitalised words after the first, not function words."""
    from agentmem_ref.api.context_selection import FUNCTION_WORDS, _WORD, content_terms

    subjects: set[str] = set()
    for token in _WORD.findall(question.replace("’", "'"))[1:]:
        base = token.split("'", 1)[0]
        if base[:1].isupper() and base.casefold() not in FUNCTION_WORDS:
            subjects |= content_terms(base)
    return frozenset(subjects)


def grounded(subjects: frozenset[str] | set[str], text: str) -> bool:
    """Every named subject occurs in ``text`` under the runtime fold."""
    from agentmem_ref.api.context_selection import content_terms

    return set(subjects) <= content_terms(text)


def decide(question: str, contexts: Sequence[str], answering: Sequence[bool],
           joint_answering: bool) -> dict[str, Any]:
    """Support = subject applicability AND answerability, per item and for the joint text."""
    subjects = named_subjects(question)
    applicable = [grounded(subjects, text) for text in contexts]
    per_item = [a and b for a, b in zip(applicable, answering)]
    joint_applicable = grounded(subjects, "\n".join(contexts))
    return {"per_item": per_item, "joint": any(per_item) or (joint_applicable and bool(joint_answering)),
            "subjects": sorted(subjects), "applicable": applicable, "answering": list(answering),
            "joint_applicable": joint_applicable, "joint_answering": bool(joint_answering)}


def memory_names(text: str) -> frozenset[str]:
    """Folded names in a memory: capitalised words that do not start a sentence, not function words."""
    from agentmem_ref.api.context_selection import FUNCTION_WORDS, _STATEMENT_END, _WORD, content_terms

    names: set[str] = set()
    for sentence in _STATEMENT_END.split(text.replace("\u2019", "'")):
        for token in _WORD.findall(sentence)[1:]:
            base = token.split("'", 1)[0]
            if base[:1].isupper() and base.casefold() not in FUNCTION_WORDS:
                names |= content_terms(base)
    return frozenset(names)


def decide_per_memory(question: str, contexts: Sequence[str], answering: Sequence[bool],
                      joint_answering: bool) -> dict[str, Any]:
    """1.1.0: support only where one memory is both subject-applicable and answering.

    Without such a memory, each pair (anchor, partner) with the anchor naming every question
    subject and the partner sharing a name with it is a cross-memory *candidate* with its facts
    and shared names: an unresolved relationship, never support and never proof of absence.
    """
    from agentmem_ref.api.context_selection import content_terms

    subjects = named_subjects(question)
    applicable = [grounded(subjects, text) for text in contexts]
    per_item = [a and b for a, b in zip(applicable, answering)]
    candidates: list[dict[str, Any]] = []
    # A bridge starts from a memory naming the question's subject; a question naming no one has none.
    if subjects and not any(per_item):
        terms = [content_terms(text) for text in contexts]
        names = [memory_names(text) for text in contexts]
        seen: set[tuple[int, int]] = set()
        for anchor in (i for i, ok in enumerate(applicable) if ok):
            for partner in range(len(contexts)):
                pair = tuple(sorted((anchor, partner)))
                if partner == anchor or pair in seen:
                    continue
                links = ((names[anchor] | names[partner]) & terms[anchor] & terms[partner]) - subjects
                if not links:
                    continue
                seen.add(pair)
                candidates.append({"facts": list(pair), "link_terms": sorted(links),
                                   "relationship": "shared_name_unresolved"})
    return {"per_item": per_item, "joint": any(per_item), "subjects": sorted(subjects),
            "applicable": applicable, "answering": list(answering),
            "cross_memory_candidates": candidates,
            "diagnostics": {"joint_answering_unadmitted": bool(joint_answering)}}


class Answerability:
    """Cycle 2: subject-grounded, sentence-level answerability (QNLI cross-encoder)."""

    METHOD = ANSWERABILITY.method
    MODEL_REF = ANSWERABILITY.model_ref
    REASONS = ("no_supported_answer_in_current_evidence", "supported_answer_candidate_not_verified")

    def __init__(self, model_dir: Path):
        self._np, self._session, self._tokenizer = _runtime(model_dir, ANSWERABILITY)
        self._cls = self._tokenizer.token_to_id("[CLS]")
        self._sep = self._tokenizer.token_to_id("[SEP]")
        self._inputs = {item.name for item in self._session.get_inputs()}

    def answers(self, question: str, context: str) -> bool:
        np = self._np
        question_ids = self._tokenizer.encode(question, add_special_tokens=False).ids[: CLASSIFIER_MAX_LEN // 4]
        context_ids = self._tokenizer.encode(context, add_special_tokens=False).ids
        if not context_ids:
            return False
        room = CLASSIFIER_MAX_LEN - len(question_ids) - 3
        for window in _windows(context_ids, room, CLASSIFIER_STRIDE):
            ids = [self._cls, *question_ids, self._sep, *window, self._sep]
            feed = {"input_ids": np.array([ids], dtype=np.int64),
                    "attention_mask": np.ones((1, len(ids)), dtype=np.int64)}
            if "token_type_ids" in self._inputs:
                feed["token_type_ids"] = np.array([[0] * (len(question_ids) + 2) + [1] * (len(window) + 1)],
                                                  dtype=np.int64)
            if float(self._session.run(None, feed)[0].reshape(-1)[0]) > 0.0:
                return True
        return False

    def check(self, question: str, contexts: Sequence[str]) -> dict[str, Any]:
        answering = [self.answers(question, text) for text in contexts]
        joint = len(contexts) > 1 and self.answers(question, "\n".join(contexts))
        return decide(question, contexts, answering, joint)


class AnswerabilityPerMemory(Answerability):
    """Cycle 3: per-memory support, joined text only as a diagnostic, bounded linked pairs."""

    METHOD = "answerability-subject-grounded/1.1.0"
    CROSS_MEMORY_REASON = "cross_memory_relationship_not_established"

    def check(self, question: str, contexts: Sequence[str]) -> dict[str, Any]:
        answering = [self.answers(question, text) for text in contexts]
        joint = len(contexts) > 1 and self.answers(question, "\n".join(contexts))
        return decide_per_memory(question, contexts, answering, joint)


_METHODS = {EXTRACTIVE.method: AnswerSupport, Answerability.METHOD: Answerability,
            AnswerabilityPerMemory.METHOD: AnswerabilityPerMemory}


def methods_for(spec: Spec) -> tuple[str, ...]:
    """The method versions a pinned model serves, the default first."""
    if spec is ANSWERABILITY:
        return (AnswerabilityPerMemory.METHOD, Answerability.METHOD)
    return (EXTRACTIVE.method,)


_LOADED: dict[tuple[str, str], Any] = {}


def _spec_for(model_dir: Path) -> Spec:
    present = [spec for spec in SPECS if (model_dir / spec.graph).is_file()]
    if len(present) != 1:
        raise SupportCheckUnavailable("support model directory matches no single pinned method")
    return present[0]


def from_environment() -> Any:
    """``None`` when the host has not enabled the check; raises when enabled but unusable."""
    raw = os.environ.get(ENV_DIR, "")
    if not raw:
        return None
    model_dir = Path(raw)
    if not model_dir.is_absolute():
        raise SupportCheckUnavailable("support model directory must be an absolute path")
    offered = methods_for(_spec_for(model_dir))
    method = os.environ.get(METHOD_ENV) or offered[0]
    if method not in offered:
        raise SupportCheckUnavailable("requested support method is not served by this model directory")
    if (raw, method) not in _LOADED:
        _LOADED[(raw, method)] = _METHODS[method](model_dir)
    return _LOADED[(raw, method)]


def fetch(spec: Spec, model_dir: Path) -> None:
    """Explicit download of the pinned files from the Hugging Face hub, verified before use."""
    for relative, (_digest, size) in spec.files.items():
        target = model_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file():
            try:
                _verified_bytes(model_dir, relative, spec)
                continue
            except SupportCheckUnavailable:
                pass
        url = f"https://huggingface.co/{spec.model_id}/resolve/{spec.revision}/{relative}"
        with urllib.request.urlopen(url) as response, tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as part:
            while chunk := response.read(1 << 20):
                part.write(chunk)
                if part.tell() > size:
                    raise SupportCheckUnavailable(f"download larger than pinned size: {relative}")
        os.replace(part.name, target)
        _verified_bytes(model_dir, relative, spec)
    print(f"{spec.model_ref} verified in {model_dir}")


if __name__ == "__main__":
    methods = {"extractive": EXTRACTIVE, "answerability": ANSWERABILITY}
    if len(sys.argv) != 4 or sys.argv[1] != "fetch" or sys.argv[2] not in methods:
        raise SystemExit(__doc__.rsplit("usage: ", 1)[1])
    fetch(methods[sys.argv[2]], Path(sys.argv[3]).resolve())
