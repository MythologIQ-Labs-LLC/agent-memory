# Plan: #674 P0 — a successor-baseline procedure for Runtime Baseline v1

**change_class**: governance
**doc_tier**: standard
**risk_grade**: L2
**research_artifact**: docs/research-brief-north-star-six-tranches-2026-10-06.md (ledger Entry #60; research gate `2026-10-06T1200-668ns/research.json`, gitignored)
**roadmap**: `.qor/roadmaps/north-star-best-in-class` scope `scope-p0-baseline-procedure-plan` (handoff recorded); the merged outcome resolves `prereq-successor-baseline`, which gates every runtime tranche scope (#669, #670, #671, #673)
**iteration**: 3 (attempt-1 VETO V1-V3, C1-C4, A1-A4 amended, Entry #61, Shadow Genome Failure #13; attempt-2 VETO V1, C1-C4, A1-A6 amended, Entry #62, Failure #14)

**terms**:
- term: baseline register
  home: docs/67-runtime-baseline-succession.md
- term: declared successor
  home: docs/67-runtime-baseline-succession.md
- term: transition
  home: docs/67-runtime-baseline-succession.md
- term: pinned
  home: docs/67-runtime-baseline-succession.md

**boundaries**:
- limitations: a baseline is published only after the runtime change it names has merged, against that merge commit, exactly as v1 was published against `f2aef57` after PR #646; between that merge and the publication the repository is in a declared transition, and the checker says so on every run. During a transition the protected surface is still pinned: it must equal the frozen surface plus the exact git blobs the declaration names, nothing else. The procedure admits one declared successor at a time, and none while the current baseline's public-Gauntlet qualification is `pending`. Publication is two commits by construction (a record with `pending` qualification, then the evidence binding), because a record cannot name a Gauntlet run that was produced after the record existed. Nothing here decides which bytes a tranche may change; the tranche's own plan, audit and lane gates do.
- non_goals: changing runtime behaviour (the protected surface is untouched; `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` stays `PASS` on this plan's own commits); authoring Runtime Baseline v2 (that is the publication step of the first runtime tranche); the lane ids for the next lanes (`prereq-lane-v3-ids`); revising the v1 source boundary's protected or excluded sets; any relaxation of the diff (a transition is pinned to declared blobs, never to a path allowlist); editing `reports/runtime/baseline-v1.json`, `baseline-v1.md` or `baseline-v1-source-boundary.json` (the register pins their git blobs to the commit that published them and the validator refuses a change).
- exclusions: `reports/runtime/baseline-v1.json`, `baseline-v1-source-boundary.json`, `examples/gauntlet/agent-memory-runtime-baseline-v1.json`, `examples/gauntlet/agent_memory_runtime_baseline_stdio.py` and `fixtures/gauntlet/agent-memory-public-durability-adapter.json` are byte-unchanged; `scripts/import_amb_lane_evidence.py` and `scripts/import_longmemeval_lane_evidence.py` are not changed (they bind exact revisions already); `reference/agentmem_ref/**` and `pyproject.toml` are not touched; `.github/workflows/benchmark-integration-contract.yml` keeps its single checker call unchanged (a `TRANSITION` is acceptable there: its contract tests claim no revision, and LD6 makes the test it runs accept both green states).

## Open Questions

None blocking. Two defaults are taken and flagged for the owner; each is a one-line change if overruled:

1. **Transition exit code.** `TRANSITION` exits 0 by default and 1 under `--pinned-only`. The alternative (always 1) would make every runtime tranche PR red until publication, which is the state #674 exists to end. Workflows whose evidence claims an exact revision skip their evidence steps on `TRANSITION` (LD7).
2. **One declared successor at a time.** A second tranche that merges during a transition amends the open declaration (its `declared_changes` and `identity_deltas`, same `baseline_id`) rather than declaring a third baseline; the amended declaration still pins every changed blob. The register has one `declared_successor` slot by construction.

## Locked Decisions

**LD1 — The register is the only place that says which baseline is current, and it pins published bytes to history.** New `reports/runtime/baseline-register.json`:

```json
{
  "schema_version": 1,
  "register_id": "agent-memory-runtime-baseline-register",
  "baselines": [
    {
      "baseline_id": "agent-memory-runtime-baseline-v1",
      "record": "reports/runtime/baseline-v1.json",
      "record_blob": "c8acfa1d94856bb88c7b77f498d74a81913c10ca",
      "source_boundary": "reports/runtime/baseline-v1-source-boundary.json",
      "source_boundary_blob": "f0ffc998033939288c816698111983fa371c4e90",
      "public_gauntlet_manifest": "examples/gauntlet/agent-memory-runtime-baseline-v1.json",
      "qualification": {
        "path": "reports/runtime/baseline-v1.json",
        "pointer": "qualification_evidence.public_gauntlet_baseline_qualification",
        "blob": "c8acfa1d94856bb88c7b77f498d74a81913c10ca"
      },
      "published_commit": "c3a1bdf19bafca720a6513661cad3f08127659a5"
    }
  ],
  "declared_successor": null
}
```

The last entry is the current baseline; there is no `status` field and no `superseded_by` (order is the lineage). `frozen_revision` is not repeated: it is read from the boundary, and the validator requires `boundary.frozen_revision == record.runtime_revision.commit`. `record_blob` and `source_boundary_blob` are `git hash-object` of the named files at the candidate. `published_commit` is a commit on the candidate's first-parent history whose tree holds exactly the record and boundary blobs (`git rev-parse <published_commit>:<path>` equals each pin); it is `null` only while the entry's qualification is `pending` (LD5). The authoring commit of a file is not the right pin under a first-parent rule (the repository merges with merge commits, so `git log -1 -- <path>` names a side-branch commit); for v1 the pin is `c3a1bdf`, the merge of PR #651, which is the first first-parent commit of `main` whose tree holds both blobs. `qualification` names where the entry's public-Gauntlet block lives and pins that file's bytes too: inside the record for v1 (`pointer` is a dotted path and `blob` equals `record_blob`), in a companion `reports/runtime/baseline-v<N>-qualification.json` with `pointer: ""` for every successor, so a successor's record is never edited after publication (LD5). `qualification.blob` is verified against the candidate tree only, never against `published_commit`, because the qualification file is written after the record's publication commit (LD8 Step B2). `declared_successor` is `null` or `{"baseline_id": ..., "declaration": "<path>"}`.
Grep-evidence for the first-parent predicate on the v1 pin:
`git rev-list --first-parent origin/main | grep -c c3a1bdf19bafca720a6513661cad3f08127659a5 -> 1`; `git rev-list --first-parent origin/main | grep -c 788ea6fdcf2dfa370dacf00944e52ae78654ad0e -> 0`; `git rev-parse c3a1bdf:reports/runtime/baseline-v1.json -> c8acfa1d94856bb88c7b77f498d74a81913c10ca`; `git rev-parse c3a1bdf:reports/runtime/baseline-v1-source-boundary.json -> f0ffc998033939288c816698111983fa371c4e90`
Grep-evidence for `scripts/check_runtime_baseline_equivalence.py:18`:
`git show origin/main:scripts/check_runtime_baseline_equivalence.py | grep -nE '^DEFAULT_BOUNDARY' -> 18:DEFAULT_BOUNDARY = ROOT / "reports" / "runtime" / "baseline-v1-source-boundary.json"`

**LD2 — A runtime change declares its successor before it merges, and the declaration pins every byte it changes.** New `schemas/runtime-baseline-declaration.schema.json` (`additionalProperties: false`), instance path `reports/runtime/baseline-v<N>-declaration.json`:

```json
{
  "schema_version": 1,
  "baseline_id": "agent-memory-runtime-baseline-v2",
  "predecessor_baseline_id": "agent-memory-runtime-baseline-v1",
  "issue": 673,
  "declared_changes": [
    {"path": "reference/agentmem_ref/runtime/ranking_policy.py", "blob": "0123456789abcdef0123456789abcdef01234567"},
    {"path": "reference/agentmem_ref/runtime/route_fusion.py", "blob": "89abcdef0123456789abcdef0123456789abcdef"}
  ],
  "identity_deltas": [
    {"identity_path": "identity.ranking.active_policy_version", "from": "3.1.2", "to": "3.2.0"}
  ],
  "pyproject_change": null,
  "acceptance_evidence_required": [
    {"kind": "public_gauntlet", "ref": "gauntlet-orchestration-retrieval-probe-v1"},
    {"kind": "lane", "ref": "longmemeval-s-retrieval-parity-v2"}
  ]
}
```

`declared_changes` is the complete list of protected, non-excluded paths whose bytes differ from the frozen revision, each with the exact git blob the candidate carries (`null` for a deleted file); a declaration with an empty list is invalid (a successor with no change is not a successor). `identity_path` must name an entry of the identity table (LD4); `from` must equal the predecessor record's value at that path. `pyproject_change` is `null` or `{"reason": "<non-empty>"}` and is required exactly when `pyproject.toml` is among `declared_changes`. `acceptance_evidence_required` is non-empty and each `kind` is one of `public_gauntlet`, `replay`, `lane`. The example above is the schema's own `examples` entry; no instance is committed by this plan. New `scripts/declare_runtime_baseline_changes.py --declaration <path>` rewrites only the `declared_changes` block from `git diff --name-only <frozen> -- <protected> <exclusions>` against the working tree and `git hash-object` of each listed working-tree file (deleted → `null`), so the author never computes a blob by hand; it refuses to run when `declared_successor` is `null` or names a different declaration. The declared blobs survive the tranche PR's merge because main cannot change a protected file without a declaration (LD3), so the pin is computable before merge and remains true after it.

**LD3 — The checker has three outcomes; a transition pins the surface to the frozen bytes plus the declared blobs and nothing else.** `scripts/check_runtime_baseline_equivalence.py` reads the register (`--register`, default `reports/runtime/baseline-register.json`; `--boundary` is removed) and resolves the current entry's boundary. With `changed = git diff --name-only <frozen> <candidate> -- <protected> <exclusions>` (the same pathspecs as today's `--exit-code` diff):

- `changed` empty → `PASS`, exit 0, stdout `Runtime Baseline equivalence: PASS; baseline=<id>; frozen=<rev>; candidate=<ref>; explicit non-runtime exclusions=<paths>`;
- `changed` non-empty and `declared_successor` is `null` → exit 1, `candidate <ref> changes the protected Runtime Baseline source surface relative to <rev> and the register declares no successor: <paths>`;
- `changed` non-empty and a declared successor → the declaration is loaded and schema-validated; the current entry's qualification must not be `pending` and its `published_commit` must not be `null`; `predecessor_baseline_id` must equal the current `baseline_id`; `sorted(changed)` must equal the sorted declared paths; for each declared path, `git rev-parse <candidate>:<path>` must equal the declared blob (a `null` blob requires the path to be absent at the candidate); for every delta, `read_identities(frozen)[path] == from` and `read_identities(candidate)[path] == to`; for every identity-table path not named by a delta, `read_identities(frozen)[path] == read_identities(candidate)[path]`; `pyproject_change` must be set exactly when `pyproject.toml` is declared. All hold → `TRANSITION`, exit 0, stdout `Runtime Baseline equivalence: TRANSITION; baseline=<id>; declared_successor=<id> (issue #<n>); protected surface = frozen <rev> + <k> declared blobs; deltas=<path> <from>-><to>[, ...]; candidate=<ref>`; with `--pinned-only` → exit 1, `candidate <ref> is in a declared transition to <id>; this check requires a pinned baseline`. Any check failing → exit 1 with one of, in this order: `declared successor <id> cannot open while <current> qualification is pending or unpinned`; `declared successor <id> names predecessor <x> but the current baseline is <y>`; `undeclared protected change: <path>`; `declared change absent from candidate: <path>`; `declared blob mismatch for <path>: declared <a>, candidate <b>`; `declared delta <path>: predecessor value is <a>, declaration says from=<b>`; `declared delta <path>: candidate value is <a>, declaration says to=<b>`; `undeclared identity <path> changed: frozen=<a>, candidate=<b>`; `pyproject.toml declared without pyproject_change` / `pyproject_change given but pyproject.toml is not declared`.

`check(root, register_path, candidate, *, pinned_only, identity_sources=IDENTITY_SOURCES) -> Outcome` where `Outcome` is a frozen dataclass `(state: str, baseline_id: str, frozen_revision: str, message: str)`; `main` prints `message` and maps the state to the exit code. `ROOT` stops being a module constant read by the functions: every function takes `root`, so the tests run the same code against a temporary repository (LD6). The three state strings are the public contract of the script; workflows grep them (LD7). The declaration is validated with `jsonschema` (a package dependency, `pyproject.toml:13`); every workflow that runs the checker installs the package first (LD7).
Grep-evidence for `scripts/check_runtime_baseline_equivalence.py:76`:
`git show origin/main:scripts/check_runtime_baseline_equivalence.py | grep -nE '^def check\(' -> 76:def check(boundary_path: Path, candidate: str) -> int:`

**LD4 — One identity table, read from any revision.** New `scripts/runtime_baseline_identity.py` holds, as data, the twenty-three `expect(...)` comparisons in `validate_runtime_baseline_source.py` that read the protected surface at the frozen revision (lines 100-146 today, twenty-three calls: the contract version (:100); the four profile values `runtime_id`, `runtime_version`, `profile_id`, `profile_version` read from `_profiles/rc1-local.json` (:104-107, kind `json`); the four `sqlite_substrate.py` constants, of which `SQLITE_SUBSTRATE_SCHEMA_VERSION` and `SQLITE_SUBSTRATE_PROFILE` land under `identity` and `BUCKETED_DIGEST_SCHEME` and `GOVERNANCE_SCHEME` under `persistence_and_durability.*_commitment.active_scheme` (:110-113); the typed relation schema (:116); the two query-interpreter values (:119-120) and the three write-interpreter values (:123-125); the five `ranking_policy.py` values `POLICY_FAMILY`, `POLICY_VERSION`, `LEXICAL_ANTI_LAUNDERING_GUARD`, `BM25_K1`, `BM25_B` (:128-132, the last two kind `numeric`) and the two `temporal_order_constraints.py` values `POLICY_VERSION` → `identity.ranking.active_policy_version` and `UNKNOWN_BASIS_POLICY` (:135-136); and the one candidate-routes comparison (:146) whose four constants span `runtime_composition.py` (three) and `vector_retrieval.py` (one) and become four rows), twenty-six rows:

```python
@dataclass(frozen=True)
class IdentitySource:
    identity_path: str      # dotted path into the baseline record, integer segments allowed
    file: str               # path inside the protected surface
    kind: str               # "constant" | "numeric" | "json"
    key: str                # constant name, or dotted key for kind "json"

IDENTITY_SOURCES: tuple[IdentitySource, ...] = (
    IdentitySource("identity.public_contract_version", "reference/agentmem_ref/api/contract.py", "constant", "CONTRACT_VERSION"),
    IdentitySource("identity.runtime_id", "reference/agentmem_ref/_profiles/rc1-local.json", "json", "runtime.runtime_id"),
    IdentitySource("persistence_and_durability.canonical_state_commitment.active_scheme", "reference/agentmem_ref/state/sqlite_substrate.py", "constant", "BUCKETED_DIGEST_SCHEME"),
    IdentitySource("read_semantics.candidate_routes.0", "reference/agentmem_ref/runtime/runtime_composition.py", "constant", "LEXICAL_ROUTE"),
    ...
)

def read_identities(root: Path, revision: str, sources=IDENTITY_SOURCES) -> dict[str, object]
def record_value(record: dict, identity_path: str) -> object
```

`git_show`, `constant`, `numeric_constant` and `git_blob_sha` move here unchanged. The six `expect` calls at lines 196-203 read the Gauntlet manifest at `verified_head`, not the protected surface; they stay in the validator as qualification checks (LD5). The checker (LD3) and the validator (LD5) share this module; the table is the single statement of what "identity" means for a baseline.
Grep-evidence for `scripts/validate_runtime_baseline_source.py:91`:
`git show origin/main:scripts/validate_runtime_baseline_source.py | grep -nE '^def main' -> 91:def main() -> int:`
Grep-evidence for `scripts/validate_runtime_baseline_source.py:100`:
`git show origin/main:scripts/validate_runtime_baseline_source.py | grep -nE 'expect\("public contract"' -> 100:    expect("public contract", constant(contract, "CONTRACT_VERSION"), identity["public_contract_version"])`

**LD5 — The validator validates the register, every record in it, and the open declaration; qualification is a two-state block.** `scripts/validate_runtime_baseline_source.py` `main` loads the register and, for each entry: readable record and boundary; `boundary.baseline_id == record.baseline_id`; `boundary.frozen_revision == record.runtime_revision.commit`; `boundary.baseline_mutation is False`; blobs match the candidate tree; identities at `frozen_revision` equal the record (LD4); `production_1_0` false; `authority_effect` none; the dogfood block is required with `status == "completed"`, `authority_effect == "none"`, `evidence_class == "baseline_or_probe"`, and the `#637` close-gate key and the ancestry check `merge-base --is-ancestor <frozen> <dogfood merge_commit>` run only for the entry whose record carries `dogfood.required_before_issue_638_close` (v1; a successor's dogfood block names the same `#637` evidence by pointer and is not re-run). The qualification block is read from `entry.qualification` (`record_value` over the named file and pointer) and is one of two shapes: `{"status": "pending", "profile_id": ..., "transport": "stdio"}`, or the complete shape v1 has today, on which every check at lines 170-203 runs unchanged (`verified_head` descends from the frozen revision; `require_frozen_runtime_equivalence` uses the boundary's pathspecs, not the bare two paths, so an evaluation-only commit between freeze and head is not drift; manifest and adapter read at `verified_head`). Register rules: `record_blob`, `source_boundary_blob` and `qualification.blob` equal `git hash-object` of the named files at the candidate; `published_commit` is required and verified (first-parent ancestor of the candidate, `git rev-list --first-parent <candidate>`; the record and boundary blobs equal `git rev-parse <published_commit>:<path>`) for every entry except a last entry whose qualification is `pending`; only the last entry may be `pending`. When `declared_successor` is set: the declaration validates against the schema, `predecessor_baseline_id` is the last entry's `baseline_id`, `baseline_id` is not already in `baselines`, each `from` equals `record_value(current_record, path)`, and the last entry is neither `pending` nor unpinned. `scripts/render_runtime_baseline.py` takes `--baseline <id>` (default: every register entry), derives the title (`# Agent Memory Runtime Baseline v<N>`), the generated-from line and the `#638` sentences from the record (`baseline_id`, `runtime_revision.baseline_issue`), reads the qualification block through the register entry, renders a `pending` block as `Public Gauntlet path: **pending**` with no head or digest, and writes `<record>.md` beside each record; `--check` compares every rendered file. The v1 rendering is byte-identical to today's `baseline-v1.md` (the test asserts it).
Grep-evidence for `scripts/validate_runtime_baseline_source.py:164`:
`git show origin/main:scripts/validate_runtime_baseline_source.py | grep -nE 'merge-base", "--is-ancestor", commit, dogfood_commit' -> 164:    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", commit, dogfood_commit], cwd=ROOT)`
Grep-evidence for `scripts/render_runtime_baseline.py:23`:
`git show origin/main:scripts/render_runtime_baseline.py | grep -nE '"# Agent Memory Runtime Baseline v1"' -> 23:        "# Agent Memory Runtime Baseline v1",`

**LD6 — The procedure is tested on a throwaway repository, not on this one.** New `reference/tests/test_runtime_baseline_succession.py` builds a temporary git repository in `setUp` (`git init`, `user.email`/`user.name` set locally) with a two-row identity table passed explicitly (`identity.public_contract_version` from `reference/agentmem_ref/api/contract.py` constant `CONTRACT_VERSION`; `identity.ranking.active_policy_version` from `reference/agentmem_ref/runtime/temporal_order_constraints.py` constant `POLICY_VERSION`), a `pyproject.toml`, an `evaluation/` subtree, a second protected module `reference/agentmem_ref/state/other.py`, a record, a boundary, and a register pinning their blobs; commits the frozen revision; then builds candidates by committing changes. It imports the scripts as modules from `scripts/` (sys.path insert of `REPO_ROOT / "scripts"`). Cases:

- `test_pass_when_only_evaluation_changes` → `PASS`;
- `test_fail_without_declaration` → exit 1, message names the frozen revision, "declares no successor" and the changed path;
- `test_transition_with_honest_declaration` → `POLICY_VERSION` 3.1.2→3.2.0 declared, the one changed file declared with its blob → `TRANSITION`, message carries "+ 1 declared blobs" and the delta;
- `test_pinned_only_refuses_transition` → exit 1 with the pinned message;
- `test_fail_when_undeclared_protected_file_changes` (declaration covers the ranking file; `state/other.py` also edited, no constant touched) → `undeclared protected change: reference/agentmem_ref/state/other.py`;
- `test_fail_when_declared_blob_differs` (declaration pins the first edit; a second edit lands) → `declared blob mismatch`;
- `test_fail_when_declared_change_is_absent`, `test_fail_when_declared_to_is_not_in_candidate`, `test_fail_when_declared_from_is_not_in_frozen`, `test_fail_when_undeclared_identity_changes` (contract constant changed, file declared with its blob, no delta for it), `test_fail_when_pyproject_declared_without_reason`, `test_transition_with_declared_pyproject_change`, `test_fail_when_predecessor_is_not_current`, `test_fail_when_current_is_pending` (register last entry qualification `pending`, a declaration present);
- `test_declare_script_writes_blobs` → the helper's `declared_changes` equals the checker's expectation and a second run is idempotent;
- register validator: `test_register_refuses_record_blob_drift` (edit the record bytes after pinning), `test_register_refuses_published_commit_with_other_bytes`, `test_register_allows_pending_last_entry_without_published_commit`, `test_register_refuses_pending_non_last_entry`;
- `test_register_pins_v1_bytes` on the real repository: the register's v1 blobs equal `git hash-object` of the v1 record and boundary at `HEAD` and `qualification.blob` equals `record_blob` (no history needed); when `c3a1bdf` is in the checkout, `git rev-parse c3a1bdf:<path>` equals each pin and `c3a1bdf` is on `git rev-list --first-parent HEAD`.

`test_benchmark_integration_contract.test_evaluation_only_change_keeps_runtime_baseline_equivalence` reads the boundary path from the register's last entry instead of the literal path, and, after its existing `returncode == 0` assertion, its stdout assertion becomes `assertRegex(result.stdout, r"Runtime Baseline equivalence: (PASS|TRANSITION)\b")` (a declared transition is a green state for a contract test that claims no revision; a failure exits 1 before the regex is reached).
Grep-evidence for `reference/tests/test_benchmark_integration_contract.py:379`:
`git show origin/main:reference/tests/test_benchmark_integration_contract.py | grep -nE 'assertIn\("PASS", result.stdout\)' -> 379:        self.assertIn("PASS", result.stdout)`

**LD7 — Workflows that claim an exact revision classify first and skip, never lie.** `.github/workflows/runtime-baseline.yml`: path triggers become `reports/runtime/baseline-*.json`, `reports/runtime/baseline-*.md`, `reports/runtime/baseline-register.json`, `schemas/runtime-baseline-declaration.schema.json`, `examples/gauntlet/agent_memory_runtime_baseline*_stdio.py`, `examples/gauntlet/agent-memory-runtime-baseline-*.json`, the five scripts (`check_runtime_baseline_equivalence.py`, `render_runtime_baseline.py`, `validate_runtime_baseline_source.py`, `runtime_baseline_identity.py`, `declare_runtime_baseline_changes.py`), `reference/tests/test_runtime_baseline_succession.py` and the workflow itself (so a successor's record, rendering, qualification, declaration, manifest or adapter triggers the run); after the install step, a step with `id: classify` runs the checker, tees its stdout, and writes `state=<PASS|TRANSITION>` to `GITHUB_OUTPUT` (`grep -oE 'equivalence: [A-Z]+'`); a step `id: current` prints `record=`, `boundary=`, `manifest=`, `adapter=` (the last element of the manifest's `transport.startup`, which is `examples/gauntlet/agent_memory_runtime_baseline_stdio.py` for v1 at manifest lines 51-54), `revision=` and `published_commit=` from the register's last entry to `GITHUB_OUTPUT`; the "Verify exact public contestant identity" step hashes `steps.current.outputs.adapter` instead of the literal v1 adapter path (line 66 today); the "Verify exact public contestant identity", "Validate public contestant manifest", "Run ... through public Gauntlet path", "Validate public-path qualification evidence", inventory and upload steps carry `if: steps.classify.outputs.state == 'PASS'` and assert against `steps.current` values instead of the literal `f2aef57…` and `agent-memory-runtime-baseline-v1` strings; a step `Transition notice` with `if: steps.classify.outputs.state == 'TRANSITION'` prints the checker line and exits 0. The upload step names its artifact after `steps.current.outputs.manifest`'s baseline id, so a `pending` publication PR (LD8 Step B1) produces the artifact that B2 binds. `.github/workflows/agmi-agent-memory-qualification.yml`: `python -m pip install -e .` moves above the checker; the same `classify` and `current` steps; the reproduction, validation and upload steps carry the `PASS` condition; the evidence header (lines 58-63 today) prints `agent_memory_frozen_runtime`, `agent_memory_runtime_source_boundary` and `agent_memory_baseline_merge` from `steps.current` (`revision`, `boundary`, `published_commit`) instead of the three literals; before reproducing, a step asserts `profile["agent_memory"]["runtime_baseline_revision"] == steps.current.outputs.revision` for `reports/gauntlet/agmi-agent-memory-v1/qualification.json` (line 22) so a stale profile is refused rather than copied into evidence (`scripts/run_agmi_agent_memory_qualification.py:90` copies the profile value and `scripts/validate_agmi_agent_memory_qualification.py:34` only compares evidence to profile); a transition notice. `.github/workflows/gauntlet-durability-recovery.yml`: an install step already precedes its assertions; `classify` and `current` steps after it; the inline assertion at line 55 compares `manifest["system"]["revision"]` to `git-commit:<steps.current.outputs.revision>` (so a stale `fixtures/gauntlet/agent-memory-public-durability-adapter.json`, line 87, is refused truthfully after a successor publishes); the durability run, evidence validation and upload steps carry the `PASS` condition; a transition notice. `.github/workflows/benchmark-integration-contract.yml`: unchanged (exclusions). Every workflow that asserts a baseline revision or runs the checker (`grep -rln 'check_runtime_baseline_equivalence\|f2aef57293b516e065cad5d0afea26ac7e3c28a9' .github/workflows`): these four. The probe assertions `exact_top1 == 1.0` and `sample_count == 3` in `runtime-baseline.yml` (lines 126-127) stay: they are the publication acceptance gate for the orchestration probe (a successor that cannot answer the three-query probe exactly does not publish), not authority and not a score the validator reads.
Grep-evidence for `.github/workflows/agmi-agent-memory-qualification.yml:62`:
`git show origin/main:.github/workflows/agmi-agent-memory-qualification.yml | grep -nE 'agent_memory_baseline_merge=' -> 62:            echo "agent_memory_baseline_merge=32783fad3c5cf50a9d712c8bcc0a023907ce9433"`
Grep-evidence for `.github/workflows/runtime-baseline.yml:66`:
`git show origin/main:.github/workflows/runtime-baseline.yml | grep -nE 'ADAPTER_REVISION="git-blob' -> 66:          ADAPTER_REVISION="git-blob:$(git hash-object examples/gauntlet/agent_memory_runtime_baseline_stdio.py)"`
Grep-evidence for `.github/workflows/gauntlet-durability-recovery.yml:55`:
`git show origin/main:.github/workflows/gauntlet-durability-recovery.yml | grep -nE 'manifest\["system"\]\["revision"\] == "git-commit:f2aef57' -> 55:          assert manifest["system"]["revision"] == "git-commit:f2aef57293b516e065cad5d0afea26ac7e3c28a9"`
Grep-evidence for `.github/workflows/agmi-agent-memory-qualification.yml:35`:
`git show origin/main:.github/workflows/agmi-agent-memory-qualification.yml | grep -nE 'check_runtime_baseline_equivalence.py --candidate HEAD' -> 35:        run: python scripts/check_runtime_baseline_equivalence.py --candidate HEAD`

**LD8 — The procedure is written down once, where contributors look.** New `docs/67-runtime-baseline-succession.md`: the four terms; the procedure in three steps. **Step A (the tranche PR)**: `reports/runtime/baseline-v<N>-declaration.json` and the register's `declared_successor`; `scripts/declare_runtime_baseline_changes.py` after the last protected edit; the checker prints `TRANSITION`; lane and replay evidence for the new runtime binds the exact commits it ran at, and the v1 lanes (`revision_rule` text "frozen at Runtime Baseline v1 f2aef57…") are not evidence for a successor until new lane ids exist (`prereq-lane-v3-ids`); a second tranche in the window amends the open declaration. **Step B1 (publication, no runtime change)**: `baseline-v<N>.json` with a `predecessor` block `{baseline_id, identity_deltas, declared_changes}` copied from the declaration, `runtime_revision.commit` = Step A's merge commit, a dogfood block pointing at the `#637` evidence, `baseline-v<N>-source-boundary.json` with that `frozen_revision`, `baseline-v<N>-qualification.json` with `status: "pending"`, `baseline-v<N>.md` rendered, `examples/gauntlet/agent-memory-runtime-baseline-v<N>.json` whose `transport.startup` names a copied adapter `examples/gauntlet/agent_memory_runtime_baseline_v<N>_stdio.py` with its `FROZEN_RUNTIME_REVISION`, `PUBLIC_CONTRACT_VERSION`, tenant, actor, scope and purpose constants (`examples/gauntlet/agent_memory_runtime_baseline_stdio.py:26-34`) updated to the successor, the register entry appended with its three blobs, `published_commit: null`, and `declared_successor: null`; the checker prints `PASS` again and `runtime-baseline.yml` runs the Gauntlet with the new manifest, producing the artifact. B1 also re-pins or retires every contestant and profile file that names the predecessor's revision, listed in docs/67: `fixtures/gauntlet/agent-memory-public-durability-adapter.json` (`system.revision`, line 87) and `reports/gauntlet/agmi-agent-memory-v1/qualification.json` and `accepted-result.json` (`runtime_baseline_revision`, lines 22 and 14), each re-pinned with fresh evidence or retired with its workflow condition; the lane files' `revision_rule` sentences are frozen lane facts and are not edited (a successor gets new lane ids). A red B1 run is not merged: the register is unchanged, the transition stays open, and the defect is fixed in a tranche that amends the declaration. **Step B2 (evidence binding)**: the qualification file becomes the complete shape (workflow run, artifact id and digest, `verified_head` = B1's PR head, `system_revision`, adapter blob); the register entry gets `published_commit` = B1's merge commit (whose tree holds the record and boundary bytes B1 pinned; the qualification file is not checked there) and the new `qualification.blob`; the record itself is untouched. What each checker line means, which workflows skip on `TRANSITION`, and the invariants: published records are blob-pinned to a commit in history; a transition pins the surface to frozen bytes plus declared blobs; one declared successor at a time and none while the current baseline is `pending` or unpinned; a declaration is a claim the checker verifies in both directions. `docs/CONTRIBUTOR_ARCHITECTURE.md` §8 retitled "Runtime Baseline source equivalence and succession": the first paragraph names the register as the source of the current baseline, the three outcomes, and links docs/67. `docs/GOVERNANCE_INDEX.md` Tier 4: this plan `ACTIVE`, the research brief `supporting research`; a Tier 2 row for docs/67. `reports/runtime/baseline-v1.json` is not edited (its `drift_policy` already says `observable_behavior_changes_must_bind_new_revision`; docs/67 is where that sentence becomes a procedure).

## Phase 1: register, shared identity table, register-aware validator and renderer

### Affected Files

- `reports/runtime/baseline-register.json` - new, LD1
- `scripts/runtime_baseline_identity.py` - new, LD4
- `scripts/validate_runtime_baseline_source.py` - register loop, identity table, two-state qualification, declaration checks, LD5
- `scripts/render_runtime_baseline.py` - `--baseline`, register default, record-derived title and sentences, LD5
- `reference/tests/test_runtime_baseline_succession.py` - new: register-validator cases, `read_identities`, `record_value`, `test_register_pins_v1_bytes`, LD6

### Changes

Write the register with the three blob values and `published_commit` `c3a1bdf…`. Move `git_show`, `constant`, `numeric_constant`, `git_blob_sha` into the new module; add `IdentitySource`, `IDENTITY_SOURCES` (twenty-six rows), `read_identities`, `record_value`. Rewrite `validate_runtime_baseline_source.main` as `validate_register(root, register_path) -> None` plus `main`; `require_frozen_runtime_equivalence` takes the boundary dict and uses its pathspecs. `render_runtime_baseline.render(data, qualification)`; `main` iterates the register.

### Unit Tests

- `reference/tests/test_runtime_baseline_succession.py` - the four register-validator cases and the v1 blob pin; `read_identities` on the temporary repository returns the two declared values at the frozen revision; `record_value` resolves an integer segment (`read_semantics.candidate_routes.3`); the v1 rendering equals `reports/runtime/baseline-v1.md` byte for byte.
- `python scripts/validate_runtime_baseline_source.py` and `python scripts/render_runtime_baseline.py --check` exit 0 on the real repository with v1 unchanged.

## Phase 2: declaration schema, the declare helper, and the three-outcome checker

### Affected Files

- `schemas/runtime-baseline-declaration.schema.json` - new, LD2
- `scripts/declare_runtime_baseline_changes.py` - new, LD2
- `scripts/check_runtime_baseline_equivalence.py` - register, declaration, declared blobs, `Outcome`, `--pinned-only`, root-parametrised functions, LD3
- `reference/tests/test_runtime_baseline_succession.py` - the checker and helper cases, LD6
- `reference/tests/test_benchmark_integration_contract.py` - register path; `PASS` or `TRANSITION`, LD6

### Changes

Schema per LD2 with the v2 example under `examples`. Helper per LD2. Checker per LD3: `load_register(root, path)`, `current_entry(register)`, `changed_paths(root, boundary, candidate) -> list[str]`, `candidate_blob(root, candidate, path) -> str | None`, `load_declaration(root, entry) -> dict` (jsonschema), `verify_declaration(root, frozen, candidate, record, entry, declaration, sources) -> list[str]` returning the failing messages in LD3's order, `check(...) -> Outcome`, `main`. `_load_boundary` keeps its structural refusals verbatim.

### Unit Tests

- `reference/tests/test_runtime_baseline_succession.py` - the fifteen checker cases and the helper case listed in LD6; each asserts the exact message prefix from LD3.
- `reference/tests/test_benchmark_integration_contract.py` - the parsed state is `PASS` or `TRANSITION`.

## Phase 3: workflows and documentation

### Affected Files

- `.github/workflows/runtime-baseline.yml` - install before classify, `current`, `PASS`-conditioned evidence steps, transition notice, LD7
- `.github/workflows/agmi-agent-memory-qualification.yml` - install moved above the checker, classify, `PASS`-conditioned reproduction, LD7
- `.github/workflows/gauntlet-durability-recovery.yml` - classify, register-derived revision, `PASS`-conditioned run, LD7
- `docs/67-runtime-baseline-succession.md` - new, LD8
- `docs/CONTRIBUTOR_ARCHITECTURE.md` - §8, LD8
- `docs/GOVERNANCE_INDEX.md` - Tier 4 and the docs/67 row, LD8

### Changes

Per LD7 and LD8. No literal baseline revision or baseline id remains in the three workflows outside their path triggers.

### Unit Tests

- `reference/tests/test_runtime_baseline_succession.py` - `test_workflows_carry_no_literal_v1_revision`: none of the three workflow files contains `f2aef57293b516e065cad5d0afea26ac7e3c28a9`, `32783fad3c5cf50a9d712c8bcc0a023907ce9433` or `agent-memory-runtime-baseline-v1` outside a path trigger line; each contains `--candidate HEAD` once, in a step whose id is `classify`, after a step that installs the package.
- `qor-logic governance-health --profile skill-entry` stays green after the index edits.

## Definition of Done

### Deliverable: the register names the current baseline and pins its bytes to history

- **D1**: `reports/runtime/baseline-register.json` with v1 last, three blobs pinned, `published_commit` `c3a1bdf` verified on first-parent history; the validator refuses blob drift, a published commit holding other bytes, a `pending` entry that is not last, and a declaration while the current entry is `pending` or unpinned.

### Deliverable: a transition is pinned, and a declaration is verified in both directions

- **D2**: the checker prints exactly one of `PASS`, `TRANSITION`, or a failure message from LD3; a transition is honoured only when the changed protected paths equal the declared paths, every declared blob matches, every declared delta holds at both ends and no undeclared identity moved; `--pinned-only` refuses a transition.

### Deliverable: publication is executable and workflows tell the truth during a transition

- **D3**: a `pending` publication passes the validator and triggers the Gauntlet run that its evidence-binding commit cites; the three revision-claiming workflows skip their evidence steps on `TRANSITION` and print why; docs/67 states Steps A, B1 and B2; CONTRIBUTOR_ARCHITECTURE §8 and GOVERNANCE_INDEX point to it.

## Feature Inventory Touches

| entry_id | operation | test_path | test_descriptor |
|---|---|---|---|
| n/a (governance tooling under `scripts/`, `reports/runtime/`, `schemas/`, `.github/workflows/`, `docs/`; no `reference/agentmem_ref` feature is touched) | n/a-justified | `reference/tests/test_runtime_baseline_succession.py` | the three checker outcomes, the declared-blob pin, the dishonest-declaration refusals, the register invariants and the v1 blob pin |

## CI Commands

- `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` — prints `PASS` for this plan's own commits (no protected path changes)
- `python scripts/validate_runtime_baseline_source.py` — register, v1 record, blobs at `c3a1bdf` and identities at `f2aef57` agree
- `python scripts/render_runtime_baseline.py --check` — `baseline-v1.md` is byte-identical to the rendering
- `python -m unittest reference.tests.test_runtime_baseline_succession reference.tests.test_benchmark_integration_contract` — the new cases and the amended equivalence test
- `python -m unittest discover -s reference/tests -t reference` — the full suite, 0 failures (the known local-only `test_proposition_evaluator` ancestry skip on a shallow clone aside)
- `qor-logic governance-health --profile skill-entry` — index edits keep the governance surfaces healthy
