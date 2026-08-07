"""
backend_limits.py — honest capability limits of the current Mode A backends.

Reusable, side-effect-free record of what the CURRENT API-based backends can
and cannot do. Its job is to stop the UI, prompts, and dissertation wording
from claiming capabilities the backend does not have (e.g. exact pose transfer).

Extracted while repairing the street run. No API, no I/O on import.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BackendCapability:
    backend: str
    role: str
    can: tuple = field(default_factory=tuple)
    cannot: tuple = field(default_factory=tuple)
    notes: str = ""


# ── Current backends (what actually produced the completed runs) ─────────────
CURRENT_BACKENDS = (
    BackendCapability(
        backend="gpt-image-1",
        role="keyframe generation (images.edit)",
        can=(
            "condition on reference images in weighted slots (earlier = stronger)",
            "hold identity/outfit reasonably via input_fidelity=high anchors",
            "respect framing/composition described in text",
        ),
        cannot=(
            "accept a hard ControlNet-style pose interface",
            "guarantee an exact skeleton/keypoint is followed",
        ),
        notes=(
            "There is NO hard pose interface. A clean skeleton image passed as a "
            "reference slot is WEAK guidance only — orientation is really driven by "
            "the text prompt, so the prompt must state the orientation explicitly."
        ),
    ),
    BackendCapability(
        backend="kling-v1-6 (I2V, std)",
        role="image-to-video animation",
        can=(
            "animate a keyframe with prompt-described motion",
            "produce plausible walk / turn / gesture motion",
        ),
        cannot=(
            "guarantee exact frame-level motion transfer from a reference",
            "copy a reference gait/trajectory precisely",
        ),
        notes=(
            "Prompt-level I2V. Motion is biased by the prompt, not transferred. "
            "Damping words suppress motion (see motion_policy.DAMPING_WORDS)."
        ),
    ),
)

# Quick booleans for guard code / UI labels.
SKELETON_IS_WEAK_GUIDANCE_ONLY = True
GPT_IMAGE_1_HAS_HARD_POSE_INTERFACE = False
KLING_GUARANTEES_EXACT_MOTION_TRANSFER = False


# ── Future backends (explicitly NOT part of the current main implementation) ──
@dataclass(frozen=True)
class FutureBackend:
    name: str
    would_add: str


FUTURE_BACKENDS = (
    FutureBackend("LoRA",       "fine-tuned identity — stronger than reference-slot conditioning"),
    FutureBackend("IPAdapter / IPAdapter-FaceID", "stronger image-prompt identity injection"),
    FutureBackend("InstantID",  "single-reference identity-preserving generation"),
    FutureBackend("ControlNet", "a true hard pose/edge interface for exact pose control"),
)


def supports_hard_pose_control(backend: str) -> bool:
    """No current backend offers hard pose control; ControlNet (future) would."""
    return False


def describe_limits() -> str:
    """Human-readable summary for logs / dissertation scope notes. Pure."""
    lines = ["Current Mode A backend limits:"]
    for b in CURRENT_BACKENDS:
        lines.append(f"  - {b.backend} ({b.role}): {b.notes}")
    lines.append("Future backends (not in the current main implementation): "
                 + ", ".join(f"{f.name} ({f.would_add})" for f in FUTURE_BACKENDS))
    return "\n".join(lines)


__all__ = [
    "BackendCapability", "CURRENT_BACKENDS",
    "SKELETON_IS_WEAK_GUIDANCE_ONLY", "GPT_IMAGE_1_HAS_HARD_POSE_INTERFACE",
    "KLING_GUARANTEES_EXACT_MOTION_TRANSFER",
    "FutureBackend", "FUTURE_BACKENDS",
    "supports_hard_pose_control", "describe_limits",
]
