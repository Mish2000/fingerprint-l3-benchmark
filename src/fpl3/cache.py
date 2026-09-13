"""Immutable content-bound feature cache with explicit descriptor point mapping."""

import io
from pathlib import Path

import numpy as np

from .contracts import Descriptors, Points
from .io import digest, fingerprint, read_json, write_bytes, write_json


def cache_key(image, signature):
    return fingerprint({"input": {"key": image.key, "sha256": image.sha256, "shape": [image.height, image.width],
                                   "source_ppi": image.source_ppi, "processing_ppi": image.processing_ppi,
                                   "frame": image.frame}, "signature": signature})


def encode(source, descriptors):
    data = io.BytesIO()
    np.savez_compressed(data, source_points_xy=source.xy, points_xy=descriptors.points.xy,
                        descriptors=descriptors.values, source_indices=descriptors.source_indices)
    return data.getvalue()


def decode(path, image):
    with np.load(path, allow_pickle=False) as data:
        source = Points(image.key, data["source_points_xy"])
        descriptors = Descriptors(Points(image.key, data["points_xy"]), data["descriptors"], data["source_indices"])
    descriptors.validate(source, image)
    return source, descriptors


def read_cache(root, key, image):
    path = Path(root) / key
    if not path.exists():
        return None
    meta = read_json(path / "entry.json")
    if meta["key"] != key or meta["npz_sha256"] != digest(path / "features.npz"):
        raise ValueError("Stale/corrupt cache is not reusable")
    return decode(path / "features.npz", image)


def write_cache(root, key, image, source, descriptors):
    descriptors.validate(source, image)
    existing = read_cache(root, key, image)
    if existing is not None:
        old_points, old_desc = existing
        if not all(np.array_equal(a, b) for a, b in [(source.xy, old_points.xy),
                    (descriptors.points.xy, old_desc.points.xy), (descriptors.values, old_desc.values),
                    (descriptors.source_indices, old_desc.source_indices)]):
            raise ValueError("Fresh extraction disagrees with immutable cache")
        return
    path = Path(root) / key
    path.mkdir(parents=True, exist_ok=False)
    write_bytes(path / "features.npz", encode(source, descriptors))
    write_json(path / "entry.json", {"key": key, "npz_sha256": digest(path / "features.npz")})
