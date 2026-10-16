# Jev-Mem CPU fp32 subset run: stopped (2026-10-16)

**Why it was stopped.** The owner authorised stopping the CPU run on 2026-10-16. It had held about 3 of 4 vCPUs for more than a day, and the external lane records Jev-Mem as blocked on GPU (`BLOCKER-2026-10-15.md`).

**How it ended.** A container restart at about 00:14Z ended the process first, so no exec record was written for the final segment.

**What remains.** `session.jev_mem_laya.rows.jsonl` holds **8 of 50** session-plane rows. All are valid JSON, CPU fp32, with Laya `7b928d8`.

**Status.** These are partial rows with no score. Per `HANDOFF.md`, CPU fp32 rows must never be pooled with CUDA bf16 rows. Resume only on a CUDA host under the handoff.
