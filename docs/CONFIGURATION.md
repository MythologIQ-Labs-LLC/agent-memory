# Configuration and Extension Surfaces

Agent Memory is a reference architecture and evidence repository, not one monolithic runtime with one global configuration file.

That distinction matters. Configuration in this repository is intentionally split by responsibility so an implementation, comparator, policy consumer, or optional substrate cannot quietly become the canonical meaning of Agent Memory.

## Current configuration model

There is currently **no required global `.env` contract and no canonical `agent-memory.toml` / YAML runtime file** for the repository as a whole.

Instead, configuration is expressed through explicit, versioned surfaces:

| Surface | Canonical location | What it configures |
|---|---|---|
| Doctrine and lifecycle semantics | `docs/`, `docs/adr/` | Meaning, ownership, maturity, lifecycle and governance boundaries |
| Machine-readable contracts | `schemas/` | Valid record and evidence shapes |
| Interoperability / implementation profiles | `docs/profiles/` and matching schemas | Optional cross-system behavior and evidence boundaries |
| Reference validation dependencies | `reference/requirements.txt` | Pinned dependencies used by the main reference test environment |
| Reference runner options | `reference/run_*.py` | Bounded experiment- or comparator-specific CLI configuration |
| Doctrine / adversarial scenarios | `fixtures/` | Structural and negative-path expectations |
| Source-rights records | `sources/source-registry.json` | External source, license, provenance, and reuse posture |
| Wiki publication | `wiki-src/` + `.github/workflows/publish-wiki.yml` | Reader-facing documentation source and publication |
| CI behavior | `.github/workflows/` | Repository evidence and validation execution |

An external product's configuration format is never automatically an Agent Memory configuration format.

## Reference environment

The main executable evidence environment is installed from the checked-in dependency manifest:

```bash
python -m pip install -r reference/requirements.txt
python -m unittest discover -s reference/tests -t reference
```

The reference environment is intentionally broader than the low-cost documentation/fixture validators because it exercises cryptographic, interoperability, and runtime evidence paths.

For the bounded conformance/evidence runner:

```bash
python reference/run_conformance.py --trials 500
```

`--trials` is an experiment input. It is not a governance or authority setting.

See [`../reference/README.md`](../reference/README.md) for the current executable evidence boundary and exact comparator commands.

## Optional real-substrate profile

The current reference evidence includes an optional Graphiti/Kuzu temporal-graph path. It is not required for ordinary Agent Memory doctrine or schema use.

```bash
python -m pip install graphiti-core kuzu
python -m unittest discover -s reference/tests -t reference
python reference/run_conformance.py
```

The substrate is deliberately treated as an implementation surface:

```text
substrate capability
!= Agent Memory doctrine
!= recall permission
!= mutation authority
```

A future graph, retrieval, relational, ledger, learned-state, or hybrid module must preserve the same separation.

## Optional comparator environments

Some external comparators intentionally use isolated dependency environments when their dependency graph should not become part of the core reference environment.

The reference README records the exact commands and versions for those paths. Comparator configuration must preserve at least:

- external project / specification identity;
- exact release, package, source commit, or checkpoint where applicable;
- adapter/profile version;
- relevant policy, model, schema, or configuration identity;
- explicit unavailable/unsupported behavior;
- the claim the comparator proves and the claims it does not prove.

A comparator being installed does not make it a required dependency.

## Profiles are configuration with semantics

Files under `docs/profiles/` define optional implementation or interoperability contracts. A profile may describe, for example, governance context projection, portable evidence, external policy composition, runtime correlation, or other bounded behavior.

Profile configuration must remain subordinate to canonical doctrine:

```text
profile setting
-> selects or parameterizes allowed implementation behavior

profile setting
!= permission to weaken a stricter lifecycle / scope / PAMA boundary
```

Unknown or incompatible consequential profile versions should fail explicitly rather than being coerced into a permissive default.

## Schema and policy version binding

When a runtime or evidence record depends on a schema, policy, projection, estimator, external consumer, or module configuration, bind the relevant version or stable identity into the evidence whenever the corresponding contract requires it.

Do not collapse these independent version dimensions into one generic `version` string when their drift has different consequences.

Examples include:

```text
memory schema version
PAMA decision schema version
policy version
projection/profile version
external peer version
estimator/model version
substrate/module version
```

Version drift is evidence to evaluate, not permission to guess compatibility.

## Source rights are part of dependency configuration

Before adding a material external dependency, copied asset, comparator, source-derived fixture, or adapted implementation:

1. identify the exact source;
2. verify the applicable license or permission basis;
3. choose citation, independent synthesis, licensed reuse, author-originated reuse, or explicit permission deliberately;
4. add or update `sources/source-registry.json` when required by [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md);
5. preserve any required attribution, NOTICE, modification notice, trademark, or redistribution obligation.

Agent Memory's Apache-2.0 license covers this repository's own licensed distribution. It does not relicense external projects merely because they are linked, compared, or integrated.

## Wiki configuration

The GitHub Wiki is generated from `wiki-src/`; direct Wiki UI edits are not canonical.

Validate Wiki source with:

```bash
python scripts/validate_wiki_links.py wiki-src
```

Publication behavior is defined in `.github/workflows/publish-wiki.yml` and documented in `wiki-src/README.md`.

## Future modular memory configuration

Implementation program #274 owns the transition from completed architecture-family research into optional first-class memory modules.

The shared module configuration contract should eventually make these properties explicit without importing a vendor-specific schema into core:

```text
module identity / type / version
capabilities
implementation/runtime reference
configuration profile identity
canonical-vs-derived posture
scope/isolation behavior
provenance/currentness bindings
correction/deletion/rebuild semantics
failure/unavailable posture
migration/import/export posture
optional dependency/license metadata
```

Graph, retrieval, ledger, relational, learned/latent, and hybrid modules may require different implementation settings. They must still expose enough common configuration evidence for Agent Memory to govern their consequences consistently.

## Configuration review checklist

A configuration or extension change is not complete merely because it starts successfully. Review whether it:

- preserves canonical doctrine ownership;
- binds consequential versions and identities;
- fails explicitly when required configuration is unknown or stale;
- keeps optional dependencies optional;
- preserves scope and isolation boundaries;
- does not turn estimator/backend capability into authority;
- records source-rights and license posture;
- updates README, canonical docs, Wiki, and visuals when the public architecture actually changes;
- produces evidence appropriate to the claim being made.

Configuration is an implementation surface. The repository's semantics remain governed by canonical doctrine, schemas, profiles, evidence, and accepted architecture decisions.