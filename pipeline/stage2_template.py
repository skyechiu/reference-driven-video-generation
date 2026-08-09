"""
stage2_template.py — Template Builder (Enriched Storyboard)

Converts reference analysis data into a beat-aligned, VLM-enriched storyboard JSON.

Core dissertation contribution:
  - Beat alignment: snaps shot cuts to nearest beat (with max-snap-distance guard)
  - Enriched schema: each shot is a production blueprint, not a caption
  - Tool-measured fields (timing, pose, framing) are ground truth
  - VLM-assisted fields (camera angle, lighting, environment, expression) are labelled
    with source="vlm_caption" so evaluation can treat them separately

Schema hierarchy per shot:
  timing → source → visual_structure → subject_action → description →
  generation_brief → evaluation_targets → risk_flags → readiness
"""

import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import BEAT_MAX_SNAP_DISTANCE_MS, OUTPUT_DIR
import state as st


ROOT = Path(__file__).parent.parent


# ─── View Label & Identity Eval Mode ─────────────────────────────────────────

VIEW_EVAL_MODE = {
    "front":          "face_embedding",
    "three-quarter":  "face_embedding_and_look",
    "side":           "face_embedding_and_look",
    "back":           "look_and_silhouette",
    "over-shoulder":  "look_and_silhouette",
    "unknown":        "face_embedding",
}


def _infer_view_label_from_kpts(kpts: Optional[dict]) -> str:
    """
    Heuristic view label from MediaPipe keypoints.
    Falls back to 'unknown' if keypoints are absent or ambiguous.
    """
    if not kpts:
        return "unknown"
    nose = kpts.get("NOSE", {})
    nose_vis = nose.get("visibility", 0.0)
    ls_vis = kpts.get("LEFT_SHOULDER",  {}).get("visibility", 0.0)
    rs_vis = kpts.get("RIGHT_SHOULDER", {}).get("visibility", 0.0)
    left_ear_vis  = kpts.get("LEFT_EAR",  {}).get("visibility", 0.0)
    right_ear_vis = kpts.get("RIGHT_EAR", {}).get("visibility", 0.0)

    if nose_vis >= 0.60:
        return "front"
    if nose_vis >= 0.30:
        # Asymmetric ear visibility → side
        ear_diff = abs(left_ear_vis - right_ear_vis)
        if ear_diff > 0.35:
            return "side"
        return "three-quarter"
    # Very low nose visibility
    if ls_vis > 0.4 and rs_vis > 0.4:
        return "back"
    return "over-shoulder"


def _get_view_label(vlm: dict, kpts: Optional[dict]) -> str:
    """Prefer VLM body_orientation mapping, fall back to keypoint heuristic."""
    orientation = vlm.get("body_orientation", "").lower()
    _map = {
        "front":          "front",
        "front-facing":   "front",
        "facing camera":  "front",
        "three-quarter":  "three-quarter",
        "3/4":            "three-quarter",
        "side":           "side",
        "profile":        "side",
        "side profile":   "side",
        "back":           "back",
        "back-facing":    "back",
        "away from camera": "back",
        "over-shoulder":  "over-shoulder",
    }
    for key, label in _map.items():
        if key in orientation:
            return label
    return _infer_view_label_from_kpts(kpts)


# ─── Beat Alignment ───────────────────────────────────────────────────────────

def snap_to_beat(cut_time_s: float, beats: list[dict], max_snap_ms: float) -> tuple[float, bool]:
    """
    Snap a cut time to the nearest beat.
    Returns (aligned_time_s, was_snapped).
    If nearest beat is further than max_snap_ms, returns original time unchanged.
    """
    if not beats:
        return cut_time_s, False
    nearest = min(beats, key=lambda b: abs(b["time_s"] - cut_time_s))
    dist_ms = abs(nearest["time_s"] - cut_time_s) * 1000
    if dist_ms <= max_snap_ms:
        return nearest["time_s"], True
    return cut_time_s, False


def get_nearest_beat(time_s: float, beats: list[dict]) -> Optional[dict]:
    if not beats:
        return None
    return min(beats, key=lambda b: abs(b["time_s"] - time_s))


# ─── VLM Enrichment ───────────────────────────────────────────────────────────

def _init_gpt_client():
    """Load OpenAI client from .env. Returns None if key unavailable."""
    try:
        from dotenv import load_dotenv
        import os, openai
        load_dotenv()
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            print("[template] OPENAI_API_KEY not set — VLM enrichment disabled")
            return None
        return openai.OpenAI(api_key=key)
    except Exception as e:
        print(f"[template] GPT client init failed: {e}")
        return None


VLM_PROMPT = """You are analysing a reference video frame for a controllable AI video generation pipeline.

Return structured shot metadata as JSON. Extract cinematographic information that can be used to regenerate this shot with a new character while preserving the same framing, lighting, environment and composition.

Return ONLY valid JSON — no markdown, no explanation:
{
  "camera_angle": one of "front" | "front_3_4" | "side" | "back" | "high_angle" | "low_angle" | "unknown",
  "camera_motion": one of "static" | "push_in" | "pull_out" | "pan" | "handheld" | "unknown",
  "lighting_type": string (e.g. "soft daylight", "backlight", "window light", "low-key", "studio", "mixed"),
  "lighting_direction": one of "front" | "front_left" | "front_right" | "back" | "side" | "overhead" | "unknown",
  "environment_type": string (e.g. "greenhouse", "street", "studio", "runway", "dressing_room", "interior"),
  "background_elements": [string, ...],
  "body_orientation": one of "front-facing" | "side-facing" | "back-facing" | "angled",
  "action_summary": string (one short phrase, max 8 words, e.g. "slow walk forward through space"),
  "expression": one of "neutral" | "composed" | "tense" | "soft" | "serious" | "looking_away" | "unknown",
  "gaze": one of "towards_camera" | "downward" | "upward" | "sideways" | "away" | "unknown",
  "motion_intensity": one of "none" | "low" | "medium" | "high",
  "prompt_fragment": string (20-35 words describing the cinematographic setup for use in a generation prompt),
  "confidence": float between 0.0 and 1.0,
  "vlm_risk_flags": [string, ...]
}"""


def enrich_shot_with_vlm(source_panel_path: str, client) -> dict:
    """
    Call GPT-4o with the source panel image to extract visual metadata.
    Returns dict with VLM-sourced fields, or empty dict on failure.
    All returned fields are labelled source='vlm_caption' by the caller.
    """
    if not client:
        return {}
    p = Path(source_panel_path)
    if not p.exists():
        print(f"    [vlm] panel not found: {source_panel_path}")
        return {"vlm_risk_flags": ["source_panel_missing_for_vlm"]}

    try:
        img_b64 = base64.b64encode(p.read_bytes()).decode()
        ext = p.suffix.lstrip(".").lower() or "png"
        mime = f"image/{ext}"

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    {"type": "text", "text": VLM_PROMPT},
                ],
            }],
            max_tokens=600,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    [vlm] JSON parse error: {e}")
        return {"vlm_risk_flags": ["vlm_json_parse_error"]}
    except Exception as e:
        print(f"    [vlm] enrichment failed: {e}")
        return {"vlm_risk_flags": ["vlm_enrichment_failed"]}


# ─── Framing / Pose Helpers ───────────────────────────────────────────────────

SHOT_SIZE_MAP = {
    "extreme-close-up": "extreme_close_up",
    "close-up": "close_up",
    "medium-close-up": "medium_close_up",
    "medium": "medium",
    "medium-wide": "medium_wide",
    "wide": "wide",
    "extreme-wide": "extreme_wide",
    "unknown": "unknown",
}

FACE_LANDMARKS = {"nose", "left_eye", "right_eye", "left_ear", "right_ear"}


def _extract_framing_detail(kpts: Optional[dict]) -> dict:
    """Compute face/body bbox ratios from MediaPipe keypoints."""
    if not kpts:
        return {}
    detail = {}
    visible = [(k, v) for k, v in kpts.items()
                if isinstance(v, dict) and v.get("visibility", 0) > 0.5]
    if visible:
        xs = [v["x"] for _, v in visible]
        ys = [v["y"] for _, v in visible]
        detail["person_center_x"] = round(sum(xs) / len(xs), 3)
        detail["person_center_y"] = round(sum(ys) / len(ys), 3)
        detail["person_height_ratio"] = round(max(ys) - min(ys), 3)

    face_vis = [(k, v) for k, v in kpts.items()
                if k in FACE_LANDMARKS and isinstance(v, dict) and v.get("visibility", 0) > 0.5]
    if face_vis:
        fxs = [v["x"] for _, v in face_vis]
        fys = [v["y"] for _, v in face_vis]
        detail["face_center_x"] = round(sum(fxs) / len(fxs), 3)
        detail["face_center_y"] = round(sum(fys) / len(fys), 3)
        detail["face_width_ratio"] = round(max(fxs) - min(fxs), 3) if len(fxs) > 1 else 0.0
    return detail


def _pose_confidence(kpts: Optional[dict]) -> float:
    if not kpts:
        return 0.0
    vis = [v.get("visibility", 0) for v in kpts.values() if isinstance(v, dict)]
    return round(sum(vis) / len(vis), 3) if vis else 0.0


# ─── Prompt Builder ───────────────────────────────────────────────────────────

def _build_keyframe_prompt(
    shot_size: str,
    vlm: dict,
    selected_look: dict,
    selected_scene: dict | None = None,
    subject_action: dict | None = None,
) -> str:
    """Build the keyframe (static image) generation prompt from all available context."""
    look_pp = selected_look.get("prompt_profile", {})
    look_label = selected_look.get("look_label", "the selected look")
    angle = vlm.get("camera_angle", "")
    fragment = vlm.get("prompt_fragment", "")

    # --- Reference structure ---
    frame_desc = f"{shot_size.replace('_', ' ')} framing"
    if angle and angle != "unknown":
        frame_desc += f", {angle.replace('_', ' ')} angle"
    parts = [
        "Redraw the source panel as the fixed IP character.",
        f"Preserve the {frame_desc}, pose, subject placement and composition from the reference.",
        "Replace the full person with the IP character.",
    ]

    # --- Subject / look ---
    if look_pp:
        look_parts = []
        if look_pp.get("outfit"):
            look_parts.append(f"Outfit: {look_pp['outfit']}.")
        if look_pp.get("hair"):
            look_parts.append(f"Hair: {look_pp['hair']}.")
        if look_pp.get("makeup"):
            look_parts.append(f"Makeup: {look_pp['makeup']}.")
        if look_pp.get("shoes"):
            look_parts.append(f"Shoes: {look_pp['shoes']}.")
        if look_parts:
            parts.append(" ".join(look_parts))

    # --- Scene ---
    if selected_scene and selected_scene.get("scene_id") and selected_scene.get("scene_id") != "preserve":
        spp = selected_scene.get("prompt_profile", {})
        location = spp.get("location", selected_scene.get("scene_name", ""))
        lighting = spp.get("lighting", "")
        bg_elements = spp.get("background_elements", [])
        if location:
            parts.append(f"Place the character in: {location}.")
        if lighting:
            parts.append(f"Lighting: {lighting}.")
        if bg_elements:
            parts.append(f"Background: {', '.join(bg_elements[:4])}.")
        parts.append(
            "Adapt the scene into a 9:16 vertical composition while preserving "
            "the lighting, material palette and key background elements."
        )
    else:
        parts.append("Adapt the environment into a 9:16 vertical composition.")

    # --- Action / mood ---
    if subject_action:
        action = subject_action.get("action") or vlm.get("action_summary", "")
        expr = subject_action.get("expression") or vlm.get("expression", "")
        if action:
            parts.append(f"The character {action}.")
        if expr and expr not in ("unknown", "neutral"):
            parts.append(f"Expression: {expr}.")
    if fragment:
        parts.append(fragment)

    # --- Single-character constraint ---
    parts.append(
        "Generate only one visible character in the frame. "
        "Do not add extra people, background figures, duplicated bodies or additional faces. "
        "Background people from the reference video must not be reproduced."
    )
    parts.append(
        "Output: 9:16 vertical keyframe, realistic cinematic fashion editorial. "
        "Maintain identity consistency with the IP reference images."
    )
    return " ".join(parts)


def _build_video_prompt(
    shot_size: str,
    vlm: dict,
    selected_look: dict,
    selected_scene: dict | None = None,
    subject_action: dict | None = None,
    duration_s: float = 2.5,
) -> str:
    """Build the Kling I2V video prompt for a shot."""
    motion = "low motion" if not subject_action else (
        subject_action.get("motion_intensity", "low") + " motion"
    )
    action = (subject_action or {}).get("action", "") or vlm.get("action_summary", "")
    camera_motion = vlm.get("camera_motion", "static")

    look_label = selected_look.get("look_label", "the character's look")
    look_pp = selected_look.get("prompt_profile", {})

    # Scene context for video
    scene_ctx = ""
    if selected_scene and selected_scene.get("prompt_profile", {}).get("lighting"):
        scene_ctx = selected_scene["prompt_profile"]["lighting"]

    parts = [
        f"A short cinematic {shot_size.replace('_', ' ')} vertical video shot, {duration_s:.1f} seconds.",
    ]
    if action:
        parts.append(f"The character {action} with natural {motion}.")
    else:
        parts.append(f"The character holds the pose with subtle breathing and {motion}.")

    camera_desc = {
        "static": "camera remains stable",
        "push_in": "slow editorial push-in",
        "pull_out": "slow pull-out",
        "pan_left": "slow pan left",
        "pan_right": "slow pan right",
        "orbit": "slow camera orbit around the subject",
    }.get(camera_motion, "camera remains stable with minimal movement")
    parts.append(f"The {camera_desc}.")

    # Identity and look preservation
    preserve_parts = ["same face", "same identity"]
    if look_pp.get("outfit"):
        preserve_parts.append("same outfit and hairstyle")
    if scene_ctx:
        preserve_parts.append(scene_ctx.split(",")[0].lower())
    parts.append(f"Preserve throughout: {', '.join(preserve_parts)}.")

    parts.append(
        "No identity change, no cuts, no transition effects, "
        "realistic fabric movement, natural hair physics."
    )
    parts.append(
        "Generate only one character throughout. No extra people, no background characters, "
        "no duplicated person."
    )
    return " ".join(parts)


def _build_negative_prompt(shot_size: str, risk_flags: list, view: str = "front") -> str:
    base = [
        "different face", "changed identity", "wrong outfit", "extra limbs",
        "unstable hands", "distorted proportions", "copied original background",
        "multiple people", "extra person", "second face", "background characters",
        "crowd", "duplicated body",
    ]
    if shot_size == "extreme_close_up":
        base.append("cropped head")
    if shot_size in ("wide", "extreme_wide"):
        base.append("face too small to identify")
    if view in ("back", "over-shoulder"):
        base.append("visible face when back is to camera")
    return ", ".join(base)


# ─── Risk Flag Detection ──────────────────────────────────────────────────────

def _compute_risk_flags(
    framing: str,
    beat_offset_ms: float,
    was_snapped: bool,
    pose_conf: float,
    kpts: Optional[dict],
    source_panel: str,
    vlm: dict,
) -> list[str]:
    flags = []
    if abs(beat_offset_ms) > 150:
        flags.append("beat_offset_too_large")
    if not was_snapped:
        flags.append("beat_not_snapped")
    if framing == "unknown":
        flags.append("unknown_framing")
    if pose_conf < 0.5:
        flags.append("low_pose_confidence")
    if not kpts:
        flags.append("no_pose_detected")
    if not source_panel or not Path(source_panel).exists():
        flags.append("source_panel_missing")
    ca = vlm.get("camera_angle", "")
    if not ca or ca == "unknown":
        flags.append("camera_angle_unknown")
    flags.extend(vlm.get("vlm_risk_flags", []))
    return list(dict.fromkeys(flags))  # deduplicate, preserve order


# ─── Main Shot Builder ────────────────────────────────────────────────────────

def build_structured_shot(
    raw: dict,
    aligned_time_s: float,
    was_snapped: bool,
    beats: list[dict],
    vlm: dict,
    s1_shots_by_id: dict,
    selected_look: dict,
    replace_scope: str = "full_subject",
    selected_scene: dict | None = None,
) -> dict:
    """
    Build a full production-blueprint shot dict from tool data + VLM enrichment.
    Tool-measured fields are ground truth. VLM fields carry source='vlm_caption'.
    """
    shot_index = raw["shot_index"]
    shot_id = f"shot_{shot_index + 1:03d}"  # 1-indexed to match stage1 filenames

    # ── Timing ────────────────────────────────────────────────────
    nearest_beat = get_nearest_beat(aligned_time_s, beats)
    nearest_beat_s = nearest_beat["time_s"] if nearest_beat else aligned_time_s
    beat_strength = nearest_beat.get("strength", 0.0) if nearest_beat else 0.0
    beat_offset_ms = round((raw["start_time_s"] - nearest_beat_s) * 1000, 1)
    snap_delta_ms = round((aligned_time_s - raw["start_time_s"]) * 1000, 1)
    snap_reason = "" if was_snapped else f"offset {abs(beat_offset_ms):.0f}ms exceeds {BEAT_MAX_SNAP_DISTANCE_MS}ms threshold"

    timing = {
        "original_start_s": raw["start_time_s"],
        "original_end_s": raw["end_time_s"],
        "duration_s": raw["duration_s"],
        "beat_snap_applied": was_snapped,
        "aligned_start_s": aligned_time_s,
        "snap_delta_ms": snap_delta_ms,
        "nearest_beat_s": nearest_beat_s,
        "beat_strength": round(beat_strength, 3),
        "beat_offset_ms": beat_offset_ms,
        "snap_reason": snap_reason,
        "source": "tool_beat_alignment",
    }

    # ── Source ─────────────────────────────────────────────────────
    # Stage1's build_storyboard() stores source_panel in state["storyboard"]["shots"]
    s1_shot = s1_shots_by_id.get(shot_id, {})
    source_panel = (s1_shot.get("source_panel")
                    or raw.get("source_panel", "")
                    or "")

    source = {
        "source_panel": source_panel,
        "keyframe_method": "best_frame_by_sharpness_and_subject_visibility",
        "pose_image": raw.get("pose_image", ""),
        "pose_ref": s1_shot.get("pose_ref", ""),
        "source": "tool_stage1_analysis",
    }

    # ── Visual Structure ───────────────────────────────────────────
    framing = raw.get("framing", "unknown")
    shot_size = SHOT_SIZE_MAP.get(framing, framing)
    kpts = raw.get("pose_keypoints")
    framing_detail = _extract_framing_detail(kpts)
    pose_conf = _pose_confidence(kpts)

    visual_structure = {
        "shot_size": shot_size,
        "shot_size_source": "tool_pose_classification",
        "camera_angle": vlm.get("camera_angle", "unknown"),
        "camera_angle_source": "vlm_caption" if vlm.get("camera_angle") else "not_available",
        "camera_motion": vlm.get("camera_motion", "unknown"),
        "lighting": {
            "type": vlm.get("lighting_type", "unknown"),
            "direction": vlm.get("lighting_direction", "unknown"),
            "source": "vlm_caption",
            "confidence": vlm.get("confidence", 0.0),
        },
        "environment": {
            "location_type": vlm.get("environment_type", "unknown"),
            "background_elements": vlm.get("background_elements", []),
            "source": "vlm_caption",
        },
        "framing_detail": framing_detail,
    }

    # ── Subject Action ─────────────────────────────────────────────
    motion_dirs = raw.get("motion_direction", [])
    motion_intensity = vlm.get("motion_intensity", "")
    if not motion_intensity or motion_intensity == "unknown":
        if not motion_dirs:
            motion_intensity = "none"
        elif len(motion_dirs) == 1:
            motion_intensity = "low"
        elif len(motion_dirs) <= 3:
            motion_intensity = "medium"
        else:
            motion_intensity = "high"

    view = _get_view_label(vlm, kpts)
    identity_eval_mode = VIEW_EVAL_MODE.get(view, "face_embedding")

    subject_action = {
        "body_orientation": vlm.get("body_orientation", "unknown"),
        "action": vlm.get("action_summary", ""),
        "expression": vlm.get("expression", "unknown") if view not in ("back", "over-shoulder") else "not visible",
        "gaze": vlm.get("gaze", "unknown") if view not in ("back", "over-shoulder") else "away from camera",
        "motion_intensity": motion_intensity,
        "motion_direction": motion_dirs,
        "pose_confidence": pose_conf,
        "view": view,
        "identity_eval_mode": identity_eval_mode,
        "source": "tool+vlm_caption" if vlm else "tool",
    }

    # ── Description (3 variants) ───────────────────────────────────
    creative = raw.get("description", "")
    short_d = vlm.get("action_summary", creative[:50] if creative else "")
    tech_d = (f"{shot_size.replace('_',' ')}, "
               f"{vlm.get('camera_angle','unknown').replace('_',' ')} angle, "
               f"{vlm.get('lighting_type','unknown')} lighting, "
               f"{motion_intensity} motion")
    description = {
        "short": short_d,
        "technical": tech_d,
        "creative": creative,
    }

    # ── Risk Flags ─────────────────────────────────────────────────
    risk_flags = _compute_risk_flags(framing, beat_offset_ms, was_snapped, pose_conf, kpts, source_panel, vlm)
    if view in ("back", "over-shoulder"):
        if "face_not_visible" not in risk_flags:
            risk_flags.append("face_not_visible")
        if "identity_score_not_applicable" not in risk_flags:
            risk_flags.append("identity_score_not_applicable")

    # ── Evaluation Targets ─────────────────────────────────────────
    evaluation_targets = {
        "identity_min": "calibrated" if identity_eval_mode == "face_embedding" else "n/a",
        "identity_eval_mode": identity_eval_mode,
        "look_consistency_min": 0.65 if identity_eval_mode == "look_and_silhouette" else 0.65,
        "framing_min": 0.75,
        "pose_min": 0.70,
        "beat_offset_ms_max": 150,
        "subject_count_expected": 1,
    }

    # ── Readiness ──────────────────────────────────────────────────
    panel_ready  = bool(source_panel) and Path(source_panel).exists()
    framing_ready = framing != "unknown"
    pose_ready   = pose_conf >= 0.5
    beat_ready   = abs(beat_offset_ms) <= 150
    review_reasons = [f for f in ("source_panel_missing" if not panel_ready else None,
                                   "unknown_framing" if not framing_ready else None,
                                   "low_pose_confidence" if not pose_ready else None,
                                   "beat_offset_too_large" if not beat_ready else None)
                       if f]

    readiness = {
        "source_panel_ready": panel_ready,
        "framing_ready": framing_ready,
        "pose_ready": pose_ready,
        "beat_ready": beat_ready,
        "requires_human_review": bool(review_reasons),
        "reason": review_reasons,
    }

    status = "blocked" if not panel_ready else ("review" if review_reasons else "ready")

    # ── Replacement Target ─────────────────────────────────────────
    _replace_map = {
        "full_subject": {
            "preserve": ["pose", "camera_framing", "shot_timing", "motion_rhythm", "background"],
            "replace": ["face", "hair", "outfit", "shoes", "body_appearance", "accessories"],
        },
        "head_and_hair": {
            "preserve": ["pose", "camera_framing", "shot_timing", "motion_rhythm", "background", "outfit", "body_appearance"],
            "replace": ["face", "hair"],
        },
        "face_only": {
            "preserve": ["pose", "camera_framing", "shot_timing", "motion_rhythm", "background", "outfit", "hair", "body_appearance"],
            "replace": ["face"],
        },
        "full_subject_restyle_bg": {
            "preserve": ["pose", "camera_framing", "shot_timing", "motion_rhythm"],
            "replace": ["face", "hair", "outfit", "shoes", "body_appearance", "accessories", "background"],
        },
    }
    scope_config = _replace_map.get(replace_scope, _replace_map["full_subject"])
    look_pp = selected_look.get("prompt_profile", {})

    replacement_target = {
        "identity_id": "ip_character",
        "look_id": selected_look.get("look_id", ""),
        "replace_scope": replace_scope,
        "preserve": scope_config["preserve"],
        "replace": scope_config["replace"],
        "prompt_profile": {
            "hair": look_pp.get("hair", ""),
            "makeup": look_pp.get("makeup", ""),
            "outfit": look_pp.get("outfit", ""),
            "shoes": look_pp.get("shoes", ""),
            "body_silhouette": look_pp.get("body_silhouette", ""),
            "jewellery": look_pp.get("jewellery", ""),
            "palette": look_pp.get("palette", ""),
            "texture": look_pp.get("texture", ""),
        },
    }

    # ── Scene Target ───────────────────────────────────────────────
    scene_target = None
    if selected_scene and selected_scene.get("scene_id"):
        spp = selected_scene.get("prompt_profile", {})
        scene_target = {
            "scene_id": selected_scene["scene_id"],
            "scene_name": selected_scene.get("scene_name", ""),
            "scene_mode": "replace_reference_scene",
            "location": spp.get("location", ""),
            "lighting": spp.get("lighting", ""),
            "background_elements": spp.get("background_elements", []),
            "floor": spp.get("floor", ""),
            "palette": spp.get("palette", ""),
            "mood": spp.get("mood", ""),
            "adaptation": "vertical_recompose",
            "adaptation_note": spp.get("adaptation_note", "Adapt into 9:16 vertical frame while preserving lighting, materials and background elements."),
            "shot_refs": _select_scene_refs(selected_scene, framing, vlm.get("camera_angle", "")),
        }

    # ── Upgrade generation_brief with full prompts ─────────────────
    keyframe_prompt = _build_keyframe_prompt(
        shot_size, vlm, selected_look,
        selected_scene=selected_scene,
        subject_action=subject_action,
    )
    video_prompt = _build_video_prompt(
        shot_size, vlm, selected_look,
        selected_scene=selected_scene,
        subject_action=subject_action,
        duration_s=raw.get("duration_s", 2.5),
    )
    negative_prompt = _build_negative_prompt(shot_size, risk_flags, view=view)

    look_refs = []
    for role in ["face_closeup", "front_full_body", "overview"]:
        for ref in selected_look.get("references", []):
            if ref.get("role") == role and ref.get("filename"):
                look_refs.append(ref["filename"])
                break

    generation_brief = {
        "keyframe_prompt": keyframe_prompt,
        "video_prompt": video_prompt,
        "negative_prompt": negative_prompt,
        "priority": ["identity", "look_consistency", "scene_consistency", "framing"],
        "look_refs_to_use": look_refs[:3],
        "scene_refs_to_use": (scene_target or {}).get("shot_refs", []),
        "vlm_prompt_fragment": vlm.get("prompt_fragment", ""),
    }

    # ── Primary Subject & Character Constraints ─────────────────────
    primary_subject = {
        "track_id": "person_01",
        "selection_rule": "largest_central_person",
        "background_people_policy": "ignore",
        "locked": True,
        "note": "Single-primary-subject pipeline. Background people in reference are not tracked or reproduced.",
    }

    generation_constraints = {
        "single_character_only": True,
        "no_extra_people": True,
        "do_not_reproduce_background_characters": True,
        "background_people_policy": "ignore",
        "subject_count_expected": 1,
    }

    # ── Assemble ───────────────────────────────────────────────────
    # Carry unit_type from stage1 storyboard (shot / key_moment_clip / dance_segment)
    unit_type = raw.get("unit_type", "shot")

    shot = {
        "shot_id": shot_id,
        "unit_id": raw.get("unit_id", shot_id),
        "unit_type": unit_type,
        "status": status,
        "timing": timing,
        "source": source,
        "visual_structure": visual_structure,
        "subject_action": subject_action,
        "description": description,
        "generation_brief": generation_brief,
        "evaluation_targets": evaluation_targets,
        "replacement_target": replacement_target,
        "primary_subject": primary_subject,
        "generation_constraints": generation_constraints,
        "risk_flags": risk_flags,
        "readiness": readiness,
        # ── Pipeline-compat flat fields (used by stage3/4) ──────
        "beat_time_s": aligned_time_s,
        "duration_s": raw["duration_s"],
        "framing": framing,
        "source_panel": source_panel,
        "pose_keypoints": kpts,
        "pose_image_path": raw.get("pose_image"),
        "generated_image": None,
        "video_clip": None,
        "evaluation": {"status": "pending", "attempts": []},
    }
    if scene_target:
        shot["scene_target"] = scene_target
    return shot


# ─── Look Resolver ────────────────────────────────────────────────────────────

def _get_selected_look(state: dict) -> dict:
    """Read selected look config from state, load look_package.json if possible."""
    config = state.get("config", {})
    look_id = config.get("selected_look_id", "")
    look_label = config.get("selected_look_label", "the selected look")
    references = []
    prompt_profile = {}

    if look_id:
        for looks_root in [ROOT / "assets" / "looks", ROOT / "uploads" / "looks"]:
            if not looks_root.exists():
                continue
            for look_dir in looks_root.iterdir():
                pkg_path = look_dir / "look_package.json"
                if not pkg_path.exists():
                    continue
                try:
                    pkg = json.loads(pkg_path.read_text())
                    if pkg.get("look_id") == look_id:
                        references = pkg.get("references", [])
                        prompt_profile = pkg.get("prompt_profile", {})
                        look_label = f"Look {pkg.get('look_number','?')} — {pkg.get('look_name','')}"
                        break
                except Exception:
                    pass

    return {"look_id": look_id, "look_label": look_label,
            "references": references, "prompt_profile": prompt_profile}


def _get_selected_scene(state: dict) -> dict | None:
    """Read selected scene from state and load scene_package.json if available."""
    sel = state.get("selected_scene", {})
    if not sel or not sel.get("scene_id"):
        return None

    scene_id = sel["scene_id"]
    pkg_path = sel.get("package_path", f"assets/scenes/built_in/{scene_id}/scene_package.json")

    # Try loading the package JSON
    for base in [ROOT, ROOT / "assets" / "scenes" / "built_in" / scene_id]:
        candidate = ROOT / pkg_path if not (ROOT / pkg_path).is_absolute() else Path(pkg_path)
        if candidate.exists():
            try:
                pkg = json.loads(candidate.read_text())
                return {
                    "scene_id": scene_id,
                    "scene_name": pkg.get("scene_name", sel.get("scene_name", "")),
                    "references": pkg.get("references", []),
                    "prompt_profile": pkg.get("prompt_profile", {}),
                    "shot_type_map": pkg.get("shot_type_map", {}),
                }
            except Exception:
                break

    # Fallback — return just what's in state
    return {"scene_id": scene_id, "scene_name": sel.get("scene_name", ""),
            "references": [], "prompt_profile": {}, "shot_type_map": {}}


def _select_scene_refs(selected_scene: dict, framing: str, camera_angle: str) -> list[str]:
    """Pick the most relevant scene reference filenames for a given shot type."""
    if not selected_scene:
        return []
    shot_type_map = selected_scene.get("shot_type_map", {})
    refs = selected_scene.get("references", [])
    ref_by_role = {r["role"]: r["filename"] for r in refs if "role" in r and "filename" in r}

    # Determine shot bucket
    bucket = framing
    if camera_angle in ("side", "profile"):
        bucket = "side_profile"
    elif camera_angle in ("back", "rear"):
        bucket = "back_view"

    selected_roles = shot_type_map.get(bucket) or shot_type_map.get("close_up") or list(ref_by_role.keys())[:2]
    # Always include vertical_preview if available
    if "vertical_preview" in ref_by_role and "vertical_preview" not in selected_roles:
        selected_roles.append("vertical_preview")

    return [ref_by_role[r] for r in selected_roles if r in ref_by_role]


# ─── Main Entry ───────────────────────────────────────────────────────────────

def run(state: dict, scene_prompt: str | None = None) -> dict:
    """
    Build beat-aligned, VLM-enriched storyboard from reference analysis data.
    Updates state["shots"] and state["storyboard"].
    """
    ref = state.get("reference_data", {})
    shots_raw = ref.get("shot_cuts", [])
    beats = ref.get("beats", [])
    scene_prompt = scene_prompt or state.get("scene_prompt", "")
    selected_look = _get_selected_look(state)
    selected_scene = _get_selected_scene(state)

    # Index stage1 storyboard shots for source_panel lookup
    s1_storyboard_shots = state.get("storyboard", {}).get("shots", [])
    s1_shots_by_id = {s["shot_id"]: s for s in s1_storyboard_shots if "shot_id" in s}

    # GPT-4o client for VLM enrichment (disabled if no API key)
    gpt_client = _init_gpt_client()

    scene_label = selected_scene["scene_name"] if selected_scene else "none"
    print(f"[template] {len(shots_raw)} shots · {len(beats)} beats · BPM={ref.get('bpm',0):.1f} · "
          f"look={selected_look['look_label']} · scene={scene_label} · vlm={'on' if gpt_client else 'off'}")

    # Replacement scope from state config
    replace_scope = state.get("config", {}).get("replace_scope", "full_subject")
    print(f"[template] replace_scope={replace_scope} · scene={scene_label}")

    storyboard_shots = []
    total_snapped = 0

    for raw in shots_raw:
        shot_index = raw["shot_index"]
        shot_id = f"shot_{shot_index + 1:03d}"

        # Beat alignment
        aligned_s, was_snapped = snap_to_beat(raw["start_time_s"], beats, BEAT_MAX_SNAP_DISTANCE_MS)
        if was_snapped:
            total_snapped += 1

        # Source panel path (for VLM + source field)
        s1_shot = s1_shots_by_id.get(shot_id, {})
        source_panel = s1_shot.get("source_panel", "") or raw.get("source_panel", "")

        # VLM enrichment
        vlm = {}
        if gpt_client and source_panel:
            print(f"  [vlm] {shot_id} ...")
            vlm = enrich_shot_with_vlm(source_panel, gpt_client)

        # Build full structured shot
        shot = build_structured_shot(
            raw=raw,
            aligned_time_s=aligned_s,
            was_snapped=was_snapped,
            beats=beats,
            vlm=vlm,
            s1_shots_by_id=s1_shots_by_id,
            selected_look=selected_look,
            replace_scope=replace_scope,
            selected_scene=selected_scene,
        )
        storyboard_shots.append(shot)

        snap_tag = "✓ snap" if was_snapped else "  keep"
        print(f"  {shot_id}  {raw['start_time_s']:.2f}→{raw['end_time_s']:.2f}s  "
              f"{snap_tag}  framing={raw.get('framing','?'):15s}  status={shot['status']}")

    # Update pipeline state
    state["shots"] = storyboard_shots
    state["run_stats"]["total_shots"] = len(storyboard_shots)

    # Build storyboard document with metadata header
    video_path = (state.get("config", {}).get("reference_video")
                  or state.get("reference_video", ""))

    # Pull reference_type from state (set by stage1 router)
    reference_type = state.get("reference_type", "multi_shot")
    reference_type_source = state.get("reference_type_source", "auto_detected")
    _strategy_to_label = {
        "shot_storyboard":          "Reference Strategy A — Multi-shot Storyboard",
        "single_take_key_moments":  "Reference Strategy B — Single-take Key Moments",
        "key_pose_sequence":        "Reference Strategy C — Driving Performance",
    }
    analysis_strategy = ref.get("recommended_strategy", "shot_storyboard")

    storyboard_doc = {
        "storyboard_id": f"mode_a_{Path(video_path).stem}_storyboard" if video_path else "mode_a_storyboard",
        "schema_version": "0.3",
        "generated_at": datetime.now().isoformat(),
        "input_mode": "reference_video",
        "reference_type": reference_type,
        "reference_type_source": reference_type_source,
        "reference_strategy_label": _strategy_to_label.get(analysis_strategy, analysis_strategy),
        "strategy": analysis_strategy,
        "scene_prompt": scene_prompt,
        "character_mode": "single_primary_subject",
        "supported_subject_count": 1,
        "multi_subject_policy": "select_primary_subject_only",
        "format": {
            "scene_reference_aspect": "16:9",
            "target_video_aspect": "9:16",
            "adaptation_strategy": "vertical_recompose_per_shot",
        },
        "note": (
            "Tool-measured fields (timing, framing, pose) are ground truth used for evaluation. "
            "VLM-assisted fields (camera_angle, lighting, environment, expression) carry "
            "source='vlm_caption' and are used for prompt building and human review."
        ),
        "source_video": {
            "path": video_path,
            "duration_s": ref.get("duration_s"),
            "fps": ref.get("fps"),
            "bpm": ref.get("bpm"),
            "beats_detected": len(beats),
            "audio_policy": "beat_analysis_only — reference audio never appears in output",
        },
        "selected_identity": {
            "identity_id": state.get("config", {}).get("identity_id", "ip_01_four_selves"),
            "locked": True,
        },
        "selected_look": {
            "look_id": selected_look.get("look_id", ""),
            "look_label": selected_look.get("look_label", ""),
        },
        "alignment_stats": {
            "total_shots": len(storyboard_shots),
            "snapped_to_beat": total_snapped,
            "kept_original": len(storyboard_shots) - total_snapped,
            "snap_threshold_ms": BEAT_MAX_SNAP_DISTANCE_MS,
        },
        "shots": storyboard_shots,
    }

    state["storyboard"] = storyboard_doc

    # Export storyboard JSON
    out_path = OUTPUT_DIR / "storyboard.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(storyboard_doc, indent=2))
    print(f"[template] storyboard exported → {out_path}")
    print(f"[template] {total_snapped}/{len(shots_raw)} shots snapped to beats")

    st.set_stage(state, "templated")
    return state


# ─── Hand-authored Fallback ───────────────────────────────────────────────────

def load_manual_storyboard(json_path: str, state: dict) -> dict:
    """
    Fallback: load a hand-authored storyboard JSON.
    Keeps the dissertation valid even without a reference video.
    """
    with open(json_path) as f:
        data = json.load(f)

    shots = []
    for raw in data.get("shots", []):
        shot = st.make_shot(
            shot_id=raw["shot_id"],
            beat_time_s=raw.get("beat_time_s", 0.0),
            duration_s=raw.get("duration_s", 3.0),
            framing=raw.get("framing", "medium"),
            description=raw.get("description", ""),
            pose_keypoints=raw.get("pose_keypoints"),
            pose_image_path=raw.get("pose_image_path"),
        )
        shots.append(shot)

    state["shots"] = shots
    state["scene_prompt"] = data.get("scene_prompt", state.get("scene_prompt", ""))
    state["run_stats"]["total_shots"] = len(shots)
    st.set_stage(state, "templated")
    print(f"[template] loaded {len(shots)} manual shots from {json_path}")
    return state


if __name__ == "__main__":
    import sys
    s = st.load()
    if len(sys.argv) > 1 and sys.argv[1].endswith(".json"):
        load_manual_storyboard(sys.argv[1], s)
    else:
        scene = sys.argv[1] if len(sys.argv) > 1 else s.get("scene_prompt", "")
        run(s, scene)
    st.save(s)
