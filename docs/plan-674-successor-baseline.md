# Plan: #674 P0 — a successor-baseline procedure for Runtime Baseline v1

**change_class**: governance
**doc_tier**: standard
**risk_grade**: L2
**research_artifact**: docs/research-brief-north-star-six-tranches-2026-10-06.md (ledger Entry #60; research gate `2026-10-06T1200-668ns/research.json`, gitignored)
**roadmap**: `.qor/roadmaps/north-star-best-in-class` scope `scope-p0-baseline-procedure-plan` (handoff recorded); the merged outcome resolves `prereq-successor-baseline`, which gates every runtime tranche scope (#669, #670, #671, #673)
**iteration**: 1

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
- limitations: a baseline is published only after the runtime change it names has merged, against that merge commit, exactly as v1 was published against `f2aef57` after PR #646; between that merge and the publication the repository is in a declared transition, and the checker says so on every run. The procedure admits one declared successor at a time. A declared successor is honoured only when every identity it says changes has changed, every identity it does not name is byte-equal to the predecessor's, and `pyproject.toml` changes only when the declaration says so. Nothing here decides which identities a tranche may change; the tranche's own plan, audit and lane gates do.
- non_goals: changing runtime behaviour (the protected surface is untouched; `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` stays `PASS` on this plan's own commits); authoring Runtime Baseline v2 (that is the publication step of the first runtime tranche); the lane ids for the next lanes (`prereq-lane-v3-ids`); revising the v1 source boundary's protected or excluded sets; any relaxation of the diff (a successor is a new pinned identity, never an allowlist of paths that may drift); editing `reports/runtime/baseline-v1.json`, `baseline-v1.md` or `baseline-v1-source-boundary.json` (the register pins their git blobs and the validator refuses a change).
- exclusions: `reports/runtime/baseline-v1.json`, `baseline-v1-source-boundary.json`, `examples/gauntlet/agent-memory-runtime-baseline-v1.json` and `examples/gauntlet/agent_memory_runtime_baseline_stdio.py` are byte-unchanged; `scripts/import_amb_lane_evidence.py` and `scripts/import_longmemeval_lane_evidence.py` are not changed (they bind exact revisions already); `reference/agentmem_ref/**` and `pyproject.toml` are not touched; `.github/workflows/benchmark-integration-contract.yml` keeps its single checker call unchanged (a `TRANSITION` is acceptable there: its contract tests claim no revision).

## Open Questions

None blocking. Three defaults are taken and flagged for the owner; each is a one-line change if overruled:

1. **Transition exit code.** `TRANSITION` exits 0 by default and 1 under `--pinned-only`. The alternative (always 1) would make every runtime tranche PR red until publication, which is the state #674 exists to end. Workflows whose evidence claims an exact revision pass `--pinned-only` or skip their evidence steps (LD7).
2. **One declared successor at a time.** A second tranche that merges during a transition amends the open declaration's deltas (one more `identity_deltas` entry, same `baseline_id`) rather than declaring a third baseline. The register has one `declared_successor` slot by construction.
3. **Superseded manifests stay.** `examples/gauntlet/agent-memory-runtime-baseline-v1.json` remains in the tree after v2 is published (it is evidence of what v1 ran); only the current baseline's manifest is run by `runtime-baseline.yml`.

## Locked Decisions

**LD1 — The register is the only place that says which baseline is current.** New `reports/runtime/baseline-register.json`:

```json
{
  "schema_version": 1,
  "register_id": "agent-memory-runtime-baseline-register",
  "baselines": [
    {
      "baseline_id": "agent-memory-runtime-baseline-v1",
      "status": "current",
      "record": "reports/runtime/baseline-v1.json",
      "record_blob": "c8acfa1d94856bb88c7b77f498d74a81913c10ca",
      "source_boundary": "reports/runtime/baseline-v1-source-boundary.json",
      "source_boundary_blob": "f0ffc998033939288c816698111983fa371c4e90",
      "frozen_revision": "f2aef57293b516e065cad5d0afea26ac7e3c28a9",
      "public_gauntlet_manifest": "examples/gauntlet/agent-memory-runtime-baseline-v1.json",
      "superseded_by": null
    }
  ],
  "declared_successor": null
}
```

Rules, enforced by `scripts/validate_runtime_baseline_source.py` (LD5): `baselines` is non-empty and ordered by publication; exactly one entry has `status: "current"` and it is the last; every other entry has `status: "superseded"` and `superseded_by` equal to the next entry's `baseline_id`; `record_blob` and `source_boundary_blob` equal `git hash-object` of the named files at the candidate (immutability of a published record is a checkable fact, not a comment); `frozen_revision` equals the record's `runtime_revision.commit` and the boundary's `frozen_revision`; `declared_successor` is `null` or `{"baseline_id": ..., "declaration": "<path>"}`. The two blob values above are `git hash-object` of the v1 files at `main` today and are asserted by `test_runtime_baseline_succession.test_register_pins_v1_bytes`.
Grep-evidence for `scripts/check_runtime_baseline_equivalence.py:18`:
`git show origin/main:scripts/check_runtime_baseline_equivalence.py | grep -nE '^DEFAULT_BOUNDARY' -> 18:DEFAULT_BOUNDARY = ROOT / "reports" / "runtime" / "baseline-v1-source-boundary.json"`

**LD2 — A runtime change declares its successor before it merges; the declaration is a value the checker verifies, not a permission.** New `schemas/runtime-baseline-declaration.schema.json` (`additionalProperties: false`), instance path `reports/runtime/baseline-v<N>-declaration.json`:

```json
{
  "schema_version": 1,
  "declaration_id": "agent-memory-runtime-baseline-v2-declaration",
  "baseline_id": "agent-memory-runtime-baseline-v2",
  "predecessor_baseline_id": "agent-memory-runtime-baseline-v1",
  "issue": 673,
  "status": "declared",
  "identity_deltas": [
    {
      "identity_path": "identity.ranking.active_policy_version",
      "from": "3.1.2",
      "to": "3.2.0"
    }
  ],
  "pyproject_change": null,
  "acceptance_evidence_required": [
    {"kind": "public_gauntlet", "ref": "gauntlet-orchestration-retrieval-probe-v1"},
    {"kind": "replay", "ref": "temporal_currentness_580_584"},
    {"kind": "lane", "ref": "longmemeval-s-retrieval-parity-v2"}
  ]
}
```

`identity_path` is a dotted path into the baseline record and must name an entry of the identity table (LD4); `from` must equal the predecessor record's value at that path; `pyproject_change` is `null` or `{"reason": "<non-empty>"}`; `acceptance_evidence_required` is non-empty and each `kind` is one of `public_gauntlet`, `replay`, `lane`; `status` is the constant `declared` (a declaration never records publication: publication retires it from the register). The example above is the schema's own `examples` entry and is not committed as an instance by this plan.

**LD3 — The checker has three outcomes and names the one it reached.** `scripts/check_runtime_baseline_equivalence.py` reads the register (`--register`, default `reports/runtime/baseline-register.json`; `--boundary` is removed) and resolves the current baseline's boundary. With `diff = git diff --exit-code <frozen> <candidate> -- <protected> <exclusions>` exactly as today:

- no diff → `PASS`, exit 0, stdout `Runtime Baseline equivalence: PASS; baseline=<id>; frozen=<rev>; candidate=<ref>; explicit non-runtime exclusions=<paths>`;
- diff and `declared_successor` is `null` → exit 1, `candidate <ref> changes the protected Runtime Baseline source surface relative to <rev> and the register declares no successor`;
- diff and a declared successor → the declaration is loaded and schema-validated; `predecessor_baseline_id` must equal the current `baseline_id`; for every delta, `read_identities(frozen)[path] == from` and `read_identities(candidate)[path] == to`; for every identity-table path not named by a delta, `read_identities(frozen)[path] == read_identities(candidate)[path]`; `git diff --quiet <frozen> <candidate> -- pyproject.toml` must be clean unless `pyproject_change` is set. All hold → `TRANSITION`, exit 0, stdout `Runtime Baseline equivalence: TRANSITION; baseline=<id>; declared_successor=<id> (issue #<n>); deltas=<path> <from>-><to>[, ...]; undeclared identities unchanged; candidate=<ref>`; with `--pinned-only` → exit 1, `candidate <ref> is in a declared transition to <id>; this check requires a pinned baseline`. Any check failing → exit 1 with one of: `declared successor <id> names predecessor <x> but the current baseline is <y>`; `declared delta <path>: predecessor value is <a>, declaration says from=<b>`; `declared delta <path>: candidate value is <a>, declaration says to=<b>`; `undeclared identity <path> changed: frozen=<a>, candidate=<b>`; `pyproject.toml changed without a declared pyproject_change`.

`check(root, register_path, candidate, *, pinned_only, identity_sources=IDENTITY_SOURCES) -> Outcome` where `Outcome` is a frozen dataclass `(state: str, baseline_id: str, frozen_revision: str, message: str)`; `main` prints `message` and maps the state to the exit code. `ROOT` stops being a module constant read by the functions: every function takes `root`, so the tests run the same code against a temporary repository (LD6). The three state strings are the public contract of the script; workflows grep them (LD7).
Grep-evidence for `scripts/check_runtime_baseline_equivalence.py:76`:
`git show origin/main:scripts/check_runtime_baseline_equivalence.py | grep -nE '^def check\(' -> 76:def check(boundary_path: Path, candidate: str) -> int:`

**LD4 — One identity table, read from any revision.** New `scripts/runtime_baseline_identity.py` holds the table `validate_runtime_baseline_source.py` currently spells out as thirty `expect(...)` calls, as data:

```python
@dataclass(frozen=True)
class IdentitySource:
    identity_path: str      # dotted path into the baseline record
    file: str               # path inside the protected surface
    kind: str               # "constant" | "numeric" | "json"
    key: str                # constant name, or dotted key for kind "json"

IDENTITY_SOURCES: tuple[IdentitySource, ...] = (
    IdentitySource("identity.public_contract_version", "reference/agentmem_ref/api/contract.py", "constant", "CONTRACT_VERSION"),
    IdentitySource("identity.runtime_id", "reference/agentmem_ref/_profiles/rc1-local.json", "json", "runtime.runtime_id"),
    ...  # one row per expect() in validate_runtime_baseline_source.py today, including the four candidate-route constants as read_semantics.candidate_routes.0 .. .3
)

def read_identities(root: Path, revision: str, sources=IDENTITY_SOURCES) -> dict[str, object]
def record_value(record: dict, identity_path: str) -> object   # dotted path with integer segments
```

`git_show`, `constant`, `numeric_constant` and `git_blob_sha` move here unchanged. `validate_runtime_baseline_source.py` keeps its record-level checks (`production_1_0`, dogfood, public Gauntlet qualification) and replaces its thirty `expect` calls with one loop over `IDENTITY_SOURCES` comparing `read_identities(root, commit)` with `record_value(record, path)`. The checker (LD3) and the validator (LD5) share this module; the table is the single statement of what "identity" means for a baseline.
Grep-evidence for `scripts/validate_runtime_baseline_source.py:91`:
`git show origin/main:scripts/validate_runtime_baseline_source.py | grep -nE '^def main' -> 91:def main() -> int:`

**LD5 — The validator validates the register, every record in it, and the open declaration.** `scripts/validate_runtime_baseline_source.py` `main` loads the register and, for each entry: readable record and boundary; the three revisions agree (LD1); blobs match (`git hash-object` via `git_blob_sha` of the file content at the candidate tree); `boundary.baseline_id == record.baseline_id`; `boundary.baseline_mutation is False`; identities at `frozen_revision` equal the record (LD4); the record-level checks that today are v1-specific run on every record (they read fields every record carries; the `#637` dogfood check reads `dogfood.required_before_issue_638_close` only when `baseline_id` is v1, since that key is a v1 fact, and otherwise requires `dogfood.status == "completed"` and the two authority fields). Ordering and status rules (LD1). When `declared_successor` is set: the declaration file validates against the schema, `predecessor_baseline_id` is the current `baseline_id`, `baseline_id` is not already in `baselines`, and each `from` equals `record_value(current_record, path)`. `scripts/render_runtime_baseline.py` takes `--baseline <id>` (default: every register entry) and renders `<record>.md` beside each record; `--check` compares every rendered file. The v1 rendering is byte-identical to today's `baseline-v1.md` (the test asserts it).

**LD6 — The procedure is tested on a throwaway repository, not on this one.** New `reference/tests/test_runtime_baseline_succession.py` builds a temporary git repository in `setUp` (`git init`, `user.email`/`user.name` set locally) with a two-row identity table passed explicitly (`identity.public_contract_version` from `reference/agentmem_ref/api/contract.py` constant `CONTRACT_VERSION`; `identity.ranking.active_policy_version` from `reference/agentmem_ref/runtime/temporal_order_constraints.py` constant `POLICY_VERSION`), a `pyproject.toml`, an `evaluation/` subtree, a record, a boundary, and a register pinning their blobs; commits the frozen revision; then builds candidates by committing changes. It imports the scripts as modules from `scripts/` (sys.path insert of `REPO_ROOT / "scripts"`, the pattern `test_benchmark_integration_contract.py` already uses for `reference`). Cases:

- `test_pass_when_only_evaluation_changes` → `PASS`;
- `test_fail_without_declaration` → exit 1, message names the frozen revision and "declares no successor";
- `test_transition_with_honest_declaration` → `POLICY_VERSION` 3.1.2→3.2.0 declared and changed → `TRANSITION`, message lists the delta and "undeclared identities unchanged";
- `test_pinned_only_refuses_transition` → exit 1 with the pinned message;
- `test_fail_when_declared_to_is_not_in_candidate`, `test_fail_when_declared_from_is_not_in_frozen`, `test_fail_when_undeclared_identity_changes` (contract constant changed with only the ranking delta declared), `test_fail_when_pyproject_changes_undeclared`, `test_transition_with_declared_pyproject_change`;
- `test_fail_when_predecessor_is_not_current`;
- register validator: `test_register_refuses_two_current`, `test_register_refuses_record_blob_drift` (edit the record bytes after pinning), `test_register_refuses_superseded_without_successor_link`, `test_register_requires_current_last`;
- `test_register_pins_v1_bytes` on the real repository: the register's two v1 blobs equal `git hash-object` of the two v1 files at `HEAD`, skipped (like the existing equivalence test) when `f2aef57` is not in the checkout.

`test_benchmark_integration_contract.test_evaluation_only_change_keeps_runtime_baseline_equivalence` reads the boundary path from the register's current entry instead of the literal path; its `PASS` assertion is unchanged.
Grep-evidence for `reference/tests/test_benchmark_integration_contract.py:363`:
`git show origin/main:reference/tests/test_benchmark_integration_contract.py | grep -nE 'def test_evaluation_only_change_keeps_runtime_baseline_equivalence' -> 363:    def test_evaluation_only_change_keeps_runtime_baseline_equivalence(self):`

**LD7 — Workflows that claim an exact revision classify first and skip, never lie.** `.github/workflows/runtime-baseline.yml`: path triggers gain `reports/runtime/baseline-register.json`, `reports/runtime/baseline-*-declaration.json`, `schemas/runtime-baseline-declaration.schema.json`, `scripts/runtime_baseline_identity.py`, `reference/tests/test_runtime_baseline_succession.py`; a step `classify` runs the checker, tees its stdout, and writes `state=<PASS|TRANSITION>` to `GITHUB_OUTPUT` (`grep -oE 'equivalence: [A-Z]+'`); the "Verify exact public contestant identity", "Validate public contestant manifest", "Run Runtime Baseline ... through public Gauntlet path", "Validate public-path qualification evidence", inventory and upload steps carry `if: steps.classify.outputs.state == 'PASS'`, read the record, boundary and manifest paths from the register's current entry (one inline `python - <<'PY'` that prints `record=`, `boundary=`, `manifest=`, `revision=` to `GITHUB_OUTPUT`) and assert against those values instead of the literal `f2aef57…` and `agent-memory-runtime-baseline-v1` strings; a step `Transition notice` with `if: steps.classify.outputs.state == 'TRANSITION'` prints the checker line and exits 0. `.github/workflows/agmi-agent-memory-qualification.yml`: the same `classify` step; the agmi reproduction steps carry the `PASS` condition and the boundary path they echo comes from the register; a transition notice step. `.github/workflows/benchmark-integration-contract.yml`: unchanged (exclusions). Every other workflow that greps `PASS` today: none (verified by `grep -rn "check_runtime_baseline_equivalence" .github/workflows` → the three above).

**LD8 — The procedure is written down once, where contributors look.** New `docs/67-runtime-baseline-succession.md`: the four terms; the two-step procedure (Step A, the tranche PR: declaration file + register `declared_successor`; checker prints `TRANSITION`; lane and replay evidence for the new runtime binds the exact commits it ran at; Step B, the publication PR, no runtime change: `baseline-v<N>.json` with a `predecessor` block `{baseline_id, declaration_id, identity_deltas}`, `runtime_revision.commit` = Step A's merge commit, `qualification_evidence` satisfying every `acceptance_evidence_required` item, `baseline-v<N>-source-boundary.json` with that `frozen_revision`, `baseline-v<N>.md` rendered, `examples/gauntlet/agent-memory-runtime-baseline-v<N>.json`, register: new entry `current` with both blobs, predecessor `superseded` with `superseded_by`, `declared_successor: null`; checker prints `PASS` again); what each checker line means and which workflows skip on `TRANSITION`; the invariants (published records are blob-pinned; the diff is never relaxed; one declared successor at a time; a declaration is a claim the checker verifies in both directions). `docs/CONTRIBUTOR_ARCHITECTURE.md` §8 retitled "Runtime Baseline source equivalence and succession": the first paragraph names the register as the source of the current baseline, the three outcomes, and links docs/67. `docs/GOVERNANCE_INDEX.md` Tier 4: this plan `ACTIVE`, the research brief `supporting research`; Tier 2 or 5 row for docs/67. `reports/runtime/baseline-v1.json` is not edited (its `drift_policy` already says `observable_behavior_changes_must_bind_new_revision`; docs/67 is where that sentence becomes a procedure).

## Phase 1: register, shared identity table, register-aware validator

### Affected Files

- `reports/runtime/baseline-register.json` - new, LD1
- `scripts/runtime_baseline_identity.py` - new, LD4
- `scripts/validate_runtime_baseline_source.py` - register loop, identity table, declaration checks, LD5
- `scripts/render_runtime_baseline.py` - `--baseline`, register default, LD5
- `reference/tests/test_runtime_baseline_succession.py` - new: register validator cases and `test_register_pins_v1_bytes`, LD6

### Changes

Write the register with the two blob values from `git hash-object` at `main`. Move `git_show`, `constant`, `numeric_constant`, `git_blob_sha` into the new module; add `IdentitySource`, `IDENTITY_SOURCES` (one row per current `expect`, the four route constants as `read_semantics.candidate_routes.0` .. `.3`), `read_identities`, `record_value`. Rewrite `validate_runtime_baseline_source.main` as `validate_register(root, register_path) -> None` plus `main`; keep every record-level check, generalised per LD5. `render_runtime_baseline.render(data)` unchanged; `main` iterates the register.

### Unit Tests

- `reference/tests/test_runtime_baseline_succession.py` - the four register-validator cases and the v1 blob pin; `read_identities` on the temporary repository returns the two declared values at the frozen revision; `record_value` resolves an integer segment (`read_semantics.candidate_routes.3`).
- `python scripts/validate_runtime_baseline_source.py` and `python scripts/render_runtime_baseline.py --check` exit 0 on the real repository with v1 unchanged.

## Phase 2: declaration schema and the three-outcome checker

### Affected Files

- `schemas/runtime-baseline-declaration.schema.json` - new, LD2
- `scripts/check_runtime_baseline_equivalence.py` - register, declaration, `Outcome`, `--pinned-only`, root-parametrised functions, LD3
- `reference/tests/test_runtime_baseline_succession.py` - the ten checker cases, LD6
- `reference/tests/test_benchmark_integration_contract.py` - read the boundary path from the register, LD6

### Changes

Schema per LD2 with the v2 example under `examples`. Checker per LD3: `load_register(root, path)`, `current_entry(register)`, `load_declaration(root, entry) -> dict` (jsonschema validation with the repository's installed `jsonschema`, the same dependency `validate-lane` uses), `verify_declaration(root, frozen, candidate, record, declaration, sources) -> list[str]` returning the failing messages in LD3's order, `check(...) -> Outcome`, `main`. `_load_boundary` keeps its structural refusals verbatim.

### Unit Tests

- `reference/tests/test_runtime_baseline_succession.py` - `PASS`, undeclared `FAIL`, honest `TRANSITION`, `--pinned-only`, the five dishonest-declaration failures, the declared `pyproject` case, the wrong-predecessor case; each asserts the exact message prefix from LD3.
- `reference/tests/test_benchmark_integration_contract.py` - unchanged `PASS` assertion through the register.

## Phase 3: workflows and documentation

### Affected Files

- `.github/workflows/runtime-baseline.yml` - classify, register-derived identities, `PASS`-conditioned evidence steps, transition notice, LD7
- `.github/workflows/agmi-agent-memory-qualification.yml` - classify, `PASS`-conditioned reproduction, LD7
- `docs/67-runtime-baseline-succession.md` - new, LD8
- `docs/CONTRIBUTOR_ARCHITECTURE.md` - §8, LD8
- `docs/GOVERNANCE_INDEX.md` - Tier 4 and the docs/67 row, LD8

### Changes

Per LD7 and LD8. The inline Python in `runtime-baseline.yml` that asserts manifest, boundary and baseline agreement reads the register's current entry and asserts the same relationships against it; no literal revision or baseline id remains in the workflow.

### Unit Tests

- `reference/tests/test_runtime_baseline_succession.py` - `test_workflows_carry_no_literal_v1_revision`: neither workflow file contains `f2aef57293b516e065cad5d0afea26ac7e3c28a9` or `agent-memory-runtime-baseline-v1` outside a path trigger, and both contain `--candidate HEAD` once in a step whose id is `classify`.
- `test_governance_health` is not touched; `qor-logic governance-health --profile skill-entry` stays green after the index edits.

## Definition of Done

### Deliverable: the register names the current baseline and pins its bytes

- **D1**: `reports/runtime/baseline-register.json` with v1 `current`, both blobs pinned; the validator refuses blob drift, two currents, a superseded entry without its link, and a current entry that is not last.

### Deliverable: a declared successor is verified in both directions

- **D2**: the checker prints exactly one of `PASS`, `TRANSITION`, or a failure message from LD3; a transition is honoured only when every declared delta holds at both ends and nothing undeclared moved; `--pinned-only` refuses a transition.

### Deliverable: workflows and documentation tell the truth during a transition

- **D3**: `runtime-baseline.yml` and the agmi workflow skip their revision-claiming steps on `TRANSITION` and print why; docs/67 states the two-step procedure; CONTRIBUTOR_ARCHITECTURE §8 and GOVERNANCE_INDEX point to it.

## Feature Inventory Touches

| entry_id | operation | test_path | test_descriptor |
|---|---|---|---|
| n/a (governance tooling under `scripts/`, `reports/runtime/`, `.github/workflows/`, `docs/`; no `reference/agentmem_ref` feature is touched) | n/a-justified | `reference/tests/test_runtime_baseline_succession.py` | the three checker outcomes, the dishonest-declaration refusals, the register invariants and the v1 blob pin |

## CI Commands

- `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` — prints `PASS` for this plan's own commits (no protected path changes)
- `python scripts/validate_runtime_baseline_source.py` — register, v1 record, blobs and identities at `f2aef57` agree
- `python scripts/render_runtime_baseline.py --check` — `baseline-v1.md` is byte-identical to the rendering
- `python -m unittest reference.tests.test_runtime_baseline_succession reference.tests.test_benchmark_integration_contract` — the new cases and the existing equivalence test
- `python -m unittest discover -s reference/tests -t reference` — the full suite, 0 failures (the known local-only `test_proposition_evaluator` ancestry skip on a shallow clone aside)
- `qor-logic governance-health --profile skill-entry` — index edits keep the governance surfaces healthy
