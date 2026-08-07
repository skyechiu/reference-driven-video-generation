"""
reference_policy.py — Mode A reference-ordering & identity policy layer.

Reusable, side-effect-free policy for how a Mode A shot assembles its
gpt-image-1 ``images.edit`` reference slots, which identity anchor it uses,
what to do when anchors are missing, and which ``quality`` / ``input_fidelity``
setting each shot type earns.

These rules were extracted from the street-run (``live_test_04_street_look3``)
fixes. They are NOT street-specific — any Mode A run with the same shot
taxonomy can import and apply them.

Importing this module has no side effects: it calls no API, reads/writes no
state file, and does not modify the current production scripts
(``generate_street_run.py`` etc.). Folding these policies into the shared
pipeline is a separate, deliberate step (see
``docs/MODE_A_REUSABLE_POLICIES.md``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# ── Shot taxonomy ───────────────────────────────────────────────────────────
class ShotType:
    """The five reusable Mode A shot types."""
    FACE_VISIBLE = "face_visible"   # face is the primary concern (medium / close / turn-to-camera)
    BACK_VIEW    = "back_view"      # walking away, face not visible, low identity signal
    LOWER_BODY   = "lower_body"     # feet / hem insert, no face, composition-led
    SIDE_PROFILE = "side_profile"   # ¾ / side walk, partial face, pose matters
    GENERIC      = "generic"        # unclassified — safe identity-first default


SHOT_TYPES = (
    ShotType.FACE_VISIBLE,
    ShotType.BACK_VIEW,
    ShotType.LOWER_BODY,
    ShotType.SIDE_PROFILE,
    ShotType.GENERIC,
)


# ── Reference slot roles (earlier slot == more model weight) ─────────────────
class RefRole:
    IDENTITY_FRONT   = "identity_anchor_front"    # primary facial identity
    IDENTITY_PROFILE = "identity_anchor_profile"  # side / ¾ profile identity support
    OUTFIT           = "outfit_ref"               # look*_front — SECONDARY outfit only
    SHEET            = "look_sheet"                # look*_sheet — NEVER primary identity
    SCENE            = "scene_ref"                 # environment / composition only
    SKELETON         = "pose_skeleton"            # clean skeleton on neutral bg — weak guidance
    HAIR             = "hair_profile_ref"         # hair / silhouette continuity


# ── Identity-source policy ───────────────────────────────────────────────────
# The two identity anchors are BUILT from these references, never from the
# contact sheet. Street run: look3_closeup.png + look3_profile_crop.png.
IDENTITY_PRIMARY_SOURCES = ("closeup", "profile_crop")
IDENTITY_FORBIDDEN_AS_PRIMARY = ("sheet",)  # look*_sheet is outfit/pose reference, not identity


# Canonical per-shot reference order. Slot 0 = highest weight.
# Scene is deliberately kept OUT of slot 0 for face-visible / side-profile shots
# so its texture does not compete with identity ("a generic person who fits the
# scene"). For low-identity shots (back view, lower body) the scene may lead.
_REFERENCE_ORDER = {
    ShotType.FACE_VISIBLE: [RefRole.IDENTITY_FRONT, RefRole.SCENE,    RefRole.OUTFIT, RefRole.IDENTITY_PROFILE],
    ShotType.SIDE_PROFILE: [RefRole.IDENTITY_FRONT, RefRole.SKELETON, RefRole.OUTFIT, RefRole.IDENTITY_PROFILE],
    ShotType.BACK_VIEW:    [RefRole.SCENE,          RefRole.IDENTITY_FRONT, RefRole.OUTFIT, RefRole.HAIR],
    ShotType.LOWER_BODY:   [RefRole.SCENE,          RefRole.OUTFIT,   RefRole.SHEET],
    ShotType.GENERIC:      [RefRole.IDENTITY_FRONT, RefRole.SCENE,    RefRole.OUTFIT, RefRole.IDENTITY_PROFILE],
}


@dataclass
class ReferenceSlot:
    index: int
    role: str
    source: Optional[str]   # resolved path/id, or None if text-only fallback
    note: str = ""


# ── Fallback chains: if the preferred role has no source, try these in order ──
_FALLBACK = {
    RefRole.IDENTITY_FRONT:   [RefRole.IDENTITY_PROFILE, RefRole.OUTFIT],
    RefRole.IDENTITY_PROFILE: [RefRole.IDENTITY_FRONT],
    RefRole.OUTFIT:           [RefRole.SHEET],
    RefRole.HAIR:             [RefRole.IDENTITY_PROFILE, RefRole.IDENTITY_FRONT],
    RefRole.SCENE:            [],        # missing scene -> describe scene in text only
    RefRole.SKELETON:         [],        # missing skeleton -> downgrade to text_framing
    RefRole.SHEET:            [RefRole.OUTFIT],
}


def _resolve(role: str, sources: dict) -> tuple[Optional[str], str]:
    """Resolve a role to a concrete source using the fallback chain."""
    if sources.get(role):
        return sources[role], ""
    for alt in _FALLBACK.get(role, []):
        if sources.get(alt):
            return sources[alt], f"fallback: {role} missing -> using {alt}"
    return None, f"no source for {role} (text-only)"


def build_reference_order(
    shot_type: str,
    sources: dict,
    pose_skeleton_available: bool = False,
) -> list[ReferenceSlot]:
    """Return the ordered ``images.edit`` reference slots for a shot.

    Args:
        shot_type: one of :data:`SHOT_TYPES`.
        sources: mapping ``RefRole -> path/id`` for whatever this run has.
                 Missing/None entries trigger the fallback chain.
        pose_skeleton_available: if True and this is a pose-driven full-body
            shot, the clean skeleton is inserted as a soft pose slot. If a
            skeleton role is expected but unavailable, the shot silently
            downgrades to text+framing conditioning (see backend_limits.py:
            skeleton images are weak guidance only).

    Pure function — no I/O, no API. Order reflects the street-run rules and
    generalises to any Mode A run with the same taxonomy.
    """
    if shot_type not in SHOT_TYPES:
        shot_type = ShotType.GENERIC

    roles = list(_REFERENCE_ORDER[shot_type])

    # Pose-driven full-body handling: keep the skeleton only if we actually have
    # one. For side_profile the skeleton already sits at slot 1; for a walking
    # back_view we promote it to slot 0 when present.
    if RefRole.SKELETON in roles and not pose_skeleton_available:
        roles = [r for r in roles if r != RefRole.SKELETON]  # downgrade to text_framing
    if pose_skeleton_available and shot_type == ShotType.BACK_VIEW and RefRole.SKELETON not in roles:
        roles.insert(0, RefRole.SKELETON)

    slots: list[ReferenceSlot] = []
    for i, role in enumerate(roles):
        src, note = _resolve(role, sources)
        slots.append(ReferenceSlot(index=i, role=role, source=src, note=note))
    return slots


def select_identity_anchor(shot_type: str, anchors: dict) -> tuple[Optional[str], str]:
    """Pick the primary identity anchor for a shot.

    ``anchors`` maps ``RefRole.IDENTITY_FRONT`` / ``RefRole.IDENTITY_PROFILE``
    to paths. Front leads for face-visible / generic; profile leads for
    side-profile; low-identity shots still take front but at reduced weight
    (see :func:`build_reference_order`).
    """
    front = anchors.get(RefRole.IDENTITY_FRONT)
    profile = anchors.get(RefRole.IDENTITY_PROFILE)

    if shot_type == ShotType.SIDE_PROFILE:
        chosen = profile or front
    else:
        chosen = front or profile

    if not chosen:
        return None, "needs_human: no identity anchor available"
    return chosen, "ok"


@dataclass
class QualityPolicy:
    quality: str          # "high" | "medium"
    input_fidelity: str   # always "high"


def quality_policy(shot_type: str) -> QualityPolicy:
    """``quality`` / ``input_fidelity`` policy by shot type.

    ``input_fidelity`` is ``"high"`` on every call. ``quality`` is reserved
    ``"high"`` for shots where facial identity must be precise; back/lower-body
    shots use ``"medium"`` to save cost without risking identity.
    """
    identity_primary = shot_type in (ShotType.FACE_VISIBLE, ShotType.SIDE_PROFILE, ShotType.GENERIC)
    return QualityPolicy(
        quality="high" if identity_primary else "medium",
        input_fidelity="high",
    )


__all__ = [
    "ShotType", "SHOT_TYPES", "RefRole", "ReferenceSlot", "QualityPolicy",
    "IDENTITY_PRIMARY_SOURCES", "IDENTITY_FORBIDDEN_AS_PRIMARY",
    "build_reference_order", "select_identity_anchor", "quality_policy",
]
