import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from fpl3.code_identity import package_code
from fpl3.io import fingerprint, read_json, write_json
from fpl3.process_tree import run_managed
from fpl3.worker_protocol import SCHEMA


def test_managed_process_waits_for_successful_exit(tmp_path):
    with (tmp_path / "stdout.log").open("w") as stream:
        result = run_managed([sys.executable, "-I", "-B", "-c", "print('completed')"],
                             stdout=stream, env=os.environ.copy(), timeout=10)
    assert result["returncode"] == 0 and result["tree_quiescent"] and result["error"] is None


@pytest.mark.parametrize("parent_exits", [False, True])
def test_timeout_or_parent_exit_stops_descendant_writes(tmp_path, parent_exits):
    child = tmp_path / "continuous_writer.py"
    ticks = tmp_path / "ticks.bin"
    child.write_text("import sys,time\nwith open(sys.argv[1], 'ab', buffering=0) as f:\n while True:\n  f.write(b'x'); time.sleep(0.01)\n")
    parent = tmp_path / "parent.py"
    parent.write_text("import subprocess,sys,time\nfrom pathlib import Path\n"
                      "subprocess.Popen([sys.executable,'-I','-B',sys.argv[1],sys.argv[2]])\n"
                      "while not Path(sys.argv[2]).exists(): time.sleep(0.01)\n"
                      + ("" if parent_exits else "time.sleep(30)\n"))
    with (tmp_path / "stdout.log").open("w") as stream:
        result = run_managed([sys.executable, "-I", "-B", str(parent), str(child), str(ticks)],
                             stdout=stream, env=os.environ.copy(), timeout=5)
    assert result["tree_quiescent"] and result["error"]
    assert result["timed_out"] is (not parent_exits)
    assert ticks.exists() and ticks.stat().st_size > 0
    sealed_bytes = ticks.read_bytes()
    time.sleep(0.2)
    assert ticks.read_bytes() == sealed_bytes


def test_real_worker_rejects_code_mismatch_before_framework_imports(tmp_path):
    expected = package_code()
    expected["worker.py"] = "0" * 64
    request = {"schema": SCHEMA, "action": "doctor", "payload": {}, "expected_prefix": sys.prefix,
               "response": str(tmp_path / "response.json"), "code": expected}
    request["request_id"] = fingerprint(request)
    write_json(tmp_path / "request.json", request)
    result = subprocess.run([sys.executable, "-I", "-B", "-m", "fpl3.worker", "--request", str(tmp_path / "request.json")],
                            capture_output=True, text=True)
    response = read_json(tmp_path / "response.json")
    assert result.returncode == 2 and response["status"] == "failure"
    assert "code mismatch" in response["error"] and "result" not in response


def test_worker_detects_source_drift_after_action(tmp_path):
    # Execute an isolated copy; mutate only that temporary copy during a synthetic action.
    import fpl3
    source = Path(fpl3.__file__).parent
    copied = tmp_path / "source/fpl3"
    copied.mkdir(parents=True)
    for file in source.glob("*.py"):
        (copied / file.name).write_bytes(file.read_bytes())
    script = tmp_path / "drift.py"
    script.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\n"
        "from fpl3 import worker\nfrom fpl3.code_identity import package_code\n"
        "from fpl3.io import fingerprint,write_json\nfrom fpl3.worker_protocol import SCHEMA\n"
        "folder=Path(sys.argv[2])\n"
        "request={'schema':SCHEMA,'action':'doctor','payload':{},'expected_prefix':sys.prefix,'response':str(folder/'response.json'),'code':package_code()}\n"
        "request['request_id']=fingerprint(request)\nwrite_json(folder/'request.json',request)\n"
        "def mutate(_):\n p=Path(worker.__file__).with_name('runtime.py'); p.write_bytes(p.read_bytes()+b'\\n# synthetic drift\\n'); return {}\n"
        "worker.handle=mutate\nsys.argv=['worker','--request',str(folder/'request.json')]\nraise SystemExit(worker.main())\n")
    result = subprocess.run([sys.executable, "-I", "-B", str(script), str(copied.parent), str(tmp_path)], capture_output=True, text=True)
    response = read_json(tmp_path / "response.json")
    assert result.returncode == 2 and "code mismatch or drift" in response["error"]
    assert "before" in response["code_identity"] and "after" not in response["code_identity"]
