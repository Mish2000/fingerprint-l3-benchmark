import sys
import types
from pathlib import Path

import numpy as np
import pytest

from fpl3 import biometrics, runtime, worker
from fpl3.contracts import Descriptors, Points
from fpl3.io import digest, read_json, write_bytes


@pytest.mark.parametrize("fail_io", [False, True])
def test_self_invokes_two_extractors_then_real_matcher_and_reuses_templates(tmp_path, monkeypatch, fail_io):
    source = tmp_path / "source.bin"
    write_bytes(source, b"synthetic non-biometric source")
    inputs = [{"key": key, "path": str(source), "sha256": digest(source), "width": 8,
               "height": 7, "source_ppi": 1000, "processing_ppi": 1000} for key in ("opaque-a", "opaque-b")]
    calls = {"detect": [], "describe": [], "match": []}
    class Detector:
        def detect(self, image, pixels, scratch):
            calls["detect"].append(image.key)
            if fail_io:
                raise OSError("synthetic filesystem failure")
            return Points(image.key, np.array([[1, 2]], np.float32))
    class Descriptor:
        def describe(self, image, pixels, points):
            calls["describe"].append(image.key)
            # Separate side outputs deliberately differ, to expose copying.
            return Descriptors(points, np.array([[len(calls["describe"])]], np.float32), np.array([0]))
    class Matcher:
        def match(self, left, right):
            calls["match"].append((float(left.values[0, 0]), float(right.values[0, 0])))
            return float(left.values[0, 0] - right.values[0, 0])
    monkeypatch.setattr(biometrics, "build_route", lambda *args: (Detector(), Descriptor(), Matcher()))
    packages = {p: "synthetic" for p in ("numpy", "torch", "torchvision", "opencv-contrib-python", "scipy")}
    environment = {"manager": "conda", "isolated_packages": True, "enable_user_site": False, "python": "synthetic",
                   "packages": {p: {"version": v} for p, v in packages.items()}}
    monkeypatch.setattr(runtime, "doctor", lambda *args: environment)
    monkeypatch.setattr(runtime, "numerical_identity", lambda: {"synthetic": True})
    monkeypatch.setitem(sys.modules, "cv2", types.SimpleNamespace(IMREAD_GRAYSCALE=0,
                        imread=lambda *args: np.zeros((7, 8), np.uint8)))
    out = tmp_path / "run"
    pairs = [{"pair_id": str(i), "left": "opaque-a", "right": "opaque-b"} for i in range(3)]
    summary = worker.run_features({"inputs": inputs, "pairs": pairs, "config": {}, "components": {},
                                  "artifacts": str(tmp_path), "cache_dir": str(tmp_path / "cache"),
                                  "run_dir": str(out), "signature": {"environment": {"synthetic": True}},
                                  "fresh": True, "expected_runtime": {"python": "synthetic", **packages}})
    if fail_io:
        assert calls["detect"] == ["opaque-a", "opaque-b"]
        assert not calls["describe"] and not calls["match"]
        assert read_json(out / "templates/opaque-a.json")["failure_category"] == "infrastructure"
        return
    assert calls["detect"] == calls["describe"] == ["opaque-a", "opaque-b"]
    assert calls["match"] == [(1.0, 2.0)] * 3
    assert summary["fresh_extractions"] == 2 and summary["cache_hits"] == 0
    assert [r["score"] for r in read_json(out / "pairs.json")] == [-1.0] * 3
