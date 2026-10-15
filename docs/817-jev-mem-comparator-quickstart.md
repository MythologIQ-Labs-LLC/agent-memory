# Jev-Mem external retrieval comparator, candidate (#817)

**Status:** executable bridge prepared, **not installed, executed against Jev-Mem, independently accepted, or numerically scored**. This bridge is separate from Agent Memory's runtime security/v8 and must not alter benchmark gold or native evaluators.

## Verified source interface

- Upstream: https://github.com/libingzheren/Jev-Mem at `7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44`; MIT, Python 3.11+.
- `MemoryBuilder.build(text, timestamp, metadata)` inserts graph nodes; `QueryEngine.query(question, top_k)` returns the native graph-selected `context.anchor_nodes`.
- Laya local configuration is `config/laya_mem.json` at Git blob `ae526c67ccadbdbcbca84f2c1459990809a963f9`.
- Bridge `reference/longmemeval_jev_mem_bridge.py` registers `jev_mem_laya` on the preexisting `reference/run_longmemeval.py` external-backend API.
- The bridge writes the frozen evaluator's exact corpus item text and ID into a fresh per-question graph, queries Jev's native engine with a 50-deep ranked budget, and maps outputs only via returned node metadata. It never sends the gold answer, `has_answer`, or correctness to Jev. This is a **mapped retrieval-only profile**, not Jev's native LoCoMo QA or its per-message LongMemEval benchmark profile.

## Cloud/local execution handoff (no hosted Actions)

In a network-authorized **isolated** evaluator workspace with sufficient disk/RAM for local Laya and MiniLM models:

```bash
git clone https://github.com/libingzheren/Jev-Mem.git /tmp/jev-mem-source
git -C /tmp/jev-mem-source checkout --detach 7ab0c73c6d8f4f611ad252c1e6ba8083f8df0e44
export JEV_MEM_SOURCE_ROOT=/tmp/jev-mem-source
python -m pip install -e '/tmp/jev-mem-source[laya]'
python -m unittest discover -s reference/tests -t reference -p 'test_817_jev_mem_bridge.py' -v
python reference/run_longmemeval.py \
  --external-backend longmemeval_jev_mem_bridge:install_longmemeval_jev_mem_backend \
  --backend jev_mem_laya --backend lexical_overlap \
  --input reference/fixtures/benchmarks/longmemeval/synthetic.json \
  --corpus-class synthetic --max-questions 3 \
  --granularity session --granularity turn \
  --output /tmp/jev-mem-smoke.json
```

Review the runner's `--help` on the actual head before execution; it is the contract source for the output flag. Initial model weights may download from Hugging Face. **Check resolved model revision, model hashes, versions, license and network egress before running; if any is unpinned, label this candidate only.** Laya inference is local, but no real execution cost is zero. Do not use a paid OpenAI key. If the Jev config falls back to MAGMA or the graph emits a result lacking a source ID, record that; never fabricate a retrieval success.

Run the same exact frozen input selection and evaluator on the current pinned Agent Memory control, Mem0 OSS, and lexical baseline as the next stage, collecting per-question raw rows and counts. Do not optimize parameters based on gold. Require an independent adapter/protocol review before accepted dashboard publication. Retain output even if incomplete, with `blocked_dependency` / `runtime_error` rather than a false zero.

## Validation status

The offline unit test module covers source/config pin refusal and deterministic graph-node-to-benchmark-ID mapping. It does not exercise real Jev/Laya, which needs the independent cloud/local workspace. Hardware, embedding and Laya weight digests, ingress/model calls, and full raw evidence are outstanding under #817 and #808.
