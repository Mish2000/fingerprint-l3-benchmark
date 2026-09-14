import copy

import pytest

from fpl3.development_protocol import (build_development, calibrate, development_report, split_original,
                                       validate_development)
from fpl3.io import fingerprint
from fpl3.supervisor_protocol import KINDS


def manifest(group="DEV-CAL"):
    subjects = [f"{k:08}" for k in (19, 3, 21, 4, 61, 7, 12, 1, 43, 8)]
    records = []
    for s in subjects:
        for imp in ("plain", "roll"):
            for finger in range(1, 11):
                frgp = {1: 11, 6: 12}.get(finger, finger) if imp == "plain" else finger
                records.append({"subject_id": s, "impression": imp, "position": finger, "release": "SD300B",
                                "image_id": f"synthetic-{s}-{imp}-{finger}", "sha256": fingerprint([s, imp, finger]),
                                "relative_path": f"{s}_{imp}_1000_{frgp:02}.png", "width": 128, "height": 96,
                                "source_ppi": 1000, "processing_ppi": 1000})
    return build_development(subjects, records, group, {"synthetic": True})


def results(plan):
    return [{**{k: p[k] for k in ("pair_id", "left", "right")}, "status": "success", "score": float(i),
             "reason": None, "failure_stage": None, "matcher_invoked": True, "timings": {}}
            for i, p in enumerate(plan["pairs"])]


def test_ring_links_and_directed_negatives_preserve_all_slots_and_wrap():
    plan = manifest()
    assert validate_development(plan) == {"images": 200, "unique_pairs": 1200, "ring_links": 100, "extended_impostors": 900}
    assert set(plan["views"]["ring"]) <= set(plan["views"]["extended_impostors"])
    assert len(plan["views"]["supervisor"]) == 400
    index = {p["pair_id"]: p for p in plan["pairs"]}
    for key in plan["views"]["extended_impostors"]:
        p = index[key]
        assert p["left_unit"] // 10 != p["right_unit"] // 10
        assert p["left_unit"] % 10 == p["right_unit"] % 10 == p["finger"] - 1
    for key in plan["views"]["ring"]:
        p = index[key]
        assert (p["left_unit"] // 10 + 1) % 10 == p["right_unit"] // 10
    assert plan["base"]["subjects"][0] == "00000019"


@pytest.mark.parametrize("fault", ["subjects", "views", "pairs", "role"])
def test_protocol_rejects_reselection_reordering_and_broken_links(fault):
    plan = manifest()
    if fault == "subjects":
        plan["base"]["subjects"].sort()
    elif fault == "views":
        plan["views"]["ring"][0] = plan["views"]["supervisor"][0]
    elif fault == "pairs":
        plan["pairs"].reverse()
    else:
        plan["group"] = "evaluation"
    with pytest.raises(ValueError):
        validate_development(plan)


def test_original_twenty_split_never_sorts_and_rejects_bad_prefix_or_overlap():
    selected = [str(k) for k in range(20, 0, -1)]
    plan = {"selected_subjects": selected, "active_subjects": selected[:5]}
    cohort = {"subject_ids": ["protected"]}
    assert split_original(plan, cohort) == {"DEV-CAL": selected[:10], "DEV-CHECK": selected[10:]}
    with pytest.raises(ValueError):
        split_original(plan, {"subject_ids": [selected[-1]]})
    plan["active_subjects"].reverse()
    with pytest.raises(ValueError):
        split_original(plan, cohort)


def test_calibration_uses_only_negatives_with_failure_budget_and_no_self_filter():
    plan = manifest()
    rows = results(plan)
    for row in rows[:300]:
        row["score"] = 1e20
    rows[-1].update(status="failure", score=None, reason="decode", failure_stage="input")
    profile = calibrate(plan, rows, "ASM-F40-SIFT-SPATIAL", {})
    assert (profile["score_denominator"], profile["attempt_denominator"], profile["max_false_accepts"]) == (899, 900, 8)
    assert profile["false_accepts"] == 8 and profile["threshold"] == 1191
    assert profile["failures"] == 1
    for row in rows[:300]:
        row["score"] = 0
    assert calibrate(plan, rows, "ASM-F40-SIFT-SPATIAL", {}) == profile


def test_calibration_preserves_ties_zeros_and_empty_scored_population():
    plan, rows = manifest(), results(manifest())
    for row in rows:
        row["score"] = 0.0
    profile = calibrate(plan, rows, "ASM-F40-DP32-SPATIAL", {})
    assert profile["valid"] and profile["threshold"] > 0 and profile["false_accepts"] == 0
    for row in rows[300:]:
        row.update(status="failure", score=None, reason="description", failure_stage="description")
    profile = calibrate(plan, rows, "ASM-F40-DP32-SPATIAL", {})
    assert not profile["valid"] and profile["threshold"] is None and profile["failures"] == 900


def test_check_cannot_calibrate_or_drop_failed_outcomes():
    plan = manifest("DEV-CHECK")
    rows = results(plan)
    with pytest.raises(ValueError, match="DEV-CAL"):
        calibrate(plan, rows, "ASM-F40-SIFT-SPATIAL", {})
    cal = manifest()
    with pytest.raises(ValueError, match="Incomplete"):
        calibrate(cal, results(cal)[:-1], "ASM-F40-SIFT-SPATIAL", {})


def test_self_filter_keeps_all_ring_edges_and_extended_denominators():
    plan = manifest()
    rows = results(plan)
    for row in rows:
        row["score"] = 10.0
    rows[0]["score"] = 0.0  # Only unit 0 fails PLAIN SELF.
    profile = {"valid": True, "threshold": 1.0, "comparison": ">=", "route_id": "ASM-F40-SIFT-SPATIAL", "profile_id": "test"}
    report = development_report(plan, rows, profile)
    assert report["supervisor"]["X"] == 99 and report["supervisor"]["Y"] == 98
    assert report["extended_impostors"][0]["attempt_denominator"] == 900
    assert report["extended_impostors"][1]["attempt_denominator"] == 882
    assert len(report["supervisor"]["results"]) == 400
    bad = copy.deepcopy(rows)
    genuine = next(i for i, p in enumerate(plan["pairs"]) if p["kind"] == KINDS[2])
    bad[genuine].update(status="failure", score=None, reason="bad input", failure_stage="input")
    after = development_report(plan, bad, profile)
    assert after["supervisor"]["X"] == 99 and after["supervisor"]["views"][2]["PROCESSING_FAILURE"] == 1
