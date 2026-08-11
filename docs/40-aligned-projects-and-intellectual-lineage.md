# Aligned Projects and Intellectual Lineage

## Purpose

Agent Memory is built in public, in conversation with other technical work.

Some projects contribute a useful idea. Some expose an implementation pattern. Some provide a substrate, benchmark, enforcement surface, evidence layer, research challenge, or vocabulary that sharpens Agent Memory's own architecture. Those relationships deserve visible credit without turning attribution into accidental dependency, endorsement, joint authorship, or license confusion.

The governing idea is:

> **Be generous with credit and precise about boundaries.**

Agent Memory should celebrate developers, researchers, maintainers, and repositories that materially improve the work. Recognition must remain specific enough that a reader can tell:

- what was learned;
- who or what contributed it;
- what Agent Memory independently owns;
- whether the relationship is conceptual, experimental, comparative, interoperable, or implementation-backed;
- whether any external material was actually reused;
- which license governs each work; and
- whether endorsement or formal partnership exists.

## Relationship vocabulary

Use the narrowest relationship label that accurately describes the evidence.

| Relationship | Meaning | Does not imply |
|---|---|---|
| **Intellectual lineage / informed by** | External work materially shaped a question, distinction, mechanism, or design direction. | dependency, implementation, endorsement, joint authorship |
| **Conceptually aligned** | Projects independently share a useful architectural or philosophical principle. | common ownership, compatible APIs, conformance |
| **Reference substrate** | Agent Memory has executed or mapped doctrine against the system as a concrete runtime/storage substrate. | that the substrate owns Agent Memory doctrine |
| **Implementation candidate** | A system appears able to implement a bounded Agent Memory responsibility and has enough evidence to justify inspection. | conformance or canonical ownership |
| **Implementation mapping** | A concrete implementation role is supported by inspected code or reproducible evidence. | full Agent Memory conformance |
| **Comparator / benchmark target** | The project provides a useful architecture or behavior to test against adversarially. | inferiority, endorsement, dependency |
| **Interoperability target** | Agent Memory intends to exchange evidence, state, policy signals, or contracts across a defined boundary. | shared semantics beyond the declared boundary |
| **Enforcement peer** | A separate governance/runtime system may further restrict Agent Memory-permitted consequences. | power to expand Agent Memory permission |
| **Evidence / attestation peer** | A separate system can verify, bind, transport, or attest to evidence of Agent Memory decisions. | ownership of memory semantics or authority |
| **Formal partner** | A documented organizational partnership or jointly agreed collaboration exists. | anything beyond the terms of that actual agreement |

Do not use **partner**, **official integration**, **supported by**, **endorsed by**, or equivalent language unless the relationship is actually established.

## Recognition is not dependency

Agent Memory may adopt or independently derive a principle from public technical work without requiring that project's runtime, package, ontology, API, or license as an implementation dependency.

A useful architecture should survive substitution where its doctrine does not intrinsically require one vendor or repository.

For external systems, distinguish:

```text
principle learned from a project
        !=
mandatory implementation dependency
```

and:

```text
project inspired a boundary
        !=
project owns the resulting Agent Memory doctrine
```

When a specific implementation is required for a test, adapter, or profile, pin that dependency locally to the evidence and do not generalize it into repository-wide doctrine.

## Recognition is not relicensing

A link, citation, acknowledgement, implementation map, or aligned-project callout does not import the external project's license into Agent Memory and does not apply Agent Memory's Apache-2.0 license to the external work.

By default, aligned-project recognition uses:

```text
link
+ attribution
+ independent synthesis
```

rather than copied expression.

If code, prose, diagrams, tables, schemas, fixtures, or other expressive material are copied or adapted, the reuse must follow [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md) and, where material, be recorded in [`sources/source-registry.json`](../sources/source-registry.json) with the applicable license/permission obligations.

Repository licenses also do not automatically govern third-party issue comments, discussion posts, uploaded attachments, logos, screenshots, linked papers, or other nearby material.

## Names, marks, and logos

Project and organization names may be used descriptively to identify the referenced work.

Logos, badges, stylized marks, or visual brand assets should not be incorporated merely to make an acknowledgement page look more impressive. Use them only when the relevant trademark/brand-use terms or explicit permission support the intended use.

Unless a formal relationship exists, recognition should carry a short independence statement such as:

> Recognition describes intellectual lineage, technical alignment, implementation evidence, or interoperability context. It does not imply endorsement, sponsorship, formal partnership, joint authorship, or transfer of intellectual-property ownership.

## Credit the people when the people matter

A project name should not erase individual contribution.

When a specific developer, researcher, maintainer, reviewer, or community participant materially changed Agent Memory's thinking, and the provenance is public and appropriate to name, the acknowledgement should identify that contribution specifically.

Examples include:

- a maintainer clarifying a system boundary;
- a contributor publishing a calibration method;
- a reviewer exposing a failure mode;
- an issue author proposing a mechanism later tested in Agent Memory;
- a researcher publishing evidence that narrowed or overturned a favorite assumption.

Attribution should not overstate legal exclusivity. Recording that someone originated a proposal or framing is a provenance claim, not automatically a claim that the underlying idea, method, or short phrase is exclusively protectable.

## First highlighted lineage: UOR Foundation

### Relationship

**Intellectual lineage / conceptually aligned foundation.**

Agent Memory is an independent project. Work from the [UOR Foundation](https://github.com/UOR-Foundation/UOR-Framework) on deterministic object reference, content-addressed identity, explicit resolution state, and formally described object spaces materially informed parts of Agent Memory's architectural thinking.

The current UOR Framework is a Rust implementation of the UOR Foundation ontology and publishes machine-readable ontology artifacts, generated Rust traits, conformance tooling, and multiple semantic-web representations. Agent Memory does not require that implementation in order to exist or conform.

### The principle Agent Memory carries forward

The most important architectural lesson is a separation:

```text
IDENTITY
What object is this?
Can it be referred to exactly?
Can two observers resolve the same object?

        !=

MEMORY GOVERNANCE
Should it persist?
Who may recall it?
What may it influence?
When may it change?
When must it be forgotten?
```

Agent Memory adopts this separation as doctrine while remaining implementation-neutral about how exact identity is supplied.

When UOR is used, it is a strong candidate for deterministic identity and exact addressability. A conforming Agent Memory implementation may use another exact identity mechanism if it preserves the same architectural boundary.

See [`ADR-001`](adr/ADR-001-uor-is-identity-not-memory.md).

### Research lineage

[UOR Framework issue #2](https://github.com/UOR-Foundation/UOR-Framework/issues/2), opened by Kevin R. Knapp, explored whether UOR resolution/saturation primitives could inform memory decay, crystallization, conflict-driven reheating, and exact-address transition behavior.

That discussion became useful research lineage for Agent Memory's treatment of saturation, decay, crystallization, calibration, and the distinction between identity and lifecycle. It did not make the proposed thermodynamic lifecycle official UOR doctrine, and Agent Memory does not present it that way.

The issue also received material third-party contributions, including a decay-calibration protocol. Those contributions retain their own provenance and rights posture.

### Licensing boundary

The UOR Framework repository is MIT-licensed. Agent Memory is Apache-2.0 licensed.

This recognition does not copy or incorporate UOR code, generated ontology artifacts, diagrams, or distinctive documentation expression into Agent Memory. The default relationship is citation and independent synthesis.

If future Agent Memory work deliberately reuses MIT-licensed UOR material, the required UOR copyright and permission notice must be preserved for the reused material and the reuse must be recorded under the repository's source-rights policy.

### Independence statement

> Agent Memory is not affiliated with, endorsed by, sponsored by, or formally partnered with the UOR Foundation unless a separate public agreement says otherwise. Recognition here records intellectual lineage and technical alignment only.

## How projects earn a highlighted entry

A project should receive a visible highlighted entry only when at least one of these is true:

1. it materially influenced a canonical Agent Memory distinction or doctrine question;
2. it provides implementation evidence for a bounded Agent Memory responsibility;
3. it acts as a real reference substrate or adversarial comparator;
4. it provides a meaningful enforcement, evidence, interoperability, or portability boundary;
5. its maintainers or contributors materially challenged or improved Agent Memory's design; or
6. it supplies external evidence that changed a claim, boundary, test, or roadmap priority.

Mere conceptual adjacency is not enough.

## Required shape of a highlighted entry

Each entry should answer:

```text
project / people
relationship type
what specifically mattered
what Agent Memory independently owns
whether runtime dependency exists
license / source-rights posture
endorsement / partnership status
canonical links
```

This keeps acknowledgements useful to engineers rather than turning them into a logo wall.

## Future candidates

Projects already present elsewhere in Agent Memory may eventually earn dedicated entries here as their relationship becomes specific enough, including reference substrates, implementation systems, enforcement peers, evidence ecosystems, and research comparators.

Being named elsewhere in the repository does not automatically qualify a project for a highlighted lineage entry. The acknowledgement should follow evidence, not networking enthusiasm.
