# Project Run Instructions
## Reference-Driven Agentic Short-Form Video Generation System

**Last updated:** 2026-07-17
**Status:** Post identity-consistency fix — street run in progress, beach run completed

---

### 1. Current Stable Project Position

The main dissertation pipeline is **Mode A — Reference Video Pipeline**.

Mode A takes a reference short video as input, decomposes it into a structured beat-aligned storyboard, and regenerates a new video using the IP character and a new scene. This is the core dissertation contribution.

The main completed demo is:

```
outputs/runs/live_test_03_4shots/
```

This is the official Mode A reference-video run. It demonstrates:
- reference video analysis (shot cuts, beats, pose)
- 5-track generation units
- keyframe generation via gpt-image-1
- Kling I2V (image-to-video)
- final assembly
- decision log per shot

**Do not confuse this with the street scene package demo (live_test_04_street_look3).** They use the same shared pipeline (keyframe → Kling → assemble) but serve different purposes. The beach run is the dissertation evidence. The street run is a secondary scene-package experiment.

---

### 2. Main Demo: Beach Run

| Field | Value |
|---|---|
| Run ID | `live_test_03_4shots` |
| Final video | `outputs/runs/live_test_03_4shots/final/final_look3_reference_driven_demo.mp4` |
| Status | Completed demo run |
| Purpose | Main Mode A evidence for the dissertation |

**What this run claims:**
- Preserves shot structure from the reference video
- Preserves action intent per shot
- Uses selected Look 3 (The Tailored Self)
- Does **not** perform exact frame-level motion transfer — structure is preserved, not pixels
- Automated evaluation is pending unless explicitly re-run via the evaluation stage

**Do not modify or re-run this output without explicit intent.** It is the primary demonstrable artefact.

---

### 3. Secondary Demo: Street Scene Package Run

| Field | Value |
|---|---|
| Run ID | `live_test_04_street_look3` |
| Label | Scene Package Demo — shared keyframe-to-I2V pipeline |
| Main script | `generate_street_run.py` |
| Repair script | `regen_shot001_004_v2.py` |
| Status | Keyframes in progress — not yet sent to Kling |

**Purpose:**
This is a secondary experiment using a static scene package (Parisian street) instead of a reference video. It tests the shared keyframe-to-I2V pipeline with a different scene setup and stress-tests identity consistency under outdoor street lighting.

**This is NOT the main Mode A reference-video run.** No reference video is used. Scene structure comes from the static `scene_02_modern_street` asset package, not from decomposing an input clip.

---

### 4. Important Warning: Do Not Modify `api_gen.py` Yet

**File:** `pipeline/generators/api_gen.py`

This file still contains the **older general pipeline logic**. It has not yet been updated with:
- `input_fidelity="high"`
- `face_visible` / `back_view` / `lower_body` shot classification
- identity anchor logic (`look3_identity_anchor_street.png`)
- new slot-order strategy (different slot[0] per shot type)
- street-scene specific identity repair logic

**Do NOT rewrite `api_gen.py` until the street run has been fully validated.**

Reason: the new slot-order and fidelity logic is currently implemented and tested only in `generate_street_run.py` and `regen_shot001_004_v2.py`, for the specific combination of Look 3 × street scene. Generalising it into the main pipeline before validating outputs risks breaking the beach run's established pipeline behaviour.

Planned future step: once the street run keyframes are approved and Kling clips are confirmed stable, migrate the identity-anchor pattern and slot-order logic into `api_gen.py` as a general improvement.

---

### 5. Identity Consistency Strategy

Identity consistency for the street run is achieved through a combination of measures. No single measure is sufficient on its own.

**Reference images used:**
- `look3_closeup.png` — clean white-background front-facing face close-up (slot 1 for face-visible shots)
- `look3_profile_crop.png` — clean white-background near-profile face crop (slot 3 for face-visible shots)
- `look3_identity_anchor_street.png` — pre-generated portrait of the Look 3 character placed into a Parisian street environment; used as slot[0] for all face-visible shots

**Pipeline settings:**
- `input_fidelity="high"` on all `images.edit` calls — forces closer adherence to input image references
- `quality="high"` for face-visible shots and for anchor generation
- Shot-type-specific reference ordering — different slot[0] depending on whether the face is visible

**Human gates:**
- Human review of the identity anchor before running any shot keyframes
- Human review of the 4-shot keyframe contact sheet before running Kling

**Why the identity anchor is necessary but not sufficient:**
The anchor puts the character into the street environment in advance, removing the model's need to reconcile a white-background portrait against a Parisian street scene. However, if placed in the wrong slot, or if the prompt does not assign roles explicitly, the anchor alone does not guarantee identity stability. Slot order and prompt role assignments are equally important.

**Why scene reference is excluded from image slots for face-visible shots:**
Including a real-world outdoor photograph (e.g. a Parisian street scene) in the image slots introduces strong scene texture that competes with the identity references. The model tends to generate "a generic woman who fits this scene" rather than the specific IP character. For face-visible shots, the scene is described in text only. For back-view and lower-body shots, scene reference may be used at slot[0] because face identity is not the primary concern.

---

### 6. Reference Order Rules

The slot order passed to `gpt-image-1` images.edit determines which reference has the strongest influence. Earlier slots carry more weight.

**Face-visible shots (shot_001, shot_004):**

```
[0] look3_identity_anchor_street.png   ← PRIMARY: locks identity in street context
[1] scene_ref / main_scene_board       ← composition, architecture, street layout
[2] look3_front.png                    ← outfit and body proportions
[3] look3_profile_crop.png             ← side-profile facial geometry support
```

- slot[0] locks identity — the anchor is an already-approved face in the street environment
- slot[1] controls composition and scene structure
- slot[2] preserves the exact Look 3 outfit
- slot[3] reinforces facial geometry from a second angle

**Back-view shots (shot_002):**

```
[0] scene_ref / main_scene_board       ← PRIMARY: street depth and perspective
[1] look3_identity_anchor_street.png   ← silhouette and continuity
[2] look3_front.png                    ← outfit silhouette from front
[3] look3_sheet.png or profile_crop    ← supplemental outfit / hair reference
```

- Scene is the structural anchor because the face is not visible
- Identity anchor supports continuity of silhouette and hair
- Look front preserves outfit silhouette

**Lower-body shots (shot_003):**

```
[0] scene_ref / main_scene_board       ← PRIMARY: cobblestone ground, low-angle structure
[1] look3_front.png                    ← trouser hem and shoes
[2] look3_sheet.png                    ← outfit overview
```

- Face is not visible — do not waste the strongest slot on identity
- Prioritise cobblestone texture, trouser cut, and shoe detail

---

### 7. API Settings

| Context | `quality` | `input_fidelity` |
|---|---|---|
| Identity anchor generation | `"high"` | `"high"` |
| Face-visible shots (shot_001, shot_004) | `"high"` | `"high"` |
| Back-view shots (shot_002) | `"medium"` | `"high"` |
| Lower-body shots (shot_003) | `"medium"` | `"high"` |

**Rule:** `input_fidelity="high"` applies to all calls. Do not run face-visible shots without it.

`quality="high"` increases per-image cost. Reserve it for shots where facial identity must be precise. Back-view and lower-body shots do not require it.

---

### 8. Street Run Execution Order

Follow this order exactly. Do not skip human review steps.

**Step 1 — Identity anchor**
Check whether `look3_identity_anchor_street.png` already exists and is approved.
If regeneration is needed:
```bash
python3 regen_anchor.py
```
Review the output. Stop here if the anchor does not look like the correct character.

**Step 2 — Keyframe generation**
```bash
python3 generate_street_run.py
# RUN_MODE = "keyframes_only"  (default — do not change)
# ALLOW_OVERWRITE = False       (default — change only to force re-run)
```
This generates 4 keyframes in `outputs/runs/live_test_04_street_look3/keyframes/`.

**Step 3 — Review the 4-shot contact sheet**
Inspect the generated keyframes manually. Check:
- shot_001 and shot_004: does the face match the anchor?
- shot_002: does the silhouette and outfit look correct?
- shot_003: are the trousers, shoes, and cobblestone correct?

**Step 4 — Targeted repair (if needed)**
If shot_001 or shot_004 has identity drift, run:
```bash
python3 regen_shot001_004_v2.py
```
This outputs:
- `shot_001_keyframe_look3_street_v2.png`
- `shot_004_keyframe_look3_street_v3.png`
- `street_shot001v2_004v3_comparison.png` (2×2 comparison: old top, new bottom)

**Step 5 — Select approved keyframes**
Review the comparison sheet. Manually select the best version of each shot and confirm it as the active keyframe for that shot slot.

**Step 6 — Build final 4-shot contact sheet**
Assemble the approved set:
- approved shot_001
- approved shot_002
- approved shot_003
- approved shot_004

Confirm the full set before proceeding.

**Step 7 — Run Kling / full_auto**
Only after the 4-shot contact sheet is approved, switch `RUN_MODE = "full_auto"` and run.

```
DO NOT run Kling before the 4-shot keyframe contact sheet is approved.
```

---

### 9. Human Review Gates

These are mandatory stop points. Do not proceed past any of these automatically.

| Gate | When to stop |
|---|---|
| After anchor generation | Review `look3_identity_anchor_street.png` — does it look like the correct character in the correct outfit? |
| After keyframe run | Review the 4-shot contact sheet — are all shots consistent? |
| After repair run | Review the comparison sheet — is the new version better? |
| Before Kling | All 4 keyframes must be approved. No exceptions. |
| Before final assembly | If Kling clips show unstable motion or identity collapse, stop and do not assemble. |

---

### 10. What Counts as Acceptable

**Acceptable:**
- Character looks like the same Look 3 identity within practical API limits
- Outfit remains Look 3: charcoal blazer, white shirt, olive tie, wide blue denim, black oxfords
- Scene remains Parisian cobblestone street
- shot_001 and shot_004 show improved facial consistency compared to the first run
- shot_003 may be kept if lower-body detail (trousers, shoes, cobblestone) is correct, even if not re-run

**Not acceptable — do not proceed to Kling:**
- Generic brunette face (does not match the Look 3 identity)
- Outfit drift to corporate black suit or school uniform
- Black tie instead of olive/khaki-green tie
- Slim trousers instead of wide denim
- Scene photo overriding identity (character becomes "generic person in this scene")
- Extra people in frame
- Duplicated body or face artefacts
- Running Kling on keyframes that have not been reviewed

---

### 11. Dissertation Wording

**Street run finding (recommended wording):**

> "The street-scene experiment revealed a limitation of reference-conditioned image generation: when identity, outfit, scene, and framing references are provided simultaneously, facial identity can drift. The implemented repair strategy introduces identity anchors, profile crops, high input fidelity, shot-type-specific reference ordering, and human review before I2V generation."

**Scope boundary (recommended wording):**

> "The current implementation remains an API-based reference-conditioned pipeline. Stronger identity methods such as IPAdapter FaceID, InstantID, or LoRA are considered future work rather than part of the current main implementation."

These wordings set honest scope expectations and frame the identity repair work as a valid engineering contribution without overclaiming.

---

### 12. Current Next Step

```
Current next step:
  Finalize the street run keyframe set.
  Run regen_shot001_004_v2.py to regenerate shot_001 and shot_004
  with the updated identity anchor at slot[0].
  Review the comparison sheet.
  Only proceed to Kling after the 4-shot set is approved.

Do NOT modify api_gen.py yet.
Do NOT run Kling until the updated 4-shot street contact sheet is approved.
```

---

*This document covers pipeline state as of 2026-07-17 following the identity-consistency fixes applied to the street run. The beach run (live_test_03_4shots) is unaffected and remains the primary dissertation demo.*
