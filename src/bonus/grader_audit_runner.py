"""Reproducible metamorphic audit runner for grader_a, grader_b, and grader_c (Bonus B7)."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import random
from pathlib import Path
from typing import Any

from lab8.compensation import quote

GRADERS = ("grader_a", "grader_b", "grader_c")
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "grader_audit" / "fixtures"

RATE_KEYS = (
    "pass_rate",
    "seed_pass_rates",
    "cost_per_success_vnd",
    "mean_steps",
    "p95_steps",
)
TOTAL_KEYS = ("trials", "graded_trials", "successes", "total_simulated_cost_vnd")


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _approx_equal(x: Any, y: Any, tol: float = 1e-9) -> bool:
    if isinstance(x, list) and isinstance(y, list):
        return len(x) == len(y) and all(_approx_equal(a, b, tol) for a, b in zip(x, y))
    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
        return math.isclose(float(x), float(y), rel_tol=tol, abs_tol=tol)
    return x == y


def check_infra_relation(summarize_fn: Any) -> dict[str, Any]:
    fx = _load_fixture("metamorphic_infra.json")
    stats_a = summarize_fn(fx["a"])["workflow"]
    stats_b = summarize_fn(fx["b"])["workflow"]
    passed = _approx_equal(stats_a["pass_rate"], stats_b["pass_rate"]) and (
        stats_a["graded_trials"] == stats_b["graded_trials"]
    )
    return {
        "relation": fx["relation"],
        "passed": passed,
        "a": {"graded_trials": stats_a["graded_trials"], "pass_rate": stats_a["pass_rate"]},
        "b": {"graded_trials": stats_b["graded_trials"], "pass_rate": stats_b["pass_rate"]},
    }


def check_duplicate_relation(summarize_fn: Any) -> dict[str, Any]:
    fx = _load_fixture("metamorphic_duplicate.json")
    stats_a = summarize_fn(fx["a"])["workflow"]
    stats_b = summarize_fn(fx["b"])["workflow"]

    rate_diffs = {
        k: {"a": stats_a[k], "b": stats_b[k]}
        for k in RATE_KEYS
        if not _approx_equal(stats_a[k], stats_b[k])
    }
    total_diffs = {
        k: {"expected_2x": 2 * stats_a[k], "actual_b": stats_b[k]}
        for k in TOTAL_KEYS
        if not _approx_equal(2 * stats_a[k], stats_b[k])
    }
    return {
        "relation": fx["relation"],
        "passed": not rate_diffs and not total_diffs,
        "a": {k: stats_a[k] for k in (*TOTAL_KEYS, "pass_rate", "pass_5", "cost_per_success_vnd")},
        "b": {k: stats_b[k] for k in (*TOTAL_KEYS, "pass_rate", "pass_5", "cost_per_success_vnd")},
        "rate_diffs": rate_diffs,
        "total_diffs": total_diffs,
        "pass_5_note": {
            "a": stats_a["pass_5"],
            "b": stats_b["pass_5"],
            "invariant": _approx_equal(stats_a["pass_5"], stats_b["pass_5"]),
        },
    }


def check_permutation_relation(summarize_fn: Any, *, seed: int = 42) -> dict[str, Any]:
    fx = _load_fixture("metamorphic_infra.json")
    trials_a = list(fx["a"])
    trials_b = list(fx["a"])
    random.Random(seed).shuffle(trials_b)

    stats_a = summarize_fn(trials_a)["workflow"]
    stats_b = summarize_fn(trials_b)["workflow"]
    keys = (*TOTAL_KEYS, *RATE_KEYS, "seed_variance")
    diffs = {
        k: {"a": stats_a[k], "b": stats_b[k]}
        for k in keys
        if not _approx_equal(stats_a[k], stats_b[k])
    }
    return {
        "relation": "permutation_invariance",
        "passed": not diffs,
        "diffs": diffs,
    }


def check_claim_delay_relation() -> dict[str, Any]:
    fx = _load_fixture("metamorphic_claim_delay.json")
    q_a = quote(fx["a"]["order"], fx["policies"], as_of=fx["as_of"])
    q_b = quote(fx["b"]["order"], fx["policies"], as_of=fx["as_of"])
    passed = q_a.amount_vnd == 0 and q_b.amount_vnd == fx["b"]["order"]["shipping_fee_vnd"]
    return {
        "relation": fx["relation"],
        "passed": passed,
        "a_delay_2_vnd": q_a.amount_vnd,
        "b_delay_3_vnd": q_b.amount_vnd,
    }


def run_audit() -> dict[str, Any]:
    graders_report: dict[str, Any] = {}
    for name in GRADERS:
        mod = importlib.import_module(f"grader_audit.{name}")
        graders_report[name] = {
            "metamorphic_infra": check_infra_relation(mod.summarize),
            "metamorphic_duplicate": check_duplicate_relation(mod.summarize),
            "permutation_invariance": check_permutation_relation(mod.summarize),
        }
    return {
        "topic": "B7",
        "claim_delay": check_claim_delay_relation(),
        "graders": graders_report,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run metamorphic audit on grader_a/b/c.")
    parser.add_argument("--out", default="reports/bonus_grader_audit.json")
    args = parser.parse_args()

    report = run_audit()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    for name, res in report["graders"].items():
        infra_ok = res["metamorphic_infra"]["passed"]
        dup_ok = res["metamorphic_duplicate"]["passed"]
        perm_ok = res["permutation_invariance"]["passed"]
        print(f"{name}: infra={infra_ok} duplicate={dup_ok} permutation={perm_ok}")
    print(f"claim_delay: {report['claim_delay']}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
