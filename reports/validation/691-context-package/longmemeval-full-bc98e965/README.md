# Full external LongMemEval_S paired retrieval check

**CHANGES REQUIRED.** Frozen implementation `bc98e9657366e5e3a16f89708a7f22935442a2c4` loses previously returned annotated evidence. Do not merge or admit benchmark scores from this candidate. See [REVIEW_HANDOFF.md](REVIEW_HANDOFF.md).

The author ran all 500 pinned questions in both session and turn planes, using the existing native loader, adapter, scorer and summarizer. Each plane has 419 scored questions, 30 abstention exclusions and 51 no-user-target exclusions. Runtime sees plain text and opaque positional targets, no gold, question types or temporal labels. Admission, ranking and raw return receipts are asserted unchanged before/after package selection.

| Plane | Raw/default complete recall@50 | Selected complete recall@50 | Scored required evidence returned | Raw-v6 rank/metric mismatches |
|---|---:|---:|---:|---:|
| session | 419/419 | 418/419 | 794/794 → 793/794 | 0 |
| turn | 360/419 | 358/419 | 746/832 → 744/832 | 0 |

Raw results match every frozen v6 ranked list and per-case retrieval metric. This is behavioral reproduction under the candidate lineage, not acceptance of a new runtime baseline. Default context packages preserve the same IDs and order. The selected protocol has separate results.

The profile loses annotated evidence for `2e6d26dc` in both planes and for `830ce83f` in the turn plane. Per-case metric changes, gold IDs, ranking lists, native summaries, resource samples and exact identities are in the compressed reports and comparison.json. Delivery summaries report scored micro precision/recall separately from the upstream metrics; non-gold IDs are annotation-relative and are not proof that every such item is irrelevant. The upstream retrieval suite does not measure strict answer correctness, must-exclude safety or generated QA success.

## Limits and controls

- This external public dataset was loaded after implementation freeze; it is not a genuinely blinded holdout and now must remain regression evidence. No post-result implementation or configuration tuning occurred.
- No model inference, answer generation or judging occurred. Semantic retrieval and recall control are off; default ranking and metadata=none match the accepted retrieval configuration.
- Both arms use k=50. Context character/token bounds are deliberately generous to prevent truncation from hiding required evidence. These are not the ordinary consumer defaults and are recorded in identities.
- All profile packages are fully resolved; unresolved/truncated items stop the run rather than count as correct abstention.
- Raw/default/selected recall calls share ingestion, hardware and one process. Call order is fixed and warms caches. The two plane processes overlapped; CPU/wall totals are descriptive, not controlled speed claims. RSS is process high-water, not attributable per-arm memory.
- Neither arm correctly abstains on any of the 30 no-answer questions in either plane. Returning fewer IDs is not successful abstention.
- Previous 77-case AMB improvements remain known diagnostic evidence, not qualification. Accepted evidence and baseline register remain byte-unchanged.

## Commands and real results

```bash
PYTHONPATH=reference python /tmp/qualify_context_longmemeval.py --runtime /workspace/scratch/fa6d5f50ddfd/agent-memory-context-qualified --input /tmp/longmemeval_s_cleaned.json --plane session --out /tmp/691-lme-full-session
PYTHONPATH=reference python /tmp/qualify_context_longmemeval.py --runtime /workspace/scratch/fa6d5f50ddfd/agent-memory-context-qualified --input /tmp/longmemeval_s_cleaned.json --plane turn --out /tmp/691-lme-full-turn
python /tmp/compare_context_longmemeval.py
```

Both full runs completed 500 questions without runtime/ingestion/assertion failure. A successful process exit did not pass the preservation gate: loss of required evidence rejects the candidate. Checkpoint logs preserve progress and per-question counts. No dataset content is redistributed. The upstream source/data hashes and selection digest are in identity files. The manifest records SHA-256, lengths and Git blob identities for this evidence package.

Next action: independent review of the failed selection mechanism and security/authority boundaries, then separately preregister a bounded general correction and new unavailable holdout. The #805/#815 release HOLD, package acceptance, runtime successor and lane gates remain blocked independently. No new PR, merge, release or baseline-register mutation occurred.
