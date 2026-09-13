"""Launch gate: the parent assigns this process to a Job before releasing stdin."""

import subprocess
import sys


if __name__ == "__main__":
    if sys.stdin.buffer.read(1) != b"G":
        raise SystemExit(2)
    # Children inherit the Job; no breakaway flag or shell is used.
    raise SystemExit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL))
