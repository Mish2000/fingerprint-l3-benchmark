"""Small contracts. Biometric interfaces never receive protocol truth."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

FRAME = "zero-based x=column,y=row; native image pixels"


@dataclass(frozen=True)
class Image:
    key: str
    path: Path
    sha256: str
    width: int
    height: int
    source_ppi: int = 1000
    processing_ppi: int = 1000
    frame: str = FRAME

    def __post_init__(self):
        if not self.key or min(self.width, self.height, self.source_ppi, self.processing_ppi) <= 0:
            raise ValueError("Invalid image identity or geometry")
        if self.frame != FRAME or len(self.sha256) != 64:
            raise ValueError("Invalid content identity or coordinate frame")


@dataclass(frozen=True)
class Points:
    image_key: str
    xy: np.ndarray
    frame: str = FRAME

    def validate(self, image):
        if self.image_key != image.key or self.frame != image.frame:
            raise ValueError("Points refer to another image/frame")
        if self.xy.ndim != 2 or self.xy.shape[1] != 2 or not np.isfinite(self.xy).all():
            raise ValueError("Points must be finite N x 2")
        if len(self.xy) and not ((self.xy >= 0).all() and
                                (self.xy[:, 0] < image.width).all() and
                                (self.xy[:, 1] < image.height).all()):
            raise ValueError("Points outside native image")


@dataclass(frozen=True)
class Descriptors:
    points: Points
    values: np.ndarray
    source_indices: np.ndarray

    def validate(self, source, image):
        source.validate(image)
        self.points.validate(image)
        indices = self.source_indices
        if indices.ndim != 1 or indices.dtype.kind not in "iu":
            raise ValueError("Source indices must be a 1D integer array")
        if len(set(map(int, indices))) != len(indices) or (indices < 0).any() or (indices >= len(source.xy)).any():
            raise ValueError("Invalid/duplicate source index")
        if not np.array_equal(self.points.xy, source.xy[indices]):
            raise ValueError("Descriptor points lost source correspondence")
        if self.values.ndim != 2 or len(self.values) != len(indices) or not np.isfinite(self.values).all():
            raise ValueError("Descriptors must be finite and aligned with retained points")


@dataclass(frozen=True)
class MatchResult:
    status: str
    score: float | None
    reason: str | None = None
    failure_stage: str | None = None
    score_direction: str = "higher_is_more_similar"
    timings: dict = field(default_factory=dict)
    matcher_invoked: bool = False

    def __post_init__(self):
        if self.status not in {"success", "failure", "blocked", "pending"}:
            raise ValueError("Unknown match status")
        if self.score_direction != "higher_is_more_similar":
            raise ValueError("Unsupported score direction")
        if self.status == "success":
            if self.score is None or not math.isfinite(self.score) or self.reason or self.failure_stage:
                raise ValueError("Success requires a finite final score without failure")
        elif self.score is not None or not self.reason or not self.failure_stage:
            raise ValueError("Non-success requires null score and explicit reason/stage")
        if any(not math.isfinite(v) or v < 0 for v in self.timings.values()):
            raise ValueError("Invalid timing")


class Detector(Protocol):
    def detect(self, image: Image, pixels: np.ndarray, scratch: Path) -> Points: ...


class Descriptor(Protocol):
    def describe(self, image: Image, pixels: np.ndarray, points: Points) -> Descriptors: ...


class Matcher(Protocol):
    def match(self, left: Descriptors, right: Descriptors) -> float: ...


class ImagePairSystem(Protocol):
    """Extension boundary for an entire external system, without fake stages."""
    def compare(self, left: Image, right: Image) -> MatchResult: ...
