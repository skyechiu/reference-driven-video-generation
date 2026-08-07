# Demo Summary — live_test_03_4shots
## Mode A v0.8.1 · Reference-Driven Video Generation

**Date:** 2026-07-17
**Pipeline:** Mode A (Reference Video) · v0.8.1 logic freeze
**Look:** Look 3 · The Tailored Self
**Scene:** preserve_reference_scene (beach sunset)
**Output:** `final/final_look3_reference_driven_demo.mp4`

---

## What this demo shows

A complete end-to-end run of the Mode A pipeline on a 4-shot beach-walk reference video. The system:

1. Analyses the reference video (shot cuts, camera motion, pose, beat alignment)
2. Builds a 5-track source frame storyboard
3. Generates IP-conditioned keyframes (gpt-image-1, source frame + look reference + identity)
4. Animates each keyframe with Kling I2V (5s per shot, 9:16)
5. Assembles into a 20.4s final vertical video

The IP character wears Look 3 · The Tailored Self (charcoal blazer, olive tie, wide denim trousers, black oxfords) in the reference beach-sunset setting. No extra generation, no repair, no OpenAI calls after keyframe approval.

---

## Reference video

| Field | Value |
|---|---|
| File | `test/test_03_multishot_edit_4shots.mp4` |
| Duration | 7.92s |
| fps | 30 |
| Shots | 4 (hard cuts) |
| BPM | 123.05 |
| Usage | Structure extraction only — not reproduced |

---

## Results at a glance

| shot_id | Shot type | Camera | Keyframe | Clip | Status |
|---|---|---|---|---|---|
| shot_001 | Over-shoulder MCU | push_in | ✓ approved (1 attempt) | ✓ 4.9MB | Pending eval |
| shot_002 | Back-view walk | static | ✓ approved (2 attempts) | ✓ 4.3MB | Pending eval |
| shot_003 | Low-angle feet CU | handheld | ✓ approved (2 attempts) | ✓ 7.5MB | Pending eval |
| shot_004 | Side-profile walk | handheld | ✓ approved (3 attempts) | ✓ 7.5MB | Pending eval |

All 4 keyframes generated and manually approved. All 4 Kling clips generated successfully. Automated evaluation (ArcFace identity, pose similarity, beat alignment) is pending.

---

## Final video

| Field | Value |
|---|---|
| Path | `final/final_look3_reference_driven_demo.mp4` |
| Resolution | 768×1152 (9:16 vertical) |
| Frame rate | 30fps |
| Duration | 20.4s (4 × 5s Kling clips) |
| Size | 24MB |
| Assembly | ffmpeg concat / copy — no re-encode, no audio |

---

## Key claim

The system preserves reference shot structure and action intent, but does not perform exact frame-level motion transfer. Motion follows the video prompt; exact gait and step cadence are not controlled.

---

## What is not claimed

- Perfect or guaranteed identity consistency across shots
- Exact gait or skeleton-driven animation
- Fully automatic output without human review
- Frame-accurate synchronisation with the reference
