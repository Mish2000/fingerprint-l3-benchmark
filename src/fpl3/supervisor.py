"""Step 02 preparation, bounded P1 execution and read-only approval.

Only this coordinator sees subjects, decision profiles or ground truth. Finger
partitions share no inputs or pairs and use unchanged four-thread P1 workers.
"""

import struct
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from .cache import cache_key, decode
from .code_identity import check_code, package_code
from .contracts import Image
from .io import digest, fingerprint, read_json, snapshot, verify_files, write_bytes, write_json
from .protocol import COHORT, load_import
from .run_state import assess_run
from .runner import read_local, run_bound_p1
from .supervisor_protocol import KINDS, build_manifest, opaque_work, select_threshold, summarize, validate_manifest


def utc():
    return datetime.now(timezone.utc).isoformat()


def seal(folder):
    folder = Path(folder)
    write_json(folder / "complete.json", {"meaning": "file_inventory_only",
               "files": snapshot(folder, [p for p in folder.rglob("*") if p.is_file()])})


def check_seal(folder):
    folder = Path(folder)
    files = read_json(folder / "complete.json")["files"]
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file() and p != folder / "complete.json"}
    if set(files) != actual:
        raise ValueError("Sealed supervisor inventory membership differs")
    verify_files(folder, files)


def prepare(local_path, specification, output):
    """Freeze from selected metadata and verified development scores only."""
    local, spec = read_local(local_path), read_json(specification)
    imported = Path(local["import_dir"])
    inputs, pairs, receipt = load_import(imported)
    plan = read_json(imported / "reference/plan.json")
    cohort = read_json(imported / "reference/cohort.json")
    closure = read_json(spec["closure_summary"])
    development = Path(spec["development_run"]).resolve()
    assessment = assess_run(development, inputs, pairs, receipt, digest(imported / "receipt.json"))
    if not assessment["eligible"] or closure.get("approved") is not True or closure.get("parity") != "exact":
        raise ValueError("Development source or Step 01 closure is not approved")
    if closure.get("run_identity_sha256") != digest(development / "identity.json"):
        raise ValueError("Closure approval does not name the selected development run")
    if (closure.get("run_complete_sha256") != digest(development / "complete.json")
            or closure.get("import_receipt_sha256") != digest(imported / "receipt.json")):
        raise ValueError("Closure source seal or import binding differs")
    route = read_json(local["route_config"])
    old_identity = read_json(development / "identity.json")
    if route != old_identity["signature"]["config"]:
        raise ValueError("Threshold source used another route configuration")
    negatives = [(p, r) for p, r in zip(plan["pairs"], assessment["observations"]["rows"]) if p["kind"] == "impostor"]
    if len(negatives) != 200 or any(r["status"] != "success" for _, r in negatives):
        raise ValueError("Require all 200 successful development impostor scores")
    profile = {"schema": "fpl3-decision-profile-v1", "route_id": route["route_id"],
               **select_threshold([r["score"] for _, r in negatives]), "max_false_accepts": 2,
               "selection_uses": "200 development impostors only; no genuine, SELF or evaluation scores",
               "limitation": "Small previously used development sample; no population FAR guarantee",
               "source": {"run_identity_sha256": digest(development / "identity.json"),
                          "run_seal_sha256": digest(development / "complete.json"),
                          "pairs_sha256": digest(development / "pairs.json"),
                          "closure_sha256": digest(spec["closure_summary"]),
                          "import_receipt_sha256": digest(imported / "receipt.json"),
                          "historical_code": old_identity["signature"]["code"],
                          "code_assurance": assessment["code_assurance"]},
               "selection_code": package_code(),
               "scores": [{"source_row_index": plan["pairs"].index(p), **r} for p, r in negatives]}
    metadata = read_json(spec["evaluation_metadata"])
    for source in metadata["sources"]:
        if digest(source["path"]) != source["sha256"]:
            raise ValueError("Source metadata file changed")
    if metadata["sources"][0]["sha256"] != read_json(imported / "reference/settings.json")["images_sha256"]:
        raise ValueError("Evaluation source catalog differs from the original SD300B metadata")
    if metadata["cohort_sha256"] != digest(imported / "reference/cohort.json") or cohort["cohort_id"] != COHORT:
        raise ValueError("Evaluation metadata is not bound to the original cohort")
    if set(plan["active_subjects"]) & set(cohort["subject_ids"]):
        raise ValueError("Development and evaluation subjects overlap")
    if len(cohort["subject_ids"]) != 50:
        raise ValueError("Evaluation requires the existing 50 subjects")
    dev_records = [{"subject_id": r["subject_id"], "impression": r["impression"], "position": r["position"],
                    "release": "SD300B", "image_id": r["image_id"], "relative_path": r["relative_path"],
                    **{k: item[k] for k in ("sha256", "width", "height", "source_ppi", "processing_ppi")}}
                   for r, item in zip(plan["images"], inputs)]
    provenance = {"cohort_sha256": digest(imported / "reference/cohort.json"),
                  "known_exposure": plan["known_exposure"], "historically_unexposed_claim": False,
                  "development_evaluation_overlap": [], "metadata_sources": metadata["sources"]}
    manifests = {"development": build_manifest(plan["active_subjects"], dev_records, "development", provenance),
                 "evaluation": build_manifest(cohort["subject_ids"], metadata["records"], "evaluation", provenance)}
    workers = spec.get("parallel_workers", 4)
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError("Use one to four bounded workers")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "decision_profile.json", profile)
    for role, manifest in manifests.items():
        write_json(output / f"{role}.json", manifest)
    write_json(output / "route.json", route)
    write_json(output / "specification.json", spec)
    code = package_code()
    check_code(code)
    for name in code:
        write_bytes(output / "code" / name, Path(__file__).with_name(name).read_bytes())
    frozen = {"schema": "fpl3-supervisor-freeze-v1", "created_utc": utc(), "evaluation_images_opened": False,
              "decision_sha256": digest(output / "decision_profile.json"), "route_sha256": digest(output / "route.json"),
              "manifest_sha256": {role: digest(output / f"{role}.json") for role in manifests},
              "local_sha256": digest(local_path), "code": code, "parallel_workers": workers,
              "partition": "anatomical finger, all subjects per partition, no repeated extraction",
              "components": old_identity["signature"]["components"],
              "numerical_environment": old_identity["signature"]["environment"],
              "source_baseline": spec["source_baseline"], "brief_sha256": digest(spec["brief"]),
              "validation_sha256": digest(spec["synthetic_validation"])}
    write_json(output / "freeze.json", frozen)
    seal(output)
    return {"prepared": True, "decision": {k: profile[k] for k in ("threshold", "comparison", "false_accepts", "denominator")},
            "manifests": {r: validate_manifest(m) for r, m in manifests.items()}}


def load_preparation(prepared, local_path):
    prepared = Path(prepared).resolve()
    check_seal(prepared)
    frozen = read_json(prepared / "freeze.json")
    if digest(local_path) != frozen["local_sha256"]:
        raise ValueError("Local execution settings changed after freeze")
    if digest(prepared / "decision_profile.json") != frozen["decision_sha256"]:
        raise ValueError("Decision profile changed after freeze")
    local = read_local(local_path)
    if digest(local["route_config"]) != frozen["route_sha256"]:
        # JSON formatting is immaterial; the frozen portable route is authoritative.
        if read_json(local["route_config"]) != read_json(prepared / "route.json"):
            raise ValueError("Route changed after freeze")
    for role in ("development", "evaluation"):
        if digest(prepared / f"{role}.json") != frozen["manifest_sha256"][role]:
            raise ValueError("Protocol changed after freeze")
        validate_manifest(read_json(prepared / f"{role}.json"))
    return local, frozen, read_json(prepared / "specification.json")


def check_sources(manifest, data_root):
    """Only called after freeze. Hash every permitted native PNG and check IHDR."""
    inputs, _ = opaque_work(manifest, data_root)
    checked = []
    for item in inputs[::2]:
        path = Path(item["path"])
        actual = digest(path)
        with path.open("rb") as stream:
            header = stream.read(33)
        if len(header) != 33 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise ValueError("Invalid native PNG header")
        width, height, depth, color = struct.unpack(">IIBB", header[16:26])
        if actual != item["sha256"] or (width, height, depth, color) != (item["width"], item["height"], 8, 0):
            raise ValueError("Source hash, geometry or native gray8 format changed")
        checked.append({"key": item["key"][:-2], "sha256": actual, "width": width, "height": height})
    return {"checked_utc": utc(), "source_images": len(checked), "inputs": checked}


def assess_partition(run, inputs, pairs, local, frozen, binding):
    imported = Path(local["import_dir"])
    receipt = read_json(imported / "receipt.json")
    assessment = assess_run(run, inputs, pairs, receipt, digest(imported / "receipt.json"))
    problems = list(assessment["problems"])
    try:
        identity = read_json(Path(run) / "identity.json")
        signature = identity["signature"]
        if identity.get("experiment") != binding or identity.get("fresh_inference_requested") is not True:
            raise ValueError("Partition does not bind the frozen experiment and fresh extraction")
        if (signature["code"] != frozen["code"] or signature["components"] != frozen["components"]
                or signature["environment"] != frozen["numerical_environment"]):
            raise ValueError("Partition code, components or numerical environment differs from freeze")
        if fingerprint(signature["config"]) != binding["route_fingerprint"]:
            raise ValueError("Partition route differs from freeze")
        records = assessment["observations"]["images"]
        for item, record in zip(inputs, records):
            if record.get("cache_hit") or record.get("status") == "blocked":
                raise ValueError("SELF requires independently invoked extraction on each side")
            if record.get("failure_stage") in {"cache", "cache_write", "setup"}:
                raise ValueError("Cache/setup infrastructure failure prevents approval")
            if record["status"] == "success":
                image = Image(**{**item, "path": Path(item["path"])})
                source, descriptors = decode(Path(run) / "templates" / f"{image.key}.npz", image)
                if (record["points"] != len(source.xy) or record["descriptors"] != len(descriptors.values)
                        or record.get("cache_key") != cache_key(image, signature)):
                    raise ValueError("Template counts or binding differ")
                if any(k not in record.get("timings", {}) for k in ("detection_seconds", "description_seconds")):
                    raise ValueError("Independent extraction timings are missing")
        if any(r["status"] in {"blocked", "pending"} for r in assessment["observations"]["rows"]):
            raise ValueError("Infrastructure gap is not a biometric rejection")
        if any(r["status"] == "success" and r.get("matcher_invoked") is not True
               for r in assessment["observations"]["rows"]):
            raise ValueError("Successful scores must come from actual matcher calls")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        problems.append(str(exc))
    return {"approved": assessment["eligible"] and not problems, "problems": problems,
            "counts": assessment["observations"]["counts"] if assessment["observations"] else {},
            "code_assurance": assessment["code_assurance"]}


def partition_binding(prepared, frozen, role, finger):
    return {"freeze_sha256": digest(Path(prepared) / "freeze.json"), "role": role, "finger_partition": finger,
            "manifest_sha256": frozen["manifest_sha256"][role], "decision_sha256": frozen["decision_sha256"],
            "route_fingerprint": fingerprint(read_json(Path(prepared) / "route.json"))}


def assess_supervisor(prepared, local_path, run):
    """Revalidate all ten v3 runs and the aggregate without running biometrics."""
    local, frozen, spec = load_preparation(prepared, local_path)
    run = Path(run).resolve()
    check_seal(run)
    identity = read_json(run / "identity.json")
    role = identity["role"]
    if identity["freeze_sha256"] != digest(Path(prepared) / "freeze.json"):
        raise ValueError("Aggregate refers to another freeze")
    manifest = read_json(Path(prepared) / f"{role}.json")
    if identity["coordinator_code_before"]["files"] != frozen["code"] or read_json(run / "coordinator-code-after.json")["files"] != frozen["code"]:
        raise ValueError("Aggregate coordinator source checks differ from freeze")
    if datetime.fromisoformat(identity["started_utc"]) <= datetime.fromisoformat(frozen["created_utc"]):
        raise ValueError("Execution must follow the protocol and decision freeze")
    source_before, source_after = read_json(run / "source-before.json"), read_json(run / "source-after.json")
    expected_sources = [{"key": r["key"], **{k: r[k] for k in ("sha256", "width", "height")}} for r in manifest["images"]]
    if any(s["inputs"] != expected_sources or s["source_images"] != len(expected_sources) for s in (source_before, source_after)):
        raise ValueError("Source hash and geometry checks are missing or disagree")
    partitions = []
    for finger in range(1, 11):
        inputs, pairs = opaque_work(manifest, spec["data_root"], finger)
        partitions.append(assess_partition(run / f"batches/f{finger:02}", inputs, pairs, local, frozen,
                                            partition_binding(prepared, frozen, role, finger)))
    approval = read_json(run / "approval.json")
    if (not approval["approved"] or not all(p["approved"] for p in partitions)
            or approval["partitions"] != partitions or approval["errors"]
            or approval["decision_sha256"] != frozen["decision_sha256"]):
        raise ValueError("At least one partition lacks valid complete evidence")
    rows = assemble_rows(run, manifest)
    if rows != read_json(run / "pairs.json"):
        raise ValueError("Aggregate scores differ from partition originals")
    report = summarize(manifest, rows, read_json(Path(prepared) / "decision_profile.json"))
    if report != read_json(run / "report.json"):
        raise ValueError("Aggregate decision report differs from frozen inputs")
    return {"approved": True, "partitions": partitions, "pairs": len(rows), "role": role}


def assemble_rows(run, manifest):
    rows = [r for finger in range(1, 11) for r in read_json(Path(run) / f"batches/f{finger:02}/pairs.json")]
    index = {r["pair_id"]: r for r in rows}
    if len(index) != len(rows) or set(index) != {p["pair_id"] for p in manifest["pairs"]}:
        raise ValueError("Partition pair coverage is incomplete or duplicated")
    return [index[p["pair_id"]] for p in manifest["pairs"]]


def run_supervisor(prepared, local_path, role, output, development_run=None):
    local, frozen, spec = load_preparation(prepared, local_path)
    if role not in {"development", "evaluation"}:
        raise ValueError("Unknown experiment role")
    check_code(frozen["code"])
    if role == "evaluation":
        if development_run is None:
            raise ValueError("Evaluation requires the completed new development protocol check")
        validation = assess_supervisor(prepared, local_path, development_run)
        if validation["role"] != "development":
            raise ValueError("An evaluation run cannot authorize another evaluation")
    manifest = read_json(Path(prepared) / f"{role}.json")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    write_json(output / "identity.json", {"schema": "fpl3-supervisor-run-v1", "role": role, "started_utc": utc(),
               "freeze_sha256": digest(Path(prepared) / "freeze.json"),
               "development_approval_sha256": digest(Path(development_run) / "approval.json") if development_run else None,
               "coordinator_code_before": check_code(frozen["code"])})
    source_before = check_sources(manifest, spec["data_root"])
    write_json(output / "source-before.json", source_before)
    receipt = read_json(Path(local["import_dir"]) / "receipt.json")
    def execute(finger):
        inputs, pairs = opaque_work(manifest, spec["data_root"], finger)
        binding = partition_binding(prepared, frozen, role, finger)
        destination = output / f"batches/f{finger:02}"
        try:
            run_bound_p1(local_path, destination, inputs, pairs, receipt, fresh=True, experiment=binding)
            return assess_partition(destination, inputs, pairs, local, frozen, binding)
        except Exception as exc:
            return {"approved": False, "problems": [f"{type(exc).__name__}: {exc}"], "counts": {}}
    dispatch = time.perf_counter()
    with ThreadPoolExecutor(max_workers=frozen["parallel_workers"]) as pool:
        checks = list(pool.map(execute, range(1, 11)))
    dispatch_seconds = time.perf_counter() - dispatch
    errors = [f"partition {i + 1}: {problem}" for i, c in enumerate(checks) for problem in c["problems"]]
    try:
        write_json(output / "coordinator-code-after.json", check_code(frozen["code"]))
        source_after = check_sources(manifest, spec["data_root"])
        write_json(output / "source-after.json", source_after)
        if source_before["inputs"] != source_after["inputs"]:
            raise ValueError("Source inputs changed during execution")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    approved = all(c["approved"] for c in checks) and not errors
    if approved:
        rows = assemble_rows(output, manifest)
        report = summarize(manifest, rows, read_json(Path(prepared) / "decision_profile.json"))
        write_json(output / "pairs.json", rows)
        write_json(output / "report.json", report)
        summaries = [read_json(output / f"batches/f{f:02}/worker-summary.json") for f in range(1, 11)]
        stage_seconds = {kind: sum(r["timings"]["comparison_seconds"] for p, r in zip(manifest["pairs"], rows)
                                  if p["kind"] == kind) for kind in KINDS}
        totals = {k: sum(s[k] for s in summaries) for k in ("fresh_extractions", "cache_hits", "matcher_invocations", "total_seconds")}
        image_timings = {k: sum(s["shared_image_timings"][k] for s in summaries)
                         for k in ("input_seconds", "detection_seconds", "description_seconds")}
        load = sum(s["model_and_adapter_load_seconds"] for s in summaries)
        write_json(output / "timings.json", {**totals, **image_timings, "matching_seconds": stage_seconds,
                   "worker_load_seconds": load, "worker_overhead_seconds": totals["total_seconds"] - load - sum(image_timings.values()) - sum(stage_seconds.values()),
                   "dispatch_wall_seconds": dispatch_seconds, "orchestrator_wall_seconds": time.perf_counter() - started,
                   "timing_note": "Worker times add across parallel processes; ALL/FILTERED reuse the same scores"})
    approval = {"schema": "fpl3-supervisor-approval-v1", "approved": approved, "role": role,
                "errors": errors, "partitions": checks, "decision_sha256": frozen["decision_sha256"],
                "criterion": "complete valid evidence, independent extractions and finite scores or explicit processing failures",
                "biometric_performance_is_approval_criterion": False, "finished_utc": utc()}
    write_json(output / "approval.json", approval)
    quiescent = all((output / f"batches/f{f:02}/complete.json").is_file() for f in range(1, 11))
    if quiescent:
        seal(output)
    return {"approved": approved, "role": role, "errors": errors, "sealed": quiescent,
            "source_images": len(manifest["images"]), "planned_pairs": len(manifest["pairs"])}
