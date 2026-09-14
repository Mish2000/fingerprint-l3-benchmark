"""Bounded Step 03 coordinator, using the existing attested Conda run contract."""

import ast
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .cache import decode
from .code_identity import check_code, package_code
from .contracts import Image
from .development_protocol import (GROUPS, ROUTES, build_development, calibrate, development_report,
                                   dp_config, split_original, validate_development)
from .io import digest, fingerprint, read_json, verify_files, write_bytes, write_json
from .protocol import load_import
from .run_state import assess_run
from .runner import read_local, run_development_route
from .supervisor import assess_supervisor, check_seal, check_sources, seal, utc
from .supervisor_protocol import KINDS, opaque_work


def adapter_equivalence(source_run):
    names = {"tiled_survey", "survey_xy", "load_survey", "load_dahia", "SurveyF40", "DahiaSift", "DahiaSpatial"}
    def selected(path):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        return {n.name: ast.dump(n, include_attributes=False) for n in tree.body if getattr(n, "name", None) in names}
    old = selected(Path(source_run) / "code/biometrics.py")
    current = selected(Path(__file__).with_name("biometrics.py"))
    if set(old) != names or old != current:
        raise ValueError("P1 adapter implementation differs; reuse equivalence is unproved")
    return {"adapter_ast_exact": True, "functions": sorted(names), "ast_sha256": fingerprint(old)}


def prepare_comparison(local_path, specification, output):
    local, spec = read_local(local_path), read_json(specification)
    imported = Path(local["import_dir"])
    _, _, receipt = load_import(imported)
    metadata = read_json(spec["metadata"])
    for source in metadata["sources"]:
        if digest(source["path"]) != source["sha256"]:
            raise ValueError("Original development metadata changed")
    plan = read_json(metadata["sources"][0]["path"])
    if digest(metadata["sources"][0]["path"]) != digest(imported / "reference/plan.json"):
        raise ValueError("Original twenty manifest differs from the verified l3_bridge_v1 import")
    groups = split_original(plan, read_json(imported / "reference/cohort.json"))
    if metadata["subjects"] != plan["selected_subjects"] or len(metadata["records"]) != 400:
        raise ValueError("Selected source metadata differs from original twenty")
    fixtures = read_json(spec["dp_fixtures"])
    if (fixtures.get("approved") is not True or fixtures["adapter_sha256"] != digest(Path(__file__).with_name("direct_pore.py"))
            or fixtures["reference_sha256"] != digest(Path(local["third_party"]) / "dahia/utils.py")):
        raise ValueError("Exact DP source equivalence has not passed for this code")
    tests = ET.parse(spec["synthetic_validation"]).getroot()
    if any(int(s.attrib.get(k, 0)) for s in tests.iter("testsuite") for k in ("failures", "errors", "skipped")):
        raise ValueError("Synthetic validation has failures, errors or skips")
    historical = assess_supervisor(spec["step02_prepared"], spec["step02_local"], spec["reuse_run"])
    if not historical["approved"] or historical["role"] != "development":
        raise ValueError("Historical independent a/b reuse source is not approved development")
    p1 = read_json(local["route_config"])
    first = Path(spec["reuse_run"]) / "batches/f01"
    old = read_json(first / "identity.json")["signature"]
    if p1 != old["config"]:
        raise ValueError("P1 control configuration changed")
    compatibility = adapter_equivalence(first)
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    output = output.resolve()
    provenance = {"original_plan_sha256": digest(metadata["sources"][0]["path"]),
                  "known_exposure": plan["known_exposure"], "unexposed_claim": False,
                  "development_evaluation_overlap": [], "selection": "original first ten / original last ten"}
    for group, subjects in groups.items():
        records = [r for r in metadata["records"] if r["subject_id"] in subjects]
        manifest = build_development(subjects, records, group, provenance)
        validate_development(manifest)
        write_json(output / f"{group}.json", manifest)
    for alias, config in (("sift", p1), ("dp32", dp_config(p1))):
        write_json(output / f"route-{alias}.json", config)
        settings = {**local, "route_config": str(output / f"route-{alias}.json"),
                    "p1_route_config": str(output / "route-sift.json"), "cache_dir": spec["cache_dir"]}
        write_json(output / f"local-{alias}.json", settings)
    code = package_code()
    for name in code:
        write_bytes(output / "code" / name, Path(__file__).with_name(name).read_bytes())
    write_json(output / "specification.json", spec)
    freeze = {"schema": "fpl3-step03-freeze-v1", "created_utc": utc(), "code": code,
              "baseline": "60145aa025e587aafff558b35c0c28abd7e65722", "components": old["components"],
              "numerical_environment": old["environment"], "p1_compatibility": compatibility,
              "manifest_sha256": {g: digest(output / f"{g}.json") for g in GROUPS},
              "import_receipt_sha256": digest(imported / "receipt.json"),
              "reuse_run_seal_sha256": digest(Path(spec["reuse_run"]) / "complete.json"),
              "evidence": {k: {"path": spec[k], "sha256": digest(spec[k])} for k in
                           ("brief", "metadata", "dp_fixtures", "synthetic_validation", "sift_probe")},
              "calibration_rule": "all 900 DEV-CAL negative attempts, budget floor(n_score_bearing/100), >=",
              "stop": "after DEV-CHECK; no evaluation cohort execution or recalibration",
              "parallel_workers": 4, "score_reuse": False}
    check_code(code)
    write_json(output / "freeze.json", freeze)
    seal(output)
    return {"prepared": True, "groups": {g: validate_development(read_json(output / f"{g}.json")) for g in GROUPS}}


def load_comparison(prepared):
    prepared = Path(prepared).resolve()
    check_seal(prepared)
    frozen = read_json(prepared / "freeze.json")
    for group in GROUPS:
        manifest = read_json(prepared / f"{group}.json")
        if digest(prepared / f"{group}.json") != frozen["manifest_sha256"][group]:
            raise ValueError("Frozen group changed")
        validate_development(manifest)
    for evidence in frozen["evidence"].values():
        if digest(evidence["path"]) != evidence["sha256"]:
            raise ValueError("Frozen validation evidence changed")
    return prepared, frozen, read_json(prepared / "specification.json")


def work(manifest, data_root, finger):
    inputs, _ = opaque_work(manifest["base"], data_root, finger)
    pairs = [{k: p[k] for k in ("pair_id", "left", "right")} for p in manifest["pairs"] if p["finger"] == finger]
    return inputs, pairs


def reuse_receipts(source_run, inputs, local, mode):
    source_run = Path(source_run).resolve()
    job = read_json(source_run / "worker/execution/request.json")["payload"]
    imported = Path(local["import_dir"])
    assessment = assess_run(source_run, job["inputs"], job["pairs"], read_json(imported / "receipt.json"),
                            digest(imported / "receipt.json"))
    if not assessment["eligible"]:
        raise ValueError(f"Reuse source is not approved: {assessment['problems']}")
    signature = read_json(source_run / "identity.json")["signature"]
    compatibility = adapter_equivalence(source_run)
    originals = {r["key"]: r for r in job["inputs"]}
    records = {r["key"]: r for r in assessment["observations"]["images"]}
    reused = {}
    for item in inputs:
        key = item["key"]
        if key not in originals:
            continue
        if originals[key] != item:
            raise ValueError("Source product image identity differs")
        record = records[key]
        if record["status"] != "success":
            continue
        if not key.endswith(("-a", "-b")):
            raise ValueError("Independent SELF side is missing")
        reused[key] = {"mode": mode, "image": item, "signature": signature,
                       "npz_path": str(source_run / "templates" / f"{key}.npz"), "npz_sha256": record["npz_sha256"],
                       "record_path": str(source_run / "templates" / f"{key}.json"),
                       "record_sha256": digest(source_run / "templates" / f"{key}.json"),
                       "source_run": str(source_run), "source_seal_sha256": digest(source_run / "complete.json"),
                       "compatibility": compatibility}
    return reused


def assess_development_partition(run, inputs, pairs, local, frozen, binding):
    run = Path(run)
    imported = Path(local["import_dir"])
    assessment = assess_run(run, inputs, pairs, read_json(imported / "receipt.json"), digest(imported / "receipt.json"))
    problems = list(assessment["problems"])
    try:
        identity = read_json(run / "identity.json")
        if identity.get("experiment") != binding or identity.get("worker_action") != "run-development-route":
            raise ValueError("Development experiment/worker binding differs")
        signature = identity["signature"]
        if any(signature[k] != frozen[v] for k, v in
               (("code", "code"), ("components", "components"), ("environment", "numerical_environment"))):
            raise ValueError("Development source or numerical signature differs")
        if signature["config"] != read_json(local["route_config"]):
            raise ValueError("Development route differs")
        reuse = read_json(run / "worker/execution/request.json")["payload"]["reuse"]
        for item, record in zip(inputs, assessment["observations"]["images"]):
            if record["status"] == "blocked" or record.get("failure_category") == "infrastructure":
                raise ValueError("Infrastructure gap blocks scientific approval")
            if record["status"] != "success":
                continue
            image = Image(**{**item, "path": Path(item["path"])})
            points, described = decode(run / "templates" / f"{item['key']}.npz", image)
            if record["points"] != len(points.xy) or record["descriptors"] != len(described.values):
                raise ValueError("Recorded extraction counts differ from arrays")
            reasons = record["point_filtering"]
            if ([r["source_index"] for r in reasons] != list(range(len(points.xy)))
                    or [r["source_index"] for r in reasons if r["reason"] is None] != described.source_indices.tolist()):
                raise ValueError("Point filtering and source indices differ")
            if item["key"] in reuse:
                from .feature_reuse import load_reused
                source, old_desc = load_reused(reuse[item["key"]], image, signature)
                import numpy as np
                if record.get("reuse") != reuse[item["key"]] or not np.array_equal(source.xy, points.xy):
                    raise ValueError("Reused source points or receipt differ")
                if old_desc is not None and (not np.array_equal(old_desc.values, described.values)
                        or not np.array_equal(old_desc.source_indices, described.source_indices)):
                    raise ValueError("Reused descriptor payload differs")
            elif not record.get("detector_invoked") or not record.get("descriptor_invoked"):
                raise ValueError("Missing independent fresh extraction evidence")
        if any(r["status"] in {"blocked", "pending"} or
               (r["status"] == "success" and not r["matcher_invoked"]) for r in assessment["observations"]["rows"]):
            raise ValueError("Every planned outcome needs a score-bearing matcher call or processing failure")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        problems.append(str(exc))
    return {"approved": not problems, "problems": problems, "counts": assessment["observations"]["counts"]}


def check_profile_gate(folder, prepared, cal_folder):
    check_seal(folder)
    gate = read_json(Path(folder) / "gate.json")
    if gate["freeze_sha256"] != digest(Path(prepared) / "freeze.json"):
        raise ValueError("Calibration gate belongs to another frozen experiment")
    for alias in ("sift", "dp32"):
        path = Path(folder) / f"{alias}.json"
        if digest(path) != gate["profiles"][alias]:
            raise ValueError("Calibration profile changed")
        profile = read_json(path)
        if (not profile.get("valid") or profile["source"]["pairs_sha256"] !=
                digest(Path(cal_folder) / f"pairs-{alias}.json")):
            raise ValueError("Calibration profile is invalid or its score source changed")
    return gate


def run_comparison(prepared, output):
    prepared, frozen, spec = load_comparison(prepared)
    check_code(frozen["code"])
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    output = output.resolve()
    wall_start = time.perf_counter()
    write_json(output / "identity.json", {"started_utc": utc(), "freeze_sha256": digest(prepared / "freeze.json"),
               "code_before": check_code(frozen["code"]), "scope": list(GROUPS)})
    if digest(Path(spec["reuse_run"]) / "complete.json") != frozen["reuse_run_seal_sha256"]:
        raise ValueError("Approved historical a/b reuse source changed")
    locals_ = {alias: read_local(prepared / f"local-{alias}.json") for alias in ("sift", "dp32")}
    summaries = {}
    for group in GROUPS:
        manifest = read_json(prepared / f"{group}.json")
        group_out = output / group
        group_out.mkdir()
        gate = None
        if group == "DEV-CHECK":
            gate = check_profile_gate(output / "profiles", prepared, output / "DEV-CAL")
        write_json(group_out / "started.json", {"started_utc": utc(), "calibration_gate": gate})
        source_before = check_sources(manifest["base"], spec["data_root"])
        write_json(group_out / "source-before.json", source_before)
        def run_finger(finger):
            inputs, pairs = work(manifest, spec["data_root"], finger)
            decisions = {}
            for alias in ("sift", "dp32"):
                check_code(frozen["code"])
                local = locals_[alias]
                run = group_out / alias / f"f{finger:02}"
                binding = {"freeze_sha256": digest(prepared / "freeze.json"), "group": group, "finger": finger,
                           "manifest_sha256": frozen["manifest_sha256"][group],
                           "route_sha256": digest(prepared / f"route-{alias}.json"),
                           "calibration_gate_sha256": digest(output / "profiles/gate.json") if gate else None}
                reuse = {}
                if alias == "sift" and group == "DEV-CAL":
                    reuse = reuse_receipts(Path(spec["reuse_run"]) / f"batches/f{finger:02}", inputs, local, "descriptors")
                elif alias == "dp32":
                    reuse = reuse_receipts(group_out / "sift" / f"f{finger:02}", inputs, local, "points")
                    # Every successful SIFT product must supply the same detector points.
                    if len(reuse) != len(inputs):
                        raise ValueError("Shared f40 products incomplete; cannot silently redetect only for DP")
                run_development_route(prepared / f"local-{alias}.json", run, inputs, pairs,
                                      read_json(Path(local["import_dir"]) / "receipt.json"), experiment=binding, reuse=reuse,
                                      diagnostic_pairs=[manifest["base"]["examples"][k] for k in KINDS]
                                      if finger == 1 and group == "DEV-CAL" else [])
                approved = assess_development_partition(run, inputs, pairs, local, frozen, binding)
                write_json(group_out / f"approval-{alias}-f{finger:02}.json", approved)
                if not approved["approved"]:
                    raise ValueError(f"{group}/{alias}/f{finger:02} not approved: {approved['problems']}")
                decisions[alias] = approved
                print(f"{group}/{alias}/f{finger:02} approved", flush=True)
            return decisions
        # The first fixed finger partition is the feasibility batch; never repeated.
        approvals = [run_finger(1)]
        with ThreadPoolExecutor(max_workers=frozen["parallel_workers"]) as pool:
            approvals += list(pool.map(run_finger, range(2, 11)))
        source_after = check_sources(manifest["base"], spec["data_root"])
        write_json(group_out / "source-after.json", source_after)
        if source_before["inputs"] != source_after["inputs"]:
            raise ValueError("Development source drift")
        group_summary = {}
        for alias in ("sift", "dp32"):
            collected = [r for finger in range(1, 11) for r in read_json(group_out / alias / f"f{finger:02}/pairs.json")]
            indexed = {r["pair_id"]: r for r in collected}
            if len(indexed) != len(collected) or set(indexed) != {p["pair_id"] for p in manifest["pairs"]}:
                raise ValueError("Duplicate or missing partition outcomes")
            rows = [indexed[p["pair_id"]] for p in manifest["pairs"]]
            write_json(group_out / f"pairs-{alias}.json", rows)
            records = [read_json(path) for finger in range(1, 11)
                       for path in (group_out / alias / f"f{finger:02}/templates").glob("*.json")]
            group_summary[alias] = {"images": len(records), "source_points": sum(r.get("points", 0) for r in records),
                                   "descriptors": sum(r.get("descriptors", 0) for r in records),
                                   "detector_calls": sum(r.get("detector_invoked", False) for r in records),
                                   "descriptor_calls": sum(r.get("descriptor_invoked", False) for r in records),
                                   "reused_points": sum(r.get("points_reused", False) for r in records),
                                   "reused_descriptors": sum(r.get("cache_hit", False) for r in records),
                                   "matcher_calls": sum(r["matcher_invoked"] for r in rows),
                                   "point_exclusions": sum(bool(p["reason"]) for r in records for p in r.get("point_filtering", []))}
        check_code(frozen["code"])
        write_json(group_out / "approval.json", {"approved": True, "partitions": approvals, "summary": group_summary,
                   "code_after": check_code(frozen["code"])})
        seal(group_out)
        summaries[group] = group_summary
        if group == "DEV-CAL":
            profiles = output / "profiles"
            profiles.mkdir()
            for alias, route in zip(("sift", "dp32"), ROUTES):
                source = {"pairs_sha256": digest(group_out / f"pairs-{alias}.json"),
                          "run_seal_sha256": digest(group_out / "complete.json"),
                          "manifest_sha256": frozen["manifest_sha256"][group],
                          "freeze_sha256": digest(prepared / "freeze.json")}
                profile = calibrate(manifest, read_json(group_out / f"pairs-{alias}.json"), route, source)
                write_json(profiles / f"{alias}.json", profile)
                if not profile["valid"]:
                    raise ValueError("No valid calibration profile; DEV-CHECK remains blocked")
            write_json(profiles / "gate.json", {"frozen_utc": utc(), "freeze_sha256": digest(prepared / "freeze.json"),
                       "profiles": {a: digest(profiles / f"{a}.json") for a in ("sift", "dp32")},
                       "DEV_CHECK_scores_computed": False, "DEV_CHECK_scores_read": False})
            seal(profiles)
            print("Both DEV-CAL profiles sealed before DEV-CHECK", flush=True)
    for group in GROUPS:
        for alias in ("sift", "dp32"):
            report = development_report(read_json(prepared / f"{group}.json"),
                                        read_json(output / group / f"pairs-{alias}.json"),
                                        read_json(output / "profiles" / f"{alias}.json"))
            write_json(output / "reports" / f"{group}-{alias}.json", report)
    write_json(output / "approval.json", {"approved": True, "groups": summaries,
               "wall_seconds": time.perf_counter() - wall_start, "code_after": check_code(frozen["code"]),
               "new_evaluation_pairs": 0,
               "new_matcher_calls": sum(r["matcher_calls"] for group in summaries.values() for r in group.values()),
               "score_reuse": 0})
    seal(output)
    return read_json(output / "approval.json")
