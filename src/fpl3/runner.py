"""Composition, extraction sharing and pair execution; truth stays in protocol."""

from __future__ import annotations

import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .io import digest, read_json, snapshot, write_bytes, write_json
from .protocol import load_import
from .process import WorkerError, invoke_worker
from .results import coverage, execute_pairs


def read_local(path):
    local = read_json(path)
    if local.get("schema") != "fpl3-local-v2":
        raise ValueError("Use the Conda local configuration schema fpl3-local-v2")
    return local


def doctor_with_workers(local_path):
    from .runtime import doctor
    local = read_local(local_path)
    result = {"development": doctor("dev")}
    scratch = Path(local_path).resolve().parent
    with tempfile.TemporaryDirectory(prefix="doctor-", dir=scratch) as tmp:
        try:
            result["p1"] = invoke_worker(local, "doctor", {}, Path(tmp) / "worker")["environment"]
        except WorkerError as exc:
            result["p1"] = {"status": "blocked", "error": str(exc)}
    return result


def check_p1_via_worker(local_path, output):
    local = read_local(local_path)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    return invoke_worker(local, "check-p1-numerics", {"artifacts": local["third_party"], "output": str(output)},
                         output.with_suffix(".worker"))


def run_p1(local_path, run_dir, fresh=False):
    """Modern coordinator: validate protocol, dispatch opaque job, seal evidence."""
    from .runtime import doctor
    started = time.perf_counter()
    local = read_local(local_path)
    config = read_json(local["route_config"])
    inputs, pairs, receipt = load_import(local["import_dir"])
    reference = read_json(Path(local["import_dir"]) / "reference/settings.json")
    historical = {**reference["P1"], **{k: reference["shared_descriptor_matcher"][k]
                  for k in ("sift_scale", "median_blur", "clahe_clip", "ratio_threshold_on_squared_distance")}}
    if config["parameters"] != historical or config["route_id"] != "ASM-F40-SIFT-SPATIAL":
        raise ValueError("P1 numerical behavior differs from imported settings")
    if [config[s] for s in ("detector", "descriptor", "matcher")] != ["survey_f40", "dahia_sift", "dahia_spatial"]:
        raise ValueError("This CLI command is restricted to historical P1")
    environment = doctor("dev")
    if environment["manager"] != "conda" or not environment["isolated_packages"] or environment["enable_user_site"]:
        raise ValueError("Development coordinator must run in its isolated Conda environment")
    if Path(sys.prefix).resolve() != Path(local["dev_prefix"]).resolve():
        raise ValueError("Use the configured development interpreter to coordinate a run")
    out = Path(run_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "environment.json", environment)
    components = read_json(Path(local["third_party"]) / "components.json")
    if digest(Path(local["third_party"]) / "components.json") != receipt["components_sha256"]:
        raise ValueError("Component lock changed")
    code_root = Path(__file__).parent
    code_files = snapshot(code_root, list(code_root.glob("*.py")))
    for p in code_root.glob("*.py"):
        write_bytes(out / "code" / p.name, p.read_bytes())
    write_json(out / "route.json", config)
    error, numerical = None, None
    try:
        probe = invoke_worker(local, "doctor", {}, out / "worker/preflight")
        numerical = probe["numerical_identity"]
        if probe["environment"]["manager"] != "conda" or not probe["environment"]["isolated_packages"]:
            raise WorkerError("Worker preflight isolation failed")
    except WorkerError as exc:
        error = str(exc)
    signature = {"config": config, "components": components, "environment": numerical, "code": code_files}
    identity = {"schema": "fpl3-run-v2", "started_utc": datetime.now(timezone.utc).isoformat(),
                "route_id": config["route_id"], "historical_alias": "P1", "fresh_inference_requested": fresh,
                "import_receipt_sha256": digest(Path(local["import_dir"]) / "receipt.json"),
                "historical_identity_sha256": receipt["historical_identity_sha256"],
                "local_config_sha256": digest(local_path), "signature": signature,
                "coordinator_environment": environment, "worker_protocol": "fpl3-worker-v1",
                "code_identity": "executed file bytes, no new Git commit"}
    write_json(out / "identity.json", identity)
    job = {"inputs": inputs, "pairs": pairs, "config": config, "components": components,
           "artifacts": local["third_party"], "cache_dir": local["cache_dir"], "run_dir": str(out),
           "signature": signature, "fresh": fresh, "expected_runtime": reference["runtimes"]["pore_python"]}
    if not error:
        try:
            summary = invoke_worker(local, "run-p1", job, out / "worker/execution")
        except WorkerError as exc:
            error = str(exc)
    if error:
        # A process-level failure is not 250 biometric rejections. If a worker
        # died during matching, do not invent a precise physical call count.
        results = execute_pairs(pairs, {}, {}, None, error)
        if not (out / "pairs.json").exists():
            write_json(out / "pairs.json", results)
        summary = {**coverage(results), "images": len(inputs), "fresh_extractions": 0,
                   "setup_error": error, "physical_calls_known": not (out / "worker/execution").exists()}
        if not summary["physical_calls_known"]:
            summary["matcher_invocations"] = None
        if not (out / "summary.json").exists():
            write_json(out / "summary.json", summary)
        write_json(out / "process_failure.json", {"error": error})
    write_json(out / "coordinator.json", {"total_seconds": time.perf_counter() - started,
                                          "worker_protocol": "fpl3-worker-v1", "error": error})
    write_json(out / "complete.json", {"files": snapshot(out, [p for p in out.rglob("*") if p.is_file()])})
    return summary
