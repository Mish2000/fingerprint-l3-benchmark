"""Local interpreter and numerical environment evidence, without model loading."""

import importlib
import importlib.metadata
import platform
import site
import sys
from pathlib import Path

P1_PACKAGES = {"numpy": "numpy", "torch": "torch", "torchvision": "torchvision",
            "opencv-contrib-python": "cv2", "scipy": "scipy", "pillow": "PIL",
            "psutil": "psutil", "tqdm": "tqdm"}


def doctor(profile="dev"):
    if profile not in {"dev", "p1"}:
        raise ValueError("Unknown environment profile")
    required = P1_PACKAGES if profile == "p1" else {"numpy": "numpy"}
    packages = {}
    for name, module in required.items():
        try:
            value = importlib.import_module(module)
            packages[name] = {"version": importlib.metadata.version(name), "path": value.__file__}
        except Exception as exc:
            packages[name] = {"error": f"{type(exc).__name__}: {exc}"}
    prefix = Path(sys.prefix).resolve()
    conda = prefix / "conda-meta"
    return {"profile": profile, "python": platform.python_version(), "executable": sys.executable,
            "prefix": sys.prefix, "base_prefix": sys.base_prefix,
            "platform": platform.platform(), "manager": "conda" if conda.is_dir() else ("venv" if sys.prefix != sys.base_prefix else "standalone"),
            "conda_python_records": [p.name for p in conda.glob("python-*.json")] if conda.is_dir() else [],
            "enable_user_site": site.ENABLE_USER_SITE, "sys_path": sys.path,
            "packages": packages,
            "isolated_packages": all("path" in p and Path(p["path"]).resolve().is_relative_to(prefix)
                                     for p in packages.values())}


def numerical_identity():
    import cv2
    import numpy as np
    import torch
    return {"python": platform.python_version(), "packages": {p: importlib.metadata.version(p) for p in P1_PACKAGES},
            "machine": platform.machine(), "platform": platform.platform(),
            "torch_config": torch.__config__.show(), "opencv_build": cv2.getBuildInformation(),
            "numpy_config": str(np.__config__.CONFIG) if hasattr(np.__config__, "CONFIG") else "numpy-1.x",
            "device": "cpu", "torch_threads": 4}
