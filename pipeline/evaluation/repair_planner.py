"""Create non-executing repair proposals from metric verdicts."""

from __future__ import annotations

from typing import Any


def plan_repairs(shot_id: str, metrics: dict[str, dict], max_attempts: int = 3) -> dict[str, Any]:
    proposals: list[dict[str, str]] = []

    identity = metrics.get("identity", {})
    if identity.get("verdict") in {"needs_review", "fail"}:
        proposals.append({
            "trigger": "identity",
            "action": "identity anchor / profile anchor / input_fidelity repair",
            "execution": "not_executed",
        })

    framing = metrics.get("framing", {})
    if framing.get("verdict") in {"needs_review", "fail"}:
        proposals.append({
            "trigger": "framing",
            "action": "framing prompt rewrite",
            "execution": "not_executed",
        })

    pose = metrics.get("pose", {})
    if pose.get("verdict") in {"needs_review", "fail"}:
        proposals.append({
            "trigger": "pose",
            "action": "stronger pose conditioning or record backend limitation",
            "execution": "not_executed",
        })
    elif pose.get("verdict") == "pending":
        proposals.append({
            "trigger": "pose_pending",
            "action": "obtain generated-side DWPose locally before deciding; do not regenerate",
            "execution": "not_executed",
        })

    motion = metrics.get("motion_energy", {})
    if motion.get("verdict") in {"needs_review", "fail"}:
        proposals.append({
            "trigger": "motion_energy",
            "action": "motion prompt repair only; do not regenerate the keyframe",
            "execution": "not_executed",
        })

    timing = metrics.get("timing", {})
    beat = metrics.get("beat_alignment", {})
    if timing.get("verdict") in {"needs_review", "fail"} or beat.get("verdict") in {"needs_review", "fail"}:
        proposals.append({
            "trigger": "beat_or_timing",
            "action": "duration / assembly trim repair",
            "execution": "not_executed",
        })
    elif beat.get("verdict") == "pending":
        proposals.append({
            "trigger": "beat_alignment_pending",
            "action": "compute formal beat-boundary offset before changing assembly",
            "execution": "not_executed",
        })

    return {
        "shot_id": shot_id,
        "execute_repair": False,
        "max_attempts": max_attempts,
        "proposals": proposals,
        "terminal_rule": "After max attempts, mark needs_human.",
        "current_terminal_state": "needs_human" if len(proposals) >= max_attempts else "not_reached",
    }
