"""Strict JSON, content identity and atomic, non-replacing artifact writes."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def read_json(path):
    def reject(value):
        raise ValueError(f"Nonfinite JSON value: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=reject)


def write_bytes(path, content):
    """Publish only a complete file; atomic link fails if destination exists."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.link(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def write_json(path, value):
    write_bytes(path, (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)
                       + "\n").encode("utf-8"))


def verify_files(root, manifest):
    root = Path(root).resolve()
    for relative, sha in manifest.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or digest(path) != sha:
            raise ValueError(f"Artifact content mismatch: {relative}")


def snapshot(root, paths):
    root = Path(root)
    return {str(p.relative_to(root)).replace("\\", "/"): digest(p) for p in sorted(paths)}
