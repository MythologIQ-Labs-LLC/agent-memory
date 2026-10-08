# #732 oracle-ceiling diagnostic v1 (diagnostic, not a score)

**Protocol:** `currentness-oracle-ceiling-732-v1` · **kind:** `diagnostic_not_score` · **authority_effect:** `none`
**Runner:** `reference/run_currentness_oracle_ceiling.py` (tests: `reference/tests/test_currentness_oracle_ceiling.py`)
**Executed on:** `main` `5309dc4` (first run) and re-run on the PR branch head after review fixes (identical rows), Runtime Baseline v6 unchanged (equivalence checker PASS), assertion filter 6.1.0, ranking 3.4.0.
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
The oracle does not interpret write text: its typed record comes from corpus metadata (family,
variant type, the gold `older_write`/`newer_write` role indices) with placeholder
subject/attribute/value tokens; answers are looked up by exact write text. Its link to the older
fact is returned only if the runtime itself offered the older fact as a candidate. Because every
record shares one placeholder slot, a `typed_slot` relation can still form when candidate
generation missed the older fact; such records are reported separately.

**Scope of the ceiling.** It models only the regime where *both* facts were extracted. An older
fact with no typed record (written with the extractor off, or declined; there is no retroactive
extraction) goes through text-based `replaces_value_confirms`, which placeholder values cannot
exercise. That regime is not modelled.

| Mode | Newer write's typed record |
|---|---|
| `gold` | `change`; the flag a correct interpreter sets for N1–N6/N11/N12 and for the `hedge`/`attribution`/`conditional`/`coexistent` variants; structural controls (N7–N10, N13, `change_*`, `dispute`) get a clean `change` |
| `flag_blind` | always a clean `change` — a worst-case extractor that misses every semantic flag |
| `slot_drift` | `gold`, plus a correct link, but equivalent subject/attribute wording (`the oracle subject` / `current oracle attribute`) |

## Results (denominators exact; same 212 positive, 104 negative, 164 invariance, 320 must-change)

| Metric | extractor off (measurement-v1, reproduced) | `gold` | `flag_blind` | `slot_drift` |
|---|---|---|---|---|
| Positive engagement | 0/212 | **195/212** | 195/212 | **0/212** (by construction) |
| …with the older fact offered as a candidate | — | **194/212** | 194/212 | 0/212 |
| Structural false engagement (N7–N10, N13) | 0 | 0 | 0 | 0 |
| Non-structural false engagement (N1–N6, N11, N12) | 0 | 0 | **44/64** | 0 |
| M-flip (must-change refrain) | 320/320 | 320/320 | 209/320 | 320/320 |
| M-inv | 164/164 (vacuous) | 159/164 | 159/164 | 164/164 (vacuous) |
| M-attr | 0 | 0 | 0 | 0 |

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
| Candidate generation | 1 hidden | the older fact was not offered as a candidate in 69/800 records (3 base positives: P7-02, P10-07, P9-06), mostly masked by S1/S2 attributed first. P9-06 and two variants (P10-08-subject_wording, R6-05-subject_wording) reach S7 under `gold` only through the shared placeholder slot, which a real extractor could not reproduce, so the realistic ceiling is **194/212**. The same artefact affects one negative: under `flag_blind`, N2-05 engages without its older fact offered, so 43 of the 44/64 flag-blind non-structural false engagements had the older fact offered |
| Guards G1–G13 | 0 false refusals | |
| Ranking (S6) | 0 | |

M-inv mismatches (5, all `subject_wording` variants) are admission differences (S2) and one
S4 `relation_not_state_change` refusal (P4-03 variant), not ranking differences.

Structural controls are **not** all refused by guards. N7, N8 and most of N9 are refused by G8/G9.
N10 and N13 (8/8 each) stop at admission (S2 `newer_not_admitted`) in every mode, and so do all
`change_scope` and `dispute` variants (40/40 each; part of the 90 S2 must-change rows). Under `slot_drift`, N7–N9
stop at S4 before any guard. Zero structural false engagements is therefore a property of
admission plus guards together, not of the guards alone.

## Diagnosis

1. **Competing explanation (1) is supported for the read path.** Given correct, consistently
   named typed evidence, v6's guarded read-time applicability engages 194/212 positives with
   the older fact genuinely offered, no false engagement, and no must-change flip. Guards,
   labelling and ranking are not the bottleneck. This is not a gate result: the measurement
   corpus is spent, no verdict is emitted from it, and any successor mechanism must be judged
   on a fresh holdout, never on this corpus.
2. **New, general deficit — proposition identity across independent extractions.** R3
   `link_confirmed` requires an *identical normalized typed slot* when the older fact is typed.
   With equivalent but differently worded names, engagement collapses to 0/212 even with correct
   flags and a correct link. The frozen extractor sees candidate *texts*, never their typed
   records, so it cannot reuse the older fact's subject/attribute wording. The real slot-drift
   rate of the frozen extractor is **unmeasured** (not zero); this diagnostic shows engagement is
   all-or-nothing on it. The `slot_drift` 0/212 is a fact about the code made visible, not a
   measured rate: every record is given 100% drift and a typed older fact.
3. **Once a write is admitted, safety for the semantic control families rests on extractor flags alone.**
   In every mode, 11/64 non-structural negatives stop at admission (S2 `newer_not_admitted`:
   N1 1, N3 1, N4 1, N5 1, N11 3, N12 4) before any flag matters. Under `gold`, the 0/64 is therefore
   53 S4 flag refusals plus 11 admission refusals. Of the admitted negatives, only hedging (N4,
   through the interpreter's lexical hedge scan) has a defence other than extractor flags. The rest
   (N1, N2, N3, N5, N6, N11, N12: quotation, forwarding, sarcasm, conditionals, negation, multi-value /
   coexistence) rely entirely on flags. Under `flag_blind`, 44/64 engage. Of the 20 that do not,
   11 stop at S2 and 9 at S4 (N4 7, N1-02 1, N3-07 1).
4. **The lexical scans cut both ways.** They are the only flag-blind hedge defence (N4 0/8) and
   also cause the two positive false refusals. Removing or extending them case-by-case is out of
   bounds (no G12 cue-list expansion).

Unclassified: whether real extractor errors are dominated by slot drift, missing flags, false
flags or declines; this needs the frozen extractor's output and is blocked on the provider gate.

## Rejected hypothesis H-ID1 (circular) and adversarial challenge

This section records a hypothesis that was examined and **rejected**. It is not a proposal or
a remedy, and nothing here is a design input except the reasons for rejection.

**H-ID1 (rejected). Write-time identity resolution against the candidate's typed record.** When a write
carries an extracted link `updates_fact_uuid` to a candidate the runtime itself offered, and the
candidate is typed with a different slot, accept identity only when independent, typed,
non-lexical corroboration holds: the newer `replaces_value` normalizes equal to the candidate's
typed `value`, the actor/source/scope guards pass, and neither side is `multi`. Persist the
resolved identity as an explicit, versioned alias edge (`typed_link_resolved`) with
`authority_effect: none`; the read path keeps every existing guard.

Its apparent appeal was that it uses typed evidence rather than words or templates. That appeal
does not survive challenge: the "typed evidence" is produced by the same extractor call that it
would corroborate.

Adversarial challenge (independent review, recorded VETO on the first draft of this section):
- **Circular on this diagnostic.** `slot_drift` keeps `replaces_value` byte-identical to the
  older typed `value`, so H-ID1 would recover 100% here by construction. This diagnostic cannot
  support H-ID1.
- **Value drift.** Real extractions drift on values as on slots (`Django 4.2` / `4.2`,
  `8080` / `port 8080`); that breaks H-ID1 the way slot wording breaks R3.
- **Not independent corroboration.** The link and `replaces_value` come from the same extractor
  call, which sees the candidate text and can copy the value; equality is near-automatic
  whenever it links, rightly or wrongly.
- **Conflicts with the attempt-2 T2 decision** in `docs/plan-732-remediation.md`, which forbade
  confirming a link to a differently-slotted typed fact through the value branch. H-ID1
  reintroduces that path through the typed value.
- Counterexamples: cross-subject collisions with passing guards ("Team A uses Postgres" /
  "Team B moved off Postgres"); low-entropy values (`true`, `on`, `UTC`, `1`, `admin`; no
  `TRIVIAL_VALUES` analogue); `cardinality: null` passing "neither side multi"; a persisted alias
  edge merging slots transitively into later `typed_slot` matches.

**Status of H-ID1: rejected as circular; not proposed for implementation or further testing.**
The same holds for any same-extractor link plus `replaces_value` corroboration, especially across
subjects and for low-entropy values. Proposition identity across
independent extractions remains an open deficit with no qualified mechanism. Any candidate
needs evidence that does not share the extractor call it corroborates, and must be tested on
independently authored identity cases (value drift, cross-subject collisions, low-entropy values)
rather than on this corpus.

Further reasons for rejection, and constraints on any successor:
- *Same old value, different property* (port 8080 used by two settings): a same-extractor value
  match cannot tell the two properties apart, so H-ID1 can merge distinct slots whenever the
  extractor links the wrong candidate.
- *Alternative H-ID2 (send candidates' typed slots to the extractor)* changes the frozen prompt
  and input contract, so it would need a new extractor version and would invalidate the W5
  freeze. It is listed only as a constraint on #757 design work, not evaluated here.
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
R6 on published v6 can approach the ~194/212 ceiling only if the frozen extractor names slots
identically across independent calls, which is unmeasured. Whether to run the single
smoke/holdout on v6 as frozen, or first design a non-circular identity mechanism (a v7
candidate, serialized against #644 / PR #731), was put to the owner on #732.

**Owner decision (2026-10-08): option (b).** Cross-write proposition identity is designed before the
single-use R6 holdout is spent on v6. The bounded design work is tracked in #757. This choice
authorizes no v7 runtime implementation and no evaluator tuning. The `measurement-v1` FAIL (0/212)
stands, and #732 stays open.
