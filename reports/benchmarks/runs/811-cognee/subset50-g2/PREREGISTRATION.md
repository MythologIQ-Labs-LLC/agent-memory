# Cognee local (GLiNER, no LLM): 50-question LongMemEval-S, generation 2 (#811, #810)

**Status: preregistered before execution; candidate, not reviewed or accepted.** This supersedes
`../subset50/` (see `../subset50/ERRATUM-2026-10-15.md`). It is a new generation; rows from the two
generations are never pooled.

`preregistration.json` was written by `reference/run_longmemeval_resumable.py --preregister-only`
at 2026-10-15T13:31:15Z for **backend `cognee_gliner_local`** via
`longmemeval_cognee_bridge:install_longmemeval_cognee_backend`. Input sha256
`d6f21ea9…a3442`; selection seed `agent-memory-longmemeval-subset-v1`, 50 ids, ID-list sha256
`5266568e2e883b64e92e0da632d5e24c3fd61d8a447de7e629ebf93ef26a7339`; the same ids as `../subset50/`.
Planes `session` then `turn`. Evaluator `reference/run_longmemeval.py`, unchanged from `38f6a7d`.

## Configuration

The product and adapter configuration is unchanged from generation 1. Only identity recording is
added.

| Item | Value |
|---|---|
| Product | `cognee[gliner,fastembed]==1.6.4` from PyPI (tag commit `f154b32a9e544dac73e7ddf2010327cf9988edcd`) |
| Environment | installed under `../cognee-venv-freeze.txt`; the resulting freeze is byte-identical to it (197 entries) |
| Adapter | `reference/longmemeval_cognee_bridge.py` 0.1.1-candidate: public `remember` / `recall(top_k=50)`, prune before every question, opaque uuid5 ids |
| LLM | none. No key is present, and the bridge refuses to start if one is |
| Extraction model | `fastino/gliner2.5-base-v1` @ `54785d51df8d86a0d8f2eb212fec15871aad2c4d`, `model.safetensors` sha256 `7274094d…c277a` |
| Embedding model | fastembed `qdrant/bge-small-en-v1.5-onnx-q` @ `aa8f8b060edb00e03bfdd08813a2949946c8ba55`, `model_optimized.onnx` sha256 `51f1bd0a…f2431`; tokenizer files from `BAAI/bge-small-en-v1.5` @ `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` |
| Model provenance | Downloaded on first use by the product during the synthetic smoke. Every file is hashed in `model-pins.txt`. The scored run uses `HF_HUB_OFFLINE=1` against exactly these caches, and the hashes are re-checked after the run |
| Host | 4 vCPU, no GPU, run as an unprivileged user. It runs concurrently with the Hindsight full-500 run, so timings are not comparable |

Generation 1's model revisions were never recorded, so equality of the two generations' models
cannot be shown. That is one more reason generation 1 stays exploratory.
