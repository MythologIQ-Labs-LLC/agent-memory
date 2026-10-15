"""Run the pinned, credential-free Hindsight v0.10.2 server as a standalone loopback service.

Same posture as the #751 H3 self-hosted smoke and longmemeval_hindsight_bridge: pinned clean
checkout, llm_provider=none with no key, embedded PostgreSQL (pg0), verified local ONNX
embeddings, reranker provider rrf (bank reranking is off). Writes its URL to --url-file and
serves until terminated. Must run as an unprivileged user (pg0 refuses root).
"""
import argparse, json, os, signal, sys, tempfile, threading, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agentmem_ref.evaluation.hindsight_bridge import HINDSIGHT_RELEASE  # noqa: E402
from agentmem_ref.evaluation.hindsight_model_snapshot import snapshot_identity  # noqa: E402
from agentmem_ref.evaluation.hindsight_selfhosted_smoke import isolated_environment, verify_pinned_checkout  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--url-file", type=Path, required=True)
    p.add_argument("--port", type=int, default=0)
    a = p.parse_args()
    verify_pinned_checkout(a.source_dir)
    identity = snapshot_identity(a.model_dir.resolve(strict=True))
    os.environ.update(isolated_environment(a.model_dir.resolve(strict=True)))
    import importlib.metadata
    if importlib.metadata.version("hindsight-all") != HINDSIGHT_RELEASE:
        raise SystemExit("installed Hindsight release differs from pinned 0.10.2")
    from hindsight import HindsightServer
    work = tempfile.mkdtemp(prefix="am-hindsight-server-")
    os.chdir(work)
    kwargs = dict(db_url="pg0", llm_provider="none", llm_api_key="", host="127.0.0.1", mcp_enabled=False, log_level="warning")
    if a.port:
        kwargs["port"] = a.port
    server = HindsightServer(**kwargs)
    if server.llm_provider != "none" or server.llm_api_key != "":
        raise SystemExit("server has a non-frozen LLM provider or credential")
    started = time.perf_counter()
    server.start(timeout=float(os.environ.get("AGENT_MEMORY_HINDSIGHT_START_TIMEOUT", "600")))
    a.url_file.write_text(json.dumps({"url": server.url, "cold_start_seconds": round(time.perf_counter() - started, 3),
                                       "model_snapshot": identity, "release": HINDSIGHT_RELEASE, "pid": os.getpid()}) + "\n")
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    try:
        server.stop()
    except RuntimeError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
