# Source Rights and Reuse Policy

## Purpose

Agent Memory is intended to be evidence-informed, publicly traceable, and safe to reuse without quietly importing protected expression from source material.

This policy governs how external and internal source material may be cited, summarized, adapted, quoted, copied, or incorporated into repository doctrine, examples, diagrams, schemas, fixtures, code, and documentation.

The core rule is simple:

> **Public accessibility does not imply reuse permission. Citation does not imply a license.**

When reuse rights are absent, unclear, unnecessary, or disproportionate to the value of the copied expression, Agent Memory should link to the source and independently synthesize the underlying ideas rather than reproduce protected expression.

This is a repository governance policy, not a substitute for legal advice.

## Default source treatment

Unless a stronger reuse basis has been verified and recorded, treat external material as:

```text
LINKABLE
The source may be identified and linked when the locator is lawful and public.

CITABLE
Facts, findings, ideas, mechanisms, and claims may be discussed with attribution and appropriate evidence discipline.

SYNTHESIS-ONLY
The repository should express the idea independently rather than copy distinctive prose, diagrams, tables, screenshots, or code.
```

Unknown rights status defaults to **citation and independent synthesis only**.

## Reuse modes

Every material source should be classifiable as one of these modes:

| Mode | Meaning | Default posture |
|---|---|---|
| `citation_only` | Link or cite the source without importing protected expression | Safe default |
| `independent_synthesis` | Explain facts, ideas, findings, or mechanisms in original repository language | Preferred default |
| `author_originated` | Material originated with a repository contributor who is asserting authorship/provenance | May be reused subject to contributor authority and any third-party constraints |
| `licensed_reuse` | Copy or adapt material under a verified license | License obligations must be satisfied |
| `permission_granted` | Copy or adapt under explicit permission outside a standard license | Permission evidence must be retained |

`licensed_reuse` and `permission_granted` require an explicit reuse basis in the source registry.

## What may be linked

When a named source has a lawful, stable public locator, link the most specific authoritative artifact available.

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

## Source-class rules

### Research papers and books

- Link DOI, publisher, PubMed, arXiv, author manuscript, or lawful open archive where available.
- Record findings and claims in original repository language.
- Do not reproduce substantial prose, figures, tables, or diagrams unless the rights basis permits it.
- Paywalled access does not create reuse rights.
- Open access is not itself a license statement; verify the specific license before reuse.

### GitHub repositories

- Verify the repository license before copying code, documentation, examples, diagrams, or other expressive material.
- Preserve attribution, license text, notices, modification notices, or other obligations when the license requires them.
- A repository with no verified license is `citation_only` / `independent_synthesis` by default.

### Issues, discussions, and comments

- Link directly when public and material to provenance.
- Treat third-party prose as `citation_only` / `independent_synthesis` unless explicit reuse rights are established.
- Record contributor-originated material as `author_originated` only when authorship/provenance is known and the contributor has authority to reuse it.

### Private sources

- Private accessibility is not publication permission.
- Do not expose private URLs, confidential text, screenshots, or implementation details merely to make public provenance look complete.
- A public successor or related project may be identified, but it must be labeled as a successor or related implementation rather than substituted for the private provenance source.

### Code

- Do not copy source code unless a compatible license or explicit permission is verified.
- Preserve required copyright notices, license text, NOTICE files, attribution, and modification notices.
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

## Material-reuse record

When source material is materially reused rather than merely cited or independently synthesized, record at least:

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

Machine-readable primary-source records live in `sources/source-registry.json` and are validated against `schemas/source-record.schema.json`.

## Hard gates

A source record must not use `licensed_reuse` or `permission_granted` unless it records a non-empty `reuse_basis`.

A source with `rights_status = unknown` must not authorize copied or adapted material.

A source with no verified license is not open source merely because it is publicly readable.

A source marked private must not receive a fabricated public provenance link.

A project successor must not be represented as the originating source.

## Review checklist

Before merging externally sourced material, reviewers should ask:

- Is this source being linked, summarized, quoted, adapted, or copied?
- Is the most authoritative source linked?
- Is the license or permission applicable to the actual material, not merely the surrounding repository?
- Are license and NOTICE obligations satisfied?
- Could the same value be achieved through independent synthesis instead?
- Is any private or confidential provenance being exposed?
- Is contributor-originated material correctly attributed?
- Are we recording provenance without overstating legal exclusivity?

When the answer is uncertain, prefer citation and independent synthesis and record the unresolved rights question rather than rationalizing reuse after the fact.
