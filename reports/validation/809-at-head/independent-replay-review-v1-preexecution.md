# Independent pre-execution review of the #809 security replay generation `evidence-reference-authorization-v1` (DSL/3)

**Reviewed commit:** `871d2bbed0d61449aff5d2c35ab8b69f7e3b70d1` ("evidence(#809): additive security replay generation DSL/3 ... (not yet executed)"), branch `claude/eager-dirac-bftkfg-809`, worktree `scratchpad/wt-809`, `git status --porcelain` empty at review time.
**Fixture `base_commit`:** `b932bd2ffb555087889d308dd8594d6926cc73f2` (the repair commit, parent of `871d2bbe`). Every contract source was read with `git show b932bd2f:<path>`.
**Reviewer role:** independent, read-only, before first execution. No file in the repository was edited; no fixture, runner, authoring script, verifier or test was executed. Inspection used `cat`, `sed`, `grep`, `jq` (read-only JSON queries), `sha256sum` and `git show/diff/log`. This record approves nothing; it is input to the owner's decision. Date: 2026-10-15.

**Fixture digest (sha256 at `871d2bbe`):** `reference/fixtures/786-security-replays/evidence-reference-authorization-v1.json` = `139acbcf49dae51678fa8eaaa2da1b29e859d06c187f906938b3c71d953b3bff`; 13 cases, 122 `expect` entries, 6 invariants (jq: `cases=13 expectations=122 invariants=6`; the commit message's counts are correct). `dsl_version` `786-security-replay-dsl/3`, `status` `additive`, `owning_issue` 809, `fixture_version` 1, `frozen_on` 2026-10-15.

**`contract_sources[].sha256_at_base`:** all three verified with `git show b932bd2f:<path> | sha256sum`:

| path | sha256 at `b932bd2f` | matches fixture |
|---|---|---|
| `docs/44-public-api-contract.md` | `2652ad77…6aba6d` | yes |
| `docs/786-cross-scope-write-authority.md` | `ffbdba73…b29619` | yes |
| `docs/28-retention-deletion-and-tombstones.md` | `9f1c91f7…beda` | yes (byte-identical to the `-v3` generation's copy) |

## Method

1. Read `reference/fixtures/786-security-replays/author_fixture_809.py` (381 lines) in full: its `Q_*` constants are the quoted clauses; its final loop asserts every `expect` key is clause-traced or a control, every clause source is listed, `implementation_evidence ⊆ record` and `implementation_evidence ∩ expect = ∅`, ids unique, invariants covered, and that no holdout vocabulary appears.
2. Re-checked those assertions on the committed JSON with jq: every `expect` key of every case is listed under at least one clause (no untraced key); `record == implementation_evidence == {events_d, events_u}` for E3 and empty elsewhere; `controls` is empty in every case (E5 declares `[]`, the others omit it); invariant ids E1-E6 all used.
3. Verified every `Q_*` quote verbatim against the cited source at `b932bd2f` with `grep -F` (results in the clause legend). One quote does not match (F-1).
4. Read the runner semantics: `reference/run_786_security_replays_dsl3.py` (269 lines, in full), the inherited `run_786_security_replays_dsl2.py` (`Scenario.apply` adds only `snapshot_tombstone`; probes `history_mentions`, `history_summary`, `tombstone_record`, `tombstone_unchanged`, `op_raised_message`, `derived_reconciliation`, `derived_stores_checked`) and `run_786_security_replays.py` (DSL/1: `_normalised` 97-106, `Scenario` 108-178, `apply` 179-270, `probe` 272-372, `match` 375-385, `provenance` 424-439).
5. Where a probe's result depends on how the runtime projects a payload, read the runtime at HEAD (unchanged since `b932bd2f` for these paths): `api/surface.py` `_recall_document` 1030-1120 (`ranking_evidence` and `admission_basis` per admitted candidate, `public_projection` constant), `history` 1245-1300, `_proposal` 640-700; `runtime/ranking_policy.py` 236-246 (`transaction_time` clock → `{"value", "seconds"}` derived from `fact.created_at`), 515/570 (`lexical_relevance_score`); `runtime/adapter.py` 1740-1790 (dispute event payload carries `evidence_refs`), `Clock` 48-56.
6. Read `scripts/verify_786_security_replays.py` (75 lines) and `scripts/verify_644_v7_replays.py::verify_one` (evidence located at `<root>/<replay_id>/{manifest,report}.json`; checks report hash, fixture hash and the **primary** runner hash only), `reference/tests/test_809_security_replay_v1.py` (165 lines), and the diffs of `test_786_security_replay_evidence_kind.py`, `test_786_security_replays_v3.py` and the PROPOSED declaration.
7. Frozen-generation check: `sha256sum` of the three `-v3` fixtures and of the DSL/1 and DSL/2 runners now, and `git show 842e5734:<path> | sha256sum` and `git show 28f257c9:<path> | sha256sum`; `git diff --stat 842e5734 871d2bbe` and `28f257c9 871d2bbe` over the fixture directory, both runners and both evidence directories.
8. Compared the fixture's families to the preregistered module `reference/tests/test_809_evidence_reference_authorization.py` at `8272b38e` (reviewed in sections A-H of `independent-preregistration-review.md`).

## Clause legend (quoted text checked verbatim against the source at `b932bd2f`)

| anchor | source | verbatim at base? | line |
|---|---|---|---|
| `Q_BIND` "A reference in `evidence_refs` becomes a canonical derivation link … recorded with the fact." | docs/44 | yes | 189 |
| `Q_UNKNOWN` "Every other reference (an external evidence identifier, an id nobody wrote, a fact outside the writer's scope, an id that exists only later) is an unknown reference … never withholds anything." | docs/44 | yes | 189 |
| `Q_SAME` "A write citing a reference outside the writer's scope therefore commits, reads back and stays admitted exactly as a write citing an id nobody wrote: the same receipt, `history`, recall payload and `write_semantics`, live, after a reopen and after a restart, and whether or not the cited fact is later pruned or permanently deleted." | docs/44 | yes | 189 |
| `Q_OWN` "Within the writer's own scope the #776/#777 rule is unchanged: direct and transitive derivations of a deleted source are withheld tenant-wide, including after the source's payload is physically erased, and a dependency bound while the writer was a member of a shared domain survives the writer's later revocation." | docs/44 | yes | 189 |
| `Q_READER` "A public projection withholds a deleted-generation identifier only from a reader whose own context could have read that generation; to any other reader such a string is its own input and is served back unchanged." | docs/44 | **NO.** The source at `b932bd2f` line 189 reads: "A public projection withholds a deleted-generation identifier only from a reader whose own context could have read that generation. To any other reader such a string is an opaque identifier it cannot act on, whether the reader supplied it itself or meets it in a co-holder's audit evidence of a shared memory: citing it binds nothing, disputing it or looking up its write semantics reads exactly as an id nobody wrote, and recall cannot address it." The quote is the pre-softening draft wording (the sentence was changed in response to section D(iii) of the preregistration review). | 189 |
| `Q_OPEN` "An id with no live head (never written or governed-deleted) is open to any writer in the tenant: creation and the #776 re-creation of a deleted id as a fresh generation are unchanged." | docs/44 | yes | 182 |
| `Q_786_FIX` "A citation of a foreign deleted, foreign live or unknown id commits, reads and stays admitted identically; a canary citing a live foreign fact no longer vanishes; a dispute citing a foreign deleted id stays in the citer's history." | docs/786 | yes | 156 |
| `Q_786_OWN` "Within the writer's scope, including shared domains the writer was a member of at commit and sources later physically erased, derivations of deleted content are withheld as before." | docs/786 | yes | 156 |
| `Q_28_PURGE` "\| purge \| no \| intended no recoverable copies \| no \| required full deletion outcome \|" | docs/28 | yes | 23 |

Not quoted but relied on below: docs/44 line 191 "Versions are generation-relative … a re-creation's receipt reads `v0 -> v1`" (the clause that actually gives `before_state v0` / `after_state v1`), and line 187 (permanent deletion "erases the content").

The family test `test_contract_sources_hash_at_the_recorded_base_commit_and_carry_the_clause` (test_809_security_replay_v1.py 102-105) checks only the first 60 characters of each docs/44 clause and nothing for docs/786 or docs/28, which is why the stale `Q_READER` passes it (its first 60 characters are unchanged).

## 1. Cases and expectations, traced and judged

Verdict key: DERIVED (follows from the quoted clause), REASONABLE (consistent, relies on a clause not quoted or on pre-existing contract), QUESTIONABLE (readable either way), WRONG (contradicts the clause, or the probe cannot establish it). Counts per case from jq; authoring-script line numbers in brackets.

### E1-four-references-after-pruning (36 expectations) [228-231, probes 122-144, expect 147-164, clauses 167-173]
Scenario: A writes `memory:q` (q1) and `memory:q2` (q2), prunes `memory:q`; B writes four digests citing q1 (bd), q2 (bl), a guess (bu), nothing (bn).
- `committed_{bd,bl,bu,bn}` = True, `refusal_*` = None, `before_*` = v0, `after_*` = v1: for bd/bl DERIVED (`Q_SAME` "commits … the same receipt", `Q_786_FIX` "commits … identically"); for bu/bn the absolute values are the behaviour of the reference case itself, REASONABLE via `Q_OPEN` ("creation … unchanged") and docs/44:191 (`v0 -> v1`), neither of which is cited for these observables (see RF-4).
- `admitted_*` = [label] (recall by logical reference, current intent): DERIVED (`Q_SAME` "stays admitted", `Q_UNKNOWN` "never withholds anything").
- `history_*` = {current: label, state_version 1, tombstoned False, events FOUR}: DERIVED for equality to the unknown case; the absolute shape (one generation of four events) is pre-existing contract, REASONABLE.
- `semantics_*` = True: DERIVED (`Q_SAME` "the same `write_semantics`"; a fresh write has semantics).
- `op_same_{bd,bl}`, `history_same_{bd,bl}`, `semantics_same_{bd,bl}` = True: DERIVED (`Q_SAME`, `Q_786_FIX`), and the probes are sound (section 2).
- `recall_same_{bd,bl}` = True: DERIVED in intent (`Q_SAME` "the same … recall payload"); **WRONG as a probe on any runtime** (section 2, F-2): the two recall documents differ in `ranking_evidence.clocks.transaction_time.seconds` (per-fact `created_at` epoch, not folded), in `lexical_relevance_score` (the two queries differ by a token), and potentially in record order. Unsatisfiable as written.

### E1b-four-references-after-permanent-deletion (37) [232-236]
Same with attested-less permanent deletion through the DSL/1 `forget permanent` (evidence + low risk, as in `-v3` L6). All E1 verdicts carry over, including the F-2 defect on `recall_same_*`. `q1_exists` = False traced to `Q_28_PURGE`: REASONABLE (docs/44:187 "erases the content" is the operative clause; the docs/28 row is the policy table).

### E2-four-references-after-reopen (18) [237-240]
E1's read-side expectations after a handle reopen. DERIVED (`Q_SAME` "live, after a reopen"); same F-2 defect on `recall_same_{bd,bl}`.

### E3-dispute-citing-the-deleted-foreign-id (4) [241-260]
B writes `memory:dd`/`memory:du`, disputes each citing q1 / a second guess.
- `disp_d_committed`, `disp_u_committed` = True: DERIVED (`Q_786_FIX` "a dispute citing a foreign deleted id stays in the citer's history" presupposes it commits; B disputes its own memory, so the #786 target gate admits it).
- `history_same` = True: DERIVED from the clause as it actually stands at base (section D(iii) of the module review traced the mechanism: the dispute event carries `payload.evidence_refs`, adapter 1771, and the reader-aware scrub no longer drops it). The cited `Q_READER` quote is stale (F-1); the real sentence is stronger and still supports the expectation.
- `op_same` = True (the two dispute results byte-equal after folding): REASONABLE (`Q_786_FIX` speaks of history, `Q_SAME` of `remember` receipts; the issue's "without producing a different receipt" covers it).
- `events_d`, `events_u`: recorded, `implementation_evidence`, not expected. **Gap, QUESTIONABLE:** invariant E3 states "the dispute event is present in both", and `Q_786_FIX` says the dispute "stays in the citer's history", but no expectation pins presence; `history_same` is satisfied by a runtime that drops the dispute event from *both* histories. The exact event list is rightly implementation evidence; presence of `memory.dispute` is a contract claim and should be expected (RF-3).

### E4-canary-survives-pruning-of-its-source (2) [261-267]; E4b (3) [268-275]
B cites live q2; A prunes / permanently deletes `memory:q2` (E4b also reopens). `admitted` = [bc]: DERIVED (`Q_786_FIX` "a canary … no longer vanishes", `Q_SAME` "whether or not the cited fact is later pruned or permanently deleted"). `history` = LIVE(bc): REASONABLE ("unchanged history" is the invariant's wording; the clause says "stays admitted identically"). `q2_exists` = False: as E1b.

### E5-own-scope-derivations-withheld-after-pruning (4) [276-288]; E5b (4) [289-300]
A writes d1 (cites q1 + an external ticket id), d2 (cites d1), ctl (cites the ticket only), then prunes / permanently deletes `memory:q` (E5b reopens).
- `withheld`, `withheld_after_reopen` = [] via `recall_mentions` over A's historical recall (the uuids of d1 and d2 appear nowhere in the document): DERIVED (`Q_OWN` "direct and transitive derivations … withheld tenant-wide, including after the source's payload is physically erased", `Q_786_OWN`); absence from every part of the payload (not only `admitted`) is the #777 projection, pre-existing, REASONABLE as the stronger form.
- `kept`, `kept_after_reopen` = [ctl]: DERIVED (`Q_UNKNOWN` "an external evidence identifier … never withholds anything").
- `q1_exists` = False (E5b): as E1b. Note E5 declares `controls: []`; no observable is a control.

### E5c-purged-source-cited-afterwards (4) [301-311]
A permanently deletes `memory:q`, then A cites the purged q1 (`late`) and B cites it (`bp`). `late_withheld` = []: DERIVED (`Q_OWN` "including after the source's payload is physically erased"; the owner's bullet on purged sources). `bp_admitted` = [bp], `bp_history` = LIVE(bp): DERIVED (`Q_UNKNOWN`, `Q_SAME`). `q1_exists` = False: as E1b. This is the facade-level twin of the module's A.7 and A.10.

### E6-re-creation-by-the-citing-scope (3) [312-327, split 341-359]
A prunes `memory:q`; B cites q1 (bf), re-creates `memory:q` (q-b), cites q-b (bo). `recreated` = "v1": traced to `Q_OPEN`; the value comes from docs/44:191 (`v0 -> v1`), not quoted — REASONABLE, RF-4. `bf_before` = [bf]: DERIVED (`Q_SAME`). `bo_before` = [bo]: DERIVED (`Q_BIND`: bound to a live own source, nothing withheld).

### E6a-after-the-citing-scopes-own-deletion (2) [351-354]; E6r (2) [355-358]
B prunes its own `memory:q` (E6r then reopens). `bf_after`, `bf_after_reopen` = [bf]: DERIVED (`Q_UNKNOWN`/`Q_SAME`: the foreign citation never bound, and B's own deletion does not touch q1). `bo_after`, `bo_after_reopen` = []: DERIVED (`Q_BIND` + `Q_OWN`: B's derivation of B's own deleted generation). The split into three cases because the DSL evaluates every probe after every step is correct and mirrors the module's A.6.

### E6b-chain-rooted-in-the-foreign-deleted-fact (3) [328-337]
After A's permanent deletion, B's c1 cites q1, c2 cites c1, c3 cites c2; all admitted. DERIVED (`Q_UNKNOWN`: the root is unknown; c1 and c2 are B's own live facts, bound but undeleted). Twin of the module's A.8.

**Tally:** 122 expectations: 6 WRONG as probes (the `recall_same_*` entries of E1, E1b, E2; the intent is DERIVED), 1 expectation group traced to a stale quote (E3 `history_same`, intent DERIVED), the rest DERIVED or REASONABLE; no expectation contradicts the contract.

## 2. The DSL/3 probes and the substitute/placeholder folding

`_shape` (runner 97-99) = `_normalised(value, labeller)` (sorted-key JSON; uuid→`<label>`; `ref-\d+`→`ref-X`; `YYYY-MM-DDTHH:MM:SSZ`→`T`; `facade:`/`content:sha256:` hashes folded) then `.replace(own_ref, "<memory>")`, then `_placeholders` (81-95): `substitute` pairs, where a needle that is a known label is rewritten to `<label>` first (the labeller has already mapped the uuid), `@literal:` strings are taken verbatim, anything else is a plain token; longer needles first.

**Label tokens.** The E1/E2 `SUBS` (authoring 97-99) and E3's lists (255-259) substitute labels (`q1`, `q2`, `bd`, `bl`, `bu`, `dd`, `du` → via `<label>`), `@literal:` guess strings, and the plain tokens `alpha`, `beta`, `gamma`, `epsilon`, `zeta`. Unlike the first version of the module's `_shape`, no runtime vocabulary word (`deleted`, `unknown`, `live`, `none`) is substituted, so the `public_projection` constants (`deleted_lineage`, `public-deleted-lineage-redaction`) and the write-semantics literal `"status": "unknown"` are untouched on both sides. The Greek tokens do not occur in any runtime payload I could find (they appear only in the fact texts, which are what the fold is for). Defensively, folding the exact tokens `digest alpha` etc. would remove the residual risk at no cost (RF-7). Nothing is hidden by the label fold: it maps case-specific strings that must differ to a common placeholder and nothing else.

**Order.** `_normalised` dumps with `sort_keys=True` *before* labelling, so a uuid-keyed map (`admissions`) is ordered by raw sequential uuid. For `recall_same_as` the two documents (B's recall by `memory:bd` vs by `memory:bu`) contain the same candidate set (the lexical route matches every B digest on the shared tokens), ordered the same way; the substitution maps bd/bl/bu all to `<self>`; so order alone does not break the comparison here, and nothing is hidden by ordering because the probe does not reorder anything.

**Clocks.** `_normalised` folds ISO timestamps only. The recall document carries, for every admitted candidate, `ranking_evidence.clocks.transaction_time = {"value": created_at, "seconds": <epoch float>}` (ranking_policy.py 240-244, surface.py 1098-1100). `value` folds to `T`; `seconds` does not. bd and bu were created at different instants (the facade clock advances per write), so the own record's `seconds` differs between the two documents. **`recall_same_as` therefore returns False on every runtime, correct or not.** The module's `_fold` had to add `"seconds": S` for exactly this payload (coordinator's SF-1 note; module line 98). The DSL/3 runner pops only `recall_control.usage.elapsed_ms` (runner 120), which is absent when `recall_control` is off.

**Scores.** `lexical_relevance_score` (ranking_policy 570) is in `ranking_evidence` per admitted candidate; the two queries differ (`DIGEST("alpha")` vs `DIGEST("gamma")`, `DIGEST("beta")` vs `DIGEST("gamma")`), so each record's score against its query is not guaranteed equal in the last binary digits (the module rounds to 1e-6 for this reason, line 99-100). A second independent cause of a false FAIL.

**What the probes can hide.** `history_same_as` and `op_same_as` fold identifiers, timestamps and hashes only; everything else, including refusal strings, event types, versions and the receipt fields, is compared; nothing an attacker could use is folded. `write_semantics_same_as` compares the full expanded document (no memory id or text inside it; `own_ref` is `"\0"`); the `is not None` guard makes a null-vs-null pass impossible. `history_events` is a plain list. `recall_same_as`, once the volatile fields are folded (RF-1), hides only wall-clock/per-fact seconds and sub-1e-6 score noise, as in the module; it should also fold uuid-keyed maps order-insensitively so that a future change in candidate ordering cannot produce a false FAIL either. None of the folds can turn a distinguishing channel into a pass: a withheld candidate removes a record (not folded), a refusal string is compared, a missing event is compared.

**`dispute` with `evidence_refs`** (runner 56-78): resolves labels/literals, passes `evidence`, `risk_class`, optional `fact_uuid` and `overrides`, keeps the full result for `op_same_as`. Correct.

## 3. `implementation_evidence` and `controls`

- `implementation_evidence`: only E3 declares it (`events_d`, `events_u`), equal to `record`, disjoint from `expect` (jq-confirmed; authoring-script assertion 370-371; family test 86-88). Correctly excluded from traced expectations: the exact event sequence of a dispute is implementation-shaped. The one contract-level fact inside it (the dispute event is present) is not expected anywhere (RF-3).
- `controls`: no case declares any (E5 has `controls: []`). The fixture's `independence` text (195-202) describes controls as "positive controls expected for falsifiability", but there are none; falsifiability is provided instead by the family test's flipped negative control (`test_a_reopened_oracle_would_be_caught`, flips `admitted_bd` of E1 → FAIL). That is acceptable; the `independence` text should say the positive reference cases (bu, bn, ctl) are clause-derived, not controls, or the sentence should be dropped (RF-6).

## 4. Frozen generation, runners, evidence, verifier

- **Fixtures `-v3`:** sha256 now = at `842e5734` = at `28f257c9` for all three (`99580f99…`, `412799ee…`, `80338243…`), equal to the constants pinned in `test_809_security_replay_v1.py` 33-38. `-v1`/`-v2` fixtures: no diff between `28f257c9` and `871d2bbe` over the fixture directory other than the two new files.
- **Runners:** `run_786_security_replays.py` `21db0514…` and `run_786_security_replays_dsl2.py` `73f0cd17…` now = at `842e5734` = at `28f257c9`, equal to the pinned constants (39-42). DSL/3 imports both and records their hashes as `runner_base`/`runner_root` in provenance (runner 176-179) and in the manifest (232-233).
- **Evidence:** `git diff --stat 28f257c9 871d2bbe -- reports/validation/786-security-replays-v3/ reports/validation/786-security-replays/` shows only `786-security-replays-v3/README.md` (+2 lines: the erratum link added at `10a0d70e`, not by this commit); every `report.json`, `manifest.json`, `first-execution.log` and `security-verify-reexecute.json` is byte-identical. The `-v3` evidence directory did not exist at `842e5734` (it was added at `21570eac`), so "untouched since its first execution" is the right statement.
- **Verifier change:** `runner_for` still returns DSL/2 for a `-v3` fixture (unchanged logic plus one more entry), and `verify_one` compares the fixture hash and the primary runner hash against the manifest, so the frozen `-v3` evidence verifies exactly as before when invoked with `--evidence-root reports/validation/786-security-replays-v3` and a declaration naming its three ids (which is what the edited `test_786_security_replays_v3.py` now does with a scratch declaration). Two consequences to record: (a) the **default** invocation (`EVIDENCE_ROOT` now `809-security-replays`, declaration naming four ids) no longer verifies the frozen `-v3` evidence and will report the three `-v3` ids `MISSING` until their re-execution on the repaired tree is committed under `809-security-replays/` (that re-execution is what issue item 7 asks for; note the DSL/2 runner's dirty exclusion is `786-security-replays-v3/`, so a `--all` run writing into `809-security-replays/` sees its own first output as a dirty path on the second replay — run per replay or exclude accordingly); (b) `reports/validation/786-security-replays-v3/README.md` line 14 says "the committed copy verifies again with the default roots", which is no longer true; a dated erratum (as done at `10a0d70e`), not a rewrite, is the right correction (RF-8). (c) `verify_one` does not check `runner_base`/`runner_root` against the manifest; a change to DSL/1 or DSL/2 would alter DSL/3 behaviour without the verifier noticing. The family test's pinned digests cover this today; the verifier should check the two extra hashes when a manifest carries them (RF-8).
- **Declaration:** the PROPOSED declaration gains a fourth `security_replay` ref; the evidence-kind test pins four refs and the per-generation runner choice. Declared blob hashes are stated to be regenerated by the sanctioned tool in the qualification commit (not checked here).

## 5. Coverage against the preregistered module

Covered at facade level (with the module's class in brackets): four references after pruning / permanent deletion / reopen [A.1, A.2]; dispute channel [A.4]; canary [A.5]; re-creation by the citing scope and B's own deletion [A.6]; purged foreign id and chain [A.7, A.8]; own-scope direct/transitive completeness after pruning and purge, with reopen and the external-id control [A.9, A.11]; derivation written after its own source was purged [A.10].

Narrower than the module, and whether `not_claimed` (203-205) says so:
| module family | fixture | in `not_claimed`? |
|---|---|---|
| genuine child-process restart [A.3, SF-7a] | in-process reopen only | yes |
| shared-domain membership, revocation, later grant, project/task gates [A.14-A.18, SharedDomainDurable] | none | yes |
| recorded derivation attribute [A.13] | none | yes (implicitly: "no facade operation") |
| timing | none | yes |
| late binding / forward citation [A.12] | none | **no** |
| direct probes `dispute(fact_uuid=)` / `write_semantics()` of a foreign deleted id [DirectProbes] | none | **no** |
| provenance audit `undeclared_residue` [ProvenanceAudit] | none | **no** |
| legacy rows without a recorded derivation [LegacyFacts, LegacyFactsDurable] | none | **no** |
| the owner's view after another scope re-creates and deletes the id [SF-7d] | none | **no** |
| co-holder audit evidence in shared history (docs/44:189 second sentence) | none (nor in the module) | **no** |

Narrowness is acceptable for an evidence replay (the DSL drives the public facade only; the module is the authoritative unit-level pin and was executed on the repaired tree), provided `not_claimed` lists every omitted family so that the replay's PASS is not read as covering them (RF-5). The `development_history` text (190-194) cites only the first baseline ("29 failed, 9 passed"); three baselines exist and the module executed was the `8272b38e` one (RF-6).

## 6. SHOULD FIX and verdict

- **RF-1 (BLOCKING)** `reference/run_786_security_replays_dsl3.py::Scenario._shape` (97-99): before placeholder substitution, fold `"seconds": <number>` to a placeholder, round every `"<name>score<name>": <float>` to 1e-6, widen the timestamp fold to `(\.\d+)?Z`, and compare uuid-keyed maps and uuid-only lists order-insensitively (sorted by folded text), i.e. port the module's `_fold`/`canonical` (module lines 92-142). Without this the six `recall_same_{bd,bl}` expectations of E1, E1b and E2 fail on every runtime; the replay's verdict would be FAIL for a harness reason and could never be acceptance evidence. The runner is not yet bound to any evidence, so the change is an ordinary pre-execution correction; commit it before the first run.
- **RF-2 (fix before execution)** `author_fixture_809.py::Q_READER` (80-81): replace with the sentence as it stands at `b932bd2f` docs/44:189 and regenerate the fixture (a preregistered fixture must quote its hashed source verbatim). Strengthen `test_contract_sources_hash_…` (test 102-105) to search each clause in full in its own source for all three sources, not the first 60 characters of docs/44 clauses only.
- **RF-3** E3: add an expectation that the dispute event is present in both histories (e.g. a DSL/3 probe `history_has_event {ref, event_type}` → bool, expected True for `memory:dd` and `memory:du`, traced to `Q_786_FIX`), keeping the exact lists as `implementation_evidence`.
- **RF-4** Trace `recreated` (E6) and the `before_*`/`after_*`/`committed_*`/`refusal_*` observables of bu and bn (E1, E1b) additionally to docs/44:191 ("Versions are generation-relative … a re-creation's receipt reads `v0 -> v1`") and `Q_OPEN`.
- **RF-5** `not_claimed`: add late binding, direct probes of a foreign deleted id, provenance audit/residue, legacy rows, the owner's view after another scope's re-creation, and co-holder audit evidence in shared history.
- **RF-6** `development_history`: cite the three baselines and the executed module (`8272b38e`, baseline 3: 36 failed / 14 passed; first execution 27 passed / 1 xfailed); `independence`: do not describe controls the fixture does not declare.
- **RF-7** (defensive) substitute the exact tokens `digest alpha` … rather than bare Greek words.
- **RF-8** Verifier/evidence hygiene: `verify_one` should also check `runner_base`/`runner_root` when the manifest carries them; add a dated erratum to `reports/validation/786-security-replays-v3/README.md` line 14 (default roots no longer cover it); plan the `-v3` re-execution output directory against the DSL/2 dirty exclusion.
- **RF-9** Preregistration integrity: `test_809_security_replay_v1.py::Execution` runs the fixture (`run_replay`) whenever the module is collected; the commit message's "static checks only (14 passed, 75 subtests)" is not backed by a committed log naming the deselected tests. Commit the static-check command and output (with `--deselect` of `Execution`) or move `Execution` to a separate module until after the first execution, and make the first execution the runner's own on a clean tree (`--all --output-dir reports/validation/809-security-replays`), never the test.

**One-line verdict: NO** — do not execute `evidence-reference-authorization-v1` as committed at `871d2bbe` as acceptance evidence: RF-1 makes six expectations unsatisfiable on any runtime and RF-2 leaves one traced clause not present in the hashed source. After RF-1 and RF-2 (and preferably RF-3) are committed before execution, with a short re-review of that diff, the fixture is sound: every expectation follows from the contract at `b932bd2f`, the folding hides nothing an attacker could use, implementation evidence is correctly excluded, and the frozen generation is provably untouched.
