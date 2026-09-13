"""Protocol integrity only: no detector, descriptor, matcher or score loading."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .io import fingerprint, read_json, verify_files

COHORT = "sd300_50_subjects_test_22f8d52a7478"
PLAIN = {2: 2, 3: 3, 4: 4, 5: 5, 7: 7, 8: 8, 9: 9, 10: 10, 11: 1, 12: 6}


def validate_population(plan, cohort):
    if plan["role"] != "development" or cohort["cohort_id"] != COHORT or cohort["role"] != "test":
        raise ValueError("Wrong protocol/cohort role")
    subjects = plan["active_subjects"]
    protected = cohort["subject_ids"]
    if len(subjects) != 5 or len(set(subjects)) != 5 or len(protected) != 50 or len(set(protected)) != 50:
        raise ValueError("Wrong subject population")
    if set(subjects) & set(protected):
        raise ValueError("Development overlaps protected cohort")
    if plan.get("protected_overlap") != []:
        raise ValueError("Unexpected historical overlap declaration")
    images, pairs = plan["images"], plan["pairs"]
    if len(images) != 100 or len(pairs) != 250:
        raise ValueError("Missing/extra sample or pair")
    expected_order = [(s, i, f) for s in subjects for i in ("plain", "roll") for f in range(1, 11)]
    if [(x["subject_id"], x["impression"], x["position"]) for x in images] != expected_order:
        raise ValueError("Image identity/order differs from frozen population")
    for field in ("alias", "image_id", "relative_path", "expected_sha256"):
        if len({x[field] for x in images}) != 100:
            raise ValueError(f"Duplicate image {field}")
    for i, row in enumerate(images):
        match = re.fullmatch(r"(\d+)_(plain|roll)_(\d+)_(\d+)\.png", Path(row["relative_path"]).name)
        if not match:
            raise ValueError("Invalid source filename")
        subject, impression, ppi, frgp = match.groups()
        position = PLAIN.get(int(frgp)) if impression == "plain" else {f: f for f in range(1, 11)}.get(int(frgp))
        if (subject, impression, position) != expected_order[i] or int(ppi) != 1000 or row["effective_ppi"] != 1000:
            raise ValueError("Source/anatomical mapping mismatch")
        if row["alias"] != f"image-{i:03d}" or not row["image_id"].startswith("sd300b_"):
            raise ValueError("Unexpected opaque alias or dataset")
    aliases = {key: row["alias"] for key, row in zip(expected_order, images)}
    expected_pairs = []
    for kind in ("genuine", "impostor"):
        for left in subjects:
            for right in subjects:
                if (left == right) != (kind == "genuine"):
                    continue
                for finger in range(1, 11):
                    p = {"kind": kind, "left": aliases[left, "plain", finger],
                         "right": aliases[right, "roll", finger], "finger": finger}
                    p["pair_id"] = "l3b-" + fingerprint(p)[:20]
                    expected_pairs.append(p)
    if pairs != expected_pairs:
        raise ValueError("Pair identity, truth, order, finger or side role changed")
    return {"images": 100, "subjects": 5, "pairs": 250,
            "pair_kinds": dict(Counter(p["kind"] for p in pairs)), "protected_overlap": 0,
            "historical_exposure_preserved": plan.get("known_exposure", {})}


def load_import(root):
    root = Path(root)
    receipt = read_json(root / "receipt.json")
    verify_files(root, receipt["files"])
    plan = read_json(root / "reference/plan.json")
    validate_population(plan, read_json(root / "reference/cohort.json"))
    inputs = read_json(root / "inputs.json")
    pairs = read_json(root / "pairs.json")
    historical_inputs = read_json(root / "reference/worker-inputs.json")
    if len(inputs) != 100:
        raise ValueError("Input count changed")
    for image, item, original in zip(plan["images"], inputs, historical_inputs):
        if item["key"] != image["alias"] or item["sha256"] != image["expected_sha256"]:
            raise ValueError("Input identity changed")
        if (item["width"], item["height"]) != (original["width"], original["height"]):
            raise ValueError("Input geometry changed")
        if item["source_ppi"] != 1000 or item["processing_ppi"] != 1000:
            raise ValueError("Input resolution changed")
    expected = [{k: p[k] for k in ("pair_id", "left", "right")} for p in plan["pairs"]]
    if pairs != expected:
        raise ValueError("Opaque pair interface changed")
    return inputs, pairs, receipt
