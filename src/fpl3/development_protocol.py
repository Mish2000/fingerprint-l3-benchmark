"""Step 03 ordered development split, linked ring views and calibration only."""

import math
from collections import Counter

from .contracts import MatchResult
from .io import fingerprint
from .supervisor_protocol import KINDS, build_manifest, decision, select_threshold, summarize

ROUTES = ("ASM-F40-SIFT-SPATIAL", "ASM-F40-DP32-SPATIAL")
GROUPS = ("DEV-CAL", "DEV-CHECK")
DP_PARAMETERS = {"dp_patch_size": 32, "dp_pixels": "float32_0_1", "dp_orientation": "sparse-exact-v1"}


def dp_config(p1):
    parameters = {k: v for k, v in p1["parameters"].items() if k not in {"sift_scale", "median_blur", "clahe_clip"}}
    return {"route_id": ROUTES[1], "detector": "survey_f40", "descriptor": "dahia_dp32",
            "matcher": "dahia_spatial", "parameters": {**parameters, **DP_PARAMETERS},
            "descriptor_equivalence": {"mode": "exact", "atol": 0, "rtol": 0}}


def split_original(plan, cohort):
    subjects = plan["selected_subjects"]
    if (len(subjects) != 20 or len(set(subjects)) != 20 or subjects[:5] != plan["active_subjects"]
            or len(plan["active_subjects"]) != 5 or set(subjects) & set(cohort["subject_ids"])):
        raise ValueError("Require the original ordered twenty, original five prefix and no evaluation overlap")
    return {GROUPS[0]: subjects[:10], GROUPS[1]: subjects[10:]}


def build_development(subjects, records, group, provenance):
    if group not in GROUPS or len(subjects) != 10:
        raise ValueError("Step 03 requires DEV-CAL or DEV-CHECK with ten original subjects")
    base = build_manifest(subjects, records, "development", {**provenance, "step03_group": group})
    ring = {(p["left"], p["right"]): p for p in base["pairs"] if p["kind"] == KINDS[3]}
    by_slot = {(r["subject_id"], r["impression"], r["position"]): r for r in base["images"]}
    negatives = []
    for left_subject in subjects:
        for right_subject in subjects:
            if left_subject == right_subject:
                continue
            for finger in range(1, 11):
                left, right = by_slot[left_subject, "plain", finger], by_slot[right_subject, "roll", finger]
                key = (left["key"] + "-a", right["key"] + "-a")
                pair = ring.get(key)
                if pair is None:
                    pair = {"left": key[0], "right": key[1], "left_source": left["key"],
                            "right_source": right["key"], "left_unit": left["unit"], "right_unit": right["unit"],
                            "finger": finger, "kind": "development_extended_non_mated", "ground_truth": "non_mated"}
                    pair["pair_id"] = "s3pair-" + fingerprint({"group": group, **pair})[:24]
                negatives.append(pair)
    pairs = [p for p in base["pairs"] if p["kind"] != KINDS[3]] + negatives
    return {"schema": "fpl3-development-comparison-v1", "group": group, "base": base, "pairs": pairs,
            "views": {"supervisor": [p["pair_id"] for p in base["pairs"]],
                      "ring": [p["pair_id"] for p in base["pairs"] if p["kind"] == KINDS[3]],
                      "extended_impostors": [p["pair_id"] for p in negatives]},
            "reuse_rule": "ring references 100 of the same 900 outcomes; no extra matcher calls"}


def validate_development(manifest):
    base = manifest["base"]
    records = [{k: v for k, v in r.items() if k not in {"key", "unit"}} for r in base["images"]]
    provenance = {k: v for k, v in base["provenance"].items() if k != "step03_group"}
    if manifest != build_development(base["subjects"], records, manifest["group"], provenance):
        raise ValueError("Development population, ordering or view links changed")
    if len({(p["left"], p["right"]) for p in manifest["pairs"]}) != 1200:
        raise ValueError("Duplicate/missing physical comparisons")
    return {"images": 200, "unique_pairs": 1200, "ring_links": 100, "extended_impostors": 900}


def ordered_rows(manifest, rows):
    validate_development(manifest)
    if len(rows) != 1200 or any(any(r[k] != p[k] for k in ("pair_id", "left", "right"))
                               for p, r in zip(manifest["pairs"], rows)):
        raise ValueError("Incomplete, reordered or substituted development outcomes")
    for row in rows:
        MatchResult(row["status"], row["score"], row.get("reason"), row.get("failure_stage"),
                    row.get("score_direction", "higher_is_more_similar"), row.get("timings", {}),
                    row.get("matcher_invoked", False))
        if row["status"] in {"blocked", "pending"}:
            raise ValueError("Infrastructure gap blocks scientific approval")
    return {r["pair_id"]: r for r in rows}


def calibrate(manifest, rows, route, source):
    if manifest["group"] != "DEV-CAL" or route not in ROUTES:
        raise ValueError("Only the fixed DEV-CAL negatives can select a profile")
    indexed = ordered_rows(manifest, rows)
    negatives = [indexed[key] for key in manifest["views"]["extended_impostors"]]
    successful = [r for r in negatives if r["status"] == "success"]
    n = len(successful)
    budget = n // 100
    profile = {"schema": "fpl3-development-decision-v1", "profile_id": f"step03-{route}-DEV-CAL-1pct",
               "route_id": route, "group": "DEV-CAL", "attempt_denominator": 900, "score_denominator": n,
               "failures": 900 - n, "max_false_accepts": budget, "source": source,
               "selection_uses": "all score-bearing DEV-CAL extended impostors; no SELF filtering, genuine or DEV-CHECK",
               "selection_rows": negatives, "valid": bool(n)}
    if n:
        selected = select_threshold([r["score"] for r in successful], budget)
        if selected["comparison"] != ">=":
            raise ValueError("No finite binary64 boundary above maximum for required >= rule")
        profile.update(selected)
        profile["false_acceptance_rate_all_attempts"] = selected["false_accepts"] / 900
    else:
        profile.update(threshold=None, comparison=">=", reason="no_score_bearing_calibration_impostors")
    return profile


def development_report(manifest, rows, profile):
    indexed = ordered_rows(manifest, rows)
    if not profile.get("valid") or not math.isfinite(profile["threshold"]):
        raise ValueError("No valid calibration decision profile")
    report = summarize(manifest["base"], [indexed[k] for k in manifest["views"]["supervisor"]], profile)
    eligible = {r["unit"] for r in report["eligibility"] if r["eligible"]}
    selected_ids = set(manifest["views"]["extended_impostors"])
    detail = []
    for pair in manifest["pairs"]:
        if pair["pair_id"] in selected_ids:
            row = indexed[pair["pair_id"]]
            detail.append({**row, "decision": decision(row, profile),
                           "self_eligible": pair["left_unit"] in eligible and pair["right_unit"] in eligible,
                           "in_ring": pair["pair_id"] in manifest["views"]["ring"]})
    appendix = []
    for view in ("ALL", "SELF_FILTERED"):
        selected = [r for r in detail if view == "ALL" or r["self_eligible"]]
        counts = Counter(r["decision"] for r in selected)
        appendix.append({"view": view, "attempt_denominator": len(selected),
                         "score_denominator": sum(r["status"] == "success" for r in selected),
                         **{k: counts[k] for k in ("MATCH", "NON_MATCH", "PROCESSING_FAILURE")}})
    return {"group": manifest["group"], "route_id": profile["route_id"], "profile_id": profile["profile_id"],
            "supervisor": report, "extended_impostors": appendix, "extended_results": detail,
            "unique_comparisons": 1200, "ring_view_references": 100,
            "limitation": "Development only; shared images/subjects are dependent; no population FAR guarantee"}
