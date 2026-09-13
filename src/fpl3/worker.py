"""P1-only process entry point. It receives no subject selection or pair truth."""

from __future__ import annotations

import argparse
import contextlib
import sys
import time
from pathlib import Path

from .cache import cache_key, encode, read_cache, write_cache
from .code_identity import check_code
from .contracts import Image
from .io import digest, fingerprint, read_json, verify_files, write_bytes, write_json
from .worker_protocol import SCHEMA
from .results import coverage, execute_pairs


def validate_opaque_job(payload):
    allowed = {"inputs", "pairs", "config", "components", "artifacts", "cache_dir", "run_dir", "signature", "fresh", "expected_runtime"}
    if set(payload) != allowed:
        raise ValueError("Unexpected P1 job fields")
    input_keys = {"key", "path", "sha256", "width", "height", "source_ppi", "processing_ppi"}
    if any(set(item) != input_keys for item in payload["inputs"]):
        raise ValueError("Worker image interface contains unexpected fields")
    if any(set(pair) != {"pair_id", "left", "right"} for pair in payload["pairs"]):
        raise ValueError("Worker pair interface cannot carry protocol truth")
    keys = {item["key"] for item in payload["inputs"]}
    if len(keys) != len(payload["inputs"]) or len({p["pair_id"] for p in payload["pairs"]}) != len(payload["pairs"]):
        raise ValueError("Duplicate worker input")
    if any(pair[side] not in keys for pair in payload["pairs"] for side in ("left", "right")):
        raise ValueError("Worker pair references unknown input")


def run_features(payload):
    from .runtime import doctor, numerical_identity
    validate_opaque_job(payload)
    started = time.perf_counter()
    inputs, pairs, config = payload["inputs"], payload["pairs"], payload["config"]
    out, signature, fresh = Path(payload["run_dir"]), payload["signature"], payload["fresh"]
    local = {"cache_dir": payload["cache_dir"]}
    error, matcher = None, None
    mark = time.perf_counter()
    try:
        import cv2
        from .biometrics import build_route
        environment = doctor("p1")
        write_json(out / "worker-environment.json", environment)
        if environment["manager"] != "conda" or not environment["isolated_packages"] or environment["enable_user_site"]:
            raise ValueError("P1 worker is not isolated in Conda")
        expected = payload["expected_runtime"]
        if environment["python"] != expected["python"]:
            raise ValueError("Historical Python version differs")
        for package in ("numpy", "torch", "torchvision", "opencv-contrib-python", "scipy"):
            if environment["packages"][package]["version"] != expected[package]:
                raise ValueError(f"Historical numerical package differs: {package}")
        if numerical_identity() != signature["environment"]:
            raise ValueError("Worker numerical environment changed after preflight")
        for component, meta in payload["components"].items():
            verify_files(Path(payload["artifacts"]) / component, meta["files"])
        detector, descriptor, matcher = build_route(config, payload["artifacts"])
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    load_seconds = time.perf_counter() - mark
    templates, extraction = {}, {}
    for i, item in enumerate(inputs):
        image = Image(**{**item, "path": Path(item["path"])})
        record = {"key": image.key, "status": "blocked" if error else "failure", "reason": error,
                  "failure_stage": "setup" if error else None, "timings": {}, "cache_hit": False}
        stage = "source_binding"
        mark = time.perf_counter()
        try:
            if not error:
                if digest(image.path) != image.sha256:
                    raise ValueError("Input digest changed")
                stage = "input"
                pixels = cv2.imread(str(image.path), cv2.IMREAD_GRAYSCALE)
                if pixels is None or pixels.shape != (image.height, image.width) or str(pixels.dtype) != "uint8":
                    raise ValueError("Expected unchanged native gray8 geometry")
                record["timings"]["input_seconds"] = time.perf_counter() - mark
                key = cache_key(image, signature)
                record["cache_key"] = key
                stage = "cache"
                features = None if fresh else read_cache(local["cache_dir"], key, image)
                if features is None:
                    mark, stage = time.perf_counter(), "detection"
                    points = detector.detect(image, pixels, out / "scratch" / image.key)
                    points.validate(image)
                    record["timings"]["detection_seconds"] = time.perf_counter() - mark
                    mark, stage = time.perf_counter(), "description"
                    described = descriptor.describe(image, pixels, points)
                    described.validate(points, image)
                    record["timings"]["description_seconds"] = time.perf_counter() - mark
                    # Persist fresh arrays before cache validation, retaining discrepancies.
                    write_bytes(out / "templates" / f"{image.key}.npz", encode(points, described))
                    stage = "cache_write"
                    write_cache(local["cache_dir"], key, image, points, described)
                else:
                    points, described = features
                    record["cache_hit"] = True
                    write_bytes(out / "templates" / f"{image.key}.npz", encode(points, described))
                templates[image.key] = described
                record.update(status="success", reason=None, failure_stage=None,
                              points=len(points.xy), descriptors=len(described.values),
                              npz_sha256=digest(out / "templates" / f"{image.key}.npz"))
        except Exception as exc:
            infrastructure = isinstance(exc, OSError) or stage in {"source_binding", "cache", "cache_write"}
            record.update(status="failure", reason=f"{type(exc).__name__}: {exc}", failure_stage=stage,
                          failure_category="infrastructure" if infrastructure else "processing")
            record["timings"]["failed_stage_seconds"] = time.perf_counter() - mark
        extraction[image.key] = record
        write_json(out / "templates" / f"{image.key}.json", record)
        print(f"image {i + 1}/{len(inputs)} {record['status']}", file=sys.stderr, flush=True)
    results = execute_pairs(pairs, templates, extraction, matcher, error)
    write_json(out / "pairs.json", results)
    summary = {**coverage(results), "images": len(inputs),
               "extraction_attempts": sum(r["status"] != "blocked" for r in extraction.values()),
               "extraction_successes": sum(r["status"] == "success" for r in extraction.values()),
               "cache_hits": sum(r["cache_hit"] for r in extraction.values()),
               "fresh_extractions": sum(r["status"] == "success" and not r["cache_hit"] for r in extraction.values()),
               "model_and_adapter_load_seconds": load_seconds,
               "shared_image_timings": {k: sum(r["timings"].get(k, 0) for r in extraction.values())
                                        for k in ("input_seconds", "detection_seconds", "description_seconds")},
               "comparison_seconds": sum(r["timings"]["comparison_seconds"] for r in results),
               "total_seconds": time.perf_counter() - started, "setup_error": error}
    write_json(out / "worker-summary.json", summary)
    return summary


def validate_request(request):
    if request.get("schema") != SCHEMA:
        raise ValueError("Unsupported worker protocol version")
    expected_id = fingerprint({k: v for k, v in request.items() if k != "request_id"})
    if request.get("request_id") != expected_id:
        raise ValueError("Worker request checksum changed")
    if Path(sys.prefix).resolve() != Path(request["expected_prefix"]).resolve():
        raise ValueError("Worker started in the wrong interpreter prefix")
    if request["action"] not in {"doctor", "check-p1-numerics", "run-p1"}:
        raise ValueError("Unknown worker action")
    if request["action"] == "run-p1" and request["payload"]["signature"]["code"] != request["code"]:
        raise ValueError("Worker request and run code signature differ")


def handle(request):
    action, payload = request["action"], request["payload"]
    if action == "doctor":
        from .runtime import doctor, numerical_identity
        environment = doctor("p1")
        return {"environment": environment, "numerical_identity": numerical_identity()}
    if action == "check-p1-numerics":
        from .numerical import check_p1
        return check_p1(payload["artifacts"], payload["output"])
    if action == "run-p1":
        return run_features(payload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    response = {"schema": SCHEMA, "request_id": request.get("request_id")}
    try:
        with contextlib.redirect_stdout(sys.stderr):
            validate_request(request)
            response["code_identity"] = {"before": check_code(request["code"])}
            result = handle(request)
            response["code_identity"]["after"] = check_code(request["code"])
            response.update(status="success", result=result)
        code = 0
    except Exception as exc:
        response.update(status="failure", error=f"{type(exc).__name__}: {exc}")
        code = 2
    write_json(request["response"], response)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
