# #808 integration handoff: what can proceed, what is blocked

**Scope:**
- the checker and fixtures on this branch, `claude/808-provenance-qualification-no-ci`;
- the receipts on `claude/810-external-exec-no-ci` at `8649219`.

Details and evidence are in `VALIDATION.md` and `RECEIPT-AUDIT.md`. This handoff authorizes nothing: there is no merge, no PR and no publication.

## A. The checker (#808 items 1–5, 7)

This is ready for review as an isolated change: 5 files plus fixtures and the validation record, with no schema version change.

What a reviewer should check:
1. **The acceptance rule.** `accepted` requires three things:
   - `--evidence-root`, so that every pointer is re-hashed;
   - `--review-authority`, a decision record binding reviewer, `decision_ref`, `run_id` and normalized digest, with executor ≠ reviewer after normalisation;
   - `--review-authority-sha256`, the record's digest as **published by the owner** out of band.

   Without that last item, whoever writes a manifest could also write its authority file.
2. **The pointer-base contract.** Pointers resolve relative to the repository root at the evidence commit.
3. **Hosted inference.** It is never cost `not_applicable`.

**Migration risk is low:**
- The 12 committed real manifests that were valid before stay valid as committed in schema/semantic mode (without `--evidence-root`).
- In re-hash mode, **none** of the 21 passes yet. Their `normalized_run` is not a `memory-benchmark-run` record (R10), and the checker now refuses that clearly instead of failing on a decode error.
- The `normalized_run` / `artifacts` association is opt-in and carries no `sha256`.
- The UI catalog output is unchanged (`--check` passes).
- No frozen run is touched.

## B. Candidate rows that can proceed to independent review

These 7 result rows have intact receipts (130/130 hashes) and need **no new experiment, no compute and no paid inference**. Each needs only superseding v1 manifests that apply fixes R1–R9 from `RECEIPT-AUDIT.md`. The values come from two places:
- committed evidence;
- for the Graphiti row only, `top_p` from the pinned llama-cpp-python 0.3.16 server source, whose file digest is verified against the wheel's RECORD.

| Row | Owning issue |
|---|---|
| Hindsight chunk-only, LongMemEval-S full 500, session | #640 |
| Hindsight chunk-only, LongMemEval-S full 500, turn | #640 |
| MemPalace default, LongMemEval-S full 500, session | #810 (cohort #789) |
| MemPalace default, LongMemEval-S full 500, turn | #810 (cohort #789) |
| Hindsight chunk-only, AMB-77 protocol A | #640 |
| MemPalace, AMB-77 protocol A | #810 (cohort #789) |
| Graphiti 0.31.1 with local 3B, AMB-77 protocol A (LLM-ingestion tier) | #812 |

The superseding manifests should sit **next to** the originals, so that history is kept. They should be written by the evidence branch's owner. R10, the normalized records, waits on G1.

## C. Decisions needed before any of them can be accepted

These are governance items, not engineering ones.

- **G1 Evidence class.** Today an external row is accepted only as a frozen same-harness lane row. In every lane, Hindsight is listed as `deferred`, and the lane `change_rule` requires a lane to be frozen before any score is observed. These scores have been observed. There are two options:
  - **(a)** Freeze new lanes (Hindsight chunk-only, MemPalace, Graphiti-3B) and execute them through the hosted lane workflow. This needs an Actions budget, which this session is not authorized to spend.
  - **(b)** Define a separate "self-run candidate" evidence class that uses the #807 envelope as its contract. It needs:
    - its own place for normalized records, outside `reports/benchmarks/normalized/`, so scorecards and the catalog are not silently changed;
    - its own UI label;
    - a rule that it never shares a comparison set with lane rows unless the harness-equivalence check holds. That check holds here per question for lexical overlap; see `RECEIPT-AUDIT.md` section 3.

  **Recommendation: (b) now, with (a) only for systems worth a permanent lane.**
- **G2 Review authority.** The existing reviews (`independent-review-810.md`, `independent-review-812-graphiti.md`) were done by agents launched by the executing session. They are adversarial, but not independent of the executor in the governance sense. The owner needs to:
  - name an independent reviewer;
  - name an owner-only location for the review-authority record the checker consumes.
- **G3 (withdrawn after review).** No new input-digest rule is needed. The AMB rows use the frozen lane's own `input_sha256` (`caf5869b…`, SHA-256 over the raw fixture bytes in order).
- **G4 Public relabelling (P1) and the Pages guard (P2).** P1 needs the owner of `claude/817-jev-mem-execution-no-ci`. P2 needs the Pages owner (#807).

## D. Remains blocked by external resources (no metadata fix helps)

| Item | Needs |
|---|---|
| Graphiti on LongMemEval-S | sustained local compute, or approved hosted or GPU time |
| A valid LangMem row | a capable tool-calling model (GPU host or approved paid inference) |
| Graphiti with a frontier LLM, if wanted | approved paid inference |
| Jev-Mem | a CUDA host |
| Cognee generation 2 | owned by the cycle-2 lane; not this session |
| AML service | owner hold |

## E. Historical coverage (#808 item 6)

This is done, as a proposal, in `HISTORICAL-COVERAGE.md`. For the 69 normalized runs it records which fields were captured, and it backfills nothing. CPU/RAM/GPU, stdout/stderr digests and cost are `evidence_gap` for every historical run, as is per-run model identity for the 41 rows of systems that use a model. The envelope is not imposed retroactively, so the accepted lane rows are unaffected.
