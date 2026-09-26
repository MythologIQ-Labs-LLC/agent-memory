"""Transport execution for the system-neutral Agent Memory Gauntlet contract."""

from __future__ import annotations

import importlib
import json
import queue
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from typing import Any

from .gauntlet_contract import validate_manifest, validate_operation_envelope


class GauntletExecutionError(RuntimeError):
    """Execution failure with explicit attribution to one Gauntlet boundary."""

    def __init__(self, source: str, code: str, message: str):
        super().__init__(message)
        self.source = source
        self.code = code


def _load_callable(path: str) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    module_name, separator, attribute = path.partition(":")
    if not separator or not module_name or not attribute:
        raise GauntletExecutionError(
            "system_adapter",
            "invalid_callable",
            "in_process transport callable must use module:function syntax",
        )
    try:
        module = importlib.import_module(module_name)
        value = getattr(module, attribute)
    except (ImportError, AttributeError) as exc:
        raise GauntletExecutionError(
            "system_adapter",
            "callable_unavailable",
            f"unable to load adapter callable {path}: {exc}",
        ) from exc
    if not callable(value):
        raise GauntletExecutionError(
            "system_adapter",
            "callable_not_callable",
            f"adapter target is not callable: {path}",
        )
    return value


class AdapterSession:
    """One stateful adapter transport session for a Gauntlet run.

    ``in_process`` is intentionally restricted to repository-trusted fixtures. Arbitrary
    external code should enter through an explicit process boundary. ``stdio`` execution
    requires a caller opt-in because the manifest startup command is executable content.
    """

    def __init__(
        self,
        manifest: Mapping[str, Any],
        *,
        allow_external_process: bool = False,
        timeout_seconds: float = 10.0,
    ):
        self.manifest = validate_manifest(manifest)
        self.allow_external_process = allow_external_process
        self.timeout_seconds = timeout_seconds
        self._callable: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None
        self._process: subprocess.Popen[str] | None = None
        self._stdout_queue: queue.Queue[str | None] | None = None
        self._reader_thread: threading.Thread | None = None

    def __enter__(self) -> "AdapterSession":
        transport = self.manifest["transport"]
        kind = transport["kind"]
        if kind == "in_process":
            if self.manifest.get("metadata", {}).get("trusted_fixture") is not True:
                raise GauntletExecutionError(
                    "orchestrator",
                    "untrusted_in_process_adapter",
                    "in_process execution is restricted to manifests marked metadata.trusted_fixture=true",
                )
            self._callable = _load_callable(transport["callable"])
            return self
        if kind == "stdio":
            if not self.allow_external_process:
                raise GauntletExecutionError(
                    "orchestrator",
                    "external_process_opt_in_required",
                    "stdio adapter execution requires explicit external-process opt-in",
                )
            try:
                self._process = subprocess.Popen(
                    transport["startup"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                )
            except OSError as exc:
                raise GauntletExecutionError(
                    "system_adapter",
                    "startup_failed",
                    f"unable to start adapter process: {exc}",
                ) from exc
            assert self._process.stdout is not None
            self._stdout_queue = queue.Queue()

            def _reader() -> None:
                assert self._process is not None and self._process.stdout is not None
                for line in self._process.stdout:
                    self._stdout_queue.put(line)
                self._stdout_queue.put(None)

            self._reader_thread = threading.Thread(target=_reader, daemon=True)
            self._reader_thread.start()
            return self
        if kind == "http":
            raise GauntletExecutionError(
                "orchestrator",
                "transport_not_implemented",
                "http transport is declared by the contract but not implemented in Gauntlet alpha",
            )
        raise GauntletExecutionError("orchestrator", "unknown_transport", f"unknown transport: {kind}")

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._process is not None:
            if self._process.stdin is not None:
                try:
                    self._process.stdin.close()
                except OSError:
                    pass
            try:
                self._process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1.0)

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        validated = validate_operation_envelope(request)
        kind = self.manifest["transport"]["kind"]
        started = time.perf_counter()

        if kind == "in_process":
            assert self._callable is not None
            try:
                raw = self._callable(validated)
            except Exception as exc:
                raise GauntletExecutionError(
                    "system_adapter",
                    "adapter_exception",
                    f"in-process adapter raised {type(exc).__name__}: {exc}",
                ) from exc
        elif kind == "stdio":
            assert self._process is not None
            assert self._process.stdin is not None
            assert self._stdout_queue is not None
            if self._process.poll() is not None:
                raise GauntletExecutionError(
                    "system_adapter",
                    "adapter_exited",
                    f"adapter process exited with code {self._process.returncode}",
                )
            try:
                self._process.stdin.write(json.dumps(validated, sort_keys=True) + "\n")
                self._process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise GauntletExecutionError(
                    "system_adapter", "adapter_pipe_failed", str(exc)
                ) from exc
            try:
                line = self._stdout_queue.get(timeout=self.timeout_seconds)
            except queue.Empty as exc:
                self._process.kill()
                raise GauntletExecutionError(
                    "system_adapter",
                    "adapter_timeout",
                    f"adapter produced no response within {self.timeout_seconds:g}s",
                ) from exc
            if line is None:
                raise GauntletExecutionError(
                    "system_adapter",
                    "adapter_eof",
                    "adapter process closed stdout before producing a response",
                )
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise GauntletExecutionError(
                    "system_adapter",
                    "invalid_adapter_json",
                    f"adapter emitted invalid JSON: {exc}",
                ) from exc
        else:
            raise AssertionError(f"transport session entered unsupported kind: {kind}")

        if not isinstance(raw, Mapping):
            raise GauntletExecutionError(
                "system_adapter",
                "invalid_adapter_response",
                "adapter response must be a JSON object",
            )
        try:
            response = validate_operation_envelope(raw)
        except (KeyError, TypeError, ValueError) as exc:
            raise GauntletExecutionError(
                "system_adapter",
                "invalid_adapter_envelope",
                f"adapter emitted an invalid operation envelope: {exc}",
            ) from exc
        if response["direction"] != "response":
            raise GauntletExecutionError(
                "system_adapter", "wrong_direction", "adapter must emit a response envelope"
            )
        if response["request_id"] != validated["request_id"] or response["operation"] != validated["operation"]:
            raise GauntletExecutionError(
                "system_adapter",
                "response_correlation_mismatch",
                "adapter response does not correlate to the request",
            )
        response.setdefault("adapter_evidence", {})["orchestrator_elapsed_ms"] = max(
            0.0, (time.perf_counter() - started) * 1000.0
        )
        return response


__all__ = ["AdapterSession", "GauntletExecutionError"]
