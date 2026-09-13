"""Shared pair execution and accounting; compatible with the P1 interpreter."""

import time
from dataclasses import asdict

from .contracts import MatchResult


def execute_pairs(pairs, templates, extraction, matcher, setup_error=None):
    """One logical result per frozen opaque pair, including valid zeros."""
    results = []
    for pair in pairs:
        invoked, start = False, time.perf_counter()
        try:
            if setup_error:
                result = MatchResult("blocked", None, setup_error, "setup")
            elif any(extraction[pair[s]]["status"] != "success" for s in ("left", "right")):
                result = MatchResult("failure", None, "EXTRACTION_FAILURE", "extraction")
            else:
                invoked = True
                score = matcher.match(templates[pair["left"]], templates[pair["right"]])
                result = MatchResult("success", score, matcher_invoked=True)
        except Exception as exc:
            result = MatchResult("failure", None, f"{type(exc).__name__}: {exc}", "matching", matcher_invoked=invoked)
        row = {**pair, **asdict(result)}
        row["timings"] = {"comparison_seconds": time.perf_counter() - start}
        results.append(row)
    return results


def coverage(results):
    if len({r["pair_id"] for r in results}) != len(results):
        raise ValueError("Duplicate pair result")
    return {"planned": len(results), "logical_attempts": sum(r["status"] in {"success", "failure"} for r in results),
            "matcher_invocations": sum(r["matcher_invoked"] for r in results),
            **{s: sum(r["status"] == s for r in results) for s in ("success", "failure", "blocked", "pending")},
            "zero_scores": sum(r["status"] == "success" and r["score"] == 0 for r in results)}
