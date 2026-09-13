"""Immutable reference comparison, separate from biometric execution."""

import csv
import io
import math
from pathlib import Path

import numpy as np

from .contracts import MatchResult
from .code_identity import package_code
from .io import digest, read_json, write_bytes, write_json
from .run_state import assess_run
from .protocol import load_import


def numeric_difference(old, new):
    old, new = np.asarray(old), np.asarray(new)
    if not np.isfinite(old).all() or not np.isfinite(new).all():
        raise ValueError("Nonfinite numeric evidence")
    if old.shape != new.shape:
        return {"exact": False, "shape_equal": False, "max_absolute": None, "max_relative": None}
    delta = np.abs(old.astype(np.float64) - new.astype(np.float64))
    unbounded = bool(((old == 0) & (delta != 0)).any())
    relative = np.divide(delta, np.abs(old), out=np.zeros_like(delta), where=old != 0)
    return {"exact": bool(np.array_equal(old, new)), "shape_equal": True,
            "dtype_equal": old.dtype == new.dtype,
            "max_absolute": float(delta.max(initial=0)),
            "max_relative": None if unbounded else float(relative.max(initial=0)),
            "relative_unbounded_at_zero": unbounded}


def validate_score_row(row):
    MatchResult(row["status"], row["score"], row.get("reason"), row.get("failure_stage"),
                row.get("score_direction", "higher_is_more_similar"), row.get("timings", {}),
                row.get("matcher_invoked", False))


def verify_migration(local_path, run_dir, out_dir):
    local, run, out = read_json(local_path), Path(run_dir).resolve(), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    inputs, pairs, receipt = load_import(local["import_dir"])
    ref = Path(local["import_dir"]) / "reference"
    evidence = assess_run(run, inputs, pairs, receipt, digest(Path(local["import_dir"]) / "receipt.json"))
    identity = read_json(run / "identity.json")
    policy = identity["signature"]["config"]["parity_policy"]
    if policy != {"mode": "exact", "atol": 0, "rtol": 0}:
        raise ValueError("This migration verifier only implements predeclared exact parity")
    source_hashes = 0
    for item in inputs:
        try:
            if digest(item["path"]) != item["sha256"]:
                raise ValueError("Source image hash changed")
            source_hashes += 1
        except (OSError, ValueError) as exc:
            evidence["problems"].append(f"Source {item['key']}: {exc}")
            evidence["eligible"] = False
    component_file = Path(local["third_party"]) / "components.json"
    if digest(component_file) != receipt["components_sha256"] or read_json(component_file) != identity["signature"]["components"]:
        evidence["eligible"] = False
        evidence["problems"].append("Component manifest differs from reference/run")
    observed = evidence.pop("observations") or {"rows": [], "images": [], "counts": {}, "worker_summary": None}
    new_by_id = {r["pair_id"]: r for r in observed["rows"]} if evidence["integrity_verified"] else {}
    old_rows = list(csv.DictReader((ref / "P1/scores.csv").open(encoding="utf-8", newline="")))
    if len(old_rows) != len(pairs):
        raise ValueError("Reference pair coverage mismatch")
    comparisons = []
    score_abs, score_rel, statuses_equal, score_exact, old_zeros, new_zeros = 0., 0., 0, 0, 0, 0
    for pair, old in zip(pairs, old_rows):
        if old["pair_id"] != pair["pair_id"]:
            raise ValueError("Reference pair order differs")
        old_score = float(old["score"]) if old["score"] else None
        if old["status"] == "success" and (old_score is None or not math.isfinite(old_score)):
            raise ValueError("Invalid successful reference score")
        if old["status"] != "success" and old_score is not None:
            raise ValueError("Reference failure has score")
        raw = read_json(ref / f"P1/pairs/{pair['pair_id']}.json")
        if raw["score"] != old_score or raw["status"] != old["status"] or any(raw[k] != v for k, v in pair.items()):
            raise ValueError("Historical pair JSON and CSV disagree")
        new = new_by_id.get(pair["pair_id"], {"status": "unrecorded", "score": None})
        same_status, same_score = old["status"] == new["status"], old_score == new["score"]
        statuses_equal += same_status
        score_exact += same_score
        old_zeros += old_score == 0
        new_zeros += new["score"] == 0
        difference = None if old_score is None or new["score"] is None else new["score"] - old_score
        if difference is not None:
            score_abs = max(score_abs, abs(difference))
            score_rel = max(score_rel, abs(difference) / abs(old_score)) if old_score else score_rel
        comparisons.append({"pair_id": pair["pair_id"], "old_status": old["status"], "new_status": new["status"],
                            "old_score": old_score, "new_score": new["score"], "difference": difference,
                            "status_equal": same_status, "score_exact": same_score})
    image_rows = []
    new_images = {r["key"]: r for r in observed["images"]} if evidence["integrity_verified"] else {}
    for item in inputs:
        key = item["key"]
        old_detection = read_json(ref / f"P1/detections/{key}.json")
        old_description = read_json(ref / f"P1/templates/{key}.json")
        new = new_images.get(key, {"status": "unrecorded"})
        row = {"key": key, "new_status": new["status"], "old_detection_status": old_detection["status"],
               "old_description_status": old_description["status"], "new_points": new.get("points"),
               "old_points": old_detection.get("pores"), "new_descriptors": new.get("descriptors"),
               "old_descriptors": old_description.get("descriptors"), "reference_arrays_available": False}
        paths = [ref / f"P1/detections/{key}.npz", ref / f"P1/templates/{key}.npz", run / f"templates/{key}.npz"]
        if all(p.exists() for p in paths) and new["status"] == "success":
            try:
                with np.load(paths[0], allow_pickle=False) as det, np.load(paths[1], allow_pickle=False) as desc, np.load(paths[2], allow_pickle=False) as fresh:
                    row["points"] = numeric_difference(det["points_xy"], fresh["source_points_xy"])
                    row["retained_points"] = numeric_difference(desc["points_xy"], fresh["points_xy"])
                    row["descriptors"] = numeric_difference(desc["descriptors"], fresh["descriptors"])
                    row["source_mapping_exact"] = bool(np.array_equal(fresh["source_indices"], np.arange(len(det["points_xy"])))
                                                         and np.array_equal(det["points_xy"], desc["points_xy"]))
                    row["reference_arrays_available"] = True
            except (OSError, ValueError, KeyError) as exc:
                evidence["eligible"] = False
                evidence["problems"].append(f"Array comparison {key}: {exc}")
        image_rows.append(row)
    evidence["recorded_counts"] = observed["counts"]
    try:
        saved_summary = read_json(run / "summary.json")
    except (OSError, ValueError):
        saved_summary = None
    result = {"schema": "fpl3-migration-v2", "parity_policy": policy, "evidence": evidence,
              "input_and_pair_order_identity_roles": "exact" if len(new_by_id) == len(pairs) else "incomplete_or_invalid",
              "source_images_sha256_verified": source_hashes,
              "images": len(inputs), "pairs": len(pairs), "status_exact_pairs": statuses_equal,
              "score_exact_pairs": score_exact, "scores_max_absolute_difference": score_abs,
              "scores_max_relative_difference": None if any(r["old_score"] == 0 and r["difference"] not in (None, 0) for r in comparisons) else score_rel,
              "old_zero_scores": old_zeros, "new_zero_scores": new_zeros,
              "reference_arrays_available_images": sum(r["reference_arrays_available"] for r in image_rows),
              "points_exact_images": sum(r.get("points", {}).get("exact", False) for r in image_rows),
              "descriptors_exact_images": sum(r.get("descriptors", {}).get("exact", False) for r in image_rows),
              "retained_points_exact_images": sum(r.get("retained_points", {}).get("exact", False) for r in image_rows),
              "source_mapping_exact_images": sum(r.get("source_mapping_exact", False) for r in image_rows),
              "old_total_points": sum(r["old_points"] or 0 for r in image_rows),
              "new_total_points": sum(r["new_points"] or 0 for r in image_rows),
              "array_max_absolute_difference": {s: max((r.get(s, {}).get("max_absolute") or 0 for r in image_rows), default=0)
                                                  for s in ("points", "retained_points", "descriptors")},
              "run": saved_summary,
              "population": receipt["population"],
              "historical_revision": receipt["historical_revision"], "historical_identity_sha256": receipt["historical_identity_sha256"],
              "import_receipt_sha256": identity["import_receipt_sha256"], "run_identity_sha256": digest(run / "identity.json"),
              "run_complete_sha256": digest(run / "complete.json") if (run / "complete.json").is_file() else None,
              "components_sha256": receipt["components_sha256"], "biometric_accuracy_claim": False,
              "verifier_code": package_code(), "original_run_modified": False, "model_inference_performed": False}
    result["parity"] = "exact" if (statuses_equal == score_exact == len(pairs) and all(result[k] == len(inputs) for k in
                           ("points_exact_images", "descriptors_exact_images", "retained_points_exact_images", "source_mapping_exact_images"))) else "partial_or_mismatch"
    if not evidence["integrity_verified"]:
        result["parity"] = "not_evaluated"
    result["fresh_extraction_verified"] = observed["counts"].get("fresh_extractions") == len(inputs)
    result["approved"] = evidence["eligible"] and result["parity"] == "exact" and result["fresh_extraction_verified"]
    result["verification_status"] = ("passed_legacy_evidence" if evidence["limitations"] else "passed") if result["approved"] else "rejected"
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
    writer.writeheader()
    writer.writerows(comparisons)
    write_bytes(out / "migration_comparison.csv", stream.getvalue().encode())
    write_json(out / "migration_images.json", image_rows)
    write_json(out / "migration_summary.json", result)
    return result
