"""
mode_a_policy_service.py — shared Mode A policy application (integration seam).

Composes the ``pipeline.policies`` layer into the actual per-shot decision the
Mode A pipeline should make:

    shot metadata
      -> classify shot type
      -> select identity anchor
      -> build reference order
      -> apply quality policy
      -> emit a `reference_policy` block written back onto the shot

This is what turns the four policy modules from "importable" into "applied".
It runs NO generation, calls NO API and spends nothing — it only annotates
state so the UI can show what the pipeline WILL do per shot, and so the
decision log carries the policy provenance. Having the generator actually
*consume* build_reference_order() when it builds the images.edit call is the
final wiring step and is left to the generator on purpose (kept out of here so
this service never triggers paid work).
"""

from __future__ import annotations

from policies import reference_policy as rp
from policies import motion_policy as mp


# ── Shot-type classification from TOOL-MEASURED structure (ground truth) ──────
# Deliberately does NOT read the keyframe prompt: outfit/scene words there
# (e.g. "black oxfords", "cobblestone") falsely signal body parts. We classify
# from deterministic pose/framing fields and expose the evidence + a confidence
# so the UI can show tool-vs-manual provenance and the user can override.

def classify_shot_type(shot: dict) -> tuple[str, str, str]:
    """Return (shot_type, evidence, confidence). Honours an explicit
    shot['shot_type'] (e.g. a manual override) first. Pure."""
    explicit = shot.get("shot_type")
    if explicit in rp.SHOT_TYPES and shot.get("shot_type_source") == "manual_override":
        return explicit, "manual override", "high"

    vs = shot.get("visual_structure", {}) or {}
    sa = shot.get("subject_action", {}) or {}
    size   = str(vs.get("shot_size", "")).lower()
    view   = str(sa.get("view", "")).lower()
    orient = str(sa.get("body_orientation", "")).lower()
    mdir   = str(sa.get("motion_direction", "")).lower()
    conf   = sa.get("pose_confidence", None)
    has_pose = bool(shot.get("pose_keypoints"))

    # 1) no body detected -> feet / lower-body insert (MediaPipe found 0 points)
    if (conf in (0, 0.0)) and not has_pose:
        return rp.ShotType.LOWER_BODY, "no body keypoints (pose_confidence 0)", "high"

    away    = any(w in mdir or w in orient for w in ("away", "behind", "back"))
    profile = any(w in view or w in orient for w in ("profile", "side", "3/4", "three-quarter", "3\u30444"))

    # 2) medium / close framing with a body -> face is the subject
    if size in ("medium", "close", "close_up", "closeup"):
        return rp.ShotType.FACE_VISIBLE, f"shot_size={size} (face-primary)", "high" if has_pose else "medium"

    # 3) wide / full-body
    if size in ("wide", "full", "full_body", "long"):
        if away:
            return rp.ShotType.BACK_VIEW, f"wide + motion '{mdir or orient}' (away)", "medium"
        if profile:
            return rp.ShotType.SIDE_PROFILE, f"wide + view '{view or orient}'", "medium"
        return rp.ShotType.GENERIC, f"wide full-body, orientation unclear (view={view or 'unknown'})", "low"

    # 4) size unknown -> lean on orientation only
    if profile:
        return rp.ShotType.SIDE_PROFILE, "profile cue, shot_size unknown", "low"
    if away:
        return rp.ShotType.BACK_VIEW, "away cue, shot_size unknown", "low"
    return rp.ShotType.GENERIC, f"insufficient tool signal (shot_size={size or 'unknown'})", "low"


def _sources_for(shot: dict, state: dict) -> tuple[dict, bool]:
    """Best-effort map of RefRole -> availability, plus pose_skeleton flag.
    Availability is inferred from the brief; we care about presence, not paths."""
    gb = shot.get("generation_brief", {}) or {}
    cfg = (state or {}).get("config", {}) or {}
    look_refs = gb.get("look_refs_to_use") or []
    scene_refs = gb.get("scene_refs_to_use") or []
    # identity anchors: assume the run's two-anchor set exists unless told otherwise
    have_anchors = bool(cfg.get("identity_anchors_ready", True))
    sources = {
        rp.RefRole.IDENTITY_FRONT:   "anchor_front"   if have_anchors else None,
        rp.RefRole.IDENTITY_PROFILE: "anchor_profile" if have_anchors else None,
        rp.RefRole.OUTFIT:           "look_front"      if look_refs else None,
        rp.RefRole.SHEET:            "look_sheet"      if look_refs else None,
        rp.RefRole.SCENE:            "scene_ref"       if scene_refs else None,
        rp.RefRole.HAIR:             "anchor_profile"  if have_anchors else None,
    }
    return sources, have_anchors


def annotate_shot(shot: dict, state: dict | None = None) -> dict:
    """Compute the reference_policy block for one shot (pure — returns the block,
    does not mutate)."""
    state = state or {}
    shot_type, evidence, confidence = classify_shot_type(shot)
    sources, have_anchors = _sources_for(shot, state)

    # pose-driven shots expect a soft skeleton slot; mark it available for the
    # full-body pose-driven types (matches the graded-conditioning design).
    pose_skeleton = shot_type in (rp.ShotType.SIDE_PROFILE, rp.ShotType.BACK_VIEW)
    if pose_skeleton:
        sources[rp.RefRole.SKELETON] = "clean_skeleton"

    anchor_path, anchor_note = rp.select_identity_anchor(shot_type, {
        rp.RefRole.IDENTITY_FRONT: sources.get(rp.RefRole.IDENTITY_FRONT),
        rp.RefRole.IDENTITY_PROFILE: sources.get(rp.RefRole.IDENTITY_PROFILE),
    })
    identity_anchor = "profile" if shot_type == rp.ShotType.SIDE_PROFILE else "front"
    if anchor_path is None:
        identity_anchor = "none"

    slots = rp.build_reference_order(shot_type, sources, pose_skeleton_available=pose_skeleton)
    q = rp.quality_policy(shot_type)
    fallback_used = any(s.note.startswith("fallback") or s.source is None for s in slots)

    return {
        "shot_type": shot_type,
        "reference_policy": {
            "identity_anchor": identity_anchor,
            "slot_order": [s.role for s in slots],
            "slot_sources": [s.source for s in slots],
            "quality": q.quality,
            "input_fidelity": q.input_fidelity,
            "fallback_used": fallback_used,
            "pose_skeleton_slot": pose_skeleton,
            "classified_by": evidence,
            "classification_confidence": confidence,
            "identity_note": anchor_note,
        },
        "motion_policy": {
            "damping_words_removed": sorted(
                w for w in mp.DAMPING_WORDS
                if w in (shot.get("generation_brief", {}) or {}).get("video_prompt", "").lower()
            ),
        },
    }


def annotate_state(state: dict) -> dict:
    """Apply policies to every shot in `state`, writing `shot_type`,
    `reference_policy` and `motion_policy` onto each shot IN PLACE. Returns a
    summary. No generation, no API."""
    shots = state.get("shots", []) or []
    summary = []
    for sh in shots:
        block = annotate_shot(sh, state)
        sh["shot_type"] = block["shot_type"]
        sh["reference_policy"] = block["reference_policy"]
        sh["motion_policy"] = block["motion_policy"]
        summary.append({
            "shot_id": sh.get("shot_id"),
            "shot_type": block["shot_type"],
            "identity_anchor": block["reference_policy"]["identity_anchor"],
            "slot_order": block["reference_policy"]["slot_order"],
            "quality": block["reference_policy"]["quality"],
            "input_fidelity": block["reference_policy"]["input_fidelity"],
            "fallback_used": block["reference_policy"]["fallback_used"],
            "classified_by": block["reference_policy"]["classified_by"],
            "classification_confidence": block["reference_policy"]["classification_confidence"],
        })
    state.setdefault("policy_layer", {})["applied"] = True
    return {"ok": True, "n_shots": len(shots), "shots": summary}


__all__ = ["classify_shot_type", "annotate_shot", "annotate_state"]
