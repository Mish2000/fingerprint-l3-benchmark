"""Adapters around pinned author code; no population, pair selection or truth.

Tiling and coordinate adapter migrated from the user's l3_bridge_v1 P1 worker.
Survey/Dahia algorithms remain in their attributed, ignored source closures.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import numpy as np

from .contracts import Descriptors, Points
from .direct_pore import DahiaDP32


def tiled_survey(model, image, output_tile=256):
    """Preserved P1 valid-convolution tiling; stitch then perform one global NMS."""
    import torch
    height, width = image.shape
    if min(height, width) < 17:
        raise ValueError("Image is smaller than the Survey receptive field")
    result = torch.empty((1, 1, height - 16, width - 16), dtype=torch.float32)
    with torch.no_grad():
        for y in range(0, height - 16, output_tile):
            for x in range(0, width - 16, output_tile):
                end_y, end_x = min(y + output_tile, height - 16), min(x + output_tile, width - 16)
                tile = np.ascontiguousarray(image[y:end_y + 16, x:end_x + 16], dtype=np.float32) / np.float32(255)
                prediction = model(torch.from_numpy(tile)[None, None])
                if prediction.shape[-2:] != (end_y - y, end_x - x):
                    raise ValueError("Survey output geometry changed")
                result[:, :, y:end_y, x:end_x] = prediction.cpu()
    return result


def survey_xy(rows):
    """Survey writer has already added +8 in zero-based row,column coordinates."""
    return [(column, row) for row, column in rows]


def load_survey(path):
    import torch
    path = Path(path).resolve()
    sys.path.insert(0, str(path))
    try:
        import entireImage
        from util.utils import loadModel
        if not Path(entireImage.__file__).resolve().is_relative_to(path):
            raise ValueError("Survey module came from another closure")
        torch.set_num_threads(4)
        model = loadModel(str(path / "out_of_the_box_detect/models/40"), torch.device("cpu"),
                          8, 40, False, 17, False, False, False)
        model.eval()
        return model, entireImage
    finally:
        sys.path.remove(str(path))


def load_dahia(path):
    """Only SIFT/numpy functions are called; temporary TF stub is never a worker."""
    path = Path(path)
    sentinel = object()
    previous = {name: sys.modules.get(name, sentinel) for name in ("tensorflow", "utils")}
    try:
        if "tensorflow" not in sys.modules:
            sys.modules["tensorflow"] = types.ModuleType("tensorflow")
        def load(name, filename):
            spec = importlib.util.spec_from_file_location(name, path / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        utils = load("_fpl3_dahia_utils", "utils.py")
        sys.modules["utils"] = utils
        matching = load("_fpl3_dahia_matching", "matching.py")
        return utils, matching
    finally:
        for name, value in previous.items():
            if value is sentinel:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value


class SurveyF40:
    def __init__(self, parameters, artifacts):
        self.parameters = parameters
        self.model, self.entire = load_survey(Path(artifacts) / "survey")

    def detect(self, image, pixels, scratch):
        p = self.parameters
        prediction = tiled_survey(self.model, pixels, p["output_tile"])
        scratch.mkdir(parents=True, exist_ok=False)
        self.entire.apply_nms(prediction, p["nms_probability"], p["window"], p["nms_iou"],
                              str(scratch) + os.sep, 0, str(scratch) + os.sep, p["window"])
        rows = [tuple(map(int, line.split(","))) for line in (scratch / "0.txt").read_text().splitlines()]
        return Points(image.key, np.asarray(survey_xy(rows), dtype=np.float32).reshape(-1, 2))


class DahiaSift:
    def __init__(self, parameters, artifacts):
        self.parameters = parameters
        self.utils, _ = load_dahia(Path(artifacts) / "dahia")

    def describe(self, image, pixels, points):
        # Historical helper swaps internally before constructing OpenCV x,y.
        values = self.utils.sift_descriptors(pixels, points.xy[:, ::-1].copy(),
                                             scale=self.parameters["sift_scale"], normalize=True)
        if len(points.xy) == 0:
            values = np.empty((0, 128), dtype=np.float32)
        if values is None or len(values) != len(points.xy):
            raise ValueError("Historical SIFT point count changed; no new filtering is allowed")
        return Descriptors(points, values, np.arange(len(points.xy), dtype=np.int64))


class DahiaSpatial:
    def __init__(self, parameters, artifacts):
        self.parameters = parameters
        _, self.matching = load_dahia(Path(artifacts) / "dahia")

    def match(self, left, right):
        return float(self.matching.spatial(left.values, right.values, left.points.xy, right.points.xy,
                                           thr=self.parameters["ratio_threshold_on_squared_distance"]))


FACTORIES = {"survey_f40": SurveyF40, "dahia_sift": DahiaSift, "dahia_dp32": DahiaDP32,
             "dahia_spatial": DahiaSpatial}


def build_route(config, artifacts):
    return tuple(FACTORIES[config[stage]](config["parameters"], artifacts)
                 for stage in ("detector", "descriptor", "matcher"))
