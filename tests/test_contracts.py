import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from fpl3.contracts import Descriptors, Image, MatchResult, Points
from fpl3.verification import numeric_difference, validate_score_row


def test_import_is_inert_from_unrelated_directory(tmp_path):
    code = "import fpl3,sys; assert not any(x in sys.modules for x in ['fpbench','torch','cv2','tensorflow']); print(fpl3.__version__)"
    from fpl3 import __version__
    assert subprocess.check_output([sys.executable, "-I", "-B", "-c", code], cwd=tmp_path).strip() == __version__.encode()


def test_subset_mapping_on_non_square_image():
    image = Image("synthetic", Path("unused"), "a" * 64, 159, 73)
    source = Points(image.key, np.array([[123, 21], [89, 51], [0, 0]], np.float32))
    subset = Points(image.key, source.xy[[2, 0]])
    result = Descriptors(subset, np.ones((2, 128), np.float32), np.array([2, 0]))
    result.validate(source, image)
    with pytest.raises(ValueError, match="correspondence"):
        Descriptors(subset, result.values, np.array([0, 2])).validate(source, image)
    with pytest.raises(ValueError):
        Points(image.key, source.xy[:, ::-1]).validate(image)


@pytest.mark.parametrize("xy", [np.array([[np.nan, 1]]), np.ones((2, 3)), np.array([[-1, 0]]), np.array([[159, 0]])])
def test_invalid_points(xy):
    with pytest.raises(ValueError):
        Points("s", xy).validate(Image("s", Path("unused"), "a" * 64, 159, 73))


@pytest.mark.parametrize("status,score,reason,stage", [("success", None, None, None), ("success", float("nan"), None, None),
    ("success", float("inf"), None, None), ("failure", 0, "error", "detection"), ("failure", None, None, None)])
def test_invalid_score_contract(status, score, reason, stage):
    with pytest.raises(ValueError):
        MatchResult(status, score, reason, stage)


def test_zero_is_success_and_failure_has_no_score():
    assert MatchResult("success", 0).score == 0
    assert MatchResult("failure", None, "decode failed", "input").score is None
    with pytest.raises(ValueError):
        validate_score_row({"status": "success", "score": None})
    with pytest.raises(ValueError):
        numeric_difference([float("nan")], [0])
    assert not numeric_difference(np.ones((1, 2)), np.ones((2, 1)))["shape_equal"]


def test_nonfinite_descriptor_is_rejected():
    image = Image("s", Path("unused"), "a" * 64, 50, 40)
    p = Points("s", np.array([[3, 4]], np.float32))
    with pytest.raises(ValueError):
        Descriptors(p, np.array([[float("inf")]]), np.array([0])).validate(p, image)
