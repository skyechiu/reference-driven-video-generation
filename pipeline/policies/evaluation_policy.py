"""
evaluation_policy.py — Mode A motion-evaluation & repair-priority policy.

Reusable, side-effect-free policy for judging whether a generated clip moves
enough, using the optical-flow motion audit as evidence, and deciding what
repair action a shot earns.

Extracted from the street-run audit. Key lesson: the first/mid/last "clip
review sheet" is NOT sufficient evidence — for a near-static clip its three
columns look identical and hide the problem. Motion energy must be measured
from dense optical flow, not eyeballed from three frames.

This module records the *concept and thresholds*. It does not run optical flow
itself (no cv2/numpy import at module load); pass in already-measured numbers,
or wire it to the existing audit that produces them. No API, no I/O on import.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Repair-priority outcomes ─────────────────────────────────────────────────
class MotionRepairPriority:
    KEEP               = "keep"                # motion adequate (or reference itself calm)
    RERUN_PROMPT_ONLY  = "rerun_prompt_only"   # strip damping / add cues, same keyframe
    RERUN_KEYFRAME     = "rerun_keyframe"       # keyframe pose/framing blocks motion; redo it
    ARCHIVE_LIMITATION = "archive_limitation"   # backend can't do it — record as honest limit


# ── Thresholds (optical flow, % of frame height per frame) ───────────────────
# Calibrated from the street run: v1 shot_001=14%, shot_003=19% read as
# "too static"; after prompt repair 51% / 47% read as clearly moving.
MOTION_ENERGY_LOW   = 20.0   # below this: subject looks static -> needs repair
MOTION_ENERGY_OK    = 35.0   # at/above this: motion reads as present
# Fraction of total flow that must come from the SUBJECT (not the camera) for
# the motion to count as real subject motion rather than a camera pan.
SUBJECT_SHARE_MIN   = 0.35


@dataclass
class MotionMetrics:
    shot_id: str
    motion_energy_ratio: float          # dense optical-flow mean, % of frame height / frame
    subject_share: float = 1.0          # subject flow / total flow  (1.0 = unknown/assume subject)
    reference_energy_ratio: Optional[float] = None   # same metric on the matching reference segment
    from_optical_flow: bool = True      # evidence source guard (see require_optical_flow_evidence)
    identity_ok: bool = True            # identity held in the clip (from ArcFace / human review)
    keyframe_pose_supports_motion: bool = True  # does the keyframe pose/framing allow the motion?


def compute_motion_energy_ratio(per_frame_flow_magnitudes: list, frame_height_px: int) -> float:
    """Reduce a sequence of per-frame mean flow magnitudes (in pixels) to the
    motion_energy_ratio: mean magnitude as a percentage of frame height.

    Pure arithmetic — the caller supplies numbers already measured by the
    optical-flow audit (Farnebaeck). Kept dependency-free on purpose.
    """
    if not per_frame_flow_magnitudes or frame_height_px <= 0:
        return 0.0
    mean_mag = sum(per_frame_flow_magnitudes) / len(per_frame_flow_magnitudes)
    return round(mean_mag / frame_height_px * 100.0, 3)


def require_optical_flow_evidence(metrics: MotionMetrics) -> None:
    """Guard: refuse to classify from first/mid/last review sheets alone.

    The three-frame review sheet is a convenience preview, not evidence — a
    static clip makes its columns identical. Raise if the metric did not come
    from the dense optical-flow audit.
    """
    if not metrics.from_optical_flow:
        raise ValueError(
            f"{metrics.shot_id}: motion_energy_ratio must come from the optical-flow "
            "audit, not the first/mid/last review sheet."
        )


def classify_motion_repair_priority(metrics: MotionMetrics) -> str:
    """Decide the repair action for one shot. Pure decision function.

    Logic:
      * If the matching reference segment is itself calm, KEEP (faithful — do
        not invent motion the reference never had).
      * Adequate subject-driven energy -> KEEP.
      * Too static but the keyframe pose allows motion -> RERUN_PROMPT_ONLY
        (strip damping, add cues via motion_policy.repair_motion_prompt).
      * Too static because the keyframe pose/framing blocks it -> RERUN_KEYFRAME.
      * Prompt repair already tried and it is still static, or identity breaks
        whenever motion rises -> ARCHIVE_LIMITATION (record honestly; do not
        keep burning generations).
    """
    require_optical_flow_evidence(metrics)

    # Faithful-to-reference: never fabricate motion a calm reference lacks.
    if (metrics.reference_energy_ratio is not None
            and metrics.reference_energy_ratio < MOTION_ENERGY_LOW):
        return MotionRepairPriority.KEEP

    subject_energy = metrics.motion_energy_ratio * metrics.subject_share
    if subject_energy >= MOTION_ENERGY_OK:
        return MotionRepairPriority.KEEP

    if not metrics.keyframe_pose_supports_motion:
        return MotionRepairPriority.RERUN_KEYFRAME

    if not metrics.identity_ok:
        # motion is achievable but it costs identity -> honest limitation
        return MotionRepairPriority.ARCHIVE_LIMITATION

    if metrics.motion_energy_ratio < MOTION_ENERGY_LOW:
        return MotionRepairPriority.RERUN_PROMPT_ONLY

    # borderline (between LOW and OK) with good keyframe + identity: cheap retry
    return MotionRepairPriority.RERUN_PROMPT_ONLY


__all__ = [
    "MotionRepairPriority", "MotionMetrics",
    "MOTION_ENERGY_LOW", "MOTION_ENERGY_OK", "SUBJECT_SHARE_MIN",
    "compute_motion_energy_ratio", "require_optical_flow_evidence",
    "classify_motion_repair_priority",
]
