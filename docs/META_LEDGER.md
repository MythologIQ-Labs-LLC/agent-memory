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
