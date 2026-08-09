"""
motion_policy.py — Mode A motion-prompt policy layer.

Reusable, side-effect-free policy for writing and repairing Kling I2V video
prompts so that intended motion actually renders. Extracted from the street-run
motion repair, where damping language ("subtle", "slight", ...) had suppressed
motion to near-static clips; removing it and naming observable cues raised the
optical-flow motion energy of shot_001 (14% -> 51%) and shot_003 (19% -> 47%).

Prompt-level I2V does NOT guarantee exact motion transfer (see
backend_limits.py). These policies bias the model toward *more visible* motion;
they do not copy the reference trajectory frame-for-frame.

Importing this module has no side effects and calls no API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Damping words: suppress motion; strip from any video (I2V) prompt ─────────
# These read as "please barely move", which Kling honours literally.
DAMPING_WORDS = frozenset({
    "subtle", "subtly", "slight", "slightly", "minimal", "minimally",
    "unhurried", "mostly static", "static", "gentle", "gently", "light",
    "lightly", "soft", "softly", "barely", "faint", "faintly", "delicate",
    "delicately", "understated", "restrained", "still", "motionless",
    "nearly still", "almost still", "very slow", "imperceptible",
})


@dataclass(frozen=True)
class MotionCue:
    key: str
    label: str
    describes: str      # what to write into the prompt to make it observable
    applies_to: tuple   # shot types (from reference_policy.ShotType) where it reads


# ── Observable motion cues: name these instead of adjectives of degree ────────
# The fix is to describe *what visibly changes on screen*, not how "much".
MOTION_CUES = (
    MotionCue("head_turn_speed",  "Head-turn speed",
              "head rotates decisively from turned-away to facing camera",
              ("face_visible", "side_profile", "generic")),
    MotionCue("stride_visibility", "Stride visibility",
              "clear full stride — legs visibly alternate, knees lift",
              ("back_view", "side_profile", "generic")),
    MotionCue("weight_shift", "Weight shift",
              "body weight shifts from one leg to the other between steps",
              ("back_view", "side_profile", "lower_body", "generic")),
    MotionCue("arm_swing", "Arm swing",
              "arms swing naturally in opposition to the legs",
              ("back_view", "side_profile", "generic")),
    MotionCue("footstep_rhythm", "Footstep rhythm",
              "feet land in an even, visible walking rhythm",
              ("lower_body", "back_view", "side_profile")),
    MotionCue("body_displacement", "Body displacement",
              "subject visibly travels across / into the frame, not walking in place",
              ("back_view", "side_profile", "generic")),
    MotionCue("camera_parallax", "Camera parallax",
              "slight camera move so background parallax confirms real depth/motion",
              ("face_visible", "back_view", "side_profile", "generic")),
)

MOTION_CUES_BY_KEY = {c.key: c for c in MOTION_CUES}


# ── Appearance vs motion vocabulary ──────────────────────────────────────────
# Identity / outfit / scene words describe *appearance* and belong in the
# keyframe prompt. The video prompt should carry *motion* words only. Mixing
# heavy appearance description into the I2V prompt dilutes the motion signal.
APPEARANCE_WORDS = frozenset({
    "hair", "face", "eyes", "skin", "blazer", "shirt", "tie", "denim", "jeans",
    "oxfords", "outfit", "charcoal", "olive", "cobblestone", "limestone",
    "facade", "street", "lamp", "daylight", "identity", "look", "wearing",
    "tailored", "colour", "color", "makeup", "profile", "portrait",
})
MOTION_WORDS = frozenset({
    "walk", "walking", "step", "steps", "stride", "turn", "turns", "turning",
    "swing", "swings", "shift", "shifts", "move", "moves", "moving", "rotate",
    "rotates", "lift", "lifts", "travel", "travels", "gait", "pace", "rhythm",
    "gesture", "raises", "raise", "advance", "advancing", "forward",
})


def _tokens(text: str) -> list[str]:
    return [t.strip(".,;:!?()[]").lower() for t in text.split()]


def strip_damping(prompt: str) -> str:
    """Remove damping words / phrases from a video prompt.

    Handles both multi-word phrases ("mostly static") and single adjectives.
    Pure string transform.
    """
    out = prompt
    # phrases first (longest match)
    for phrase in sorted((w for w in DAMPING_WORDS if " " in w), key=len, reverse=True):
        out = out.replace(phrase, "").replace(phrase.capitalize(), "")
    kept = []
    for tok in out.split():
        bare = tok.strip(".,;:!?()[]").lower()
        if bare in DAMPING_WORDS:
            continue
        kept.append(tok)
    # tidy double spaces / stray punctuation spacing
    return " ".join(" ".join(kept).replace(" ,", ",").replace(" .", ".").split())


def separate_appearance_from_motion(prompt: str) -> dict:
    """Split a prompt's tokens into appearance vs motion vs neutral buckets.

    Returns ``{"appearance": [...], "motion": [...], "neutral": [...]}``.
    Use this to check that a *video* prompt is motion-dominant and to move
    appearance description back to the keyframe prompt.
    """
    buckets = {"appearance": [], "motion": [], "neutral": []}
    for tok in _tokens(prompt):
        if not tok:
            continue
        if tok in APPEARANCE_WORDS:
            buckets["appearance"].append(tok)
        elif tok in MOTION_WORDS:
            buckets["motion"].append(tok)
        else:
            buckets["neutral"].append(tok)
    return buckets


def repair_motion_prompt(
    prompt: str,
    shot_type: str = "generic",
    emphasize: Optional[list] = None,
) -> str:
    """Return a repaired video prompt with more visible motion.

    Steps:
      1. Strip damping words.
      2. Append the observable motion cues relevant to ``shot_type`` (or the
         explicit ``emphasize`` list of cue keys) as concrete phrases.

    This is a prompt-level nudge only — it biases toward *more* motion, not
    exact reference-motion reproduction (see backend_limits.py). Pure function.
    """
    base = strip_damping(prompt).rstrip(" .")
    if emphasize:
        cues = [MOTION_CUES_BY_KEY[k] for k in emphasize if k in MOTION_CUES_BY_KEY]
    else:
        cues = [c for c in MOTION_CUES if shot_type in c.applies_to]
    phrases = "; ".join(c.describes for c in cues)
    if phrases:
        return f"{base}. {phrases}. Full, clearly visible motion throughout."
    return f"{base}. Full, clearly visible motion throughout."


__all__ = [
    "DAMPING_WORDS", "MotionCue", "MOTION_CUES", "MOTION_CUES_BY_KEY",
    "APPEARANCE_WORDS", "MOTION_WORDS",
    "strip_damping", "separate_appearance_from_motion", "repair_motion_prompt",
]
