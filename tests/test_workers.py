import json
import subprocess
import sys
from pathlib import Path

import pytest

from fpl3.io import fingerprint, read_json, write_json
from fpl3.process import SCHEMA, WorkerError, invoke_worker
from fpl3.worker import validate_opaque_job


def test_coordinator_doctor_does_not_import_model_frameworks(tmp_path):
    code = "from fpl3.runtime import doctor; import sys; d=doctor(); assert set(d['packages']) == {'numpy'}; assert not any(x in sys.modules for x in ['torch','cv2','tensorflow','fpbench']); print(d['python'])"
    subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=tmp_path, check=True, capture_output=True)


def test_worker_does_not_load_coordinator_or_private_protocol(tmp_path):
    code = "import fpl3.worker, sys; assert not any(m in sys.modules for m in ['fpl3.runner','fpl3.process','fpl3.protocol','fpl3.importer','fpbench'])"
    subprocess.run([sys.executable, "-I", "-B", "-c", code], cwd=tmp_path, check=True, capture_output=True)


@pytest.mark.parametrize("fault", ["unknown_action", "wrong_prefix", "changed_request"])
def test_worker_protocol_roundtrip_rejects_invalid_requests(tmp_path, fault):
    directory = tmp_path / "path with spaces"
    directory.mkdir()
    request = {"schema": SCHEMA, "action": "unknown", "payload": {},
               "expected_prefix": str(directory if fault == "wrong_prefix" else Path(sys.prefix)),
               "response": str(directory / "response.json")}
    request["request_id"] = fingerprint(request)
    if fault == "changed_request":
        request["payload"] = {"changed": True}
    write_json(directory / "request.json", request)
    process = subprocess.run([sys.executable, "-I", "-B", "-m", "fpl3.worker", "--request", str(directory / "request.json")],
                             cwd=directory, capture_output=True, text=True)
    assert process.returncode == 2
    response = read_json(directory / "response.json")
    assert response["status"] == "failure" and response["request_id"] == request["request_id"]
    expected = {"unknown_action": "Unknown worker action", "wrong_prefix": "wrong interpreter", "changed_request": "checksum changed"}
    assert expected[fault] in response["error"]


def test_worker_job_forbids_truth_and_duplicate_bindings():
    job = {k: {} for k in ("config", "components", "signature", "expected_runtime")}
    job.update(artifacts="unused", cache_dir="unused", run_dir="unused", fresh=True,
               inputs=[{"key": "a", "path": "unused", "sha256": "a" * 64, "width": 20,
                        "height": 30, "source_ppi": 1000, "processing_ppi": 1000}],
               pairs=[{"pair_id": "p", "left": "a", "right": "a"}])
    validate_opaque_job(job)
    job["pairs"][0]["kind"] = "genuine"
    with pytest.raises(ValueError, match="truth"):
        validate_opaque_job(job)
    job["pairs"][0].pop("kind")
    job["inputs"].append(job["inputs"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        validate_opaque_job(job)


def test_missing_conda_worker_is_explicit(tmp_path):
    local = {"workers": {"p1": {"prefix": str(tmp_path / "missing")}}}
    with pytest.raises(WorkerError, match="interpreter is missing"):
        invoke_worker(local, "doctor", {}, tmp_path / "dispatch")


def test_stale_worker_response_rejected(monkeypatch, tmp_path):
    import fpl3.process as process
    local = {"conda_executable": "unused", "workers": {"p1": {"prefix": sys.prefix}}}
    def fake_run(command, **kwargs):
        assert kwargs.get("shell", False) is False
        request = read_json(command[-1])
        write_json(request["response"], {"schema": SCHEMA, "request_id": "stale", "status": "success", "result": {}})
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(process.subprocess, "run", fake_run)
    with pytest.raises(WorkerError, match="does not match"):
        invoke_worker(local, "doctor", {}, tmp_path / "dispatch")
