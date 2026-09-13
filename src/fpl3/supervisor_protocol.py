"""Fixed supervisor populations and SELF views; no image or algorithm access.

The cyclic next-subject rule and tie-preserving development threshold are Step 02
implementation choices. The previous same-subject/finger-shift plan is unchanged.
"""

import math
import re
from collections import Counter
from pathlib import Path

from .contracts import MatchResult
from .io import fingerprint
from .protocol import PLAIN

KINDS = ("plain_self", "roll_self", "plain_roll_mated", "plain_roll_next_subject_non_mated")
SCHEMA = "fpl3-supervisor-sd300b-next-subject-v1"


def build_manifest(subjects, records, role, provenance=None):
    """Require every SD300B slot; preserve subject order and string identities.

    Records are selected metadata, never decoded pixels. Multis 13/14 must be
    excluded by the metadata import, and are rejected here if passed as singles.
    """
    if role not in {"development", "evaluation"}:
        raise ValueError("Unknown population role")
    if (len(subjects) < 2 or any(not isinstance(s, str) or not s for s in subjects)
            or len(set(subjects)) != len(subjects)):
        raise ValueError("Need at least two distinct string subjects in frozen order")
    slots = {}
    for row in records:
        key = (row["subject_id"], row["impression"], row["position"])
        if key in slots:
            raise ValueError("Duplicate anatomical slot")
        if row["subject_id"] not in subjects or row["release"] != "SD300B":
            raise ValueError("Wrong subject or release")
        match = re.fullmatch(r"(\d+)_(plain|roll)_(\d+)_(\d+)\.png", Path(row["relative_path"]).name)
        if match is None:
            raise ValueError("Invalid SD300B source filename")
        subject, impression, ppi, frgp = match.groups()
        position = PLAIN.get(int(frgp)) if impression == "plain" else {f: f for f in range(1, 11)}.get(int(frgp))
        if (subject, impression, position) != key or position is None or int(ppi) != 1000:
            raise ValueError("Filename/metadata anatomical mapping differs")
        if row["source_ppi"] != 1000 or row["processing_ppi"] != 1000:
            raise ValueError("Supervisor protocol requires native SD300B 1000 PPI")
        if (not re.fullmatch(r"[a-f0-9]{64}", row["sha256"])
                or any(type(row[k]) is not int or row[k] <= 0 for k in ("width", "height"))):
            raise ValueError("Invalid source digest or dimensions")
        slots[key] = row
    order = [(s, imp, f) for s in subjects for imp in ("plain", "roll") for f in range(1, 11)]
    if set(slots) != set(order):
        raise ValueError("Missing or extra single-finger input slot")
    ordered = [slots[k] for k in order]
    for field in ("image_id", "relative_path", "sha256"):
        if len({r[field] for r in ordered}) != len(ordered):
            raise ValueError(f"Duplicate source {field}")
    images = []
    for row in ordered:
        source_key = "s2img-" + fingerprint({k: row[k] for k in ("image_id", "sha256", "release")})[:20]
        images.append({**row, "key": source_key,
                       "unit": subjects.index(row["subject_id"]) * 10 + row["position"] - 1})
    protocol_id = "s2-" + fingerprint({"schema": SCHEMA, "subjects": subjects, "role": role,
                                      "images": images})[:24]
    index = {(r["subject_id"], r["impression"], r["position"]): r for r in images}
    pairs = []
    for kind in KINDS:
        for i, subject in enumerate(subjects):
            for finger in range(1, 11):
                left = index[subject, "roll" if kind == "roll_self" else "plain", finger]
                if kind in KINDS[:2]:
                    right, replica = left, "b"
                else:
                    other = subjects[(i + 1) % len(subjects)] if kind == KINDS[3] else subject
                    right, replica = index[other, "roll", finger], "a"
                pair = {"kind": kind, "left": left["key"] + "-a", "right": right["key"] + "-" + replica,
                        "left_source": left["key"], "right_source": right["key"],
                        "left_unit": left["unit"], "right_unit": right["unit"], "finger": finger,
                        "ground_truth": "non_mated" if kind == KINDS[3] else "mated"}
                pair["pair_id"] = "s2pair-" + fingerprint({"protocol_id": protocol_id, **pair})[:24]
                pairs.append(pair)
    return {"schema": SCHEMA, "protocol_id": protocol_id, "role": role, "release": "SD300B",
            "subjects": list(subjects), "images": images, "pairs": pairs,
            "provenance": provenance or {}, "pairing": "next list subject, cyclic, same anatomical finger",
            "self_extraction": "a and b independently extracted; other pairs reuse a",
            "examples": {kind: next(p["pair_id"] for p in pairs if p["kind"] == kind) for kind in KINDS},
            "additional_example_rule": "first NON_MATCH and first processing failure in manifest order per kind"}


def validate_manifest(manifest):
    records = [{k: v for k, v in r.items() if k not in {"key", "unit"}} for r in manifest["images"]]
    rebuilt = build_manifest(manifest["subjects"], records, manifest["role"], manifest["provenance"])
    if manifest != rebuilt:
        raise ValueError("Supervisor manifest differs from its deterministic protocol")
    return {"subjects": len(manifest["subjects"]), "source_images": len(records),
            "pair_kinds": dict(Counter(p["kind"] for p in manifest["pairs"]))}


def opaque_work(manifest, data_root, finger=None):
    """Finger partitions contain all subjects, so cyclic edges never cross jobs."""
    root = Path(data_root).resolve()
    inputs = []
    for row in manifest["images"]:
        if finger is not None and row["position"] != finger:
            continue
        path = (root / row["relative_path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Source path leaves dataset root")
        for replica in ("a", "b"):
            inputs.append({"key": row["key"] + "-" + replica, "path": str(path),
                           **{k: row[k] for k in ("sha256", "width", "height", "source_ppi", "processing_ppi")}})
    pairs = [{k: p[k] for k in ("pair_id", "left", "right")} for p in manifest["pairs"]
             if finger is None or p["finger"] == finger]
    return inputs, pairs


def select_threshold(scores, max_false_accepts=2):
    """Minimum of unique float64 score candidates plus the boundary above max."""
    if (not scores or any(isinstance(s, bool) or not isinstance(s, (float, int)) or not math.isfinite(s) for s in scores)
            or type(max_false_accepts) is not int or not 0 <= max_false_accepts < len(scores)):
        raise ValueError("Need complete finite scores and a valid FA budget")
    values = sorted(set(float(s) for s in scores))
    for threshold in values:
        fa = sum(s >= threshold for s in scores)
        if fa <= max_false_accepts:
            return {"threshold": threshold, "comparison": ">=", "false_accepts": fa,
                    "denominator": len(scores), "numeric_type": "IEEE-754 binary64",
                    "candidate_rule": "unique impostor scores plus boundary above maximum"}
    above = math.nextafter(values[-1], math.inf)
    return {"threshold": above if math.isfinite(above) else values[-1],
            "comparison": ">=" if math.isfinite(above) else ">", "false_accepts": 0,
            "denominator": len(scores), "numeric_type": "IEEE-754 binary64",
            "candidate_rule": "unique impostor scores plus boundary above maximum"}


def decision(row, profile):
    MatchResult(row["status"], row["score"], row.get("reason"), row.get("failure_stage"),
                row.get("score_direction", "higher_is_more_similar"), row.get("timings", {}),
                row.get("matcher_invoked", False))
    if row["status"] in {"blocked", "pending"}:
        raise ValueError("Infrastructure gap prevents a complete supervisor report")
    if row["status"] == "failure":
        return "PROCESSING_FAILURE"
    threshold = profile["threshold"]
    if not math.isfinite(threshold) or profile["comparison"] not in {">=", ">"}:
        raise ValueError("Invalid decision rule")
    accepted = row["score"] >= threshold if profile["comparison"] == ">=" else row["score"] > threshold
    return "MATCH" if accepted else "NON_MATCH"


def summarize(manifest, rows, profile):
    """Preserve ALL truth and every planned row; filtering never uses mated scores."""
    validate_manifest(manifest)
    pairs = manifest["pairs"]
    if len(rows) != len(pairs) or any(any(r[k] != p[k] for k in ("pair_id", "left", "right"))
                                     for r, p in zip(rows, pairs)):
        raise ValueError("Incomplete, reordered or substituted results")
    outcomes = {r["pair_id"]: decision(r, profile) for r in rows}
    selfs = {unit: {} for unit in range(len(manifest["subjects"]) * 10)}
    for pair in pairs:
        if pair["kind"] in KINDS[:2]:
            selfs[pair["left_unit"]][pair["kind"]] = outcomes[pair["pair_id"]]
    eligibility = [{"unit": unit, "eligible": all(value == "MATCH" for value in self_rows.values()),
                    **self_rows, "reasons": [f"{kind}:{outcome}" for kind, outcome in self_rows.items() if outcome != "MATCH"]}
                   for unit, self_rows in selfs.items()]
    eligible = {r["unit"] for r in eligibility if r["eligible"]}
    views, detail = [], []
    for pair, row in zip(pairs, rows):
        survives = pair["left_unit"] in eligible and pair["right_unit"] in eligible
        detail.append({**row, "kind": pair["kind"], "ground_truth": pair["ground_truth"],
                       "decision": outcomes[pair["pair_id"]], "self_eligible": survives,
                       "score_origin": "fresh_matcher"})
    for kind in KINDS:
        for view in ("ALL", "SELF_FILTERED") if kind in KINDS[2:] else ("ALL",):
            selected = [r for r in detail if r["kind"] == kind and (view == "ALL" or r["self_eligible"])]
            counts = Counter(r["decision"] for r in selected)
            total = len(selected)
            numerator = counts["MATCH"]
            views.append({"kind": kind, "view": view, "total": total,
                          **{k: counts[k] for k in ("MATCH", "NON_MATCH", "PROCESSING_FAILURE")},
                          "rate_numerator": numerator, "rate_denominator": total,
                          "rate": numerator / total if total else None,
                          "rate_meaning": "false acceptance" if kind == KINDS[3] else "match"})
    return {"schema": "fpl3-supervisor-report-v1", "role": manifest["role"],
            "protocol_id": manifest["protocol_id"], "subjects": len(manifest["subjects"]),
            "plain_images": len(manifest["images"]) // 2, "roll_images": len(manifest["images"]) // 2,
            "metadata_mated_units": len(selfs), "X": len(eligible),
            "Y": views[-1]["total"], "views": views, "eligibility": eligibility, "results": detail}
