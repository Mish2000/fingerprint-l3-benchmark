"""Immutable reference comparison, separate from biometric execution."""

import csv
import io
import math
from pathlib import Path

import numpy as np

from .contracts import MatchResult
from .io import digest, read_json, verify_files, write_bytes, write_json
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
    local, run, out = read_json(local_path), Path(run_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    inputs, pairs, receipt = load_import(local["import_dir"])
    ref = Path(local["import_dir"]) / "reference"
    verify_files(run, read_json(run / "complete.json")["files"])
    identity = read_json(run / "identity.json")
    if identity["import_receipt_sha256"] != digest(Path(local["import_dir"]) / "receipt.json"):
        raise ValueError("Reference receipt differs from executed run")
    if identity["historical_identity_sha256"] != receipt["historical_identity_sha256"]:
        raise ValueError("Reference historical identity differs")
    policy = identity["signature"]["config"]["parity_policy"]
    if policy != {"mode": "exact", "atol": 0, "rtol": 0}:
        raise ValueError("This migration verifier only implements predeclared exact parity")
    new_rows = read_json(run / "pairs.json")
    old_rows = list(csv.DictReader((ref / "P1/scores.csv").open(encoding="utf-8", newline="")))
    if len(new_rows) != len(pairs) or len(old_rows) != len(pairs):
        raise ValueError("Pair coverage mismatch")
    comparisons = []
    score_abs, score_rel, statuses_equal, score_exact, old_zeros, new_zeros = 0., 0., 0, 0, 0, 0
    for pair, old, new in zip(pairs, old_rows, new_rows):
        if old["pair_id"] != pair["pair_id"] or any(new[k] != v for k, v in pair.items()):
            raise ValueError("Reference/new pair order, identity or side differs")
        validate_score_row(new)
        old_score = float(old["score"]) if old["score"] else None
        if old["status"] == "success" and (old_score is None or not math.isfinite(old_score)):
            raise ValueError("Invalid successful reference score")
        if old["status"] != "success" and old_score is not None:
            raise ValueError("Reference failure has score")
        raw = read_json(ref / f"P1/pairs/{pair['pair_id']}.json")
        if raw["score"] != old_score or raw["status"] != old["status"] or any(raw[k] != v for k, v in pair.items()):
            raise ValueError("Historical pair JSON and CSV disagree")
        same_status = old["status"] == new["status"]
        same_score = old_score == new["score"]
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
    for item in inputs:
        key = item["key"]
        old_detection = read_json(ref / f"P1/detections/{key}.json")
        old_description = read_json(ref / f"P1/templates/{key}.json")
        new = read_json(run / f"templates/{key}.json")
        row = {"key": key, "new_status": new["status"], "old_detection_status": old_detection["status"],
               "old_description_status": old_description["status"], "new_points": new.get("points"),
               "old_points": old_detection.get("pores"), "new_descriptors": new.get("descriptors"),
               "old_descriptors": old_description.get("descriptors"), "reference_arrays_available": False}
        paths = [ref / f"P1/detections/{key}.npz", ref / f"P1/templates/{key}.npz", run / f"templates/{key}.npz"]
        if all(p.exists() for p in paths) and new["status"] == "success":
            row["reference_arrays_available"] = True
            with np.load(paths[0], allow_pickle=False) as det, np.load(paths[1], allow_pickle=False) as desc, np.load(paths[2], allow_pickle=False) as fresh:
                row["points"] = numeric_difference(det["points_xy"], fresh["source_points_xy"])
                row["retained_points"] = numeric_difference(desc["points_xy"], fresh["points_xy"])
                row["descriptors"] = numeric_difference(desc["descriptors"], fresh["descriptors"])
                row["source_mapping_exact"] = bool(np.array_equal(fresh["source_indices"], np.arange(len(det["points_xy"])))
                                                     and np.array_equal(det["points_xy"], desc["points_xy"]))
        image_rows.append(row)
    result = {"schema": "fpl3-migration-v1", "parity_policy": policy,
              "input_and_pair_order_identity_roles": "exact", "source_images_sha256_verified": 100,
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
              "run": read_json(run / "summary.json"), "population": receipt["population"],
              "historical_revision": receipt["historical_revision"], "historical_identity_sha256": receipt["historical_identity_sha256"],
              "import_receipt_sha256": identity["import_receipt_sha256"], "run_identity_sha256": digest(run / "identity.json"),
              "components_sha256": receipt["components_sha256"], "biometric_accuracy_claim": False}
    result["parity"] = "exact" if (statuses_equal == score_exact == 250 and all(result[k] == 100 for k in
                           ("points_exact_images", "descriptors_exact_images", "retained_points_exact_images", "source_mapping_exact_images"))
                           and result["run"]["fresh_extractions"] == 100) else "partial_or_mismatch"
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
    writer.writeheader()
    writer.writerows(comparisons)
    write_bytes(out / "migration_comparison.csv", stream.getvalue().encode())
    write_json(out / "migration_images.json", image_rows)
    write_json(out / "migration_summary.json", result)
    return result
