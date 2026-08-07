# Evaluation Report — live_test_04_street_look3
## Reference-Driven Agentic Short-Form Video Generation System

**Date:** 2026-07-18 22:19 UTC
**Scene:** scene_02_modern_street — Quiet Parisian cobblestone street
**Look:** Look 3 · The Tailored Self
**scene_mode:** use_scene_package

---

## Experiment Overview

| Field | Value |
|---|---|
| Pipeline mode | Scene Package Demo — shared keyframe-to-I2V pipeline |
| Reference scene | scene_02_modern_street — quiet Parisian cobblestone street |
| Scene references used | main_scene_board · establishing_view · side_view |
| Selected look | Look 3 · The Tailored Self |
| Outfit | Cropped charcoal blazer · white shirt · muted olive tie · wide faded denim · black oxfords |
| Keyframe model | gpt-image-1 / images.edit / 1024×1536 / medium |
| Video model | Kling v1.6 / std / 9:16 / 5s |
| Shots | 4 |
| Repair triggered | No |

## Per-Shot Results

| shot_id | Framing | slot_mode | Scene ref (role) | Keyframe | Clip | Status |
|---|---|---|---|---|---|---|
| shot_001 | medium_over_shoulder | face_visible | main_scene_board_16x9.jpg (slot[3] env-only) | ✓ | ✓ | Pass (visual) |
| shot_002 | wide_full_body_walk_away | back_view | establishing_view_16x9.png (slot[3] env-only) | ✓ | ✓ | Pass (visual) |
| shot_003 | extreme_low_angle_feet_CU | lower_body | main_scene_board_16x9.jpg (slot[3] env-only) | ✓ | ✓ | Pass (visual) |
| shot_004 | wide_side_profile_walk | face_visible | side_view_16x9.png (slot[3] env-only) | ✓ | ✓ | Pass (visual) |

## Evaluation Findings

- **Identity conditioning strategy:** For face-visible shots (001, 002, 004), `look3_sheet.png` is
  placed in slot [0] (highest model weight) as the primary identity reference, with `look3_closeup.png`
  in slot [1]. The scene reference occupies slot [3] (lowest weight) and is explicitly labelled as
  environment-only in the prompt. Shot_003 uses `scene_first` slot order — face not visible, composition
  is the priority.
- **Cross-shot continuity:** For shots 002 and 004, the approved shot_001 keyframe replaces
  `look3_front.png` in slot [2] to reinforce silhouette and hair continuity across cuts.
- **Scene continuity:** All 4 shots reference the same Parisian cobblestone street scene package.
  Limestone facades, cobblestone paving, gas lamps, and soft diffused daylight are consistent across shots.
- **Look consistency:** Look 3 outfit (charcoal blazer, olive tie, wide denim, black oxfords) applied to all shots.
  Forbidden-word guard passed all 4 prompts before generation.
- **Motion:** Prompt-level I2V. Action intent (walking, glance, side-profile, feet detail) communicated via video prompt.
  Exact gait and frame-level pose transfer are not guaranteed.
- **Evaluation status:** Human visual review only. Automated ArcFace scoring and pose evaluation are pending.

## Key Claim

> "The system preserves referenced scene structure and action intent, but does not perform
> exact frame-level motion transfer. Identity is conditioned via the look sheet reference in
> slot [0], not by text description alone."

## Limitations

1. Identity conditioning via reference images in slot [0] — no LoRA or IP-Adapter fine-tuning.
   Identity stability depends on how consistently the model weights the first reference slot.
2. Exact gait and frame-level motion transfer are not guaranteed (Kling is prompt-level I2V).
3. Camera motion and character motion follow prompt intent, not extracted reference trajectories.
4. No reference video was used for this run — scene structure comes from static scene package images.
5. Human review is still required before final output.

## Artifacts

| Artifact | Path |
|---|---|
| Final video | `final/final_look3_street_demo.mp4` |
| Keyframe contact sheet | `final/keyframe_contact_sheet.png` |
| Clip review sheet | `final/clip_review_sheet.png` |
| Run summary | `final/run_summary.md` |
| Decision log | `final/decision_log.json` |
