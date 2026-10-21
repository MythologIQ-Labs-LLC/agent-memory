# Erratum: expectation count in the `-v3` pre-execution review addendum

Record: `reports/validation/805-at-head/independent-replay-review-v3-preexecution.md`, section
"Addendum: revision 842e5734", paragraph "(1) Expectation deltas". Raised by the owner on PR #805
(2026-10-15, F-R3-2 checkpoint). The frozen `-v3` fixtures, the review record's findings and the
first-execution evidence under `reports/validation/786-security-replays-v3/` are not changed by
this erratum; the record itself is left as written and carries a one-line pointer here.

| | as written | correct |
|---|---|---|
| expectations remaining after the `842e5734` revision | "235 expectations remain, 240 minus the three removals, with `derived` counted once" | **237**: 240 minus the three removals (W6 `parked_committed`, W8b `parked_b`, L5b `member_tombstone_unchanged`); `derived` was narrowed, not removed, so it still counts once |

The committed fixtures at `842e5734` (and unchanged since) contain:

| fixture | cases | `expect` entries |
|---|---|---|
| `cross-scope-write-authority-denial-v3` (W) | 13 | 121 |
| `deleted-lineage-generations-and-restart-v3` (L) | 10 | 82 |
| `public-tombstone-redaction-and-observer-separation-v3` (R) | 8 | 34 |
| total | 31 | 237 |

The addendum's own table of `679cefbf` counts (W 123, L 83, R 34 = 240) and the evidence README's
"31 cases, 237 expectations" are consistent with this; only the subtraction in the addendum was
wrong. The addendum's other statements (which expectations moved, that none was added, that
every quotation was re-verified) are unaffected. The documented order of events stands as recorded:
the addendum was completed after the first execution at `842e5734`, and the reviewer read committed
text only, never the evidence.

Reproduce: `python3 -c "import json; ..."` over the three fixtures, or
`reference/tests/test_786_security_replays_v3.py` (which pins the fixture digests). Counted on
2026-10-15 at `28f257c9`.
