# Mode A Reusable Policies

**Status:** policy layer only — documents and structures the recent street-run
fixes as general Mode A logic. It does **not** change the current production
scripts, does not call any API, and does not modify completed outputs.

**Files**

| File | What it captures |
|---|---|
| `pipeline/policies/reference_policy.py` | Shot taxonomy, reference-slot ordering, identity-anchor selection, anchor fallback, quality / input_fidelity policy. |
| `pipeline/policies/motion_policy.py` | Damping words to remove, observable motion cues, appearance-vs-motion separation, `repair_motion_prompt`. |
| `pipeline/policies/evaluation_policy.py` | `motion_energy_ratio` concept, repair-priority classification, optical-flow-as-evidence rule. |
| `pipeline/policies/backend_limits.py` | Honest capability limits of gpt-image-1 / Kling; future backends. |

---

## Why this exists

These policies were **discovered during the street-scene repair process**
(`live_test_04_street_look3`), not designed up front. Fixing that one run
surfaced rules that turned out to be general:

- **Reference ordering & identity.** Face-visible shots break when a real scene
  photo sits in the high-weight slot — the model paints "a generic person who
  fits the scene." Identity must lead; scene is described in text or demoted to
  a low slot. The identity anchors are built from the close-up / profile-crop
  references, never from the contact sheet.
- **Motion.** Damping words ("subtle", "slight", "mostly static") were
  suppressing motion to near-static clips. Removing them and naming *observable
  cues* (head-turn speed, stride visibility, weight shift, arm swing, footstep
  rhythm, body displacement, camera parallax) raised measured motion energy
  (shot_001 14% → 51%, shot_003 19% → 47%).
- **Evaluation.** The first/mid/last "clip review sheet" is not evidence — for a
  static clip its three columns look identical and hide the problem. Motion has
  to be measured from the **dense optical-flow audit**, decomposed into subject
  vs camera flow, and judged against the matching reference segment so we don't
  fabricate motion a calm reference never had.
- **Backend limits.** gpt-image-1 has **no** hard ControlNet-style pose
  interface; a skeleton image is weak guidance only. Prompt-level Kling I2V does
  not guarantee exact motion transfer. LoRA / IPAdapter / InstantID / ControlNet
  are future backends, not the current build.

## They are not street-specific

Nothing above depends on Paris, cobblestones, or Look 3. The rules are keyed to
**shot type** (`face_visible`, `back_view`, `lower_body`, `side_profile`,
`generic`) and to **observable, measured** signals (optical-flow energy, forbidden
words). Any future Mode A run with the same taxonomy can import these modules and
get the same behaviour. The street run is just where they were first observed.

## How to fold them into the shared pipeline (later)

The policy layer is deliberately **inert**: importing it changes nothing. Folding
it in is a separate, explicit step, and each is a small, testable seam:

1. **Reference ordering** — have the generator build its `images.edit` slot list
   from `reference_policy.build_reference_order(shot_type, sources, pose_skeleton_available)`
   and read `quality_policy(shot_type)` for `quality` / `input_fidelity`, instead
   of the hand-written per-shot ordering in the standalone street script.
2. **Motion prompts** — run every video prompt through
   `motion_policy.strip_damping()` (and `repair_motion_prompt()` on a repair) so
   damping words can never re-enter, keeping appearance words in the keyframe
   prompt and motion words in the video prompt.
3. **Evaluation** — feed the optical-flow audit numbers into
   `evaluation_policy.classify_motion_repair_priority(MotionMetrics(...))` and act
   on the returned `keep / rerun_prompt_only / rerun_keyframe / archive_limitation`,
   recording the verdict in the per-shot decision log.
4. **Backend honesty** — read `backend_limits` in the UI/report layer so labels
   and dissertation wording stay consistent with what the backend actually does.

## What this avoids claiming

The current implementation is **still partly standalone**: the completed runs
were produced by the tuned scripts (`generate_street_run.py`, `run_kling_i2v.py`,
the motion-v2 rerun), not by these modules. This document records the fixes as
**policy** so we do not overclaim that the temporary repair scripts are already
fully integrated into the shared pipeline. They are not — this layer is the
bridge that says *how* they would be, when that integration is done on purpose.
