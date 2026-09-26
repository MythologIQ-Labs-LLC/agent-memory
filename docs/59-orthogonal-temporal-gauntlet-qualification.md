# Orthogonal Temporal Gauntlet Qualification

Status: qualification record for the ADR-039 acceptance gate (#544). This is a qualification pass only; no benchmark run is claimed. ADR-039 remains **Proposed**.

## What the gauntlet must test

The external evidence so far (LongMemEval_S and AgentMemBench; see `docs/57-query-conditioned-applicability.md`) barely exercises:

- explicit validity intervals;
- as-of and historical behavior;
- prospective behavior;
- temporal-intent metadata.

A useful next gauntlet must be able to falsify at least one of:

| claim | needs |
| --- | --- |
| (a) non-compensation: a semantically strong but expired fact must not outrank a weaker but valid fact under a current query | per-fact validity, or state changes with gold "current" evidence |
| (b) as-of / historical discrimination | questions targeting a past instant or interval |
| (c) prospective handling | future-valid facts and forward-looking questions |
| (d) a simpler universal policy (newer-first) matching query-conditioned behavior across classes | several temporal classes in one corpus |
| (e) protocol-faithful text-only lane vs explicit-temporal-metadata conformance lane | gold validity metadata that can be withheld or supplied |

## Candidates

### Ground Truth First (Q. Spencer, arXiv:2607.21962)

- **Design fit: best.** The paper, known only through search snippets, describes:
  - a seeded life-script sampler that emits facts with validity intervals, volatility classes, and source channels before any text is rendered;
  - about 380 validated questions across 15 types, including as-of-date sets.
- **Library:** `github.com/veracium-ai/Veracium`, MIT, main `190521f26bafe5be9a31c3a3b34017cacf540f73`, tag `v0.26.1` (`e97ffb0`).
  - This is the memory **library** (validity bounds, volatility classes, `facts_valid_at` as-of lookup).
  - It contains **no** generator, corpus, or question set. Its README points to a separate research project that we could not locate.
- **Paper text: not read.** arxiv.org is blocked by this environment's egress policy, and we did not route around it.
- **Claimed releases (unverified):** generator and harness (MIT), corpus (CC BY 4.0), judged verdicts. "Judged verdicts" suggests an LLM judge for answer scoring.
- **Falsifies:** (a), (b), (d) likely; (c) unconfirmed; (e) **uniquely possible**, because the script's intervals are gold metadata.
- **Status: qualified by design, blocked on artifact availability.**
  - Next action: locate the generator or corpus. Enable arXiv egress to read the artifact statement, or contact the author.
  - Then run the bounded slice (below).

### Microsoft RHELM ("Beyond Static Dialogues", arXiv:2605.31086)

**Provenance**
- Code: `github.com/microsoft/RHELM`, MIT, main `5e170da7a2db96b4d222620a2aaaddb031cb8098`, no tags.
- Data: `huggingface.co/datasets/microsoft/RHELM` at revision `d0e8e0cc7be6b7042819175ddef550d217c7c5a9`, CC BY 4.0, fully synthetic personas. A copy is under `data/` in the code repository, about 43 MB.
- The generation pipeline is unreleased, so the corpus cannot be regenerated.

**Corpus and evaluator**
- Corpus: 10 personas, 1,305 QA, 629 dated conversation sessions, 625 emails, 1,053 attachments.
- Every question has a `question_date` and `supporting_evidence` (2,936 references, mostly `YYYY-MM-DD:turn`), so evidence-recall@k is computable without an LLM.
- Evaluator: exact, fuzzy, and contains matching, plus a gpt-4o judge. A deterministic retrieval-only lane needs no paid API.

**Temporal content, measured locally**

We ran the frozen deterministic temporal-intent interpreter (`bb4cc29`) over every question:

- Only **17 of 1,305** carry a high-confidence *current* cue.
- The `temporal` type is mostly event lookup and sequencing.
- The 65 `misleading` questions are mostly proactive-advice prompts with long free-text gold answers: 33 prospective, 28 unspecified.
- **No per-fact validity metadata is released**, and there is **no as-of question class**.

**Falsifies**
- (a): only indirectly, through derived evidence-date pairs.
- (b), (c), (e): no.
- (d): no. With so few temporal classes, a newer-first policy is not penalized anywhere.

**Status: qualified as runnable, but not able to falsify the targeted ADR-039 claims.** It is not run as ADR-039 evidence. It remains a candidate retrieval-quality gauntlet for #537 on its own merits: heterogeneous sources and stale-premise questions.

## Recommended bounded slice (once Ground Truth First artifacts are available)

About 20 questions each of current, as-of, historical, and prospective, if present (80–100 in total). If a class is thin, it is marked not testable rather than padded.

Compare under the **same relevance policy** (admitted-set BM25):

1. `temporal_regime = universal_newer_first` (policy 2.x);
2. `temporal_regime = query_conditioned` (policy 3.0.0).

Run in two lanes, never mixed:

- **Protocol-faithful / text-only lane:** only text reaches Agent Memory, and temporal intent comes from the question text. This lane is the only one that can be compared to published systems.
- **Explicit-temporal-metadata conformance lane:** gold validity intervals map to `valid_from` / `valid_until`, and question dates map to `reference_time` or `as_of`. This is **not** leaderboard evidence unless every compared system receives equivalent metadata.

If the universal policy matches query-conditioned behavior across the tested classes in the text-only lane, record that as falsification pressure on ADR-039 condition 1.

## Environment limits recorded

- arxiv.org is blocked by the egress proxy. We did not route around it.
- `github.com/Hanzhang-lang/RHELM_Benchmark`, referenced by the RHELM dataset card, required authentication.
