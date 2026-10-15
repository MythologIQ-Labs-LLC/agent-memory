# #644 — Indexed same-slot audit and independent reconciliation

**State:** implementation staged on a quiet, unopened branch. Candidate Runtime Baseline v7 is declared but **not** published. Independent verdict **CHANGES REQUIRED** remains binding.

## Change to the existing safety reconciliation

Claude's independent assessment of candidate `e002536` demonstrated that the all-facts SQLite audit was 608 ms at 10,000 facts, versus 259 ms for recall. The reference adapter already maintains a scoped typed/semantic slot index during governed writes and recovery. A repeated `all_facts()` scan forced expensive SQLite deserialization for evidence unrelated to the requested slot.

`GovernedMemoryAdapter.current_typed_slot_obstacles` now walks `_semantic_index()` and selects only entries whose canonical slot is requested. The index is **not** a trust or admission authority: each candidate is retrieved and rechecked with `_admission_refusal`, current transaction validity, and `write_semantics` scope/tombstone visibility before being counted. Malformed index keys or substrates incapable of complete enumeration fail closed. No hidden fact IDs or raw values are returned to callers.

The temporal obstacle now covers a declared `valid_until` and a declared `valid_from` later than the fact's recorded `created_at`. `parse_time` handles time-zone normalization, and malformed declared starts are conservative obstacles. No time-of-observation clock read is added.

The two compatibility aliases now match the exact output of `scripts/restructure_package.py:alias_source`. The succession test requires the exact candidate-v7 `declared_successor` object while still asserting that the last published baseline is v6. An explicitly **unaccepted** declaration entry is recorded in `docs/META_LEDGER.md`, with no gate PASS.

## Tests added, pending execution

New controls in `reference/tests/test_recall_control.py` cover: future-dated `valid_from`, warm-index execution where calling `all_facts()` would fail, and an independent same-slot visible-fact census compared to the indexed result. Existing regression cases cover unavailable candidate membership, weaker same-slot counter-evidence, declared `valid_until`, mutable results, missing untyped competitors and refusal of a completeness stop.

**No passing results are claimed yet for this exact branch.** The full repository is not present in this execution container, and the connected desktop remains offline. Source-level review and exact protected blob pins do not substitute for tests.

The original 126-case held-out corpus must remain unchanged. Its earlier 0/78 unsafe stop count and 0/48 safe stop count belong to `e002536`, not this new SHA. The new index must be shown equivalent to full-store enumeration across insert/correct/delete/dispute/recover and SQLite 1k/3k/10k scale. Formal release gates remain the 8 package tests, 40 succession tests, full reference suite, sanctioned declaration tool and checker (TRANSITION), noninterference, replay, public gauntlet, AMB and LongMemEval.

## Residual requirements

This fixes neither untyped same-slot counter-evidence classification nor authenticated slot completeness. The runtime must continue to refuse stop recommendations. Immutable planner-receipt development is independently staged on a different branch, and must be reconciled only after both candidates pass their respective local and adversarial evaluations. Avoid creating conflicting v7 register declarations or spending GitHub Actions minutes on iterative debugging.
