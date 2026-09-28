"""#594 Phase B: deterministic selection of the proposition-interpreter qualification sample.

Usage: python select_sample.py <longmemeval_s_cleaned.json> <out_dir>

Independence rules (enforced by construction and pinned by a test):

* this script imports nothing from ``agentmem_ref`` or ``run_longmemeval``; the
  Agent Memory interpreter is never run to select, stratify, or order items;
* gold fields (``answer``, ``answer_session_ids``, ``has_answer``, the ``answer_``
  session-id prefix) are never read for selection and never written;
* strata are surface cues of the source text, written from the annotation rubric's
  semantic categories, not from the runtime grammar.

Unit: one unique user-turn text of the LongMemEval_S turn-plane corpus (exact-text
dedupe, first occurrence in source order). Eligibility: 20..600 characters, >= 4
words, and no e-mail address, URL, or phone-number-like digit run (privacy hygiene
and annotation feasibility). Order key: sha256(SEED || NUL || sha256(text)).

Part R (representative): the first ``R_SIZE`` eligible items by order key.
Part S (stratified): for each stratum in fixed order and each origin in fixed
order, the first ``PER_CELL`` not-yet-selected eligible items flagged with that
stratum's cue. Origin is ``public_chat_filler`` for sessions whose id starts with
``sharegpt_`` / ``ultrachat_`` and ``simulated_user`` otherwise.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

SAMPLE_ID = "proposition-semantics-sample-v1"
SEED = "agent-memory-594-proposition-sample-v1"
R_SIZE = 100
PER_CELL = 7
ORIGINS = ("simulated_user", "public_chat_filler")
MIN_CHARS, MAX_CHARS, MIN_WORDS = 20, 600, 4
_PRIVACY = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|https?://|www\.|\d[\d\s().-]{8,}\d")


def _cue(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# Fixed order. Each cue is a surface signal for the rubric category of the same name.
STRATA: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("change_language", _cue(r"\b(moved|switched|changed (to|my)|no longer|not anymore|any ?more|stopped|quit|used to\b.*\bnow)\b")),
    ("coexistence_language", _cue(r"\b(also|as well|in addition|both|another)\b|\btoo\b")),
    ("employment", _cue(r"\b(i work|working (at|for|as)|my (job|boss|employer|company|coworkers?|colleagues?|manager)|hired|internship|part-time|full-time|side (job|gig|hustle))\b")),
    ("residence_location", _cue(r"\b(i live|living in|live in|my (apartment|house|home|neighborhood|hometown|city)|relocat\w*|based in|moved (to|into|from))\b")),
    ("preference", _cue(r"\b(i (really |absolutely |just )?(love|like|prefer|enjoy|hate|dislike|adore)|my favou?rite|i'?m (a big )?fan of|i'?m into)\b")),
    ("hedging", _cue(r"\b(maybe|might|perhaps|probably|possibly|i think|i guess|not sure|i believe)\b")),
    ("present_current", _cue(r"\b(currently|right now|these days|at the moment|nowadays|lately)\b")),
    ("prospective", _cue(r"\b(planning (to|on)|going to|gonna|will be|next (week|month|year|weekend)|upcoming|starting (next|in|on)|about to)\b")),
    ("past_habitual", _cue(r"\b(used to|back when|when i was (a |younger|in)|i would always|in the past)\b")),
    ("proper_noun_subject", re.compile(r"(?:^|[.!?]\s+)(?!I\b|The\b|This\b|That\b|It\b|My\b|What\b|How\b|Can\b|Could\b|Please\b|Write\b)[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\s(?:is|was|has|works|lives|likes|loves|moved|went|got)\b")),
    ("temporal_word_non_temporal", _cue(r"(?:^|[.!?]\s+)now,|\bnow that\b|\bfor now\b|\bjust now\b|\bany time\b|\bat the same time\b|\bin time\b")),
    ("simple_first_person_statement", re.compile(r"^I(?:'m| am| have| live| work| like| love| own| got| just)\b[^.!?;,]{3,100}[.!]?$")),
)


def _user_turns(source: Path):
    for question in json.loads(source.read_bytes()):
        for session_id, session in zip(question["haystack_session_ids"], question["haystack_sessions"]):
            origin = "public_chat_filler" if str(session_id).startswith(("sharegpt_", "ultrachat_")) else "simulated_user"
            for turn in session:
                if turn.get("role") == "user":
                    yield str(turn.get("content", "")), origin


def main() -> int:
    source, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    raw = source.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    seen: dict[str, str] = {}
    for text, origin in _user_turns(source):
        seen.setdefault(text, origin)
    population = []
    for text, origin in seen.items():
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        eligible = MIN_CHARS <= len(text) <= MAX_CHARS and len(text.split()) >= MIN_WORDS and not _PRIVACY.search(text)
        population.append({
            "text": text, "text_sha256": text_sha, "origin": origin, "eligible": eligible,
            "order_key": hashlib.sha256(f"{SEED}\x00{text_sha}".encode("utf-8")).hexdigest(),
            "cues": [name for name, pattern in STRATA if pattern.search(text)],
        })
    eligible = sorted((item for item in population if item["eligible"]), key=lambda item: item["order_key"])
    chosen: dict[str, dict] = {}
    for item in eligible[:R_SIZE]:
        chosen[item["text_sha256"]] = {**item, "part": "R", "stratum": None}
    cells = {}
    for name, _ in STRATA:
        for origin in ORIGINS:
            pool = [item for item in eligible if name in item["cues"] and item["origin"] == origin]
            picked = [item for item in pool if item["text_sha256"] not in chosen][:PER_CELL]
            for item in picked:
                chosen[item["text_sha256"]] = {**item, "part": "S", "stratum": name}
            cells[f"{name}/{origin}"] = {"eligible_population": len(pool), "selected": len(picked)}
    ordered = sorted(chosen.values(), key=lambda item: (item["part"], STRATA_INDEX.get(item["stratum"], -1), item["origin"], item["order_key"]))
    items = [
        {"item_id": f"ps1-{index:03d}", "part": item["part"], "stratum": item["stratum"], "origin": item["origin"],
         "surface_cues": item["cues"], "text_sha256": item["text_sha256"], "text": item["text"]}
        for index, item in enumerate(ordered, start=1)
    ]
    sample = {"sample_id": SAMPLE_ID, "source_sha256": source_sha, "items": items}
    rendered = json.dumps(sample, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    (out_dir / "sample-v1.json").write_text(rendered, encoding="utf-8")
    population_eligible = len(eligible)
    manifest = {
        "sample_id": SAMPLE_ID,
        "status": "FROZEN sample; annotations are not accepted gold",
        "source": {
            "dataset": "xiaowu0162/longmemeval-cleaned", "revision": "98d7416c24c778c2fee6e6f3006e7a073259d48f",
            "file": "longmemeval_s_cleaned.json", "sha256": source_sha, "license_note": "LongMemEval is distributed by its authors under MIT; filler turns originate from ShareGPT/UltraChat as redistributed there",
        },
        "unit": "unique user-turn text of the turn-plane corpus (exact-text dedupe, first occurrence in source order)",
        "selection": {
            "script": "reference/fixtures/benchmarks/proposition-semantics/select_sample.py",
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "seed": SEED, "order_key": "sha256(SEED || NUL || sha256(text))",
            "eligibility": {"min_chars": MIN_CHARS, "max_chars": MAX_CHARS, "min_words": MIN_WORDS, "privacy_exclusion": _PRIVACY.pattern},
            "part_R": {"size": R_SIZE, "method": "first R_SIZE eligible items by order key (simple random sample of the eligible population)"},
            "part_S": {"per_cell": PER_CELL, "strata_in_order": [name for name, _ in STRATA], "origins_in_order": list(ORIGINS),
                       "cue_patterns": {name: pattern.pattern for name, pattern in STRATA}, "cells": cells},
            "interpreter_used": False, "gold_fields_used": False,
        },
        "population": {
            "unique_user_turns": len(population), "eligible": population_eligible,
            "eligible_by_origin": {origin: sum(1 for item in eligible if item["origin"] == origin) for origin in ORIGINS},
        },
        "sample": {
            "size": len(items), "part_R": sum(1 for item in items if item["part"] == "R"), "part_S": sum(1 for item in items if item["part"] == "S"),
            "sample_file_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            "item_text_sha256_list_sha256": hashlib.sha256("\n".join(item["text_sha256"] for item in items).encode("utf-8")).hexdigest(),
        },
        "weighting_note": "Part R estimates population rates directly. Part S deliberately over-represents cue strata; report it per stratum and never pool it with Part R into one population rate.",
    }
    (out_dir / "sample-v1.manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


STRATA_INDEX = {name: index for index, (name, _) in enumerate(STRATA)}

if __name__ == "__main__":
    raise SystemExit(main())
