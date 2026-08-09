"""
stage3_generate.py — Per-Shot Generation

Iterates over all pending shots in state and generates:
  1. Keyframe image (via chosen backend)
  2. Video clip (via chosen backend)

Skips shots that already passed evaluation.
On failure, marks shot status and continues — the repair loop in Stage 5
will pick up failed shots.
"""

import os
import traceback

from config import (
    GENERATOR_BACKEND, VIDEO_BACKEND,
    IP_REFERENCE_IMAGES, IP_CHARACTER_DESCRIPTION,
)
import state as st


def get_generator():
    if GENERATOR_BACKEND == "api":
        from generators.api_gen import APIGenerator
        return APIGenerator()
    elif GENERATOR_BACKEND == "local":
        from generators.local_gen import LocalGenerator
        return LocalGenerator(video_backend=VIDEO_BACKEND)
    else:
        raise ValueError(f"Unknown GENERATOR_BACKEND: {GENERATOR_BACKEND}")


def generate_shot(gen, shot: dict, state: dict, repair_hints: dict | None = None) -> bool:
    """
    Generate keyframe + video for one shot.
    Returns True on success, False on failure.

    Image resolution priority:
      1. state["ip_references"]  — set by api_select_look_package / enrichment from selected look
      2. state["ip_character"]["reference_images"]  — legacy fallback only

    Character description:
      IP_CHARACTER_DESCRIPTION (face/body only — no outfit).
      Outfit comes from look_package via generation_brief.keyframe_prompt.
    """
    shot_id    = shot["shot_id"]
    scene_mode = state.get("scene_mode", "scene_restyle")

    # ── Resolve IP images from selected look (preferred) or legacy fallback ──
    # Identity note: until a separate identity image set is configured,
    # look reference images serve as IP conditioning for both identity and look.
    ip_refs = state.get("ip_references") or []
    if ip_refs:
        ip_images = [r["path"] if isinstance(r, dict) else r for r in ip_refs]
        print(f"[stage3] look IP references ({len(ip_images)}): "
              f"{[os.path.basename(p) for p in ip_images]}")
    else:
        ip_images = state.get("ip_character", {}).get("reference_images", [])
        if ip_images:
            print("[stage3] WARNING: using legacy ip_character.reference_images "
                  "— select a look package to use correct reference images")

    # ── When scene_mode = preserve_reference_scene, append source frame ──
    # The source frame gives images.edit both pose/framing structure AND
    # the background/lighting to preserve. It must come LAST so the model
    # treats it as a structural+scene reference, not an identity reference.
    source_frame = (shot.get("source_frame") or shot.get("best_keyframe_path")
                    or shot.get("pose_image") or "")
    if scene_mode == "preserve_reference_scene" and source_frame and os.path.exists(source_frame):
        ip_images = ip_images + [source_frame]
        print(f"[stage3] appended source frame for preserve_reference_scene: "
              f"{os.path.basename(source_frame)}")
    elif scene_mode == "preserve_reference_scene" and not source_frame:
        print(f"[stage3] WARNING: preserve_reference_scene requested but no source_frame "
              f"found for {shot_id} — scene preservation relies on prompt text only")

    # ── Character description (face/body only) ────────────────────────────
    char_desc = IP_CHARACTER_DESCRIPTION  # from config — must not contain outfit wording
    scene_prompt = state.get("active_scene_prompt") or state.get("source_scene_description") \
                   if scene_mode == "preserve_reference_scene" \
                   else state.get("scene_prompt", "")

    try:
        # Record which prompt is being used — stage4 reads shot["_last_prompt"]
        # for prompt_used in the decision log. Must be set before generate_keyframe
        # so the value persists via the next update_shot_output → save(state) call.
        shot["_last_prompt"] = shot.get("generation_brief", {}).get("keyframe_prompt", "")

        # 1. Keyframe — skip if already on disk (e.g. from a previous run)
        existing_img = shot.get("generated_image")
        if existing_img and os.path.exists(existing_img) and repair_hints is None:
            img_path = existing_img
            print(f"[gen] keyframe already exists, skipping generation: {img_path}")
        else:
            img_path = gen.generate_keyframe(
                shot=shot,
                ip_images=ip_images,
                character_description=char_desc,
                scene_prompt=scene_prompt,
                repair_hints=repair_hints,
            )
            st.update_shot_output(state, shot_id, generated_image=img_path)

        # 2. Video clip
        clip_path = gen.generate_video_clip(
            keyframe_path=img_path,
            shot=shot,
            scene_prompt=scene_prompt,
        )
        st.update_shot_output(state, shot_id, video_clip=clip_path)

        print(f"[gen] ✓ {shot_id} generated")
        return True

    except Exception as e:
        print(f"[gen] ✗ {shot_id} generation failed: {e}")
        traceback.print_exc()
        return False


def run(state: dict, shot_ids: list[str] | None = None) -> dict:
    """
    Generate all pending shots (or a specific subset via shot_ids).
    Repair_hints are None for first-pass generation.
    """
    gen = get_generator()
    print(f"[gen] backend={GENERATOR_BACKEND}, video={VIDEO_BACKEND}")

    shots_to_process = [
        s for s in state["shots"]
        if s["evaluation"]["status"] in ("pending", "fail")
        and (shot_ids is None or s["shot_id"] in shot_ids)
    ]

    print(f"[gen] processing {len(shots_to_process)} shots")
    st.set_stage(state, "generating")

    for shot in shots_to_process:
        print(f"\n── {shot['shot_id']} ──────────────────────────")
        generate_shot(gen, shot, state)

    st.set_stage(state, "evaluating")
    return state


def run_repair(state: dict, shot_id: str, repair_hints: dict) -> bool:
    """
    Re-generate a single shot with repair hints.
    Called by the repair loop (Stage 5).
    """
    gen = get_generator()
    shot = st.get_shot(state, shot_id)
    if shot is None:
        raise ValueError(f"Shot {shot_id} not found")

    print(f"[gen] repair attempt for {shot_id}: {repair_hints}")
    return generate_shot(gen, shot, state, repair_hints=repair_hints)


if __name__ == "__main__":
    import sys
    s = st.load()
    if len(sys.argv) > 1:
        run(s, shot_ids=sys.argv[1:])
    else:
        run(s)
