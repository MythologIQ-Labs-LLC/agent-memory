# #732 oracle-ceiling diagnostic v1 (diagnostic, not a score)

**Protocol:** `currentness-oracle-ceiling-732-v1` · **kind:** `diagnostic_not_score` · **authority_effect:** `none`
**Runner:** `reference/run_currentness_oracle_ceiling.py` (tests: `reference/tests/test_currentness_oracle_ceiling.py`)
**Executed on:** `main` `5309dc4`, Runtime Baseline v6 unchanged (equivalence checker PASS), assertion filter 6.1.0, ranking 3.4.0.
**Inputs:** the frozen #732 *measurement* corpus (`freeze/`, corpus `cf2e7646c4ba…`, variants `72588822196e…`): 316 base cases + 484 scored variants.
**Credentials / egress / model calls:** none. **Holdout:** none authored, none read.

This record does **not** re-score, re-threshold or replace `measurement/measurement-v1.json` (the
bound FAIL stands), does **not** accept the extractor path, and is **not** R6 evidence. The
measurement corpus is already spent for measurement; here it is used as a *development*
diagnostic only. The future R6 holdout must remain independent of it (K8).

## Question

`measurement-v1` stops 197/212 positives at S3 (no write-time relation). That is consistent with
two competing explanations:

1. **Write-interpretation only:** with correct typed evidence, everything downstream works.
2. **Downstream defects too:** candidate generation, typed relation/identity, guards, admission
   or ranking would still fail even with a perfect extractor, so R6 would burn its single-use
   holdout regardless of the extractor.

Only (1) justifies spending the one subscription smoke and the one holdout on v6 as published.

## Method

The unchanged `run_currentness_generalization.run_record` executes each record with an oracle
`PropositionExtractor` attached through the public `AgentMemory.open(..., proposition_extractor=)`.
The oracle **never reads write text**: its typed record comes from corpus metadata (family,
variant type, write role) with placeholder subject/attribute/value tokens. Its link to the older
fact is returned only if the runtime itself offered the older fact as a candidate.

| Mode | Newer write's typed record |
|---|---|
| `gold` | `change`; the flag a correct interpreter sets for N1–N6/N11/N12 and for the `hedge`/`attribution`/`conditional`/`coexistent` variants; structural controls (N7–N10, N13, `change_*`, `dispute`) get a clean `change` |
| `flag_blind` | always a clean `change` — a worst-case extractor that misses every semantic flag |
| `slot_drift` | `gold`, plus a correct link, but equivalent subject/attribute wording (`the oracle subject` / `current oracle attribute`) |

## Results (denominators exact; same 212 positive, 104 negative, 164 invariance, 320 must-change)

| Metric | extractor off (measurement-v1, reproduced) | `gold` | `flag_blind` | `slot_drift` |
|---|---|---|---|---|
| Positive engagement | 0/212 | **195/212 (0.920)** | 195/212 | **0/212** |
| Structural false engagement (N7–N10, N13) | 0 | 0 | 0 | 0 |
| Non-structural false engagement (N1–N6, N11, N12) | 0 | 0 | **44/64** | 0 |
| M-flip (must-change refrain) | 320/320 | 320/320 | 209/320 | 320/320 |
| M-inv | 164/164 (vacuous) | 159/164 | 159/164 | 164/164 (vacuous) |
| M-attr | 0 | 0 | 0 | 0 |
| G5 verdict *if it were scored* | FAIL | PASS | FAIL | FAIL |

Per-family positive recall under `gold`: P1, P2, P5, P8, R1–R6 = 1.000; P10, P11, P12 = 0.917;
P3, P4, P6, P9, P13 = 0.833; R7 = 0.875; P7 = 0.750 (three S1). Every family ≥ 0.60.

`flag_blind` non-structural false engagements by family: N1 6/8, N2 8/8, N3 6/8, **N4 0/8**,
N5 7/8, N6 8/8, N11 5/8, N12 4/8. Must-change variants engaged: attribution 34/40, conditional
38/40, coexistent 39/40, **hedge 0/40**, change_actor/scope/source_ref and dispute 0/40 each.

Baseline reproduction (`baseline-reproduction-v6-extractor-off.json`): all 800 rows and all
scores of `measurement-v1` reproduce byte-identically on v6 with the extractor off.

## Attribution of every residual failure

| Stage (general capability) | `gold` positives | Notes |
|---|---|---|
| S1/S2 retrieval admission | 15 | identical set to extractor-off; independent of typed evidence |
| S4 lexical ineligibility false refusal | 2 | P9-07 `I think in Celsius` → interpreter hedge scan; P11-09 subjectless report → `untrusted_self_claim` |
| Candidate generation | 0 | 1 positive's older fact was not offered as a candidate (seen as S3 under `slot_drift`); under `gold` the shared typed slot still related it |
| Guards G1–G13 | 0 false refusals | structural guards refuse every structural control in every mode |
| Ranking (S6) | 0 | |

M-inv mismatches (5, all `subject_wording` variants) are admission differences (S2) and one
S4 `relation_not_state_change` refusal (P4-03 variant), not ranking differences.

## Diagnosis

1. **Competing explanation (1) is supported for the read path.** Given correct, consistently
   named typed evidence, v6's guarded read-time applicability meets every G5 PASS criterion on
   the measurement corpus. Guards, labelling and ranking are not the bottleneck.
2. **New, general deficit — proposition identity across independent extractions.** R3
   `link_confirmed` requires an *identical normalized typed slot* when the older fact is typed.
   With equivalent but differently worded names, engagement collapses to 0/212 even with correct
   flags and a correct link. The frozen extractor sees candidate *texts*, never their typed
   records, so it cannot reuse the older fact's subject/attribute wording. The real slot-drift
   rate of the frozen extractor is **unmeasured** (not zero); this diagnostic shows engagement is
   all-or-nothing on it.
3. **Safety is single-sourced for six semantic control families.** Apart from hedging (the
   interpreter's lexical hedge scan) and the structural guards, the read path relies entirely on
   extractor flags for quotation, forwarding, sarcasm, conditionals, negation and multi-value /
   coexistence. An extractor that misses those flags produces up to 44/64 false engagements.
4. **The lexical scans cut both ways.** They are the only flag-blind hedge defence (N4 0/8) and
   also cause the two positive false refusals. Removing or extending them case-by-case is out of
   bounds (no G12 cue-list expansion).

Unclassified: whether real extractor errors are dominated by slot drift, missing flags, false
flags or declines; this needs the frozen extractor's output and is blocked on the provider gate.

## Mechanism hypothesis (proposed, not implemented) and adversarial challenge

**H-ID1. Write-time identity resolution against the candidate's typed record.** When a write
carries an extracted link `updates_fact_uuid` to a candidate the runtime itself offered, and the
candidate is typed with a different slot, accept identity only when independent, typed,
non-lexical corroboration holds: the newer `replaces_value` normalizes equal to the candidate's
typed `value`, the actor/source/scope guards pass, and neither side is `multi`. Persist the
resolved identity as an explicit, versioned alias edge (`typed_link_resolved`) with
`authority_effect: none`; the read path keeps every existing guard.

Why it generalizes: it uses the system's own persisted typed evidence (value equality on a
linked, guard-compatible pair), not words, domains, entities or benchmark templates.

Adversarial challenge:
- *Same old value, different property* (port 8080 used by two settings): the link must still
  name that candidate and both slots must be `single`; residual risk remains when an extractor
  links the wrong candidate → test with independently authored cross-property collisions.
- *Extractor omits `replaces_value`* (common for bare restatements): H-ID1 then refuses —
  recall loss, not unsafety; measure separately.
- *Alternative H-ID2 (send candidates' typed slots to the extractor)* changes the frozen prompt
  and input contract → requires a new extractor version and invalidates the W5 freeze; H-ID1
  does not touch the prompt.
- *Alternative H-ID3 (fuzzy slot similarity)* is rejected: it is a lexical heuristic with no
  typed corroboration.
- Any of these is a protected-runtime change → requires a gated plan, a Runtime Baseline
  successor declaration (the v7 identity must also be serialized against #644 / PR #731), and
  must not be tuned on the R6 holdout.

**Safety hypothesis H-SAFE1** (finding 3) is recorded for design only: require positive typed
assertion evidence rather than treating absent flags as assertive. It changes the extractor
contract and is not proposed for this cycle.

## Decision

**HOLD** any runtime change. The diagnostic changes the risk picture for R6, not the gates:
R6 on published v6 may engage near the `gold` ceiling only if the frozen extractor names slots
identically across independent calls. Whether to (a) run the single smoke/holdout on v6 as
frozen, or (b) first gate H-ID1 as a v7 candidate, is an owner/governance decision recorded on
#732.
