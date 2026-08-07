# Reference-vs-Street Motion Audit

**Date:** 2026-07-18
**Ground-truth motion target:** `test/test_03_multishot_edit_4shots.mp4`
**Shot cuts source:** `project_state.json → reference_data.shot_cuts` (shot_001 0.0–2.4s · shot_002 2.4–4.667s · shot_003 4.667–6.8s · shot_004 6.8–7.9s)
**Constraints:** No OpenAI, no Kling, no clip/keyframe modification. New files only, under `final/motion_audit/`.

> The street clips are evaluated against the original reference motion for action energy and motion amplitude, while the beach generated clips are used only as a secondary generated-output baseline.

This is a motion-**energy / amplitude** comparison, not a claim of exact frame-level motion transfer. The reference is real footage in a different outfit and framing, so only per-frame motion magnitude and speed are compared, never pixel-level correspondence.

## Method

Each reference shot segment and each generated clip is decoded, resized to a common height of 288px with **native aspect preserved** (reference 16:9, clips 2:3 — no squeezing). Per consecutive frame pair: Farnebäck optical flow, reported as **% of frame height per frame** (`avg_optflow_pct_h`) so different aspect ratios compare fairly; median flow vector ≈ camera/global motion, residual ≈ subject motion; plus frame-difference magnitude. `captured %` = generated flow ÷ reference flow for the same shot (per-frame, so the 5s clip vs ~2s reference segment does not bias it).

## A. Reference-video motion fidelity (street vs ground-truth target)

| shot | reference (target) | street | **street captured** | reference character of motion |
|---|---|---|---|---|
| shot_001 | 0.336 (peak 1.48) | 0.047 | **14%** | energetic head-turn toward camera (subject 0.335, camera ~0) |
| shot_002 | 0.119 (peak 0.49) | 0.044 | **37%** | calm slow walk away (lowest-motion reference shot) |
| shot_003 | 0.753 (peak 2.57) | 0.141 | **19%** | most active: stepping feet + turn (subject 0.698) |
| shot_004 | 0.273 (peak 0.83) | 0.175 | **64%** | lateral walk with camera movement |

**Fidelity findings.** The street clips reproduce only **14–64%** of the reference's per-frame motion. The two shots with the largest deficit are exactly the reference's two most energetic moments: shot_001 (quick head-turn, 14% captured) and shot_003 (active feet-step + turn, 19% captured). The system reproduces the calm reference shot (002) proportionally better than the energetic ones — i.e., it flattens motion peaks. shot_002's low absolute motion is partly faithful, because the reference itself is calm there.

## B. Generated beach-vs-street comparison (secondary baseline)

| shot | reference | beach (baseline) | street | beach captured | street captured |
|---|---|---|---|---|---|
| shot_001 | 0.336 | 0.084 | 0.047 | 25% | 14% |
| shot_002 | 0.119 | 0.077 | 0.044 | 65% | 37% |
| shot_003 | 0.753 | 0.189 | 0.141 | 25% | 19% |
| shot_004 | 0.273 | 0.186 | 0.175 | 68% | 64% |

**Baseline findings.** Both generations under-animate versus the reference on every shot (neither exceeds 68%). The beach `preserve_reference_scene` run captured modestly **more** motion than street on all four shots, but is itself far below the reference — so beach is a useful "what Kling produced here" yardstick, **not** a motion target. The street/beach gap is small (a few points to ~28pts on shot_002); the dominant gap is generation-vs-reference, not street-vs-beach. street shot_004's motion is also disproportionately camera-driven (subject 0.109 vs camera 0.135).

## C. Street clip repair recommendations

**Recommendation: B — rerun Kling for selected shots only.** No keyframe regeneration, no OpenAI.

- **shot_001 — highest priority.** 14% of target and visually frozen; the reference has a clear energetic head-turn the clip drops. Rerun Kling with an explicit motion prompt (quick head-turn toward camera, larger amplitude), motion sourced from the reference, not from the Look package.
- **shot_003 — second priority.** Reference is the most dynamic shot; street captured 19%. street_003 already reads acceptably, so this is "raise toward target", not a rescue.
- **shot_002 — low priority.** Low motion is partly faithful (reference is the calmest shot). Optional mild boost of stride/arm-swing; otherwise acceptable.
- **shot_004 — keep.** 64% captured; acceptable.

**Do not claim exact motion transfer.** Even with stronger prompts, single-still I2V cannot reach 100% of real-footage motion energy. Target a meaningful lift (e.g., shot_001 14% → ~40–50%), not parity. Any residual gap is a legitimate, quantified limitation for the dissertation, consistent with the system's stated boundary ("preserves structure and action intent, not exact frame-level motion transfer").

## Files in this audit

- `reference_vs_street_motion_metrics.csv` — reference / street / beach(secondary) per shot, with capture %.
- `reference_vs_street_dense_filmstrip.png` — reference vs street, native aspect, per shot.
- Companion (3-way with beach): `beach_vs_street_motion_comparison.png`, `motion_audit_report.md`.
