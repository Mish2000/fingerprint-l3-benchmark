import os
import types
from pathlib import Path

import numpy as np
import pytest

from fpl3 import biometrics
from fpl3.contracts import Image


@pytest.mark.skipif(os.name != "nt", reason="Windows extended-length path semantics")
@pytest.mark.parametrize("extended", [False, True])
def test_survey_writer_accepts_native_and_extended_windows_directories(tmp_path, monkeypatch, extended):
    scratch = tmp_path / "scratch"
    if extended:
        scratch = Path("\\\\?\\" + str(scratch))
    detector = biometrics.SurveyF40.__new__(biometrics.SurveyF40)
    detector.parameters = {"output_tile": 256, "nms_probability": .65, "window": 17, "nms_iou": .2}
    detector.model = None
    def write_nms(prediction, probability, window, iou, output, index, diagnostics, model_window):
        # The external writer concatenates a filename onto its supplied directory.
        with open(output + "0.txt", "w") as stream:
            stream.write("2,3\n")
    detector.entire = types.SimpleNamespace(apply_nms=write_nms)
    monkeypatch.setattr(biometrics, "tiled_survey", lambda *args: None)
    image = Image("synthetic", Path("unused"), "a" * 64, 10, 10)
    result = detector.detect(image, np.zeros((10, 10), np.uint8), scratch)
    assert result.xy.tolist() == [[3.0, 2.0]]
