"""File identities for the fpl3 closure in each process, independent of Git HEAD."""

import sys
from pathlib import Path

from .io import snapshot


def package_code():
    root = Path(__file__).resolve().parent
    return snapshot(root, list(root.glob("*.py")))


def check_code(expected):
    root = Path(__file__).resolve().parent
    observed = package_code()
    if not expected or observed != expected:
        raise ValueError("fpl3 worker/coordinator code mismatch or drift")
    loaded = {}
    for name, module in list(sys.modules.items()):
        if name == "fpl3" or name.startswith("fpl3.") or (name == "__main__" and getattr(module, "__package__", None) == "fpl3"):
            path = getattr(module, "__file__", None)
            if path:
                path = Path(path).resolve()
                if not path.is_relative_to(root) or path.name not in expected:
                    raise ValueError(f"fpl3 module loaded outside the checked closure: {name}")
                loaded[name] = str(path)
    return {"root": str(root), "files": observed, "loaded_modules": loaded}
