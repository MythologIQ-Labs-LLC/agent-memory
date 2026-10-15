# Integration candidate evidence after the owner's PR #805 checkpoint (contract 1.8.0)

Candidate evidence for the integrated runtime stack #783 → #784 → #788 → #804 reconciled with
`main` `38f6a7dc`, after the owner's checkpoint on PR #805 (review 5526286544): contract `1.8.0`
adopted, `security_replay` a first-class acceptance evidence kind, the trust boundary recorded.
**Not** acceptance, not a baseline publication; the owner's HOLD stands (no merge, no register
mutation, no security acceptance, no activation). Produced locally (no GitHub Actions, no hosted
CI, no paid provider).

- runtime protected blobs (`pyproject.toml`, `reference/agentmem_ref`) pinned at `ef8b6cb226f2ae1eaeab716b1432b6b9fb4f0bbe`
  (the commit that adopts 1.8.0); every later commit on the branch changes tests, documentation
  and evidence only, and `git ls-tree` of the protected paths is identical at each of them.
- replays, Gauntlet probe, focused and full suites executed at `ecbcbf33a8203b34d670218a57a5d9731514cc98`
  (`ef8b6cb2` + the two future-minor test literals); blind holdouts executed at `ef8b6cb2` (clean tree).
- the branch head that adds this directory and the review record is the evidence commit on top.
- the cumulative v6 → v8 declaration (`reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json`)
  was regenerated with the sanctioned tool at `ef8b6cb2`: 14 protected blobs, identity delta
  `1.6.0 -> 1.8.0`, the three `-v2` security replays listed under `kind: security_replay`.

| evidence | command (repository root, clean tree) | outcome |
|---|---|---|
| three #786 security replay contracts (`786-security-replay-dsl/1`, `-v2`; fixtures untouched) | `python3 reference/run_786_security_replays.py --all --output-dir <scratch>`, then `python3 scripts/verify_786_security_replays.py --evidence-root <scratch> --reexecute` (exit 0); the verifier now reads the declaration itself | all three `VERIFIED` / `PASS` / re-executed, 28/28 cases (`security-replays/`); the committed copy verifies again without re-execution |
| five #644 v7 replay contracts | `python3 reference/run_644_v7_replays.py --all --output-dir <scratch>`, `python3 scripts/verify_644_v7_replays.py --reexecute --evidence-root <scratch>` (exit 0), `python3 scripts/check_644_v7_replay_inventory.py --evidence-root <scratch>` (exit 2, BLOCKED by design) | all five `VERIFIED` / `PASS` / re-executed, 104/104 (`replays/`) |
| public Gauntlet probe through the public facade | scratch contestant (v7 stdio adapter with `FROZEN_RUNTIME_REVISION=ecbcbf33…`, `PUBLIC_CONTRACT_VERSION=1.8.0`; not committed), `gauntlet-orchestration-retrieval-probe-v1` | `status: complete`, `exact_top1 1.0`, `correct_top1 3/3`, `authority_effect none` (`gauntlet/`) |
| blind theatre and vineyard holdouts (served-memory quality evaluator v3 @ `9961067`) | scratch harness identical to `reports/validation/774-on-integrated-head/measure_head.py`, `060e7cd7` vs `ef8b6cb2`, `composed` and `strict-target` | rate-identical on both heads (theatre top1_critical 0.4286 / 0.7619, vineyard 0.45 / 0.90); P0 prohibited and stale exposures 0 on every run; both runtimes clean (`blind-holdouts/summary.json`) |
| contract 1.8.0 surface: compatibility states, six versioned schemas, facade and runtime results, #777 successor and compatibility review, #786 suites, succession tests | `python3 -m pytest reference/tests/test_api_contract.py reference/tests/test_api_surface.py reference/tests/test_api_action_authority.py reference/tests/test_777_contract_1_7_successor.py reference/tests/test_777_contract_1_7_compat_review.py reference/tests/test_developer_facade.py reference/tests/test_typed_propositions.py reference/tests/test_rc_cognitive_memory_scenario.py reference/tests/test_facade_recall_control.py reference/tests/test_786_*.py reference/tests/test_runtime_baseline_succession.py -q` | passed (186 + 40 across the two runs; every `1.0.0`–`1.7.0` envelope stays `current` with a `1.8.0` result, `1.9.0` reads `migration_required`) |
| `security_replay` evidence kind | `reference/tests/test_786_security_replay_evidence_kind.py` | 4 passed: schema admits the kind and rejects unknown kinds; the declaration lists the three frozen `-v2` refs; the verifier reads the declaration by default; the identity delta equals `CONTRACT_VERSION` |
| payload-level scope separation (independent replay review, finding 7) | `reference/tests/test_786_cross_scope_write_authority.py::PayloadLevelSeparation` | 2 passed: after a pruning and after an attested permanent deletion followed by a foreign re-creation and correction, the whole serialised `history`, `recall` and `write_semantics` payloads of the re-creating scope contain no identifier or text of the former generation, the former owner's whole public view is unchanged, and a third project reads a never-written memory |
| #802 cache, permanent deletion, recovery, developer facade | 4 modules | 66 passed, 1 skipped |
| #774/#776/#777 lineage and disclosure, #786, deletion authority and completeness (22 modules) | | 201 passed, 133 subtests |
| restart, recovery, scope, isolation, tenancy, shared revocation, checkpoint | | 62 passed |
| durability gauntlet through the real facade | from the repository root | 14 passed |
| root-level tests and architecture catalog validator (#797) | | 19 OK |
| full reference suite | `python3 -m pytest reference/tests -q` from the repository root at `ecbcbf33` | 2921 passed, 4 failed, 35 skipped, 1870 subtests (4m07s); the four are the by-design freeze guards (`test_644_v7_gauntlet_identity…`, two `test_770…ReplayEvidenceFreshness`, `test_benchmark_integration_contract…equivalence`), identical on every head of the stack |
| reference conformance report | `python3 reference/run_conformance.py` | no fixture failed; `derived_state_hard_gate_passed: true`; `known_failures` = the four guards |
| Runtime Baseline equivalence and declaration | `python3 scripts/check_runtime_baseline_equivalence.py --register reports/runtime/proposals/786-scratch-register-v8.DEMO.json --candidate HEAD` | `TRANSITION … 14 declared blobs; deltas=identity.public_contract_version 1.6.0->1.8.0` (exit 0); `--pinned-only` exit 1 by design; real register exit 1 by design |

## Independent invariant-by-invariant replay review

`independent-replay-review-v2.md` is a separate agent's read of the 28 `-v2` cases against the
hashed contract sources, the runner, the verifier and the committed evidence (reviewed at
`e5abd116`; fixture digests recorded). It approves nothing. Verdict: 21 of 28 cases correspond to
the hashed contract sources, W7c and L5b correspond to the contract at head but not to the sources
hashed at `560785a8` (one commit before the closed-generation clauses), W4b/L2/R6b each carry one
sub-expectation not derivable from a cited contract (positive-control side observables), L5 is
weaker than its statement (no restart), L6's wording is stronger than its probes. No expectation
contradicts a contract clause; no post-execution correction weakened a security claim; no BLOCKING
finding. Acted on here without touching the frozen fixtures: finding 2 (W4 privileged-host caveat
in the fixtures README, docs/44, docs/786), finding 7 (the payload-level probes above), finding 9
(docs/44 now distinguishes the fact-level `already_deleted` answer from the facade's by-reference
`fact_not_found`). Findings 1, 6, 8, 10, 11, 13 are for the owner's acceptance record or a `-v3`
generation; nothing in `-v2` was edited to match observed output.

## Statuses

IMPLEMENTED; TESTED (locally); INDEPENDENTLY REVIEWED (runtime: three reviews of #788, three of
#804; fixtures: this record); DECLARED: no (proposal only, `TRANSITION` under the demo register);
QUALIFIED: no; MERGED: no. The owner's HOLD from the PR #805 checkpoint stands.
