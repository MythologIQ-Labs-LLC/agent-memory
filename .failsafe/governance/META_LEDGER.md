# META LEDGER — agent-memory

Qor-logic S.H.I.E.L.D. decision ledger for `Knapp-Kevin/agent-memory`.

Note: this repository was not previously bootstrapped with Qor-logic governance.
Entry #0 below is a genesis anchor created at research time; a full
`/qor-bootstrap` (CONCEPT.md + ARCHITECTURE_PLAN.md) remains available as a
later step if the Governor wants full S.H.I.E.L.D. DNA. Repository content was
not modified — this session is observational/commentary only per Governor
directive (Codex structural overhaul in flight).

---

### Entry #0: GENESIS

**Timestamp**: 2026-08-10T22:30:00Z
**Phase**: GENESIS
**Author**: Analyst
**Risk Grade**: L1

**Content Hash**:
```
SHA256("agent-memory:qor-logic:genesis:2026-08-10")
= 5305376f89cb2d3c5631329efbc06b2740b2208713d58229db6c06b4f95d1e21
```

**Previous Hash**: none (genesis)

**Decision**: Ledger initialized to anchor research and planning artifacts for
the open-issue backlog consolidation effort.

---

### Entry #1: RESEARCH BRIEF

**Timestamp**: 2026-08-10T22:30:00Z
**Phase**: RESEARCH
**Author**: Analyst
**Risk Grade**: L1 (observational — no repo mutations)

**Content Hash**:
```
SHA256(RESEARCH_BRIEF.md)
= 8f2c899c77e4e5b09eaad3434aa2228a987a2d145ba8042654fcbbaaeafaefbe
```

**Previous Hash**: 5305376f89cb2d3c5631329efbc06b2740b2208713d58229db6c06b4f95d1e21

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 2a456d3b6993ca2b520a89eb654542bd44d2c3eaaa969c735ceb5f052b1ed704
```

**Decision**: All 25 open issues triaged against repository reality. Key
findings: 9 issues already delivered but unclosed (Group A); docs 30/31/32
unwritten and blocking ADR-017/018/019; 8 distinct DRIFT findings, dominated by
positional doc-number staleness in issue bodies and README; schemas/validator/
fixtures lag the docs-26–29 contracts slice; no CI. Plan must sequence around
Codex's in-flight structural overhaul and treat stable references as a
prerequisite for resuming doctrine authoring.

---

### Entry #2: PLAN — Issue Backlog Consolidation

**Timestamp**: 2026-08-10T22:45:00Z
**Phase**: PLAN
**Author**: Governor
**Risk Grade**: L1 (advisory — execution gated on Milestone 0 post-overhaul
re-baseline)

**Content Hash**:
```
SHA256(plan-issue-backlog-consolidation.md)
= f360ef7793edd29934ac3810ff712957c12b19bdef595ecef3278ec65bae4a5f
```

**Previous Hash**: 2a456d3b6993ca2b520a89eb654542bd44d2c3eaaa969c735ceb5f052b1ed704

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 910773ec64c0b3330d2d1790eaa74db54a45e9e6e6ca765554dc424232f585a9
```

**Decision**: End-to-end plan covering all 25 open issues in four gated
milestones: M0 post-overhaul re-baseline (hard gate), M1 stabilize (CI gate +
verify-then-close of 9 delivered issues + reference repair), M2 evidence
(docs 30/31/32, audit slice 7B schema/fixture reconciliation, schema-driven
validator, calibration generator), M3 doctrine wave and ecosystem
(#6→#7→#18→#26/#27→#28→#30, then #5/#8; #19/#29 stay gated). Five Governor
decisions flagged as Open Questions with recommended defaults. Plan removes
three identified braids (tracker/delivery state, identity/ordering,
schema/validator) before adding new doctrine. No repository content modified —
observational directive honored; execution awaits Governor approval and
Codex overhaul completion.

---

### Entry #3: MILESTONES 0-2 EXECUTED

**Timestamp**: 2026-08-10T23:30:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256(RESEARCH_BRIEF.md with Milestone 0 delta)
= 8f2c899c77e4e5b09eaad3434aa2228a987a2d145ba8042654fcbbaaeafaefbe
```

**Previous Hash**: 910773ec64c0b3330d2d1790eaa74db54a45e9e6e6ca765554dc424232f585a9

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 77ae4f73a32bd51d0f1dfca9d4a20b62b80a2d033b7a3ab54926498fe8250af3
```

**Decision**: Governor authorized execution ("entirely up to you... proceed").
Milestone 0: overhaul landed with no renames; identity path map; all validators
green on merged tree. Milestone 1: 13 delivered issues verified against
acceptance criteria by independent verification pass (6 clean, 7 with narrow
residual gaps consolidated into follow-up issue #43); stale references repaired
in 8 open issue bodies (deliverables reassigned to free slots docs/33-39);
CI step-summary gap fixed. Milestone 2: calibration report generator delivered
(#4) with input schema, worked example, and CI sync check. Remaining scope:
Milestone 3 doctrine wave (#6 -> #7 -> #18 -> #26/#27 -> #28 -> #30),
cross-repo (#5, #8), gated futures (#19, #29). Per Governor directive,
commit messages and issue comments carry no attribution trailers.

---

### Entry #4: MILESTONE 3 EXECUTED — DOCTRINE WAVE COMPLETE

**Timestamp**: 2026-08-11T00:45:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("milestone-3:" + git tree hash of docs/ at HEAD)
= 2e830c86d818f2e6e947d754328709f9e369e6cb94a67755710ae641052ef398
(docs tree: 9055f56e2969bb4916462f1372e17b836249801b)
```

**Previous Hash**: 77ae4f73a32bd51d0f1dfca9d4a20b62b80a2d033b7a3ab54926498fe8250af3

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 43f3936ffe183f5a536ba86edbc79519cf5c6f733027765a8571b0f5e3fb448c
```

**Decision**: Milestone 3 executed in dependency order per the plan. Delivered
and closed: #6 (docs/33 PAMA decision table), #7 (docs/34 adapter contracts),
#18 (docs/35 interoperability profiles), #26 (docs/36 policy-as-memory),
#27 (docs/37 memory economics), #28 (docs/38 correction UX contract),
#8 (docs/39 ownership map, declared-not-verified), #30
(docs/profiles/durable-decision-memory-profile), #19 and #29 (gated future
notes, gates cleared by #18 and the contracts slice). All 14 previously
verified issues also closed with delivery evidence. Backlog reduced from 25
open issues to 2: #5 (blocked on external repository access) and #43
(consolidated residual gaps). All validators green at every commit; commit
messages and issue comments carry no attribution trailers per Governor
directive.

---

### Entry #5: EXTERNAL ADVISORY ASSESSED AND ACTIONED

**Timestamp**: 2026-08-11T05:30:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("advisory-slice:" + git tree hash of docs/ at HEAD)
= 9786a6ffada43b961fb5d918287bcd30f9182087db5cf9722955ed0cbcfd63b5
(docs tree: 740a8aa93c1478b35adce84bb994b0d7cc9c3e1e)
```

**Previous Hash**: 43f3936ffe183f5a536ba86edbc79519cf5c6f733027765a8571b0f5e3fb448c

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= b37f4b80a93ccd115a684e13a337d003b5ae9bcbc3a8c44bb38db1ea3e9cc5b1
```

**Decision**: Five-item external advisory (non-binding) assessed against
repository reality after upstream commits 217a74e and ec73edd elevated PAMA to
native doctrine. Item 1 (executable harness): accepted, scoped as issue #48
with a thin system-under-test interface, toy implementation, multi-trial
stochastic support, and a second-phase external substrate bridge. Item 2
(proven-vs-aspirational matrix): already delivered by docs/39, further
strengthened upstream by the doctrine-owned status vocabulary; no action.
Item 3 (verification economics): accepted; verification-budget section added
to docs/37 with sufficiency floors, cost attribution, bounded deferral, and
three new metrics. Item 4 (promotion-queue flooding): accepted; threat 19
added to docs/15 with controls and a conformance case. Item 5 (inter-system
authority conflict): advisory arrived truncated; inferable core implemented in
docs/35 (authority does not transit seams, singular ownership, fail-closed
competing claims, per-hop receipts, recognition-not-transfer certification).
Branch restarted from post-merge main per merged-PR protocol; all six
validators green; stealth maintained.

---

### Entry #6: P0 EVIDENCE FLOOR CLOSED (#43)

**Timestamp**: 2026-08-11T07:00:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("evidence-floor:" + git tree hash at HEAD)
= 76ea088221889f59eafe9acd06a2fd757560765170f7d92ae874924c80ef09ce
(tree: b24bb9ac75977a76e7d352928f81f3fa785212c8)
```

**Previous Hash**: b37f4b80a93ccd115a684e13a337d003b5ae9bcbc3a8c44bb38db1ea3e9cc5b1

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= ade0126711cd9b4195b850386a82a832f997075fba0b4ce5c3509dc60c740472
```

**Decision**: Executed P0 of the runtime-evidence roadmap. All seven #43 gaps
closed at b2159ca on the designated branch, incorporating the
agent/close-evidence-gaps-43 starter commit by merge: 25 versioned fixtures
with validator enforcement and documented rules; governed-promotion audit-trace
fixture with five schema-validated correlated events; doc 32 four-stratum
scorecard with disqualifying hard gates and trap-class severity; twelve
canonical ADR backlinks; docs 15/19 governance cross-links with PAMA named;
CONTRIBUTING validator dependency split; doc 27 seven-schema inventory.
Full validation gate green at branch head. #43 left open for merge-time
closure per the branch owner's no-partial-satisfaction stance. #48 cross-linked
into #46 as the P3 slice with Graphiti-first sequencing note. Roadmap P1-P10
assessed and endorsed; P1 (#5) requires external repository access.

---

### Entry #7: P2 SUBSTRATE MAPPING AND ORGANIZATION TRANSFER

**Timestamp**: 2026-08-11T08:30:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("org-transfer:" + git tree hash at HEAD)
= c1744ba6d1b1f97d5c03e69ecaf0ab48c00852820e942f0649e2bba02a1f166b
```

**Previous Hash**: ade0126711cd9b4195b850386a82a832f997075fba0b4ce5c3509dc60c740472

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 9be289079d826c6127eb8e6e912badd553101fc51a11a6bc757ec2d72e70149f
```

**Decision**: Two changes recorded together.

P2 executed: runtime-evidence program opened under docs/programs/, and the
first substrate (Graphiti, graphiti-core 0.29.3) mapped across the fourteen
conformance concerns from its public source tree, registered in the source
registry as an external comparator under independent synthesis. Mapping is
documentation-verified only and explicitly constitutes no runtime evidence.
Load-bearing findings: ordinary ingestion is LLM-mediated and therefore an
estimator that may propose but must not commit; no authorization layer exists;
tenancy is a permissive query-filter convention; deletion is physical without
tombstoning; decision reasoning is discarded. The substrate's no-LLM
direct-write paths are the seam that makes a governed wrapper viable. Five
questions recorded as requiring an executed probe rather than inferred.

Repository transferred to MythologIQ-Labs-LLC/agent-memory for public
distribution. Thirteen active owner references updated across citation
metadata, README badge, governance canonical-upstream statement, the two
prescribed cross-repo backlink strings, and seven schema $id identifiers;
git remote repointed. Four references deliberately preserved as historical
anchors: the point-in-time research brief target, this ledger's own header,
and the pinned baseline audit anchor in doc 25, which records the repository
and commit the first audit pass actually ran against. Rewriting those would
falsify history to flatter present naming. Schema $id identity changed at
the pre-public-release moment, when no external consumer can have pinned the
prior identifiers; this is a schema-registry identity event and is flagged
for Governor review rather than treated as cosmetic.

---

### Entry #8: P3 MINIMAL GOVERNED ADAPTER

**Timestamp**: 2026-08-11T10:00:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("p3-adapter:" + git tree hash at parent commit)
= 60bf182602d00de902e95c7e846e6e3d2fb738366556da1ec2d3cd9fa6d86701
```

**Previous Hash**: 9be289079d826c6127eb8e6e912badd553101fc51a11a6bc757ec2d72e70149f

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= f46b0871cdf68cfa976a359ccd65888380806a7ebe86725939982d750fae4622
```

**Decision**: P3 executed. A minimal governed adapter under reference/ implements
the full path from evidence through proposal, authority envelope, permitted
action set, selected action, substrate mutation, decision receipt, retrieval
candidate, and governed admission. Twelve paths execute in CI: one positive and
eleven negative, exceeding the five-negative exit gate. Artifacts are emitted
against four canonical repository schemas rather than invented shapes, and the
selected-action membership rule the receipt schema delegates to consumers is
enforced in code.

The substrate is a model, not a running instance, and deliberately reproduces
the mapped substrate's verified permissiveness: opaque identity, unfiltered
partition default, physical deletion without tombstones, and no authority check
anywhere. Several tests assert both that the substrate would misbehave and that
the adapter refuses regardless, so the governance layer is demonstrated to be
load-bearing rather than merely present.

Two policy behaviors were discovered by execution rather than assumed. Permanent
deletion cannot commit autonomously at any risk class, which failed an initial
test that had assumed otherwise; the test was wrong and the doctrine was right.
Pruning and permanent deletion were consequently separated so pruning tombstones
and removes from recall while content stays recoverable.

Claims are bounded. The emitted conformance report declares level 0 with three
stated exemptions, because execution against a substrate model is not runtime
evidence under the program's own rules. Four limitations are documented rather
than left to be discovered, including that substrate binding remains unimplemented.
That binding is where runtime evidence begins and is the next slice.

---

### Entry #9: FIRST RUNTIME EVIDENCE AGAINST A REAL SUBSTRATE

**Timestamp**: 2026-08-11T11:30:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("p3-runtime-evidence:" + git tree hash at parent commit)
= 26960978cf3dc1529242f73ea913103e12350acfbfd49337b7bcc2b87579828f
```

**Previous Hash**: f46b0871cdf68cfa976a359ccd65888380806a7ebe86725939982d750fae4622

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= f00fff3fc0a23982dff9ddb18578cc7f83c0f742fd6dac752328aa4c756c56d6
```

**Decision**: The Governor asked whether the substrate binding could be
established in a hosted development container, and to defer otherwise.
Investigation found it unnecessary: the binding runs in the existing session.
Container runtime is unavailable, but the substrate ships an embedded backend
requiring no server, and the mapping's central architectural claim held under
test, so no credentials were required either.

Nineteen paths now execute, seven of them against graphiti-core 0.29.3 over an
embedded graph database with no LLM, no embedder, no API key, and no server.
This is the program's first runtime evidence rather than precondition work.

Execution verified three facts source reading had not established. The no-LLM
write path works end to end when pre-computed vectors are supplied. The
library's top-level facade force-constructs a provider client even when every
operation in use is provider-free and fails without credentials, so a governed
adapter must bind at driver level; this is an integration constraint, not a
documentation nuance. An empty partition signals absence by raising rather than
returning an empty result. Open question 3 is partially resolved: invalidated
edges are returned by the partition query, so an adapter that fails to filter
them would admit superseded facts as current.

Claims remain bounded. Conformance level 0 is still declared, now with five
stated exemptions, because the doctrine fixture corpus is not driven through
the adapter and levels require it. The backend used is deprecated upstream and
that is declared rather than hidden; no governance behavior under test depends
on the backend choice. Substrate tests skip cleanly when the library is absent,
so the standard-library gate remains runnable everywhere, and CI installs the
substrate with continue-on-error so runtime evidence never becomes a hard
dependency of the doctrine gate.

---

### Entry #10: FIXTURE CORPUS DRIVEN THROUGH THE ADAPTER

**Timestamp**: 2026-08-11T12:45:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("fixture-corpus:" + git tree hash at parent commit)
= d597b428902ec7461b60401442368bf9a5e72548c6b8b2d74f0f60e3b5beca47
```

**Previous Hash**: f00fff3fc0a23982dff9ddb18578cc7f83c0f742fd6dac752328aa4c756c56d6

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= a4a7d8da4f94664ed44bc3357bc18150995cf30df28ebcda62794df9d2c75d96
```

**Decision**: Governor directed that substrate CI remain optional and that the
fixture corpus be driven through the adapter. Both done.

All 25 doctrine fixtures now execute against the adapter's own authority
enforcement rule, the same function the write path uses, rather than a
reimplementation of it. Seventeen carry a declared authority envelope. Five
checks run per envelope: permitted and prohibited sets disjoint, declared
selection is a member of the permitted set, declared selection is not
prohibited, every prohibited action is actively refused, and a fixture
expecting no crystallization does not permit one. All 25 pass.

A first-run pass was treated as suspicious rather than satisfying. The checker
was mutation-tested against four deliberately corrupted envelopes and detected
every one; those mutations are now permanent tests, so a check that silently
stops being able to fail will itself fail. This is what distinguishes corpus
evidence from a suite agreeing with its own author: the fixtures were written
to describe doctrine, not to satisfy this implementation.

Conformance level remains 0, now for a sharper reason than before. The doc 06
levels are cumulative and this adapter implements neither decay nor calibrated
saturation, so levels 2 and 3 are unmet however well enforcement performs.
Nine exemptions are stated in the report. Corpus coverage is explicitly
envelope enforcement, not full scenario execution.

Substrate installation in CI remains best-effort per Governor direction, so
runtime evidence never becomes a hard dependency of the standard-library
doctrine gate. Total: 25 executable paths plus 25 corpus fixtures, 50 trials.

---

### Entry #11: STOCHASTIC CONTAINMENT AND WIKI PARALLEL TRACK

**Timestamp**: 2026-08-11T14:00:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("stochastic-containment:" + git tree hash at parent commit)
= e6ba10acdaab966d7d77da0ce3de5132fef5433c48c5c67ee2eb4d0c06f8f42c
```

**Previous Hash**: a4a7d8da4f94664ed44bc3357bc18150995cf30df28ebcda62794df9d2c75d96

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= eaeaf16e8189bd61ba2620ef6baac7fc6921a77c47c8a21d65ba3d905f9d363b
```

**Decision**: Branch rebased onto post-transfer main, which introduced the
wiki-src tree, a wiki link validator, and hardened issue intake. Eleven
recurring workflow conflicts were resolved by keeping both the extended
documentation link list and the new wiki validation step.

Stochastic containment implemented, closing the last outstanding criterion of
issue #48. Selection is now delegated to a selector abstraction with
deterministic and seeded stochastic implementations, and the adapter treats
every selector as untrusted: whatever a selector returns is re-checked against
the permitted set before use, with violations recorded and failed closed to a
deferral. Randomness proposes; it does not authorize.

Three properties are asserted together rather than only the flattering one.
Safety: across 500 sampled trials no selection escapes the envelope, reported
through the standardized stochastic_action_set_violation_rate metric at 0.0.
Liveness: the selector demonstrably varies across three distinct actions, so
the safety assertion is not vacuous. Containment under hostility: a selector
deliberately returning a prohibited action is contained by the adapter and the
violation recorded, proving the guarantee comes from the gate rather than the
selector's good behavior. The harness gained the --trials flag doc 06 sketched.

Wiki parallel track opened per Governor direction. A Runtime-Evidence page was
added following the established wiki conventions: reader-facing, no wiki-only
doctrine, canonical links back to the repository. Its "what this still does not
prove" section is deliberately as prominent as its claims, since a public
surface is where overclaiming does the most damage. Neighbouring pages were
corrected: the conformance page's stale fixture count and its list of
undemonstrated properties, several of which are now demonstrated and several of
which are not. Active fixture counts in the README were updated from 24 to 25;
the two audit records citing 24 were left untouched because they correctly
describe the branch they audited.

---

### Entry #12: SESSION SEAL

**Timestamp**: 2026-08-11T15:00:00Z
**Phase**: SUBSTANTIATE
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("session-close:" + git tree hash at parent commit)
= d2c7129d4ace95e9a7f7c49b3df1233188e7089fcc4c32e85ab24b32cb34b91c
```

**Previous Hash**: eaeaf16e8189bd61ba2620ef6baac7fc6921a77c47c8a21d65ba3d905f9d363b

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 32a674bb717c71207f75f161d3dc28055bf059e95b3815694ff571b1357020c8
```

**Decision**: Session sealed. PR #58 merged to main at 1fae404, carrying twelve
commits: the evidence floor, the runtime-evidence program, the first substrate
capability mapping, the governed reference adapter with runtime evidence, the
fixture corpus driven through enforcement, stochastic containment, the
organization transfer, and the first wiki evidence page.

Backlog moved from 25 open issues to 2. Closed this session with delivery
evidence: 23 doctrine and tooling issues, plus #43 (evidence floor) and #48
(conformance harness). Remaining: #5, blocked on external repository access,
and #46, the runtime-evidence program umbrella whose P4 and later slices are
unstarted.

Two errors were made and corrected rather than concealed. Commit author and
committer fields carried a model identity through eleven commits despite the
standing stealth directive; only message trailers had been stripped. Identities
were rewritten to the repository owner, local configuration corrected, and a
server-appended attribution footer was removed from the pull request body
before merge. Separately, compiled Python bytecode was swept into the
repository by an overly broad add and merged; a .gitignore was added and the
twelve cache files untracked in a follow-up.

Verification at seal: 25 fixtures, 7 schemas, 25 memory units, 5 audit events,
8 source-rights records, doctrine boundaries, 17 wiki files, 31 reference
tests, and a 200-trial stochastic sweep, all green on main.

Standing claims remain bounded. No conformance level is claimed, and ADR-020
remains Proposed pending concurrency behavior, deletion-propagation
measurement, and evidence across a wider surface than one reference adapter.
The wiki source tree is ahead of the published wiki, which remains unpublished
pending Governor direction.

---

### Entry #13: P4 EXECUTED — CANONICAL AND DERIVED STATE

**Timestamp**: 2026-08-11T16:30:00Z
**Phase**: IMPLEMENT
**Author**: Governor
**Risk Grade**: L1

**Content Hash**:
```
SHA256("p4-derived-state:" + git tree hash at parent commit)
= 48d657dff24782adbecfe76e9da4277be34f4491084ac937d4771141d1b46f80
```

**Previous Hash**: 32a674bb717c71207f75f161d3dc28055bf059e95b3815694ff571b1357020c8

**Chain Hash**:
```
SHA256(content_hash + previous_hash)
= 25fe3794d02da6bfe553f605a0a7488fdf7de424529e82f43d3482c705b4e2f3
```

**Decision**: P4 executed against the architectural design authored upstream.
The division of labor is explicit and preserved: the canonical-and-derived-state
design spike, its three-tier model, its freshness relation, its residue
partition, and its seven-item evidence bar were specified elsewhere. This work
implements that specification and does not amend its argument.

All seven bar items now execute in CI. A tier-3 declaration surface records
basis at build time. Freshness is computed as a relation over recorded basis
versus current canonical state, never set by a flag, with residual dominating
stale because they carry different authorities. Correction supersedes
content-bearing projections without erasing the version a prior decision used.
Purge traverses the transitive derivation closure including retained superseded
versions, honoring deletion-dominates-correction. An independent sweep
re-derives residual status rather than asking the purge whether it finished.
Estimator-mediated rebuild is refused without an authority decision, while
deterministic reproducible rebuild is categorically authorized.

Items 4, 5, and 6 were called out upstream as the ones a persuasive
demonstration would skip. Each carries a paired negative test: a deliberate
one-hop purge must be caught by the sweep, an unauthorized purge must not run,
and staleness alone must not commit estimator content. Two implementation bugs
were found by those negative tests rather than by inspection: a dropped
projection was not recorded as purged, so dependents read as merely stale
instead of residual; and a refused purge recorded a no-action sentinel while
the envelope still permitted deferrals.

A review-satisfaction path was added to the policy so an externally approved
purge is reachable at all. Review is discharged only by an approval record from
someone other than the proposer, block remains absorbing, and self-approval
cannot buy past review. This also closes a previously documented limitation.

Reported metrics: deletion_residue_rate 0.0 with an empty undeclared cell, and
stochastic_action_set_violation_rate 0.0. Forty-six tests plus sweeps.
Conformance level remains 0 and ADR-020 remains Proposed: this discharges one
validation item, and clearing one bar is not acceptance.
