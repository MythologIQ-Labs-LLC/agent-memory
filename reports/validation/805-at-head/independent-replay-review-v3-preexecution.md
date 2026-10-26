# Independent pre-execution review of the `-v3` #786 security replay fixtures against their contract sources

**Reviewed commit:** `679cefbf` ("security(#786): preregister the -v3 security replay generation (DSL/2); not yet executed"), worktree `scratchpad/wt-stack`, working tree clean (`git status --porcelain` empty).
**Fixture `base_commit`:** `8c2a71c08977ff92bb7b29ae80d6fe71a7714158` (the parent of `679cefbf`). Every contract source was read with `git show 8c2a71c0:<path>`.
**Reviewer role:** independent, read-only, before first execution. No file in the repository was edited; no fixture, replay, generator or runner was executed. This record approves nothing; it is input to the owner's decision.

**Tree drift during the review.** The worktree was at `679cefbf` with a clean tree when the review started. While this record was being written another process committed `62077db4` ("evidence(#805): F-R3-2 investigated as evidence; POSIX versus no-descriptor-table trust assessment; pinning tests") on top of it and left two uncommitted changes. Checked afterwards: `62077db4` touches only `reference/tests/test_786_cross_scope_write_authority.py`, `reference/tests/test_representation_cache.py` and two new reports under `reports/validation/805-at-head/`; none of the reviewed inputs (the three fixtures, both runners, the generator, the README, the seven contract sources) differs between `679cefbf` and `62077db4`, and the three fixture digests above were re-computed at `62077db4` and are identical. The uncommitted edit to `docs/786-cross-scope-write-authority.md` changes one bullet (l.180, the F-R3-2 disposition), which no fixture quotes; the hashed source at `8c2a71c0` is unaffected. The untracked `reference/tests/test_786_security_replays_v3.py` contains `test_every_case_of_every_replay_passes`, which calls `run_replay(replay_id, allow_dirty=True)` on every `-v3` fixture: running that module executes the fixtures. It was not run by this reviewer; whether it has been run by anyone cannot be seen from the tree (`reports/validation/786-security-replays-v3/` is still absent). See finding F-15. Every judgement below was made from the inputs at `679cefbf`/`8c2a71c0`.

**Fixture digests (sha256, `sha256sum` at `679cefbf`):**

| fixture | cases | expectations | sha256 |
|---|---|---|---|
| `reference/fixtures/786-security-replays/cross-scope-write-authority-denial-v3.json` | 13 | 123 | `6d0b601faff5be01fe1a6001093810babc80b9a97ce00e8dc1f0188171c5fa0e` |
| `reference/fixtures/786-security-replays/deleted-lineage-generations-and-restart-v3.json` | 10 | 83 | `ac4ec1f218ff8de90c7f2e0cc3f1acdcbb58e4897d7adf1a8331db6ac822e5bf` |
| `reference/fixtures/786-security-replays/public-tombstone-redaction-and-observer-separation-v3.json` | 8 | 34 | `d821c4b04c05b715016caa12473864db98b7862f9523d98ec9ea3f72bc04af25` |

31 cases, 240 `expect` entries (the README's "31 cases, 240 expectations" is correct).

**`contract_sources[].sha256_at_base`:** all seven verified with `git show 8c2a71c0:<path> | sha256sum`:

| path | sha256 at `8c2a71c0` | matches fixture |
|---|---|---|
| `docs/786-cross-scope-write-authority.md` | `b548c340…3ce1fe4f` | yes (W, L, R) |
| `docs/44-public-api-contract.md` | `0187a9a3…cb20ed17af54` | yes (W, L, R) |
| `docs/plan-776-777-772-exact-head-qualification.md` | `c8e724ae…15734922` | yes (W, L, R) |
| `docs/774-776-lineage-integration-contract.md` | `d6c5ba69…1c814e10` | yes (L) |
| `docs/774-strict-successor-target-policy.md` | `fe910667…3379a01ecd7be` | yes (L) |
| `docs/28-retention-deletion-and-tombstones.md` | `9f1c91f7…29b03beda` | yes (L) |
| `docs/777-public-contract-1-7-successor-qualification.md` | `28405f04…8c91faba9` | yes (R) |

## Method

1. Read the three `-v3` fixtures case by case (steps, probes, `expect`, `record`, `implementation_evidence`, `clauses`), the generator `author_fixtures_v3.py` (its `Q_*` constants are the quoted clauses; its final loop asserts that every `expect` key is traced by a clause, that every clause source is in `contract_sources`, and that `implementation_evidence ⊆ record` and `implementation_evidence ∩ expect = ∅`), and the README section "Generation -v3".
2. Re-checked those assertions independently (script over the JSON): every `expect` key of every case is listed under at least one clause; every `record` key equals the `implementation_evidence` list; no recorded observable is also expected; every clause-listed observable is a probe. One clause-listed observable is not expected (L2 `old_exists`, a recorded one).
3. Verified every quoted clause against the cited source at `8c2a71c0`: each `Q_*` string was split at its ` ... ` elisions and each fragment searched verbatim (then whitespace-normalised, for line-wrapped sources). Results in the clause legend below.
4. Read the runner semantics: `reference/run_786_security_replays_dsl2.py` (DSL/2: `snapshot_tombstone`, `history_mentions`, `history_summary`, `tombstone_record`, `tombstone_unchanged`, `op_raised_message`, `derived_reconciliation`, and the `_raised_message` re-execution) and the inherited `reference/run_786_security_replays.py` (DSL/1 ops and probes, `_normalised` folding, `match`).
5. Where a derivation depends on how a probe projects a result, read the runtime at `8c2a71c0`: `api/surface.py` (`_proposal` l.675-692, `history` l.1245-1300, `open` reconciliation l.540-568, `forget` reconciliation l.1205-1232, `semantic_retrieval_posture` l.1311-1335, `SEMANTIC_RETRIEVAL_DEFAULT = "off"` l.350), `runtime/adapter.py` (`_dispute_refusal` l.1660-1680, `_delete_refusal` l.2020-2058, `governed_delete` l.2100-2205 incl. the tombstone record and the version it records, `tombstone()` l.2212, `tombstoned_ids` l.1814, `public_deleted_version` l.1877-1898, audit events l.445-580, clock format l.53-55), `runtime/representation_cache.py` (`reconcile_derived_vector_stores` l.282-372), `core/receipts.py` (`build_audit_event` l.480-510), `core/policy.py` (base-outcome table l.75-102, `_envelope` l.327-336, `_DEFERRALS` l.124).
6. Read the `-v2` review (`reports/validation/805-at-head/independent-replay-review-v2.md`) and the committed `-v2` evidence (`reports/validation/786-security-replays/*-v2/report.json`) only to check whether a `-v3` probe that is unchanged from `-v2` has a known false-positive risk (R4 query tokens, R6b/R1 `late`, W8 `midnight`). No `-v3` expectation was judged by `-v2` evidence.
7. Checked preregistration integrity: `git log` for the `-v3` files and `ls reports/validation/786-security-replays-v3`.

**How the probes measure (what a derivation must be judged against).** `op_result` reads one summary field of a named step (`committed`, `refusal`, `before_state`, `after_state`, `state_snapshot`, `raised`). `op_mentions` substring-scans the full serialised facade result for tokens; a token that is a label is replaced by that fact's uuid before scanning, every other token is searched literally. `history` projects `{current (label), state_version, tombstoned, events (types only)[, rejected_values (count)]}`. `history_summary` is the same without `events`. `history_mentions` substring-scans the whole serialised public `history` result (events with their payloads included). `history_same_as_unknown` / `op_same_as_unknown` / `recall_same_as_unknown` compare the whole result, as sorted JSON with uuids relabelled and `ref-N`, ISO timestamps, `facade:<sha>`, `content:sha256:<sha>` folded, against the same call on `memory:never`. `tombstone_record` / `snapshot_tombstone` / `tombstone_unchanged` read `adapter.tombstone(uuid)` (`_tombstones.get`), relabel uuids and fold timestamps (`_fold`: `YYYY-MM-DDTHH:MM:SS[.f]Z` → `T`); `tombstone_unchanged` is `before == after` on the folded record. `op_raised_message` re-runs the named step and records `str(ValueError)`. `derived_reconciliation` reads `semantic_retrieval_posture()["derived_reconciliation"]` and projects `status`, `stores_checked`, `pending`. Private reads (`canonical_head`, `canonical_version`, `fact_valid`, `fact_exists`, `tombstoned_ids`, `disputed`, `episode_present`, `version_in_effect`, `tombstone_*`) are ground truth, not public observables. `delete_version` and `commit_with_episode` are adapter-level calls. `reopen` is `close()` + `open()` in one process.

Two facts about the payloads matter for several rows: (a) audit events (`build_audit_event`) carry `event_id`, `event_type`, `timestamp`, `component`, `memory_id`, `correlation_id`, `causation_id`, `policy_version`, `authority` (`permitted_actions`/`prohibited_actions` = the operation name plus `collect_more_evidence`/`defer`, `selection_mode`, and `authority_refs` only for a write-target-refused proposal), `receipt_ref`; **they never carry fact text, a scope ref or a fact uuid**. So in a `history_mentions` scan the uuid (label) tokens are the meaningful ones; text tokens (`dawn`, `noon`, `night`, `early`, `late`, `dusk`, `mid`) and `project:a` cannot match a history payload at this runtime and are inert. (b) The runtime clock formats `%Y-%m-%dT%H:%M:%SZ`, which `_fold` replaces by `T`, so a tombstone's `deleted_at` is invisible to `tombstone_unchanged`.

## Clause legend (quoted text verified against the cited source at `8c2a71c0`)

Tags are the generator's `Q_*` names. **VERIFIED** = every fragment found verbatim (line wrapping of the source ignored); **PARAPHRASED** = the quoted text is not in the source as written but its substance is, with the difference named; **NOT FOUND** = a fragment is absent from the cited source.

| tag | source (line) | status | note |
|---|---|---|---|
| Q_REM | docs/44 l.180 | VERIFIED | |
| Q_CFD | docs/44 l.181 | VERIFIED | |
| Q_OVR | docs/44 l.183 | VERIFIED | the `(... ` elision drops "a `project_ref` without its isolation domain is refused;" |
| Q_CONT | docs/44 l.184 | VERIFIED | elision drops "the head's own scope must be eligible for the scope the new fact would be stored under" |
| Q_HOST | docs/44 l.194 | VERIFIED | three elisions; the omitted text does not change the sense |
| Q_CLOSED | docs/44 l.187 | VERIFIED | elision drops "because the reference has no visible head"; the quote also stops before the escalation sentence ("keeps the tombstone's `deleted_at`, recorded version and lineage") that L5b would also want |
| Q_V0 | docs/44 l.188 | VERIFIED | |
| Q_GEN | docs/44 l.190 | VERIFIED | elision drops the definition "`state_version`, `state_snapshot`, `before_state` and `after_state` count within the live generation of a logical id" |
| Q_CAND | docs/44 l.86 | VERIFIED | |
| Q_DERIVED | docs/44 l.108 | VERIFIED | long elision (the sidecar dispositions) |
| Q_786_SUP | docs/786 l.86 | VERIFIED | table row; the `| ...` elision drops the pre-repair cell |
| Q_786_COMPLETE | docs/786 l.87 | VERIFIED | table row; elision drops "existing fixtures depend on it;" |
| Q_786_EP | docs/786 l.56-57 | VERIFIED | |
| Q_786_F7 | docs/786 l.106 | PARAPHRASED | source: "the authorize event of a write-target-refused proposal carries `authority_refs: ["write-target:refused"]` (schema-valid) and the public history projection withholds **that** correlation"; the quote substitutes "a write-target-refused proposal's" for "that". Sense preserved |
| Q_786_RESTART | docs/786 l.82 | PARAPHRASED | table row `| wrong-scope correction after restart (x2) | commits | refused; `_fact_scope` survives every restart |` with the first and third cells joined by ": " |
| Q_786_SAME | docs/786 l.89 | PARAPHRASED | table row `| same text in unrelated memories of two projects | independent | independent (positive control) |` joined; "(positive control)" dropped |
| Q_786_GEN | docs/786 l.80 + l.21 | PARAPHRASED | composite: table row l.80 (`B re-creates A's **deleted** id | allowed (fresh generation) | unchanged, with isolation proven (A cannot write it back while B's generation is live)`, emphasis stripped, cells reordered) joined with the last clause of the "invariant" paragraph l.21 ("every deleted generation stays a #774 as-of barrier for everyone"). Two sentences from two sections presented as one |
| Q_786_FC | docs/786 l.134 | PARAPHRASED | condensed: source reads "re-pruning an **already** deleted head rewrote its tombstone (new `deleted_at`, shrunken lineage) … FIXED: `already_deleted` **for a tombstoned fact or a direct member of a deleted lineage**; only pruning -> permanent deletion is a further governed act, and that escalation keeps `deleted_at`, `state_version` and the lineage (the tombstone is reassigned, not mutated …)". The quote drops the member clause (the one that supports `again_member`) and writes "version" for "`state_version`" |
| Q_786_W4 | docs/786 l.185-187 | VERIFIED | |
| Q_786_DISCLOSED | docs/786 l.174 | VERIFIED | |
| Q_L1 | docs/774-776 l.119-121 | VERIFIED | elision drops "ID must make the new current fact visible," |
| Q_L2 | docs/774-776 l.122-123 | VERIFIED | stops before "to invent a predecessor" |
| Q_L3 | docs/774-776 l.124-125 | VERIFIED | |
| Q_LX | docs/774-776 l.143-146 | PARAPHRASED | two bullets joined with "; "; the first is truncated before "after memory-ID re-creation. Ordinary stated state-change history remains reachable when not deleted." (the sentence L5's `kept_mentions` needs) |
| Q_774 | docs/774 l.188-190 | VERIFIED | |
| Q_PLAN_OWNER | docs/plan l.32-36 | PARAPHRASED | source: "a reader who could have read the deleted head (same tenant; domain, project and task eligible against the canonical `_fact_scope` …) reads `{"current_fact_uuid": null, "tombstoned": true, "events": [], "state_version": <canonical>}` …"; the quote writes "the owner reads" and unquotes the JSON keys. Sense preserved (the owner is such a reader) |
| Q_PLAN_OTHER | docs/plan l.37 | VERIFIED | |
| Q_PLAN_RECREATED | docs/plan l.38 | VERIFIED | |
| Q_777 | docs/777 | fragment 1 **NOT FOUND**; fragment 2 VERIFIED | "out-of-scope indistinguishability" does not occur in docs/777 at `8c2a71c0`; it is in docs/plan l.27-28 ("goes beyond what #777 decided (no deleted-generation identifiers, timestamps, topology; out-of-scope indistinguishability)"). "no regression to transitive deleted content refusal" is docs/777 l.283-284, a requirement placed on "a future integrated successor", not a statement of behaviour |
| Q_28_PRUNE | docs/28 l.173 + l.175 | PARAPHRASED | heading "### Prune versus delete" joined with "Expected: pruned memory remains recoverable under policy; deleted memory follows stronger semantics." |
| Q_28_CLAIM | docs/28 l.163 | VERIFIED | |

Derivation key used in the tables: **DERIVED** = follows from the quoted clause given what the probe measures; **DERIVED (cite: …)** = follows from the cited source document, but from a sentence other than the quoted one (named); **STRONGER** = the expectation pins more than the clause states; **WEAKER** = the expectation establishes less than the invariant statement claims; **NOT DERIVABLE** = no clause of any listed source states it (positive control, policy/configuration precondition, or implementation literal); **WRONG** = contradicts a clause. For `history` expectations the four fields are judged separately: `current`/`state_version`/`tombstoned` and the *count* of events are derivable; the exact event-type vocabulary (`memory.propose, memory.authorize, memory.commit, memory.receipt`) appears in no contract source (docs/44 l.45 says only "the target's retained audit events (commit and deletion events …)") and is marked "vocab STRONGER".

## W family: `cross-scope-write-authority-denial-v3` (13 cases, 123 expectations)

### W1-remember-over-live-head

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| b1_committed | eq false | Q_REM | VERIFIED | DERIVED |
| b1_refusal | eq "target_unavailable" | Q_REM | VERIFIED | DERIVED |
| b1_before | eq "v0" | Q_REM | VERIFIED | DERIVED |
| b1_after | eq "v0" | Q_REM | VERIFIED | DERIVED |
| b1_snapshot | eq "v0" | Q_REM | VERIFIED | DERIVED |
| b1_mentions | eq [] (tokens `memory:k`→uuid, `project:a`, `dawn`, `v1`) | Q_REM | VERIFIED | DERIVED for `v1` (all states `v0`); DERIVED (cite: docs/786 l.65-70 "neither the proposal id nor the receipt discloses the protected memory's version"; fixture title "refusals … disclose nothing") for the uuid/text/project tokens |
| head | eq "memory:k" | Q_REM ("Nothing is written") | VERIFIED | DERIVED |
| owner_history | eq {memory:k, 1, false, 4 events} | Q_REM ("no version moves") | VERIFIED | DERIVED; vocab STRONGER |
| owner_recall | eq ["memory:k"] | Q_REM | VERIFIED | DERIVED (owner's seed admitted; nothing changed) |
| other_recall | eq [] | Q_786_SAME | PARAPHRASED | DERIVED (cite: docs/44 l.86 "Domain-ineligible matches are never caller-visible"; Q_786_SAME is about two unrelated memories, B wrote none here) |
| other_history_unknown | eq true | Q_CFD | VERIFIED | DERIVED (cite: Q_PLAN_OTHER docs/plan l.37; Q_CFD is about write results, not `history`) |

### W2-correct-forget-dispute-by-other

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| correct_unknown | eq true | Q_CFD | VERIFIED | DERIVED (whole-result equality is exactly "byte-identical to the result for an id nobody wrote") |
| forget_unknown | eq true | Q_CFD | VERIFIED | DERIVED |
| permanent_unknown | eq true | Q_CFD | VERIFIED | DERIVED (permanent `forget` is a `forget`; docs/786 l.78 names "permanent forget" explicitly) |
| dispute_unknown | eq true | Q_CFD | VERIFIED | DERIVED |
| tombstones | eq [] | Q_CFD | VERIFIED | DERIVED (cite: docs/786 l.78 "no tombstone"; implied by "byte-identical to unknown id") |
| disputed | eq [] | Q_CFD | VERIFIED | DERIVED (cite: docs/786 l.79 "no dispute mark") |
| head | eq "memory:k" | Q_CFD | VERIFIED | DERIVED |
| valid | eq true | Q_CFD | VERIFIED | DERIVED (cite: docs/786 l.77 "A's fact stays valid") |
| owner_recall | eq ["memory:k"] | Q_CFD | VERIFIED | DERIVED |

### W3-refusal-survives-restart

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| b1 | eq false | Q_786_RESTART | PARAPHRASED | DERIVED |
| b1_refusal | eq "target_unavailable" | Q_REM | VERIFIED | DERIVED |
| b1_after | eq "v0" | Q_REM | VERIFIED | DERIVED |
| b1_mentions | eq [] (`memory:k`, `memory:k@2`, `v2`, `dawn`, `noon`, `project:a`) | Q_REM | VERIFIED | DERIVED (as W1 b1_mentions) |
| b2 | eq false | Q_786_RESTART | PARAPHRASED | DERIVED (the clause names "correction after restart (x2)" literally) |
| b2_refusal | eq "fact_not_found" | Q_CFD | VERIFIED | DERIVED |
| b3 | eq false | Q_786_RESTART | PARAPHRASED | DERIVED (forget after the second reopen: "`_fact_scope` survives every restart" + Q_CFD) |
| b3_refusal | eq "fact_not_found" | Q_CFD | VERIFIED | DERIVED |
| b4 | eq false | Q_786_RESTART | PARAPHRASED | DERIVED |
| b4_refusal | eq "fact_not_found" | Q_CFD | VERIFIED | DERIVED |
| head | eq "memory:k@2" | Q_REM | VERIFIED | DERIVED (owner's own correct committed under `require_committed`; refusals move nothing) |
| owner_history | eq {memory:k@2, 2, false, 8 events} | Q_REM | VERIFIED | DERIVED; vocab STRONGER |
| owner_recall | eq ["memory:k@2"] | Q_REM | VERIFIED | DERIVED |

Note: "restart" is a handle reopen in one process (DSL/1 `reopen`, unchanged in DSL/2); the clause's "survives every restart" is shown for the SQLite-backed state a handle reloads (carried from the `-v2` review, finding 12).

### W4-overrides

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| bad_target | eq "ValueError" | Q_OVR | VERIFIED | DERIVED |
| bad_unknown | eq "ValueError" | Q_OVR | VERIFIED | DERIVED ("before any target is resolved" ⇒ the same for `memory:never`) |
| bad_target_message | eq "required isolation domains must also be bound isolation domains" | Q_OVR | VERIFIED | equality across targets DERIVED (Q_OVR "before any target is resolved"; docs/786 l.102 "identical for any target"); the **literal** is NOT DERIVABLE from any contract document: it is the implementation text, `surface.py` l.692 at `8c2a71c0`, which it matches exactly (check 6) |
| bad_unknown_message | eq same literal | Q_OVR | VERIFIED | as above |
| sup_rem_committed | eq false | Q_786_SUP, Q_CONT | VERIFIED | DERIVED |
| sup_rem_refusal | eq "target_unavailable" | Q_REM | VERIFIED | DERIVED (cite: docs/786 l.53 "`promotion` reports `target_unavailable`" + l.101 "`write_target_refusal` now also requires scope continuity"). Q_REM's premise ("a live head outside the writer's scope") does not hold here: the superset writer is an eligible reader; the refusal is scope continuity, not scope |
| sup_rem_before | eq "v0" | Q_REM | VERIFIED | DERIVED (cite: docs/786 l.55-56 "a refused target … reports `before_state = after_state = "v0"`") |
| sup_cor_committed | eq false | Q_786_SUP, Q_CONT | VERIFIED | DERIVED |
| head | eq "memory:k" | Q_REM | VERIFIED | DERIVED |
| valid | eq true | Q_REM | VERIFIED | DERIVED |
| owner_recall | eq ["memory:k"] | Q_REM | VERIFIED | DERIVED |
| tombstones | eq [] | Q_REM | VERIFIED | DERIVED (trivially: no deletion is attempted in this case) |

`record`/`implementation_evidence`: `sup_cor_refusal` (not expected). Appropriate: docs/786 l.54 would predict `fact_not_found` for a refused correction, but the continuity path's token is not stated for `correct`.

### W4b-documented-dispositions-of-complete-and-superset-declarations

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| sup_disp | eq true | Q_786_SUP | VERIFIED | DERIVED (documented disposition: "`forget`/`dispute` admitted as an eligible reader's") |
| sup_forget | eq true | Q_786_SUP | VERIFIED | DERIVED |
| tombstones | eq ["memory:k"] | Q_786_SUP | VERIFIED | DERIVED (an admitted forget tombstones the memory; `tombstoned_ids` returns memory ids) |
| complete | eq true | Q_786_COMPLETE, Q_HOST, Q_786_W4 | VERIFIED | DERIVED (documented host-model disposition; the override equals the owner handle's scope exactly, so docs/44 l.185 exact-scope supersession is satisfied). The invariant text and the stop line state the privileged-host qualification |
| k2_head | eq "complete" | Q_786_COMPLETE, Q_HOST | VERIFIED | DERIVED |

`record`/`implementation_evidence`: `k2_owner_recall` (the `-v2` sub-expectation corrected toward observed output) is no longer expected. Correct closure of `-v2` finding 4(b).

### W5-positive-controls-and-unrelated-same-text

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| a1 | eq true | Q_786_SAME | PARAPHRASED | DERIVED (positive control the clause presupposes: two memories are written) |
| a2 | eq true | Q_786_SAME | PARAPHRASED | DERIVED (cite: docs/786 l.141-142 "the owner's own writes, corrections, deletions, escalations and disputes commit as before"); not in the quoted clause |
| a3 | eq true | Q_786_SAME | PARAPHRASED | DERIVED (cite: docs/786 l.141-142) |
| b1 | eq true | Q_786_SAME | PARAPHRASED | DERIVED |
| owner_recall | eq [] | Q_CAND | VERIFIED | DERIVED (`disputed` and `superseded_not_current` are "lifecycle refusals" ⇒ neither version admitted) |
| owner_candidates | eq ["memory:k", "memory:k@2"] | Q_CAND | VERIFIED | DERIVED as a set ("remain visible candidates"); the **order** is STRONGER (ranking order is stated nowhere; `recall_candidates` returns the runtime's candidate order) |
| disputed | eq ["memory:k@2"] | Q_CAND | VERIFIED | DERIVED (cite: docs/786 l.141-142; a committed own dispute marks the head) |
| head | eq "memory:k@2" | Q_CAND | VERIFIED | DERIVED (weakly: a disputed head "remains a visible candidate", i.e. is not replaced) |
| other_recall | eq ["other"] | Q_786_SAME | PARAPHRASED | DERIVED |
| other_view_of_k | eq true | Q_786_SAME | PARAPHRASED | DERIVED (independence; also Q_PLAN_OTHER) |
| owner_view_of_other | eq true | Q_786_SAME | PARAPHRASED | DERIVED |

### W6-denied-proposals-persist-no-episode

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| denied_committed | eq false | Q_786_EP | VERIFIED | DERIVED (Q_REM at the adapter level, docs/786 l.51-56) |
| denied_refusal | eq "target_unavailable" | Q_REM | VERIFIED | DERIVED (adapter-level `commit_proposal`; docs/786 l.53) |
| denied_before | eq "v0" | Q_REM | VERIFIED | DERIVED (docs/786 l.56) |
| parked_committed | eq false | Q_786_EP | VERIFIED | NOT DERIVABLE from any clause: that a `risk: high` promotion parks under review is the policy table (`core/policy.py` l.89 `("promotion","high"): REQUIRE_REVIEW`), not a contract sentence; the clause presupposes a parked proposal exists. A scenario precondition stated as an expectation |
| kept_committed | eq true | Q_786_EP | VERIFIED | DERIVED (cite: docs/786 l.88 "committed proposals keep theirs") |
| episode_denied | eq false | Q_786_EP | VERIFIED | DERIVED (after reopen: docs/786 l.39-40/88 name recoverability after restart) |
| episode_parked | eq false | Q_786_EP | VERIFIED | DERIVED |
| episode_kept | eq true | Q_786_EP | VERIFIED | DERIVED (cite: docs/786 l.88); the quoted clause says nothing about committed proposals |
| head | eq "memory:k" | Q_786_EP | VERIFIED | DERIVED (Q_REM "nothing is written") |
| parked_head | eq null | Q_786_EP | VERIFIED | DERIVED given `parked_committed` |

### W7-refused-attempt-leaves-no-public-trace

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| b1 | eq false | Q_786_F7 | PARAPHRASED | DERIVED (Q_REM) |
| other_history_unknown | eq true | Q_CFD | VERIFIED | DERIVED (cite: Q_PLAN_OTHER) |
| canonical_version | eq 2 | Q_786_F7 | PARAPHRASED | DERIVED (owner's correct → 2; the refusal "moves no version") |
| owner_history_mentions | eq [] (`dusk`, `project:b`) | Q_786_F7 | PARAPHRASED | DERIVED; but both tokens are inert for a history payload (events carry no text or scope), so this probe cannot fail at this runtime whatever F7 does; the F7 check in this case is the event count below |
| owner_history | eq {memory:k@2, 2, false, 8 events} | Q_786_F7 | PARAPHRASED | DERIVED (withheld correlation ⇒ exactly the owner's two writes); vocab STRONGER |

### W7b-refused-dispute-and-forget-attempts-leave-no-public-trace

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| bd | eq false | Q_786_F7 | PARAPHRASED | DERIVED (cite: Q_CFD; docs/786 l.79 "by id or by fact uuid") |
| bf | eq false | Q_786_F7 | PARAPHRASED | DERIVED (cite: Q_CFD) |
| bdf | eq false | Q_786_F7 | PARAPHRASED | DERIVED (cite: docs/786 l.79) |
| other_history_unknown | eq true | Q_CFD | VERIFIED | DERIVED (cite: Q_PLAN_OTHER) |
| owner_history_mentions | eq [] (`project:b`, `dispute`, `forget`) | Q_786_F7 | PARAPHRASED | DERIVED; tokens inert (checked: `authority.permitted_actions`/`prohibited_actions` hold the operation name and `collect_more_evidence`/`defer`, never `dispute`/`forget`, so no false positive from the owner's own events) |
| owner_history | eq {memory:k, 1, false, 4 events} | Q_786_F7 | PARAPHRASED | DERIVED; vocab STRONGER |

### W7c-former-owner-attempts-leave-no-trace-in-the-new-generation

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| a_rem | eq false | Q_REM, Q_786_GEN | VERIFIED / PARAPHRASED | DERIVED |
| a_rem_refusal | eq "target_unavailable" | Q_REM | VERIFIED | DERIVED |
| a_disp | eq false | Q_CLOSED | VERIFIED | DERIVED (fact-level `dispute` of a tombstoned fact by uuid) |
| a_disp_refusal | eq "already_deleted" | Q_CLOSED | VERIFIED | DERIVED |
| a_disp_mentions | eq [] (`gen-b`→uuid, `dusk`, `v1`, `v2`) | Q_V0 | VERIFIED | DERIVED (refused dispute reports `v0` states: docs/786 l.59-60; Q_CLOSED "neither moves or reads the live generation" ⇒ no `gen-b`/`dusk`) |
| a_del | eq false | Q_CLOSED | VERIFIED | DERIVED ("a governed pruning of one of its versions" of a closed generation) |
| a_del_refusal | eq "already_deleted" | Q_CLOSED | VERIFIED | DERIVED |
| a_forget | eq false | Q_CLOSED | VERIFIED | DERIVED (logical-reference `forget` ⇒ `fact_not_found`) |
| a_forget_refusal | eq "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED |
| other_history_mentions | eq [] (`memory:k`→A's uuid, `dawn`, `night`, `project:a`) | Q_786_F7, Q_PLAN_RECREATED | PARAPHRASED / VERIFIED | DERIVED (the uuid token is the live check; text/scope tokens inert) |
| other_history | eq {gen-b, 1, false, 4 events} | Q_786_F7 | PARAPHRASED | DERIVED (B's generation; A's refused `remember` correlation withheld; A's `dispute`/`delete_version`/`forget` are refused before any event reaches the live generation); vocab STRONGER |
| other_recall | eq ["gen-b"] | Q_786_GEN | PARAPHRASED | DERIVED (positive: B's live generation admitted to B) |

Note: this case does not probe A's own `history` view under the live foreign generation (W8 and R3 do); the control below pins it without a re-creation.

### W7c-control-former-owner-attempts-without-a-re-creation

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| a_disp | eq false | Q_CLOSED | VERIFIED | DERIVED; literal identical to W7c |
| a_disp_refusal | eq "already_deleted" | Q_CLOSED | VERIFIED | DERIVED; identical to W7c |
| a_disp_mentions | eq [] (`v1`, `v2`) | Q_CLOSED | VERIFIED | DERIVED (cite: docs/786 l.59-60 "a refused deletion or dispute reports `v0` states"; Q_GEN "reports `0` to any writer"); the two shared tokens equal W7c's |
| a_del | eq false | Q_CLOSED | VERIFIED | DERIVED; identical to W7c |
| a_del_refusal | eq "already_deleted" | Q_CLOSED | VERIFIED | DERIVED; identical to W7c |
| a_forget | eq false | Q_CLOSED | VERIFIED | DERIVED; identical to W7c |
| a_forget_refusal | eq "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED; identical to W7c |
| owner_history | eq {null, 2, true, []} | Q_GEN | VERIFIED | DERIVED ("the version its deletion recorded"; one write then a deletion records 2, see note N-7 on the numeral) |

### W8b-refused-and-parked-proposals-on-a-tombstoned-id-report-v0

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| parked_b | eq false | Q_GEN | VERIFIED | NOT DERIVABLE from a clause: that B's `risk_class: medium` promotion parks is `policy.py` l.88 (`("promotion","medium"): REQUIRE_REVIEW`); the clause ("open to any writer", "reports `0`") does not say the proposal is not admitted. Scenario precondition stated as an expectation |
| parked_b_states | eq [] (`v1`, `v2`, `v3`, both old uuids) | Q_GEN | VERIFIED | DERIVED ("the id reports `0` to any writer"; the old uuids are deleted-generation identifiers) |
| parked_b_after | eq "v0" | Q_GEN | VERIFIED | DERIVED ("the id reports `0` to any writer"; docs/786 l.132 F-A "refused and parked writes report `v0/v0`" corroborates) |
| parked_a_after | eq "v0" | Q_GEN | VERIFIED | DERIVED (as above); `parked_a` is the owner's own `risk_class: high` promotion, parked by `policy.py` l.89 |
| parked_a_snapshot | eq "v0" | Q_GEN | VERIFIED | DERIVED |
| parked_b2_after | eq "v0" | Q_GEN | VERIFIED | DERIVED (after reopen) |
| other_history | eq {null, 0, false, []} | Q_PLAN_OTHER | VERIFIED | DERIVED (the never-existed shape: docs/44 l.45 names the four fields) |
| other_history_unknown | eq true | Q_PLAN_OTHER | VERIFIED | DERIVED |
| owner_history | eq {null, 3, true, []} | Q_GEN | VERIFIED | DERIVED (see N-7) |

### W8-recreated-generation-starts-its-own-counter

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| b1_snapshot | eq "v0" | Q_GEN | VERIFIED | DERIVED |
| b1_before | eq "v0" | Q_GEN | VERIFIED | DERIVED ("a re-creation's receipt reads `v0 -> v1`") |
| b1_after | eq "v1" | Q_GEN | VERIFIED | DERIVED |
| b1_mentions | eq [] (`v3`, both old uuids, `dawn`, `noon`) | Q_GEN | VERIFIED | DERIVED ("the former generation's count never reaches the new one") |
| b2_before | eq "v1" | Q_GEN | VERIFIED | DERIVED (count within the live generation) |
| b2_after | eq "v2" | Q_GEN | VERIFIED | DERIVED |
| a_back | eq false | Q_REM, Q_786_GEN | VERIFIED / PARAPHRASED | DERIVED |
| a_back_refusal | eq "target_unavailable" | Q_REM | VERIFIED | DERIVED |
| owner_history | eq {null, 3, true, []} | Q_GEN | VERIFIED | DERIVED (stable under B's generation: "the owner of the deleted generation still reads the version its deletion recorded"; see N-7) |
| other_history_mentions | eq [] (A's two uuids, `dawn`, `noon`, `night`, `v3`, `project:a`) | Q_PLAN_RECREATED | VERIFIED | DERIVED. `night` is a substring of B's own `midnight` (step b2); it cannot collide because history payloads carry no fact text, but it is a fragile token choice (N-6) |
| other_history | eq {gen-b@2, 2, false, 8 events} | Q_GEN | VERIFIED | DERIVED; vocab STRONGER |
| head | eq "gen-b@2" | Q_GEN | VERIFIED | DERIVED |

## L family: `deleted-lineage-generations-and-restart-v3` (10 cases, 83 expectations)

### L1-deletion-withholds-live

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| current | eq [] | Q_L1 | VERIFIED | DERIVED |
| historical | eq [] | Q_L1 | VERIFIED | DERIVED ("without returning any old deleted version in explicit historical retrieval") |
| by_ref_unknown | eq true | Q_786_GEN | PARAPHRASED | DERIVED (cite: Q_PLAN_OWNER "no deleted-generation identifier, timestamp, event or value is served", which is cited in this very case for `owner_history`; Q_786_GEN's "as-of barrier" is the weakest fit). Note N-10: docs/44 l.86 still says `tombstoned` candidates "remain visible candidates with decisions", which the owner's whole-result equality with `memory:never` contradicts in wording; the plan clause (post-#777) governs |
| mentions | eq [] (both uuids, `dawn`, `noon`) | Q_L1 | VERIFIED | DERIVED |
| owner_history | eq {null, 3, true, []} | Q_PLAN_OWNER, Q_GEN | PARAPHRASED / VERIFIED | DERIVED (N-7) |

### L1-deletion-withholds-after-restart

Same five observables, same matchers and clauses, after `reopen`: all DERIVED (the plan l.40 names "live and restart reads"); `by_ref_unknown` as above (cite).

### L2-owner-recreation

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| owner_history | eq {gen2, 1, false, 4 events} | Q_L2, Q_PLAN_RECREATED | VERIFIED | DERIVED (Q_GEN gives the counter 1); vocab STRONGER |
| owner_history_mentions | eq [] (both old uuids, `dawn`, `noon`, `v3`) | Q_PLAN_RECREATED | VERIFIED | DERIVED |
| historical | eq ["gen2"] | Q_L1 | VERIFIED | DERIVED ("make the new current fact visible, without returning any old deleted version") |
| mentions | eq [] | Q_L1 | VERIFIED | DERIVED |
| old_semantics | eq false | Q_L2 | VERIFIED | DERIVED (cite: docs/774-776 l.138-140 "A public visibility gate for a fact must use the same canonical admission/deletion decision as `write_semantics` and recall"); Q_L2 is about predecessor traversal |
| new_semantics | eq true | Q_L2 | VERIFIED | DERIVED (cite: same sentence; positive control) |

`record`/`implementation_evidence`: `old_exists` (listed under the docs/28 clause although recorded, not expected: a clause is cited for an observable the fixture itself says is not derivable, N-11).

### L3-other-project-recreation-is-isolated

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| owner_historical | eq [] | Q_786_GEN | PARAPHRASED | DERIVED (A's generation deleted: Q_L1; B's generation ineligible to A: docs/44 l.86) |
| owner_mentions | eq [] (`gen-b`→uuid, `dusk`) | Q_786_GEN | PARAPHRASED | DERIVED |
| owner_history | eq {null, 3, true, []} | Q_PLAN_OWNER, Q_GEN | PARAPHRASED / VERIFIED | DERIVED (stable under the foreign generation; N-7); identical to L3-control |
| other_mentions | eq [] (A's uuids, `dawn`, `noon`) | Q_786_GEN | PARAPHRASED | DERIVED ("the new generation sees nothing of the old one", docs/786 l.19-20; Q_PLAN_OTHER) |
| other_history | eq {gen-b, 1, false, 4 events} | Q_PLAN_RECREATED | VERIFIED | DERIVED; vocab STRONGER |
| other_history_mentions | eq [] (A's uuids, `dawn`, `noon`, `midnight`, `v3`, `project:a`) | Q_PLAN_RECREATED | VERIFIED | DERIVED (uuid tokens live; `midnight` is A's refused text, withheld by F7 and inert anyway) |
| a_rem | eq false | Q_786_GEN | PARAPHRASED | DERIVED |
| a_rem_refusal | eq "target_unavailable" | Q_REM, Q_786_DISCLOSED | VERIFIED | DERIVED (the documented disclosure) |
| a_rem_after | eq "v0" | Q_REM | VERIFIED | DERIVED |
| a_cor | eq false | Q_CLOSED | VERIFIED | DERIVED |
| a_cor_refusal | eq "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED (logical-reference `correct`) |
| a_del | eq false | Q_CLOSED | VERIFIED | DERIVED (this `a_del` is a facade `forget`, not `delete_version`) |
| a_del_refusal | eq "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED |
| a_disp | eq false | Q_CLOSED | VERIFIED | DERIVED |
| a_disp_refusal | eq "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED (`dispute` by `target_reference`) |
| a_disp_fact | eq false | Q_CLOSED | VERIFIED | DERIVED |
| a_disp_fact_refusal | eq "already_deleted" | Q_CLOSED | VERIFIED | DERIVED (`dispute` of a tombstoned fact by its uuid; `memory:f@2` is the deleted head) |
| a_mentions | eq [] (`gen-b`→uuid, `dusk`, `v1`) | Q_REM | VERIFIED | DERIVED (`state_snapshot`/states `v0`; nothing of the live generation disclosed) |
| head | eq "gen-b" | Q_786_GEN | PARAPHRASED | DERIVED |

### L3-control-former-owner-answers-without-a-re-creation

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| owner_history | eq {null, 3, true, []} | Q_PLAN_OWNER, Q_GEN | PARAPHRASED / VERIFIED | DERIVED; identical to L3 |
| a_cor / a_cor_refusal | false / "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED; identical to L3 |
| a_del / a_del_refusal | false / "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED; identical to L3 |
| a_disp / a_disp_refusal | false / "fact_not_found" | Q_CLOSED | VERIFIED | DERIVED; identical to L3 |
| a_disp_fact / a_disp_fact_refusal | false / "already_deleted" | Q_CLOSED | VERIFIED | DERIVED; identical to L3 |

The control omits `a_rem` (the documented disclosure: on an open id the owner's `remember` would commit), as the L3 invariant statement says. Correct.

### L5b-a-deleted-head-or-version-cannot-be-deleted-again

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| again_head | eq false | Q_CLOSED | VERIFIED | DERIVED ("a governed pruning of one of its versions" → `already_deleted`) |
| again_head_refusal | eq "already_deleted" | Q_CLOSED | VERIFIED | DERIVED |
| again_member | eq false | Q_CLOSED | VERIFIED | DERIVED ("the adapter's delete of a member of a deleted lineage") |
| again_member_refusal | eq "already_deleted" | Q_CLOSED | VERIFIED | DERIVED |
| head_tombstone_unchanged | eq true | Q_786_FC | PARAPHRASED | DERIVED for `state_version` and `deleted_fact_uuids` (lineage) and the other record fields; **WEAKER than the L5 invariant statement for `deleted_at`**: `_fold` replaces the clock's `YYYY-MM-DDTHH:MM:SSZ` by `T` before comparison, so a rewritten `deleted_at` (the very symptom F-C names first) would not be detected (check 4, finding F-2) |
| member_tombstone_unchanged | eq true | Q_786_FC | PARAPHRASED | DERIVED but near-vacuous: a lineage member has no tombstone record of its own (`_tombstones` is keyed by the deleted head), so `ts_member` is `None` and the probe asserts `None == None`; it detects only a *created* member tombstone, not a rewritten lineage (that is `head_tombstone_unchanged`'s job). The L5 statement's "recorded tombstone … unchanged" reads as if a member record existed |
| historical | eq [] | Q_L1 | VERIFIED | DERIVED (after reopen) |
| old_semantics | eq false | Q_L1 | VERIFIED | DERIVED (cite: docs/774-776 l.138-140, as L2) |
| at_v1 | eq null | Q_774 | VERIFIED | DERIVED ("Never cross a deleted-lineage boundary") |
| owner_history | eq {null, 3, true, []} | Q_PLAN_OWNER, Q_GEN | PARAPHRASED / VERIFIED | DERIVED (N-7); also the version survives the refused re-deletions |

`record`/`implementation_evidence`: `head_tombstone` (the folded record; useful for the owner to see `mode`, `reversible`, lineage, version).

### L4-three-generations-as-of-barriers

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| owner_at_gen3 | eq "gen3" | Q_774 | VERIFIED | DERIVED (positive: the owner's live generation resolves at its own instant) |
| other_at_gen3 | eq null | Q_774 | VERIFIED | DERIVED (cite: docs/774-776 l.147-148 "If the resolved successor is outside reader scope or has been deleted, return no predecessor without leaking the fact ID"; Q_774 "verify admission") |
| owner_at_v1 | eq null | Q_774, Q_LX | VERIFIED / PARAPHRASED | DERIVED |
| owner_at_v2 | eq null | Q_774, Q_LX | VERIFIED / PARAPHRASED | DERIVED |
| owner_at_genb | eq null | Q_774 | VERIFIED | DERIVED (B's generation: deleted, and out of A's scope) |
| other_at_genb | eq null | Q_774 | VERIFIED | DERIVED (B's own deleted generation) |
| other_at_v2 | eq null | Q_774 | VERIFIED | DERIVED |
| head | eq "gen3" | Q_LX, Q_786_GEN | PARAPHRASED | DERIVED |
| b_back | eq false | Q_786_GEN | PARAPHRASED | DERIVED (the clause with the roles mirrored: the former owner B cannot write while A's generation is live) |
| other_history | eq {null, 2, true, []} | Q_GEN, Q_PLAN_OWNER | VERIFIED / PARAPHRASED | DERIVED (B reads the version its own deletion recorded, one write + deletion = 2, N-7; A's later gen3 is invisible to B) |

### L5-partial-deletion-withholds-only-that-version

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| d1 | eq true | Q_L3 | VERIFIED | DERIVED (positive control the clause presupposes) |
| deleted_mentions | eq [] (`memory:f@2`→uuid, `noon`) | Q_L3 | VERIFIED | DERIVED (cite: Q_L1 "without returning any old deleted version in explicit historical retrieval"; Q_L3 says what is *not* hidden) |
| kept_mentions | eq ["memory:f", "memory:f@3"] | Q_L3 | VERIFIED | `memory:f@3` DERIVED ("must not … hide it from current recall"; here historical recall, a fortiori); `memory:f` (the superseded, undeleted v1 served in historical recall) DERIVED (cite: docs/774-776 l.144-145 "Ordinary stated state-change history remains reachable when not deleted", the sentence the Q_LX quote truncates) |
| head | eq "memory:f@3" | Q_L3, Q_LX | VERIFIED / PARAPHRASED | DERIVED ("Deletion of one superseded fact must not hide its live successor") |
| current | eq ["memory:f@3"] | Q_L3, Q_LX | VERIFIED / PARAPHRASED | DERIVED |

### L5-partial-deletion-withholds-only-that-version-after-restart

Same five observables (`d1`, `deleted_mentions_after`, `kept_mentions_after`, `head_after`, `current_after`) after `reopen`: same derivations. Closes `-v2` finding 10.

### L6-permanent-deletion-removes-canonical-facts-and-withholds-every-public-read

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| p1 | eq true | Q_28_PRUNE | PARAPHRASED | DERIVED (positive control the clause presupposes; "deleted memory follows stronger semantics") |
| v1_exists | eq false | Q_28_PRUNE | PARAPHRASED | DERIVED (cite: docs/786 l.78 "permanent forget … physically deletes … lineage"; docs/28 "stronger semantics" alone does not say the canonical accessor returns nothing). Probe: `_substrate.get_fact(uuid) is None`, one accessor, as the bounded L6 statement now says |
| v2_exists | eq false | Q_28_PRUNE | PARAPHRASED | as `v1_exists` ("it removes every version in the deleted lineage" is the adapter comment, l.2149-2150, not a contract sentence) |
| mentions | eq [] | Q_L1 | VERIFIED | DERIVED |
| other_unknown | eq true | Q_PLAN_OTHER | VERIFIED | DERIVED |
| other_history_mentions | eq [] | Q_PLAN_OTHER | VERIFIED | DERIVED |
| old_semantics | eq false | Q_L1 | VERIFIED | DERIVED (cite: docs/774-776 l.138-140) |
| owner_history | eq {null, 3, true, []} | Q_PLAN_OWNER, Q_GEN | PARAPHRASED / VERIFIED | DERIVED (a permanent deletion is a governed head deletion; the tombstone survives with its recorded version; N-7) |
| derived | eq {status "complete", stores_checked 0, pending []} | Q_DERIVED, Q_28_CLAIM | VERIFIED | `status: "complete"` DERIVED (every `open` reconciles and reports; complete = nothing unsafe/foreign/failed; nothing under `<root>/derived` on a fresh root); `pending: []` DERIVED (`open` sets it to `[]` always, and complete ⇒ no pending); **`stores_checked: 0` NOT DERIVABLE from a clause**: it is the runner's configuration (`AgentMemory.open` with `SEMANTIC_RETRIEVAL_DEFAULT = "off"`, no sidecar ever created), i.e. a statement that there is nothing to reconcile, not that reconciliation reconciled anything (check 5) |

## R family: `public-tombstone-redaction-and-observer-separation-v3` (8 cases, 34 expectations)

### R1-owner-tombstone-live

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| owner_history | eq {null, 3, true, []} | Q_PLAN_OWNER, Q_GEN | PARAPHRASED / VERIFIED | DERIVED (the projection emits exactly these four fields for a tombstoned view, `surface.py` l.1266-1269; N-7 for the numeral) |
| owner_probe | eq {null, 3, true, [], rejected_values 0} | Q_PLAN_OWNER | PARAPHRASED | DERIVED ("with a value probe, `rejected_values: []`"; the runner projects the count) |
| mentions | eq [] (both uuids, `early`, `late`) | Q_PLAN_OWNER | PARAPHRASED | DERIVED |

### R1-owner-tombstone-after-restart

Same three observables after `reopen`: DERIVED (plan l.40 "live and restart reads"). Closes the `-v2` R1 note (value probe now repeated after restart).

### R2-other-reads-unknown-live

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| history | eq true | Q_PLAN_OTHER, Q_777 | VERIFIED / fragment NOT FOUND | DERIVED from Q_PLAN_OTHER alone |
| value_probe | eq true | Q_PLAN_OTHER, Q_777 | VERIFIED / fragment NOT FOUND | DERIVED from Q_PLAN_OTHER |
| by_ref | eq true | Q_PLAN_OTHER, Q_777 | VERIFIED / fragment NOT FOUND | DERIVED from Q_PLAN_OTHER |
| historical | eq [] | Q_PLAN_OTHER | VERIFIED | DERIVED |

### R2-other-reads-unknown-after-restart

`history`, `value_probe`, `by_ref` eq true after `reopen`: DERIVED from Q_PLAN_OTHER (plan l.40-41 "live and restart reads, other-project indistinguishability (history and logical-reference recall)"). Q_777's first fragment is misattributed as above.

### R3-owner-view-stable-under-other-scope-with-distinct-generation-lengths

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| owner_history | eq {null, 3, true, []} | Q_GEN, Q_PLAN_OWNER | VERIFIED / PARAPHRASED | DERIVED: A wrote v1, v2 and deleted (records 3); "the owner of the deleted generation still reads the version its deletion recorded" and nothing B does later (re-creation, reopen, deletion at 2) is visible to A (check 3) |
| owner_mentions | eq [] (`gen-b`→uuid, `mid`) | Q_786_GEN | PARAPHRASED | DERIVED |
| other_history | eq {null, 2, true, []} | Q_GEN, Q_PLAN_OWNER | VERIFIED / PARAPHRASED | DERIVED: B's generation is v1 and its deletion records 2; A's deletion (3) is of a head B could not read, so it is not B's "deletion it could have read" (plan l.32-33) |
| b1_before | eq "v0" | Q_GEN | VERIFIED | DERIVED |
| b1_after | eq "v1" | Q_GEN | VERIFIED | DERIVED |
| b3_after | eq "v2" | Q_GEN | VERIFIED | DERIVED (B's deletion receipt counts within B's generation: v1 → v2; N-7) |

### R4-derived-from-deleted-withheld-live-derivation-kept

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| withheld | eq [] (`digest`→uuid, `memory:t`→uuid, `early`) | Q_777, Q_PLAN_OWNER | fragment NOT FOUND / PARAPHRASED | DERIVED: `memory:t` uuid and `early` from Q_PLAN_OWNER ("no deleted-generation identifier … or value is served"); the `digest` uuid (a memory citing the deleted fact as evidence) from docs/777 "no regression to transitive deleted content refusal" and docs/plan l.42 "derived memories citing a deleted source" (unquoted). The query echoes `digest` and `early`, but `digest` is relabelled to its uuid and the recall result does not echo the query (the identical probe is in `-v2` and recorded `[]`) |
| kept | eq ["live", "live-digest"] | Q_777 | fragment NOT FOUND | NOT DERIVABLE: no cited clause says a live derivation and its source remain served; this is a positive control (the R4 statement's "while a live derivation keeps its provenance"). Keep it, but it does not "follow from" docs/777 |

### R6b-refused-proposals-on-the-tombstoned-id-carry-no-former-count

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| parked_after | eq "v0" | Q_GEN | VERIFIED | DERIVED (cite: docs/786 l.132 F-A). The precondition that the `medium` proposal parks is not pinned directly, but a commit would make the next `gen-b` write a v2 correction and `parked_after` `v1`, so the expectation detects it |
| parked_mentions | eq [] (`v3`, both old uuids, `early`, `late`) | Q_GEN | VERIFIED | DERIVED ("the former generation's count never reaches the new one") |
| a_back_mentions | eq [] (`gen-b`→uuid, `mid`, `v1`) | Q_GEN | VERIFIED | DERIVED (cite: Q_REM `v0` states; docs/786 l.69-70 non-disclosure) |
| a_disp | eq false | Q_CLOSED | VERIFIED | DERIVED (dispute of `memory:t@2`, a tombstoned fact, by uuid) |
| a_disp_mentions | eq [] (`gen-b`→uuid, `mid`, `v1`) | Q_CLOSED | VERIFIED | DERIVED ("neither moves or reads the live generation"; `v0` states) |
| other_view | eq {gen-b, 1, false} | Q_GEN | VERIFIED | DERIVED (the new generation's history counts from 1) |
| other_history_mentions | eq [] (A's uuids, `early`, `late`, `v3`, `project:a`) | Q_PLAN_RECREATED | VERIFIED | DERIVED |

`record`/`implementation_evidence`: `other_history` (the seven-event list that `-v2` corrected toward observed output). Correct closure of `-v2` finding 4(c): the public view is pinned without the event list.

### R5-recreated-history-only-own-events

| observable | matcher | clause | quote | derivation |
|---|---|---|---|---|
| other_history | eq {gen-b, 1, false, 4 events} | Q_786_F7, Q_PLAN_RECREATED | PARAPHRASED / VERIFIED | DERIVED (A's refused `remember` correlation withheld; one write ⇒ one write's events); vocab STRONGER |
| other_history_mentions | eq [] (`memory:t`→A's uuid, `early`, `late`, `v2`, `project:a`) | Q_PLAN_RECREATED | VERIFIED | DERIVED |
| a_back | eq false | Q_786_F7, Q_REM | PARAPHRASED / VERIFIED | DERIVED |
| b1_snapshot | eq "v0" | Q_GEN | VERIFIED | DERIVED |
| b1_before | eq "v0" | Q_GEN | VERIFIED | DERIVED |
| b1_after | eq "v1" | Q_GEN | VERIFIED | DERIVED |

## 1. Closure of the 14 findings of the `-v2` review

| `-v2` finding | `-v3` status | where |
|---|---|---|
| 1. sources hashed at the pre-remediation contract (`560785a8`) | **CLOSED.** `base_commit` is `8c2a71c0`; all seven hashes verified; docs/44 l.187/188/190/194 and docs/786 F-A..F-H, F-R3-*, "Scope is privileged host input" are present at that revision | W7c, W7c-control, W8b, L5b, L3, R6b (`already_deleted`, generation-relative versions, host input) |
| 2. W4/W4b presented the complete-scope override as a facade property | **CLOSED.** W4 invariant statement restated ("ONLY because `overrides` is privileged host input … host re-declaration, never end-user isolation"); W4b cites Q_HOST and Q_786_W4; stop line added | W4, W4b |
| 3. verifier default declaration absent at `e5abd116` | **Outside the fixtures; a new inconsistency of the same kind appears** (finding F-9 below): at `679cefbf` `scripts/verify_786_security_replays.py` defaults `EVIDENCE_ROOT` to `reports/validation/786-security-replays-v3/` while `DECLARATION` (`786-cumulative-v6-to-v8.PROPOSED.json`) still lists only the three `-v2` ids | — |
| 4. direction of the post-execution corrections (W5 `owner_candidates`, W4b `k2_owner_recall`, R6b `other_history`) | **CLOSED.** `k2_owner_recall` and R6b `other_history` are `record`/`implementation_evidence`, never expected; `owner_candidates` stays expected with Q_CAND cited (its order is STRONGER than the clause, N-8) | W4b, R6b, W5 |
| 5. one shared `development_history` literal | **CLOSED.** Each fixture carries its own `development_history`. (The `-v3` `supersession_reason` and the generator docstring map "former-owner observables had no no-re-creation control" to "finding 5"; in the `-v2` record that gap is in the W7c/L3 table rows and finding 9, not finding 5. A provenance-text inaccuracy, N-12) | all three |
| 6. L6 oversold ("erases", "no byte … reaches a public read") | **CLOSED.** Case renamed; statement bounded to canonical facts and public reads with an explicit non-claim; `derived_reconciliation` probe added. Residual: "no public read of any scope" is probed for A's historical recall / `write_semantics` and B's `history`, not for every public read (N-13) | L6 |
| 7. live-generation histories compared by event type and count only | **PARTIALLY CLOSED.** `history_mentions` scans the whole serialised history for the former generation's uuids (effective) and for text/scope tokens (inert: audit events carry no fact text or scope, see Method). The former generation's event/correlation/receipt ids are not tokens, so a leak of a former-generation *event* would still be caught only by the event count. Payload-level cleanliness is now shown for identifiers, not for "any text" | W7, W7b, W7c, W8, L2, L3, L6, R5, R6b |
| 8. R3's two deletions recorded the same version | **CLOSED.** A: v1, v2, delete ⇒ 3; B: v1, delete ⇒ 2; both pinned (check 3) | R3 |
| 9. docs/44 l.187 and the facade disagreed on the token for ref-level `forget`/`dispute` | **CLOSED** on the contract side at `8c2a71c0` (the clause now distinguishes the fact level and the logical-reference level and cites the review) and on the fixture side: both levels are pinned with and without a re-creation | L3, L3-control, W7c, W7c-control |
| 10. L5 promised a restart it did not perform | **CLOSED.** `L5-…-after-restart` added | L5 |
| 11. W4's `ValueError` pinned by type only | **CLOSED.** `op_raised_message` pins the message for both targets; the literal equals `surface.py` l.692 (check 6) | W4 |
| 12. restart = handle reopen in one process | **LEFT** (by design; DSL/2 inherits `reopen`). Not misdescribed by the fixtures, but the W3 clause "survives every restart" is still shown only for reloaded SQLite state | W3, W6, W8, W8b, L1, L2, L3, L3-control, L4, L5, L5b, L6, R1, R2, R3, R5 |
| 13. L fixture omitted docs/44 and docs/plan-776-777-772 | **CLOSED.** The L fixture lists docs/44, docs/plan-776-777-772 and docs/28 and cites them | L1, L3, L4, L5b, L6 |
| 14. provenance / dirty-tree block | **unchanged, carried forward.** DSL/2 `provenance()` keeps the dirty block (output dir `786-security-replays-v3/` excluded) and records both the DSL/2 and the frozen DSL/1 runner hashes | runner |

## 2. Controls (W7c-control, L3-control)

- W7c vs W7c-control pin the same literals for every observable the contract says must not differ: `a_disp` false / `already_deleted`, `a_del` false / `already_deleted`, `a_forget` false / `fact_not_found`, `a_disp_mentions` `[]` (the control's token set `{v1, v2}` is the subset of W7c's `{gen-b, dusk, v1, v2}` that has a meaning without a re-creation). Confirmed identical.
- L3 vs L3-control: `a_cor`, `a_del` (facade `forget`), `a_disp` (by ref) false / `fact_not_found`; `a_disp_fact` false / `already_deleted`; `owner_history` `{null, 3, true, []}`. Confirmed identical.
- The documented difference (`remember` on an open id commits; on a foreign live head it is refused `target_unavailable`, docs/786 l.174 and the L3 statement) is excluded from both controls: neither W7c-control nor L3-control has an `a_rem` step. Confirmed.
- Limits: the equality is pinned field by field (`committed`, `refusal`, absence of version tokens), not as whole-result equality across the two cases (the DSL cannot compare results across cases). W7c-control pins A's `owner_history` while W7c does not probe it; the "same view with a re-creation" half is pinned in W8 and R3 instead.

## 3. R3 under the generation-relative rule

docs/44 l.190 (Q_GEN) at `8c2a71c0`: `before_state`/`after_state` "count within the live generation of a logical id … the owner of the deleted generation still reads the version its deletion recorded". A's generation: `remember` (v1), `correct` (v2), `forget` (the deletion's receipt records 3: a governed deletion is the generation's last state change, `adapter.py` l.2161-2163 increments and stores it in the tombstone). B's generation starts at 0 (`b1_before v0`, `b1_after v1`), `forget` records 2 (`b3_after v2`). The expectations pin A `owner_history.state_version 3` and B `other_history.state_version 2`, and `public_deleted_version` serves each reader "the latest head deletion this reader could have read" (adapter l.1877-1898), which for A excludes B's (unreadable) head and for B excludes A's. A runtime serving the latest deletion regardless of scope would give A 2 (caught by `owner_history`); one serving the largest would give B 3 (caught by `other_history`). The discriminator the `-v2` review asked for is present. The numeral itself rests on "a deletion records v+1", which no contract sentence states in those words (N-7).

## 4. L5b `tombstone_unchanged`

The docs/786 F-C row (Q_786_FC, paraphrased) and the docs/44 l.187 escalation sentence support "a re-deletion attempt leaves the tombstone unchanged" in all three named fields: `already_deleted` means no governed act commits, and "only pruning -> permanent deletion is a further governed act, and that escalation keeps `deleted_at`, `state_version` and the lineage". No field can legitimately change on a refused re-deletion; the only legitimate change to a tombstone is the escalation's `mode`/`reversible`/`declared_derived_refs`/widened `deleted_fact_uuids` (adapter l.2124-2133), which L5b does not perform. The probe, however, compares the record after `_fold`, which replaces the `deleted_at` timestamp by `T`; so of the three fields the invariant names, `deleted_at` is not actually compared (finding F-2). `state_version` and `deleted_fact_uuids` (relabelled) are compared and would catch F-C's "shrunken lineage". `member_tombstone_unchanged` compares `None` with `None` because only the head carries a record; it detects a *created* member tombstone and nothing else.

## 5. L6 statement vs probes; `derived_reconciliation`

The L6 statement claims four things: (i) "the canonical substrate holds no fact of the lineage" — probed by `fact_exists` (`_substrate.get_fact`) for the two uuids: matches; (ii) "no public read of any scope serves an identifier or text of it" — probed for A's historical `recall` (`mentions`), A's `write_semantics` (`old_semantics`), B's `history` (`other_unknown`, `other_history_mentions`): the statement generalises over "any scope" and "any public read" from two scopes and three reads (A's `history`, which is a public read, is pinned as the tombstone view; B's `recall` is not probed). Slightly STRONGER in wording, honest in its exclusions; (iii) "the derived-store reconciliation reports complete" — probed; (iv) "the owner still reads tombstoned" — probed. The explicit non-claim (journals, WAL, backups, snapshots, filesystem) matches docs/44 l.108 and docs/28 l.163.

`derived` `{status: "complete", stores_checked: 0, pending: []}`: at `8c2a71c0`, `AgentMemory.open` always calls `_reconcile_cached_representations` and sets `pending = []`; `reconcile_derived_vector_stores` starts from `{"status": "complete", "stores_checked": 0, …}` and returns it unchanged when `<root>/derived` does not exist (`representation_cache.py` l.324-334). The runner opens with the default `semantic_retrieval = "off"` (`SEMANTIC_RETRIEVAL_DEFAULT`, `surface.py` l.350), so no sidecar is ever created under the scenario root. The probe reads the posture *after* `reopen`, i.e. the open-time report (the forget-time report is overwritten by `open`), which is what the Q_DERIVED clause names ("every `open`"). So `status` and `pending` are derivable; `stores_checked: 0` is a true statement about the runner's configuration (nothing to check), not about reconciliation behaviour, and would be better recorded than expected (or pinned as `status` only), because a future runner with the semantic route on would fail this case for a non-contract reason.

## 6. W4 `ValueError` message

`MALFORMED = "required isolation domains must also be bound isolation domains"` (generator l.53; fixture `bad_target_message`/`bad_unknown_message`). `reference/agentmem_ref/api/surface.py` at `8c2a71c0`, l.692: `raise ValueError("required isolation domains must also be bound isolation domains")`, raised in `_proposal` after `envelope.update(overrides)` and before `_state_snapshot` resolves any target (l.686-695). Identical. The DSL/2 `_raised_message` re-executes the step to capture the message; this is side-effect free exactly because the raise precedes any target resolution, which the same code shows. The other `ValueError` in that block ("facade proposal overrides may not replace protected fields") is not reachable by these overrides.

## 7. Implementation evidence

`record` = `implementation_evidence` in every case that has them, and none of their keys is in `expect`: W4 `sup_cor_refusal`; W4b `k2_owner_recall`; L2 `old_exists`; L5b `head_tombstone`; R6b `other_history`. DSL/2 `run_case` writes `recorded` from `record` and `checks` from `expect` only, so recorded observables cannot affect the verdict. The three `-v2` not-derivable sub-expectations (finding 4) are all here.

Expected observables that are closer to implementation or configuration evidence than to contract derivation: `L6.derived.stores_checked` (runner configuration); `W4.bad_target_message`/`bad_unknown_message` literal (implementation text; the contract claim is only their equality, which a two-message equality probe would pin without the literal); `W6.parked_committed`, `W8b.parked_b` (policy-table preconditions); `W5.owner_candidates` order (ranking order); the event-type vocabulary in nine `history` expectations (the contract claim is the count). None of these is a security claim and none contradicts a clause; they are listed so the owner can decide whether a `-v4` should move them.

## 8. Preregistration integrity

- The three `-v3` fixtures, `author_fixtures_v3.py`, `run_786_security_replays_dsl2.py`, the README section and the verifier change first appear in `679cefbf` (`git log -- reference/fixtures/786-security-replays/` shows no earlier commit touching `*-v3.json`); the fixtures' `frozen_on` is `2026-10-15`, the commit date.
- `reports/validation/786-security-replays-v3/` does not exist at `679cefbf` (`ls` fails); no `-v3` evidence is committed. The working tree is clean.
- `independence` says the comparison record "is committed beside the evidence"; this record is written to the scratchpad only, outside the repository, as instructed.
- The generator's self-checks (coverage, sources, evidence/expect disjointness, probe existence) hold on the committed JSON (re-verified independently).

## 9. What an adversarial or degenerate runtime would satisfy, and which cases catch it

- **Refuse-everything runtime** (every write refused): every case has at least one `require_committed` seed step except W5, so 30 cases end in `scenario error` (outcome `error`, verdict FAIL); W5 fails on `a1`/`a2`/`a3`/`b1` eq true. Positive expectations that would also flip: W4b `sup_disp`/`sup_forget`/`complete`/`tombstones`, W6 `kept_committed`/`episode_kept`, W7c `other_recall`, W8 `b1_after v1`/`b2_after v2`, L2 `historical [gen2]`/`new_semantics`, L4 `owner_at_gen3`/`head`, L5 `d1`/`current`, L6 `p1`, R3 `b1_after`/`b3_after`, R4 `kept`, R5 `b1_after`, R6b `other_view`.
- **Scope-ignoring writes** (any same-tenant write commits): W1 `b1_committed`, W2 (four `op_same_as_unknown`, `tombstones`, `disputed`, `valid`), W3, W4 `sup_rem_committed`/`sup_cor_committed`, W6 `denied_committed`, W7 `canonical_version`/`owner_history`, W7b, W7c `a_rem`, W8 `a_back`, L3 `a_rem`/`a_cor`/`a_del`/`a_disp`, L4 `b_back`, R5 `a_back`, R6b `other_view.state_version`.
- **Scope-ignoring reads** (serve everything to everyone): W1 `other_recall`/`other_history_unknown`, W5 `other_recall`/`other_view_of_k`/`owner_view_of_other`, W7/W7b `other_history_unknown`, W8b `other_history`, L3 `owner_mentions`/`other_mentions`/`owner_historical`, L4 `other_at_gen3`, L6 `other_unknown`, R2 (all), R3 `owner_mentions`.
- **A runtime that never deletes** (forget commits but withholds nothing): L1 `current`/`historical`/`mentions`/`owner_history.tombstoned`, L6 `v1_exists`/`v2_exists`, R1, R4 `withheld`, L5 `deleted_mentions`.
- **A global tombstone set** (a deleted id stays dead): W8 `b1_after v1`/`other_history`, L2 `historical [gen2]`/`owner_history`, L4 `owner_at_gen3`, R5 `other_history`, R6b `other_view`.
- **A runtime that reports `v0` on every receipt**: W8 `b1_after`/`b2_before`/`b2_after`, R3 `b1_after`/`b3_after`, R5 `b1_after`.
- **An oracle through `already_deleted` vs `fact_not_found`** (answer depends on a foreign re-creation): W7c vs W7c-control, L3 vs L3-control.
- **A runtime that ignores `overrides`**: W4 `bad_*` (no `ValueError`), W4b `complete`/`sup_disp`/`sup_forget`.
- **Expectations an adversary satisfies trivially** (they add no discrimination on their own): the text/scope tokens of every `history_mentions` probe (inert at this runtime); `member_tombstone_unchanged` (`None == None`); W4 `tombstones []` (no deletion attempted); W6 `parked_head null` (follows from the park); L6 `derived` on a semantic-off runner. None of these is load-bearing alone; each sits beside a load-bearing observable in the same case.

## Findings

Severity: BLOCKING / SHOULD FIX / NOTE. No BLOCKING finding.

**F-1. SHOULD FIX (traceability). A quoted clause is attributed to the wrong source.** `Q_777` = "out-of-scope indistinguishability ... no regression to transitive deleted content refusal" is cited as `docs/777-public-contract-1-7-successor-qualification.md` in R2-live, R2-after-restart and R4. The first fragment does not occur in docs/777 at `8c2a71c0`; it is docs/plan-776-777-772 l.28. The second fragment is docs/777 l.283-284, phrased as a requirement on "a future integrated successor" rather than as a behaviour. R2's expectations are fully derivable from Q_PLAN_OTHER, which is cited beside it; R4 `withheld` is derivable from Q_PLAN_OWNER plus docs/plan l.42 ("derived memories citing a deleted source"). No expectation is unsupported, but the fixture's claim that each clause is "quoted from the sources at BASE_COMMIT" is false for this one.

**F-2. SHOULD FIX. L5b's `tombstone_unchanged` cannot see `deleted_at`.** DSL/2 `_tombstone()` applies `_fold`, which rewrites `YYYY-MM-DDTHH:MM:SSZ` (the adapter clock's exact format, `adapter.py` l.55) to `T`, before the snapshot and the comparison. The L5 invariant says the attempt "leaves the recorded tombstone (deleted_at, version, lineage) unchanged"; the probe establishes version and lineage only. F-C's first symptom was precisely "new `deleted_at`". A `-v4` (or a DSL/2 patch before first execution, since the runner is not frozen until evidence exists) should snapshot the unfolded `deleted_at` (or hash it) and compare it; `member_tombstone_unchanged` should be described as "no tombstone record is created for a lineage member" rather than as an unchanged record.

**F-3. SHOULD FIX (traceability). Nine quoted clauses are paraphrases presented as quotations.** Q_786_F7, Q_786_RESTART, Q_786_SAME, Q_786_GEN, Q_786_FC, Q_LX, Q_PLAN_OWNER, Q_28_PRUNE (see legend). Two of them matter beyond wording: Q_786_GEN splices a table row and a sentence from a different section into one "clause" (cited 8 times); Q_786_FC drops "for a tombstoned fact or a direct member of a deleted lineage", the words that derive `again_member`, and Q_LX drops "Ordinary stated state-change history remains reachable when not deleted", the words that derive L5 `kept_mentions`' `memory:f`. Every paraphrase preserves the source's sense, so no derivation fails; but a reviewer checking the quotes verbatim (as the generator invites) finds 9 of 32 absent. A `-v4` should quote verbatim with marked elisions (table rows as `cell | cell`).

**F-4. SHOULD FIX (traceability). Observables cited under a clause whose premise does not cover them.** W4 `sup_rem_refusal`/`sup_rem_before` cite Q_REM ("a live head outside the writer's scope"), but the superset writer is an eligible reader and is refused by scope continuity; the deriving sentences are docs/786 l.53 and l.55-56 (promotion refusal token and `v0/v0` for any refused target) and l.101 (F2). W1/W7/W7b `other_history_unknown` cite Q_CFD (write results), not Q_PLAN_OTHER (reads). L1 `by_ref_unknown` cites Q_786_GEN ("as-of barrier") where Q_PLAN_OWNER (cited in the same case) is the deriving clause. L6 `v1_exists`/`v2_exists` cite the docs/28 prune/delete sentence, which does not say the canonical accessor returns nothing; docs/786 l.78 does. All are derivable from a listed source; the citations are imprecise, which weakens the "clause by clause" promise of `independence`.

**F-5. NOTE. Three expectations are policy or configuration preconditions, not contract derivations.** W6 `parked_committed`, W8b `parked_b` (and the unpinned park in R6b) rest on `core/policy.py` l.88-89 (`promotion` at `medium`/`high` → `REQUIRE_REVIEW`); L6 `derived.stores_checked: 0` rests on the runner opening with `semantic_retrieval="off"`. They are true at `8c2a71c0` and harmless, but they are the kind of expectation that fails for a non-contract reason when the policy table or the runner configuration changes; `implementation_evidence`, or a `require`-style precondition, would be the honest place.

**F-6. NOTE. Text and scope tokens in `history_mentions` are inert.** Audit events never carry fact text, a scope ref or a fact uuid (`build_audit_event`), so of the tokens scanned over a `history` payload only the label (uuid) tokens can ever match; `dawn`, `noon`, `night`, `early`, `late`, `dusk`, `mid`, `midnight`, `project:a`, `project:b`, `dispute`, `forget` cannot. Finding 7 of the `-v2` review is therefore closed for identifiers, not for "any text". Separately, W8's token `night` is a substring of B's own `midnight`; it is safe only because of this inertness, and a future projection that echoed fact text would make W8 fail for B's own content rather than A's. A `-v4` should choose tokens that are not substrings of in-scope text.

**F-7. NOTE. The tombstone numerals (A 3, B 2, W7c-control 2) rest on "a governed deletion records v+1".** Q_GEN says the owner "reads the version its deletion recorded" and that receipts "count within the live generation"; that the deletion itself advances the count (so two writes and a deletion record 3) is adapter behaviour (`governed_delete`, l.2161-2163) and is not written in any cited clause. The fixture pins the numeral consistently in 13 expectations (L1 x2, L3 x2, L4, L5b, L6, W7c-control, W8, W8b, R1 x2, R3 x2, and `b3_after v2`). Derivable under the natural reading of "recorded"; flagged because a contract reader could also read "the version at deletion" (2 and 1).

**F-8. NOTE. Two expectations pin more than the clause.** W5 `owner_candidates` pins the order `[memory:k, memory:k@2]`; Q_CAND says only that both remain visible candidates. Nine `history` expectations pin the exact event-type vocabulary (`memory.propose, memory.authorize, memory.commit, memory.receipt`), which no contract source lists (docs/44 l.45: "commit and deletion events"); the contract-bearing part is the count.

**F-9. NOTE. The verifier's defaults are inconsistent at `679cefbf`.** `scripts/verify_786_security_replays.py` now defaults `EVIDENCE_ROOT` to `reports/validation/786-security-replays-v3/` but `DECLARATION` still points at `786-cumulative-v6-to-v8.PROPOSED.json`, which lists only the three `-v2` ids (l.106-115). A default `verify()` would look for `-v2` evidence under the `-v3` root and find none until the declaration names the `-v3` ids. Not a fixture defect; the same class as `-v2` finding 3.

**F-10. NOTE. docs/44 l.86 and the owner's deleted-id recall.** L1 `by_ref_unknown` (owner's `recall(logical_memory_refs=[memory:f], historical)` byte-identical to the never-written id) follows from docs/plan l.32-37 (no deleted-generation identifier served). docs/44 l.86 still says `tombstoned` lifecycle refusals "remain visible candidates with decisions, as before" (pre-#777 wording). The fixture follows the later, more specific document; the owner may want docs/44 l.86 reconciled with #777/DUR-DEL-001.

**F-11. NOTE. L2 cites a clause for a recorded observable.** `old_exists` is listed under the docs/28 prune/delete clause and also under `implementation_evidence`; the generator's own rule is that evidence observables are the ones no clause derives. Either the clause derives it (then it could be expected: "pruned memory remains recoverable under policy" does predict the fact's physical presence after a reversible `forget`) or the citation should go. Harmless either way.

**F-12. NOTE. Provenance text numbering.** The `supersession_reason` (identical in all three fixtures) and the generator docstring attribute the missing no-re-creation control to "finding 5" of the `-v2` review; in that record finding 5 is the shared `development_history` literal and the control gap is in the W7c/L3 rows and finding 9. The substance of the closure is right; the pointer is wrong.

**F-13. NOTE. L6's "no public read of any scope".** Probed: A historical recall, A `write_semantics`, B `history`; A's `history` is pinned as the tombstone view. Not probed: A's non-historical recall or recall by logical reference, B's recall. The statement is a little wider than the probes; the bounded non-claim is correct.

**F-14. NOTE. Restart remains a handle reopen** (`-v2` finding 12, by design); W3's "survives every restart" and the eight "after restart" cases show durability of the SQLite-backed state a handle reloads, not of a process.

**F-15. NOTE (preregistration order). A test that executes the `-v3` fixtures exists in the working tree before this record is committed.** The untracked `reference/tests/test_786_security_replays_v3.py` (`test_every_case_of_every_replay_passes`, `test_a_weakened_runtime_would_be_caught`, `test_untampered_evidence_verifies_and_a_mutated_report_is_tampered`) runs `run_replay(..., allow_dirty=True)` on every `-v3` fixture. Such a run produces a `BLOCKED` verdict and no committed evidence, but it is an execution, and the fixtures' `independence` field says the comparison happened "before this fixture was first executed by the runner". The repository cannot show the order. The owner should record, in the evidence README or the acceptance record, that this review (written from `679cefbf`) preceded the first run of that test and of the runner, or state otherwise.

## Verdict (no approval; the record is input to the owner's decision)

**All 240 expectations are consistent with the contract sources at `8c2a71c0`: none is WRONG, and none contradicts a clause.** The fixtures are committed before execution, their sources are hashed at a revision that contains every clause they rely on, the five previously not-derivable or corrected-toward-output sub-expectations are now recorded rather than expected, and the controls, R3 lengths, L5 restart, `ValueError` message and payload scans the `-v2` review asked for are present.

The four groups below are disjoint and name 52 distinct expectations; the remaining **188 of 240 are DERIVED from the quoted clause as cited**.

**DERIVED from the cited source, but from a sentence other than the quoted clause (citation imprecise; 34):** W1 `b1_mentions` (uuid/text/project tokens), `other_recall`, `other_history_unknown`; W2 `tombstones`, `disputed`, `valid`; W3 `b1_mentions` (same tokens as W1); W4 `sup_rem_refusal`, `sup_rem_before`; W5 `a2`, `a3`, `disputed`; W6 `kept_committed`, `episode_kept`; W7 `other_history_unknown`; W7b `bd`, `bf`, `bdf`, `other_history_unknown`; W7c-control `a_disp_mentions`; L1-live and L1-after-restart `by_ref_unknown`; L2 `old_semantics`, `new_semantics`; L4 `other_at_gen3`; L5 and L5-after-restart `deleted_mentions`, `kept_mentions` (the `memory:f` token); L5b `old_semantics`; L6 `v1_exists`, `v2_exists`, `old_semantics`; R6b `a_back_mentions`.

**NOT DERIVABLE from any clause of the listed sources (6, none a security claim):** W6 `parked_committed` (policy table), W8b `parked_b` (policy table), R4 `kept` (positive control), L6 `derived` for its `stores_checked: 0` component (runner configuration; `status`/`pending` derivable), W4 `bad_target_message` and `bad_unknown_message` for their literal (implementation text at `surface.py` l.692; their equality is derivable).

**STRONGER than the clause (10, harmless):** W5 `owner_candidates` (order); the event vocabulary in W1 `owner_history`, W3 `owner_history`, W7 `owner_history`, W7b `owner_history`, W7c `other_history`, W8 `other_history`, L2 `owner_history`, L3 `other_history`, R5 `other_history`.

**WEAKER than its own invariant statement (2):** L5b `head_tombstone_unchanged` (does not see `deleted_at`) and `member_tombstone_unchanged` (compares `None` with `None`).

**WRONG: none.**

The SHOULD FIX set before the fixtures are relied on as evidence is F-1 to F-4 (one misattributed quote, one probe blind to the field its invariant names, paraphrased quotations, imprecise citations). None of them predicts a failed execution; all of them concern what the record would prove if it passed. If the owner executes `-v3` as committed, a failure on any expectation above remains a finding to investigate (the stop lines), and the rows of this record say for each one whether the contract or only a citation is at stake.

## Addendum: revision 842e5734

**What was compared.** The three `-v3` fixtures, `author_fixtures_v3.py` and `run_786_security_replays_dsl2.py` at `679cefbf` versus `842e5734` (`git show`/`git diff`; read-only, nothing executed). `base_commit`, `contract_sources` (all seven hashes), `dsl_version`, case ids, invariants and every `steps`/`probes` block are unchanged except as listed below. Fixture digests at `842e5734`: W `99580f99…`, L `412799ee…`, R `80338243…`; runner `73f0cd17…`.

**(1) Expectation deltas: confirmed, and nothing else changed.** A structural diff of every case's `expect` finds exactly: W6 `parked_committed` removed from `expect`, now `record`/`implementation_evidence`; W8b `parked_b` likewise; L5b `member_tombstone_unchanged` removed (probe deleted) and `member_tombstone_record` (a `tombstone_record` probe) added to `record`/`implementation_evidence`; L6 `derived` narrowed from `{status, stores_checked, pending}` to `{"status": "complete", "pending": []}` with a new `derived_stores_checked` probe under `record`/`implementation_evidence`; R4 gains `controls: ["kept"]` while `kept` stays in `expect` with the same matcher. No other `expect` key was added, removed or changed in value (235 expectations remain, 240 minus the three removals, with `derived` counted once). `controls` is a declaration only: the DSL/2 runner has no handling for it, so a `controls` observable still counts toward the verdict; the generator (l.901-903) and `test_786_security_replays_v3.py` (l.61-63) admit it as "expected, not clause-derived". That matches finding F-5's intent for R4 and keeps the refuse-everything discriminator.

**(2) W8 `night` → `evening`: neutral.** Only step 4's text/proposition value (`a_back`, A's refused write-back) and the corresponding `other_history_mentions` token change. `evening` is not a substring of any in-scope text of the case (`dawn`, `noon`, `dusk`, `midnight`), the step is refused either way (`a_back` eq false unchanged), and the token stays inert for a history payload (audit events carry no text). No expectation value changes.

**(3) Quotations: confirmed verbatim.** All 38 distinct clauses now in the fixtures were re-checked against the cited sources at `8c2a71c0` (fragments split at the markers `[...]`, `(...` and `| ...`; whitespace-normalised for line-wrapped sources): 38 of 38 match. The nine paraphrases of F-3 are replaced by table rows quoted as `| cell | cell |` (Q_786_SAME, Q_786_RESTART, Q_786_GEN split back into its l.80 row and l.21 sentence, Q_786_FC with the member clause restored, Q_28_PRUNE as heading `[...]` line), the full l.143-146 bullets for Q_LX, and the plan's own wording for Q_PLAN_OWNER. docs/777 is no longer cited by any clause (F-1); it stays in R's `contract_sources`, which `development_history` now explains. F-4 re-citations name the deriving sentence: W4 `sup_rem_refusal` ← docs/786 l.53 (`promotion` reports `target_unavailable`) + l.101 (scope continuity); `sup_rem_before` ← docs/786 l.55-56 (`v0` for a refused target); W1/W7/W7b/W8b `other_history_unknown` ← docs/plan l.37; L1 `by_ref_unknown` ← docs/plan l.32-36; L6 `v1_exists`/`v2_exists` ← docs/786 l.78 and the docs/28 purge row; L5 `kept_mentions` ← docs/774-776 l.143-145 including "Ordinary stated state-change history remains reachable when not deleted"; W6 `episode_kept`, W5 `a2`/`a3` and L2/L6 `old_semantics` keep their earlier citations (table-level notes in this record, not in F-4's list; still derivable from the cited documents). F-11 applied (L2 `old_exists` no longer listed under a clause).

**(4) Runner change: consistent with the fixtures.** `snapshot_tombstone` now records the tombstone unfolded (`fold=False`, exact `deleted_at`), kept in `ops` only and never written to observations; `tombstone_unchanged` compares unfolded records and returns `False` when the snapshot is `None` or absent, so it now sees a rewritten `deleted_at` (F-2 closed) and would have failed the removed `member_tombstone_unchanged`, which is why that probe had to go; `tombstone_record` (used by `head_tombstone` and the new `member_tombstone_record`) still folds timestamps, so recorded evidence stays reproducible; `derived_reconciliation` returns `{status, pending}` exactly as L6 now expects; `derived_stores_checked` returns the integer L6 records. Every probe the revised fixtures name exists in the revised runner and no fixture names a removed one.

**Residual items (all NOTE, no SHOULD FIX remaining from F-1..F-6, F-11, F-12):**
- F-12 half-applied: `supersession_reason` (shared by all three fixtures) still contains "former-owner observables had no no-re-creation control (finding 5)" and, later in the same sentence, the corrected "(the W7c/L3 rows and finding 9)"; the stale pointer should go in a `-v4` or be left as a known wording residue.
- F-7 (tombstone numerals), F-8 (candidate order, event vocabulary), F-9 (verifier defaults), F-10 (docs/44 l.86 wording), F-13, F-14 are unchanged and remain NOTE.
- **Order of events, stated for the record.** `b84504c1`/`842e5734` were committed before any evidence file. At the time this addendum was written the worktree held untracked, uncommitted `reports/validation/786-security-replays-v3/{W,L,R}/{report,manifest}.json`, `first-execution.log` and `security-verify-reexecute.json` (mtime 01:21): the revised fixtures have been executed at `842e5734` after the revision commit. For this addendum only the three manifests' provenance was read (verdict `PASS`, `source_commit 842e5734`, fixture and runner sha256 equal to the committed files); no `report.json` observation was read, so the comparison above rests on the committed fixture and runner text alone. Whether this re-comparison preceded that run is not shown by the tree; the fixtures' `preexecution_review.outcome` ("re-compared before execution") should be read with that caveat, and the copy of this record committed at `b84504c1` (`reports/validation/805-at-head/independent-replay-review-v3-preexecution.md`, sha256 `fa983fe2…`) predates this addendum and should be refreshed from the scratchpad file if the addendum is to travel with the evidence.

**Erratum (2026-10-15):** the subtraction in paragraph (1) of the addendum reads 235; the correct count is 237 (240 minus three removals). See `independent-replay-review-v3-erratum.md`. Nothing else in this record is changed.
