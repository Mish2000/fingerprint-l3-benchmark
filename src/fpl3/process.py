"""Versioned file/JSON process boundary, using Conda activation and no shell."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .io import fingerprint, read_json, write_json
from .worker_protocol import SCHEMA


class WorkerError(RuntimeError):
    pass


def invoke_worker(local, action, payload, directory):
    """Worker receives explicit opaque inputs, not protocol truth or old roots."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    prefix = Path(local["workers"]["p1"]["prefix"]).resolve()
    executable = prefix / ("python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        raise WorkerError("P1 Conda interpreter is missing")
    request = {"schema": SCHEMA, "action": action, "payload": payload,
               "expected_prefix": str(prefix), "response": str(directory / "response.json")}
    request["request_id"] = fingerprint(request)
    write_json(directory / "request.json", request)
    command = [str(local["conda_executable"]), "run", "--no-capture-output", "--prefix", str(prefix),
               str(executable), "-I", "-B", "-m", "fpl3.worker", "--request", str(directory / "request.json")]
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    write_json(directory / "invocation.json", {"argv": command, "shell": False})
    try:
        with (directory / "stdout.log").open("x", encoding="utf-8") as log:
            result = subprocess.run(command, stdout=log, stderr=None, env=environment,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                    timeout=local["workers"]["p1"].get("timeout_seconds", 1800), check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkerError(f"Worker launch failed: {type(exc).__name__}: {exc}") from exc
    response_path = directory / "response.json"
    if not response_path.exists():
        raise WorkerError(f"Worker exited {result.returncode} without a complete response")
    try:
        response = read_json(response_path)
    except (OSError, ValueError) as exc:
        raise WorkerError("Worker response is not valid complete JSON") from exc
    if response.get("schema") != SCHEMA or response.get("request_id") != request["request_id"]:
        raise WorkerError("Worker response does not match request/version")
    if result.returncode or response.get("status") != "success":
        raise WorkerError(f"Worker failed: {response.get('error', result.returncode)}")
    if not isinstance(response.get("result"), dict):
        raise WorkerError("Worker result must be a JSON object")
    return response["result"]
