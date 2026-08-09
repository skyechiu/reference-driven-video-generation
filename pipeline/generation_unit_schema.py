"""
generation_unit_schema.py
=========================
Canonical generation unit schema for the Reference-Driven Video Generation System.

All three reference strategies normalize into generation_units before entering
the shared core loop (generation → evaluation → repair → decision log).

unit_type values:
  "shot"             — Strategy A: Multi-shot Storyboard
  "key_moment_clip"  — Strategy B: Single-take Key Moments
  "dance_segment"    — Strategy C: Driving Performance

This file defines:
  - GENERATION_UNIT_SCHEMA  : the default template (all fields)
  - make_unit()             : factory with validation
  - validate_unit()         : check required fields
  - EVALUATION_PROFILES     : evaluation metric sets per unit_type
  - REPAIR_RULES            : failure → repair action table
  - DECISION_LOG_SCHEMA     : per-attempt decision log template
"""

from __future__ import annotations
from copy import deepcopy
from typing import Literal

# ─── Unit types ────────────────────────────────────────────────────────────

UNIT_TYPES = ("shot", "key_moment_clip", "dance_segment")

# ─── Canonical schema (all fields, defaults None / empty) ─────────────────

GENERATION_UNIT_SCHEMA: dict = {
    # Identity
    "unit_id":      None,   # str  e.g. "shot_001" / "single_take_001_m02" / "dance_seg_001"
    "unit_type":    None,   # str  "shot" | "key_moment_clip" | "dance_segment"

    # Timing
    "start_s":      None,   # float
    "end_s":        None,   # float
    "duration_s":   None,   # float

    # Strategy B: parent shot this moment belongs to
    "parent_shot_id": None,  # str | None

    # Source media
    "source_panel":   None,  # str  path to best frame / key pose image
    "pose_ref":       None,  # str  path to pose JSON (MediaPipe keypoints)
    "pose_sequence":  None,  # str  path to pose sequence JSON (Strategy C only)

    # Framing (tool-measured ground truth)
    "framing_target": {
        "shot_size":          None,   # str  "medium_close_up" / "wide" / "full_body" etc.
        "face_center_x":      None,   # float 0–1, None if face not visible
        "face_center_y":      None,   # float 0–1
        "face_width_ratio":   None,   # float fraction of frame width
        "person_center_x":    None,   # float 0–1
        "person_height_ratio": None,  # float fraction of frame height
        "feet_visible":       None,   # bool  | None
    },

    # Camera (tool-measured + VLM)
    "camera": {
        "angle":    None,   # str  "front" / "side" / "back" / "three-quarter"
        "motion":   None,   # str  "static" / "orbit" / "slow_push_in" etc.
        "distance": None,   # str  mirrors shot_size
    },

    # VLM semantic enrichment (source: "vlm_caption")
    "semantic_analysis": {
        "action":                    None,  # str
        "expression":                None,  # str  | "not visible"
        "emotion":                   None,  # str
        "gaze":                      None,  # str
        "body_orientation":          None,  # str  "front" / "side" / "back" etc.
        "lighting":                  None,  # str
        "scene_notes":               None,  # str
        "relation_to_previous_shot": None,  # str  (Strategy A only)
        "continuity_role":           None,  # str  (Strategy B: "mid-orbit" etc.)
        "lighting_change":           None,  # str  (Strategy B)
        "background_perspective_change": None,  # str  (Strategy B)
        "prompt_fragment":           None,  # str  VLM-suggested generation hint
        "source":                    "vlm_caption",
    },

    # View / identity eval routing
    "view":               None,   # str  "front" | "three-quarter" | "side" | "back" | "over-shoulder"
    "identity_eval_mode": None,   # str  "face_embedding" | "face_embedding_and_look" | "look_and_silhouette"

    # Asset targets (from Setup)
    "subject_target": {
        "identity_id":   None,          # str  e.g. "ip_01_four_selves"
        "look_id":       None,          # str  e.g. "look_3_tailored_self"
        "replace_scope": "full_subject",  # str
    },
    "scene_target": {
        "scene_id":   None,                       # str  e.g. "scene_02_modern_street"
        "scene_mode": "replace_reference_scene",  # str
    },

    # Strategy C backend
    "backend_config": {
        "type":   None,  # str  "pose_guided_human_animation"
        "name":   None,  # str  "mimicmotion" | "musepose" | "placeholder"
        "status": None,  # str  "active" | "placeholder"
    },

    # Generation prompts (built by PromptBuilder)
    "generation_prompts": {
        "keyframe_prompt": None,  # str
        "video_prompt":    None,  # str
        "negative_prompt": None,  # str
    },

    # Evaluation targets (set by strategy / unit_type)
    "evaluation_targets": {
        "identity_min":         "calibrated",  # str | float
        "look_min":             0.70,
        "scene_min":            0.70,
        "framing_min":          0.75,
        "pose_min":             0.70,
        "body_integrity_min":   0.75,   # Strategy C only
        "beat_offset_ms_max":   150,
        "subject_count_expected": 1,
    },

    # Risk flags
    "risk_flags": [],  # list[str]

    # Pipeline state
    "status":         "pending",   # str  "pending" | "generating" | "pass" | "fail" | "needs_human"
    "generated_image": None,       # str  path
    "generated_clip":  None,       # str  path
    "evaluation":     {"status": "pending", "attempts": []},
}


# ─── Factory ───────────────────────────────────────────────────────────────

def make_unit(
    unit_id:   str,
    unit_type: Literal["shot", "key_moment_clip", "dance_segment"],
    start_s:   float,
    end_s:     float,
    **overrides,
) -> dict:
    """
    Create a new generation unit from the canonical schema.
    Pass any field overrides as keyword arguments using flat names for
    nested dicts (e.g. framing_target={"shot_size": "medium"}).
    """
    if unit_type not in UNIT_TYPES:
        raise ValueError(f"unit_type must be one of {UNIT_TYPES}, got: {unit_type!r}")

    unit = deepcopy(GENERATION_UNIT_SCHEMA)
    unit["unit_id"]   = unit_id
    unit["unit_type"] = unit_type
    unit["start_s"]   = round(float(start_s), 3)
    unit["end_s"]     = round(float(end_s), 3)
    unit["duration_s"] = round(float(end_s) - float(start_s), 3)

    for k, v in overrides.items():
        if k in unit and isinstance(unit[k], dict) and isinstance(v, dict):
            unit[k].update(v)
        else:
            unit[k] = v

    return unit


def validate_unit(unit: dict) -> list[str]:
    """
    Validate a generation unit. Returns a list of error strings.
    Empty list = valid.
    """
    errors = []
    if not unit.get("unit_id"):
        errors.append("unit_id is required")
    if unit.get("unit_type") not in UNIT_TYPES:
        errors.append(f"unit_type must be one of {UNIT_TYPES}")
    if unit.get("start_s") is None:
        errors.append("start_s is required")
    if unit.get("end_s") is None:
        errors.append("end_s is required")
    if unit.get("unit_type") == "dance_segment" and not unit.get("pose_sequence"):
        errors.append("dance_segment requires pose_sequence path")
    return errors


# ─── Evaluation profiles (metric sets per unit_type) ──────────────────────

EVALUATION_PROFILES: dict[str, list[str]] = {
    "shot": [
        "identity_score",
        "look_score",
        "scene_score",
        "framing_score",
        "pose_score",
        "subject_count_check",
        "beat_score",   # optional — skipped if no audio
    ],
    "key_moment_clip": [
        "identity_score",
        "look_score",
        "scene_score",
        "framing_score",
        "pose_score",
        "subject_count_check",
        # beat_score not applicable — moments are semantic, not beat-cut
    ],
    "dance_segment": [
        "identity_score",
        "look_score",
        "pose_sequence_score",
        "body_integrity_score",
        "full_body_visibility",
        "framing_score",
        "subject_count_check",
    ],
}

# ─── Repair rules table ────────────────────────────────────────────────────

REPAIR_RULES: list[dict] = [
    {
        "failure":        "identity_drift",
        "applies_to":     ["shot", "key_moment_clip", "dance_segment"],
        "repair_action":  "Regenerate keyframe with stronger identity reference. Increase ip_adapter_scale.",
        "targeted_param": "ip_scale_boost",
    },
    {
        "failure":        "look_mismatch",
        "applies_to":     ["shot", "key_moment_clip", "dance_segment"],
        "repair_action":  "Strengthen look prompt. Add more look reference images.",
        "targeted_param": "look_ref_boost",
    },
    {
        "failure":        "scene_mismatch",
        "applies_to":     ["shot", "key_moment_clip"],
        "repair_action":  "Rewrite scene prompt. Use scene reference images explicitly.",
        "targeted_param": "scene_prompt_rewrite",
    },
    {
        "failure":        "framing_error",
        "applies_to":     ["shot", "key_moment_clip", "dance_segment"],
        "repair_action":  "Rewrite framing instruction in keyframe prompt.",
        "targeted_param": "framing_prompt_rewrite",
    },
    {
        "failure":        "pose_mismatch",
        "applies_to":     ["shot", "key_moment_clip"],
        "repair_action":  "Strengthen pose reference. Explicitly describe body position.",
        "targeted_param": "controlnet_scale_boost",
    },
    {
        "failure":        "motion_issue",
        "applies_to":     ["shot", "key_moment_clip"],
        "repair_action":  "Rerun I2V only. Keep keyframe, change video prompt.",
        "targeted_param": "rerun_i2v",
    },
    {
        "failure":        "extra_subject",
        "applies_to":     ["shot", "key_moment_clip", "dance_segment"],
        "repair_action":  "Add stricter single-character constraint. Increase negative prompt weight for 'multiple people'.",
        "targeted_param": "single_char_constraint",
    },
    {
        "failure":        "body_deformation",
        "applies_to":     ["dance_segment"],
        "repair_action":  "Shorten segment. Choose clearer key pose. Reduce motion intensity.",
        "targeted_param": "segment_shorten",
    },
    {
        "failure":        "beat_drift",
        "applies_to":     ["shot"],
        "repair_action":  "Adjust cut timing. Snap to nearest beat within max_snap_distance.",
        "targeted_param": "beat_resnap",
    },
    {
        "failure":        "pose_sequence_drift",
        "applies_to":     ["dance_segment"],
        "repair_action":  "Smooth pose sequence. Filter low-confidence frames. Re-extract with higher min_confidence.",
        "targeted_param": "pose_smooth",
    },
]

REPAIR_RULES_BY_FAILURE = {r["failure"]: r for r in REPAIR_RULES}


# ─── Decision log schema ───────────────────────────────────────────────────

DECISION_LOG_ENTRY_SCHEMA: dict = {
    "unit_id":     None,   # str
    "unit_type":   None,   # str  "shot" | "key_moment_clip" | "dance_segment"
    "attempt_id":  None,   # int  1-indexed
    "stage":       None,   # str  "keyframe_generation" | "i2v_generation" | "pose_driven_generation"
    "backend":     None,   # str  "openai_image_backend" | "kling_i2v" | "mimicmotion" | etc.
    "inputs": {
        "source_panel":   None,   # str
        "identity_refs":  [],     # list[str]
        "look_refs":      [],     # list[str]
        "scene_refs":     [],     # list[str]
        "pose_ref":       None,   # str
        "pose_sequence":  None,   # str
    },
    "outputs": {
        "keyframe":  None,   # str  path
        "video":     None,   # str  path
    },
    "scores": {
        "identity":         None,  # float | None
        "look":             None,
        "scene":            None,
        "framing":          None,
        "pose":             None,
        "body_integrity":   None,  # dance_segment only
        "pose_sequence":    None,  # dance_segment only
        "beat_offset_ms":   None,  # shot only
        "subject_count":    None,  # dict {expected, detected, pass}
    },
    "verdict":               None,   # str  "pass" | "fail" | "needs_human"
    "failed_metrics":        [],     # list[str]
    "diagnosis":             None,   # str
    "repair_action":         None,   # str
    "next_attempt":          None,   # int | None
    "improved_from_previous": None,  # bool | None
}


def make_log_entry(
    unit_id: str,
    unit_type: str,
    attempt_id: int,
    stage: str,
    backend: str,
    scores: dict,
    verdict: str,
    diagnosis: str = "",
    repair_action: str = "",
    inputs: dict = None,
    outputs: dict = None,
    improved: bool | None = None,
) -> dict:
    """Create a decision log entry with all required fields."""
    entry = deepcopy(DECISION_LOG_ENTRY_SCHEMA)
    entry["unit_id"]    = unit_id
    entry["unit_type"]  = unit_type
    entry["attempt_id"] = attempt_id
    entry["stage"]      = stage
    entry["backend"]    = backend
    entry["scores"].update(scores)
    entry["verdict"]    = verdict
    entry["failed_metrics"] = [k for k, v in scores.items()
                                if v is not None and isinstance(v, (int, float)) and v < 0.5]
    entry["diagnosis"]      = diagnosis
    entry["repair_action"]  = repair_action
    entry["improved_from_previous"] = improved
    if inputs:  entry["inputs"].update(inputs)
    if outputs: entry["outputs"].update(outputs)
    return entry


if __name__ == "__main__":
    import json
    u = make_unit("shot_001", "shot", 0.0, 2.1,
                  framing_target={"shot_size": "medium_close_up"})
    print(json.dumps(u, indent=2, default=str))
    print("\nValidation errors:", validate_unit(u))
