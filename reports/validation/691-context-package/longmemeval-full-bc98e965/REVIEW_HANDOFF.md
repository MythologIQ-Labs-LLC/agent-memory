# Frozen selective context candidate: CHANGES REQUIRED

Implementation: `bc98e9657366e5e3a16f89708a7f22935442a2c4`.
Pre-change base: `585e76fb87e5c08da51020327a70d6d1807e06b4`.
Existing issue-owned branch: `claude/eager-dirac-bftkfg-691-context` (#691).
Previous development evidence: `af699e4dab0af803935dc2abc2ee501e3ecac9ca`, sibling `lexical-profile-bc98e965/`.

This is an execution/review record, not an architecture or contract owner. `docs/ARCHITECTURE_INDEX.md` routes canonical ownership, `docs/44-public-api-contract.md` owns the API. Runtime source and accepted evidence govern behavior/qualification. No accepted baseline, corpus, lane, score, ADR or register changed.

## Review outcome to assess

Do not merge this candidate. A post-freeze full external LongMemEval_S run found loss of required evidence. Session question `2e6d26dc` loses `answer_fa526fc0_1`: all four annotated session targets were in the raw top 50; the selected package retains three. Complete recall@50 falls from 419/419 to 418/419. The lower delivered context load cannot compensate for this failed gate. The turn run also loses `answer_fa526fc0_1_1` in that question and `answer_0b1a0942_1_5` in `830ce83f`. Turn complete recall@50 falls from 360/419 to 358/419; scored required-turn coverage falls from 746/832 to 744/832. No production implementation or configuration was changed after viewing these results.

The diagnosed mechanism is lexical morphology and implicit relationships. Query tokens use plural forms while the omitted relevant content uses singular forms and a specific family relationship. A safe general remedy requires more than treating exact token intersection as proof of necessary relevance. Do not add this question, its answer, ID, or query pattern to runtime code. A follow-up candidate needs independently specified morphology/paraphrase/relationship counterexamples and genuinely unavailable holdout cases after its own freeze. This now-observed benchmark is regression evidence, never an unseen holdout.

## Independent reviewer work

1. Independently inspect the complete five-file diff from base to implementation. Confirm default 0.1.0 package compatibility, opt-in 0.2.0 scope, read authority, omissions/partial resolution receipts, and preservation of candidate/admission/ranking semantics.
2. Reproduce the recall loss using the pinned external input and the recorded driver. Verify the scorer is unchanged and gold/fixture identities do not enter runtime selection. Inspect the assertion that default content exactly matches raw ranked IDs.
3. Review security and unresolved content paths, no-answer behavior, currentness/supersession, negative selection, nonlexical provenance and information disclosure. An author's successful test execution does not satisfy independent review.
4. Preserve failed candidate evidence. Decide a bounded replacement mechanism and preregister fresh disjoint holdout cases unavailable to the implementation author. Existing public AMB 77 cases and LongMemEval are diagnostic/regression suites.
5. Keep #691 open. The inherited #805/#815 release HOLD and security acceptance, contract/successor decision and lane qualification are separate unresolved gates. Do not mutate the baseline register or conflate these records with accepted-lane qualification.

Prior exact-head results: 131 targeted tests, package layout 8 tests/156 subtests, DSL2 31 and DSL3 13 security cases pass. Full reference suite: 3011 passed, five failures also reproduced unchanged on base, 35 skipped, one xfailed, 2080 subtests. Four failures are inherited identity/freshness expectations. The fifth foreign-UID directory ownership test fails at `os.chown` with OSError 22 in the one-UID container before exercising the runtime; that property remains unqualified. See prior raw logs for exact names and commands.

## Reproduction

Obtain the dataset yourself; it is not redistributed here:
`https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/98d7416c24c778c2fee6e6f3006e7a073259d48f/longmemeval_s_cleaned.json?download=true`
SHA-256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.

At a clean implementation checkout, with the reference package configured:

```bash
PYTHONPATH=reference python qualify_context_longmemeval.py --runtime /absolute/checkout --input /absolute/longmemeval_s_cleaned.json --plane session --out /absolute/session-results
PYTHONPATH=reference python qualify_context_longmemeval.py --runtime /absolute/checkout --input /absolute/longmemeval_s_cleaned.json --plane turn --out /absolute/turn-results
```

The comparison helper records the original Work checkout paths and can be edited only for file locations. Runtime input and scoring rules must remain identical. The primary driver accepts portable input/output/runtime paths and records its own hash and revision identity. The data loader verifies all 500 questions and source/selection hashes.

No paid inference, QA model judge, hosted GitHub Actions, private Jarvis access, merge or release is part of these commands. These runs measure retrieval, not answer-generation task success.
