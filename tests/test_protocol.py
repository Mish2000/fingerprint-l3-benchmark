import copy

import pytest

from fpl3.io import fingerprint
from fpl3.protocol import COHORT, validate_population


@pytest.fixture
def population():
    subjects = [f"9{i:07d}" for i in range(5)]
    plan = {"role": "development", "active_subjects": subjects, "protected_overlap": [], "images": [], "pairs": []}
    aliases = {}
    for subject in subjects:
        for impression in ("plain", "roll"):
            for finger in range(1, 11):
                alias = f"image-{len(plan['images']):03d}"
                aliases[subject, impression, finger] = alias
                code = {1: 11, 6: 12}.get(finger, finger) if impression == "plain" else finger
                plan["images"].append({"alias": alias, "subject_id": subject, "impression": impression, "position": finger,
                                       "image_id": "sd300b_synthetic_" + alias, "effective_ppi": 1000,
                                       "relative_path": f"synthetic/{subject}_{impression}_1000_{code:02}.png",
                                       "expected_sha256": fingerprint(alias)})
    for kind in ("genuine", "impostor"):
        for left in subjects:
            for right in subjects:
                if (left == right) != (kind == "genuine"):
                    continue
                for finger in range(1, 11):
                    p = {"kind": kind, "left": aliases[left, "plain", finger], "right": aliases[right, "roll", finger], "finger": finger}
                    p["pair_id"] = "l3b-" + fingerprint(p)[:20]
                    plan["pairs"].append(p)
    cohort = {"cohort_id": COHORT, "role": "test", "subject_ids": [f"8{i:07d}" for i in range(50)]}
    return plan, cohort


def test_complete_population(population):
    assert validate_population(*population)["pair_kinds"] == {"genuine": 50, "impostor": 200}


@pytest.mark.parametrize("mutation", ["missing_image", "duplicate_image", "swap_image", "missing_pair", "duplicate_pair", "swap_pair", "flip_sides", "wrong_truth", "overlap", "wrong_reference", "wrong_thumb"])
def test_bad_protocol_is_rejected(population, mutation):
    plan, cohort = copy.deepcopy(population)
    if mutation == "missing_image": plan["images"].pop()
    elif mutation == "duplicate_image": plan["images"][1] = plan["images"][0]
    elif mutation == "swap_image": plan["images"][0], plan["images"][1] = plan["images"][1], plan["images"][0]
    elif mutation == "missing_pair": plan["pairs"].pop()
    elif mutation == "duplicate_pair": plan["pairs"][1] = plan["pairs"][0]
    elif mutation == "swap_pair": plan["pairs"][0], plan["pairs"][1] = plan["pairs"][1], plan["pairs"][0]
    elif mutation == "flip_sides": plan["pairs"][0]["left"], plan["pairs"][0]["right"] = plan["pairs"][0]["right"], plan["pairs"][0]["left"]
    elif mutation == "wrong_truth": plan["pairs"][0]["kind"] = "impostor"
    elif mutation == "overlap": cohort["subject_ids"][0] = plan["active_subjects"][0]
    elif mutation == "wrong_reference": cohort["cohort_id"] = "another-cohort"
    elif mutation == "wrong_thumb": plan["images"][0]["relative_path"] = plan["images"][0]["relative_path"].replace("_11.png", "_12.png")
    with pytest.raises(ValueError): validate_population(plan, cohort)
