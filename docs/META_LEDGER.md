# Qor-logic Meta Ledger

## Chain Status: ACTIVE
## Genesis: 2026-09-01T20:47:00-04:00

---

### Entry #1: GENESIS

**Timestamp**: 2026-09-01T20:47:00-04:00
**Phase**: BOOTSTRAP
**Author**: Governor
**Risk Grade**: L3

**Content Hash**:
SHA256(CONCEPT.md + ARCHITECTURE_PLAN.md) = 41e5730727c4b2ebb79d6fd538f41d914d87876bed072b2108d8c31ea2ed3df9

**Previous Hash**: GENESIS (no predecessor)

**Decision**: Project DNA initialized for an existing mature repository (359+ merged PRs, 42 doctrine docs, 36 ADRs, 58 schemas, reference runtime). Lifecycle: ALIGN/ENCODE complete. Forward objective bound to the committed roadmap `.qor/roadmaps/agent-memory-1_0-completion`. Repository is public; Qor DNA is committed under `docs/` by owner decision, with `.agent/` and `.qor/gates/` session state gitignored.

**Branch**: `feat/agent-memory-genesis` from `main` @ 8b676f4

---

### Entry #2: RESEARCH BRIEF

**Timestamp**: 2026-09-01T22:05:00-04:00
**Phase**: RESEARCH
**Author**: Analyst
**Risk Grade**: L2 (Sprint 1 touches packaging, test guards, CI, docs; no authority-path code)
**Session**: 2026-09-02T0158-2a109f

**Content Hash**:
```
SHA256(docs/research-brief-sprint1-install-correctness-2026-09-01.md)
= 4386c8f06896a6f6770d398b1bc334dceaaf0d769f60fe6b161beecd706923bd
```

**Previous Hash**: `41e5730727c4b2ebb79d6fd538f41d914d87876bed072b2108d8c31ea2ed3df9`
**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 8f260d40b14b5e7ddc3cd94deae7c31a831525f05088ff9373f237adef1655fc
```

**Decision**: Loop 1 (ADR-035 program) research complete for Sprint 1 install correctness. All eight target interfaces verified against source; build-time schema-copy packaging mechanism prototyped and proven. Drifts: ARCHITECTURE_PLAN Dependencies table understates runtime deps (cryptography, rfc8785 required by 17 modules); installed package has no acceptance gate; RESEARCH_BRIEF GAP-DOC-13 downgraded to LOW (commands already disclaimed at CONFIGURATION.md:326). Owner decisions locked: host authenticates recall principals; CONCEPT.md unchanged; README badge reworded. Next: /qor-plan.

---

### Entry #3: GATE TRIBUNAL

**Timestamp**: 2026-09-01T22:40:00-04:00
**Phase**: GATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: VETO
**Session**: 2026-09-02T0158-2a109f
**Target**: docs/plan-sprint1-install-correctness.md (plan content hash 65cf128b9e97ea4f2b410f252f146cdcac4c588d953ca7c9974a37420f3f0d16)

**Content Hash**:
SHA256(.agent/staging/AUDIT_REPORT.md) = 76f88222b94aa8709330b4f995ecb940c49081c2fe472ea192a1831671c0d603

**Previous Hash**: `8f260d40b14b5e7ddc3cd94deae7c31a831525f05088ff9373f237adef1655fc`
**Chain Hash**:
SHA256(content_hash + previous_hash) = da74f30e6d06f404701cc25bcf81c27ec3681a6196e5fdb563ed5e1ccf77fe19

**Decision**: VETO, attempt 1 of 5 for this scope. Grounds (all plan-text): V1 fail-open wheel-install smoke under bash -e; V2 LD7 false premise (cli-doctor.yml:26 and provider-discovery.yml:26 already pip install . from repo root); V3 two FX002 tests target unreachable branches; V4-V6 specification drift; V7 build_py zero-copy fail-open. Security, OWASP, Razor, Dependency, Macro, Orphan, Filter-stage passes clean. Option B independent review was mandatory (author-momentum flag) and surfaced the correct fail-open direction. Required next action: Governor amends plan text, re-runs /qor-audit.

---

### Entry #4: GATE TRIBUNAL

**Timestamp**: 2026-09-01T23:15:00-04:00
**Phase**: GATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: VETO
**Session**: 2026-09-02T0158-2a109f
**Target**: docs/plan-sprint1-install-correctness.md iteration 2 (plan content hash 2a1a31bb66bf4e6cfe0351d02f4dceea3be27f9fbf48987e4abfd8651f96a2c1)

**Content Hash**:
SHA256(.agent/staging/AUDIT_REPORT.md) = 2b4d21baee7ba2dec05dd3dc965414a49e4983bf5c8243983d95f8f930e98a9c

**Previous Hash**: `da74f30e6d06f404701cc25bcf81c27ec3681a6196e5fdb563ed5e1ccf77fe19`
**Chain Hash**:
SHA256(content_hash + previous_hash) = 87e3f3e9d58aa12122bf485b4bee31cd2c8dd1ae607fd47af4a8402b5a295cfd

**Decision**: VETO, attempt 2 of 5. Iteration-1 grounds V1-V7 confirmed closed (smoke fail-closed traced; seams reachable; sdist-to-wheel schema carriage and zero-copy build failure reproduced). Residual grounds, all plan-text: V1 LD7 masking mechanism false (installed receipts never resolves source schemas; masking is source-tree imports in the validate job plus a CLI that never imports receipts); V2 stale-Proposed rewrite rule unexecutable (no dates on ADR-020/022/035) and omits ADR-022; V3 two further stale sites uncorrected while D1 claims GAP-DOC-09 corrected; V4 test_pin_support.py missing from Affected Files. Option B independent review mandatory and performed with shell access. Required next action: Governor amends plan text, re-runs /qor-audit (attempt 3).

---

### Entry #5: GATE TRIBUNAL

**Timestamp**: 2026-09-01T23:45:00-04:00
**Phase**: GATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: VETO
**Session**: 2026-09-02T0158-2a109f
**Target**: docs/plan-sprint1-install-correctness.md iteration 3 (plan content hash 572ff17857af39c31727def0fab1c9269f44906b323b2087e63939390406e0d6)

**Content Hash**:
SHA256(.agent/staging/AUDIT_REPORT.md) = 8308871d46156bb9f0c31db228292d9fc31eb7e1795130952c0340b82f04ac0b

**Previous Hash**: `87e3f3e9d58aa12122bf485b4bee31cd2c8dd1ae607fd47af4a8402b5a295cfd`
**Chain Hash**:
SHA256(content_hash + previous_hash) = 98a284dd5557ceed2ec4feb7ae7bcf87a5aee212a59f06ba200f9b62c2927296

**Decision**: VETO, attempt 3 of 5, second consecutive with signature (infrastructure-mismatch, specification-drift, coverage-gap). Iteration-2 V2/V4 closed. Residual plan-text grounds: V1 LD7 clause "console command never imports receipts" refuted by agentmem_ref/__init__.py:9 (true masking: _validator is lazy); V2 wiki replacement points at absent content; V3 six same-class stale sites neither corrected nor deferred. All code, test, security, dependency, build-path passes clean. Required next action: Governor amends plan text, re-runs /qor-audit (attempt 4); a third same-signature VETO routes to /qor-remediate.

---

### Entry #6: GATE TRIBUNAL

**Timestamp**: 2026-09-02T00:20:00-04:00
**Phase**: GATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-02T0158-2a109f
**Target**: docs/plan-sprint1-install-correctness.md iteration 4 (plan content hash f3a1d786f9821d60d957209b3a438aab2196814a8f06805f78ceb857da55165e)

**Content Hash**:
SHA256(.agent/staging/AUDIT_REPORT.md) = 1f98e20824f925488ca135366cf571a51ddf551a41c2e92c9feef7151a58f66c

**Previous Hash**: `98a284dd5557ceed2ec4feb7ae7bcf87a5aee212a59f06ba200f9b62c2927296`
**Chain Hash**:
SHA256(content_hash + previous_hash) = b14d48b4e945441298ba3ddea3811834262f84b85eb20cd0f99ce3cb4de9a4f9

**Decision**: PASS, attempt 4 of 5. All iteration-3 grounds closed with text true at HEAD; LD7 behavioral clause proven (zero _validator calls during installed --help); nine-site table verbatim; six same-class sites deferred by file:line to Sprint 9; LD1-LD9 9/9 exact. Option B independent review reported 0 violations. Gate OPEN. Next: /qor-implement. Hashes recomputed once after adding the canonical `**Verdict**: PASS` line required by intent_lock's parser (format fix, verdict unchanged, no downstream entry existed).

---

### Entry #7: IMPLEMENTATION

**Timestamp**: 2026-09-02T01:05:00-04:00
**Phase**: IMPLEMENT
**Author**: Specialist
**Risk Grade**: L3
**Session**: 2026-09-02T0158-2a109f
**Plan**: docs/plan-sprint1-install-correctness.md iteration 4 (audit PASS, Entry #6)

**Files** (26): setup.py, MANIFEST.in, pyproject.toml, .gitattributes, .gitignore, .github/dependabot.yml, .github/workflows/cli-doctor.yml, reference/agentmem_ref/receipts.py, reference/agentmem_ref/cedar_policy_comparator.py, reference/tests/pin_support.py, reference/tests/test_pin_support.py, reference/tests/test_receipts_schema_location.py, reference/tests/test_cedar_policy_comparator.py, reference/tests/test_agent_manifest_correlation.py, reference/tests/test_trace_action_evidence.py, README.md, docs/CONFIGURATION.md, docs/ARCHITECTURE_PLAN.md, docs/FEATURE_INDEX.md, docs/future/multi-agent-shared-memory-protocol.md, docs/profiles/policy-projection-compatibility-profile.md, docs/profiles/temporal-commitment-evidence-profile.md, docs/programs/runtime-evidence/cognitive-mesh.md, docs/programs/runtime-evidence/evolveai-cognitive-mesh.md, wiki-src/Runtime-Evidence.md, wiki-src/Canonical-and-Derived-State.md

**Content Hash**:
SHA256(concatenated path + bytes of the files above) = e5088de0741e9bed1541dcf0c9373db4f10d120ee0f2a6f28899af013a7b9ba4

**Previous Hash**: `b14d48b4e945441298ba3ddea3811834262f84b85eb20cd0f99ce3cb4de9a4f9`
**Chain Hash**:
SHA256(content_hash + previous_hash) = 8bd16fbc3ebaf384423d147a09de765568173856080f397f90a0e84ff2bd52d1

**Decision**: Sprint 1 implemented red-to-green. Tests: 868 run, 0 failures, 9 skipped (7 Graphiti unavailable, 2 pin-identity tests skip by design). validate_schemas, validate_fixtures, markdown and wiki link validators clean. Build: sdist + wheel; wheel carries 58 schemas under agentmem_ref/_schemas; fresh-venv smoke from outside the checkout exits 0 with the schema resolved, portable_evidence imports, agent-memory --help exits 0. FEATURE_INDEX rows FX001-FX003 verified. Deferred by plan: six same-class stale doc sites to Sprint 9. Review Boundary: nothing committed or pushed.

---

### Entry #8: SESSION SEAL - Phase 1 (Sprint 1 install correctness)

**Entry ID**: `88d5be71778f`
**Content Hash**: `f3a1d786f9821d60d957209b3a438aab2196814a8f06805f78ceb857da55165e`
**Previous Hash**: `8bd16fbc3ebaf384423d147a09de765568173856080f397f90a0e84ff2bd52d1`
**Chain Hash**: `810f42dbb31bffeaf366fb40c658a61a2d514b130ed643034af953eadb92eb94`
**Timestamp**: 2026-09-02T01:40:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-02T0158-2a109f
**Plan**: docs/plan-sprint1-install-correctness.md (iteration 4; change_class feature)
**Version**: 0.1.0 -> 0.2.0 (pyproject.toml, python backend; no tag created: Review Boundary)
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 9fe57b089fe081c9c81c9c6889fc3b5407fc68fb):
564fb97a2d25e26197ccff2ee9893ac058bfcb243032963c8c8a9ea61172d213

**Content Hash**:
SHA256(docs/plan-sprint1-install-correctness.md) = f3a1d786f9821d60d957209b3a438aab2196814a8f06805f78ceb857da55165e

**Previous Hash**: `8bd16fbc3ebaf384423d147a09de765568173856080f397f90a0e84ff2bd52d1`
**Chain Hash**:
SHA256(content_hash + previous_hash) = 810f42dbb31bffeaf366fb40c658a61a2d514b130ed643034af953eadb92eb94

**Reality = Promise**: all 26 planned files exist and match; no MISSING; UNPLANNED: none beyond governance scaffold docs already registered.

**Gate ladder**:
| Gate | Result |
|---|---|
| 0 prior artifact (implement.json) | PASS |
| 2.5 version | 0 tags; 0.1.0 -> 0.2.0 |
| 3 reality audit | PASS |
| 3.5 blockers | none open |
| 4 tests | 868 run, 0 fail, 9 skipped |
| 4.6 intent_lock verify / skill_admission / gate_skill_matrix / session_id_lint | PASS / ADMITTED / 34 skills 164 handoffs 0 broken / PASS |
| 4.6.5 secret_scanner --staged | PASS (0 findings) |
| 4.6.6 procedural_fidelity | PASS |
| 4.6.7 dod_check | PASS |
| 4.6.8 merge_velocity | healthy (0 merges in window) |
| 4.6.9 skill_size_budget | SKIP (no qor/skills corpus; event emitted) |
| 4.6.10 data_api_acl | SKIP (no SQL migrations; event emitted) |
| 4.6.11 instruction_hygiene --staged | PASS |
| 4.7 doc_integrity strict | SKIP (glossary path is Qor-logic layout; repo glossary at docs/00-glossary.md; event emitted) |
| 4.7.5 governance-index enforce | PASS after registering 43 numbered docs, canonical architecture doc, process genome, plan, research brief |
| 6 feature_index_verify | see command output above; FX001-FX003 verified |
| 6.5 doc currency | no warnings |
| 6.5 seal_artifacts --check | SKIP (Qor-logic layout; event emitted) |
| 6.8 hash integrity | 4/4 validated |
| 7.6 changelog stamp | SKIP (CHANGELOG.md absent, GAP-REL-01; event emitted) |

**Feature Inventory**: Total: 3 / verified: 3 / unverified: 0 / n/a: 0
**Newly unverified**: none

**Decision**: Sprint 1 install correctness sealed. Installable wheel now resolves canonical schemas (58 packaged), declares its runtime deps, ships an sdist, has a fail-closed CI acceptance job, deterministic Cedar digest, environment-tolerant pin tests, dependabot, corrected README badge, and nine stale-status doc fixes (six deferred to Sprint 9, recorded in RESEARCH_BRIEF). Review Boundary honored: staged, not committed. Next: /qor-enterprise-handoff.

---
*Chain integrity: VALID*
*Next required action: /qor-enterprise-handoff (Review Boundary packet); then Loop 2 /qor-research for Sprint 2*

### Entry #9: MIGRATION ATTESTATION

**Timestamp**: 2026-09-04T15:41:00-04:00
**Phase**: IMPLEMENT
**Author**: Specialist
**Risk Grade**: L2
**Session**: 2026-09-04T1541-bbb157
**Plan**: docs/plan-ledger-markup-repair.md

**Attested Entries**:
#1=38bcc1339da0

**Content Hash**: `d06167be57ffcc0c58f3368dd6e81233ac71f4e51f0a4147150413efbf5709c3`
**Previous Hash**: `810f42dbb31bffeaf366fb40c658a61a2d514b130ed643034af953eadb92eb94`
**Chain Hash**: `a8f9bd52c21a43b47e31a301d048dd6bb70d67f0ecd9ba7def2d35f20bc37a8f`

**Content Hash definition**: this entry commits no file. Its content hash is the
SHA-256 of its `**Attested Entries**` block exactly as written above -- the single
line `#1=38bcc1339da0`, UTF-8, no trailing newline -- because that block is the
payload this entry asserts. Chain hash is `SHA256(content + "|" + previous)`, the
Phase 23 separator form used throughout this ledger.

**Decision**: Entry #1 (GENESIS) predates the chain-hash convention: it carries a
content hash and `**Previous Hash**: GENESIS (no predecessor)`, and no chain hash,
because none was computed at genesis. It therefore cannot verify by chain
arithmetic and must not be made to: retrofitting a zeros previous-hash and a
computed chain hash would write a value into sealed history that never existed.
This attestation digest-binds Entry #1's body instead, per Phase 193 (GH #278), so
a later edit to genesis becomes a hard failure rather than a silent skip.

---

### Entry #10: AMENDMENT

**Timestamp**: 2026-09-04T15:41:00-04:00
**Phase**: IMPLEMENT
**Author**: Specialist
**Risk Grade**: L2
**Session**: 2026-09-04T1541-bbb157

**Artifact**: `docs/research-brief-sprint1-install-correctness-2026-09-01.md`
**Content Hash**: `b899b5e660c630d3d44309586eff872f5f40e58375eb74fd5dcf7aba03be8c27`
**Superseded Content Hash**: `4386c8f06896a6f6770d398b1bc334dceaaf0d769f60fe6b161beecd706923bd`
**Previous Hash**: `a8f9bd52c21a43b47e31a301d048dd6bb70d67f0ecd9ba7def2d35f20bc37a8f`
**Chain Hash**: `7ec0a04e1a192b81ed6e0b37190aae4fcd9c17d11db248eb304fb9f906a73cc2`

**Decision**: Entry #2 committed `4386c8f06896a6f6...` for the Sprint 1 research
brief. During audit attempt 2 of that cycle the tribunal correctly identified a
false claim in the brief -- it asserted that no workflow ran `pip install .`, which
was wrong (`cli-doctor.yml:26` and `provider-discovery.yml:26` both do) -- and the
brief was corrected. The correction was right; the ledger's commitment to the
artifact was never updated, so Entry #2 has described a file that no longer exists
in that form since 2026-09-01. This amendment records the superseded hash, the
current hash `b899b5e660c630d3...`, and the reason. Chain integrity was never
affected: chain hashes commit to recorded hex, not to live bytes. Recorded as
V-2 by `/qor-validate` on 2026-09-02.

**Cycle provenance**: `docs/plan-ledger-markup-repair.md`. Recorded in prose rather
than as a `**Plan**:` field because `ledger_commitment._ARTIFACT_RE` matches
`Artifact|Plan|Brief` and takes the first hit in document order: a `**Plan**:` line
in a committing-kind entry binds that entry's content hash to the plan path,
producing a false commitment. Observed here -- with the field present this entry
registered `docs/plan-ledger-markup-repair.md -> b899b5e6...`, the research brief's
digest under the plan's path.
---

### Entry #11: SESSION SEAL - Phase 2 (ledger markup repair)

**Entry ID**: `8987a2b36f4a`
**Content Hash**: `cc53e92320e56c5bba635faaba1fba0094516ab73e37009bf19d914cb92dcf86`
**Previous Hash**: `7ec0a04e1a192b81ed6e0b37190aae4fcd9c17d11db248eb304fb9f906a73cc2`
**Chain Hash**: `e86cf1c9b0c196688a49c750f87342e440886da8dfdf0ac961440ac6c0fa3b0d`
**Timestamp**: 2026-09-04T15:41:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L2
**Verdict**: PASS
**Session**: 2026-09-04T1541-bbb157
**Plan**: docs/plan-ledger-markup-repair.md (iteration 2; change_class hotfix)
**SSDF Practices**: PO.1.4, PS.2.1

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 5147979bef45a0d6d7a09cfe93283dc9c1473b0f):
`3d73349bce8c09fb2fd990600a21638a9181e7ce7e9b75d5735289973b249d28`

**Reality = Promise**: all planned changes present. `docs/META_LEDGER.md` (7 markup
normalizations, entries #9 and #10 appended), `docs/GOVERNANCE_INDEX.md` (Tier 1
ledger row, Tier 4 registration, Last Reviewed), `docs/PROCESS_SHADOW_GENOME.md`
(10 event closures). No UNPLANNED changes; no code, schema, CI, or dependency touched.

**Definition of Done**:
| # | Item | Result |
|---|---|---|
| 1 | `verify-ledger` exit 0, no FAIL/TAINTED/Skipped | PASS -- 10/10 entries OK; #1 attested by #9 |
| 2 | post-anchor exit 0, zero DISCLOSED_PRE_ANCHOR | PASS -- boundary=#10, none tolerated |
| 3 | governance-health | struck as non-evidential (V2); run, reports OK, not counted |
| 4 | commitment gate sees the corrected brief hash | PASS -- brief registered at `b899b5e6...`; stale empty |
| 5 | hash-multiset invariance | PASS -- 0 removed; 6 added, all accounted to entries #9/#10 |
| 6 | `governance-index --cross-check-ledger` | PASS -- exit 0 |
| 7 | `prompt_injection_canaries` runs | PASS -- exit 0 (refused on iteration 1) |
| 8 | shadow severity < 10, marker absent | PASS -- severity sum 0; marker absent |
| 9 | 868 tests unchanged | PASS -- 868 run, 0 failures, 9 skipped |

**Decision**: The 0.169.0 upgrade turned this repository's ledger markup debt from a
silent skip into a hard failure, correctly and at this cycle's own request (GH #404
suggested fix 3). Entries #2-#8 are repaired by backticking previous-hash values
already recorded, changing no hash input. Entry #1 predates the chain-hash
convention and is closed by MIGRATION ATTESTATION rather than by retrofitting a
chain hash that never existed. Entry #10 amends the Sprint 1 research brief's stale
commitment, the V-2 finding. All ten shadow events are closed: five as
`deferred_upstream` against issues verified as shipped in 0.169.0, five as
`remediated` under this cycle's audit PASS.

Audit: VETO then PASS, attempts 1-2 of 5. Grounds V1-V5 closed and recorded.
Upstream: issues 404 and 408 reopened with verification evidence; 430 filed.
Review Boundary honored: staged, not committed.
---

### Entry #12: SESSION SEAL - Phase 3 (Sprint 2a identity and decision table)

**Entry ID**: `bf96baf94d27`
**Content Hash**: `5f8d9a20d25d5bd83e3c02294d917303290863c942c074ab6bfa72102e813871`
**Previous Hash**: `e86cf1c9b0c196688a49c750f87342e440886da8dfdf0ac961440ac6c0fa3b0d`
**Chain Hash**: `2c6a1ab4c4554b8c5d8b78257f55611fd82c52805cdfd298a70a81691f6cab5c`
**Timestamp**: 2026-09-04T16:00:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-04T1600-c8b357
**Plan**: docs/plan-sprint2a-identity-and-decision-table.md (iteration 2; change_class feature)
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 20a85e936d46ed2b984730e30d9656567aab5d1c):
`feb194b3d6297c8dd830a19055b71edd95f8d1971e438d64ccad06cea9df4aea`

**Gaps closed**: GAP-SEC-08 (HIGH), GAP-ARCH-09 (MEDIUM), plus a new doctrine
drift found in research (docs/33 missing the `domain_schema_mutation` row).

**Reality = Promise**: all seven planned files present; no UNPLANNED changes.
`substrate.py`, `adapter.py`, `policy.py`, `restart_runtime.py`,
`test_substrate_identity.py` (new), `test_substrate_identity_restart.py` (new),
`test_decision_table_doctrine.py` (new), `docs/33-pama-decision-table.md`,
`docs/FEATURE_INDEX.md` (FX004, FX005).

**Definition of Done**: 11 of 11 PASS. Both tenants' facts survive a shared
substrate; no identifier shared across tenants (fact uuid, receipt_id,
correlation_id, four event ids pairwise disjoint); a substrate without a shared
counter still works and its collision raises; identical re-write is a no-op; all
52 doctrine cells resolve as documented; `score_adjustment/critical` now `block`
and `link_deletion/critical` now `require_external_verification`; single-adapter
sequence pinned bit-identical at `ref-0001`-`ref-0007`; **884 tests pass, 0
failures** (868 prior + 16 new, no prior test amended); schemas and fixtures
clean with no fixture regenerated; docs/33 carries 13 operations and documents
why three enum members have none; restored adapter stays bound to the substrate
counter and advances past every restored identifier.

**Decision**: Research reproduced GAP-SEC-08 end to end and found it materially
worse than the deep audit recorded: two adapters over one substrate collided on
*every* identifier, not only the fact uuid, so two tenants emitted decision
receipts under the same `receipt_id` and event chains under the same
`correlation_id`. The blast radius was the evidence surface, not just storage.
The fix mints identifiers per substrate, discovered by attribute so
`TemporalGraphPort` stays Sprint 4's to change, with a `write_fact` collision
guard as defence in depth for foreign substrates.

Audit VETOed iteration 1 on five grounds. The decisive one: `restart_runtime`
rebound `adapter._ids` to a private counter, which would have silently reverted
the entire fix on the first restart. Also caught a vacuous DoD item resting on a
false premise (no test or fixture asserts a literal `ref-000N`; the claim that
many did was wrong), and two arithmetic contradictions between decision records
and Definition of Done.

Scope discipline: Sprint 2's other five gaps (SEC-02, SEC-03, SEC-04, ARCH-04,
ARCH-18) are deliberately deferred to Loops 3-5 rather than bundled into one
verdict. Review Boundary honored: staged, not committed.
---

### Entry #13: SESSION SEAL - Phase 4 (Sprint 2b recall authority record)

**Entry ID**: `c79f9182bbef`
**Content Hash**: `ac9084c542ff93e4f3bfc995a6355e542acb77f918fe38d35b68cb03cabed6ab`
**Previous Hash**: `2c6a1ab4c4554b8c5d8b78257f55611fd82c52805cdfd298a70a81691f6cab5c`
**Chain Hash**: `5f7cf42c8fd19aba3429dabb2a8bc8e703e2166b4c2ce679df36ecfee6664a2e`
**Timestamp**: 2026-09-04T16:23:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-04T1623-fc1836
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 4e1112a27fc425cf8fe460731f562a6eb47b69b6):
`2f6ad57ae62809ee4248a6fc0649a320f92ef36d097cacf7274e2fa16440a880`

**Gaps**: GAP-ARCH-18 **closed**. GAP-SEC-02 **partially addressed -- REMAINS
OPEN** (DoD 10).

**GAP-SEC-02 legs deliberately NOT closed by this cycle**:
1. `RecallContext.principal_ref` stays caller-asserted. This is the owner's
   trust-boundary decision -- the host authenticates, the adapter records -- not
   an oversight. A forged principal is now recorded accurately as the principal
   the host asserted.
2. `set_shared_domain_members` remains an unguarded setter.
3. Write-side crossing still never mutates `_fact_scope`.

**Reality = Promise**: four planned files present, no UNPLANNED changes.

**Definition of Done**: 11 of 11 PASS. Scope-less facts refused `unknown_scope`
including with empty `target_domain_refs`; the string matches the JS runtime
exactly; refusal ordering unchanged so both shielded call sites still refuse
`out_of_scope` and `derived_from_tombstoned_source`; exactly one schema-valid
`memory.recall` event per recall carrying `signal_type: recall_admission`, the
outcome in `signal_semantics`, `principal`, and `policy_version`; every candidate
carries a decision validating against `contextual-recall-admission.schema.json`;
`policy.status` pinned `unavailable`; `characterize_recall` reports
`admitted_count == size`; **901 tests pass, 0 failures** (884 prior + 17 new, no
prior test amended); schemas and fixtures clean, no fixture regenerated.

**Decision**: Research found the fix was much smaller than the deep audit implied.
A complete schema-backed recall decision record already existed
(`contextual-recall-admission.schema.json`, built and validated by
`ContextualRecallAdapter`) -- but that adapter *wraps* the base one and only sees
candidates built-in admission already passed, returning no record when no policy
is configured. Built-in admission decisions were therefore recorded by neither
layer, and every refusal reason was computed and discarded. The fix wires the
existing record into the base path rather than inventing one.

GAP-ARCH-18's refusal string was dictated rather than chosen: the JS runtime
already refuses this case as `unknown_scope`, so this closed a Python/JS
divergence on a shared contract.

Audit VETOed iteration 1 on three grounds, all schema-truth failures the plan
asserted without checking: the planned event could not validate because
`memory-audit-event.schema.json` sets `additionalProperties: False`; the plan
omitted `signal`, the very field the `docs/34` contract it cited names; and LD6
specified a `policy.status` value that does not exist in the enum.

**Recorded for Sprint 4 / GAP-ARCH-01**: `contextual-recall-admission.schema.json`
has no `policy.status` value meaning "built-in admission, no contextual policy
evaluated". `unavailable` is used and defended as the honest member of the four,
with `policy_ref: contextual-recall-policy:none` carrying the distinction. The
vocabulary gap belongs to the boundary freeze, not to a cycle that must not change
a public schema.

**Implementation deviation, disclosed**: `receipts.build_audit_event` is the
commit-path builder -- it requires a single `memory_id` and supports neither
`principal`, `signal`, nor `payload`. A recall event spans many candidates and has
no single `memory_id` (docs/34 puts `memory_id` on the per-unit decisions). The
event document is therefore built in `_recall_event` and validated against the
same schema, rather than widening the commit builder for a shape it does not
model. This kept the change inside the plan's declared files; `receipts.py` is
unmodified.

Review Boundary honored: staged, not committed.
---

### Entry #14: SESSION SEAL - Phase 5 (Sprint 2c deletion authority)

**Entry ID**: `972ee56a84d1`
**Content Hash**: `0ef584648ab4391f82e30fc6878be340a2c971551fefef8a3220f2836fc60b6c`
**Previous Hash**: `5f7cf42c8fd19aba3429dabb2a8bc8e703e2166b4c2ce679df36ecfee6664a2e`
**Chain Hash**: `2228f2c409f4fdd1c69512e2a5e2e7a371ce852c8c7ce7d1a5d563e4f27f76f7`
**Timestamp**: 2026-09-04T16:35:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-04T1635-bb5378
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 599b0e9168819281be29f2f0ba2d322f2d2c0406):
`b5188317ed2dd17f0e9b7fc628e5aac9114e52500b1746d2abdeaa0245b2c57d`

**Gaps**: GAP-SEC-03 **closed** (five defects). GAP-SEC-04 **investigated and
deliberately not implemented** -- see the operator decision below.

**Definition of Done**: 11 of 11 PASS. A stale delete is refused `stale_decision`
and the fact survives; a delete whose fact does not belong to the claimed target
is refused `target_binding_mismatch` and writes **no tombstone**; a cross-tenant
delete is refused `cross_tenant_delete` and the victim fact **remains in the
substrate**; a nonexistent uuid is refused `fact_not_found` with no tombstone;
both positive paths still commit; the guard is opt-in so the 16 default callers
are unchanged and the one snapshot-passing caller still commits; guard ordering
asserted; the binding survives a restart; **912 tests pass, 0 failures** (901
prior + 11 new, no prior test amended); schemas and fixtures clean.

**Decision**: `governed_delete` enforced none of the authority the write path
enforces. Probes confirmed five defects, of which two are the serious ones: a
second tenant performed `permanent_deletion` of another tenant's fact on a shared
substrate and the fact was physically removed, and a delete claiming an unrelated
target wrote a tombstone attributing the victim fact to a memory it never belonged
to. The second is evidence corruption rather than an authorization bypass -- the
tombstone is the record that survives the deletion, and it could be made to lie.
Loop 2 did not address the cross-tenant case: it fixed identifier minting, while
`governed_delete` accepts a `fact_uuid` directly.

Audit VETOed iteration 1 on three grounds. The decisive one: LD2 named
`_fact_scope` as the fact-to-memory binding source, and `_fact_scope` carries no
memory reference at all -- the check was unimplementable as written, and the
obvious substitute (`_current_fact_by_memory`) would have wrongly refused deletion
of superseded facts. The correct fix adds adapter state, which the audit then
required be carried through `restart_runtime` or every post-restart delete would
refuse and the guard would become an outage. The audit also caught a blanket
safety claim about 17 call sites that had not been checked; one of them does pass
a non-empty snapshot, and it is now exercised end to end rather than argued from
inspection.

**OPERATOR DECISION REQUIRED -- GAP-SEC-04 trust anchor**: research established
that grant artifacts are *already* content-addressed (`grant_id` is
`sha256(rfc8785(body))`) and that `evaluate_reusable_grant` never recomputes it.
But recomputing the digest **does not close the gap**: `_digest` is unkeyed, so an
attacker who edits the body recomputes the id and evaluation returns `current`
against a perfectly self-consistent artifact -- demonstrated by probe. Shipping the
digest check alone would pass every test, close nothing against the actual threat
model, and read in this ledger as a fix. Four options are carried to the operator:
adapter-held issuance registry; keyed digest; bind to the existing but uncalled
`verify_approval_evidence`; or declare the host the trust boundary for grants as
already decided for recall principals. GAP-SEC-04 does not enter an implementation
cycle until this is answered.

**Partial refutation of the deep audit, recorded**: editing `scope_refs` does not
evaluate `current` against the harness projection -- it is caught as
`not_applicable`/`scope_mismatch`. The audit's result required also supplying a
matching caller-built projection. The `expires_at` case stands exactly as reported.

Review Boundary honored: staged, not committed.
---

### Entry #15: SESSION SEAL - Phase 6 (Sprint 2d derived authority)

**Entry ID**: `83f35521054e`
**Content Hash**: `7f59f7d26905e8cb5864892b248bf7b835d58bde804e1619e548ae7cd0a7abe5`
**Previous Hash**: `2228f2c409f4fdd1c69512e2a5e2e7a371ce852c8c7ce7d1a5d563e4f27f76f7`
**Chain Hash**: `ae7fb38720555b483249d4ff0a1c0f27db2bebf598797f082c91ce7f1734fd7d`
**Timestamp**: 2026-09-04T16:52:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-04T1652-5eb9f9
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index ba9b6f0dc5ac5bfcc6ce3180f20d02e06a62c9fd):
`84c08e03e155f6e331c0be712db18aa541133345c5ad75623726226b1c644ac8`

**Gap**: GAP-ARCH-04 **partially addressed -- REMAINS OPEN**. Only the
self-approval leg closes.

**GAP-ARCH-04 legs still open**:
1. `review_satisfied=True` plus any non-empty `approval_refs` still discharges
   `require_review` -- 74 occurrences in the suite.
2. `require_external_verification` is still dischargeable by assertion.
3. `actor_authority_resolved` still defaults `True`, skipping M-AUTH.
4. `crossing.py` and `scope_governance.py` still inherit the assertion-backed
   discharge (their self-approval leg does close, via `policy.evaluate`).

**Definition of Done**: 9 of 9 PASS. A proposal naming its own actor in its
approval refs blocks, alone or among several refs; the derivation reaches
`allow_with_ledger` base cells; a genuine third-party discharge still allows;
the asserted flag still blocks independently; matching is exact so
`actor_id="a"` does not self-approve against `("grant:human",)`;
`Decision.review_discharge` records `asserted` and never `verified`; a
self-approved `share` crossing now blocks while a third-party one is unaffected;
**925 tests pass, 0 failures** (912 prior + 13 new, no prior test amended);
schemas and fixtures clean.

**Decision**: `_apply_review`'s docstring has always said "Review is satisfied by
an approver, never by the proposer". The invariant was checked -- but only against
`approves_own_authority`, a boolean the proposer sets, so nothing reached it. With
`actor_id="agent:x"` and `approval_refs=("agent:x",)`, an actor approving itself in
plain sight discharged `require_external_verification` on `policy_mutation/critical`
to `allow_with_ledger`. Research also confirmed the strictest non-blocking outcome
collapsed to allow on the literal string `"i-said-so"`.

The fix generalizes two patterns that already existed in this repository:
`decision_overwrite.py:171` already derives self-approval from identity, and
`enforcement_evidence.py:61-80` already distinguishes unverified from verified
approval evidence. Neither was applied in the shared evaluator every other module
routes through.

Blast radius was **measured, not estimated**: `_apply_review` was instrumented
across a full 912-test run, finding 74 assertion-backed `require_review`
discharges, 4 `require_external_verification` discharges, and **zero**
self-approvals reaching a discharge. The prediction of zero breakage held exactly.

Audit VETOed iteration 1 on three grounds. The decisive one: the derivation was
placed in `_apply_review`, which runs only for review-requiring outcomes, so a
self-approving proposal at `allow_with_ledger` would have been permitted when
derived and blocked when asserted -- the generalization would have been *weaker*
than the flag it generalizes. Moved to `_apply_modifiers` beside that flag, and a
test now fails any implementation placed in the wrong function. The audit also
found the non-goal list wrong about `crossing.py`, which `policy.evaluate` reaches
directly, and that the plan never said how `review_discharge` would reach the
`Decision`.

**Deliberately not done -- sequencing**: `require_external_verification` is
dischargeable by assertion at only four sites, which makes tightening look cheap.
Two are `decision_overwrite` presenting a *validated grant* through the asserted
channel; they would have to re-express real authority through a verified carrier
that does not exist until Loop 6. Forcing legitimate callers to fake a channel is
how a control acquires a workaround that outlives it. Loop 5 makes provenance
visible; Loop 6 makes it required.

**Operator decision recorded (2026-09-04), scheduled for Loop 6**: GAP-SEC-04
trust anchor resolved as **option C as the code path** -- bind grant evaluation to
independently-held ratification evidence -- **with option D retained as a
declarable deployment profile** for single-trust-domain embedded use. Binding
requirement: at least one term in the verification must come from a store the
presenter cannot write. `verify_approval_evidence` has the right relational shape
but currently takes both artifacts as parameters, so a caller supplying both can
forge them consistently.

Review Boundary honored: staged, not committed.
---

### Entry #16: SESSION SEAL - Phase 7 (Sprint 2e ratification anchor)

**Entry ID**: `34fc1a779a25`
**Content Hash**: `234bc741ec0b24d5fbba161fe25236799ca8651cd0c8ca5b559b4111837af43d`
**Previous Hash**: `ae7fb38720555b483249d4ff0a1c0f27db2bebf598797f082c91ce7f1734fd7d`
**Chain Hash**: `cb0ac64eb16e4b1efd28425fe2110b8e361389a93ae1b7a8fa7a5bb7b9870a37`
**Timestamp**: 2026-09-04T17:13:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-04T1713-79ea9b
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 851a582140092d626ba323ef0961b1e03dcf0000):
`37a22128079186d2cf157676ead102d511aa9c9025d00002b7cef0e3e343ef02`

**Gap**: GAP-SEC-04 **closed for the grant path**. Implements the operator
decision of 2026-09-04: option C as the code path, option D retained as a
declarable profile.

**Definition of Done**: 12 of 12 PASS. An untampered grant verifies and is marked
`ratification_evidence_verified`; a tampered body with a stale id is caught by
integrity; **a tampered body with a recomputed id -- the case that defeated a
digest-only fix -- is caught as `ratification_evidence_unregistered`**; the forged
grant cannot obtain a registration, because ratification refuses an expiry beyond
the proposed validity; the registry exposes no public registration method; the
declared host profile still evaluates `current` but is labelled
`ratification_evidence_asserted`; silence never reads as verified; results still
validate against the **unmodified** schema; the grant bridge still refuses to
discharge `require_external_verification`; **937 tests pass, 0 failures** (925
prior + 12 new, no prior test amended); schemas and fixtures clean, and
`git diff --name-only schemas/` is empty.

**Decision**: research found the same defect a third time. `ratification_evidence_present`
is a caller-asserted boolean, exactly like `approves_own_authority` (Loop 5) and
`review_satisfied` (open). Stated once: **the controls are present and correct,
and their inputs are supplied by the party they constrain.** That is the whole of
GAP-ARCH-04 and GAP-SEC-04.

The fix generalizes `decision_overwrite.DurableDecisionRegistry`, the third
existing in-repo pattern this program has generalized rather than reinvented.

Audit VETOed iteration 1 on three grounds, and the first was decisive. The plan
gave the registry a public `register(grant)` and defended it as an anchor because
it refuses to overwrite. Refusing overwrite is the wrong property: the recompute
attack produces a *new* grant id, so there is nothing to overwrite -- the attacker
registers the forgery, all three checks pass against the attacker's own record,
and evaluation reports `current` with `ratification_evidence_verified`. The cycle
would have shipped a control that certifies the exact forgery it exists to defeat,
and labels it verified. The operator's binding requirement -- at least one term
from a store the presenter cannot write -- was not met by the plan that claimed to
implement it.

The audit also found the plan's designated "discriminating check" was unreachable:
because `grant_id` is a digest of the body, checks 1 and 2 passing imply the held
and presented bodies are identical, so the divergence check cannot fire against a
tamper. DoD 3 asserted an outcome the design could not produce. Same defect class
as Loop 2's unreachable-branch veto.

Corrected: registration is a consequence of ratification and there is no public
method to register an arbitrary grant. An actor cannot obtain a record for tampered
values without performing a valid ratification of them, and
`ratify_reusable_grant`'s preconditions refuse that. The divergence check is
retained and honestly relabelled as a consistency assertion.

**Disclosed limit**: in a single-process reference implementation the
presenter/host separation is by ownership, not enforcement -- a caller handed the
registry instance can reach its internals. Written into the class docstring in the
same terms `DurableDecisionRegistry` uses, so the boundary is demonstrated and its
limit recorded rather than asserted as stronger than it is.

**Relocated, not closed**: GAP-ARCH-04's external-verification leg does not belong
to the grant path at all. `evaluate_pama_with_reusable_grant:397` already refuses
to discharge anything but `REQUIRE_REVIEW`. The two production sites discharging
external verification by assertion are `decision_overwrite`, which builds its
`Proposal` directly and bypasses that bridge. Loop 7.

Review Boundary honored: staged, not committed.
---

### Entry #17: SESSION SEAL - Phase 8 (Sprint 2f verified discharge)

**Entry ID**: `45a627a0f157`
**Content Hash**: `4b3357931d84b53d1057086333fd53a4b3229cef6373947f70201245b63e988c`
**Previous Hash**: `cb0ac64eb16e4b1efd28425fe2110b8e361389a93ae1b7a8fa7a5bb7b9870a37`
**Chain Hash**: `2fd54bae86d94ca781390dadbeed36954306c40cb803bbaf4253858694d12929`
**Timestamp**: 2026-09-04T17:54:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-04T1754-81306b
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 302504e5f5db7be503d1dcc311ff8d97b32ac457):
`b5ad08b0717c7f0778adcdf6c344b2b809d3e3a56cc05446277fffbec4c237e4`

**Gap**: GAP-ARCH-04 external-verification leg **closed**. The `review_satisfied`
discharge of `require_review` (74 sites) remains open.

**Definition of Done**: 12 of 12 PASS. `policy.evaluate` with `review_satisfied`
and the string "i-said-so" now returns `require_external_verification` for
`policy_mutation/critical`, `scope_expansion/high`, and
`permanent_deletion/critical`; `require_review` discharge is unchanged and still
records `asserted`; a bound, non-self, human-confirmation attestation discharges
and records `verified`; each attestation check refuses by name; an attestation
bound to another proposal is refused; `decision_overwrite` still commits its
high-risk overwrite through the attested path; **948 tests pass, 0 failures**
(937 prior + 11 new, six declared amendments); schemas and fixtures clean, no
schema modified.

**Decision**: research reframed this leg entirely. `decision_overwrite` was
believed to bypass a control; it does not. `_grant_refusal:329-367` binds the
grant to the proposal and target, derives self-approval from identity, enforces a
risk ceiling, and **requires HUMAN_CONFIRMATION for high or critical risk** --
which is what external verification means doctrinally. Its discharge was
legitimate. The defect was that `policy` had no channel for verified authority,
so a human-confirmed proposal-bound grant and the literal string "i-said-so"
arrived identically and discharged identically.

The fix caps assertion at `require_review` and adds an explicit attested entry
point, mirroring `evaluate_pama_with_reusable_grant`. The attestation is a frozen
record cross-checked relationally against the proposal, deliberately **not** a
fourth caller-asserted boolean.

**Stated limit, not discovered later**: the attestation is caller-constructed and
therefore forgeable. What changes is that the assertion path is closed entirely.
Binding attestations to evidence the presenter cannot write is the same problem
`RatificationRegistry` solved for grants, and applying that pattern to
attestations is open work. This is recorded in the plan, in
`docs/33-pama-decision-table.md`, and here.

Audit VETOed iteration 1 on three grounds. V1 found an **uncovered production
path**: `structural_mutation.py:436` passes
`base_outcome=REQUIRE_EXTERNAL_VERIFICATION` with discharge allowed, so the cap
reaches it -- and instrumentation showed no test exercised that discharge, so a
green suite would have proved nothing about the change. Coverage was added rather
than assumed. V2 found the amendment count wrong by a factor of three, and named
the one amendment with a governance consequence.

**AMENDED TESTS -- first exception to a discipline five seals have cited.**
Entries #11-#16 each recorded "no prior test amended". This cycle amends six
sites, deliberately, because the behaviour they depended on is being removed:
four in `test_derived_authority.py`, two in `test_deletion_authority.py`.

**One of them is evidence in ledger Entry #15.**
`test_derived_authority.py` `test_third_party_discharge_still_works` was Loop 5's
DoD 3. It asserted that `policy_mutation/critical` with a third-party approval
discharged to `allow_with_ledger`. That was true when Entry #15 sealed. Loop 7
narrows it: external verification is no longer dischargeable by assertion, so the
test now exercises the same property -- a third-party discharge works -- at a
review-requiring outcome, which is what it was actually about. Entry #15 is named
here so the ledger reads as a sequence rather than as two entries that disagree
with nothing connecting them.

**SCOPE ADDITION discovered during implementation, disclosed**: capping the
discharge made `governed_delete` unable to perform `permanent_deletion` at high or
critical risk at all, because the adapter calls `policy.evaluate` and had no
channel for an attestation. That would have removed a legitimate operation rather
than governing it. `governed_delete` gains an optional `external_verification`
parameter. `adapter.py` was not in the plan's Affected Files; this is recorded
rather than absorbed.

**Documentation** (operator instruction, 2026-09-04): `docs/33-pama-decision-table.md`
gains a "Discharging a decision" section stating what each outcome requires, that
self-approval is derived from identity, and the attestation's limit. `README.md`
gains the installable-distribution path Sprint 1 delivered but never documented.

Review Boundary: staged, not committed. Prior work is committed at `fe7724e` and
`97721dc`.
---

### Entry #18: SESSION SEAL - Phase 9 (Sprint 2g parked verification)

**Entry ID**: `3961f7d97ed9`
**Content Hash**: `f67fd881819b614be4ecbb8ecbac7815c6849cc581ac87315bc4072c4ef033de`
**Previous Hash**: `2fd54bae86d94ca781390dadbeed36954306c40cb803bbaf4253858694d12929`
**Chain Hash**: `07bde207e78cc97268e85c782f55d407fc30030349d190132224a9a656230a58`
**Timestamp**: 2026-09-04T23:59:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L2
**Verdict**: PASS
**Session**: 2026-09-04T2347-39681d
**Plan**: docs/plan-sprint2g-parked-verification.md (iteration 4)
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 2f7f6177dea169708ed15365f27c86fb46e32cbd):
`e3cecc621ff23efb0120b202d7ec0a39cd74d8cd54867a70ba09e2196a80aa8a`

**Scope**: ADR-037 implementation **step 1 of 4**, and only step 1. The operator
fixed a rigid order -- parked state, then evidence qualification, then governed
resumption, then fail-closed conversion of the 51 caller sites -- and directed
that the gate not flip before the first three exist. Steps 2-4 are not built.
`policy._apply_review` is unmodified, verified by empty diff. Assertion still
discharges `require_review` after this cycle, deliberately.

**Reality = Promise**: two new files, four documentation updates, no existing
module modified, no schema modified. No UNPLANNED changes.

**Definition of Done**: 11 of 11 PASS.
| # | Item | Result |
|---|---|---|
| 1 | Park records the `Proposal`, decision, correlation, `parked_at`, `policy_version` | PASS |
| 1b | Retained proposal re-evaluates to the recorded decision | PASS -- `policy.evaluate(record.proposal) == record.decision` |
| 1c | `state_snapshot` rides along for the staleness guard | PASS |
| 2 | `permitted_actions` equals the decision's, per outcome | PASS -- asserted by equality, never a literal |
| 3 | One schema-valid event; modeled fields top-level | PASS -- absence from `payload` asserted |
| 4 | Duplicate park raises; first record intact | PASS |
| 5 | `allow` and `allow_with_ledger` refused | PASS |
| 6 | `require_external_verification` parks with its own route | PASS |
| 7 | `block` refused | PASS -- prohibition asserted from the decision |
| 8/9 | No method discharges or permits; `resume` absent, not stubbed | PASS |
| 10 | Full suite; `_apply_review` unmodified | PASS -- 971 pass / 0 fail / 7 skip; `policy.py` diff empty |
| 11 | Validators clean, no schema modified | PASS -- 58 schemas, 64 fixtures, exit 0 |

**Test count**: 951 -> 971 (+20). Run under the pinned `cryptography==50.0.1` the
repository declares, not the ambient interpreter's 48.0.0.

**Negative control**: five mutations, each caught, control restored green --
park accepting `block`; the route hardcoded to `enter_pending_verification`;
a `resume` stub raising `NotImplementedError`; `correlation_id` demoted into
`payload`; duplicate park overwriting instead of raising.

**Decision**: audit VETOed twice, on four grounds, and every one was a design
correction rather than wording.

*V1* -- the planned record held identity fields only (`proposal_id`, `actor_id`,
`target_reference`, `operation`, `risk_class`). `policy.evaluate` takes a
`Proposal` of 28 fields, and the floors and modifiers read `target_class`,
`downstream_authority`, `reversibility`, `evidence_refs`, and the isolation-domain
fields. Step 3 could not have re-evaluated from that summary, so it would have had
to reshape the record -- the exact cost this cycle existed to avoid. The record now
retains the `Proposal`.

*V2* -- the plan parked `block` and treated its empty `permitted_actions` as a
feature. `_envelope` names `enter_pending_verification` in the **prohibited** set
for `block`. Parking one contradicts the envelope being recorded and produces a
record no evidence can ever discharge: permanent parked residue charged against
retention. `block` is now refused, on the same footing as `allow` but for the
opposite reason -- `allow` had no refusal to record, `block` has no route out.

*V3* -- staleness had no anchor. Fixed by V1: `state_snapshot` is a `Proposal`
field, so it is recorded as a reason rather than acquired by luck.

*V4* -- DoD 2 and DoD 6 could not both be satisfied. Measured: `require_review`
permits `enter_pending_verification`; `require_external_verification` permits
`request_external_verification` instead. The danger was not the failing test but
the fix an implementer reaches for -- hardcoding the review route to make DoD 2
pass, which is the caller-asserted-input defect this program has now found four
times. The envelope has three states, not two: permitted, unlisted, prohibited.

**Audit conditions on the PASS**: C1, modeled event fields (`correlation_id`,
`policy_version`, `state_snapshot`) take their modeled top-level home rather than
`payload` -- legal either way, but a modeled field buried in `payload` is invisible
to any consumer joining on it. C2, parked records have no eviction path in this
cycle and retention belongs to #363, recorded as a deferral rather than left to be
discovered. Both satisfied.

**Known limitation, disclosed**: `decision_overwrite._event` places
`state_snapshot` inside `payload`, the placement C1 rules against. It is
pre-existing, out of this cycle's scope, and named here so it is not later read as
precedent.

Audit: VETO, VETO, PASS -- attempts 1-3 of 5. Grounds V1-V4 closed and recorded.
Review Boundary: staged, not committed.
---

### Entry #19: SESSION SEAL - Phase 10 (Sprint 2h evidence qualification)

**Entry ID**: `e2c500fff592`
**Content Hash**: `2555d59b5c3826708f6bb77c53bc438a5b4f84dc1a9a335f534b9d1e59ce305d`
**Previous Hash**: `07bde207e78cc97268e85c782f55d407fc30030349d190132224a9a656230a58`
**Chain Hash**: `23d71557eeb046ad071585e3a20a2edc4c39b7c8a7b4460febf725ac98b968f5`
**Timestamp**: 2026-09-05T01:10:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L2
**Verdict**: PASS
**Session**: 2026-09-05T0045-37f432
**Plan**: docs/plan-sprint2h-evidence-qualification.md (iteration 4)
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 87eb6a6c9dbca6cf801163f7de191329b0db3846):
`7d281120671c481a5560ec115ebeb55ff71ec3c5528aaa823cec96a2d88d28ed`

**Scope**: ADR-037 implementation **step 2 of 4**, and only step 2. R2 and R3
made computable. Resumption (step 3) and fail-closed conversion (step 4) are not
built. `policy.py` is unmodified, verified by empty diff; `PendingVerificationRegistry`
is not imported, asserted over the module's parsed import statements.

**The gap this closes, measured**: `policy._apply_modifiers:252` was the shared
evaluator's entire treatment of evidence -- `if not proposal.evidence_refs`. On
`semantic/write/low/reversible`, `(" ",)` and `("i-said-so",)` and ten copies of
one reference all cleared M-EVID exactly as `("receipt://sha256:deadbeef",)` did.
Evidence was a truthiness check on a tuple. This is the **sixth** control found
implemented in one module and absent from the shared evaluator.

**Reality = Promise**: two new files, five documentation updates, no existing
module modified, no schema modified. No UNPLANNED changes.

**Definition of Done**: 16 of 16 PASS. Test count 971 -> 999 (+28), 0 failures,
7 skipped, under the pinned `cryptography==50.0.1`. Validators clean (58 schemas,
64 fixtures).

**Negative control**: six mutations, each caught, control restored green --
`artifact_bound` requiring only one binding; a failing verifier collapsing to
`asserted`; relation 3 removed; groups counted at their strongest status rather
than weakest; estimator groups counted as directly satisfying; a named-but-unheld
verifier trusted.

**Decision**: audit VETOed twice, on five grounds, and the first was the most
important thing this cycle produced.

*V1* -- the plan claimed that deriving a class from present bindings was "the
direct answer" to the caller-asserted defect found six times. It is not. The
bindings are themselves caller-supplied strings: `digest="deadbeef"` with
`verifier="trust-me"` classifies `artifact_bound` with nothing checked. That is
the same defect with more fields to fill in, and shipping it under a closure
claim would have been worse than not claiming it. The repository had already
solved this shape twice -- `ratification_evidence_verified`/`_asserted` (Loop 6)
and `review_discharge` recording `asserted`/`verified` (Loop 7) -- and the plan
had ignored both. Classification now carries a binding status, and **the claim
is narrowed to what the work supports**: evidence stops being an opaque string
and becomes a typed, ranked claim that names its own verifier. The
caller-asserted pattern remains open.

*V2* -- the stated algorithm (union-find over `derived_from` and shared
`failure_domain`) could not satisfy its own DoD 9. Two runs of one deterministic
procedure share no derivation edge and need declare no failure domain, so they
would have reported as two independent groups -- precisely the laundering R2
names by name. A third relation, identical `(method, method_version, inputs)`,
is the mechanism. DoD 9 now also asserts the absence of the other two relations
so the test cannot pass by accident.

*V3* -- ADR-037 §4 (`collect_more_evidence` must state what would discharge
*this* proposal) was owned by **no step** of the ADR's own four-step order. It is
now assigned to step 3, with the reason: it needs a risk class, and step 2
refuses one so it cannot return a sufficiency verdict. The ADR is amended.

*V4* -- introducing a verifier introduced a state the plan had not: a verifier
that runs and **fails**. Two statuses meant the obvious implementation was
`"verified" if passed else "asserted"`, making "nobody has checked this digest"
and "somebody checked it and it did not match" the same state. The second is a
refutation, and collapsing it lets a proposer whose artifact failed keep
re-presenting it as merely unchecked. `refuted` is a distinct third status that
never collapses into `asserted`. Neither prior precedent carried a third state,
because neither runs a verifier that can fail -- this was new to the repository,
not a repeated oversight.

*V5* -- Loop 8's V1 shape returned. The result broke groups down by class only,
so a group holding an `asserted` artifact and one holding a `verified` artifact
were indistinguishable -- collapsing the very distinction V1 had just
introduced, and forcing step 4 to reach past the result and re-derive the
grouping. `DependenceAnalysis` now counts by (class rank x binding status), and
DoD 10 answers step 4's actual question from the result alone.

**Audit conditions on the PASS**: C1, counting discipline -- a group counts at
its **weakest** status, so a group holding a `verified` and a `refuted` item is
never counted as verified and is reported among the refuted-carrying groups; and
no total mixes `unqualified` groups with qualifying ones, because ten distinct
bare strings legitimately form ten groups and qualify nothing. C2, FX013's index
note carries the narrowed claim including the residual, on the FX011 precedent.
Both satisfied.

**Naming, found in research before it was spent**: `EVIDENCE_CLASSES` was already
taken. `derivation_currentness.py:26` uses it for polarity and role -- ordinary,
negative, adversarial, correction, incident -- with two schema consumers. R3
ranks checkability, an orthogonal axis. The module says `qualification_class`.
Discovering this after step 4 would have been an expensive rename across a
schema surface.

**Recorded, not acted on**: `reusable_grants` establishes independence by
`source_ref` identity plus a caller-asserted `independent_adjudication` boolean,
which R2 says is not sufficient on its own. R4 fences that module off -- it
governs reusable authority from historical precedent and must not be generalized
-- so the tension is recorded rather than resolved. `_eligible_human_precedents`
dedupes correctly via `by_source.setdefault`; there is no defect to fix there.

Audit: VETO, VETO, PASS -- attempts 1-3 of 5. Grounds V1-V5 closed and recorded.
Review Boundary: staged, not committed.
---

### Entry #20: SESSION SEAL - Phase 11 (Sprint 2i governed resumption)

**Entry ID**: `348d5f58d97e`
**Content Hash**: `f442ffcbce0ed02625eb34e502de19047ae5591f72dbc7409c94d3d4fd966a0a`
**Previous Hash**: `23d71557eeb046ad071585e3a20a2edc4c39b7c8a7b4460febf725ac98b968f5`
**Chain Hash**: `62243685ea6622ca21b2173f133a57eb88a7be56ae9cbc871c654a5d24030a81`
**Timestamp**: 2026-09-05T02:20:00-04:00
**Phase**: SUBSTANTIATE
**Author**: Judge
**Risk Grade**: L3
**Verdict**: PASS
**Session**: 2026-09-05T0140-688455
**Plan**: docs/plan-sprint2i-governed-resumption.md (iteration 4)
**SSDF Practices**: PO.1.4, PS.2.1, PW.1.1, PW.7.2

**Merkle Seal** (SHA256 over `git write-tree` of the staged index 65e471134b71188389d6920f05be5c7f6fd318ae):
`562ff31ddde811b2bd27bbbe32bada0cb53bc4127cde941c75fb70ad41783fcd`

**Scope**: ADR-037 implementation **step 3 of 4**, plus **section 4**, which step 2
assigned here. Step 4 is not built: `policy.py` is unmodified by empty diff, and
the 51 assertion sites are unconverted. **After this seal all three prerequisites
exist, so step 4 becomes permissible** -- which is what the ordering was for.

**Graded L3**, higher than steps 1 and 2. Those described; this transitions. A
resumption that returns `allow` for a proposal that should still be parked is an
authority bypass rather than a wrong shape.

**The honest range, measured and stated in the plan rather than discovered later**:
`require_external_verification` is resumable through a bound, separated
attestation (to `allow_with_ledger`). `require_review` is **not**. Evidence
reaches the evaluator only as `proposal.evidence_refs`, and M-EVID is an
emptiness check, so appending qualified, independently verified evidence to a
proposal that already had one reference changes the outcome not at all. Its only
discharge today is `review_satisfied` plus `approval_refs` -- exactly the
assertion route step 4 converts. Step 2's headline finding applies to step 3's
own mechanism.

**Definition of Done**: 15 of 15 PASS. Test count 999 to 1020 (+21), 0 failures,
7 skipped, under the pinned `cryptography==50.0.1`. Validators clean.

**Negative control**: six mutations, each caught, control restored green --
staleness returning a computed decision (refuse-then-evaluate); the attestation
ignored in favour of plain `evaluate`; resumption rewriting `risk_class`; an
invented independence bar; a newly-yielded `block` resuming; refuted evidence
admitted.

**AMENDED TESTS -- second exception, declared.** Loop 8 asserted `resume` was
absent from `PendingVerificationRegistry`, which was correct then: step 3 was
gated on step 2 existing. Step 3 has landed, so two tests invert. The half of the
original assertion that still matters is retained and strengthened:
**`ParkedProposal` must never grow a `resume`.** Resumption is an evaluator
operation; a `resume` on the record itself would put the transition in the hands
of whoever holds the record, which is how a parked proposal becomes a standing
authority.

**Decision**: audit VETOed twice, on four grounds.

*V1* -- LD6 required excluding evidence "whose verifier principal is the
proposing actor". Measured: `EvidenceItem` has **no principal field**, and its
`verifier` is a name step 2 deliberately made non-authoritative. Left
unspecified, the easiest fix is adding `verifier_principal_id` to `EvidenceItem`
-- putting a separation control's input back in the hands of the party it
constrains, for the eighth time. The principal lives on
`ExternalVerification.verifier_principal_id`, where Loop 7 already derives
`attestation_self_verified`. **No new separation logic is written this cycle**,
and DoD 6b asserts no principal field is added.

*V2* -- DoD 6 required consulting `attestation_refusal`, which takes an
`ExternalVerification`; the signature had no attestation parameter. The plan had
conflated evidence qualification (step 2) with external attestation (Loop 7) --
two objects Loops 2 and 7 kept apart. Both are needed at resumption.

*V3* -- section 5 requires re-evaluation "against current policy and current
state". The plan handled state and ignored policy, though `ParkedProposal`
carries `policy_version` precisely to detect drift. Drift is now compared and
**reported without refusing**, since re-evaluating under current policy is the
correct behaviour, and a decision that changed for policy reasons rather than
evidence reasons is a materially different fact to the actor.

*V4* -- the mechanism was inert for the majority outcome and the plan implied
otherwise, **and the discharge function was missing entirely**. LD2 named
`attestation_refusal` -- the guard -- and never
`evaluate_with_external_verification`, which is what actually discharges. As
written it would have validated an attestation and then re-evaluated through a
path that ignores it. The one path that genuinely works would not have worked.

**Audit conditions on the PASS**: C1, do not pre-call `attestation_refusal` --
`evaluate_with_external_verification` calls it internally and surfaces the result
in `decision.reasons`, and a second copy of a control already correctly placed in
the shared evaluator is two things that can diverge. Nine cycles have gone into
controls present in one place and absent from another; a redundant copy is the
same mistake with the polarity reversed. C2, pin the Loop 7 early return this
cycle now depends on: an otherwise-valid attestation must not discharge a parked
`require_review`, because that early return is the only thing stopping an
attestation becoming a general-purpose discharge. Both satisfied.

**Section 4's independence bar: refused rather than invented.** Section 4
requires stating "what independence bar applies at this risk class". **No such
bar exists in accepted doctrine.** The only count threshold is
`reusable_grants.minimum_independent_human_evidence >= 2`, which R4 explicitly
forbids generalizing; section 2b argues against counting outright; and ADR-037
line 128 warns by name against inventing
`independent_verified_approver_count >= 2`. The report states `bar: undefined`
with the open question attached, a test asserts no numeric threshold appears
anywhere in it, and the question is filed as **GH #379** rather than answered
inside an implementation cycle. A message saying "this criterion has no defined
bar" is more useful to an agent than a confidently invented number.

**Recorded, not acted on**: `DELEGATED_POLICY`, a non-human authority kind valid
at low and medium risk, exists only in `decision_overwrite.py`; `policy.py` has
no concept of it. Seventh instance of the control-in-one-module pattern, adjacent
to R4. Generalizing an authority kind is a doctrine change, not a step-3
implementation detail.

Audit: VETO, VETO, PASS -- attempts 1-3 of 5. Grounds V1-V4 closed and recorded.
Review Boundary: staged, not committed.
