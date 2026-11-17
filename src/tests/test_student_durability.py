"""Durability tests for the three student shapes (owner: Trinh Gia Huy, Durability & Eval).

What T11/T12 in the public matrix do not cover:

- every crash point (before_effect / after_effect_before_checkpoint / after_checkpoint),
  not only after_effect_before_checkpoint, resumed through the shape itself;
- crash + resume on the per-order cap case (T14): the full quote must reach the host on
  both runs, otherwise the resume subtracts twice;
- crash_at on a claim the host denies must neither fire nor write anything
  (a crash path is not a way around the approval gate);
- a committed amount that differs from the new quote: the shape reports `failed`,
  keeps the full quote as proposal, and the old ledger row stays.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lab8.db import connect, init_store
from lab8.durability import InjectedCrash, committed_audit_count, get_refund, issue_refund
from lab8.shapes import SHAPES
from tests.conftest import BY_ID, CLAIMS, WORLD

STUDENT_SHAPES = ["workflow", "single", "orchestrator"]
CRASH_POINTS = ["before_effect", "after_effect_before_checkpoint", "after_checkpoint"]


def _store(tmp_path: Path, name: str) -> str:
    store = tmp_path / name
    init_store(store, WORLD, CLAIMS).close()
    return str(store)


def _ledger(store: str, claim_id: str) -> tuple[int, int, int | None]:
    """(ledger rows, refund_committed audits, amount) for one claim."""
    conn = connect(store)
    try:
        rows = conn.execute(
            "SELECT COUNT(*) AS n FROM refund_ledger WHERE claim_id = ?", (claim_id,)
        ).fetchone()["n"]
        effect = get_refund(conn, claim_id)
        return int(rows), committed_audit_count(conn, claim_id), (
            int(effect["amount_vnd"]) if effect else None
        )
    finally:
        conn.close()


@pytest.mark.parametrize("point", CRASH_POINTS)
@pytest.mark.parametrize("claim_id", ["C-001", "C-014"])
@pytest.mark.parametrize("shape", STUDENT_SHAPES)
def test_crash_then_resume_pays_exactly_once(tmp_path, shape, claim_id, point):
    expected = BY_ID[claim_id]["expected"]
    store = _store(tmp_path, f"{shape}-{claim_id}-{point}.sqlite")

    with pytest.raises(InjectedCrash):
        SHAPES[shape](claim_id, seed=11, store_path=store, crash_at=point)

    rows, _, _ = _ledger(store, claim_id)
    assert rows == (0 if point == "before_effect" else 1)

    result = SHAPES[shape](claim_id, seed=11, store_path=store)
    rows, audits, amount = _ledger(store, claim_id)

    assert result.status == "resolved"
    assert result.proposal_amount == expected["proposal_amount"]  # full quote, never the net
    assert (rows, audits, amount) == (1, 1, expected["refund_vnd"])
    assert len(result.refund_effects) == 1
    assert result.committed_audit_count == 1


@pytest.mark.parametrize("claim_id", ["C-007", "C-013"])
@pytest.mark.parametrize("shape", STUDENT_SHAPES)
def test_crash_at_cannot_bypass_host_denial(tmp_path, shape, claim_id):
    """C-007: approval broken. C-013: order already refunded. Host denies before any crash point."""
    expected = BY_ID[claim_id]["expected"]
    store = _store(tmp_path, f"{shape}-{claim_id}-deny.sqlite")

    for point in CRASH_POINTS:
        result = SHAPES[shape](claim_id, seed=11, store_path=store, crash_at=point)
        assert result.status == "denied"
        assert result.proposal_amount == expected["proposal_amount"]

    rows, audits, _ = _ledger(store, claim_id)
    assert (rows, audits) == (0, 0)


@pytest.mark.parametrize("shape", STUDENT_SHAPES)
def test_conflicting_committed_amount_reports_failed_and_keeps_old_row(tmp_path, shape):
    store = _store(tmp_path, f"{shape}-conflict.sqlite")
    conn = connect(store)
    try:
        assert issue_refund(conn, "C-001", 10000)["ok"]
    finally:
        conn.close()

    result = SHAPES[shape]("C-001", seed=11, store_path=store)
    rows, audits, amount = _ledger(store, "C-001")

    assert result.status == "failed"
    assert result.proposal_amount == 35000
    assert (rows, audits, amount) == (1, 1, 10000)


@pytest.mark.parametrize("shape", STUDENT_SHAPES)
def test_retry_across_seeds_is_still_one_refund(tmp_path, shape):
    """Same store, five seeds in a row: seed must not change the idempotency key."""
    store = _store(tmp_path, f"{shape}-seeds.sqlite")
    for seed in (11, 22, 33, 44, 55):
        result = SHAPES[shape]("C-011", seed=seed, store_path=store)
        assert result.status == "resolved"
    assert _ledger(store, "C-011") == (1, 1, 35000)
