"""Read human-coded framing acceptance from the immutable source decision log."""

from __future__ import annotations

import json
from pathlib import Path

from .metric_status import VERIFIED, metric_result


def evaluate_framing(decision_log_path: Path) -> dict[str, dict]:
    data = json.loads(decision_log_path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for shot in data.get("shots", []):
        shot_id = shot.get("shot_id", "")
        keyframe = shot.get("keyframe_generation") or {}
        approved = keyframe.get("status") == "approved"
        out[shot_id] = metric_result(
            "pass" if approved else "pending",
            value="accepted_by_human_review" if approved else None,
            source_status=VERIFIED,
            source=str(decision_log_path),
            note=(
                f"Human-coded visual framing status; recorded framing={shot.get('framing', 'unknown')}. "
                "This is not an automatic numeric framing score."
            ),
            framing_label=shot.get("framing", "unknown"),
        )
    return out
