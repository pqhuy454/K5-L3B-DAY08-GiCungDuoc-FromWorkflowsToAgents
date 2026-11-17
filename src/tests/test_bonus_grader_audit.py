"""Metamorphic audit tests for grader_a, grader_b, and grader_c (Bonus B7)."""

from __future__ import annotations

import importlib
import math

import pytest

from bonus.grader_audit_runner import (
    GRADERS,
    check_claim_delay_relation,
    check_duplicate_relation,
    check_infra_relation,
    check_permutation_relation,
)


@pytest.mark.parametrize("name", GRADERS)
def test_metamorphic_infra_identifies_infra_failure_bug(name: str):
    mod = importlib.import_module(f"grader_audit.{name}")
    res = check_infra_relation(mod.summarize)
    if name == "grader_c":
        # grader_c counts infra_error=True as passed=False, inflating graded_trials and dropping pass_rate.
        assert res["passed"] is False
        assert res["a"]["graded_trials"] == 12
        assert res["b"]["graded_trials"] == 16
        assert res["b"]["pass_rate"] < res["a"]["pass_rate"]
    else:
        assert res["passed"] is True


@pytest.mark.parametrize("name", GRADERS)
def test_metamorphic_duplicate_identifies_cost_double_counting_bug(name: str):
    mod = importlib.import_module(f"grader_audit.{name}")
    res = check_duplicate_relation(mod.summarize)
    if name == "grader_a":
        # grader_a adds each unique claim_id's cost once extra, so duplicating rows fails 2x cost scaling.
        assert res["passed"] is False
        assert "total_simulated_cost_vnd" in res["total_diffs"]
        assert "cost_per_success_vnd" in res["rate_diffs"]
    else:
        assert res["passed"] is True
    # Note: base summarize() checks len(claim_rows) == len(seeds), so pass_5 drops on duplicated rows.
    assert res["pass_5_note"]["invariant"] is False


@pytest.mark.parametrize("name", GRADERS)
def test_metamorphic_permutation_invariance(name: str):
    mod = importlib.import_module(f"grader_audit.{name}")
    res = check_permutation_relation(mod.summarize, seed=42)
    if name == "grader_a":
        # grader_a picks the first-seen trial per claim_id, making total cost depend on input order.
        assert res["passed"] is False
        assert "total_simulated_cost_vnd" in res["diffs"]
    else:
        assert res["passed"] is True


def test_metamorphic_claim_delay_flips_eligibility():
    res = check_claim_delay_relation()
    assert res["passed"] is True
    assert res["a_delay_2_vnd"] == 0
    assert res["b_delay_3_vnd"] == 35000


def test_permutation_invariance_catches_order_dependent_bug():
    """Demonstrate an order-dependent bug (unsorted p95) caught only by permutation invariance."""
    from bonus.grader_audit_runner import _load_fixture

    def buggy_unsorted_p95_summarize(trials):
        steps = [t["steps"] for t in trials if not t.get("infra_error")]
        idx = max(0, math.ceil(0.95 * len(steps)) - 1)
        return {"workflow": {"p95_steps": steps[idx]}}

    fx = _load_fixture("metamorphic_infra.json")
    a = list(fx["a"])
    b_reordered = list(reversed(a))
    # Original order ends with steps=5, reversed ends with steps=3 -> permutation catches the bug.
    assert buggy_unsorted_p95_summarize(a)["workflow"]["p95_steps"] == 5
    assert buggy_unsorted_p95_summarize(b_reordered)["workflow"]["p95_steps"] == 3
