# Evaluation Report — Mode A v0.8.1
## Reference-Driven Agentic Short-Form Video Generation System

**Institution:** National Centre for Computer Animation (NCCA), Bournemouth University
**Programme:** MSc AI for Media
**Submission target:** September 2026
**Pipeline version:** Mode A v0.8.1 (logic freeze)
**Report date:** 2026-07-17
**Run ID:** live_test_03_4shots

---

## A. System Overview

### Project Title

*Reference-Driven Agentic Short-Form Video Generation System*

A system that accepts a reference short video and a fixed IP character as inputs, decomposes the reference into a structured source frame storyboard (shots, camera motion, pose, framing, timing, and semantic description), and regenerates a new 9:16 vertical short video in which the IP character appears in a user-selected look and scene. The pipeline is framed as a four-stage agentic workflow: reference decomposition → template building (storyboard JSON) → IP-conditioned keyframe generation → image-to-video animation with an evaluation and repair loop.

### Mode A — Reference Video (primary)

Mode A is the primary and fully implemented pipeline path. It accepts a real reference video as input and uses deterministic computer-vision tools — PySceneDetect for shot detection, librosa for beat/tempo analysis, MediaPipe for pose estimation, and an optical-flow classifier for camera motion — to produce a structured source frame storyboard. This storyboard drives all downstream generation.

### Mode B — Animated Storyboard Prompt (secondary)

Mode B bypasses the reference video analysis stage. Instead, the user provides a text description that is rendered as an animated 4-panel storyboard sheet using gpt-image-1. The rendered panels are then cropped and converted to the same storyboard JSON format used by Mode A. From the IP Keyframes stage onward, Modes A and B share identical logic. Mode B is implemented and functional but is secondary; it was designed to demonstrate that the shared generation-evaluation-repair loop is decoupled from the input source.

### Reference-Driven Agentic Workflow

The system is agentic in the specific sense that agents (Template Builder, Generation Planner, Evaluator, Repair Decision Maker) make decisions at each stage rather than executing a fixed linear script. Deterministic tools compute measurements; agents decide what to generate, whether output passes quality thresholds, how to diagnose failure, and what repair action to apply. Each shot maintains a decision log recording all attempts, scores, verdicts, diagnoses, and repair actions — making the agentic behaviour auditable and reproducible.

The central shared data structure is `project_state.json`, a single readable and writable state file that persists across all pipeline stages and records the full decision log per shot.

---

## B. Mode A Pipeline — Stage-by-Stage Description

### Stage 0 — Run Configuration

The user selects the reference video, sets copyright status, chooses a reference strategy (Strategy A: multi-shot edit; Strategy B: single continuous take; Strategy C: driving performance), selects an IP character look, and specifies `scene_mode` (`preserve_reference_scene` or `replace_with_selected_scene`). A pre-flight checker verifies all prerequisites before generation begins.

### Stage 1 — Analyze Reference Video

**1. Reference video upload and strategy selection**
The reference video is loaded locally. The system inspects frame count, fps, and duration and recommends a reference strategy. For this run, Strategy A (multi-shot edit) was selected.

**2. Shot detection**
PySceneDetect detects hard cuts using content-aware thresholding. For `test_03_multishot_edit_4shots.mp4` (7.92s, 30fps), 4 shot cuts were detected and validated against a beat-snapping constraint (cuts are snapped to the nearest librosa beat within a configurable tolerance; if no beat is close enough, the original cut time is preserved).

Reference video parameters:
- Duration: 7.92s
- Frame rate: 30fps
- BPM: 123.05
- Beats detected: 13
- Shot cuts detected: 4

**3. Camera motion analysis**
An optical-flow classifier (`_classify_camera_motion`) analyses each shot using dense optical flow to separate background (camera) motion from foreground (subject) motion. Each shot is classified into one of 12 camera motion types. Results per shot:

| shot_id | duration | camera motion | source |
|---|---|---|---|
| shot_001 | 2.40s | push_in | optical_flow |
| shot_002 | 2.27s | static | optical_flow |
| shot_003 | 2.13s | handheld | optical_flow |
| shot_004 | 1.10s | handheld | optical_flow |

**4. Character motion and pose analysis**
MediaPipe Pose estimates body keypoints per frame. Character motion type (walking, standing, turning, etc.) is inferred from keypoint displacement across frames. Pose overlay images were generated for all 4 shots and are stored in `outputs/runs/live_test_03_4shots/analysis/pose_overlay/`.

**5. GPT-4o Semantic Enrichment**
GPT-4o Vision is called per shot with the extracted source frame. It returns per-shot semantic data: camera angle, camera motion label, lighting type, environment type, character expression, gaze direction, action summary, and a prompt fragment. These are stored under `source="vlm_caption"` and used in keyframe prompt construction.

**6. Generation units (5-track schema)**
After analysis, the system builds `generation_units` — one per shot — in the 5-track schema. Each unit encodes five orthogonal tracks (see Section C). All 4 units in this run have `track_completeness = full` and `camera_motion_source = optical_flow`, indicating that the optical flow classifier ran successfully for all shots.

**7. Prompt blocks**
The `_build_prompt_blocks` function assembles structured keyframe prompts from the 5-track data. Prompts are divided into blocks: CHARACTER IDENTITY (from IP package), LOOK (from selected look package), FRAMING AND POSE (from source frame), SCENE (from scene_mode), REALISM, AVOID, and GUARD. All 4 shots in this run use `prompt_path = 5track_local_rebuild`.

### Stage 2 — Source Frame Storyboard

The system builds a human-readable source frame storyboard from analysis results — one extracted frame per shot with framing labels, pose confidence, camera motion type, timing (start/end seconds, beat position), and semantic description. This storyboard is reviewed and approved by the human operator before the storyboard JSON is exported. This is an explicit human-in-the-loop gate: generation does not proceed without approval.

### Stage 3 — IP Keyframe Generation

Each shot's generation unit is used to generate a keyframe image via `gpt-image-1 images.edit` (1024×1536, medium quality). The API accepts up to 4 input images; slot layout is fixed:

- `[0]` source frame (structural anchor — PRIMARY; highest weight)
- `[1]` look front/body reference (outfit detail)
- `[2]` look sheet (overview)
- `[3]` look face closeup (weakest weight)

Exception: shot_003 is an extreme low-angle feet-only close-up with no face in frame. The face reference was moved to `[3]` (weakest position) to avoid face-detail bleed into a composition where face is not visible.

Each keyframe was reviewed and approved by the human operator via a dry-run display before the paid API call was executed. This prevents unnecessary API spend on prompts that are structurally wrong.

### Stage 4 — Kling Image-to-Video

Each approved keyframe is submitted to Kling AI image-to-video (`kling-v1-6`, standard mode, 9:16, 5 seconds per clip) with a natural-language video prompt describing the intended motion. Tasks are submitted sequentially with a 2-second gap to avoid rate limiting; polling runs in parallel every 10 seconds until all tasks complete. Clips are downloaded to `outputs/runs/live_test_03_4shots/clips/`.

Motion in all 4 clips is **prompt-level I2V** — Kling animates from the keyframe according to the natural-language video prompt. This is not frame-level pose transfer or skeleton-driven animation. Action intent (walking direction, camera movement, body orientation) is communicated via the video prompt; exact gait, step cadence, and inter-frame pose continuity are not guaranteed.

### Stage 5 — Evaluation

The evaluation stage scores each generated shot on four metrics:
- **Identity consistency** — ArcFace cosine similarity between the IP reference face embedding and the generated keyframe or clip frame
- **Pose sequence similarity** — keypoint distance between the source frame pose and the generated output pose
- **Framing accuracy** — compositional match between source framing and generated output
- **Beat alignment error** — millisecond offset between the reference cut time and the generated cut or clip boundary

Evaluation for the current run (`live_test_03_4shots`) is **pending** — all 4 shots have status `pending`. Keyframes and clips were approved via manual human review; automated metric scoring has not yet been run.

### Stage 6 — Repair Loop

If a shot fails evaluation, the repair decision agent classifies the failure type and selects a repair action:
- Identity drift → raise look reference weight / adjust seed
- Pose mismatch → strengthen pose conditioning / rewrite framing block
- Framing error → rewrite framing prompt
- Beat error → adjust cut timing

Shots that exceed maximum retries without passing are set to `status = needs_human` (terminal state). Repair has not been triggered in this run; it is pending evaluation completion.

---

## C. 5-Track Representation

Each generation unit encodes five orthogonal tracks that together define the target output shot:

| Track | Field | Content | Tool |
|---|---|---|---|
| **1. Visual structure / framing** | `framing` | Shot scale (wide/medium/close-up/extreme), camera angle, subject placement in frame | PySceneDetect + VLM caption |
| **2. Camera motion** | `camera_motion` | One of 12 types: static, push_in, pull_out, pan_left, pan_right, tilt_up, tilt_down, handheld, crane_up, crane_down, zoom_in, zoom_out | Optical flow classifier |
| **3. Character motion** | `character_motion` | Action type (walking, standing, turning, sitting, etc.), direction, intensity | MediaPipe keypoint displacement |
| **4. Timing** | `timing` | Shot start time (s), end time (s), duration (s), nearest beat position, beat alignment offset (ms) | librosa beat tracking |
| **5. Semantic description** | `semantic` | Action summary, expression, gaze, lighting type, environment, prompt fragment | GPT-4o Vision enrichment |

The 5-track schema is the core contribution of the Template Builder stage. It converts heterogeneous analysis outputs (frame-level, time-series, semantic) into a normalised per-shot representation that can be consumed by the prompt builder, the evaluator, and the repair agent independently.

When `track_completeness = full`, all five tracks are populated from their primary source. When `track_completeness = partial`, the camera motion track falls back to a semantic label (`camera_motion_source = semantic_fallback`) because the optical flow classifier did not run. In this run, all 4 shots have `track_completeness = full`.

---

## D. Identity / Look / Scene Separation

The system separates four concerns that are conflated in naive text-prompt-only generation:

**Identity package** — the fixed IP character. Defines physical appearance: face structure, skin tone, build, hair colour. This is invariant across all shots and looks. The identity package is provided as reference images to `gpt-image-1 images.edit` and is never overridden by look or scene selection.

**Look package** — outfit, hairstyle, shoes, silhouette. Defined per look selection (in this run: Look 3 · The Tailored Self — cropped charcoal blazer, white cotton shirt, muted olive tie, wide faded blue denim trousers, black leather oxford shoes). The look package is independent of identity and of the reference video's original costume. The source subject may be wearing anything; the look package replaces the outfit entirely.

**Scene mode** — controls how the background is handled:
- `preserve_reference_scene` (used in this run): the background, lighting, environment, and atmosphere are extracted from the source frame and preserved in the generated output. The generated character appears in the same location and lighting as the reference.
- `replace_with_selected_scene`: the background is replaced with a selected scene package (e.g., urban rooftop, dark studio). This mode is implemented but was not used in this run.

**Source frame** — used exclusively for structural conditioning: crop, camera angle, body orientation, subject scale, framing, and pose. The source frame is always slot `[0]` in the `images.edit` call (highest weight). It does not provide identity or costume information to the generated output; those come from the IP package and look package respectively.

### Why this separation matters: the prompt contamination bug

In an earlier iteration, a hardcoded description in `config.py` referred to the look4b character as "a bride in a white wedding gown with cathedral veil." This description was being injected into every keyframe prompt regardless of the selected look. When the pipeline selected Look 3 (tailored outfit), the generation was still receiving bridal costume language, producing outputs in white dresses rather than the tailored blazer.

The fix required three changes: (1) removing all hardcoded character/costume descriptions from `config.py`; (2) adding a look resolver that reads the selected look package from disk and injects only its content; and (3) adding a forbidden-word guard that scans the assembled KEYFRAME_PROMPT string before any API call and blocks on terms associated with the contaminated look (bride, bridal, wedding, veil, cathedral veil). The guard scans only the positive prompt; a separate NEGATIVE_PROMPT string (used for reference/logging only, not passed to the API) is explicitly excluded from the scan to prevent false positives on exclusion clauses.

---

## E. Iteration History

### Iteration 1 — Initial baseline (gpt-image-1-mini)

The first end-to-end test used `gpt-image-1-mini` (lower-cost model) as a baseline to verify pipeline connectivity before committing to higher-cost generation. The run processed 4 shots. Automated evaluation results:

| Metric | Result |
|---|---|
| Total shots | 4 |
| Passed (auto) | 2 |
| Failed → needs_human | 2 |
| Total repair attempts | 10 |

Diagnosis: identity drift across shots. The mini model produced variable face renderings with inconsistent feature sharpness. The repair loop correctly detected the drift (ArcFace cosine below threshold) and escalated to `needs_human` after max retries.

This test established that: (a) the pipeline connectivity was correct end-to-end; (b) model tier significantly affects identity consistency; (c) the repair loop functioned as designed.

### Iteration 2 — Bug discovery

After the baseline, a systematic audit of prompts and state revealed several compounding bugs:

**Bug 1 — Hardcoded bridal description in config.py.** The character description was hardcoded with bridal costume language from an earlier project state, contaminating every generated prompt regardless of look selection.

**Bug 2 — Stale look4b references.** Several pipeline functions still referenced a deprecated look identifier (`look4b`) rather than reading from `selected_look_id`.

**Bug 3 — Selected look not connected to generation.** The look selector UI stored `selected_look_id` in state but the keyframe prompt builder did not read from it. All keyframes were generated with a fallback character description, not the selected look's outfit data.

**Bug 4 — Source frame outfit influence.** With no explicit look constraint, `gpt-image-1` was partially reproducing the source subject's costume (a white sheer beach dress) rather than Look 3's tailored outfit.

**Bug 5 — Stale scene prompt.** The `scene_prompt` field in state still contained "urban rooftop" from a previous run's manual config, not from the reference video analysis. This caused the generation to place the character on a rooftop despite the reference video depicting a beach at sunset.

### Iteration 3 — Fixes applied

All five bugs were resolved:

1. Removed all hardcoded character/costume strings from `config.py` and `api_gen.py`.
2. Replaced stale look4b references with dynamic look resolver reading from `selected_look_id`.
3. Wired `selected_look_id` → look package folder → look reference images into the `images.edit` input list.
4. Added source frame as slot `[0]` (structural anchor only) with explicit prompt instruction to preserve framing and replace only identity and outfit.
5. Added `scene_mode = preserve_reference_scene` and set `active_scene_prompt` from the reference video's analysed environment (beach, sunset, coastal).
6. Added the forbidden-word guard (`check_forbidden`) scanning the full KEYFRAME_PROMPT string before any API call.
7. Added a dry-run display mode: the assembled prompt, image slots, and output path are printed and must receive manual approval before the API call executes.

### Iteration 4 — Per-shot keyframe generation (live_test_03_4shots)

After bug fixes, keyframes were generated one shot at a time. Each shot required visual inspection of the source frame, a dry-run prompt review, and explicit human approval before the API call was made.

**shot_001 — Over-shoulder medium close-up**
1 attempt. The v3 prompt (preserve scene, over-shoulder MCU, character turns head back toward camera) was approved on first review. Output: preserved seaside sunset background, Look 3 outfit applied, face visible in over-shoulder profile.

**shot_002 — Wide full-body back-view walking shot**
2 attempts. Attempt 1 was blocked before the API call by the forbidden-word guard: the GUARD section of the prompt contained negative instructions listing bridal terms ("Do not add bride, bridal, wedding, veil"), and the guard correctly flagged the word "bride" in the positive prompt string. Fix: the negative instruction was replaced with a neutral formulation ("Do not copy the source subject's outfit, hairstyle, or styling. Keep the selected tailored look only."). v2 prompt: natural-realism language (removed "cinematic", "polished", "fashion editorial"; added documentary-like realism framing). Output approved.

**shot_003 — Extreme low-angle feet close-up**
2 attempts. Attempt 1 prompt described a face-forward turning-toward-camera pose — incorrect. Source frame inspection revealed an extreme low-angle shot at ground level showing only bare feet and lower legs, no upper body in frame. Prompt was rewritten from scratch to describe lower legs and feet only. Image slot order adjusted: face reference moved to `[3]` (weakest weight) since face is not in frame. v2 output: denim trouser hem and black oxford shoes on wet sand, correct framing.

**shot_004 — Wide side-profile walking shot**
3 attempts. Attempt 1 (v1): prompt too generic; model defaulted to a black business blazer and straight trousers. Attempt 2 (v2): revised look description, still too generic; model produced office-uniform silhouette. Attempt 3 (v3): prompt restructured with explicit labelled subsections (BLAZER:, TIE:, TROUSERS:), strong differentiating language ("charcoal means dark grey, NOT black"), negative anchors in the positive prompt ("NOT slim fit, NOT straight leg, NOT office trousers"), and look3_front.png moved to slot `[1]` (higher weight). Look 3 outfit rendered correctly.

### Iteration 5 — Kling I2V animation

All 4 approved keyframes were submitted to Kling AI (`kling-v1-6`, std, 9:16, 5s per clip) via `run_kling_i2v.py`. Prior to submission, the video prompts in `project_state.json` were audited and corrected: all 4 had defaulted to "standing, composed posture" from an earlier state schema — incorrect for walking shots. Corrected video prompts were written directly into state before submission.

Four clips were generated successfully. The assembled video is 20.4 seconds (4 × 5s clips, no audio). Evaluation (automated metric scoring) has not yet been run on this output.

---

## F. Experiments

### Experiment 1 — Schema Smoke Test

**Objective:** Verify that the 5-track schema, generation unit pipeline, and prompt builder produce valid and complete output across three distinct reference video types, without running generation.

**Inputs:**
- `test_01`: single-take video, static camera
- `test_02`: single-take video with camera push and pan
- `test_03`: 4-shot multi-shot edit (the production run reference)

**Procedure:** For each test video, run full analysis (shot detection, beat tracking, camera motion, pose, semantic enrichment), generate generation units, build prompt blocks, and inspect output schema.

**Results:**

| Field | test_01 | test_02 | test_03 |
|---|---|---|---|
| Shots detected | 1 | 1 | 4 |
| Generation units built | 1 | 1 | 4 |
| prompt_path | 5track_local_rebuild | 5track_local_rebuild | 5track_local_rebuild |
| track_completeness | full | full | full |
| camera_motion_source | optical_flow | optical_flow | optical_flow |
| Result | PASS | PASS | PASS |

**Conclusion:** The schema pipeline handles single-take and multi-shot inputs without error. All units achieved full 5-track completeness with optical-flow camera motion.

### Experiment 2 — Production Keyframe Generation Test

**Objective:** Generate Look 3 keyframes for all 4 shots of the official reference video under `scene_mode = preserve_reference_scene`, with the corrected pipeline.

**Inputs:**
- Reference: `test/test_03_multishot_edit_4shots.mp4`
- IP character: young woman, mid-twenties, light olive skin, almond eyes
- Look: Look 3 · The Tailored Self (charcoal blazer, olive tie, wide denim trousers, black oxfords)
- scene_mode: preserve_reference_scene
- Model: gpt-image-1 / images.edit / 1024×1536 / medium

**Results:**

| Shot | Attempts | Source structure | Look applied | Scene preserved | Result |
|---|---|---|---|---|---|
| shot_001 | 1 | Yes — over-shoulder MCU preserved | Yes | Yes — beach sunset | PASS |
| shot_002 | 2 | Yes — back-view framing preserved | Yes | Yes — beach sunset | PASS |
| shot_003 | 2 | Yes — low-angle ground-level preserved | Partial (lower body only) | Yes — wet sand shoreline | PASS |
| shot_004 | 3 | Yes — wide side-profile preserved | Yes | Yes — beach with sun and headland | PASS |

**Limitations:** Identity consistency across all 4 shots has been assessed by human visual inspection only. Automated ArcFace identity scoring has not yet been run. The face in shot_003 is not in frame (correct for the shot type); cross-shot face consistency cannot be verified from this shot.

**Conclusion:** All 4 keyframes produced acceptable output after between 1 and 3 attempts. Source frame structural conditioning was effective; look conditioning required explicit subsection labelling for shot_004 to override the model's genre defaults.

### Experiment 3 — Kling I2V Animation Test

**Objective:** Animate all 4 approved keyframes using Kling I2V and assess motion quality.

**Inputs:** 4 approved keyframes from Experiment 2
**Model:** kling-v1-6, std mode, 9:16, 5s per clip, cfg_scale=0.5

**Results:**

| Shot | Keyframe used | Video prompt intent | Clip generated | Motion assessment |
|---|---|---|---|---|
| shot_001 | shot_001_keyframe_look3_preserve_scene_test.png | Head turn toward camera, subtle push-in | Yes (4.9MB) | Subtle motion, head movement present |
| shot_002 | shot_002_keyframe_look3_preserve_scene.png | Back-view walk away from camera | Yes (4.3MB) | Walking motion visible |
| shot_003 | shot_003_keyframe_look3_preserve_scene.png | Feet walking through wet sand | Yes (7.5MB) | Foot/leg motion present |
| shot_004 | shot_004_keyframe_look3_preserve_scene.png | Side-profile walk toward frame-left | Yes (7.5MB) | Walking motion visible |

All 4 clips generated without error. No additional OpenAI calls were made during the Kling run. No repair was triggered.

**Limitations:** Motion follows prompt-level action intent. Kling I2V is an image-to-video model; it does not receive skeleton data or explicit pose sequences. Exact gait, step cadence, and per-frame body position are not controlled. The system does not perform exact frame-level motion transfer.

**Conclusion:** Usable demo output produced. All 4 clips playable and consistent with intended action. Assembly into a 20.4s final video (ffmpeg copy, no re-encode) completed successfully.

---

## G. Results Table

### Shot-level results (live_test_03_4shots)

| shot_id | Shot type | Framing | Duration | Camera motion | Character action intent | Keyframe | Clip | Keyframe status | Eval status |
|---|---|---|---|---|---|---|---|---|---|
| shot_001 | Over-shoulder MCU | medium | 2.40s | push_in | Turns head back toward camera | shot_001_keyframe_look3_preserve_scene_test.png | shot_001_look3.mp4 | Approved (1 attempt) | Pending |
| shot_002 | Back-view walk | wide | 2.27s | static | Walks away from camera along beach | shot_002_keyframe_look3_preserve_scene.png | shot_002_look3.mp4 | Approved (2 attempts) | Pending |
| shot_003 | Low-angle feet | unknown (extreme CU) | 2.13s | handheld | Walking stride, feet through wet sand | shot_003_keyframe_look3_preserve_scene.png | shot_003_look3.mp4 | Approved (2 attempts) | Pending |
| shot_004 | Side-profile walk | wide | 1.10s | handheld | Walks sideways toward frame-left | shot_004_keyframe_look3_preserve_scene.png | shot_004_look3.mp4 | Approved (3 attempts) | Pending |

### Baseline test results (earlier gpt-image-1-mini run — for comparison)

| Metric | Value |
|---|---|
| Total shots | 4 |
| Passed (auto evaluation) | 2 |
| Failed → escalated to needs_human | 2 |
| Total repair attempts across all shots | 10 |
| Model | gpt-image-1-mini |
| Evaluation | Automated (ArcFace identity scoring active) |

---

## H. Limitations

The following limitations apply to the current implementation and should be stated clearly in any academic or demonstration context.

1. **Identity consistency depends on reference image conditioning.** The system uses `gpt-image-1 images.edit` with up to 4 reference images for IP conditioning. Identity consistency across shots is not guaranteed. Face embedding similarity varies depending on shot framing, pose angle, and lighting. Stronger IP conditioning (LoRA fine-tuning, IP-Adapter) would improve cross-shot consistency but requires local GPU infrastructure not available in the current cloud-API-only pipeline.

2. **Exact gait and frame-level motion transfer is not performed.** Kling I2V generates motion from a keyframe and a natural-language video prompt. The system communicates action intent (walking direction, camera movement, body orientation) but does not transmit skeleton sequences, optical flow fields, or frame-level pose data to the video model. Exact gait reproduction, specific step timing, and inter-frame pose continuity are not controlled.

3. **Camera motion and character motion are estimated heuristically.** The optical-flow camera motion classifier uses dense optical flow aggregated over shot segments. It classifies camera motion into discrete types (push_in, static, handheld, etc.) but does not compute exact camera trajectory parameters. Character motion type is inferred from MediaPipe keypoint displacement and may misclassify ambiguous actions.

4. **Pose and framing evaluation is partial.** The evaluation stage computes ArcFace identity similarity and beat alignment error. Pose sequence similarity (keypoint distance between source and generated frame) and framing accuracy are implemented in the schema but depend on additional tooling (DWPose extraction from generated outputs) that has not been run on this batch.

5. **Mode B is secondary.** Mode B is implemented and produces valid storyboard JSON that feeds into the shared generation loop. However, it has not been tested with the same rigour as Mode A and is presented as a secondary demonstration of the pipeline's input-agnosticism rather than an equally validated path.

6. **Human review is required before final output.** The system includes mandatory human-in-the-loop review gates at the storyboard approval stage and before each keyframe generation. The repair loop can reduce the number of shots requiring intervention, but `needs_human` terminal states always require human decision. The system does not claim to be fully automatic.

7. **No audio.** The current pipeline produces silent video. The reference audio is used for beat analysis only and is never included in output, in accordance with copyright-aware practice for research use of third-party reference material.

---

## I. Correct Wording for Claims

The following language should be used in all academic, demonstration, and public-facing descriptions:

**Use:**
- "The system preserves reference shot structure and action intent, but does not perform exact frame-level motion transfer."
- "Identity consistency across shots is maintained through reference image conditioning; consistency is assessed by ArcFace cosine similarity and visual inspection."
- "Camera motion type is estimated from optical flow analysis; exact camera trajectory is not computed."
- "The evaluation and repair loop reduces the number of shots requiring manual intervention; it does not guarantee fully automatic final quality."
- "The system extracts formal structure (shot cuts, camera motion, timing, framing, pose) from the reference video. No reference content is reproduced in the output."

**Do not claim:**
- Exact motion transfer or skeleton-driven animation
- Perfect or guaranteed identity consistency
- Fully automatic final quality without human review
- Exact gait reproduction
- Frame-accurate synchronisation between reference and output

---

## J. Artifacts Generated (live_test_03_4shots)

### Keyframe images

| File | Size | Location |
|---|---|---|
| shot_001_keyframe_look3_preserve_scene_test.png | 2.0 MB | `outputs/runs/live_test_03_4shots/keyframes/` |
| shot_002_keyframe_look3_preserve_scene.png | 1.9 MB | `outputs/runs/live_test_03_4shots/keyframes/` |
| shot_003_keyframe_look3_preserve_scene.png | 2.0 MB | `outputs/runs/live_test_03_4shots/keyframes/` |
| shot_004_keyframe_look3_preserve_scene.png | 2.1 MB | `outputs/runs/live_test_03_4shots/keyframes/` |

### Video clips

| File | Size | Location |
|---|---|---|
| shot_001_look3.mp4 | 4.9 MB | `outputs/runs/live_test_03_4shots/clips/` |
| shot_002_look3.mp4 | 4.3 MB | `outputs/runs/live_test_03_4shots/clips/` |
| shot_003_look3.mp4 | 7.5 MB | `outputs/runs/live_test_03_4shots/clips/` |
| shot_004_look3.mp4 | 7.5 MB | `outputs/runs/live_test_03_4shots/clips/` |

### Analysis outputs

| File | Description | Location |
|---|---|---|
| shot_001_pose_overlay.png (926KB) | MediaPipe pose skeleton overlaid on source frame | `analysis/pose_overlay/` |
| shot_002_pose_overlay.png (1.0MB) | MediaPipe pose skeleton overlaid on source frame | `analysis/pose_overlay/` |
| shot_003_pose_overlay.png (1.4MB) | MediaPipe pose skeleton overlaid on source frame | `analysis/pose_overlay/` |
| shot_004_pose_overlay.png (1.4MB) | MediaPipe pose skeleton overlaid on source frame | `analysis/pose_overlay/` |

### Final deliverables

| File | Description | Location |
|---|---|---|
| `final_look3_reference_driven_demo.mp4` | 24MB · 768×1152 · 30fps · 20.4s assembled final video | `final/` |
| `keyframe_contact_sheet.png` | 4-panel approved keyframe contact sheet | `final/` |
| `clip_review_sheet.png` | First/mid/last frame per clip, 4-row review grid | `final/` |
| `run_summary.md` | Full run log with config, paths, and pipeline notes | `final/` |
| `decision_log.json` | Per-shot decision log: attempts, prompts, prompts used, Kling status | `final/` |

### State files

| File | Description |
|---|---|
| `project_state.json` | Central pipeline state file: all shots, generation briefs, evaluation state, config |

---

## K. Dissertation-Ready Summary

### Methodology paragraph

This dissertation presents a reference-driven agentic video generation system for producing character-consistent short-form vertical video. The system decomposes a reference video into a structured 5-track storyboard representation — encoding visual framing, camera motion, character motion, timing, and semantic description per shot — using deterministic tools (PySceneDetect for shot detection, librosa for beat tracking, MediaPipe for pose estimation, and an optical-flow classifier for camera motion type). This structured representation, stored as a normalised JSON schema (`generation_units`), is passed to an IP-conditioned keyframe generation stage using OpenAI's `gpt-image-1 images.edit` API, which receives the source frame as a structural anchor alongside character identity and look reference images. Each keyframe is then animated using Kling AI's image-to-video model, producing individual 5-second 9:16 clips that are assembled into a final output video. The system implements an automated evaluation and repair loop that scores each shot on identity consistency (ArcFace cosine similarity), pose similarity, framing accuracy, and beat alignment; shots that fail scoring thresholds are diagnosed and regenerated with targeted prompt or conditioning adjustments, up to a maximum retry count. Human review gates are placed at the storyboard approval and keyframe approval stages to ensure correctness before committing to paid API generation.

### Evaluation findings paragraph

Evaluation of the Mode A pipeline on a 4-shot beach-walk reference video (7.9s, 30fps, 123bpm) demonstrated successful end-to-end pipeline execution. Shot detection, 5-track unit construction, and prompt generation all completed with full track completeness and optical-flow camera motion classification for all four shots. Keyframe generation required between 1 and 3 attempts per shot; the main source of iteration was look conditioning specificity, particularly for shots where the model defaulted to generic costume categories (business suit, straight trousers) rather than the target tailored look. Kling image-to-video animation produced four usable 5-second clips consistent with the intended action per shot; the assembled final video is 20.4 seconds. The system does not perform exact frame-level motion transfer; motion follows prompt-level action intent. Identity consistency across shots was approved by human visual review; automated ArcFace scoring is pending. An earlier baseline test using the lower-cost `gpt-image-1-mini` model produced 2/4 passing shots with 10 repair attempts, establishing that model tier is a significant factor in identity consistency and that the repair loop correctly escalates persistent failures to `needs_human` status. A prompt contamination bug was identified and resolved during development: a hardcoded bridal character description in the configuration layer was injecting incorrect costume language into all generated prompts regardless of look selection, and was fixed by adding a look resolver, removing hardcoded strings, and implementing a forbidden-word guard on all keyframe prompts.
