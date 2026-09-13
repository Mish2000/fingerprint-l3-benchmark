"""Bound a launched process tree and confirm it cannot write before finalization."""

import ctypes
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


class WindowsJob:
    def __init__(self):
        from ctypes import wintypes as w

        class BasicLimits(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_int64), ("job_time", ctypes.c_int64),
                        ("flags", w.DWORD), ("min_working_set", ctypes.c_size_t),
                        ("max_working_set", ctypes.c_size_t), ("active_limit", w.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("basic", BasicLimits), ("io", ctypes.c_uint64 * 6),
                        ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                        ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]

        class Accounting(ctypes.Structure):
            _fields_ = [("times", ctypes.c_int64 * 4), ("faults", w.DWORD),
                        ("total", w.DWORD), ("active", w.DWORD), ("terminated", w.DWORD)]

        self.accounting = Accounting
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            "QueryInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
            "CloseHandle": ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE; never allow breakaway.
        try:
            self.check(self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
        except BaseException:
            self.close()
            raise

    @staticmethod
    def check(result):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process):
        self.check(self.api.AssignProcessToJobObject(self.handle, int(process._handle)))

    def active(self):
        info = self.accounting()
        self.check(self.api.QueryInformationJobObject(self.handle, 1, ctypes.byref(info), ctypes.sizeof(info), None))
        return info.active

    def terminate(self):
        self.check(self.api.TerminateJobObject(self.handle, 2))

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def _linux_active(group):
    if not Path("/proc").is_dir():
        raise OSError("Process-tree confirmation requires Windows Jobs or Linux /proc")
    active = 0
    for path in Path("/proc").glob("[0-9]*/stat"):
        try:
            fields = path.read_text().rsplit(")", 1)[1].split()
            active += int(fields[2]) == group and fields[0] not in {"Z", "X"}
        except (OSError, ValueError, IndexError):
            continue  # An exited process can disappear during enumeration.
    return active


def run_managed(command, *, stdout, env, timeout, cleanup_timeout=10):
    """Return termination evidence, including failures; never infer quiescence from a root exit alone."""
    job, process = None, None
    result = {"returncode": None, "timed_out": False, "tree_quiescent": True,
              "error": None, "method": "windows_job" if os.name == "nt" else "linux_process_group"}
    try:
        if os.name == "nt":
            job = WindowsJob()
            command = [sys.executable, "-I", "-B", "-m", "fpl3._process_entry", *command]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=subprocess.STDOUT,
                                       env=env, creationflags=subprocess.CREATE_NO_WINDOW)
            # The gate cannot launch Conda (and hence a worker) before assignment succeeds.
            job.assign(process)
            process.stdin.write(b"G")
            process.stdin.close()
        else:
            if not Path("/proc").is_dir():
                raise OSError("This worker launcher supports Windows and Linux only")
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
        result.update(pid=process.pid, tree_quiescent=False)
        result["returncode"] = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        result.update(timed_out=True, error="Worker timeout")
    except (OSError, ValueError) as exc:
        result["error"] = f"Worker launch failed: {type(exc).__name__}: {exc}"
    finally:
        if process is not None:
            try:
                remaining = job.active() if job else _linux_active(process.pid)
                # Job accounting can lag the signalled root handle briefly.
                # Wait for normal teardown before classifying a live descendant.
                grace = time.monotonic() + min(0.5, cleanup_timeout)
                while remaining and result["error"] is None and time.monotonic() < grace:
                    time.sleep(0.01)
                    remaining = job.active() if job else _linux_active(process.pid)
                if remaining:
                    if result["error"] is None:
                        result["error"] = "Launcher exited with live descendants"
                    if job:
                        job.terminate()
                    else:
                        os.killpg(process.pid, signal.SIGKILL)
                # Assignment may have failed while the gate was waiting. Kill that root too.
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=cleanup_timeout)
                deadline = time.monotonic() + cleanup_timeout
                while (job.active() if job else _linux_active(process.pid)):
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Worker tree did not become quiescent")
                    time.sleep(0.02)
                result.update(tree_quiescent=True, returncode=process.returncode)
            except (OSError, TimeoutError, subprocess.TimeoutExpired) as exc:
                result.update(tree_quiescent=False, error=f"Worker tree cleanup failed: {exc}")
            finally:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
        if job:
            job.close()  # Also terminates the tree if this process unwinds unexpectedly.
    return result
