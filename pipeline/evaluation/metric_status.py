"""Shared metric result schema for audit-only evaluation."""

from __future__ import annotations

from typing import Any


VALID_VERDICTS = {"pass", "needs_review", "fail", "not_applicable", "pending"}
VERIFIED = "VERIFIED FROM EXISTING REPORT"
COMPUTED_LOCAL = "COMPUTED LOCAL / $0"
PENDING = "PENDING · NOT COMPUTED"


def metric_result(
    verdict: str,
    *,
    value: Any = None,
    source_status: str,
    source: str,
    note: str,
    **extra: Any,
) -> dict[str, Any]:
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"Unsupported metric verdict: {verdict}")
    result = {
        "verdict": verdict,
        "value": value,
        "source_status": source_status,
        "source": source,
        "note": note,
    }
    result.update(extra)
    return result
