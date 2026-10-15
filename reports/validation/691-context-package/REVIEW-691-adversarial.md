# Independent adversarial review of #691 `recall_context` at `f6184d22` (base `77c472e6`)

A separate review agent worked read-only. Its main result: **no way was found for a caller to get
text for a fact that `recall()` with the same arguments would not return to it.** Its findings and
the dispositions:

| # | Severity | Finding | Disposition |
|---|---|---|---|
| F1 | blocking | Historical/as-of packages could not tell the current fact from a superseded one: every item carried only `admission_mode: historical_evidence`. | **Fixed.** Items carry `currentness`, plus `replacement_kind`, `replaced_at` and the historical validity window. |
| F2 | should-fix | `write_operation` was never populated (no such provenance key). | **Fixed.** Replaced by `write_channel`. |
| F3 | should-fix | The package schema did not enforce fail-closed states, so the final validation caught no leak. | **Fixed.** `if/then` rules: unresolved, unsupported and omitted items have no content or provenance; resolved and truncated items require both; `empty` and `complete` are consistent with their items. |
| F4 | should-fix (owner decision) | Forwarding `recall`'s privileged-host scope and identity overrides turned an ID-level override into content disclosure. | **Fixed conservatively.** `recall_context` refuses `target_domain_refs`, `project_ref`, `task_ref`, `principal_ref` and `purpose`. |
| N1 | note | `source_ref` (default `actor:<id>`) and `memory_ref` are newly disclosed to same-project readers. | Kept as requested provenance; listed as an **open owner decision** in docs/44. |
| N2 | note | `source_ref` is writer-controlled and was not withheld. | **Fixed.** It is checked by the #777 withholding predicate and documented as writer-declared. |
| N3 | note | There is no separate audit event for content reads. | **Open owner decision** (docs/44). |
| N4 | note | Truncation split grapheme clusters; the token estimate under-counted non-ASCII text. | **Fixed.** Cuts never split combining marks, joiners or variation selectors; the estimate counts each non-ASCII character as a token. |
| N5 | note | Package size was unbounded with `max_items=None`. | **Fixed.** Default `max_items=20`, and `None` is refused. |
| N6 | note | The re-check passes `target_seconds=None`. | Not exploitable (the lock is held); recorded. |
| N7 | note | The README overstated cross-process refusal. | **Corrected:** a second process can open the store, and the stale handle then fails with a checkpoint conflict. |

All six new regression tests in `tests/test_context_package.py` (`ReviewRegressions`) fail on
`f6184d22` and pass after the fix.

Attacks that held:
- **Interleaving:** correct, forget, dispute or revocation forced between recall and resolution
  resolves to `no_longer_admissible`.
- **Concurrency:** concurrent threads are serialised; a cross-process stale reader conflicts and is
  served nothing.
- **Corrections, disputes and derivation:** error corrections are never admitted; disputed facts
  are refused; facts derived from a forgotten source (two hops) are refused.
- **Identifiers:** re-remembering under a forgotten ref never shows the old uuid. The exact-identity
  route does not leak.
- **Compatibility:** `recall()` output is byte-identical to the base across six scenarios.
- **Input handling:** budget input fuzzing is refused correctly. Lone surrogates cannot be written.
  A failure inside `resolve` fails closed and releases the lock.
- **Untrusted text:** it only ever lands in `content`.
