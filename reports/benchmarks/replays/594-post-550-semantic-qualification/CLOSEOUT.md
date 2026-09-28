# #594 semantic qualification closeout

Status: **QUALIFIED**. This file supersedes the pre-gold stop line in this directory's original Phase B README. The Phase A evidence remains unchanged and accepted; Phase B now has independently frozen accepted gold and a first deterministic score.

No #594 commit changes `reference/agentmem_ref/`, ranking policy 3.1.0, BM25, recall admission, proposal application, or lifecycle semantics. ADR-039 remains **Proposed**. PR #587 / issue #583 remains intentionally **DRAFT / HOLD**.

## Phase A: adapted external evidence

C = canonical LongMemEval_S, P1 = source/session `observed_at`, P2 = P1 plus host-declared question-date `reference_time`.

Result: **NO EFFECT, fully attributed**.

- 23,867 / 23,867 session memories mapped; 122,416 / 122,416 turn memories mapped.
- 0 changed ranking rows and 0 changed gold ranks under P1 or P2.
- canonical C reproduces accepted `f76c441` evidence.
- interpreted self-validity resolves for only 8 session memories and 33 turn memories after anchoring.
- 0 admitted candidates in the ordering-intent audit carry applicability basis `interpreted`.
- the one admitted resolved-window turn is non-gold at rank 132 and the P2 reference time is inside the window, so limit-only semantics correctly does not affirm it.
- future-dated subgroup: 76 questions, 69 scored; still 0 ranking/gold/metric changes.

Conclusion: for #550 interpreted self-validity **demotion efficacy on this external corpus**, the result is an **EVIDENCE GAP**, not a runtime failure. LongMemEval_M escalation for the adapted profile remains unwarranted.

## Phase B: repository-owned natural-language conformance

### Freeze

The 268-turn sample is immutable: 100 random Part R turns plus 168 stratified Part S turns. Part R is the only population-estimating sample.

The reviewed annotation chain is preserved byte-for-byte as v1 -> v2 -> v3 -> v4 -> v5. Maintainer review `5339771805` accepts v5 semantic content as the final source for gold.

Accepted gold is represented by `reference/fixtures/benchmarks/proposition-semantics/gold-v1.json`, an immutable acceptance manifest over frozen `draft-annotations-v5.json`:

- v5 sha256 `bb336e72281b64dbdd090447194a67f0638b820a4adb18f1463d24c77859aec7`
- rubric v5 sha256 `94775c3c6b4f4bcc13f8b3455e7cfda7a90c8dfa54dade0937f89270ca1618ad`
- sample sha256 `b1957ca4ff95c3b8a227b8b75f74327911172305cf770c927d56091e7fedd8d3`
- text-hash-list sha256 `3dceb7cde08abf45af3ea1d4dc12d117c390a3441eed38b3ca2273e04f986b88`
- gold counts: 148 known / 35 ambiguous / 85 unknown.

Direct loading of drafts v1-v5 remains refused. Gold loading verifies the frozen v5 digest before materializing items.

The property-alias table was deliberately frozen **empty before scoring**. No semantic synonym was added after seeing predictions.

### First score

Scored head: `73216bebc596de4876692a8f00d1e3fabaa899f1`.

Workflow run `36434626348`, artifact `10974877443`, artifact zip sha256 `34decf958f7ed1b537241b360cc863eb8904ca27aa220fcf48c876b4975345f9`. The full scoring runner is committed and deterministic; immediate replay was byte-identical.

Part R, 100 random natural turns:

| status | gold | predicted | precision | recall |
| --- | ---: | ---: | ---: | ---: |
| known | 54 | 10 | **0.800** | **0.148** |
| ambiguous | 13 | 62 | 0.210 | **1.000** |
| unknown | 33 | 28 | **1.000** | 0.848 |

Gold-known confusion is the headline defect: 8 known -> known and **46 known -> ambiguous**. Gold-unknown has 28 -> unknown, 3 -> ambiguous, and 2 -> known.

Part R failure counters:

- wrong slot: 8;
- unknown promoted to known: 2;
- temporal aspect mismatch: 4;
- temporal aspect over-classification: 1;
- over-eager single-valued cardinality: 0;
- coexistence-as-replacement: 0.

The dominant defect is therefore **under-recognition / over-ambiguity**, not reckless promotion. The current grammar is conservative but much less capable than the v5 semantic contract.

Strict slot/value conformance is 0 under the frozen empty alias table. Treat that as an exact-label diagnostic, not as semantic synonym precision. Inspection shows both harmless label variation (`worry` vs `tends to worry about`) and real parser defects (`200` as a property, surface scaffolding such as `think of`/`going to`, request text bleeding into values, clipped stems). #597 owns an independently frozen canonicalization method before any semantic re-score.

Temporal-aspect errors are real and isolated to #598. #598 is memory-side and is distinct from query-side #585.

### Follow-ons

- #596: raise natural-data proposition recognition without weakening abstention.
- #597: canonicalize proposition slot/value boundaries before semantic re-score; no post-hoc alias fitting.
- #598: calibrate write-time temporal aspect on natural turns.

#598 is on the temporal RC dependency path before redesigned #583. #596/#597 are high-priority interpreter-quality limitations; their dominant fail-safe behavior does not create authority, so they are not automatically promoted to RC blockers unless later evidence requires it.

## #594 disposition

**QUALIFIED** under the issue's own stop line:

1. Phase A is defensible adapted external evidence with an explicit demotion-efficacy EVIDENCE GAP.
2. Phase B reached independently reviewed, immutable accepted gold and deterministic scoring.
3. Defects discovered by scoring are preserved as defects and moved into bounded remediation issues rather than changing gold or fitting the evaluator.

The next RC step is the canonical dashboard refresh, then #585 query-intent span calibration. See `reports/benchmarks/dashboard/current.md` and `docs/64-current-governance-and-benchmark-dashboard.md`.
