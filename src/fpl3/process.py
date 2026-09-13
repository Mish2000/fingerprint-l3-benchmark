"""Versioned file/JSON process boundary, using Conda activation and no shell."""

from __future__ import annotations

import os
from pathlib import Path

from .code_identity import package_code
from .io import fingerprint, read_json, write_json
from .process_tree import run_managed
from .worker_protocol import SCHEMA


class WorkerError(RuntimeError):
    def __init__(self, message, *, quiescent=True):
        super().__init__(message)
        self.quiescent = quiescent


def invoke_worker(local, action, payload, directory, expected_code=None):
    """Worker receives explicit opaque inputs, not protocol truth or old roots."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    prefix = Path(local["workers"]["p1"]["prefix"]).resolve()
    executable = prefix / ("python.exe" if os.name == "nt" else "bin/python")
    if not executable.is_file():
        raise WorkerError("P1 Conda interpreter is missing")
    request = {"schema": SCHEMA, "action": action, "payload": payload,
               "expected_prefix": str(prefix), "response": str(directory / "response.json"),
               "code": package_code() if expected_code is None else expected_code}
    request["request_id"] = fingerprint(request)
    write_json(directory / "request.json", request)
    command = [str(local["conda_executable"]), "run", "--no-capture-output", "--prefix", str(prefix),
               str(executable), "-I", "-B", "-m", "fpl3.worker", "--request", str(directory / "request.json")]
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE"):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    write_json(directory / "invocation.json", {"argv": command, "shell": False})
    with (directory / "stdout.log").open("x", encoding="utf-8") as log:
        termination = run_managed(command, stdout=log, env=environment,
                                  timeout=local["workers"]["p1"].get("timeout_seconds", 1800))
    write_json(directory / "termination.json", termination)
    if termination["error"] or not termination["tree_quiescent"]:
        raise WorkerError(termination["error"] or "Worker tree is not quiescent",
                          quiescent=termination["tree_quiescent"])
    response_path = directory / "response.json"
    if not response_path.exists():
        raise WorkerError(f"Worker exited {termination['returncode']} without a complete response")
    try:
        response = read_json(response_path)
    except (OSError, ValueError) as exc:
        raise WorkerError("Worker response is not valid complete JSON") from exc
    if not isinstance(response, dict) or response.get("schema") != SCHEMA or response.get("request_id") != request["request_id"]:
        raise WorkerError("Worker response does not match request/version")
    if termination["returncode"] or response.get("status") != "success":
        raise WorkerError(f"Worker failed: {response.get('error', termination['returncode'])}")
    attestations = response.get("code_identity")
    if not isinstance(attestations, dict) or any(not isinstance(attestations.get(phase), dict)
            or attestations[phase].get("files") != request["code"] for phase in ("before", "after")):
        raise WorkerError("Worker code identity is missing or differs from request")
    if not isinstance(response.get("result"), dict):
        raise WorkerError("Worker result must be a JSON object")
    return response["result"]
