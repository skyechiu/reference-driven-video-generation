# Motion-Quality Audit — Street Kling Clips (reference-anchored)

**Date:** 2026-07-18
**Scope:** Objective, local motion audit of the 4 street Kling clips. No OpenAI, no Kling, no regeneration; existing clips and final video untouched. Only new files under `final/motion_audit/`.

## Correction vs the first pass

The first version compared street against the **beach clips**. That was wrong: the beach clips are themselves keyframe→I2V generations, not ground truth. The real motion target is the **original reference video** (`test/test_03_multishot_edit_4shots.mp4`). This version anchors on the reference; beach is kept only as a second generation for peer context.

## Method

Reference video and both generations decoded, each frame resized to a **common height of 288px with native aspect preserved** (reference is 16:9, clips are 2:3 — so no squeezing). Optical flow (Farnebäck) per frame pair, reported as **% of frame height per frame** (`flow_pct_h`) so 16:9 and 2:3 sources compare fairly. Median flow vector ≈ camera motion; residual ≈ subject motion. `captured %` = generation flow ÷ reference flow for the same shot (per-frame speed, so clip duration does not matter).

Note: reference is real footage in a different outfit/framing, so content is not identical — only **motion magnitude/speed** is compared, which is the valid axis here.

## Results (flow = % of frame height per frame)

| shot | REFERENCE (target) | BEACH | STREET | street captured | beach captured |
|---|---|---|---|---|---|
| shot_001 | 0.336 (peak 1.48) | 0.084 | 0.047 | **14%** | 25% |
| shot_002 | 0.119 (peak 0.49) | 0.077 | 0.044 | 37% | 65% |
| shot_003 | 0.753 (peak 2.57) | 0.189 | 0.141 | **19%** | 25% |
| shot_004 | 0.273 (peak 0.83) | 0.186 | 0.175 | 64% | 68% |

Subject vs camera (street): 001 subj 0.042 / cam 0.018 · 002 subj 0.037 / cam 0.017 · 003 subj 0.137 / cam 0.014 · 004 subj 0.109 / **cam 0.135**.

## Findings

1. **Both generations systematically under-animate vs the reference.** Neither beach nor street reaches 68% of the reference's per-frame motion on any shot; the worst cases capture 14–19%. This is the honest headline — it is not "street vs beach", it is "generations vs the real reference", and both fall well short.
2. **Visually static street clips:** shot_001 and shot_002 (subject flow ~0.04 — near frozen).
3. **Biggest deficit vs the target:** shot_001 (14%) and shot_003 (19%) — precisely the reference's two most energetic shots (the quick head-turn in 001, the active feet-step + turn in 003). The system reproduces the calm shots better than the energetic ones.
4. **shot_004 is camera-driven:** its motion (cam 0.135 > subj 0.109) comes mostly from camera tracking, not the walk. It still reads acceptably.
5. **Why the earlier "Pass (visual)" missed this:** three-frame sampling + frame-difference cannot see a static clip and even ranked street_002 above beach_002 by frame-diff (backwards). Optical flow + reference anchoring is what exposes the gap.

## Recommendation

**B — rerun Kling for selected shots only.** No keyframe regeneration, no OpenAI.

- **shot_001 — highest priority.** Visually frozen and only 14% of the reference's motion; the reference has a clear energetic head-turn that the clip drops entirely. Rerun Kling with an explicit head-turn motion prompt.
- **shot_003 — second priority (optional).** Reference is the most dynamic shot; street captured 19%. street_003 is already the 2nd-most-active street clip and reads acceptably, so this is an "improve toward target" rerun, not a rescue.
- **shot_002 — low priority.** Visually static, but the reference itself is the calmest shot (0.119), so low motion here is partly faithful. A mild boost or accept-as-is.
- **shot_004 — keep.** 64% captured, acceptable.

Realistic expectation: I2V from a single still cannot reach 100% of real-footage motion energy. Target a meaningful lift (e.g., shot_001 14%→~40–50%), not parity. If a prompt-only rerun of shot_001/003 still under-moves, that residual gap is a legitimate, quantified dissertation limitation — not a failure to hide.

Not A (001 measurably static, far under target). Not C-for-all-4 (004 acceptable; 002 partly faithful). Not D (fixable at the Kling stage; keyframes usable).

## Constraints honoured

No existing clip overwritten. `final/final_look3_street_demo.mp4` untouched. All outputs are new files under `final/motion_audit/`.
