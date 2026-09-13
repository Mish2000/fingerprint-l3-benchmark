import copy
import math
import sys
from collections import Counter

import pytest

from fpl3.io import fingerprint
from fpl3.supervisor_protocol import KINDS, build_manifest, opaque_work, select_threshold, summarize, validate_manifest
from fpl3.worker import validate_opaque_job


def population(subjects=("00000101", "00000830", "00000402"), role="development"):
    records = []
    for s in subjects:
        for imp in ("plain", "roll"):
            for f in range(1, 11):
                frgp = {1: 11, 6: 12}.get(f, f) if imp == "plain" else f
                records.append({"subject_id": s, "impression": imp, "position": f, "release": "SD300B",
                                "image_id": f"synthetic-{s}-{imp}-{f}", "sha256": fingerprint([s, imp, f]),
                                "relative_path": f"{s}_{imp}_1000_{frgp:02}.png", "width": 100, "height": 120,
                                "source_ppi": 1000, "processing_ppi": 1000})
    return build_manifest(list(subjects), records, role)


def results(plan, score=10.0):
    return [{**{k: p[k] for k in ("pair_id", "left", "right")}, "status": "success", "score": score,
             "reason": None, "failure_stage": None, "matcher_invoked": True, "timings": {}}
            for p in plan["pairs"]]


def test_next_subject_nonconsecutive_wrap_and_four_populations(tmp_path):
    plan = population()
    assert validate_manifest(plan)["pair_kinds"] == dict.fromkeys(KINDS, 30)
    negative = [p for p in plan["pairs"] if p["kind"] == KINDS[3]]
    for p in negative:
        assert p["left_unit"] // 10 != p["right_unit"] // 10
        assert p["left_unit"] % 10 == p["right_unit"] % 10 == p["finger"] - 1
        assert p["right_unit"] // 10 == (p["left_unit"] // 10 + 1) % 3
    all_inputs, all_pairs = opaque_work(plan, tmp_path)
    assert len(all_inputs) == len(all_pairs) == 120
    # Two physical extraction records per input; no copying or same-key SELF.
    assert set(Counter(r["path"] for r in all_inputs).values()) == {2}


def test_finger_partitions_cover_every_edge_once_without_extra_extractions(tmp_path):
    plan = population()
    all_inputs, all_pairs = opaque_work(plan, tmp_path)
    shards = [opaque_work(plan, tmp_path, f) for f in range(1, 11)]
    assert Counter(r["key"] for inputs, _ in shards for r in inputs) == Counter(r["key"] for r in all_inputs)
    assert Counter(p["pair_id"] for _, pairs in shards for p in pairs) == Counter(p["pair_id"] for p in all_pairs)
    for inputs, pairs in shards:
        validate_opaque_job({"inputs": inputs, "pairs": pairs, **dict.fromkeys(
            ["config", "components", "artifacts", "cache_dir", "run_dir", "signature", "fresh", "expected_runtime"])})
        assert all(p["left"] != p["right"] for p in pairs)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "thumb", "multi", "release", "ppi", "subject", "hash"])
def test_reject_bad_metadata(fault):
    plan = population()
    records = [{k: v for k, v in r.items() if k not in {"key", "unit"}} for r in plan["images"]]
    if fault == "missing": records.pop()
    if fault == "duplicate": records.append(records[0])
    if fault == "thumb": records[0]["position"] = 6
    if fault == "multi": records[0]["relative_path"] = "00000101_plain_1000_13.png"
    if fault == "release": records[0]["release"] = "SD300C"
    if fault == "ppi": records[0]["processing_ppi"] = 500
    if fault == "subject": records[0]["subject_id"] = "not-selected"
    if fault == "hash": records[0]["sha256"] = "invalid"
    with pytest.raises(ValueError): build_manifest(plan["subjects"], records, "development")


def test_threshold_ties_zeros_and_above_float64_max():
    tied = select_threshold([0.0] * 195 + [1.0] * 3 + [2.0] * 2)
    assert tied["threshold"] == 2.0 and tied["false_accepts"] == 2
    tied_max = select_threshold([0.0] * 197 + [1.0] * 3)
    assert tied_max["threshold"] == math.nextafter(1.0, math.inf)
    assert tied_max["comparison"] == ">=" and tied_max["false_accepts"] == 0
    extreme = select_threshold([sys.float_info.max] * 200)
    assert extreme["comparison"] == ">" and extreme["threshold"] == sys.float_info.max
    assert select_threshold([0.0] * 200)["threshold"] == math.nextafter(0.0, math.inf)
    with pytest.raises(ValueError): select_threshold([0.0, math.nan])


def test_genuine_failure_stays_filtered_and_truth_is_immutable():
    plan = population()
    before = copy.deepcopy(plan)
    rows = results(plan)
    rows[60]["score"] = 0.0
    report = summarize(plan, rows, {"threshold": 5.0, "comparison": ">="})
    assert report["X"] == report["Y"] == 30
    assert report["views"][3]["NON_MATCH"] == 1 and report["views"][3]["total"] == 30
    assert plan == before


def test_plain_self_failure_only_excludes_both_incident_fixed_negatives():
    plan = population()
    rows = results(plan)
    rows[0].update(status="failure", score=None, reason="decode", failure_stage="input", matcher_invoked=False)
    report = summarize(plan, rows, {"threshold": 5.0, "comparison": ">="})
    assert report["X"] == 29 and report["Y"] == 28
    assert report["views"][0]["PROCESSING_FAILURE"] == 1
    assert report["views"][4]["total"] == 30
    assert report["eligibility"][0]["reasons"] == ["plain_self:PROCESSING_FAILURE"]


def test_empty_view_is_undefined_and_infrastructure_is_not_non_match():
    plan = population()
    rows = results(plan, 0.0)
    report = summarize(plan, rows, {"threshold": 5.0, "comparison": ">="})
    assert report["X"] == report["Y"] == 0
    assert report["views"][3]["rate"] is report["views"][5]["rate"] is None
    with pytest.raises(ValueError): summarize(plan, rows[:-1], {"threshold": 5.0, "comparison": ">="})
    rows[0].update(status="blocked", score=None, reason="runtime", failure_stage="setup")
    with pytest.raises(ValueError, match="Infrastructure"):
        summarize(plan, rows, {"threshold": 5.0, "comparison": ">="})
