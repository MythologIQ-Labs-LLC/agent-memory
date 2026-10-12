# Successor-resolution corpus: Kesselwand Mountain Rescue (v8/nlsucc)

## Purpose
Measures whether a memory system, from the natural-language question alone, can identify which stored version is the "later value" a predecessor question measures from (successor resolution), and how often it should refuse because the reference is ambiguous, absent or invisible.

## Domain
Fictional alpine mountain rescue team (tenant `kesselwand-mrt`, project `ops-handbook`). All names, suppliers, products and people are invented.

## Memories (18; 42 events, 41 non-delete)
- 5 versions: `radio-primary` (VHF4 -> VHF7 -> TG-31 -> TG-35 -> TG-38)
- 4 versions: `heli-provider` (Alpenflug -> Bergair -> Alpenflug -> Nordlicht), the A->B->A->C chain
- 3 versions: `schneekar-fuel`, `casualty-stretcher`, `training-night`, `rope-inspection` (6 months corrected to 3 months, then updated to 2 months)
- 2 versions: `dog-radio`, `rotstein-fuel`, `weekday-shift`, `weekend-shift`, `avalanche-transceiver`, `callout-alerting`, `kit-check`
- Deleted after update: `hollenzahn-staging`
- Never changed: `medical-director`, `glacier-rule`
- Invisible: `radio-drill` (project `regional-drill`, mentions TG-38 -> TG-40), `heli-provider-sulztal` (tenant `sulztal-mrt`, Nordlicht -> Bergair)

Wrong-subject traps (shared vocabulary and values): main radio vs dog-unit radio (VHF 7, TG-35, "summer 2026 re-banding"); Rotstein vs Schneekar hut fuel (Huber and Kramer, in opposite order); weekday vs weekend standby (07:00); training night vs kit check (Tuesday, Wednesday; "rota" phrases).

## Queries (35)
29 predecessor questions: implicit latest (2), latest by name (2), older by name (2), time phrase (3), paraphrase (5), wrong-subject traps resolvable by a named subject (4), ambiguous (5: repeated value in one chain, value shared by two memories x2, unnamed subject x2), no history (3: first value, corrected predecessor, never changed), deleted (1), other project (1). Plus 6 non-predecessor (4 current, 1 timeless, 1 historical).

## Annotation conventions
- `successor` is non-null only when `resolution` is `unique`; for `no_history` the referenced value may be identifiable but there is no valid earlier value, so it is null.
- Predecessor grading: answer (predecessor) 3, successor 2, other versions of the same chain 1, other memories 0. The corrected-away rope value (6 months) is graded 0 everywhere.
- Prohibited items (deleted, other project, other tenant) are graded 0 in every case and listed in `prohibited` for all cases.
- `stale` on current cases lists every superseded visible event across the corpus (22 ids); empty for historical/timeless cases.
- Ambiguous, no-history, deleted and other-project cases have `safe_answer_exists: false`, empty `critical_groups`, and no eligible item graded above 1.
- Judgement calls: Q12/Q26 are marked ambiguous although one reading has no predecessor; a careful answerer should still ask which subject is meant. Q04 is ambiguous for the same reason within one chain.

## Isolation statement
Authored blind to the system under test. I did not read, list or search anything under /home/user/agent-memory or /tmp/claude-0 other than writing these outputs into /tmp/claude-0/v8/nlsucc/. No git or filesystem search was run; the only shell commands were `mkdir -p` and `python3 -c` validation/hashing of these files.
