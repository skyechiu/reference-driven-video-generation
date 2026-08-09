# Run Summary: live_test_04_street_look3

> **Label:** Scene Package Demo — shared keyframe-to-I2V pipeline
> This is NOT a Mode A reference-video run. No reference video was used.
> Scene structure comes from static scene package images (scene_02_modern_street).

## Run Config

| Field | Value |
|---|---|
| run_id | live_test_04_street_look3 |
| run_label | Scene Package Demo — shared keyframe-to-I2V pipeline |
| run_date | 2026-07-18 22:19 UTC |
| pipeline_mode | Scene Package Demo — shared keyframe-to-I2V pipeline |
| reference_video | None (scene package run) |
| selected_look | Look 3 · The Tailored Self |
| scene | scene_02_modern_street — Parisian cobblestone street |
| scene_mode | use_scene_package |
| keyframe_model | gpt-image-1 / images.edit / 1024×1536 / medium |
| video_model | Kling v1.6 / std / 9:16 / 5s |

## Image Slot Layout

### Face-visible shots (shot_001, shot_002, shot_004) — `identity_first`

| Slot | File | Role |
|---|---|---|
| [0] PRIMARY | `look3_sheet.png` | Primary identity reference — multi-angle view of the exact woman. Highest model weight. |
| [1] | `look3_closeup.png` | Secondary face fidelity reference — confirms facial details at close range. |
| [2] | `look3_front.png` or approved `shot_001` keyframe | Outfit / body reference. Shot_001 keyframe used for shots 002 and 004 to reinforce silhouette continuity. |
| [3] ENV ONLY | scene reference image | Environment and composition anchor ONLY. Does not define facial identity. |

### Feet shot (shot_003) — `scene_first`

| Slot | File | Role |
|---|---|---|
| [0] PRIMARY | scene reference (`main_scene_board_16x9.jpg`) | Composition anchor — cobblestone surface, ground-level framing, lighting. |
| [1] | `look3_front.png` | Lower-body outfit reference — denim hem and oxford shoes. |
| [2] | `look3_sheet.png` | Look overview reference. |
| [3] | `look3_closeup.png` | Deprioritised — face not visible in this shot. |

## Scene Reference Assets

| File | Used in | Slot | Role |
|---|---|---|---|
| `main_scene_board_16x9.jpg` | shot_001, shot_003 | [3] env-only (001) · [0] composition (003) | Boulangerie courtyard / cobblestone intersection |
| `establishing_view_16x9.png` | shot_002 | [3] env-only | Deep perspective down narrow street |
| `side_view_16x9.png` | shot_004 | [3] env-only | Along Haussmann facade with iron railings |

## Shots

### shot_001

| Field | Value |
|---|---|
| framing | medium_over_shoulder |
| slot_mode | face_visible |
| image slots | [face_visible+anchor] identity_anchor[0] · closeup[1] · look_front[2] · profile[3]  [scene→text_only] |
| scene_ref | main_scene_board_16x9.jpg |
| keyframe | `shot_001_keyframe_look3_street.png` (3425 KB) |
| keyframe_status | ✓ generated |
| clip | `shot_001_look3_street.mp4` (10489 KB) |
| clip_status | ✓ success |

**Video prompt:** Medium over-shoulder shot. The character walks slowly along the quiet cobblestone Parisian street. She naturally turns her head slightly to the left — an unhurried glance, not dramatic. Very subtle mo...

### shot_002

| Field | Value |
|---|---|
| framing | wide_full_body_walk_away |
| slot_mode | back_view |
| image slots | [back_view+anchor] scene[0] · identity_anchor[1] · look_front[2] · profile[3] |
| scene_ref | establishing_view_16x9.png |
| keyframe | `shot_002_keyframe_look3_street.png` (2297 KB) |
| keyframe_status | ✓ generated |
| clip | `shot_002_look3_street.mp4` (9811 KB) |
| clip_status | ✓ success |

**Video prompt:** Wide full-body shot. The character walks away from the camera down the center of the narrow cobblestone Parisian street toward the vanishing point. Natural unhurried walking stride. Wide denim trouser...

### shot_003

| Field | Value |
|---|---|
| framing | extreme_low_angle_feet_CU |
| slot_mode | lower_body |
| image slots | [lower_body] scene[0] · look_front[1] · look_sheet[2] |
| scene_ref | main_scene_board_16x9.jpg |
| keyframe | `shot_003_keyframe_look3_street.png` (2567 KB) |
| keyframe_status | ✓ generated |
| clip | `shot_003_look3_street.mp4` (8488 KB) |
| clip_status | ✓ success |

**Video prompt:** Low-angle close-up of lower legs and feet only. Animate subtle walking movement across grey Parisian cobblestone. Wide denim trouser hems and black oxford shoes step across the irregular stone paving....

### shot_004

| Field | Value |
|---|---|
| framing | wide_side_profile_walk |
| slot_mode | face_visible |
| image slots | [face_visible+anchor] identity_anchor[0] · closeup[1] · look_front[2] · profile[3]  [scene→text_only] |
| scene_ref | side_view_16x9.png |
| keyframe | `shot_004_keyframe_look3_street.png` (3645 KB) |
| keyframe_status | ✓ generated |
| clip | `shot_004_look3_street.mp4` (11249 KB) |
| clip_status | ✓ success |

**Video prompt:** Wide side-profile shot. The character walks from left to right along the Parisian building facade. Head slightly lowered, soft private gaze, not looking at camera. Natural unhurried walking stride. Li...

## Pipeline Notes

- **Identity conditioning strategy:** For face-visible shots, `look3_sheet.png` is placed in slot [0]
  (highest model weight) as the primary identity reference. `look3_closeup.png` is in slot [1] as a
  secondary face fidelity reference. The scene reference image occupies slot [3] (lowest weight) and
  is explicitly labelled as environment-only in the prompt — it does not define facial identity.
- **Continuity:** For shots 002 and 004, the approved shot_001 keyframe replaces `look3_front.png`
  in slot [2] to reinforce silhouette and hair consistency across shots.
- **Feet shot exception:** shot_003 uses `scene_first` slot order — the scene reference is at [0]
  because composition (cobblestone, ground level) is the primary concern. Face references are
  deprioritised in slots [2–3] since no face is visible.
- **Prompt policy:** Every face-visible prompt explicitly states:
  "The street scene reference (image 4) controls the environment, NOT the face."
  Anti-drift guards included: "Do not invent a new face. Do not average into a generic woman."
- Forbidden-word guard passed all 4 prompts before any API call.
- Motion is prompt-level I2V (not frame-level pose transfer).
- Automatic Stage-4/5 repair loop: not triggered (`decision_log.json.repair_triggered = false`).
  Human-guided prompt-level motion repair: executed for shot_001 and shot_003 — see "Motion v2
  promotion" below. This is a separate, explicitly logged event; it is not the automatic loop.
- No modification to beach run (live_test_03_4shots).
- Final video: `final/final_look3_street_demo.mp4` — assembled ✓

## Claim

The system preserves referenced scene structure and action intent,
but does not perform exact frame-level motion transfer.
Identity is conditioned via the look sheet reference in slot [0], not by text description alone.


## Motion v2 promotion (2026-07-20)

The motion_v2 clips were promoted to the official street run for **shot_001** and **shot_003**.

- shot_001 recovered motion: **14% -> 51%**
- shot_003 recovered motion: **19% -> 47%**
- Repair method: **prompt-only Kling I2V** (damping words removed, motion cues named)
- **No keyframe regeneration**; shot_002 and shot_004 unchanged
- v1 clips retained as backups (`clips/*_premotion_backup.mp4`); `final/final_look3_street_demo.mp4` and `final/clip_review_sheet.png` rebuilt
- This is motion-**energy** recovery, not exact frame-level motion transfer.
