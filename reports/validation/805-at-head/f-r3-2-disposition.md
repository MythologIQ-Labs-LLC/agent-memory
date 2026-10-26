# F-R3-2: the evidence-reference deletion oracle, investigated as evidence

Owner direction (PR #805, review 5526560856): investigate and disposition F-R3-2 as evidence
rather than silently accepting it. This record reproduces the finding on the integration
candidate (runtime protected blobs at `ef8b6cb2`, contract 1.8.0), states the exact observable,
measures what it discloses, and lays out the dispositions with their cost. It decides nothing:
the disposition is the owner's, and the one change that would close the channel is a protected
runtime change held by the release HOLD.

## Reproduction (deterministic, offline, through the public facade)

Test: `reference/tests/test_786_cross_scope_write_authority.py::EvidenceReferenceOracle::test_fr3_2_citing_a_deleted_foreign_uuid_is_observable_to_the_citer`
(2 sub-cases: pruning and attested permanent deletion). Probe script of the same scenario:
`scratchpad/probe/fr32_probe2.py` (not committed).

Scenario: project A writes `memory:a` (fact `a1`) and `memory:a2` (fact `a2`), then governed-deletes
`memory:a`. Project B, which can read neither, writes four digests, each citing one `evidence_ref`:
`a1` (deleted, foreign), `a2` (live, foreign), a guessed uuid that names no fact, and no reference.

| B cites | B's `remember` | B's own digest in B's recall | what B learns |
|---|---|---|---|
| `a1` (member of a deleted generation of A) | commits, `allow_with_ledger`, no refusal | **withheld** (0 admitted, 0 candidates) | the uuid belongs to a deleted generation |
| `a2` (live fact of A, unreadable to B) | commits | admitted | nothing (same as a guess) |
| guessed uuid naming no fact | commits | admitted | nothing |
| no reference | commits | admitted | nothing |

The write itself discloses nothing (every citation commits identically). The disclosure is the
citer's own recall: a derived memory whose provenance leads to a deleted fact is withheld
tenant-wide (`_derives_from_deleted`, transitive over canonical fact references), whatever the
citer's scope. Live foreign facts are **not** disclosed by this channel: a citation of a live
unreadable fact reads exactly like a guess.

## Guessability

Fact uuids are minted by `DeterministicIds("ref")` as `ref-0001`, `ref-0002`, ... in one tenant-wide
sequence (`runtime/adapter.py`, `mint_id`). Enumerating `ref-0001` .. `ref-N` with one digest each
therefore yields, for every fact ever written in the tenant, the bit "member of a deleted
generation" or "not". It never yields content, scope, memory id, timestamp or version; the
uuid-to-memory binding stays hidden. What leaks is the count and the identity (by sequence
position) of deleted-generation facts across scopes, from which deletion activity in other
projects can be inferred.

## Why it exists

It is the mechanism of the #776/#777 deletion-completeness rule: a derivation of deleted content
must not survive its source, across the tenant, so that a copy in another scope cannot outlive a
deletion. The rule is right for content the citer could read. For content the citer could never
read, the "derivation" carries no content; withholding it serves no erasure purpose and only
answers the oracle.

## Dispositions (owner's decision)

| option | change | closes the oracle | cost / risk |
|---|---|---|---|
| (a) opaque identifiers | mint fact uuids from a CSPRNG instead of a tenant-wide sequence (protected: `DeterministicIds` / `mint_id`) | makes guessing impractical; the channel stays for a uuid the citer legitimately learned | changes every recorded uuid; replay runners label uuids by lookup so fixtures survive, but any committed evidence that records raw `ref-N` outside the folded fields must be re-executed; deterministic test fixtures that assert `ref-N` literals change |
| (b) **unreadable references are unknown** (recommended) | at commit time, record a provenance link (`episode_uuids`) only for cited facts the writer is eligible to read under its own writer context; a reference to a fact outside the writer's scope is treated exactly like a reference that names no fact (protected: `runtime/adapter.py`, one filter at the derivation-binding site) | yes for cross-scope guesses: the deleted-foreign citation is admitted like a guess; within readable scope (own project, shared domains) a derivation of a deleted source is still withheld, so deletion completeness is preserved where content could have flowed | small, scoped protected change; needs a preregistered reproducer (the oracle test above with its expectation flipped for the foreign case and an added shared-domain case that must stay withheld), a docs/44 clause, a declaration blob regeneration and a ladder re-run; it is a behavioural change of the derivation rule and must not ride on the current HOLD without the owner's word |
| (c) accept as the price of tenant-wide deletion completeness | none | no | the oracle remains; it discloses only deleted-generation membership of guessable ids, never content or scope; record it in docs/786 (already there) and in the threat model |

Not an option: refusing the write (a refusal would be a louder oracle than the withheld recall).

## Recommendation and status

Recommend (b). Not implemented here: it is a protected runtime change and the owner's HOLD covers
protected changes without an explicit decision. The documenting test pins the observable as it
stands so that whichever disposition is taken is measured against a committed baseline.
Status: INVESTIGATED, EVIDENCED, NOT DISPOSED (owner), NOT CHANGED.
