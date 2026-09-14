import pytest

from fpl3.development import check_profile_gate
from fpl3.io import digest, write_json
from fpl3.supervisor import seal


@pytest.mark.parametrize("fault", [None, "unsealed", "score_source", "profile", "freeze", "invalid"])
def test_check_requires_immutable_valid_calibration_gate(tmp_path, fault):
    prepared, cal, profiles = (tmp_path / n for n in ("prepared", "cal", "profiles"))
    write_json(prepared / "freeze.json", {"code": "frozen"})
    for alias in ("sift", "dp32"):
        write_json(cal / f"pairs-{alias}.json", [{"score": 1}])
        write_json(profiles / f"{alias}.json", {"valid": fault != "invalid", "threshold": 2,
                   "source": {"pairs_sha256": digest(cal / f"pairs-{alias}.json")}})
    write_json(profiles / "gate.json", {"freeze_sha256": digest(prepared / "freeze.json"),
               "profiles": {a: digest(profiles / f"{a}.json") for a in ("sift", "dp32")}})
    if fault != "unsealed":
        seal(profiles)
    if fault == "score_source": (cal / "pairs-sift.json").write_text("[]")
    elif fault == "profile": (profiles / "sift.json").write_text("{}")
    elif fault == "freeze": (prepared / "freeze.json").write_text("{}")
    if fault:
        with pytest.raises((ValueError, FileNotFoundError)):
            check_profile_gate(profiles, prepared, cal)
    else:
        assert check_profile_gate(profiles, prepared, cal)["profiles"]["sift"] == digest(profiles / "sift.json")
