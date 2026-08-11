# MythologIQ Labs AI-Assisted Contribution Standard

**Status:** Organization default

**Applies to:** MythologIQ Labs repositories unless a repository documents a stricter local rule

**Canonical copy:** `MythologIQ-Labs-LLC/agent-memory`

## Purpose

MythologIQ Labs builds with coding agents and other AI-assisted development tools. Their use is permitted and encouraged when it improves implementation speed, validation coverage, accessibility, or review quality.

The governing rule is not who typed the code. The governing rule is who is accountable for the contribution.

> **AI-assisted development is allowed. Autonomous contribution is not accepted by default.**

A responsible human must direct the work, review the specific contribution, understand its meaningful behavior and tradeoffs, and take responsibility for what is submitted.

This standard is intentionally compatible with contribution models used by projects such as Microsoft Agent Governance Toolkit and AgenTrust projects, while remaining technology-neutral. It applies whether the implementation was produced with Codex, Claude Code, Gemini, GLM, Copilot, another coding agent, an IDE assistant, or conventional hand-authored development.

## Definitions

### AI-assisted contribution

A contribution is **AI-assisted** when a human contributor uses one or more AI tools to help research, design, implement, test, refactor, document, review, or prepare a change, while the human remains accountable for the specific output submitted.

The human contributor does not need to have typed every line of code.

### Autonomous contribution

A contribution is **autonomous** when an agent acts as the effective contributor without meaningful human review of the specific output or without a responsible human who can explain and defend the change.

Examples include an agent independently opening a pull request, filing an issue it has not had a human verify, responding to maintainers without human review, or merging changes without human authorization.

### Responsible human

The **responsible human** is the person who owns the contribution at the repository boundary. That person must be able to explain the change, its purpose, its material design choices, its verification evidence, and its known limitations.

## Allowed uses of AI development tools

AI tools may be used for:

- implementation and refactoring;
- tests, fixtures, and adversarial vectors;
- documentation and diagrams;
- debugging and root-cause analysis;
- local code review and security review;
- standards and interoperability mapping;
- migration planning;
- dependency analysis;
- benchmark and validation harnesses;
- drafting commit messages, issue text, and pull-request descriptions;
- generating candidate solutions for human evaluation.

No disclosure is required merely because an AI tool participated in the workflow, unless a repository-specific rule requires it.

## Human accountability requirements

Before a contribution is submitted for review, the responsible human must:

1. **Direct the work.** The change must have a human-understood objective, scope, and acceptance boundary.
2. **Review the specific output.** Review the actual diff, generated files, material configuration changes, and relevant test evidence. Reviewing only an agent summary is not enough for a substantive contribution.
3. **Demonstrate understanding.** Be able to explain what each meaningful change does, why it exists, what alternatives or tradeoffs matter, and what failure modes remain.
4. **Verify the evidence.** Run or inspect the tests, validators, benchmarks, or other checks appropriate to the change. Security-sensitive work requires independent validation where self-referential tests could mask an implementation error.
5. **Check provenance and rights.** Confirm that generated code, documentation, diagrams, and other material do not introduce unattributed or incompatibly licensed third-party work.
6. **Own the submission.** The responsible human is accountable for bugs, security issues, design errors, misleading claims, and attribution failures in the submitted contribution.
7. **Participate in review.** Maintainer questions and review comments must receive a human-reviewed response. AI may draft a response, but an agent must not impersonate the responsible human in an unreviewed discussion.

If the responsible human cannot explain a meaningful part of the change, that part is not ready for submission.

## Repository-boundary rule

Unless a bot or agent is explicitly authorized by repository policy, the following actions require a responsible human to review the specific content before the action occurs:

- opening a pull request;
- filing a bug report, feature request, or design proposal;
- posting a substantive issue, discussion, or pull-request comment;
- responding to maintainer review;
- requesting or recording an approval decision;
- merging a pull request.

For ordinary contributions, the responsible human should submit the pull request from their own GitHub identity after reviewing the diff and evidence.

AI tools and connectors may prepare branches, commits, candidate PR descriptions, test results, and other artifacts before that human submission boundary.

Mechanical automation that does not claim human judgment, such as CI status reporting, dependency updates, formatting checks, or workflow-defined labeling, may be separately authorized.

## Prohibited autonomous behavior by default

Unless explicitly authorized, agents and bots must not:

- open pull requests without prior human review of the specific changes;
- file issues or feature requests without a human verifying that the issue is real and worth maintainer attention;
- claim issues without a responsible human intending to follow through;
- post unsolicited code review feedback to other contributors;
- respond to repository discussions or review threads without human oversight;
- approve pull requests;
- merge pull requests without explicit human authorization;
- manufacture stars, issues, comments, forks, or other synthetic community activity;
- use AI generation to obscure unattributed derivative work or licensing conflicts.

## DCO and contribution provenance

For public MythologIQ Labs repositories that accept external code or specification contributions, the default provenance mechanism is the [Developer Certificate of Origin](https://developercertificate.org/) unless the repository documents an alternative or additional contributor agreement.

For Agent Memory, new contribution commits submitted after adoption of this standard must include a `Signed-off-by` trailer:

```text
git commit -s -m "type(scope): summary"
```

DCO sign-off is a contributor certification. An agent must not invent or apply a human's sign-off without that person's authorization and review.

Repositories should add automated DCO enforcement when practical. Until enforcement exists, maintainers must treat sign-off as a review requirement rather than assume CI proves it.

## Security-sensitive changes

AI assistance does not lower the review bar for security-sensitive work.

Changes involving cryptography, authentication, authorization, policy enforcement, sandboxing, supply-chain controls, secrets handling, isolation boundaries, signing, provenance, or destructive lifecycle actions require heightened review.

At minimum:

- verify that tests are not merely testing an AI-generated implementation against assumptions generated by the same implementation;
- prefer independent vectors, reference implementations, or known-answer tests where available;
- review dependency and algorithm choices for hallucinated packages, obsolete primitives, or insecure defaults;
- do not place secrets, credentials, or restricted data into AI prompts or external tooling;
- state what the validation proves and what remains unproven.

## Prior art, copyright, and licensing

AI assistance does not erase provenance obligations.

Contributors must:

- identify and credit material prior art when architecture, algorithms, APIs, documentation structure, or other expressive work is substantially derived from an external source;
- comply with the repository's source-rights and attribution rules;
- avoid copying or laundering incompatible third-party code through model output;
- preserve required notices and licenses;
- disclose uncertainty when the origin or reuse right of generated material cannot be established.

When in doubt, prefer independent synthesis and explicit attribution.

## Disclosure

Routine AI assistance does not require a disclosure label.

Disclosure is required when:

1. a contribution contains material AI-produced content that the human submitter has not meaningfully reviewed; or
2. an explicitly authorized autonomous agent is acting under a repository-specific automation policy.

The first case is normally not merge-ready. Disclosure is not a substitute for human accountability.

## Authorizing repository agents and bots

A repository may authorize specific automated actors by documenting:

- the bot or agent identity;
- the actions it may perform;
- the files, labels, issue classes, or workflow surfaces within scope;
- the required human oversight model;
- who can revoke that authorization.

Authorization is narrow. Permission to run CI does not imply permission to open PRs, review code, answer maintainers, or merge changes.

## Relationship to local repository rules

This document is the MythologIQ Labs default standard.

A repository may impose stricter requirements because of security, regulatory, contractual, release, or standards obligations. Local rules may narrow automation privileges but should not silently weaken the human-accountability baseline.

Where a repository-specific `CONTRIBUTING.md`, `GOVERNANCE.md`, security policy, or upstream contribution rule is stricter, the stricter rule controls.

When contributing to an external project, that project's rules always control the upstream submission even if MythologIQ Labs permits a broader internal workflow.

## Practical workflow

A compliant agent-first workflow can be:

```text
human defines problem, scope, and acceptance boundary
        |
        v
coding agents research / implement / test / review
        |
        v
human reviews the actual diff and evidence
        |
        v
human resolves provenance, risk, and design questions
        |
        v
DCO / repository provenance requirement satisfied
        |
        v
human submits PR and participates in maintainer review
        |
        v
human-authorized merge after required checks and approvals
```

The purpose of this standard is not to recreate manual coding as a ritual. It is to preserve human accountability, reviewability, provenance, and maintainer trust while using modern coding agents as first-class development tools.
