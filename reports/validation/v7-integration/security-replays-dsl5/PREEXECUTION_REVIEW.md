Reviewed commit: 4d807b89bd8fb6cc99c16425c2330c94a3b82dfa

# Pre-execution review of the DSL/5 successor security replays (`*-v4`, `evidence-reference-authorization-v2`)

The independent reviewer's text is reproduced below as returned. The integrator's response follows it in a separate
section.

**Role and limits.** Independent and read-only. Nothing was executed: no DSL/5 runner, no `run_case`, no ad-hoc reproduction. Inputs read: the four successor fixtures, `author_fixtures_dsl5.py`, the predecessors, runners DSL/1–3 and 5, `docs/44-public-api-contract.md` and `docs/META_LEDGER.md`. I also read some adapter and surface code, but only to judge whether a token in a fixture could appear for a legitimate reason. No verdict below depends on what the runtime does.

**Tree drift.** HEAD moved to `372b79d9` while I was reviewing. That commit adds only `reference/tests/test_v7_review_findings.py` and a log. None of the reviewed inputs differs from `4d807b89`.

**Integrity.** Every `contract_sources[].sha256_at_base` matches at `6a12e1cd`. Every `superseded_fixture.sha256` matches. Every quoted clause is verbatim in its source once `[...]` elisions are allowed for.

| fixture | cases | expect |
|---|---|---|
| cross-scope-write-authority-denial-v4 | 15 | 135 |
| deleted-lineage-generations-and-restart-v4 | 10 | 79 |
| public-tombstone-redaction-and-observer-separation-v4 | 8 | 34 |
| evidence-reference-authorization-v2 | 13 | 124 |

## Findings

**F-1 — W4 / W4b: the identity-change refusal — NOT DERIVABLE.**
- **Observables:** `sup_rem_raised`, `sup_cor_raised`, `sup_disp_raised`, `sup_forget_raised` and `complete_raised` are expected to equal `ValueError`. `sup_rem_committed`, `sup_cor_committed`, `sup_disp`, `sup_forget` and `complete` are expected to be `false`.
- **Clause:** FIB says overrides "may restate or narrow that identity, never change it". On this profile, it says a `scope_distinct_v1` store "answers with per-project keys". It fixes a refusal form only for the malformed override (the 1.8.0 message, "checked first").
- **Why this fails:** the clause names no exception type and no refusal shape for an identity change. "Answers with per-project keys" can also be read as acting in B's own namespace, in which case `committed` would be `true`. The integration entry in META_LEDGER lists "Facade W4 refusal under store-open 1.0.0" as an open owner decision. The generator's docstring says "refused with ValueError", but that wording is not in docs/44.
- **What is derivable:** "never change it" plus SD decide the A-side observables: `head`, `valid`, `owner_recall`, `tombstones`, `k2_head == memory:k2`. They also decide `bad_*` and `bad_*_message`.
- **Correction:** move the ten observables above to `record`, and keep the A-side checks and the malformed-override checks expected. Alternatively, get the owner's decision first, write it into docs/44, and cite it. Also record `sup_rem_refusal` and `sup_rem_before`: they were dropped from `expect` but never added to `record`.

**F-2 — W1 and W7: `other_history_unknown` removed — WEAKENED.**
- The -v3 probe compared B's whole folded `history` payload with that of an id nobody wrote.
- Its replacement, `other_history`, checks only the current label, the version, `tombstoned` and the event types. A uuid, text or key of A's that leaked into B's history payload would pass.
- **Correction:** add `history_mentions` as project:b on `memory:k`, expecting `[]`:
  - W1 tokens: `["memory:k","dawn","project:a"]`
  - W7 tokens: `["memory:k","memory:k@2","dawn","noon","project:a"]`
- **Stronger alternative:** in the same case, have B write `memory:j` with the same text, then use `history_same_as` (`ref memory:k`, `other memory:j`, substituting B's labels). That restores "byte-identical to a key A never wrote".

**F-3 — Rule M1 applied beyond its premise — WEAKENED.**
- **M1's premise:** "the caller's own receipt carries its own versions". A creation's receipt carries only `v0` and `v1` (VERSIONS; `b1_after == v1` is expected).
- **Real cross-scope signals that were dropped:**
  - W3 `b1_mentions` lost `v2`, which is A's live version.
  - W8 `b1_mentions` lost `v3`, which is A's tombstoned count.
- **Operations that do not commit**, so M1 does not apply:
  - W7c `a_disp` is a refused dispute. Dropping `v1` is defensible, because it may be A's own re-created head. Dropping `v2` is not: `v2` is A's former count. W7c-control, in the same fixture, expects `v2` absent from the identical refusal (FORMER: "neither moves or reads the live generation"; VERSIONS: "the former generation's count never reaches the new one").
  - W8b `parked_b` is parked, not committed, and B reads `v0`. Its `v1` was dropped for no reason.
- **Correction:** restore `v2` in W3, `v3` in W8, `v2` in W7c and `v1` in W8b. False-fail risk is low: no string constant containing `v2` or `v3` exists in `api/`, `runtime/adapter.py` or the policy and receipt modules.
- **Already fine:** dropping `v1` in R6b is OK, because whether `a_back` commits is recorded, not expected.

**F-4 — A's newly committed re-creations are missing from B-side scans — WEAKENED.**
- Now that A's re-creation commits, its identifiers are new disclosure signals, but they were not added:
  - L3 `other_mentions` (B's historical recall) needs `memory:f@3` and `midnight`. L3 `other_history_mentions` needs `memory:f@3`.
  - W7c `other_history_mentions` needs `memory:k@2`.
  - W8 needs `memory:k@3`.
  - R5 needs `memory:t@2`.
- **Correction:** add these tokens. Their texts are already present, except `midnight` in L3 `other_mentions`.

**F-5 — The cross-scope re-creation scenario is lost — WEAKENED, with no contract reason.**
- **What -v3 tested:** in W7c, W8, L3, R3, R5, R6b and E6/E6a/E6r, B re-created A's deleted id. That is the #776/#777 property: the former owner's answers, counters, as-of barriers and citation taint do not depend on another scope's generation of the same id.
- **What -v4 tests:** through the facade, A and B now hold unrelated memories, so these cases test only own-namespace behaviour plus SD.
- **The clauses still apply:** FORMER says "the same whether or not another scope has since re-created the id", and VERSIONS still holds. Both apply at the canonical layer, which the module surface still serves "exactly as contract 1.8.0 states". DSL/5 can reach that layer (`commit_with_episode` with `ref_scope`), but rule H1 was applied only to W1, W2 and W6.
- **Dispositions that are now wrong:**
  - R3 and E6* are labelled "carried forward unchanged: observables do not depend on the store profile".
  - The E6 invariant still says "B may re-create A's deleted id", but no step does that any more.
  - L4's `other_at_*` probes now read B's own memory, so the cross-scope as-of gate is not exercised.
- **Correction:** add host-layer variants of W7c, W8, L3 and E6. In each, B re-creates A's deleted canonical id with `commit_with_episode` and `ref_scope: project:a` (expect `committed: true` and v0→v1, by OPEN and VERSIONS). Then carry over the -v3 A-side expectations:
  - `a_rem`/`a_back` read `target_unavailable` (GATE_W1);
  - `a_disp` and `a_del` read `already_deleted`;
  - `a_forget` reads `fact_not_found`;
  - in L3, `head` is B's generation;
  - in E6, `bf` stays admitted.

  Also add an L4 `version_in_effect` probe as project:b with `ref_scope: project:a` at `gen3`, expecting `null`. Then fix the R3 and E6 dispositions and the E6 invariant.

**F-6 — W2 (carried forward), with W2h — WEAKENED, and partly VACUOUS.**
- **Vacuous part:** W2's four `op_same_as_unknown` probes now compare B's own never-written key with `memory:never`. They would hold even if the canonical gate were removed. They test only SD.
- **What W2h covers:** it restores pruning only, and checks it by refusal token rather than by byte-identity.
- **What is left unexercised:** the canonical-layer gate for supersession (`correct`), permanent deletion and dispute by logical reference. W7b `bdf` covers only fact-level dispute, and only as `committed: false`.
- **Correction:**
  - Extend the DSL/5 host steps to `correct`, `dispute` and permanent deletion with `ref_scope`, or record the gap as an explicit residual.
  - In W2h, add a control `delete_version` naming (project:a, `memory:never`) with an `@literal:` fact, and an `op_same_as` probe comparing the two results (GATE_W2: "byte-identical to the result for an id nobody wrote").
  - Correct W2's disposition text.

**F-7 — W1h and W2h — OK-with-note.**
- Both are non-vacuous: if the gate were broken, the write would commit.
- **W2h `h_refusal == fact_not_found`:** this follows from l.206, "The decision is the adapter's (… `_delete_refusal` …)", rather than from GATE_W2's facade list. Cite l.206 as well.
- **W1h `h_mentions`:** it is not traced to any clause. The DSL/5 generator dropped -v3's assertion that every expected observable is clause-traced. Add `h_mentions` to GATE_W1's observables. R4 `kept`, carried over from -v3, is likewise untraced.
- **Parity with -v3 W1:**
  - add `other_recall` as project:b, expecting `[]`;
  - note that `state_snapshot` (GATE_W1: v0) is not captured, because the runner's `commit_with_episode` keeps only before and after.
- Leaving `project:a` out of `h_mentions` is correct, because B supplied A's canonical key itself.

**F-8 — W8b `other_history` and `other_history_unknown` recorded; L3 `owner_history` recorded — over-recorded.**
- **W8b:** rule R1 justifies recording the event list only. `current: null`, `state_version: 0` and `tombstoned: false` are decided: a parked proposal commits nothing, and the W8 invariant says it "reports v0". R6b, in the same generation, already uses the right split: `history_summary` expected, `history` recorded.
- **Correction (W8b):** add `history_summary` as project:b, expecting `{current: null, state_version: 0, tombstoned: false}`, plus a `history_mentions` probe with A's tokens.
- **L3 (minor):** `tombstoned: true` is decided, while `state_version` correctly stays recorded because of `a_cor`.

**F-9 — Runner: mention scans map keys by the handle open at probe time — OK-with-note.**
- `publicize` maps canonical keys relative to the handle that is open when the probe runs, not the operation's actor.
- L3 `a_mentions` and R6b `parked_mentions` run while the other project's handle is open, so the actor's own key reads as `<project>key`.
- This is harmless with the current tokens. A future `project:*` token on such a probe would false-fail.

## Checked and found correct

- **Creation receipts:** v0→v1 for W1 `b1_*`, W3 `b1_after`, R5 `b1_*`, L3 `a_rem_after` and E6 `recreated`, by VERSIONS. A fresh id reads 0, so the same rule covers it.
- **Former owner on its own deleted id:** `fact_not_found` at logical-reference level for W3 `b4` and L3 `a_disp`. `already_deleted` at fact level for L3 `a_disp_fact` and W7c `a_disp` and `a_del`. Both follow FORMER.
- **Owner re-creating its own deleted id is admitted:** W7c `a_rem`, W8 `a_back`, L3 `a_rem`, R5 `a_back`, L4 `b_back`, by OPEN. W7c `a_forget == true` follows, because A then holds the live head.
- **Recorded under R1, correctly:** W3 `b2` and L3 `a_cor` (each corrects to the value already current), and R6b `a_back_committed` (no clause decides re-writing a deleted value).
- **W4 malformed override:** the message and its "checked first" order are derivable from FIB.
- **W6:** `ref_scope` restores the -v3 semantics.
- **W8:** `owner_history` with 4 events matches the L2 precedent.
- **Carried-forward spot checks:** W5 `other_view_of_k`, W7b `other_history_unknown`, R2 (6 probes), L6 `other_unknown`, L1 and L5 `kept_mentions` positive controls, and E1–E5 and E6b.
  - They stay byte-comparable after key mapping. B's canonical `memory:k` reads as `memory:k` and is replaced by `memory:never`; a leaked foreign key would read `<project:a>memory:k` and differ.
  - On scope_distinct they test key binding rather than the read gate. W7b relies on the same premise -v3 expected: refused attempts leave no event in B's view.
  - The fact-level citation behaviour in E1–E5 and E6b does not depend on the store profile.

## Verdict

Do not execute yet. F-1 to F-6 should go into this generation before its first execution, because no fixture is edited after that. F-1 is either a change to `record` or an owner decision written into docs/44. F-2 to F-4 are token and probe additions. F-5 and F-6 need new host-layer cases, plus host steps for `correct`, `dispute` and permanent deletion, or a written residual if those steps are not added. The changes that weaken the predecessor (F-2, F-3, F-5, F-6) conflict with the stop line "no expectation weakened to obtain PASS", even if no one intended that.

---

# Integrator's response

Every change below was applied in `author_fixtures_dsl5.py` before any execution. The fixtures were re-authored with
`base_commit` `9eb72391`, and the contract sources are hashed there. No case has been executed.

| Finding | Response |
|---|---|
| F-1 | **Second alternative taken: written into docs/44 and cited.** docs/44 (at `9eb72391`) now states that any override changing the handle's tenant, project or isolation domains raises `ValueError` (`facade proposal may not override host-bound scope identity`) before any target is resolved, for every operation. It is marked as a v7 integration direction whose adoption for the published contract is an open owner decision. The FIB clause quotes it, and the refusal type and message are expected. `sup_rem_refusal` and `sup_rem_before` are recorded. |
| F-2 | B-side `history_mentions` added to W1 and W7 with the tokens given, expected `[]`. The stronger `history_same_as` alternative was not taken: an extra B memory would change W1's `other_recall` expectation. |
| F-3 | Restored `v2` in W3, `v3` in W8, `v2` in W7c (keeping `v1` dropped) and `v1` in W8b. |
| F-4 | Added `memory:f@3` and `midnight` to L3 `other_mentions`, `memory:f@3` to L3 `other_history_mentions`, `memory:k@2` to W7c, `memory:k@3` to W8 and `memory:t@2` to R5. |
| F-5 | **Added host-layer variants built from the frozen cases:** W7c-h, W8-h, L3-h, E6-h, E6a-h and E6r-h. In each, B re-creates A's deleted canonical id with `commit_with_episode`/`ref_scope`, and B's own deletion of it uses `delete_version`/`ref_scope`. Each carries the -v3/-v1 A-side expectations and cites OPEN and FORMER. B-side facade probes, which can no longer name that memory, are dropped, and the canonical head is probed instead. Also added L4 `other_at_gen3_canonical` (project:b, `ref_scope` project:a, expected `null`). The R3, E6, E6a and E6r dispositions and the E6 invariant are corrected. |
| F-6 | **Residual recorded rather than new host steps.** Host-layer `correct`, permanent deletion and dispute by reference are stated as a residual in every successor fixture (`residuals`), covered by the tenant-wide unit suites. W2h gains the unknown-id control: the same host step naming `memory:never` must read `fact_not_found` too. Both refusals are compared by token, because a full-result byte comparison of the host `GovernedDeleteResult` is not a DSL probe. W2's disposition is corrected. |
| F-7 | W2h cites docs/44 l.206 (`ADAPTER`). `h_mentions` is traced to GATE_W1. W1h gains `other_recall` as project:b, expected `[]`. The missing `state_snapshot` is noted in W1h's disposition. The author script again asserts that every expected observable is clause-traced or a labelled control. R4 `kept` is a labelled control, as in -v3. |
| F-8 | W8b: `history_summary` as project:b is expected `{current: null, state_version: 0, tombstoned: false}`, `history_mentions` with A's tokens is expected `[]`, and the full history is still recorded. L3: not changed, because the DSL has no tombstoned-only probe; `owner_history` stays recorded. |
| F-9 | Noted. No current token is affected. |

**Resulting generation:**

| Fixture | Cases | Changed or new |
|---|---|---|
| `cross-scope-write-authority-denial-v4` | 17 | 14 |
| `deleted-lineage-generations-and-restart-v4` | 11 | 3 |
| `public-tombstone-redaction-and-observer-separation-v4` | 8 | 3 |
| `evidence-reference-authorization-v2` | 16 | 6 |
