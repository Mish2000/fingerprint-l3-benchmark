"""Read-only run evidence checks; a file inventory never grants approval by itself."""

from pathlib import Path

from .contracts import MatchResult
from .io import digest, fingerprint, read_json, verify_files
from .results import coverage


def read_optional(path, problems):
    try:
        return read_json(path)
    except (OSError, ValueError) as exc:
        problems.append(f"{Path(path).name}: {type(exc).__name__}")
        return None


def observe_outputs(run, inputs, pairs, summary_name="worker-summary.json"):
    run, problems = Path(run), []
    rows = read_optional(run / "pairs.json", problems)
    valid_rows = []
    if isinstance(rows, list):
        for index, row in enumerate(rows):
            try:
                if index >= len(pairs) or any(row[k] != v for k, v in pairs[index].items()):
                    raise ValueError("Pair order, identity or side differs")
                MatchResult(row["status"], row["score"], row.get("reason"), row.get("failure_stage"),
                            row.get("score_direction", "higher_is_more_similar"), row.get("timings", {}),
                            row.get("matcher_invoked", False))
                valid_rows.append(row)
            except (KeyError, TypeError, ValueError) as exc:
                problems.append(f"Pair record {index}: {exc}")
                break
    if len(valid_rows) != len(pairs):
        problems.append("Pair outputs are incomplete or invalid")
    counts = coverage(valid_rows)
    counts.update(planned=len(pairs), recorded_pairs=len(valid_rows), unrecorded_pairs=len(pairs) - len(valid_rows))
    images = []
    for item in inputs:
        record = read_optional(run / "templates" / f"{item['key']}.json", problems)
        if not isinstance(record, dict) or record.get("key") != item["key"] or record.get("status") not in {"success", "failure", "blocked"}:
            problems.append(f"Image record missing or invalid: {item['key']}")
            continue
        images.append(record)
        if record.get("failure_category") == "infrastructure":
            problems.append(f"Image infrastructure failure: {item['key']}")
        if record["status"] == "success":
            payload = run / "templates" / f"{item['key']}.npz"
            if not payload.is_file() or record.get("npz_sha256") != digest(payload):
                problems.append(f"Image array missing or hash differs: {item['key']}")
    counts.update(images=len(inputs), recorded_images=len(images),
                  extraction_attempts=sum(r["status"] != "blocked" for r in images),
                  extraction_successes=sum(r["status"] == "success" for r in images),
                  cache_hits=sum(bool(r.get("cache_hit")) for r in images),
                  fresh_extractions=sum(r["status"] == "success" and not r.get("cache_hit") for r in images))
    summary = read_optional(run / summary_name, problems)
    if not isinstance(summary, dict):
        problems.append("Worker summary missing or invalid")
        summary = None
    else:
        for key in ("planned", "logical_attempts", "matcher_invocations", "success", "failure", "blocked", "pending",
                    "zero_scores", "images", "extraction_attempts", "extraction_successes", "cache_hits", "fresh_extractions"):
            if summary.get(key) != counts[key]:
                problems.append(f"Worker summary disagrees with recorded outputs: {key}")
    return {"counts": counts, "worker_summary": summary, "problems": problems,
            "rows": valid_rows, "images": images}


def _check_exchange(run, phase, identity, problems, modern):
    folder = run / "worker" / phase
    request = read_optional(folder / "request.json", problems)
    response = read_optional(folder / "response.json", problems)
    if not isinstance(request, dict) or not isinstance(response, dict):
        problems.append(f"{phase}: missing request/response")
        return None, None
    schema = "fpl3-worker-v2" if modern else "fpl3-worker-v1"
    expected_id = fingerprint({k: v for k, v in request.items() if k != "request_id"})
    if (request.get("schema") != schema or request.get("request_id") != expected_id
            or response.get("schema") != schema or response.get("request_id") != expected_id
            or response.get("status") != "success" or not isinstance(response.get("result"), dict)):
        problems.append(f"{phase}: invalid or unsuccessful worker acknowledgement")
    action = identity.get("worker_action", "run-p1")
    if action not in {"run-p1", "run-development-route"}:
        problems.append("Unknown declared worker action")
    if request.get("action") != ("doctor" if phase == "preflight" else action):
        problems.append(f"{phase}: incorrect worker action")
    if Path(request.get("response", "")).resolve() != (folder / "response.json").resolve():
        problems.append(f"{phase}: response destination differs")
    if modern:
        code = identity["signature"]["code"]
        if request.get("code") != code:
            problems.append(f"{phase}: requested code differs from run identity")
        for point in ("before", "after"):
            attestations = response.get("code_identity")
            attested = attestations.get(point) if isinstance(attestations, dict) else None
            if not isinstance(attested, dict) or attested.get("files") != code or not attested.get("loaded_modules"):
                problems.append(f"{phase}: missing/mismatched worker code {point}")
        termination = read_optional(folder / "termination.json", problems)
        if not isinstance(termination, dict) or (termination.get("returncode") != 0 or termination.get("error")
                or termination.get("timed_out") or termination.get("tree_quiescent") is not True):
            problems.append(f"{phase}: worker tree did not finish successfully and quiescently")
    return request, response.get("result") if isinstance(response.get("result"), dict) else None


def assess_run(run, inputs, pairs, receipt, receipt_sha256):
    """Inspect original bytes, including legacy v2 runs; never amend or execute them."""
    run, problems = Path(run).resolve(), []
    identity = read_optional(run / "identity.json", problems)
    seal = read_optional(run / "complete.json", problems)
    integrity = True
    try:
        files = seal["files"]
        actual = {p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and p != run / "complete.json"}
        if set(files) != actual:
            raise ValueError("Sealed file inventory is incomplete or has extra files")
        verify_files(run, files)
    except (OSError, TypeError, KeyError, ValueError) as exc:
        problems.append(f"Run is unsealed or its file integrity failed: {exc}")
        integrity = False
    if not isinstance(identity, dict) or identity.get("schema") not in {"fpl3-run-v2", "fpl3-run-v3"}:
        return {"eligible": False, "integrity_verified": integrity, "problems": problems + ["Unsupported run identity"],
                "code_assurance": "unavailable", "observations": None}
    modern = identity["schema"] == "fpl3-run-v3"
    observations = observe_outputs(run, inputs, pairs, "worker-summary.json" if modern else "summary.json")
    problems.extend(observations["problems"])
    if identity.get("import_receipt_sha256") != receipt_sha256 or identity.get("historical_identity_sha256") != receipt["historical_identity_sha256"]:
        problems.append("Run is not bound to the supplied reference receipt/identity")
    try:
        verify_files(run / "code", identity["signature"]["code"])
        if {p.name for p in (run / "code").glob("*.py")} != set(identity["signature"]["code"]):
            raise ValueError("Source snapshot membership differs")
        if identity["signature"]["config"] != read_json(run / "route.json"):
            raise ValueError("Run route and identity differ")
        if fingerprint(identity["signature"]["components"]) != fingerprint(read_json(run / "worker/execution/request.json")["payload"]["components"]):
            raise ValueError("Executed component closure differs")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        problems.append(f"Source/configuration binding failed: {exc}")
    coordinator = read_optional(run / "coordinator.json", problems)
    if not isinstance(coordinator, dict) or coordinator.get("error") is not None or "error" not in coordinator:
        problems.append("Coordinator has an unresolved error or no completion record")
    if (run / "process_failure.json").exists():
        problems.append("Unresolved process_failure record")
    pre_request, preflight = _check_exchange(run, "preflight", identity, problems, modern)
    request, response = _check_exchange(run, "execution", identity, problems, modern)
    if request:
        payload = request.get("payload", {})
        if payload.get("signature") != identity["signature"] or payload.get("inputs") != inputs or payload.get("pairs") != pairs:
            problems.append("Execution request differs from frozen source/protocol identity")
        if Path(payload.get("run_dir", "")).resolve() != run:
            problems.append("Execution request names another run")
        if not pre_request or request.get("expected_prefix") != pre_request.get("expected_prefix"):
            problems.append("Preflight and execution interpreter bindings differ")
    if not preflight or preflight.get("numerical_identity") != identity["signature"]["environment"]:
        problems.append("Preflight numerical identity differs")
    environment = read_optional(run / "worker-environment.json", problems)
    if not isinstance(environment, dict) or not preflight or environment != preflight.get("environment"):
        problems.append("Executed worker environment differs from preflight")
    elif request and (Path(environment["prefix"]).resolve() != Path(request["expected_prefix"]).resolve()
                      or not environment.get("isolated_packages") or environment.get("enable_user_site")
                      or environment.get("manager") != "conda"):
        problems.append("Executed worker prefix/isolation differs")
    if response != observations["worker_summary"] or response is None:
        problems.append("Worker acknowledgement and saved worker summary disagree")
    if observations["worker_summary"] and observations["worker_summary"].get("setup_error"):
        problems.append("Worker reports a setup block")
    if modern:
        summary = read_optional(run / "summary.json", problems)
        if not isinstance(summary, dict) or summary.get("run_status") != "success" or summary.get("evidence_eligible") is not True:
            problems.append("Authoritative run state does not permit use")
        else:
            for key, value in observations["counts"].items():
                if summary.get(key) != value:
                    problems.append(f"Authoritative summary disagrees with outputs: {key}")
            if summary.get("errors") or summary.get("finalized") is not True or summary.get("physical_calls_known") is not True:
                problems.append("Authoritative summary has unresolved finalization state")
        if not isinstance(coordinator, dict) or coordinator.get("run_status") != "success" or coordinator.get("summary_sha256") != digest(run / "summary.json"):
            problems.append("Coordinator and authoritative summary disagree")
        code_record = read_optional(run / "coordinator-code.json", problems)
        if not isinstance(code_record, dict) or any(not isinstance(code_record.get(p), dict)
                or code_record[p].get("files") != identity["signature"]["code"] for p in ("before", "after")):
            problems.append("Coordinator source changed or lacks drift checks")
    return {"eligible": integrity and not problems, "integrity_verified": integrity, "problems": problems,
            "code_assurance": "both_processes_before_and_after" if modern else "legacy_snapshot_and_request_only",
            "limitations": [] if modern else ["v2 did not record worker code attestation, coordinator end drift or tree exit status; these cannot be proved retroactively"],
            "observations": observations}
