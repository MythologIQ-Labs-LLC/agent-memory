# #769: Untyped competition and positive-stop safety contract

**Status:** preregistered evaluation-only candidate. Not runtime implementation, benchmark acceptance, an ADR promotion, or permission to stop.  
**Parent:** #644. **Related:** #757, #732, #770 and the F6 untyped-competitor adversarial finding.  
**Baseline boundary:** published v6 remains authoritative; v7 remains an unqualified TRANSITION.  
**Files:** `reference/fixtures/runtime/769-untyped-competition-v1.json`, `reference/tests/test_769_untyped_competition_contract.py`, `scripts/check_769_untyped_competition_contract.py`.

## Problem and core decision

The v7 observer can report coverage while failing to distinguish genuinely absent
competition from *observed but untyped* possibly competing memory. That ambiguity
is not a license to treat the observed set as clear. Conversely, textual similarity
does not certify proposition identity, contradiction, exclusivity, a common
source, or currentness. More false-positive typed links would make the controller
*less* trustworthy, not more.

We separate **diagnosis**, **evidence integrity**, **scope attestation**, and
**positive-stop eligibility**. These are independent axes. The runtime's present
`stop_recommendation = abstain` remains unchanged.

### Input boundary (evaluation model only)

The synthetic observer consumes a *closed projection* over already-governed,
admitted evidence. It is forbidden to use raw strings, retrieved but refused
records, hidden tenant metadata, benchmark labels, external judge answers, or
learned similarity as ground truth. Every field must come from a real
authoritative or appropriately scoped runtime observation before production use.

| Field | Meaning | Required production provenance |
| --- | --- | --- |
| `receipt_state` | Whether this particular query/admission/route result was integrity-verified | Bound receipt checker, exact evaluated revision and query |
| `scope_enumeration` | Whether **all within-scope eligible competitors** were durably attested, not merely observed at top-k | Independent scoped enumeration, persisted revision, restart, and bounded-index checks |
| `admission_boundary` | No refused/hidden source influenced this projection | Canonical governed admission and scope |
| `support_posture` | Trusted typed support vs controller estimate or none | Versioned persisted typed observation; no conversion from confidence |
| `typed_conflict` | An *already verified* same-slot, incompatible, exclusive-value relationship exists | Persisted typed identity + cardinality/exclusivity + temporal coexistence check |
| `untyped_competitor` | A **visible admitted** contender has potentially overlapping scope without verified typed identity | Admission-safe observation, explicitly non-authoritative |

`attested_complete` is **hypothetical and not provided by the present
v7 recall result**. Its appearance in the fixture specifies a future
capability boundary, not evidence that full-scope attestation is implemented.
Current runtime observations must be projected as `read_path_observed` or
`unknown` until independent qualification says otherwise.

### Deterministic precedence

1. A missing, stale, or mismatched receipt gives `observation_integrity_unknown`.
2. Without full-scope attestation, diagnose `enumeration_unattested`.
3. With unverified admitted-only boundaries, diagnose `admission_scope_unverified`.
4. Then an actually verified typed exclusive conflict gives `typed_conflict`.
5. Otherwise, an admitted untyped possible contender gives `untyped_identity_unverified`.
6. Only otherwise use `no_competitor_observed`, meaning **among the authorized,
   attested scope**, not that no other memory exists.

For every case, `stop_recommendation` is **`abstain`** and
`authority_effect` is **`none`**. A clear status with trusted typed support
may be `reviewable_for_future_positive_policy` **only when full-scope
attestation was already supplied as input**. This bool does not recommend,
authorize, or execute a stop; a future independent versioned decision policy
must establish sufficient value and acceptable risks before any positive
recommendation can be possible.

This ordering diagnoses one primary blocker. Implementations may retain
separate internal flags but may never turn the flag/count of an inaccessible
source into an externally observable label or side channel.

## Privacy and noninterference

The reader's authorized domain is a necessary boundary, not just a filter
after scoring. A new hidden tenant memory, refused source, forgotten memory,
or non-admitted dispute may not perturb the consumer's observable diagnosis,
counts, rank, stop recommendation, or operation timing through slot audits.

Not all changes to public content are privacy-neutral. A new **admitted**
candidate can change the diagnostic. A new **unadmitted** candidate cannot.
The fixtures specify this contract without introducing actual hidden text.
The synthetic evaluator rejects unknown/opaque metadata fields rather than
logging, inspecting, or propagating them.

## Frozen adversarial set

The 32 committed synthetic cases were authored **before** the evaluator.
They cover untyped competitors, typed exclusive conflict, unknown cardinality,
coexistence, lexical overlap, paraphrases, capitalization, privacy projection,
admission mismatch, missing/stale receipts, partial vs complete enumeration,
missing typed support, multiple agreeing sources, and two-failure precedence.

Each output is typed; no fixture asserts `actual_stop = true`, a gold
answer, external source independence, or any "benchmark win." No F6 test
phrases or benchmark labels become runtime vocabulary.

### Reproduction

From the repository root, without GitHub Actions:

```bash
python scripts/check_769_untyped_competition_contract.py
python -m unittest discover -s reference/tests -t reference -p test_769_untyped_competition_contract.py
```

The first command checks the frozen fixture's shape and its expected labels.
The tests check fail-closed missing inputs, closed schema, and that hidden
metadata cannot alter the visible projection. These are **not** production
runtime tests and cannot authorize a release. A dedicated runtime adapter and
separately frozen unseen evaluations would be needed before any conclusion
about actual #644 behavior.

## Next staged work

**S1, architecture approval:** review the taxonomy against the currently
available `recall_control.py`, `evidence_sufficiency.py`, and receipt
contract, including the security threat model of full-scope attestation.
Allow unknown identity rather than demanding invented typed links.

**S2, evidence projection:** add runtime diagnostics only on a separately
declared successor protected-tree revision. Prove original status labels and
default policy behavior are preserved or explicitly governed. No controller
stop decision changes in S2. Refused and hidden memories do not enter the
projection.

**S3, adversarial qualification:** independently build an unseen corpus,
challenge rewritten paraphrases and identity mismatches, require zero unsafe
recommendations on the unchanged 126-case original holdout, and test genuinely
useful eligible recommendations **only** after a separate positive policy is
designed. No score tuning against this fixture.

**S4, performance:** indexed 1k/3k/10k SQLite stores; cold and warm,
read amplification, p50/p95/p99 recall, and restart consistency. An
unbounded slot scan is a blocker even if safe in tiny tests.

**S5, publication:** separate acceptance, reviewer, ledger, Gauntlet, AMB and
LongMemEval gates. #770's imported parity proves *retrieval parity*; it does
not certify a new F6 policy, full-scope enumeration, or positive stopping.

## Open decisions for owner and independent reviewer

- Does "complete" mean a snapshot of all eligible persisted *slot* records,
  and how is that bound to the current principal, tenant, purpose, and
  temporal target without leaking other domains?
- Which trusted typed identity proof is strong enough to classify *absence*
  of meaningful competition, not merely presence of a confirmed conflict?
- Does the production API surface competition details only to privileged
  diagnostics, or return a restricted status to ordinary callers?
- What minimum useful-positive-stop rate is acceptable while preserving
  a zero-unsafe-stop floor under unseen workloads?
- Are full-scope certificates allowed to be cached, and if so what invalidates
  them after writes, corrections, deletion, disputes, and restart?

All answers remain proposals until reviewed. This branch has **zero runtime
changes**, **zero Actions runs**, and **zero accepted performance claims**.
