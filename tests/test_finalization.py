"""Synthetic fault injection at the process boundary; no model or private data."""

import csv
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from fpl3 import runner, verification
from fpl3.code_identity import package_code
from fpl3.io import digest, fingerprint, read_json, snapshot, write_bytes, write_json
from fpl3.results import coverage


@pytest.fixture
def scenario(tmp_path, monkeypatch):
    import fpl3.process as process
    import fpl3.runtime as runtime
    config = read_json(Path(__file__).parents[1] / "configs/p1.json")
    ref, imported, artifacts = tmp_path / "import/reference", tmp_path / "import", tmp_path / "components"
    shared = {k: config["parameters"][k] for k in ("sift_scale", "median_blur", "clahe_clip", "ratio_threshold_on_squared_distance")}
    write_json(ref / "settings.json", {"P1": {k: v for k, v in config["parameters"].items() if k not in shared},
               "shared_descriptor_matcher": shared, "runtimes": {"pore_python": {}}})
    write_json(artifacts / "components.json", {})
    receipt = {"historical_identity_sha256": "a" * 64, "historical_revision": "synthetic-reference",
               "components_sha256": digest(artifacts / "components.json"), "population": {"subjects": 0}}
    write_json(imported / "receipt.json", receipt)
    inputs = []
    for i in range(2):
        source = tmp_path / f"synthetic-{i}.bin"
        write_bytes(source, f"synthetic non-biometric input {i}".encode())
        inputs.append({"key": f"image-{i}", "path": str(source), "sha256": digest(source), "width": 8,
                       "height": 7, "source_ppi": 1000, "processing_ppi": 1000})
    pairs = [{"pair_id": f"synthetic-{i}", "left": "image-0", "right": "image-1"} for i in range(3)]
    rows = [{**pair, "status": "success", "score": float(i), "reason": None, "failure_stage": None,
             "matcher_invoked": True, "timings": {"comparison_seconds": 0.0}} for i, pair in enumerate(pairs)]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["pair_id", "status", "score"])
    writer.writeheader()
    for row in rows:
        write_json(ref / f"P1/pairs/{row['pair_id']}.json", row)
        writer.writerow({k: row[k] for k in writer.fieldnames})
    write_bytes(ref / "P1/scores.csv", stream.getvalue().encode())
    points, descriptors = np.array([[1, 2]], dtype=np.float32), np.array([[0.25, 0.75]], dtype=np.float32)
    for item in inputs:
        key = item["key"]
        write_json(ref / f"P1/detections/{key}.json", {"status": "success", "pores": 1})
        write_json(ref / f"P1/templates/{key}.json", {"status": "success", "descriptors": 1})
        np.savez_compressed(ref / f"P1/detections/{key}.npz", points_xy=points)
        np.savez_compressed(ref / f"P1/templates/{key}.npz", points_xy=points, descriptors=descriptors)
    write_json(tmp_path / "route.json", config)
    local = {"schema": "fpl3-local-v2", "route_config": str(tmp_path / "route.json"),
             "import_dir": str(imported), "dev_prefix": sys.prefix, "third_party": str(artifacts),
             "cache_dir": str(tmp_path / "cache"), "conda_executable": "synthetic-boundary",
             "workers": {"p1": {"prefix": sys.prefix}}}
    local_path = tmp_path / "local.json"
    write_json(local_path, local)
    monkeypatch.setattr(runner, "load_import", lambda _: (inputs, pairs, receipt))
    monkeypatch.setattr(verification, "load_import", lambda _: (inputs, pairs, receipt))
    environment = {"manager": "conda", "prefix": sys.prefix, "isolated_packages": True, "enable_user_site": False}
    monkeypatch.setattr(runtime, "doctor", lambda *args: environment)
    state = {"fault": "none", "input": inputs, "pairs": pairs, "local": local_path, "root": tmp_path}

    def fake_managed(command, **kwargs):
        request = read_json(command[-1])
        destination = Path(request["response"])
        code = {"root": str(Path(runner.__file__).parent), "files": request["code"],
                "loaded_modules": {"fpl3.worker": str(Path(runner.__file__).with_name("worker.py"))}}
        response = {"schema": request["schema"], "request_id": request["request_id"], "status": "success",
                    "code_identity": {"before": code, "after": code}}
        term = {"returncode": 0, "tree_quiescent": True, "timed_out": False, "error": None}
        fault = state["fault"]
        if request["action"] == "doctor":
            if fault == "preflight":
                return {**term, "returncode": 2, "error": "injected preflight block"}
            response["result"] = {"environment": environment, "numerical_identity": {"fixture": True}}
        else:
            if fault in {"before", "unquiescent"}:
                return {**term, "returncode": 2, "error": "injected process failure", "tree_quiescent": fault != "unquiescent"}
            out = Path(request["payload"]["run_dir"])
            write_json(out / "worker-environment.json", environment)
            for item in inputs[:1] if fault == "partial" else inputs:
                path = out / f"templates/{item['key']}.npz"
                path.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(path, source_points_xy=points, points_xy=points,
                                    descriptors=descriptors, source_indices=np.array([0], dtype=np.int64))
                write_json(path.with_suffix(".json"), {"key": item["key"], "status": "success", "points": 1,
                           "descriptors": 1, "cache_hit": False, "npz_sha256": digest(path)})
            write_json(out / "pairs.json", rows[:1] if fault == "partial" else rows)
            if fault == "partial":
                return {**term, "returncode": 2, "error": "injected partial outputs"}
            summary = {**coverage(rows), "images": 2, "extraction_attempts": 2, "extraction_successes": 2,
                       "cache_hits": 0, "fresh_extractions": 2, "setup_error": None}
            if fault == "worker_counts":
                summary["success"] = 0
            write_json(out / "worker-summary.json", summary)
            state["original_outputs"] = {p.relative_to(out).as_posix(): digest(p) for p in out.rglob("*")
                                         if p.is_file() and not p.is_relative_to(out / "worker")}
            response["result"] = summary
            if fault == "missing_response":
                return term
            if fault == "malformed_response":
                write_bytes(destination, b"{partial JSON")
                return term
            if fault == "null_response":
                write_json(destination, None)
                return term
            if fault == "stale_response":
                response["request_id"] = "wrong"
            if fault == "wrong_result":
                response["result"] = {**summary, "success": 0}
            if fault == "wrong_code":
                response["code_identity"] = {}
            if fault == "null_code":
                response["code_identity"] = None
            if fault == "nonzero_exit":
                term["returncode"] = 2
        write_json(destination, response)
        return term

    monkeypatch.setattr(process, "run_managed", fake_managed)
    return state


def execute(scenario):
    run = scenario["root"] / "run"
    returned = runner.run_p1(scenario["local"], run, fresh=True)
    assert returned == read_json(run / "summary.json")
    checked = verification.verify_migration(scenario["local"], run, scenario["root"] / "verified")
    return run, returned, checked


def test_success_is_acknowledged_consistent_and_approved(scenario):
    run, returned, checked = execute(scenario)
    assert returned["run_status"] == "success" and returned["success"] == 3
    assert checked["approved"] and checked["parity"] == "exact"
    assert checked["verification_status"] == "passed" and not checked["evidence"]["limitations"]
    assert not (run / "process_failure.json").exists()


@pytest.mark.parametrize("fault", ["missing_response", "malformed_response", "stale_response", "wrong_result", "wrong_code", "nonzero_exit", "null_response", "null_code"])
def test_late_fault_keeps_exact_arrays_but_denies_approval(scenario, fault):
    scenario["fault"] = fault
    run, returned, checked = execute(scenario)
    assert returned["run_status"] == "infrastructure_failure" and returned["success"] == 3
    assert returned["physical_calls_known"] is False and returned["matcher_invocations"] is None
    assert checked["parity"] == "exact" and not checked["approved"]
    assert checked["verification_status"] == "rejected" and checked["evidence"]["problems"]
    assert read_json(run / "worker-summary.json")["success"] == 3
    assert (run / "process_failure.json").exists() and (run / "complete.json").exists()
    for name, sha in scenario["original_outputs"].items():
        assert digest(run / name) == sha


def test_worker_ack_and_summary_cannot_override_actual_coverage(scenario):
    scenario["fault"] = "worker_counts"
    run, returned, checked = execute(scenario)
    assert returned["success"] == 3 and returned["run_status"] == "infrastructure_failure"
    assert read_json(run / "worker-summary.json")["success"] == 0
    assert checked["parity"] == "exact" and not checked["approved"]


@pytest.mark.parametrize("fault, status, recorded", [("preflight", "blocked", 0), ("before", "infrastructure_failure", 0),
                                                   ("partial", "infrastructure_failure", 1), ("unquiescent", "infrastructure_failure", 0)])
def test_incomplete_outputs_are_reported_without_inventing_pair_failures(scenario, fault, status, recorded):
    scenario["fault"] = fault
    run, returned, checked = execute(scenario)
    assert returned["run_status"] == status and returned["recorded_pairs"] == recorded
    assert returned["unrecorded_pairs"] == 3 - recorded
    assert not checked["approved"] and checked["parity"] != "exact"
    assert (run / "complete.json").exists() is (fault != "unquiescent")
    if recorded == 0:
        assert not (run / "pairs.json").exists()


def test_coordinator_code_drift_rejects_complete_outputs(scenario, monkeypatch):
    original = runner.check_code
    calls = []
    def drift(expected):
        calls.append(True)
        if len(calls) == 2:
            raise ValueError("injected coordinator code drift")
        return original(expected)
    monkeypatch.setattr(runner, "check_code", drift)
    _, returned, checked = execute(scenario)
    assert returned["run_status"] == "infrastructure_failure"
    assert checked["parity"] == "exact" and not checked["approved"]


def _rewrite(path, value):
    # Only synthetic test artifacts are modified to exercise the read-only verifier.
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _reseal(run):
    _rewrite(run / "complete.json", {"files": snapshot(run, [p for p in run.rglob("*") if p.is_file() and p != run / "complete.json"])})


@pytest.mark.parametrize("late_error", [False, True])
def test_legacy_acknowledgement_checked_without_rewriting_original(scenario, late_error):
    run = scenario["root"] / "run"
    runner.run_p1(scenario["local"], run, fresh=True)
    identity = read_json(run / "identity.json")
    identity.update(schema="fpl3-run-v2", worker_protocol="fpl3-worker-v1")
    _rewrite(run / "identity.json", identity)
    _rewrite(run / "summary.json", read_json(run / "worker-summary.json"))
    _rewrite(run / "coordinator.json", {"error": "legacy late failure" if late_error else None})
    for phase in ("preflight", "execution"):
        folder = run / "worker" / phase
        request, response = read_json(folder / "request.json"), read_json(folder / "response.json")
        request.update(schema="fpl3-worker-v1")
        request.pop("code")
        request["request_id"] = fingerprint({k: v for k, v in request.items() if k != "request_id"})
        response.update(schema=request["schema"], request_id=request["request_id"])
        response.pop("code_identity")
        _rewrite(folder / "request.json", request)
        _rewrite(folder / "response.json", response)
    _reseal(run)
    before = snapshot(run, list(p for p in run.rglob("*") if p.is_file()))
    checked = verification.verify_migration(scenario["local"], run, scenario["root"] / "verified")
    assert checked["parity"] == "exact" and checked["approved"] is (not late_error)
    assert checked["evidence"]["code_assurance"] == "legacy_snapshot_and_request_only"
    assert checked["evidence"]["limitations"]
    assert snapshot(run, [p for p in run.rglob("*") if p.is_file()]) == before


def test_cli_requires_run_and_evidence_approval(monkeypatch, capsys):
    from fpl3.cli import main
    monkeypatch.setattr(runner, "run_p1", lambda *a: {"run_status": "infrastructure_failure", "success": 3, "planned": 3})
    assert main(["run-p1", "--local", "unused", "--out", "unused"]) == 2
    monkeypatch.setattr(verification, "verify_migration", lambda *a: {"approved": False, "parity": "exact"})
    assert main(["verify-migration", "--local", "unused", "--run", "unused", "--out", "unused"]) == 2
