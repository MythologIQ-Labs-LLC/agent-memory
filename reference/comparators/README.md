# #789 competitor source qualification: executable first slice

**Status:** Three exact external repository revisions and their licenses/API surfaces inspected; a deterministic **source-attribution gate has been implemented and locally tested in isolation**. No vendor install, remote model inference, benchmark execution, source adapter qualification, accepted result, new score, or release approval has occurred.

## Source pins and separation of ownership

| System | Inspected exact source | Package at pin | License inspected | Profile outcome |
| --- | --- | --- | --- | --- |
| Graphiti OSS | [getzep/graphiti@b2ff2ea](https://github.com/getzep/graphiti/tree/b2ff2eadd9a6b75a261a5cf0b19557883a13f752) | `graphiti-core 0.29.3` | Apache-2.0 | source-qualified only, candidate temporal graph retrieval |
| Cognee OSS | [topoteretes/cognee@4b9dd36](https://github.com/topoteretes/cognee/tree/4b9dd362625dfd3621c344e571a86f5bc7a55ee8) | `cognee 1.4.2` | Apache-2.0 | source-qualified only, candidate CHUNKS retrieval or separate graph QA |
| Hindsight OSS | [vectorize-io/hindsight@2e8c221](https://github.com/vectorize-io/hindsight/tree/2e8c221c54b1dd2f6cc003f63accf3a01a077332) | exact install version not yet pinned | MIT | **#640 owns integration**, source cross-checked only |

Machine-readable exact identities: `reference/comparators/source_qualification_789.json`.

### Real issue: native source provenance, not install instructions

Our frozen retrieval lanes measure **exact benchmark source IDs**. A graph result may express the relationship correctly but merge supporting facts from several source episodes. A retrieved chunk may be semantically identical to source text without preserving its original document UUID. Neither can be credited as an exact-source hit by matching content or selecting an arbitrary support document.

`reference/comparators/source_identity_gate.py` provides:

- a strictly explicit mapping from actual **native ingest source handles** to allowed input document IDs;
- no gold labels, answer text, query text or semantic similarity inputs;
- refusal for non-attributable, foreign, cross-document and ambiguous graph hits;
- native provider ranking order, finite top-`k` result, duplicate suppression;
- diagnostic `attributed | partial_source_attribution | unsupported_source_identity`;
- an explicit `ranked_for_scoring()` method that **throws** when any observed hit cannot be attributed.

For the isolated implementation, **14 focused unittest scenarios passed locally** with no third-party dependencies, providers, credentials or hosted CI. The committed tests live at `reference/tests/test_789_comparator_source_identity.py` and must be re-executed in the actual repository checkout before qualification:

```bash
python -m unittest discover -s reference/tests -t reference -p test_789_comparator_source_identity.py -v
```

These are **mock native source handles**. They test the adapter's honesty, not whether Graphiti or Cognee provides the necessary handles. **No comparator is benchmark-qualified** by these tests.

## Next real integration milestones

### Graphiti

At the pinned revision, the OSS package exposes `Graphiti.add_episode` and search; it requires a graph backend, LLM extraction and embeddings. First use one explicitly pinned local backend and deterministic isolation namespaces for each frozen LongMemEval question. Inspect the **actual** returned edge/node provenance. Require source episode UUIDs to map to original benchmark inputs without gold or text lookup. If edges are multi-source, do not force exact-item ID; return typed unsupported/partial and consider an appropriate native temporal reasoning profile instead.

### Cognee

At the pinned revision the Python search entrypoint accepts `query_type` and `top_k`, and the project supports `CHUNKS` and `GRAPH_COMPLETION` surfaces. First qualify source preservation through `add → cognify → CHUNKS`, with source-data UUIDs and per-dataset isolation; test the native shape **before** writing a lane adapter. If the chunks do not carry traceable original document IDs, record `unsupported_source_identity`. `GRAPH_COMPLETION` is an answer-generation profile; never use its output as exact-source recall.

### Hindsight

Do not recreate or rewrite #640's adapter ownership. The project documents self-hosted `retain/recall/reflect` through its public client; its content extraction and reflection behaviors may not preserve one-to-one original input IDs. Execute at a new frozen common lane only after #640's exact config, model cost, and source attribution are qualified. Existing old frozen lane definitions mark Hindsight `deferred`; **never backfill its scores**.

## Mandatory negative controls before any same-harness run

1. Same phrase in two different source IDs and tenants.
2. Source attribution that points to two documents for one graph edge.
3. Native result with no source handles or a non-recognized ID.
4. External result with provider-ID-only provenance (not a benchmark source reference).
5. Ingestion failure and empty retrieval return distinguished; fail closed on partial attribution.
6. Changed source mapping between ingest and search.
7. Returned ranking with more than `k` hits; score native truncation without silently reordering by a custom heuristic.
8. New lane frozen **before** execution, with Agent Memory, lexical control and all participating competitors re-executed together under the same input and evaluator versions.

A new adapter is only `protocol_qualified` when actual product outputs survive these controls and exact environment/LLM/embedder/store identity is recorded. Later `accepted_same_harness` additionally requires row-level raw outputs, scorer replay and independent review.

## Execution budget

No GitHub Actions or vendor-cloud paid provider. For any non-free LLM/embedder require a separate owner-approved cost/profile decision; default is `blocked_cost` rather than silently changing comparison semantics. Keep Graphiti OSS separate from commercial Zep identity.

## Owner decision

The next executable priority after #640 is **Graphiti native provenance feasibility first**, then Cognee. If source linkage cannot be made exact without adapter invention, do not contort the frozen retrieval evaluator: use a different benchmark-native QA/temporal evaluation in a separately frozen lane and disclose that these systems are not directly rank-comparable on exact-source metrics.


## Direct upstream Graphiti source-provenance feasibility finding

At the pinned `getzep/graphiti@b2ff2ea` SHA, `graphiti_core/edges.py` (Git blob `28c170355e02a569b60c5e070f019572889ace82`) defines `EntityEdge.episodes: list[str]` as the source episode references. `graphiti_core/graphiti.py` (blob `7555a1f828c4b94970911876bfd257aaa4577d4c`) accepts an optional caller-defined `uuid` for `add_episode` and `search(..., num_results=...)` returns `list[EntityEdge]`.

This is a **source-level path to exact-item attribution**, not speculation about whether graphs can expose provenance. A candidate runner can record the successfully ingested episode UUID next to its benchmark source ID, pass actual `edge.episodes` lists to `attribute_graphiti_edges()`, and decline to credit edges whose provenance spans multiple benchmark sources.

The implementation adds `reference/comparators/graphiti_source_probe.py` and five focused tests covering valid native edges, multi-source ambiguity, foreign episodes, empty provenance and duplicate source credit. **19 contract tests passed in isolated local Python prototypes**, without using the Graphiti SDK. The exact committed test suite requires a fresh PR-checkout run before any review promotion.

Critical unproven conditions: whether the installed Graphiti revision on the selected backend returns complete `episodes` on every searched edge; whether real ingestion/retrieval preserves caller UUIDs across model extraction and restart; and whether exact-source attribution is sufficiently complete to provide a meaningful parity comparison. Until those are runtime-observed, `graphiti-oss` remains `not_run` and has no accepted score.

The Cognee `ChunksRetriever` at its pinned revision returns `found_chunk.payload` from `DocumentChunk_text`. The public `SearchResult` wrapper carries `search_result`, `dataset_id` and `dataset_name`, **not** a guaranteed original input document ID. Before a Cognee exact-source bridge is defensible, establish native `chunk_uuid -> ingested Data/document ID` lineage via its own source data/graph model. Do not derive IDs from chunk text or assume a dataset is itself one benchmark document.


## Source-qualified Cognee document attribution path (2026-10-13)

Further inspection of exact `topoteretes/cognee@4b9dd36` exposed the native document lineage that was previously only a hypothesis.

- `cognee/modules/chunking/models/DocumentChunk.py` (blob `4637c458644fc347cf376dc88cbf73f69b48bd0d`): `DocumentChunk.is_part_of` references the source document and `document_id` is an optional original document identifier.
- Standard chunkers, including `TextChunker`, assign `document_id=str(document.id)` at ingestion. That must be checked against actual input records, not guessed from the document name.
- `cognee/modules/retrieval/chunks_retriever.py` (blob `72fed7ca5db2a7d7aa2da2d339181882f6570d9e`) returns the vector engine's original `found_chunk.payload`, rather than an LLM-generated answer, for `SearchType.CHUNKS`.
- Cognee's own `cognee/modules/retrieval/utils/references.py` (blob `b0efd708612accae76d4ffdf6d4e861d519bc725`) explicitly interprets `payload.get("document_id")` as the ingested data identifier for citation purposes.

Implemented `reference/comparators/cognee_source_probe.py` to extract **only** `payload.document_id` and pass it through the common trusted-ingestion-map gate. It never credits names, text, dataset IDs, completion answers or missing/unknown documents. Eleven deterministic tests cover native order, multiple chunks per document, unknown and cross-scope IDs, missing source IDs, generated answers, partial provenance, bad shapes, and empty retrieval. Those tests **passed against a locally reconstructed isolated contract implementation**; no Cognee SDK or vendor server was installed, so the exact committed PR-head checkout and real product output remain unqualified.

This updates Cognee's status from `unproven source-id representation` to **`source_level_feasible_unverified_runtime`**, but its evaluation status stays `not_run`. A faithful vendor run still needs to prove the returned `document_id` equals the recorded ingested Data.id across the exact benchmark fixture, namespaces, changes, and restart, without changing the frozen evaluator or importing nonreproducible scores.

Graphiti and Cognee now both have plausible **native** source lineage routes. That does not establish which architecture performs better, and creates no extra numeric bar in Pages.
