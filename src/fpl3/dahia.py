"""Explicit public-access artifact audit. Does not install or execute TensorFlow."""

from __future__ import annotations

import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .io import digest, write_bytes, write_json

IDS = {"descriptor": "16GiLG7xBj64SOjCJwlCfbBcb-DORzYg1", "detector": "1U9rm_5za2kRU2FsviCe-qrZoouwUGyzI"}
SOURCE = "https://github.com/xiaochengcike/high-res-fingerprint-recognition"
REVISION = "b3c46518f2fba4937902b5e56093177c01474de9"


def safe_member(name):
    name = name.replace("\\", "/")
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or ":" in name or not p.parts:
        raise ValueError("Unsafe archive member path")
    return p


def inspect_archive(path):
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            members = [{"name": i.filename, "size": i.file_size, "directory": i.is_dir(),
                        "symlink": (i.external_attr >> 16) & 0o170000 == 0o120000} for i in z.infolist()]
        kind = "zip"
    elif tarfile.is_tarfile(path):
        with tarfile.open(path) as t:
            members = [{"name": i.name, "size": i.size, "directory": i.isdir(),
                        "symlink": not (i.isfile() or i.isdir())} for i in t.getmembers()]
        kind = "tar"
    else:
        return {"kind": "html_or_non_archive", "members": []}
    for m in members:
        safe_member(m["name"])
        if m["symlink"]:
            raise ValueError("Archive contains link or special file")
    if sum(m["size"] for m in members) > 2 * 1024**3:
        raise ValueError("Archive exceeds bounded audit size")
    return {"kind": kind, "members": members, "safe_paths": True}


def public_download(url, path):
    record = {"url": url, "checked_utc": datetime.now(timezone.utc).isoformat()}
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; local-artifact-audit)"})
        try:
            response = urlopen(request, timeout=40)
        except HTTPError as exc:
            response = exc
        with response:
            record.update(http_status=response.code, final_url=response.geturl(),
                          content_type=response.headers.get("Content-Type"),
                          content_disposition=response.headers.get("Content-Disposition"))
            body = response.read(512 * 1024**2 + 1)
            if len(body) > 512 * 1024**2:
                raise ValueError("Download exceeds 512 MiB audit bound")
        write_bytes(path, body)
        record.update(size_bytes=len(body), sha256=digest(path), body_file=Path(path).name)
        lower = body[:8192].lower()
        record["html"] = b"<html" in lower or b"<!doctype html" in lower or "text/html" in (record["content_type"] or "")
        record["login_page"] = record["html"] and (b"sign in" in lower or b"accounts.google" in lower)
        record["content"] = inspect_archive(path) if not record["html"] else {"kind": "html", "members": []}
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def check_artifacts(source, out, network=False):
    source, out = Path(source), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    readme = (source / "README.md").read_text(encoding="utf-8")
    records = []
    for kind, file_id in IDS.items():
        link = f"https://drive.google.com/open?id={file_id}"
        if link not in readme:
            raise ValueError(f"{kind} reference not present in pinned README")
        record = {"model": kind, "source_repository": SOURCE, "source_role": "identified mirror, not verified author homepage",
                  "source_revision": REVISION, "reference_url": link, "readme_sha256": digest(source / "README.md"),
                  "checked_utc": datetime.now(timezone.utc).isoformat(), "link_verified_in_source": True,
                  "code_terms": {"source": SOURCE + "/blob/" + REVISION + "/LICENSE",
                                  "license": "CC BY-NC-SA 4.0", "sha256": digest(source / "LICENSE")},
                  "weight_terms": {"status": "not separately located", "permission_inferred_from_public_access": False},
                  "required_graph": {"source": "models/description.py" if kind == "descriptor" else "models/detection.py",
                                     "input": [None, 32, 32, 1] if kind == "descriptor" else [None, "H>=17", "W>=17", 1],
                                     "output": [None, 128] if kind == "descriptor" else [None, "H-16", "W-16", 1],
                                     "checkpoint": "TF Saver variables: conv kernels and batchnorm gamma/beta/moving_mean/moving_variance; checkpoint state file",
                                     "scope": "description" if kind == "descriptor" else "detection"},
                  "attempts": [], "downloaded_model": False, "loaded": False, "inference": False,
                  "highest_verification": "reference_verified"}
        if network:
            urls = [link, f"https://drive.google.com/uc?export=download&id={file_id}",
                    f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"]
            for i, url in enumerate(urls):
                attempt = public_download(url, out / f"{kind}-response-{i}.bin")
                record["attempts"].append(attempt)
                if attempt.get("http_status") == 200 and attempt.get("content", {}).get("kind") in {"zip", "tar"}:
                    record.update(downloaded_model=True, highest_verification="archive_inspected",
                                  artifact_file=attempt["body_file"], size_bytes=attempt["size_bytes"],
                                  sha256=attempt["sha256"], archive=attempt["content"])
                    break
        record["blocker"] = "Model loading requires isolated compatible worker" if record["downloaded_model"] else (
            "No model payload obtained through tested public endpoints; this does not establish nonexistence" if network else "Network access not requested")
        records.append(record)
        write_json(out / f"{kind}.json", record)
    result = {"schema": "fpl3-dahia-artifacts-v1", "artifacts": records,
              "next_supported_step": "inspect compatible worker for accessible artifacts" if any(r["downloaded_model"] for r in records) else "weights/access still blocked",
              "tensorflow_installed_by_audit": False, "benchmark_run": False}
    write_json(out / "dahia_artifacts.json", result)
    return result
