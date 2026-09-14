import copy
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from fpl3.cache import encode
from fpl3.contracts import Descriptors, Image, Points
from fpl3.direct_pore import DahiaDP32
from fpl3.feature_reuse import DETECTOR_PARAMETERS, load_reused
from fpl3.io import digest, write_bytes, write_json
from fpl3.worker import validate_development_job, validate_opaque_job


def product(tmp_path):
    source = tmp_path / "source.bin"
    write_bytes(source, b"synthetic")
    image = Image("opaque-b", source, digest(source), 128, 96)
    points = Points(image.key, np.array([[17, 20], [32, 31]], dtype=np.float32))
    desc = Descriptors(points, np.array([[1, 2], [3, 4]], dtype=np.float32), np.array([0, 1]))
    payload, record = tmp_path / "source.npz", tmp_path / "source.json"
    write_bytes(payload, encode(points, desc))
    write_json(record, {"key": image.key, "status": "success", "npz_sha256": digest(payload)})
    write_json(tmp_path / "complete.json", {"meaning": "test source seal"})
    config = {"route_id": "ASM-F40-SIFT-SPATIAL", "detector": "survey_f40",
              "parameters": dict.fromkeys(DETECTOR_PARAMETERS, 1)}
    signature = {"config": config, "components": {"f40": "fixed"}, "environment": {"python": "test"}}
    receipt = {"mode": "descriptors", "image": {"key": image.key, "path": str(source), "sha256": image.sha256,
               "width": 128, "height": 96, "source_ppi": 1000, "processing_ppi": 1000},
               "signature": copy.deepcopy(signature), "npz_path": str(payload), "npz_sha256": digest(payload),
               "record_path": str(record), "record_sha256": digest(record), "source_run": str(tmp_path),
               "source_seal_sha256": digest(tmp_path / "complete.json"), "compatibility": {"adapter_ast_exact": True}}
    return image, signature, receipt


def test_reuse_keeps_points_source_indices_and_independent_replica(tmp_path):
    image, signature, receipt = product(tmp_path)
    pts, desc = load_reused(receipt, image, signature)
    np.testing.assert_array_equal(pts.xy, [[17, 20], [32, 31]])
    np.testing.assert_array_equal(desc.source_indices, [0, 1])
    receipt["mode"] = "points"
    assert load_reused(receipt, image, signature)[1] is None
    receipt["image"]["key"] = "opaque-a"
    with pytest.raises(ValueError, match="side"):
        load_reused(receipt, image, signature)


@pytest.mark.parametrize("fault", ["hash", "resolution", "environment", "weight", "detector", "route", "proof", "payload", "seal"])
def test_reuse_never_bypasses_content_numerical_or_component_bindings(tmp_path, fault):
    image, signature, receipt = product(tmp_path)
    if fault == "hash": receipt["image"]["sha256"] = "0" * 64
    elif fault == "resolution": receipt["image"]["processing_ppi"] = 500
    elif fault == "environment": receipt["signature"]["environment"] = {}
    elif fault == "weight": receipt["signature"]["components"] = {}
    elif fault == "detector": receipt["signature"]["config"]["parameters"]["nms_probability"] = 2
    elif fault == "route": signature["config"]["route_id"] = "ASM-F40-DP32-SPATIAL"
    elif fault == "proof": receipt["compatibility"]["adapter_ast_exact"] = False
    elif fault == "payload": Path(receipt["npz_path"]).write_bytes(b"changed")
    else: (tmp_path / "complete.json").write_text("{}")
    with pytest.raises(ValueError):
        load_reused(receipt, image, signature)


def test_new_job_keeps_truth_out_and_historical_job_rejects_reuse():
    item = {"key": "a", "path": "unused", "sha256": "0" * 64, "width": 10, "height": 10,
            "source_ppi": 1000, "processing_ppi": 1000}
    job = {"inputs": [item], "pairs": [{"pair_id": "p", "left": "a", "right": "a"}],
           "config": {"route_id": "ASM-F40-SIFT-SPATIAL"}, "reuse": {}, "components": {}, "artifacts": "",
           "cache_dir": "", "run_dir": "", "signature": {}, "fresh": True, "expected_runtime": {}, "diagnostic_pairs": []}
    validate_development_job(job)
    with pytest.raises(ValueError):
        validate_opaque_job(job)
    job["pairs"][0]["ground_truth"] = "mated"
    with pytest.raises(ValueError, match="truth"):
        validate_development_job(job)


def test_dp_empty_fractional_and_border_contract_without_model(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "cv2", types.SimpleNamespace())
    adapter = DahiaDP32({"dp_patch_size": 32, "dp_pixels": "float32_0_1", "dp_orientation": "sparse-exact-v1"}, None)
    image = Image("test", tmp_path, "0" * 64, 96, 64)
    pixels = np.zeros((64, 96), np.uint8)
    described = adapter.describe(image, pixels, Points(image.key, np.empty((0, 2), np.float32)))
    assert described.values.shape == (0, 1024)
    # Source excludes x=width-16 and y=height-16 despite a full patch fitting.
    points = Points(image.key, np.array([[80, 20], [20, 48], [15, 25]], np.float32))
    assert adapter.describe(image, pixels, points).values.shape == (0, 1024)
    assert [r["reason"] for r in adapter.filter_details] == ["source_border_policy"] * 3
    with pytest.raises(ValueError, match="rounding"):
        adapter.describe(image, pixels, Points(image.key, np.array([[22.5, 22]], np.float32)))
