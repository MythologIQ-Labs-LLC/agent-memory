# Source Rights and Reuse Policy

## Purpose

Agent Memory is intended to be evidence-informed, publicly traceable, and safe to reuse without quietly importing protected expression from source material.

This policy governs how external and internal source material may be cited, summarized, adapted, quoted, copied, or incorporated into repository doctrine, examples, diagrams, schemas, fixtures, code, and documentation.

The core rule is simple:

> **Public accessibility does not imply reuse permission. Citation does not imply a license.**

When reuse rights are absent, unclear, unnecessary, or disproportionate to the value of the copied expression, Agent Memory should link to the source and independently synthesize the underlying ideas rather than reproduce protected expression.

This is a repository governance policy, not a substitute for legal advice.

## Native doctrine versus external source material

Agent Memory distinguishes **native contributor-authored doctrine** from **external source material**.

Native doctrine does not need to be forced into the external source registry merely to demonstrate provenance. Its canonical location and authorship should be recorded in the doctrine tree itself.

For native doctrine:

- record the contributor or originator when provenance matters;
- keep the canonical doctrine in this repository;
- do not invent an external locator or external reuse license;
- separately govern any third-party research, standards text, diagrams, code, or other expression incorporated into or used to support that doctrine.

**Proportional Adaptive Mutation Authority (PAMA) is native Agent Memory doctrine authored by Kevin R. Knapp.** Its canonical foundation is [`pama/README.md`](pama/README.md). External OWASP, NIST, regulatory, research, or implementation references may support, challenge, benchmark, or align with PAMA, but they are not the source of PAMA.

This distinction matters because a contributor-authored framework may itself cite external standards. The presence of those references does not transfer authorship of the framework to the standards body, nor does contributor authorship grant permission to copy protected expression from the referenced standards.

## Same-owner first-party ancestry

Agent Memory also distinguishes **same-owner first-party implementation ancestry** from genuinely external material.

Under [`ADR-036`](adr/ADR-036-same-owner-components-are-first-party-modules.md), owner-controlled material from CodeGenome, EvolveAI, COREFORGE, FailSafe, GG-CORE, and other explicitly mapped same-owner repositories may be adopted directly into Agent Memory. The adoption basis is common ownership, not a public repository license and not a provider-attribution requirement.

This rule has narrow boundaries:

- common ownership applies only to material controlled by the common owner;
- third-party dependencies, contributions, issue comments, attachments, trademarks, datasets, or other separately owned material retain their own rights and obligations;
- a public MIT or Apache-2.0 license may remain useful distribution metadata for external licensees even when it is not Agent Memory's internal adoption basis;
- private same-owner access does not imply permission to publish private source, screenshots, URLs, credentials, or confidential implementation detail;
- lineage should remain recorded because provenance has engineering value, not because the originating repository must remain a runtime provider.

## Default source treatment

Unless a stronger reuse basis has been verified and recorded, treat **external** material as:

```text
LINKABLE
The source may be identified and linked when the locator is lawful and public.

CITABLE
Facts, findings, ideas, mechanisms, and claims may be discussed with attribution and appropriate evidence discipline.

SYNTHESIS-ONLY
The repository should express the idea independently rather than copy distinctive prose, diagrams, tables, screenshots, or code.
```

Unknown external rights status defaults to **citation and independent synthesis only**.

## Reuse modes

Every materially relevant registered source should be classifiable as one of these modes:

| Mode | Meaning | Default posture |
|---|---|---|
| `citation_only` | Link or cite the source without importing protected expression | Safe default |
| `independent_synthesis` | Explain facts, ideas, findings, or mechanisms in original repository language | Preferred default for external sources |
| `same_owner_adoption` | Adopt owner-controlled material from an explicitly mapped same-owner first-party source under ADR-036 | Direct adoption permitted; preserve lineage and separately honor third-party constraints |
| `author_originated` | Material originated with a repository contributor who is asserting authorship/provenance outside or before the current repository | May be reused subject to contributor authority and any third-party constraints |
| `licensed_reuse` | Copy or adapt material under a verified license | License obligations must be satisfied |
| `permission_granted` | Copy or adapt under explicit permission outside a standard license | Permission evidence must be retained |

`licensed_reuse`, `permission_granted`, and `same_owner_adoption` require an explicit reuse basis in the source registry. A record using `same_owner_adoption` must use `rights_status = same_owner_first_party`; the schema enforces that pairing.

Native doctrine maintained directly in Agent Memory is not required to have a source-registry entry unless there is a separate material-reuse reason to create one.

## What may be linked

When a named external source has a lawful, stable public locator, link the most specific authoritative artifact available.

Prefer, in order:

1. originating paper, issue, specification, or design document
2. canonical implementation file or repository
3. official project documentation
4. stable public archive
5. project homepage only when no more precise source exists

A related public artifact must not be presented as the provenance source merely because the canonical source is private.

## Repository licenses do not automatically govern everything nearby

A repository-level software or documentation license must not automatically be extended to:

- third-party issue comments
- discussion posts
- linked papers
- screenshots
- user-uploaded attachments
- embedded third-party diagrams
- material copied into an issue from elsewhere
- external datasets
- trademarks or logos

The rights status of the actual material being reused matters.

For example, an MIT-licensed repository may contain an issue comment written by a third party. The repository license alone is not sufficient evidence that the third party's comment prose is MIT-licensed. The safe default is to link the comment and independently summarize its ideas.

For a same-owner repository covered by ADR-036, the public repository license is not the source of the owner's authority to adopt its own owner-controlled work into Agent Memory. That does not convert third-party material in the repository into first-party material.

## Source-class rules

### Research papers and books

- Link DOI, publisher, PubMed, arXiv, author manuscript, or lawful open archive where available.
- Record findings and claims in original repository language.
- Do not reproduce substantial prose, figures, tables, or diagrams unless the rights basis permits it.
- Paywalled access does not create reuse rights.
- Open access is not itself a license statement; verify the specific license before reuse.

### GitHub repositories

- Verify the repository license before copying code, documentation, examples, diagrams, or other expressive material from a genuinely external repository.
- Preserve attribution, license text, notices, modification notices, or other obligations when the applicable license requires them.
- A genuinely external repository with no verified license is `citation_only` / `independent_synthesis` by default.
- For repositories explicitly mapped as same-owner under ADR-036, use `same_owner_first_party` / `same_owner_adoption` for owner-controlled material and retain the public license as distribution metadata rather than pretending it is the internal adoption grant.
- Do not use same-owner classification to launder separately owned third-party material.

### Issues, discussions, and comments

- Link directly when public and material to provenance.
- Treat third-party prose as `citation_only` / `independent_synthesis` unless explicit reuse rights are established.
- Record contributor-originated material as `author_originated` only when authorship/provenance is known and the contributor has authority to reuse it.

### Private sources

- Private accessibility is not publication permission.
- Do not expose private URLs, confidential text, screenshots, or implementation details merely to make public provenance look complete.
- A public successor or related project may be identified only when that relationship is actually evidenced; it must never be substituted for the private provenance source.
- A private project should not appear in active Agent Memory provenance surfaces merely because it is conceptually adjacent. It should add a specific, articulable implementation or evidence value.
- Same-owner private material may be adopted internally under ADR-036 when owner-controlled, but that adoption right does not itself authorize public disclosure of the private source.

### Code

- Do not copy genuinely external source code unless a compatible license or explicit permission is verified.
- Preserve required copyright notices, license text, NOTICE files, attribution, and modification notices when the applicable external license requires them.
- Owner-controlled code from an ADR-036 same-owner source may be adopted under `same_owner_adoption`; preserve engineering lineage while separately screening for third-party code and obligations.
- Independent reimplementation from public ideas or interfaces should be documented as such when provenance matters.

### Diagrams, figures, screenshots, and tables

- Assume these contain protectable expression unless verified otherwise.
- Prefer an original diagram that communicates independently synthesized doctrine.
- Do not redraw a source figure so closely that the new artifact is merely a cosmetic copy.

## Facts, ideas, and expression

Agent Memory deliberately distinguishes concepts from the specific expression used to communicate them.

Examples of material generally suitable for independent synthesis include:

- an architectural idea
- a mathematical relationship
- a reported experimental finding
- a benchmark result
- an API behavior
- a lifecycle concept
- a governance requirement

The repository should not copy distinctive source language merely because the underlying idea may be discussed.

## Provenance claims versus legal exclusivity

The repository may record who originated a contribution, term, framing, implementation, or proposal when the provenance is supported.

An authorship/provenance statement is not automatically a claim that the underlying idea, method, or short phrase is exclusively protectable under copyright, trademark, patent, or another body of law.

For UOR Framework issue #2, the thermodynamic memory-lifecycle proposal was opened by Kevin R. Knapp. The **"thermodynamic ground state" framing as used in that proposal is recorded in Agent Memory as a Kevin R. Knapp contribution**. This is a provenance record. It does not depend on treating the phrase itself as an exclusively protectable asset.

PAMA is stronger than a provenance note attached to an external source: it is a contributor-authored framework maintained as native Agent Memory doctrine. Its external alignment references retain their own rights and citation requirements.

## Material-reuse record

When external source material is materially reused rather than merely cited or independently synthesized, or when same-owner first-party material is adopted and lineage materially matters, record at least:

```text
source_ref
public_url
source_type
copyright_owner_or_originator
license_or_rights_status
license_url_or_permission_ref
reuse_mode
material_reused
attribution_required
notice_required
modification_notice_required
reuse_basis
verified_at
```

Machine-readable external/material-reuse and same-owner ancestry records live in `sources/source-registry.json` and are validated against `schemas/source-record.schema.json`.

## Hard gates

A source record must not use `licensed_reuse`, `permission_granted`, or `same_owner_adoption` unless it records a non-empty `reuse_basis`.

A source using `same_owner_adoption` must be explicitly classified `same_owner_first_party` and must not use common ownership to authorize third-party material.

A source with `rights_status = unknown` must not authorize copied or adapted material.

A source with no verified license is not open source merely because it is publicly readable.

A source marked private must not receive a fabricated public provenance link.

A project successor must not be represented as the originating source, and a related project must not be labeled a successor without evidence.

Native contributor-authored doctrine must not be mislabeled as an unresolved external source merely because it previously existed in another document or repository context.

## Review checklist

Before merging sourced material, reviewers should ask:

- Is this source being linked, summarized, quoted, adapted, copied, or adopted from same-owner ancestry?
- Is the most authoritative source linked when a public locator is appropriate?
- Is the license, ownership, authorship, or permission basis applicable to the actual material, not merely the surrounding repository?
- For external material, are license and NOTICE obligations satisfied?
- For same-owner material, is the common-ownership determination explicit, and have separately owned third-party materials been excluded or handled independently?
- Could the same value from an external source be achieved through independent synthesis instead?
- Is any private or confidential provenance being exposed?
- Is contributor-originated material correctly attributed?
- Are we recording provenance without overstating legal exclusivity?
- Is this actually an external source, same-owner implementation ancestry, or native contributor-authored doctrine?
- Does a named private or external project add specific value here, or is it merely adjacent?

When the answer is uncertain, prefer citation and independent synthesis for external material and record the unresolved rights question rather than rationalizing reuse after the fact.
