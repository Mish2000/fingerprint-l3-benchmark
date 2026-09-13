from pathlib import Path

import numpy as np
import pytest

from fpl3.biometrics import FACTORIES, build_route, survey_xy
from fpl3.cache import cache_key, read_cache, write_cache
from fpl3.contracts import Descriptors, Image, Points
from fpl3.dahia import safe_member
from fpl3.io import read_json, write_json
from fpl3.runner import coverage, execute_pairs


def test_cache_reuse_change_corruption_and_no_overwrite(tmp_path):
    image = Image("s", Path("unused"), "a" * 64, 80, 40)
    source = Points("s", np.array([[1, 2], [3, 4]], np.float32))
    desc = Descriptors(source, np.ones((2, 3), np.float32), np.arange(2))
    key = cache_key(image, {"component": "synthetic-a", "environment": "test"})
    write_cache(tmp_path, key, image, source, desc)
    assert np.array_equal(read_cache(tmp_path, key, image)[1].values, desc.values)
    other = cache_key(image, {"component": "synthetic-b", "environment": "test"})
    assert other != key and read_cache(tmp_path, other, image) is None
    before = (tmp_path / key / "features.npz").read_bytes()
    write_cache(tmp_path, key, image, source, desc)
    with pytest.raises(ValueError):
        write_cache(tmp_path, key, image, source, Descriptors(source, desc.values + 1, np.arange(2)))
    assert (tmp_path / key / "features.npz").read_bytes() == before
    (tmp_path / key / "features.npz").write_bytes(b"corrupt")
    with pytest.raises(ValueError): read_cache(tmp_path, key, image)
    file = tmp_path / "final.json"
    write_json(file, {"done": True})
    with pytest.raises(FileExistsError): write_json(file, {"done": False})
    assert read_json(file) == {"done": True}


def test_config_component_swap_keeps_pair_logic_and_coverage(monkeypatch):
    class Detection:
        def __init__(self, p, a): pass
        def detect(self, image, pixels, scratch): return Points(image.key, np.array([[1, 2], [3, 4]], np.float32))
    class Description:
        def __init__(self, p, a): pass
        def describe(self, image, pixels, source): return Descriptors(source, np.ones((2, 1)), np.arange(2))
    class Subset(Description):
        def describe(self, image, pixels, source): return Descriptors(Points(image.key, source.xy[[1]]), np.ones((1, 1)), np.array([1]))
    class Matching:
        def __init__(self, p, a): pass
        def match(self, left, right): return float(len(left.values) * len(right.values))
    for k, v in {"test_detector": Detection, "test_descriptor": Description, "test_subset": Subset, "test_matcher": Matching}.items():
        monkeypatch.setitem(FACTORIES, k, v)
    config = {"detector": "test_detector", "descriptor": "test_descriptor", "matcher": "test_matcher", "parameters": {}}
    pairs = [{"pair_id": "p", "left": "a", "right": "b"}]
    coverages, scores = [], []
    for component in ("test_descriptor", "test_subset"):
        config["descriptor"] = component
        detector, descriptor, matcher = build_route(config, "unused")
        templates = {}
        for key in ("a", "b"):
            image = Image(key, Path("unused"), "a" * 64, 20, 10)
            points = detector.detect(image, None, None)
            templates[key] = descriptor.describe(image, None, points)
            templates[key].validate(points, image)
        rows = execute_pairs(pairs, templates, {k: {"status": "success"} for k in templates}, matcher)
        coverages.append(coverage(rows)); scores.append(rows[0]["score"])
    assert scores == [4, 1] and coverages[0] == coverages[1]
    assert "kind" not in pairs[0]


def test_failure_zero_and_blocked_counts():
    class Zero:
        def match(self, a, b): return 0.0
    class Broken:
        def match(self, a, b): raise RuntimeError("synthetic failure")
    pairs = [{"pair_id": "p", "left": "a", "right": "b"}]
    t, e = {"a": None, "b": None}, {"a": {"status": "success"}, "b": {"status": "success"}}
    assert coverage(execute_pairs(pairs, t, e, Zero()))["zero_scores"] == 1
    failure = execute_pairs(pairs, t, e, Broken())
    assert failure[0]["score"] is None and coverage(failure)["matcher_invocations"] == 1
    blocked = coverage(execute_pairs(pairs, {}, {}, None, "missing model"))
    assert blocked["blocked"] == 1 and blocked["logical_attempts"] == blocked["matcher_invocations"] == 0
    e["b"]["status"] = "failure"
    extraction_failure = execute_pairs(pairs, t, e, Zero())
    assert extraction_failure[0]["score"] is None and coverage(extraction_failure)["matcher_invocations"] == 0


def test_survey_offset_contract():
    assert survey_xy([(10, 68)]) == [(68, 10)]


@pytest.mark.parametrize("path", ["../escape", "/absolute", "C:/outside", "x/../../outside", "..\\outside"])
def test_archive_paths_cannot_escape(path):
    with pytest.raises(ValueError): safe_member(path)
