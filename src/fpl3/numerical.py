"""Explicit model-level synthetic checks before touching experiment images."""

import tempfile
from pathlib import Path

from .io import read_json, verify_files, write_json


def check_p1(artifacts, output):
    import cv2
    import numpy as np
    import torch
    from .biometrics import load_dahia, load_survey, survey_xy, tiled_survey
    from .verification import numeric_difference
    root = Path(artifacts)
    for key, meta in read_json(root / "components.json").items():
        verify_files(root / key, meta["files"])
    model, entire = load_survey(root / "survey")
    pixels = np.random.default_rng(40401).integers(0, 256, (83, 147), dtype=np.uint8)
    with torch.no_grad():
        full = model(torch.from_numpy(pixels.astype(np.float32) / 255)[None, None])
    tiled = tiled_survey(model, pixels, output_tile=32)
    repeated = tiled_survey(model, pixels, output_tile=32)
    torch.testing.assert_close(full, tiled, atol=2e-6, rtol=2e-5)
    assert torch.equal(tiled, repeated)
    with tempfile.TemporaryDirectory(dir=Path(output).parent) as tmp:
        prediction = torch.zeros((1, 1, 31, 79))
        prediction[0, 0, 2, 60] = 0.9
        entire.apply_nms(prediction, 0.65, 17, 0.2, tmp + "/", 0, tmp + "/", 17)
        row = tuple(map(int, (Path(tmp) / "0.txt").read_text().strip().split(",")))
        assert row == (10, 68)
        assert survey_xy([row]) == [(68, 10)]
    utils, matching = load_dahia(root / "dahia")
    image = np.random.default_rng(7).integers(0, 256, (73, 159), dtype=np.uint8)
    xy = np.asarray([[123, 21], [89, 51]], dtype=np.float32)
    actual = utils.sift_descriptors(image, xy[:, ::-1].copy(), scale=4)
    processed = cv2.createCLAHE(clipLimit=3).apply(cv2.medianBlur(image, 3))
    _, expected = cv2.xfeatures2d.SIFT_create().compute(processed, [cv2.KeyPoint(float(x), float(y), 4) for x, y in xy])
    np.testing.assert_array_equal(actual, expected)
    assert matching.spatial(np.empty((0, 128), np.float32), actual, [], xy, thr=0.7) == 0
    assert matching.spatial(actual[:1], actual[:1], xy[:1], xy[:1], thr=0.7) == 0
    result = {"status": "passed", "input": "synthetic non-biometric pixels only",
              "actual_fcn_non_square_shape": [83, 147],
              "tiling_vs_whole": numeric_difference(full.numpy(), tiled.numpy()),
              "tiling_check_tolerance_only": {"atol": 2e-6, "rtol": 2e-5},
              "repeated_tiling_exact": True, "known_peak_row_column": list(row), "native_xy": [68, 10],
              "sift_axis_values_exact": True, "empty_spatial_score": 0, "single_spatial_score": 0,
              "migration_policy_declared_before_pair_comparison": {"mode": "exact", "atol": 0, "rtol": 0}}
    write_json(output, result)
    return result
