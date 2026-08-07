# Technical Iteration Log
## Mode A v0.8.1 — live_test_03_4shots

**Project:** Reference-Driven Agentic Short-Form Video Generation System
**Scope:** All development iterations from initial baseline to v0.8.1 logic freeze
**Date of final run:** 2026-07-17

---

## Iteration 0 — Schema and analysis pipeline

**Status:** PASS

Established the core analysis pipeline:

- PySceneDetect: shot detection with beat-snapping (snap cut to nearest librosa beat within tolerance; keep original if no beat is close enough)
- librosa: beat tracking, BPM extraction
- MediaPipe: pose keypoint estimation per shot, pose overlay generation
- Optical-flow classifier: dense optical flow → 12-type camera motion classification
- GPT-4o Vision: per-shot semantic enrichment (action, expression, lighting, environment, prompt fragment)
- 5-track generation unit schema: framing | camera_motion | character_motion | timing | semantic

Verified on three test videos:
- test_01 (single-take, static camera): 1 shot, track_completeness=full
- test_02 (single-take, camera push/pan): 1 shot, track_completeness=full
- test_03 (4-shot multi-shot edit): 4 shots, track_completeness=full for all

Prompt path: `5track_local_rebuild` for all units.

---

## Iteration 1 — Baseline generation test (gpt-image-1-mini)

**Model:** gpt-image-1-mini
**Status:** PARTIAL PASS — pipeline connectivity confirmed, identity consistency insufficient

End-to-end pipeline test with a lower-cost model to verify connectivity before committing to full-cost generation. Automated evaluation ran (ArcFace identity scoring active).

Results:
- Total shots: 4
- Passed: 2
- Failed → escalated to needs_human: 2
- Total repair attempts: 10

Diagnosis: The mini model produced variable face renderings across shots. ArcFace cosine similarity fell below the pass threshold (≥0.80) on 2 shots. The repair loop ran correctly — detected failure, applied seed_change repair, re-generated, and correctly escalated to `needs_human` after max retries.

Conclusion: Pipeline architecture confirmed working end-to-end. Model tier is a significant determinant of identity consistency. Upgrade to full gpt-image-1 required.

---

## Iteration 2 — Bug audit

**Status:** BLOCKED — multiple bugs discovered

Following the mini model test, a systematic prompt and state audit identified five compounding bugs.

### Bug 1: Hardcoded bridal character description in config.py

`config.py` contained a hardcoded character description string that referenced look4b: "a bride in a white wedding gown with cathedral veil." This string was injected into every keyframe prompt via `_build_prompt_blocks`, overriding any look selection. All generated outputs had bridal costume regardless of selected look.

**Fix:** Removed all hardcoded costume and character description strings from `config.py` and `api_gen.py`. Character identity description now reads from the IP character package only. Costume description reads from the selected look package only.

### Bug 2: Stale look4b references

Several functions in the prompt builder and evaluator still referenced the deprecated identifier `look4b` via hardcoded string comparisons. The selected look (`look_3_tailored_self`) was not recognised.

**Fix:** Replaced all hardcoded look identifiers with dynamic resolution from `state.config.selected_look_id`.

### Bug 3: Selected look not connected to generation

The look selector stored `selected_look_id` in state, but `_build_prompt_blocks` did not read from this field. The look resolver function existed but was not called.

**Fix:** Wired look resolver into the prompt build path. Resolver reads the look folder, loads outfit description from look metadata, and returns look reference image paths (`look3_front.png`, `look3_sheet.png`, `look3_closeup.png`). These are passed as images `[1]`, `[2]`, `[3]` in `images.edit`.

### Bug 4: Source frame outfit bleeding into generation

Without explicit look constraints, `gpt-image-1` partially reproduced the source subject's costume (white sheer beach dress) in the output. The source frame was not tagged as structural-only.

**Fix:** Added explicit prompt instruction: "The first image is the structural and compositional reference. Treat it as a locked frame. Copy its exact body position, walking pose, crop, subject scale, camera distance, framing, and background without modification. Only replace the person's identity and outfit." Source frame fixed to slot `[0]` (highest weight) in all generation scripts.

### Bug 5: Stale scene_prompt ("urban rooftop") in state

The `scene_prompt` field in `project_state.json` contained "urban rooftop, city skyline" from a previous manual config session. This caused the generation to place the character on a rooftop despite the reference video showing a beach at sunset.

**Fix:** Added `scene_mode = preserve_reference_scene` to run config. `active_scene_prompt` now set from the reference video's analysed environment (beach, sunset, coastal atmosphere), not from a manually entered config field. Added explicit "SCENE" prompt block that reads from `active_scene_prompt`.

---

## Iteration 3 — Forbidden-word guard

**Status:** IMPLEMENTED

After fixing look contamination, a new risk emerged: negative instructions embedded in the positive prompt (e.g., "Do not add bride, bridal, wedding, veil") caused the prompt guard to false-positive on the words it was trying to exclude.

Root cause: The initial guard implementation scanned the entire prompt string including exclusion clauses. A prompt that correctly said "Do not generate bridal costume" was blocked because "bridal" appeared in the string.

**Fix:**
- Separated positive prompt (`KEYFRAME_PROMPT`) and negative reference string (`NEGATIVE_PROMPT`) into distinct variables
- `NEGATIVE_PROMPT` is for logging and reference only — it is never passed to the API and is explicitly excluded from the guard scan
- Guard (`check_forbidden`) scans only `KEYFRAME_PROMPT`
- Replacement clause for negative instructions uses neutral language: "Do not copy the source subject's outfit, hairstyle, or styling. Keep the selected tailored look only."

Shot_002 was the first to trigger this bug. The API call was blocked before any cost was incurred. The prompt was corrected and re-run.

---

## Iteration 4 — Dry-run approval workflow

**Status:** IMPLEMENTED (procedural, not code change)

To prevent API spend on structurally incorrect prompts, a dry-run workflow was established:

1. Inspect source frame visually before writing any prompt
2. Print assembled prompt, image slot list, output path — do not call API
3. Human operator reviews dry-run output
4. On explicit approval: run API call

This was particularly important for shot_003 (low-angle feet close-up) where the initial prompt incorrectly described a face-forward composition. The dry-run revealed the mismatch before any API call was made. The source frame was inspected, confirmed as an extreme low-angle shot with no face in frame, and the prompt was rewritten from scratch.

All 4 shots in live_test_03_4shots followed this workflow.

---

## Iteration 5 — Per-shot keyframe generation (live_test_03_4shots)

### shot_001 — Over-shoulder medium close-up

| Attempt | Outcome | Notes |
|---|---|---|
| v3 | APPROVED | Preserve scene, over-shoulder MCU. Look 3 applied. Beach sunset preserved. |

1 attempt total.

### shot_002 — Wide full-body back-view walking shot

| Attempt | Outcome | Notes |
|---|---|---|
| v1 | BLOCKED (guard) | GUARD section contained "Do not add bride, bridal, wedding" — guard correctly flagged "bride" in positive prompt string |
| v2 | APPROVED | Negative instructions replaced with neutral language. Natural-realism language added (removed "cinematic", "polished", "editorial fashion"). |

2 attempts total (1 blocked before API call, 1 successful).

### shot_003 — Extreme low-angle feet close-up

| Attempt | Outcome | Notes |
|---|---|---|
| v1 | REJECTED (dry-run) | Prompt described face-forward pose with smile and turn toward camera — completely wrong for source frame |
| v2 | APPROVED | Source frame inspected first. Confirmed: ground-level angle, only bare feet and lower legs visible, no upper body. Prompt rewritten from scratch as lower-body-only shot. Face reference moved to slot [3] (weakest weight). |

2 attempts total (1 dry-run reject before API call, 1 successful).

### shot_004 — Wide side-profile walking shot

| Attempt | Outcome | Notes |
|---|---|---|
| v1 | REJECTED (visual) | Generic black business blazer, straight-leg trousers. Model defaulted to business-suit category. |
| v2 | REJECTED (visual) | Stronger look description added, still produced office-uniform silhouette. Olive tie rendered as black. |
| v3 | APPROVED | Prompt restructured with labelled subsections (BLAZER:, TIE:, TROUSERS:). Added strong differentiators ("charcoal means dark grey, NOT black"; "NOT slim fit, NOT straight leg, NOT office trousers"). look3_front.png moved to slot [1] (higher weight than in v1/v2). Look 3 rendered correctly. |

3 attempts total.

---

## Iteration 6 — Video prompt audit and Kling I2V

Before Kling submission, all 4 video prompts in `project_state.json` were audited. Discovery: all 4 had `video_prompt = "standing, composed posture"` — a stale default from an earlier schema version, incorrect for all 4 walking shots.

**Fix:** All 4 video prompts corrected directly in state before submission:
- shot_001: over-shoulder head turn, subtle push-in, minimal motion
- shot_002: back-view walk away from camera along beach
- shot_003: feet and lower legs walking through wet sand
- shot_004: side-profile walk toward frame-left, slight handheld movement

Kling run: `run_kling_i2v.py`, local execution (no sandbox API calls). All 4 clips generated successfully.

| Shot | Clip file | Size | Duration |
|---|---|---|---|
| shot_001 | shot_001_look3.mp4 | 4.9MB | 5s |
| shot_002 | shot_002_look3.mp4 | 4.3MB | 5s |
| shot_003 | shot_003_look3.mp4 | 7.5MB | 5s |
| shot_004 | shot_004_look3.mp4 | 7.5MB | 5s |

---

## Iteration 7 — Final assembly

Four 5-second Kling clips (all h264, 768×1152, 30fps) concatenated with `ffmpeg -f concat -c copy` (no re-encode). Output: `final/final_look3_reference_driven_demo.mp4`, 20.4s, 24MB, silent.

---

## Current status (as of 2026-07-17)

| Stage | Status |
|---|---|
| Reference analysis (5-track) | Complete |
| Shot detection (4 shots) | Complete |
| Camera motion classification | Complete (optical_flow) |
| Pose overlay generation | Complete |
| Source frame storyboard | Complete |
| IP keyframe generation | Complete (all 4 approved) |
| Kling I2V animation | Complete (all 4 clips) |
| Final video assembly | Complete (20.4s) |
| Automated evaluation (ArcFace / pose / beat) | Pending |
| Repair loop | Not triggered (pending evaluation) |
| Human evaluation of clips | Pending |

---

## Bug summary

| # | Bug | Where | Impact | Fix |
|---|---|---|---|---|
| 1 | Hardcoded bridal description | config.py | All outputs generated as bridal costume | Removed; replaced with dynamic look resolver |
| 2 | Stale look4b references | prompt builder, evaluator | Selected look not applied | Dynamic lookup from selected_look_id |
| 3 | Look resolver not called | api_gen.py | Look package bypassed | Wired look resolver into prompt build path |
| 4 | Source frame outfit bleeding | images.edit slot layout | Source costume reproduced in output | Source frame to slot [0] with structural-only instruction |
| 5 | Stale scene_prompt (urban rooftop) | project_state.json | Wrong scene in generated outputs | scene_mode = preserve_reference_scene; active_scene_prompt from reference analysis |
| 6 | Forbidden-word guard false positive | check_forbidden() | Blocked valid prompts containing exclusion clauses | Separated positive/negative prompt strings; guard scans positive only |
| 7 | Stale video prompts (standing, composed posture) | project_state.json | Wrong motion intent sent to Kling | Corrected all 4 video prompts before Kling submission |
