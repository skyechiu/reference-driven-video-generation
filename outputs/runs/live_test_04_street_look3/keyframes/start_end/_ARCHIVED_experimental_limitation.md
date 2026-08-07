# ARCHIVED — Experimental limitation (NOT used in final output)

**Branch:** Start/end pose-guidance extension for the street run
**Scripts:** extract_start_end_poses.py, generate_street_start_end.py
**Status:** Tested, NOT selected for final output. Do NOT run Kling on these outputs.

## What was tried
Per-shot START and END keyframes for the Parisian street run, with graded
conditioning: shot_002/004 pose-driven via a clean skeleton image rendered from
beach-reference keypoints; shot_001 head-orientation; shot_003 feet/text-framing.

## Why it was not selected
- START and END are generated independently by gpt-image-1, so the two frames of a
  pair are not temporally coherent (composition/crop/pose differ) → unsuitable as
  Kling image / image_tail pairs.
- shot_001 did not preserve the intended head-orientation progression
  (START front-facing, END profile with eyes closed — inverted / incoherent).
- shot_002 became frontal walking and did not reliably follow the skeleton pose.
- shot_003 did not complete the full 8-keyframe set.
- Skeleton-image-as-reference is too weak a control signal for gpt-image-1.

## Dissertation framing
"Start/end pose-guidance extension tested; not used in final output."
This is a valid experimental limitation / negative result, not a core failure.
The final street output uses the approved single-keyframe run (identity anchors +
profile anchor + shot-type-specific reference order + input_fidelity=high +
one approved keyframe per shot).
