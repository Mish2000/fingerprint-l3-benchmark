"""Narrow verified P1-product reuse, without subjects, truth or decisions."""

from pathlib import Path

from .cache import decode
from .contracts import Descriptors, Image, Points
from .io import digest, read_json

DETECTOR_PARAMETERS = ("device", "features", "input_overlap", "nms_iou", "nms_probability",
                       "output_tile", "torch_threads", "window")


def load_reused(receipt, image, signature):
    expected = {"mode", "image", "signature", "npz_path", "npz_sha256", "record_path", "record_sha256",
                "source_run", "source_seal_sha256", "compatibility"}
    if set(receipt) != expected or receipt["mode"] not in {"points", "descriptors"}:
        raise ValueError("Invalid reuse receipt")
    old = Image(**{**receipt["image"], "path": Path(receipt["image"]["path"])})
    if any(getattr(old, k) != getattr(image, k) for k in
           ("key", "sha256", "width", "height", "source_ppi", "processing_ppi", "frame")):
        raise ValueError("Reused image identity, side or geometry differs")
    if old.path.resolve() != image.path.resolve():
        raise ValueError("Reused source path differs")
    source_signature = receipt["signature"]
    if (source_signature["components"] != signature["components"] or
            source_signature["environment"] != signature["environment"]):
        raise ValueError("Reused component/weight or numerical environment differs")
    source_config, config = source_signature["config"], signature["config"]
    if source_config["route_id"] != "ASM-F40-SIFT-SPATIAL" or source_config["detector"] != config["detector"]:
        raise ValueError("Reused detector implementation differs")
    if any(source_config["parameters"][k] != config["parameters"][k] for k in DETECTOR_PARAMETERS):
        raise ValueError("Reused detector settings differ")
    if receipt["mode"] == "descriptors" and source_config != config:
        raise ValueError("Reused descriptors belong to another route")
    if receipt["compatibility"].get("adapter_ast_exact") is not True:
        raise ValueError("Cross-version adapter equivalence was not verified")
    if digest(Path(receipt["source_run"]) / "complete.json") != receipt["source_seal_sha256"]:
        raise ValueError("Reuse source seal changed")
    for label in ("npz", "record"):
        if digest(receipt[f"{label}_path"]) != receipt[f"{label}_sha256"]:
            raise ValueError("Reuse payload or source record changed")
    record = read_json(receipt["record_path"])
    if (record["key"] != old.key or record["status"] != "success" or
            record["npz_sha256"] != receipt["npz_sha256"]):
        raise ValueError("Reuse record is not a successful bound extraction")
    points, described = decode(receipt["npz_path"], old)
    source = Points(image.key, points.xy)
    if receipt["mode"] == "points":
        return source, None
    return source, Descriptors(Points(image.key, described.points.xy), described.values, described.source_indices)
