# Run Summary: live_test_03_4shots

## Pipeline Mode
Mode A — API pipeline (gpt-image-1 keyframe generation + Kling I2V clip generation)

## Run Config

| Field | Value |
|---|---|
| run_id | live_test_03_4shots |
| run date | 2026-07-17 |
| selected look | Look 3 · The Tailored Self (`look_3_tailored_self`) |
| scene_mode | preserve_reference_scene |
| keyframe model | gpt-image-1 / images.edit / 1024×1536 / medium quality |
| video model | Kling v1.6 / std mode / 9:16 / 5s clips |
| ip_character | Young woman, mid-twenties, slender tall build, light olive skin, almond eyes, composed expression |
| active_scene_prompt | seaside sunset, beach, ocean horizon, warm golden sunset light, coastal atmosphere |

## Input Reference Video

| Field | Value |
|---|---|
| path | `test/test_03_multishot_edit_4shots.mp4` |
| usage | Structure extraction only — shot cuts, framing, pose/motion reference |
| audio | Used for beat analysis only; not reproduced in output |
| content | Royalty-free / self-created reference material |

The reference video was analysed for formal structure (shot cuts, rhythm, framing, body position).
No reference content is reproduced. Outputs use the original IP character, new prompts, and
new scene materials. This is extract-structure / regenerate-content, not a re-skin.

## Motion Note

Motion in all 4 clips is **prompt-level image-to-video (I2V)**, not exact pose transfer.
Kling animates from the approved keyframe using a natural-language video prompt describing
the intended motion (walking direction, camera, body pose). There is no per-frame skeleton
tracking or ControlNet-style pose conditioning applied at the video stage.
This is the expected behaviour for the current Mode A pipeline; pose accuracy is evaluated
post-generation in the evaluation step.

## Shots

### shot_001

| Field | Value |
|---|---|
| framing | Over-shoulder MCU — character turns head back toward camera, seaside sunset |
| keyframe path | `outputs/runs/live_test_03_4shots/keyframes/shot_001_keyframe_look3_preserve_scene_test.png` |
| keyframe size | 2003 KB |
| clip path | `outputs/runs/live_test_03_4shots/clips/shot_001_look3.mp4` |
| clip size | 4919 KB |
| keyframe attempts | 1 (v3 prompt — preserve scene, over-shoulder MCU) |
| kling status | success |

**Video prompt:**
> Over-shoulder medium close-up. The character naturally turns her head back toward the camera in the same pose as the keyframe. Very subtle push-in camera motion. Preserve the seaside sunset background, warm natural light, tailored blazer outfit, and quiet candid expression. Keep motion minimal and realistic. No identity drift, no extra people.

### shot_002

| Field | Value |
|---|---|
| framing | Wide full-body back-view — character walks away from camera along beach |
| keyframe path | `outputs/runs/live_test_03_4shots/keyframes/shot_002_keyframe_look3_preserve_scene.png` |
| keyframe size | 1993 KB |
| clip path | `outputs/runs/live_test_03_4shots/clips/shot_002_look3.mp4` |
| clip size | 4347 KB |
| keyframe attempts | 2 (v1 blocked by forbidden-word guard → v2 natural-realism prompt) |
| kling status | success |

**Video prompt:**
> Wide full-body back-view walking shot. The character walks away from the camera along the beach toward the sunset. Keep the back view, full body, visible shoes, wide denim trousers, cropped blazer, and natural walking stride. Camera remains mostly static. Preserve beach sunset background and wet sand. Do not turn the character toward camera. No extra people.

### shot_003

| Field | Value |
|---|---|
| framing | Extreme low-angle close-up — lower legs and feet only, wet sand at shoreline |
| keyframe path | `outputs/runs/live_test_03_4shots/keyframes/shot_003_keyframe_look3_preserve_scene.png` |
| keyframe size | 2088 KB |
| clip path | `outputs/runs/live_test_03_4shots/clips/shot_003_look3.mp4` |
| clip size | 7676 KB |
| keyframe attempts | 2 (v1 prompt wrong — face-forward — inspected source → v2 low-angle feet rewrite) |
| kling status | success |

**Video prompt:**
> Low-angle close-up of lower legs and feet only. Animate subtle walking movement through wet sand and shallow water. Keep wide denim trouser hems and black oxford shoes visible. Do not show face, torso, arms, or upper body. Preserve sunset reflections, wet sand, shoreline water movement, and natural video-frame softness. No extra legs, no duplicated feet.

### shot_004

| Field | Value |
|---|---|
| framing | Wide side-profile — character walks sideways along shoreline, three-quarter profile |
| keyframe path | `outputs/runs/live_test_03_4shots/keyframes/shot_004_keyframe_look3_preserve_scene.png` |
| keyframe size | 2118 KB |
| clip path | `outputs/runs/live_test_03_4shots/clips/shot_004_look3.mp4` |
| clip size | 7593 KB |
| keyframe attempts | 3 (v1 too generic → v2 still generic → v3 maximal look specificity, labeled subsections) |
| kling status | success |

**Video prompt:**
> Wide side-profile walking shot. The character walks sideways along the beach shoreline toward frame-left, head slightly lowered, not looking at camera. Preserve full-body framing, side profile, raised foot mid-stride, tailored blazer, wide denim trousers, and black shoes. Camera has slight handheld natural movement. Preserve sunset, ocean reflection, and rocky headland. No portrait pose, no front-facing turn.

## Pipeline Notes

- All 4 keyframes generated via `gpt-image-1 images.edit` with 4 input images per shot.
- Image slot order (locked): `[0]` source frame (structural anchor), `[1]` look front/body,
  `[2]` look sheet, `[3]` look closeup. Exception: shot_003 face is out of frame — closeup
  moved to `[3]` (weakest weight) to avoid face-bleed into a feet-only shot.
- Kling I2V submitted via `run_kling_i2v.py` (local run; no sandbox API calls).
- OpenAI was not called during or after the Kling run.
- **No repair loop triggered.** Pending clip review and evaluation scoring.
- **No final video assembly.** Awaiting clip review approval.
- **No extra generation.** Only the 4 approved keyframes were used.
- Forbidden-word guard active on all keyframe generation scripts (positive prompt only;
  negative prompt stored separately, never passed to API).

## Evaluation (Pending)

| Shot | Identity | Pose/Motion | Framing | Beat Alignment |
|---|---|---|---|---|
| shot_001 | TBD | TBD | TBD | TBD |
| shot_002 | TBD | TBD | TBD | TBD |
| shot_003 | TBD | TBD | TBD | TBD |
| shot_004 | TBD | TBD | TBD | TBD |

## Decision Log

| Shot | Keyframe Attempts | Key Issue | Fix |
|---|---|---|---|
| shot_001 | 1 | — | v3 prompt approved on first test |
| shot_002 | 2 | v1 blocked by forbidden-word guard (bride/bridal in negative instructions) | Separated positive/negative prompts; v2 natural-realism language |
| shot_003 | 2 | v1 prompt described face-forward pose — wrong for source frame | Inspected source frame first; v2 rewritten as extreme low-angle feet close-up |
| shot_004 | 3 | v1–v2 rendered generic black business blazer + straight jeans | v3: labeled prompt subsections (BLAZER/TIE/TROUSERS), strong negatives, look3_front.png to [1] |

## Pending

- [ ] User reviews 4 Kling clips
- [ ] Evaluation scoring (ArcFace identity / pose keypoint / framing / beat alignment)
- [ ] Repair loop decision (PENDING approval after clip review)
- [ ] Final video assembly (PENDING approval after clip review)

---

## Paper-Friendly Exports

Saved to: `final/paper_exports/`

| File | Purpose | Format |
|---|---|---|
| `keyframe_contact_sheet_landscape.png` | 2×2 grid of all 4 approved keyframes on 16:9 canvas | PNG, 3200×1800 |
| `clip_review_sheet_landscape_part1.png` | First/mid/last frames for shot_001–002 | PNG, 3400×1480 |
| `clip_review_sheet_landscape_part2.png` | First/mid/last frames for shot_003–004 | PNG, 3400×1480 |
| `reference_vs_keyframe_landscape.png` | Source frame vs generated keyframe per shot, 2×2 blocks | PNG, 3840×2160 |
| `final_video_preview_landscape.mp4` | Portrait final video centered on 16:9 black background — for presentation only | MP4, 1920×1080, CRF 16 |

**Note:** Original 9:16 generated clips and final assembled video are unchanged. Paper exports are visual evidence only.
