"""Reuse the existing ArcFace diagnostic; never run face models here."""

from __future__ import annotations

import json
from pathlib import Path

from .metric_status import VERIFIED, metric_result


NO_FACE_SHOTS = {"shot_002", "shot_003"}


def _recorded_scores(project_state_path: Path) -> dict[str, float | None]:
    if not project_state_path.exists():
        return {}
    state = json.loads(project_state_path.read_text(encoding="utf-8"))
    shots = (((state.get("experiments") or {}).get("loop_on") or {}).get("shots") or [])
    return {s.get("shot_id", ""): s.get("identity_score") for s in shots}


def evaluate_identity(shot_ids: list[str], project_state_path: Path) -> dict[str, dict]:
    scores = _recorded_scores(project_state_path)
    out: dict[str, dict] = {}
    for shot_id in shot_ids:
        if shot_id in NO_FACE_SHOTS:
            out[shot_id] = metric_result(
                "not_applicable",
                source_status=VERIFIED,
                source=str(project_state_path),
                note="No reliable face is visible (back view or feet-only insert).",
            )
            continue
        value = scores.get(shot_id)
        if value is None:
            out[shot_id] = metric_result(
                "pending",
                source_status="PENDING · NOT COMPUTED",
                source=str(project_state_path),
                note="No recorded ArcFace diagnostic was found; no model was run by this harness.",
            )
            continue
        out[shot_id] = metric_result(
            "needs_review",
            value=round(float(value), 4),
            source_status=VERIFIED,
            source=str(project_state_path),
            note=(
                "Recorded ArcFace buffalo_l diagnostic. Low cosine is an operational warning, "
                "not an automatic failure for synthetic/profile imagery."
            ),
            method="ArcFace buffalo_l cosine (post-hoc existing diagnostic)",
        )
    return out
