"""DP32 adapter for Dahia mirror b3c46518f2fba4937902b5e56093177c01474de9.

Derived orientation/patch operations: the pinned Dahia utils.py, CC BY-NC-SA 4.0.
Source and license remain in the verified external closure; see docs/provenance.md.
Local changes: explicit xy mapping, recorded invalid-point filtering and sparse
orientation evaluation. The original 17x17 dot operations and 5x5 blur are kept.
This is a descriptor integration, not the original complete DP recognition system.
"""

from __future__ import annotations

import numpy as np

from .contracts import Descriptors, Points

ORIENTATION_VERSION = "sparse-exact-v1"


def orientation_at_points(pixels, rc):
    """Exact original orientation at requested interior integer row,column points.

    A 5x5 Gaussian needs only the union of their radius-two neighborhoods. All
    gradient windows there use the original reduction order, dtypes and padding.
    Values outside requested points are deliberately unspecified, never consumed.
    """
    import cv2
    dx = cv2.Sobel(pixels, cv2.CV_64F, 1, 0, ksize=3)
    dy = cv2.Sobel(pixels, cv2.CV_64F, 0, 1, ksize=3)
    needed = np.zeros(pixels.shape, dtype=bool)
    for row, column in rc:
        needed[max(8, row - 2):min(pixels.shape[0] - 8, row + 3),
               max(8, column - 2):min(pixels.shape[1] - 8, column + 3)] = True
    nu_x = np.zeros_like(pixels, dtype=np.float32)
    nu_y = np.zeros_like(pixels, dtype=np.float32)
    for row, column in np.argwhere(needed):
        sub_dx = np.reshape(dx[row - 8:row + 9, column - 8:column + 9], -1)
        sub_dy = np.reshape(dy[row - 8:row + 9, column - 8:column + 9], -1)
        nu_x[row, column] = 2 * np.dot(sub_dx, sub_dy)
        nu_y[row, column] = np.dot(sub_dx + sub_dy, sub_dx - sub_dy)
    phi_x = cv2.GaussianBlur(nu_x, (5, 5), 0)
    phi_y = cv2.GaussianBlur(nu_y, (5, 5), 0)
    return np.arctan2(phi_x, phi_y) / 2


class DahiaDP32:
    def __init__(self, parameters, artifacts):
        if parameters.get("dp_patch_size") != 32 or parameters.get("dp_pixels") != "float32_0_1":
            raise ValueError("Step 03 fixes DP32 and source float32 [0,1] pixels")
        if parameters.get("dp_orientation") != ORIENTATION_VERSION:
            raise ValueError("Undeclared DP orientation implementation")
        self.filter_details = []

    def describe(self, image, pixels, points):
        import cv2
        points.validate(image)
        if pixels.shape != (image.height, image.width) or pixels.dtype != np.uint8:
            raise ValueError("DP adapter requires native gray8 input")
        if not np.equal(points.xy, np.floor(points.xy)).all():
            raise ValueError("DP requires integral detector points; silent rounding is forbidden")
        # Same intensity preparation as pinned utils.load_image; no SIFT CLAHE/median.
        img = np.array(pixels, dtype=np.float32) / 255
        rc = points.xy[:, ::-1].astype(np.int64)
        valid = ((rc[:, 0] >= 16) & (rc[:, 0] < image.height - 16) &
                 (rc[:, 1] >= 16) & (rc[:, 1] < image.width - 16))
        self.filter_details = [{"source_index": i, "reason": None if ok else "source_border_policy"}
                               for i, ok in enumerate(valid)]
        indices, values = [], []
        if valid.any():
            orientation = orientation_at_points(img, rc[valid])
            img = cv2.GaussianBlur(img, (3, 3), 0)
            row_grid, col_grid = np.indices((32, 32))
            mask = np.hypot(row_grid - 16, col_grid - 16) > 16
            for index in np.flatnonzero(valid):
                row, column = rc[index]
                patch = img[row - 16:row + 16, column - 16:column + 16]
                theta = orientation[row, column] - np.pi / 2
                rotation = cv2.getRotationMatrix2D((16, 16), 180 * theta / np.pi, 1)
                patch = cv2.warpAffine(patch, rotation, patch.shape[::-1], flags=cv2.INTER_LINEAR)
                patch[mask] = 0
                patch = np.reshape(patch, -1)
                patch -= np.mean(patch)
                norm = np.linalg.norm(patch)
                reason = "zero_norm" if norm == 0 else None
                if not np.isfinite(norm) or not np.isfinite(patch).all():
                    reason = "nonfinite_descriptor"
                if reason is None:
                    patch = patch / norm
                    if not np.isfinite(patch).all():
                        reason = "nonfinite_descriptor"
                self.filter_details[int(index)]["reason"] = reason
                if reason is None:
                    indices.append(index)
                    values.append(patch)
        source_indices = np.asarray(indices, dtype=np.int64)
        described = Descriptors(Points(image.key, points.xy[source_indices]),
                                np.asarray(values, dtype=np.float32).reshape(-1, 1024), source_indices)
        described.validate(points, image)
        return described
