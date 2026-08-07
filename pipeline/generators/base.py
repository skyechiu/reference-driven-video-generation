"""
base.py — Abstract generator interface.
Both backends implement this so the pipeline is backend-agnostic.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class GeneratorBase(ABC):

    @abstractmethod
    def generate_keyframe(
        self,
        shot: dict,
        ip_images: list[str],
        character_description: str,
        scene_prompt: str,
        repair_hints: dict | None = None,
    ) -> str:
        """
        Generate a keyframe image for one shot.
        repair_hints: dict with diagnosis + suggested adjustments (from repair stage).
        Returns path to saved image.
        """
        ...

    @abstractmethod
    def generate_video_clip(
        self,
        keyframe_path: str,
        shot: dict,
        scene_prompt: str,
    ) -> str:
        """
        Generate a short video clip from a keyframe image.
        Returns path to saved video clip.
        """
        ...

    def build_prompt(
        self,
        shot: dict,
        character_description: str,
        scene_prompt: str,
        repair_hints: dict | None = None,
    ) -> str:
        """
        Build the generation prompt from shot data.

        Preferred path (Mode A 5-track): read shot["generation_brief"]["keyframe_prompt"]
        written by api_run_semantic_enrichment via _build_prompt_blocks().
        This is the structured, per-track assembled prompt — richer than the
        legacy flat-field assembly below.

        Legacy path (Mode B or unenriched shots): assemble from raw shot fields
        as before.

        repair_hints adds targeted emphasis on top of whichever path was taken.
        """
        # ── Preferred: pre-built structured prompt ──────────────────
        generation_brief = shot.get("generation_brief", {})
        base_prompt = generation_brief.get("keyframe_prompt", "")

        if not base_prompt:
            # ── Legacy: flat-field assembly ──────────────────────────
            framing_instruction = {
                "extreme-close-up": "Extreme close-up. Only eyes and nose visible, no chin.",
                "close-up": "Close-up shot. Face and upper chest, no background distractions.",
                "medium-close-up": "Medium close-up. Head and shoulders visible.",
                "medium": "Medium shot. Waist and above visible.",
                "medium-wide": "Medium wide shot. Full torso and thighs visible.",
                "wide": "Wide shot. Full body from head to toe, environment visible.",
                "extreme-wide": "Extreme wide shot. Character small against environment.",
                "unknown": "Medium shot.",
            }.get(shot.get("framing", "unknown"), "Medium shot.")

            prompt_parts = [
                "Cinematic vertical 9:16 short film frame.",
                f"Character: {character_description}",
                f"Scene: {scene_prompt}",
                f"Framing: {framing_instruction}",
                f"Shot description: {shot.get('description', '')}",
                "Style: cinematic, soft natural lighting, film grain, high detail.",
                "Do not change the character's face, identity, or costume.",
            ]
            base_prompt = " ".join(prompt_parts)

        # ── Repair emphasis (appended regardless of path taken) ─────
        if repair_hints:
            repair_parts = []

            # 5-track names (new, from stage5_repair.classify_failure)
            if repair_hints.get("identity_failed"):
                repair_parts.append(
                    "IMPORTANT: Preserve exact face identity — same bone structure, "
                    "same eyes, same nose, same lips as the reference character."
                )
            if repair_hints.get("character_motion_failed"):
                repair_parts.append(
                    f"IMPORTANT: Follow the pose strictly — {repair_hints.get('pose_note', 'match body position and arm angles exactly')}."
                )
            if repair_hints.get("framing_failed"):
                repair_parts.append(
                    f"IMPORTANT: Correct framing — {repair_hints.get('framing_note', 'match the specified camera distance')}."
                )
            if repair_hints.get("camera_motion_failed"):
                repair_parts.append(
                    f"IMPORTANT: Camera motion — {repair_hints.get('camera_motion_note', 'ensure camera movement matches the reference type')}."
                )
            if repair_hints.get("timing_failed"):
                repair_parts.append(
                    "NOTE: Beat alignment adjustment requested — cut timing will be adjusted externally."
                )

            # Legacy names (backward compat if hints come from an older stage5 version)
            if repair_hints.get("identity_drift") and not repair_hints.get("identity_failed"):
                repair_parts.append(
                    "IMPORTANT: Preserve exact face identity — same bone structure, "
                    "same eyes, same nose, same lips as the reference character."
                )
            if repair_hints.get("pose_mismatch") and not repair_hints.get("character_motion_failed"):
                repair_parts.append(
                    f"IMPORTANT: Follow the pose strictly — {repair_hints.get('pose_note', '')}."
                )
            if repair_hints.get("framing_error") and not repair_hints.get("framing_failed"):
                repair_parts.append(
                    f"IMPORTANT: Correct framing — {repair_hints.get('framing_note', '')}."
                )

            # Look repair (both old and new naming use look_note)
            if repair_hints.get("look_failed") or repair_hints.get("look_mismatch"):
                look_note = repair_hints.get("look_note", "")
                if look_note:
                    repair_parts.append(f"IMPORTANT: Look correction — {look_note}.")

            # Extra subject
            if repair_hints.get("extra_subject_failed") or repair_hints.get("extra_subject_generated"):
                note = repair_hints.get("extra_subject_note", "")
                if note:
                    repair_parts.append(note)

            if repair_parts:
                base_prompt = base_prompt.rstrip(". ") + " " + " ".join(repair_parts)

        return base_prompt
