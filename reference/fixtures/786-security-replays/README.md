# #786 security replay fixtures (`786-security-replay-dsl/1`)

A separate replay family beside the five frozen #644 v7 contracts. Nothing under
`reference/fixtures/644-v7-replays/`, `reference/run_644_v7_replays.py` or
`reports/validation/644-v7-replays/` is touched, so the v7 evidence keeps binding.

Current fixtures are the `-v2` set (28 cases); the `-v1` set (22 cases, frozen at `b70ff58a`)
is superseded, kept byte-for-byte for provenance (`status: supersedes_v1` and
`supersession_reason` in each `-v2` fixture name what the second independent review found
wanting in v1). The runner still executes a `-v1` id on request; the cumulative v6 -> v8 declaration
(`reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json`, read by the verifier, which lists
the family under the first-class `security_replay` evidence kind) names only the `-v2` ids.

Reading note for W4 / W4b (owner's PR #805 checkpoint; the frozen fixture text is not edited): the
complete-scope override those cases admit is a property of the privileged-host model, not of the
facade as an isolation boundary. The facade does not authenticate who submits `overrides` or the
handle's scope; a host that declares a complete scope is trusted to have bound authenticated
authority to it first (docs/44 "Scope is privileged host input", docs/786 "What remains disclosed").
The cases prove that the override is judged exactly as a handle opened with that scope would be,
not that an end user is isolated from a host that can declare the owner's scope. The independent
invariant-by-invariant record of the `-v2` set is `reports/validation/805-at-head/independent-replay-review-v2.md`.

| replay | contract sources | what it holds |
|---|---|---|
| `cross-scope-write-authority-denial-v2` | docs/786, docs/44 | the v1 cases plus: refusal tokens and `v0` states after restart (W3), the documented superset-override admission of forget/dispute and the complete-scope override commit (W4b), owner recall candidates (W5), a former owner's `delete_version`/dispute/forget/remember against a re-created id leave no trace and answer the same as with no re-creation (W7b, W7c), refused and parked proposals on a tombstoned id report `v0` (W8b) |
| `deleted-lineage-generations-and-restart-v2` | docs/774-776 contract, docs/774 policy, docs/786 | the v1 cases plus refusal tokens (L3) and re-deletion of a deleted head answering `already_deleted` (L5b) |
| `public-tombstone-redaction-and-observer-separation-v2` | docs/777 successor qualification, docs/44, docs/786, docs/plan-776-777-772 | the v1 cases plus refused and parked proposals on a tombstoned id carrying no former count into the re-created generation's receipts or history (R6b) |
| `cross-scope-write-authority-denial-v1` (superseded) | docs/786, docs/44 | #786: remember/correct/forget/dispute by another project refused and non-disclosing, restart, overrides, positive controls, denied-episode non-persistence, no public trace, a re-created generation's own counter |
| `deleted-lineage-generations-and-restart-v1` (superseded) | docs/774-776 contract, docs/774 policy, docs/786 | #776/#774: deletion withholds the generation, owner and other-project re-creation, three-generation as-of barriers, partial and permanent deletion, restart |
| `public-tombstone-redaction-and-observer-separation-v1` (superseded) | docs/777 successor qualification, docs/44, docs/786 | #777/DUR-DEL-001: owner tombstone view, other observers read unknown, view stability under another scope, derived-from-deleted withholding, re-created history, no former count |

**Freeze rule.** `author_fixtures.py` generated the JSON from the contract documents named in
each `contract_sources` (hashed at `base_commit`). A fixture is executed with `--allow-dirty`
before freezing; every expectation corrected by that first execution, and every runtime finding
it produced, is recorded in the fixture's `development_history`. After the freeze commit a
fixture is never edited: a wrong expectation is superseded by a `-v2` (`-v3`, ...) fixture that
records the reason. The `-v2` first execution found one runtime finding (W7c, fixed in the
adapter: `docs/786` F-G/F-H) and three expectation errors (W4b, W5, R6b, corrected to the
owner-only control behaviour); no expectation was changed to match a refusal string. The expectations were
written by the session that implemented the repair, so they are preregistered but not
independent of the implementer (`independence` says so); an independent reviewer must read
them against the contracts before any acceptance.

## Scenario (`steps`)

Each case starts from a fresh SQLite store (tenant `tenant:s786`, actor `agent:s786`). One
handle is live at a time; `as` names the project a step runs under (`project:a` owns,
`project:b` is the other project); a scope switch closes the handle and recovers a fresh one.

| op | effect |
|---|---|
| `remember` (`ref`, `text`, `prop?`, `evidence_refs?`, `overrides?`, `label?`) | public `AgentMemory.remember`; a `ValueError` is recorded as `raised` |
| `correct` (`ref`, `text`, `kind`, `overrides?`, `label?`) | public `correct` with qualified evidence, `state_change` by default |
| `forget` (`ref`, `permanent?`, `overrides?`) | public `forget` |
| `dispute` (`ref`, `fact?`, `overrides?`) | public `dispute` |
| `delete_version` (`ref`, `fact`) | the #777 review's governed pruning of one superseded version |
| `commit_with_episode` (`ref`, `text`, `episode`, `risk?`) | the governed commit with an `Episode`, through the handle's own proposal envelope |
| `reopen` | close and recover the live handle |

`name` keeps a step's outcome for the `op_result` / `op_mentions` probes; `require_committed`
turns a refusal into a scenario error. Labels: the owner's first fact of `ref` is `ref`, later
heads `ref@2`…; the other project's are `project:b|ref`; `label` overrides.

## Probes

`canonical_head`, `canonical_version`, `history` (projected, uuids as labels, events as
types), `history_same_as_unknown`, `op_same_as_unknown` (correct/forget/dispute compared to the
same call on `memory:never`, ids and timestamps folded), `recall_admitted`, `recall_candidates`, `recall_mentions`,
`recall_same_as_unknown`, `fact_valid`, `fact_exists`, `tombstoned_ids`, `disputed`,
`episode_present`, `write_semantics_present`, `version_in_effect`, `op_result`, `op_mentions`.
Matchers are `eq`, `ne`, `in`, `not_in`.
