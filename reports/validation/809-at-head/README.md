# #809 (F-R3-2) security remediation: evidence at the repaired head

Evidence for the owner's option (b) decision on PR #805 review 5527079673 / issue #809, **not**
security acceptance, not a baseline publication and not a register mutation. Produced locally (no
GitHub Actions, no hosted CI, no paid inference). Branch `claude/eager-dirac-bftkfg-809`, based on
the PR #805 head `28f257c9` and not touching it.

## Identities

| what | value |
|---|---|
| starting revision (unmodified integration candidate) | `28f257c9cba5b1e1b683e5a6246f12bf075a5162`; protected blobs `59e8f97c…` `pyproject.toml`, tree `17b1ba10…` `reference/agentmem_ref` (`adapter.py` `66a216fd…`, `surface.py` `34e92bcb…`) |
| repair commit (protected tree changes) | `b932bd2ffb555087889d308dd8594d6926cc73f2` |
| repaired protected tree | `pyproject.toml` `59e8f97cb9de3dfc92f583616b79b2ee54c6fa4d` (unchanged); `reference/agentmem_ref` tree `6f4205e029d3a42a36b709991efe6ead898a687c`; `runtime/adapter.py` `4a44aa69246114fea5b8cbe46d9cdb9603a94cc0`; `api/surface.py` `565a999f311cba6ca0da357c5836aadc15467a29`. Identical at every later commit of this branch |
| replay execution head | `c70fe31572e624d0e4f031ab8334b589257cf529` (clean tree) |
| preregistration commits | `10a0d70e` (round 1, baseline 1), `53268532` (round 2 after review SF-1..SF-7, baseline 2), `8272b38e` (round 3 after review G-1/G-2, baseline 3; executed as committed) |
| replay generation commits | `871d2bbe` (round 1, reviewer NO: RF-1/RF-2), `ee427d80` (RF-1..RF-9, reviewer YES, superseded), `c70fe315` (probe replacement and corrected disclosure, reviewer YES; executed as committed) |
| declaration | `reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json`: regenerated with `scripts/declare_runtime_baseline_changes.py --declaration … --register reports/runtime/proposals/786-scratch-register-v8.DEMO.json`; exactly two declared blobs changed (`runtime/adapter.py` `66a216fd → 4a44aa69`, `api/surface.py` `34e92bcb → 565a999f`); fourth `security_replay` ref `evidence-reference-authorization-v1`; `scripts/check_runtime_baseline_equivalence.py --register …DEMO.json --candidate HEAD` → `TRANSITION … 14 declared blobs; deltas=identity.public_contract_version 1.6.0->1.8.0` (exit 0); real register exit 1 by design, untouched |

## What was repaired (docs/44 "Canonical derivation is bound under the writer's own authority"; docs/786 F-R3-2 row; docs/15 §18b)

A cited reference becomes a canonical derivation link, and so carries deletion taint, only when it
names a fact of the tenant the writer is eligible to read under the #786 scope gates, decided once at
commit and recorded with the fact (`attributes["canonical_derivation"] = {policy:
writer-eligible-at-commit/1, bound: [...]}`); `episode_uuids` keep the caller's references verbatim.
Every taint consumer, the revocation residue audit and the public withholding predicates follow the
bound set; the public predicates take the reader's context. A fact persisted without the record keeps
`episode_uuids` as its dependency set. No envelope or refusal token changed; contract `1.8.0` stays
**provisional** pending the owner's version decision. No UUID randomization; host-supplied scope
stays privileged.

## Corrected oracle observations (citer B, project A's deleted fact `a1`; unmodified runtime vs repaired)

| channel | before (`28f257c9`, baseline 3) | after (`b932bd2f`, first execution) |
|---|---|---|
| `remember` receipt citing `a1` | identical to citing a guess | identical (unchanged) |
| `recall` by B's logical reference | B's digest withheld (admitted 0; absent from `admissions`) | admitted; payload byte-identical (folded) to the guess case, after pruning, after attested permanent deletion, after reopen, after a genuine process restart |
| `history` of B's memory | events scrubbed (0 of 4, `current_fact_uuid` null) | four events, byte-identical to the guess case |
| `write_semantics` of B's fact | `null` | document, byte-identical to the guess case |
| B's dispute citing `a1` | `memory.dispute` absent from B's history | present; dispute result and history byte-identical to the guess case |
| canary citing A's live fact, then A deletes it | vanishes (1 → 0) | unchanged before/after (admitted, events, all four shapes) |
| chain rooted in `a1` (purged) | all three withheld | all admitted; a purged foreign id binds nothing |
| A's `undeclared_residue(a1)` | lists B's citing uuid (A learns a foreign fact id) | B's uuid absent; A's own undeclared derivation present or declared |
| shared domain: stranger, later-granted member, other task, other project | refused `derived_from_tombstoned_source` | admitted (never bound) |
| shared domain: member at commit, membership revoked later | refused (deletion family) | refused (unchanged; durable through reopen, facade over SQLite) |
| live-foreign vs unknown citation | identical on every channel | identical (never a channel) |
| own-scope derivations of a deleted source (direct, transitive; pruning and purge; reopen; genuine restart; written after the purge) | withheld | withheld (unchanged); external-only control admitted |
| legacy row without the record (in memory and on the durable substrate across reopens) | follows its source's deletion | follows it (unchanged) |

## Side channels examined

- **Timing** (`timing/`, 300 rounds per case, `remember` through `AgentMemory.open` on a fresh store, cases rotated): medians deleted 13031 µs, live 13041 µs, unknown 12999 µs, none 13011 µs; ratios to unknown 1.003 / 1.003 / 1.000 / 1.001; p90 17.9–19.9 ms in no case-consistent order. The write is dominated by the SQLite commit; the binding adds a dictionary probe and the scope gates. Reported as a measurement, not a guarantee.
- **Ordering and scores**: the citer's other memories are candidates of every recall and rank by the query text (which carries the case token); the comparisons fold candidate order, transaction-clock seconds and score differences below 1e-6 (an accepted tolerance). Multiplicity, every record's content, `rank_position` of the citer's own record, refusals and withheld-candidate removal are compared.
- **Co-holder audit evidence**: a co-holder of a shared memory can meet a deleted private identifier in another holder's dispute evidence; after the repair the string is inert to that reader (citing it binds nothing, disputing it or looking up its write semantics reads as `fact_not_found` / `None`). Pinned by `DirectProbes`; docs/44 states it in those terms.

## Ladder at the repaired protected tree

| evidence | command (repository root, clean tree) | outcome |
|---|---|---|
| preregistered expectations, fail-first | `python3 -m pytest tests/test_809_evidence_reference_authorization.py 'tests/test_786_cross_scope_write_authority.py::EvidenceReferenceOracle' 'tests/test_776_transitive_traversal_review.py::TransitiveTraversal::test_decision_does_not_depend_on_query_order' tests/test_776_deletion_decision_properties.py -q -p no:cacheprovider --tb=line` (cwd `reference/`) on the unmodified runtime | baseline 3 (`preregistration-baseline-3.log`): 36 failed, 14 passed, 82 subtests; RED/GREEN sets match the module docstring; baselines 1 and 2 kept |
| first execution on the repaired runtime | same command, `--tb=short -rxX` | `first-execution.log`: 27 passed, 1 xfailed (the pre-repair proof `EvidenceReferenceOracle`, kept with its body unchanged), 106 subtests; no expectation edited |
| neighbouring families (786, 776, 777, 644, unknown scope, governed paths, procedural, materialization, metabolism) | `python3 -m pytest …` (11 modules) | 158 passed, 1 xfailed, 123 subtests |
| four security replay contracts (three frozen `-v3` through DSL/2, `evidence-reference-authorization-v1` through DSL/3) | `python3 reference/run_786_security_replays_dsl3.py --all --output-dir reports/validation/809-security-replays` (runner's own first execution, clean tree at `c70fe315`); `python3 reference/run_786_security_replays_dsl2.py --all --output-dir <scratch>` (clean tree at `c70fe315`, copied in); `python3 scripts/verify_786_security_replays.py --evidence-root reports/validation/809-security-replays --reexecute` (clean tree) | PASS 13/13 (124 expectations) and 13/13, 10/10, 8/8 (237); verifier `evidence_verified: true`, VERIFIED / PASS / re-executed ×4 (`809-security-replays/security-verify-reexecute.json`); the frozen `786-security-replays-v3` evidence is untouched |
| five #644 v7 replay contracts | `python3 reference/run_644_v7_replays.py --all --output-dir <scratch>`, `python3 scripts/verify_644_v7_replays.py --reexecute --evidence-root <scratch>` (exit 0), `python3 scripts/check_644_v7_replay_inventory.py --evidence-root <scratch>` (exit 2, BLOCKED by design) | VERIFIED / PASS / re-executed ×5, 104/104 cases (`replays/`) |
| public Gauntlet probe through the public facade | scratch contestant (v7 stdio adapter, `FROZEN_RUNTIME_REVISION=c70fe315…`, `PUBLIC_CONTRACT_VERSION=1.8.0`; deleted afterwards), `… gauntlet run --profile gauntlet-orchestration-retrieval-probe-v1 --allow-external-process --allow-destructive-reset --json` | `status: complete`, `exact_top1 1.0`, `correct_top1 3/3`, `authority_effect none` (`gauntlet/`) |
| blind theatre and vineyard holdouts (served-memory quality evaluator v3 @ `9961067`) | scratch harness identical to the PR #805 run; `28f257c9` (label `805-ef8b6cb2`) vs the repaired tree (label `809-6f4205e0`, measured at `ee427d80`, protected tree identical to `c70fe315`); `composed` and `strict-target` | rate-identical on both heads (theatre top1_critical 0.4286 / 0.7619, vineyard 0.45 / 0.90); P0 prohibited and stale exposures 0 on every run; both runtimes clean (`blind-holdouts/summary.json`) |
| write-latency by citation case | `python3 timing/measure_809_timing.py reference 300` | `timing/write-latency-by-citation-case.json`, see above |
| reference conformance report | `python3 reference/run_conformance.py` | `derived_state_hard_gate_passed: true`; known failures = the four freeze guards (`conformance-summary.json`) |
| full reference suite | `python3 -m pytest reference/tests -q` from the repository root at `631e9b71` (protected tree `6f4205e0`) | 4 failed, 2966 passed, 35 skipped, 1 xfailed, 2053 subtests (4m52s); the four are the by-design freeze guards (`test_644_v7_gauntlet_identity…`, two `test_770…ReplayEvidenceFreshness`, `test_benchmark_integration_contract…equivalence`), identical to every head of the stack; the gated `test_809_security_replay_v1::Execution` ran against the committed first execution and passed (`full-suite-summary.log`) |

## Independent review (same reviewer, read-only, nothing executed by them)

- `independent-preregistration-review.md`: sections A–F on `10a0d70e` (NO: SF-1 blocking, SF-2..SF-8), G on `53268532` (NO: G-1, G-2), H on `8272b38e` (**YES**).
- `independent-replay-review-v1-preexecution.md`: sections 1–6 on `871d2bbe` (NO: RF-1, RF-2; RF-3..RF-9), 7 on `ee427d80` (YES), 8 on `c70fe315` (**YES**; `recall_admits` judged the right probe; no other probe vocabulary-dependent).
- `pre-review-execution-871d2bbe.md`: the one execution that happened before a review (by the family test inside a full-suite run, not the runner), its failures (RF-1 and the `recall_admitted` probe semantics, the latter not found by the review and first misdescribed by the coordinator), and why it is not evidence.

## Limitations and open items

1. **Legacy rows**: facts persisted before #809 keep `episode_uuids` as their dependency set, so for them the channel persists until rewritten by a governed act (deliberate; documented in docs/786). A migration or audit tool that *reports* such rows is out of scope.
2. **Late binding withdrawn**: a reference that names no fact at commit never binds (fail closed). This withdraws the #776 guarantee pinned by `test_776_transitive_traversal_review::test_decision_does_not_depend_on_query_order`, a declared behavioural change that needs the owner's explicit acceptance; it is not part of the approved disposition.
3. **Sequential identifiers** still disclose write activity (not deletion membership, scope or content); opaque identifiers remain a separate decision.
4. **Timing** is measured, not bounded; score comparisons carry a 1e-6 tolerance.
5. **Contract version**: `1.8.0` provisional; the owner decides whether the narrowed taint rule warrants a bump.
6. **Replay coverage**: the DSL/3 fixture is facade-level and narrower than the unit module (its `not_claimed` lists the unit-only families).
7. **Runtime sharp edge found on the way (pre-existing, not changed)**: an adapter-level call that is a governed act (`governed_recall`) on a facade-owned SQLite handle, followed by `close()` without a facade operation, makes the next `open` fail the substrate digest check; direct adapter calls on facade handles are an unsupported pattern (documented in the test).
8. **Frozen `-v3` README**: dated erratum appended (the verifier's default evidence root moved); contents unchanged. The `-v3` addendum arithmetic erratum (235 → 237) is recorded in `805-at-head/independent-replay-review-v3-erratum.md`.
9. The v7 replay inventory stays BLOCKED by design; the four freeze guards stay red by design until the register points at this declaration.
10. **Blind holdouts** were measured at `ee427d80`, not `c70fe315`; the protected tree is identical (`6f4205e0`) and the evaluator records both commits as clean.

## Final head after the owner's checkpoint (`03ddaef9`, protected tree `2a00f31f`)

The owner's checkpoint on PR #815 (review 5527842455) required four items before a new acceptance review. All four are on this branch; the protected tree changed again (code-review fixes `6bdff75b`; legacy upgrade `bd8a67e3`), so the ladder was re-run at the final head.

| item | where | state |
|---|---|---|
| independent adversarial code review of the altered production paths | `independent-code-review-0808cb61.md` (verbatim) | sound for new writes as ruled; SF-1 (checkpoint-migration guard), SF-2, SF-3 fixed at `6bdff75b`; L2/L3 residuals and the Graphiti exclusion recorded in docs/786 and the legacy decision |
| preregistered legacy-upgrade threat and migration decision | `../809-legacy-upgrade/` (decision, three byte-frozen v7-origin stores, three fail-first baselines, two independent review rounds with YES at `ad52cc9b` and `4b18493f`, first execution with two recorded harness findings, second execution 10 passed / 26 subtests) | IMPLEMENTED at `bd8a67e3`: `legacy_upgrade_status()` / `upgrade_canonical_derivation()`; cross-scope and forward-reference stores read `legacy_qualified` with the oracle closed; the shared-membership store reads `legacy_unqualified` with its three edges quarantined (kept bound, reported) |
| ADR-030 semantic-compatibility assessment | `adr-030-semantic-compatibility-assessment.md` | written; recommends a declared derivation-semantics identity and a minor bump to `1.9.0`, not a major boundary; the owner decides; contract stays `1.8.0` provisional |
| runtime sharp edge tracked separately | issue #816 | open, not conflated |

| identity | value |
|---|---|
| final head | `03ddaef9c0c497466ae52603a69d51078df0b444` (clean tree for every replay and the Gauntlet probe) |
| protected tree `reference/agentmem_ref` | `2a00f31f7ddd9e5677e5c968523def77d186dec5`; `pyproject.toml` `59e8f97c…` unchanged |
| declaration | regenerated with the sanctioned tool: 17 declared blobs (`checkpoint_migration.py`, `state/substrate.py`, `state/sqlite_substrate.py` new since `c70fe315`; `adapter.py`, `api/surface.py`, `recall_control.py` moved on); `--register …DEMO.json --candidate HEAD` → `TRANSITION`; real register untouched |

| evidence at `03ddaef9` | outcome |
|---|---|
| four security replay contracts (`reports/validation/809-security-replays/`, the `c70fe315` execution preserved byte-for-byte under `809-security-replays-c70fe315/`) | DSL/3 `evidence-reference-authorization-v1` PASS 13/13; `-v3` through DSL/2 PASS 13/13, 10/10, 8/8; verifier `evidence_verified: true`, VERIFIED / PASS / re-executed ×4 on the clean tree |
| five v7 replay contracts (`final-03ddaef9/replays/`) | VERIFIED / PASS / re-executed ×5; inventory BLOCKED by design |
| preregistered unit modules | `test_809_evidence_reference_authorization.py` (executed as committed at `8272b38e`) and `test_809_legacy_upgrade.py` (executed as committed at `4b18493f`) pass inside the full suite |
| public Gauntlet probe (`final-03ddaef9/gauntlet/`) | `status: complete`, `exact_top1 1.0`, `correct_top1 3/3`, `authority_effect none`, frozen revision `03ddaef9` |
| write latency by citation case (`final-03ddaef9/timing/`) | medians deleted 13282 µs, live 13174 µs, unknown 13262 µs, none 13239 µs (ratios 1.002 / 0.993 / 1.000 / 0.998) |
| conformance (`final-03ddaef9/conformance-summary.json`) | `derived_state_hard_gate_passed: true`; known failures = the four freeze guards |
| full reference suite (`final-03ddaef9/full-suite-summary.log`) | 4 failed (the by-design freeze guards), 2979 passed, 35 skipped, 1 xfailed, 2079 subtests (5m02s) |
| blind theatre and vineyard holdouts (`final-03ddaef9/blind-holdouts/summary.json`) | rate-identical to the pre-repair head on both corpora and both modes (theatre top1_critical 0.4286 / 0.7619, vineyard 0.45 / 0.90); P0 prohibited and stale exposures 0 on every run; both runtimes clean |

Statuses at `03ddaef9`, kept distinct: IMPLEMENTED (repair `b932bd2f`, code-review fixes `6bdff75b`, legacy upgrade `bd8a67e3`); TESTED (locally, this table); INDEPENDENTLY REVIEWED (expectations, replay generation, production diff at `0808cb61`, legacy decision); DECLARED: no (`TRANSITION` under the demo register only); QUALIFIED: no; MERGED: no. The owner's decisions still owed: the legacy-upgrade decision's quarantine reading (a) versus (c), the contract version (ADR-030 assessment), the register pointer. Security acceptance is not claimed.

## Statuses

IMPLEMENTED (`b932bd2f`); TESTED (locally, at `c70fe315`/`631e9b71`); INDEPENDENTLY REVIEWED
(preregistered expectations: three rounds, final YES; replay generation: three rounds, final YES;
the runtime diff itself was reviewed only through those expectations and the reviewer's design
section D, not by a separate adversarial code review); DECLARED: no (proposal regenerated;
`TRANSITION` under the demo register only); QUALIFIED: no; MERGED: no. The owner's HOLD on PR #805
stands: no register mutation, no activation, no security acceptance claimed.
