"""#594 Step A1: audit LongMemEval_S timestamp fields from the source alone (no Agent Memory).

Usage: PYTHONPATH=reference python source_timestamp_audit.py <longmemeval_s_cleaned.json> <out.json>
"""
import collections, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path

import run_longmemeval as lme

source, out = Path(sys.argv[1]), Path(sys.argv[2])
raw = source.read_bytes()
data = json.loads(raw)
pattern = re.compile(r"^(\d{4})/(\d{2})/(\d{2}) \(([A-Za-z]{3})\) (\d{2}):(\d{2})$")


def parse(value):
    match = pattern.match(value)
    if not match:
        return None, None
    y, mo, d, dow, h, mi = match.groups()
    return datetime(int(y), int(mo), int(d), int(h), int(mi)), dow


checks = collections.Counter()
years = collections.Counter()
turn_keys = collections.Counter()
for row in data:
    checks["questions"] += 1
    checks["haystack_lengths_aligned"] += len(row["haystack_dates"]) == len(row["haystack_sessions"]) == len(row["haystack_session_ids"])
    parsed = []
    for value in row["haystack_dates"]:
        checks["sessions"] += 1
        moment, dow = parse(value)
        if moment is None:
            checks["haystack_dates_unparseable"] += 1
            continue
        checks["day_of_week_mismatches"] += moment.strftime("%a") != dow
        years[str(moment.year)] += 1
        parsed.append(moment)
    checks["questions_whose_haystack_list_is_chronological"] += parsed == sorted(parsed)
    checks["adjacent_order_inversions_total"] += sum(1 for a, b in zip(parsed, parsed[1:]) if b < a)
    checks["questions_with_duplicate_session_timestamps"] += len(set(parsed)) < len(parsed)
    asked, _ = parse(row["question_date"])
    checks["question_date_unparseable"] += asked is None
    checks["question_date_before_latest_session"] += asked is not None and asked < max(parsed)
    for session in row["haystack_sessions"]:
        for turn in session:
            turn_keys[",".join(sorted(turn))] += 1
planes = {}
for plane in ("session", "turn"):
    counts = collections.Counter()
    affected = set()
    for row in data:
        items, gold = lme.corpus(row, plane)
        asked = lme._iso_date(row["question_date"])
        for item in items:
            observed = lme._iso_date(item["date"])
            counts["items"] += 1
            counts["mapped" if observed else "unmapped"] += 1
            if observed and asked and observed > asked:
                counts["items_observed_after_question_date"] += 1
                counts["gold_items_observed_after_question_date"] += item["id"] in gold
                affected.add(row["question_id"])
    planes[plane] = {**dict(sorted(counts.items())), "questions_affected_by_later_sessions": len(affected)}
out.write_text(json.dumps({
    "input_sha256": hashlib.sha256(raw).hexdigest(),
    "source_checks": dict(sorted(checks.items())),
    "years": dict(sorted(years.items())),
    "message_key_sets": dict(sorted(turn_keys.items())),
    "message_level_timestamps": sum(v for k, v in turn_keys.items() if any(t in k for t in ("date", "time"))),
    "mapping_counts": planes,
}, indent=1, sort_keys=True) + "\n")
