# Mode C · Phase 0 — 3–5 s low-res single-segment feasibility test

**Goal:** prove Wan2.2-Animate *Replacement* mode runs on `w33108` (RTX 4080, 16 GB) on ONE short
low-res segment, and measure the four things that decide whether Mode C is viable:

1. **VRAM peak** — does it fit in 16 GB at low res?
2. **Motion follows** — does the generated character move with the driving performance?
3. **Background preserved** — is everything outside the person unchanged?
4. **Identity holds** — is it the Look-3 character, not a drifted/generic face?

**This is NOT the 27 s run.** Do not run full generation until this passes and a VRAM budget is known.

---

## Honest expectations (read before installing)

- Wan2.2-**Animate-14B** is a 14-billion-parameter video model. On a **16 GB** card it is **very tight**
  even for a 4 s low-res clip. Expect to need offloading, and be prepared for an **out-of-memory (OOM)**
  result — *that is itself a valid Phase 0 finding*, not a failure of the plan.
- **Recommended low-VRAM route:** `deepbeepmeep/Wan2GP` is a community re-implementation built for
  "GPU-poor" cards (6–24 GB) with aggressive block-swap/offload and supports Wan2.2-Animate. On a 16 GB
  4080 it is more likely to run than the official 14B repo. The official repo below is the *reference
  interface*; if it OOMs, switch to Wan2GP and re-run the same segment.
- Dependencies (Wan repo, DWPose/mask preprocess checkpoints) are **not installed yet**. `setup_phase0.sh`
  installs them; expect a large checkpoint download (~tens of GB → use `/transfer`, which has ~954 G).

## Inputs already prepared (in this repo)

```
outputs/runs/mode_c_phase0/mode_c_condition_a/input/
  driving_segment_test2_phase0.mp4         # DEFAULT — 512×912 portrait, 4.0 s, from YOUR test2.mov @ 2.4 s
  driving_segment_test2_phase0_fullres.mp4 # same window, full res (measurement ground truth)
  driving_segment_phase0.mp4               # secondary — 512×912, 4.0 s, from mode_c.MP4 @ 17.5 s
  driving_segment_phase0_fullres.mp4       # secondary, full res
  target_look_reference.png                # your front-body reference (941×1672) = the replacement character
  test2.mov                                # your original second test clip (1080×1924, ~7 s)
```

## Steps on w33108 (conda env `modec`)

```bash
conda activate modec
cd <where you copy this kit + inputs>

# 1. install (downloads Wan2.2-Animate-14B into ./Wan2.2-Animate-14B — put it on /transfer)
bash setup_phase0.sh

# 2. dry-run (prints the exact commands, runs nothing)
bash run_phase0.sh

# 3. actually run Phase 0 — DEFAULT runs your test2 segment (preprocess → generate → sample VRAM)
CONFIRM_RUN=1 bash run_phase0.sh
# to run the mode_c.MP4 segment instead:
#   SEG=$PWD/input/driving_segment_phase0.mp4 CONFIRM_RUN=1 bash run_phase0.sh

# 4. measure the four metrics
python measure_phase0.py
```

Everything writes under `./phase0_out/` (segment stays untouched; nothing overwrites Mode A/B).

## What "pass" looks like

- Generation completes without OOM at the chosen low res, peak VRAM recorded and < 16 GB.
- Background-difference outside the mask is low (person replaced, room unchanged).
- Generated motion energy tracks the driving segment (moves, not frozen).
- Identity similarity to the Look reference is reasonable where a face is visible.

Record all four (plus peak VRAM and whether offload was needed) in `phase0_out/phase0_metrics.json`
and paste the summary back — that is the evidence that decides whether the full loop is worth building.
