# Evaluation Report — Mode A v0.8.1
## live_test_03_4shots · Reference-Driven Agentic Short-Form Video Generation System

**Institution:** NCCA, Bournemouth University · MSc AI for Media
**Date:** 2026-07-17
**Pipeline version:** Mode A v0.8.1 (logic freeze)

---

## 1. Experiment Overview

| Field | Value |
|---|---|
| Pipeline mode | Mode A — Reference Video |
| Pipeline version | v0.8.1 (logic freeze) |
| Run ID | live_test_03_4shots |
| Reference video | `test/test_03_multishot_edit_4shots.mp4` — 4-shot beach sunset sequence, 7.92s, 30fps, 123bpm |
| IP character | Young woman, mid-twenties, light olive skin, almond eyes, slender build |
| Selected look | Look 3 · The Tailored Self — cropped charcoal blazer, white shirt, olive tie, wide faded denim trousers, black oxford shoes |
| scene_mode | preserve_reference_scene |
| Keyframe model | gpt-image-1 / images.edit / 1024×1536 / medium |
| Video model | Kling v1.6 / std / 9:16 / 5s per clip |
| Final output | `final/final_look3_reference_driven_demo.mp4` — 20.4s, 768×1152, 30fps, 24MB |

---

## 2. Pipeline Stages Completed

| Stage | Tool / Method | Result |
|---|---|---|
| Reference analysis | PySceneDetect (cuts) · librosa (beats) · optical flow (camera motion) · MediaPipe (pose) · GPT-4o Vision (semantic) | Complete |
| Shot detection | 4 shots detected from 7.92s reference | Complete |
| 5-track generation units | framing · camera_motion · character_motion · timing · semantic — all 4 units: track_completeness=full | Complete |
| Keyframe generation | gpt-image-1 / images.edit · 4 input images per shot (source frame + look refs) | Complete — all 4 approved |
| Kling I2V animation | kling-v1-6 / std / 9:16 / 5s — 4 clips | Complete — all 4 generated |
| Final assembly | ffmpeg concat / copy — no re-encode | Complete — 20.4s video |
| Automated evaluation | ArcFace identity (post-hoc diagnostic, run later) · pose similarity/beat alignment (not computed for this run) | Partial — see §4 below |
| Repair loop | Automatic Stage-4/5 loop | Not triggered — this run used human-gated review, not the automatic loop |

---

## 3. Per-Shot Results

| shot_id | Reference structure | Keyframe path | Clip path | Keyframe attempts | Status | Notes |
|---|---|---|---|---|---|---|
| shot_001 | Over-shoulder MCU · push_in camera · 2.40s | `keyframes/shot_001_keyframe_look3_preserve_scene_test.png` | `clips/shot_001_look3.mp4` | 1 | Approved · ArcFace post-hoc = 0.374 | Look 3 applied · beach sunset preserved · over-shoulder framing maintained |
| shot_002 | Wide back-view walk · static camera · 2.27s | `keyframes/shot_002_keyframe_look3_preserve_scene.png` | `clips/shot_002_look3.mp4` | 2 | Approved · ArcFace n/a (no face) | Attempt 1 blocked by forbidden-word guard (pre-API) · v2 approved |
| shot_003 | Extreme low-angle feet CU · handheld · 2.13s | `keyframes/shot_003_keyframe_look3_preserve_scene.png` | `clips/shot_003_look3.mp4` | 2 | Approved · ArcFace n/a (no face) | Attempt 1 dry-run rejected (wrong composition) · v2 rewritten after source frame inspection |
| shot_004 | Wide side-profile walk · handheld · 1.10s | `keyframes/shot_004_keyframe_look3_preserve_scene.png` | `clips/shot_004_look3.mp4` | 3 | Approved · ArcFace post-hoc = 0.227 | 3 attempts required to achieve correct look (blazer/tie/trousers specificity) |

---

## 4. Evaluation Findings

**Shot structure preserved.** All 4 keyframes maintain the framing, camera angle, body scale, and compositional layout of the reference source frame. The source frame is used as the primary structural anchor (slot `[0]` in `images.edit`); body position, crop, and camera distance are preserved.

**Scene continuity preserved.** `scene_mode = preserve_reference_scene` was applied for all shots. The beach sunset environment, wet sand, warm amber lighting, and ocean horizon are consistently rendered across all 4 keyframes. No stale scene prompts were injected.

**Look 3 applied across shots.** The tailored outfit (charcoal blazer, olive tie, wide denim trousers, black oxfords) is present in all 4 keyframes. Shot_004 required 3 attempts due to model default bias toward generic business-suit rendering; the issue was resolved by restructuring the prompt with labelled subsections and stronger negative anchors.

**Prompt-level I2V produced usable motion.** All 4 Kling clips animate from the approved keyframe according to the natural-language video prompt. Walking motion, head turns, and leg movement are visible and consistent with the intended action per shot. Clips were assembled into a 20.4s final video without re-encoding.

**Exact gait and frame-level motion transfer are not guaranteed.** The system does not transmit skeleton sequences, optical flow fields, or per-frame pose data to Kling. Motion follows prompt-level action intent; step cadence, exact stride length, and inter-frame body position are not controlled.

---

## 5. Limitations

1. **Identity consistency depends on image-model reference conditioning.** Cross-shot face consistency was approved by human visual review at generation time. ArcFace cosine similarity was subsequently computed as a **post-hoc diagnostic** (not an in-loop acceptance gate): shot_001 = 0.374, shot_004 = 0.227, mean (face-visible shots) = 0.301; shot_002 and shot_003 are back/lower-body framings with no face in shot, so ArcFace is n/a for those. Higher is closer. Stronger IP conditioning (LoRA, IP-Adapter) would improve consistency but requires local GPU infrastructure.

2. **Exact gait and frame-level motion transfer is not guaranteed.** Kling I2V is a prompt-conditioned image-to-video model, not a skeleton-driven or optical-flow-conditioned system. Action intent is communicated via natural language; exact motion reproduction is not performed.

3. **Camera motion and character motion are estimated heuristically.** The optical-flow classifier categorises camera motion into discrete types from aggregated flow vectors. Character motion type is inferred from MediaPipe keypoint displacement. Neither provides exact trajectory data.

4. **Pose and framing evaluation is partial.** Beat-alignment and pose-similarity scoring are implemented in code (`stage4_evaluate.py`) but were not exercised as an in-loop acceptance gate on this run. ArcFace identity scoring was run post-hoc, as noted above. Framing accuracy is assessed visually.

5. **Human review is still required before final output.** The system includes mandatory human-in-the-loop gates at storyboard approval and keyframe approval. The repair loop reduces manual intervention but does not eliminate it. Shots escalated to `needs_human` require human decision before the pipeline can proceed.

---

## 6. Claim Clarity

> **"The system preserves reference shot structure and action intent, but does not perform exact frame-level motion transfer."**

This sentence should accompany any demonstration of this system. The pipeline extracts formal structure (shot cuts, camera motion type, framing, body orientation, timing) from the reference video and uses it to condition generation. It does not replicate frame-level visual content, exact gait, or precise motion trajectories. All reference video content is used for structural analysis only and does not appear in the output.

---

## 7. Artifacts

| Artifact | Path | Size |
|---|---|---|
| Final assembled video | `final/final_look3_reference_driven_demo.mp4` | 24MB · 20.4s · 768×1152 · 30fps |
| Keyframe contact sheet | `final/keyframe_contact_sheet.png` | 1.3MB — 4-panel grid, labeled shot_001–004 |
| Clip review sheet | `final/clip_review_sheet.png` | 1.2MB — first/mid/last frame per clip, 4-row grid |
| Run summary | `final/run_summary.md` | 7KB — full run log with config, paths, pipeline notes |
| Decision log | `final/decision_log.json` | 12KB — per-shot: keyframe generation history, Kling status, prompts used |
| Keyframe 001 | `keyframes/shot_001_keyframe_look3_preserve_scene_test.png` | 2.0MB |
| Keyframe 002 | `keyframes/shot_002_keyframe_look3_preserve_scene.png` | 1.9MB |
| Keyframe 003 | `keyframes/shot_003_keyframe_look3_preserve_scene.png` | 2.0MB |
| Keyframe 004 | `keyframes/shot_004_keyframe_look3_preserve_scene.png` | 2.1MB |
| Pose overlays (×4) | `analysis/pose_overlay/` | 926KB–1.4MB each |
| Project state | `project_state.json` (root) | Central pipeline state — all shots, briefs, config, eval status |
