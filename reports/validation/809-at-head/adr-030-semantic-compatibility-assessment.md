# ADR-030 semantic-compatibility assessment for the #809 changes (contract `1.8.0` provisional)

Requested by the owner's checkpoint on PR #815 (review 5527842455): "Perform an ADR-030
semantic-compatibility assessment for existing `1.6.0` envelopes and externally observable
results; explain whether these changes require a new major boundary or revised compatibility
state. Do not stamp old semantics `current` by minor-version number alone. Serialization success
is not semantic compatibility." This is an assessment with a recommendation; the version decision
is the owner's. Head assessed: `6be46927` (protected tree `6f4205e0`, repair commit `b932bd2f`).

## 1. The two compatibility mechanisms the runtime has today

| mechanism | what it binds | states | semantic? |
|---|---|---|---|
| `contract.compatibility(envelope)` (`api/contract.py`) | the envelope's `contract_version` against `CONTRACT_VERSION`: same major and minor ≤ ours → `current`; newer minor → `migration_required`; other major → `incompatible`; unparsable → `unknown` | ADR-030's four | **no**: it is a serialization/field-set statement ("this implementation understands every envelope of an older minor") |
| `evaluate_policy_projection_compatibility` (`memory/policy_projection_compatibility.py`) | a derived projection against an exact external temporal/authorization contract: projection identity/version, source currentness, domain-schema identity, target policy identity, evaluated context identity, isolation evidence | currentness `current / revalidation_required / unknown`; semantic `compatible / migration_required / incompatible / unknown` | **yes**, but only for the identities it is given; it carries no identity for the runtime's own derivation/deletion semantics |

Every public result carries `contract_version: 1.8.0` and `compatibility: <state of the request envelope>`. A `1.6.0` envelope reads `current` on this head, exactly as it did on the published v7 (`1.6.0`) runtime, for #786 and #809 alike.

## 2. Externally observable differences for a `1.6.0` caller, v7 published (`16a248b1`) → this head

| change | observable through | kind | status |
|---|---|---|---|
| #786 write-target authority: `remember` over a live head outside the writer's scope refuses `target_unavailable`; `correct` / `forget` / `dispute` of such a head read `fact_not_found`; a re-creation's receipt reads `v0 -> v1` | new refusal tokens on operations that previously committed; generation-relative versions | behavioural, refusal-token level | owner adopted `1.8.0` for it (PR #805 checkpoint) |
| #809 new writes: a derivation citing a reference outside the writer's scope is **admitted** (was withheld `derived_from_tombstoned_source` once the cited generation was deleted), its `history` is complete (was scrubbed), `write_semantics` is a document (was `null`), a dispute citing such a reference stays in the citer's history (was scrubbed); the owner's `undeclared_residue` no longer lists foreign citers | admission, history, write semantics, dispute, revocation audit | semantic: which cited references carry deletion taint | this branch; no envelope or token changes |
| #809 reader-aware withholding: a deleted-generation identifier is withheld only from a reader whose own context could have read that generation; a co-holder of a shared memory meets another holder's cited identifier as an opaque string where it was previously scrubbed | shared-memory `history` | semantic: public projection | this branch |
| late binding withdrawn (owner's ruling): a forward citation of an id that does not exist at commit never binds, so a forward note stays admitted after the id materialises as a derivation of a deleted source | admission | semantic: deletion-completeness guarantee narrowed | this branch, accepted by the owner as a candidate semantic change |
| legacy stores (preregistered, not implemented): facts persisted before #809 keep the old rule until upgraded; `legacy_upgrade_status()` / `upgrade_canonical_derivation()`; quarantined edges keep the old rule indefinitely, store `legacy_unqualified` | new facade operations (additive); per-store status | additive API + semantic for upgraded rows | `reports/validation/809-legacy-upgrade/decision.PREREGISTERED.md` |
| result envelopes, schemas, refusal vocabulary | unchanged by #809 (no field added or removed; the `canonical_derivation` attribute is a persisted fact attribute, not a public projection field: the DSL/3 replay's byte-level shape equalities would have exposed it) | — | the code review at this head is asked to confirm no projection serves the attribute |

## 3. Assessment under ADR-030

1. **Serialization**: a `1.6.0` envelope parses, validates and receives a `1.8.0` result validated against the same schema. By the number rule it is `current`. ADR-030 says that is not the question.
2. **Semantics**: the meaning of "admitted" and "withheld" for a caller's own derivations changed twice on this stack (#786 narrowed what a writer may target; #809 narrowed what a citation binds and withdrew late binding). A consumer that encoded the pre-#809 rule, in either direction, observes different results for identical envelopes:
   - a consumer relying on **tenant-wide deletion completeness whoever cites** (the #776 reading) now sees a foreign citer admitted. This is the narrowing the owner ruled on; it is a security-property change, not a regression of the public shape, but it is a change of meaning.
   - a consumer that read the withheld/admitted state of its own derivation **as information about another scope** (the oracle) loses that signal; that is the fix.
   - a consumer that relied on a **forward note becoming refused** once its cited id materialised (#776 late binding) no longer gets that; the owner accepted this withdrawal explicitly.
3. **Temporal/authorization consumers (ADR-030's subject)**: a projection built under the old rule binds "source semantics" that no longer hold. Per ADR-030 ("changed semantics require new evidence; a rebuilt projection after migration receives a new identity") such projections should read `migration_required` or `revalidation_required`. Today the evaluator cannot know, because the runtime declares no identity for its derivation/deletion semantics; for those projections the honest state is `unknown`, and ADR-030 says `unknown` is not current.
4. **Major boundary?** ADR-030 and the versioned schemas tie `incompatible` to a different major, i.e. to envelopes this implementation cannot understand. Nothing here is of that kind: every `1.0.0`–`1.8.0` envelope is understood and served. Declaring a major boundary would force every existing caller into `incompatible` to announce a change they can neither see in the schema nor adapt to by changing a field. That is the wrong instrument. The right instrument is an explicit, declared **semantics identity** that results, posture and the projection evaluator carry, so the change is visible and bindable rather than stamped `current` by number.

## 4. Recommendation (the owner's decision)

- **R1. Declare a derivation-semantics identity** and make it part of the baseline identity: `identity.derivation_semantics = "writer-eligible-at-commit/1"` as an identity delta of the cumulative v6 → v8 declaration (the register tooling already compares identity deltas), surfaced in `posture` / runtime identity, and accepted by `evaluate_policy_projection_compatibility` as a `source_semantics` identity so a projection bound under an earlier identity reads `migration_required` and one that did not bind it reads `unknown`. Additive; no envelope changes.
- **R2. Version: minor bump to `1.9.0`**, not a major boundary. The bump records that semantics changed within an understood schema (ADR-030's "changed semantics require new evidence"); `1.6.0`–`1.8.0` envelopes stay `current` for serialization, and semantic compatibility is carried by R1, documented in docs/44 beside the compatibility table with the sentence the owner used: serialization success is not semantic compatibility. Keep `1.8.0` only if the owner prefers to treat #809 as a correction of #786's own semantics within the same adopted version; in that case R1 is still required.
- **R3. Store-level compatibility**: `legacy_pending` and `legacy_unqualified` stores carry the old rule for some or all facts; posture should report the status, and the activation rule in the preregistered decision applies (no v8 activation over such stores).
- **R4. Not recommended**: a `2.0.0` boundary (every current caller becomes `incompatible` for a change it cannot adapt to by schema), or a `compatibility()` that returns `migration_required` for older envelopes by number alone (it would mark serialization-compatible envelopes as needing a migration that does not exist).

## 5. Statuses

Assessment: WRITTEN (this record). Decision: the owner's. Implementation of R1–R3: not started; if adopted, R1 changes `api/contract.py` / posture (protected) and the declaration's identity deltas, and re-runs the ladder at that head.
