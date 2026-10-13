# #786 security replay fixtures (`786-security-replay-dsl/1`)

A separate replay family beside the five frozen #644 v7 contracts. Nothing under
`reference/fixtures/644-v7-replays/`, `reference/run_644_v7_replays.py` or
`reports/validation/644-v7-replays/` is touched, so the v7 evidence keeps binding.

| replay | contract sources | what it holds |
|---|---|---|
| `cross-scope-write-authority-denial-v1` | docs/786, docs/44 | #786: remember/correct/forget/dispute by another project refused and non-disclosing, restart, overrides, positive controls, denied-episode non-persistence, no public trace, a re-created generation's own counter |
| `deleted-lineage-generations-and-restart-v1` | docs/774-776 contract, docs/774 policy, docs/786 | #776/#774: deletion withholds the generation, owner and other-project re-creation, three-generation as-of barriers, partial and permanent deletion, restart |
| `public-tombstone-redaction-and-observer-separation-v1` | docs/777 successor qualification, docs/44, docs/786 | #777/DUR-DEL-001: owner tombstone view, other observers read unknown, view stability under another scope, derived-from-deleted withholding, re-created history, no former count |

**Freeze rule.** `author_fixtures.py` generated the JSON from the contract documents named in
each `contract_sources` (hashed at `base_commit`). The fixtures were executed once with
`--allow-dirty` before freezing; the single corrected expectation is recorded in every
fixture's `development_history`. After the freeze commit a fixture is never edited: a wrong
expectation is superseded by a `-v2` fixture that records the reason. The expectations were
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
same call on `memory:never`, ids and timestamps folded), `recall_admitted`, `recall_mentions`,
`recall_same_as_unknown`, `fact_valid`, `fact_exists`, `tombstoned_ids`, `disputed`,
`episode_present`, `write_semantics_present`, `version_in_effect`, `op_result`, `op_mentions`.
Matchers are `eq`, `ne`, `in`, `not_in`.
