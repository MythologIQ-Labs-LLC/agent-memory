# Agent Memory Wiki source

This directory is the canonical source set for the reader-facing GitHub Wiki.

The Wiki is intentionally a navigation and explanation layer, not a second doctrine tree. Technical authority remains in `docs/`, `schemas/`, `fixtures/`, and `docs/adr/`.

## Design rules

- prefer concise reader-oriented pages over copying repository documents
- use progressive disclosure and role-based navigation
- avoid Mermaid on Wiki presentation surfaces
- use stable repository-native graphics where they materially help comprehension
- link every material doctrine summary back to the canonical repository source
- do not create Wiki-only doctrine
- preserve source-rights and authorship boundaries

## Publication

GitHub stores Wiki content in a separate Git repository:

```text
https://github.com/MythologIQ-Labs-LLC/agent-memory.wiki.git
```

The current ChatGPT GitHub connector does not expose Wiki write operations, so publication requires a git-capable environment.

After the repository Wiki has been initialized once from the GitHub UI if necessary:

```bash
git clone https://github.com/MythologIQ-Labs-LLC/agent-memory.wiki.git
cp wiki-src/*.md agent-memory.wiki/
cd agent-memory.wiki
git add .
git commit -m "Publish Agent Memory Wiki"
git push origin master
```

If GitHub initializes the Wiki repository with a different default branch, push to that branch instead.

## Validation

Run the Wiki-link validator before publishing:

```bash
python scripts/validate_wiki_links.py wiki-src
```

The validator understands GitHub Wiki extensionless page links such as `[PAMA](PAMA)` and verifies that a corresponding `PAMA.md` source page exists.

## Page inventory

- `Home.md`
- `Getting-Started.md`
- `Core-Concepts.md`
- `PAMA.md`
- `Lifecycle-and-Forgetting.md`
- `Governed-Uncertainty.md`
- `Security-and-Privacy.md`
- `Conformance-and-Evidence.md`
- `Research-and-Sources.md`
- `Implementation-Guide.md`
- `Architecture-Decisions.md`
- `Contributing.md`
- `Glossary.md`
- `_Sidebar.md`
- `_Footer.md`

