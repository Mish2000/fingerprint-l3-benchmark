"""One-time, read-only legacy artifact importer. Not a biometric run engine."""

from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path

from .io import digest, read_json, snapshot, write_bytes, write_json
from .protocol import COHORT, validate_population


def copy_checked(source, destination, expected=None):
    source = Path(source)
    actual = digest(source)
    if expected and actual != expected:
        raise ValueError(f"Historical checksum mismatch: {source.name}")
    write_bytes(destination, source.read_bytes())
    if digest(destination) != actual:
        raise ValueError("Copy checksum mismatch")
    return actual


def git_read(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def import_p1(config_path, destination, third_party):
    cfg = read_json(config_path)
    old = Path(cfg["historical_run"])
    dst, tp = Path(destination), Path(third_party)
    dst.mkdir(parents=True, exist_ok=False)
    tp.mkdir(parents=True, exist_ok=False)
    ref = dst / "reference"
    prepared = read_json(old / "prepared.json")
    for name, key in [("plan.json", "plan_sha256"), ("settings.json", "settings_sha256"),
                      ("worker-inputs.json", "inputs_sha256"), ("worker-pairs.json", "pairs_sha256")]:
        copy_checked(old / name, ref / name, prepared[key])
    copy_checked(old / "prepared.json", ref / "prepared.json")
    plan, settings = read_json(ref / "plan.json"), read_json(ref / "settings.json")
    cohort_source = Path(cfg["historical_workspace"]) / "manifests/protocols/sd300_50_subjects/cohorts" / COHORT / "cohort.json"
    copy_checked(cohort_source, ref / "cohort.json", settings["cohort_sha256"])
    population = validate_population(plan, read_json(ref / "cohort.json"))
    manifest_source = Path(cfg["historical_workspace"]) / "manifests/datasets/sd300/SD300B/images.parquet"
    if digest(manifest_source) != settings["images_sha256"]:
        raise ValueError("Image metadata manifest changed")
    identity = read_json(old / "P1/identity.json")
    summary = read_json(old / "P1/summary.json")
    if identity["route"] != "P1" or identity["plan_sha256"] != prepared["plan_sha256"] or identity["settings"] != settings:
        raise ValueError("Reference is not this P1 protocol/configuration")
    for name in ("identity.json", "summary.json", "scores.csv"):
        copy_checked(old / "P1" / name, ref / "P1" / name,
                     summary["scores_sha256"] if name == "scores.csv" else None)
    scores = list(csv.DictReader(io.StringIO((ref / "P1/scores.csv").read_text(encoding="utf-8"))))
    if [r["pair_id"] for r in scores] != [r["pair_id"] for r in plan["pairs"]]:
        raise ValueError("Reference score order/coverage changed")
    by_alias = {x["alias"]: x for x in plan["images"]}
    identity_sha = digest(ref / "P1/identity.json")
    for pair, row in zip(plan["pairs"], scores):
        if row["identity_sha256"] != identity_sha or row["route"] != "P1" or row["kind"] != pair["kind"]:
            raise ValueError("Reference score attribution differs")
        for side in ("left", "right"):
            if row[f"{side}_image_id"] != by_alias[pair[side]]["image_id"]:
                raise ValueError("Reference pair side changed")
        copy_checked(old / f"P1/pairs/{pair['pair_id']}.json", ref / f"P1/pairs/{pair['pair_id']}.json")
    for stage in ("detections", "templates"):
        copy_checked(old / f"P1/{stage}/runtime.json", ref / f"P1/{stage}/runtime.json")
        for item in plan["images"]:
            for ext in ("json", "npz"):
                source = old / f"P1/{stage}/{item['alias']}.{ext}"
                if source.exists():
                    copy_checked(source, ref / f"P1/{stage}/{source.name}")
                elif ext == "json":
                    raise FileNotFoundError(source)
    historic_inputs = read_json(ref / "worker-inputs.json")
    inputs, mapping = [], []
    data_root = Path(cfg["data_root"]).resolve()
    for row, historic in zip(plan["images"], historic_inputs):
        source = (data_root / row["relative_path"]).resolve()
        if not source.is_relative_to(data_root) or historic["alias"] != row["alias"] or historic["sha256"] != row["expected_sha256"]:
            raise ValueError("Input binding differs")
        if digest(source) != row["expected_sha256"]:
            raise ValueError(f"Source checksum mismatch: {row['alias']}")
        inputs.append({"key": row["alias"], "path": str(source), "sha256": row["expected_sha256"],
                       "width": historic["width"], "height": historic["height"],
                       "source_ppi": 1000, "processing_ppi": 1000})
        mapping.append({"key": row["alias"], "image_id": row["image_id"],
                        "historical_path": historic["path"], "source_path": str(source),
                        "sha256": row["expected_sha256"]})
    opaque_pairs = [{k: p[k] for k in ("pair_id", "left", "right")} for p in plan["pairs"]]
    if opaque_pairs != read_json(ref / "worker-pairs.json"):
        raise ValueError("Historical worker pair mapping differs")
    write_json(dst / "inputs.json", inputs)
    write_json(dst / "pairs.json", opaque_pairs)
    write_json(dst / "path_mapping.json", mapping)
    components = {}
    for kind, key in [("survey", "survey_dir"), ("dahia", "dahia_dir")]:
        source = Path(cfg[key])
        target = tp / kind
        frozen = settings["external"][key]
        revision = git_read(source, "rev-parse", "HEAD").decode().strip()
        if revision != frozen["revision"]:
            raise ValueError(f"Unexpected {kind} checkout revision")
        copy_checked(source / "LICENSE", target / "LICENSE")
        extra = ["README.md"]
        if kind == "dahia":
            extra += ["recognize.py", "models/detection.py", "models/description.py", "cpu-requirements.txt"]
        for name in list(frozen["files"]) + extra:
            if (source / name).exists():
                copy_checked(source / name, target / name, frozen["files"].get(name))
            elif name in extra:
                # The existing checkout is sparse. Read a pinned blob, without
                # checking it out or modifying that repository.
                write_bytes(target / name, git_read(source, "show", revision + ":" + name))
            else:
                raise FileNotFoundError(source / name)
        files = snapshot(target, [p for p in target.rglob("*") if p.is_file()])
        components[kind] = {"revision": revision, "url": settings["upstream_urls"]["survey" if kind == "survey" else "dahia_mirror"], "files": files}
    write_json(tp / "components.json", components)
    code_comparison = {}
    for name in ("pore_worker.py", "common.py", "protocol.py", "test_numerical.py"):
        relative = "V2/experiments/l3_bridge_v1/" + name
        source = Path(cfg["historical_repository"]) / relative
        current = source.read_bytes()
        historical = git_read(cfg["historical_repository"], "show", identity["source_revision"] + ":" + relative)
        copy_checked(source, ref / "code/current" / name)
        write_bytes(ref / "code/historical" / name, historical)
        code_comparison[name] = {"current_sha256": digest(source), "historical_sha256": digest(ref / "code/historical" / name),
                                 "equal_ignoring_crlf": current.replace(b"\r\n", b"\n") == historical.replace(b"\r\n", b"\n")}
    write_json(dst / "receipt.json", {"schema": "fpl3-import-v1", "historical_revision": identity["source_revision"],
                                     "historical_identity_sha256": identity_sha, "population": population,
                                     "source_images_verified": 100, "staged_images": 0,
                                     "metadata_manifest_sha256": settings["images_sha256"], "code_comparison": code_comparison,
                                     "components_sha256": digest(tp / "components.json"),
                                     "files": snapshot(dst, [p for p in dst.rglob("*") if p.is_file()])})
    return {"imported_images": 100, "imported_pairs": 250, "protected_overlap": 0, "code_comparison": code_comparison}
