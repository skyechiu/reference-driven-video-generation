# Mode C — Driving Performance Video (Condition A) · Repository Audit

**Status: PHASE 0 PASSED (runs on 16 GB). Next = quality tuning + eventual full 27 s loop; full generation still not claimed.**
**Last updated:** Phase 0 **passed** on `w33108` (RTX 4080, 16 GB). A ~4 s low-res (480×832, 81 frames, int8) single segment ran end-to-end **via Wan2GP** (int8 quant + mmgp CPU-offload, SDPA — the official 14B repo hit a flash-attn ABI mismatch on this torch build, so Wan2GP was the working low-VRAM path). Result: **runs on 16 GB ✓, motion follows ✓, background preserved ✓, identity/proportions distort on extreme poses (quality WIP)**. Evidence in the dashboard Mode C page + `outputs/runs/mode_c_phase0/phase0_results/` (replacement video, SAM3 mask). Full 27 s generation still not validated.
Condition A = replace the performer, preserve original background / camera / duration / timing.

---

## 0. Feasibility verdict (read first) — UPDATED: remote GPU verified

**Status by environment:**

| Environment | Status | Evidence |
|---|---|---|
| Local host (this dashboard, Mac Linux VM) | **blocked** | no NVIDIA GPU, no CUDA, no `torch`; only `onnxruntime` + `opencv`. Generation cannot run here. |
| Remote GPU host `w33108` — base env | **verified** | RTX 4080, 16 GB, CUDA 12.9, env `modec` (Python 3.10.20), `torch 2.6.0+cu124`, `cuda.is_available()==True` + CUDA tensor test passed, ffmpeg+git, `cv2/numpy/PIL/imageio/moviepy/tqdm` import OK, GPU memory clear, `/home` ~190 G / `/transfer` ~954 G. |
| Wan-Animate backend (Wan2GP) | **running** | int8 quant + mmgp CPU-offload + SDPA on `w33108`. Official 14B repo blocked by flash-attn ABI; Wan2GP is the working low-VRAM path. |
| Phase 0 (short low-res segment) | **passed** | runs end-to-end on 16 GB; motion follows; background preserved; proportions/identity distort on extreme poses (quality WIP). Evidence: `outputs/runs/mode_c_phase0/phase0_results/`. |
| Full Mode C generation (27 s) | **not yet validated** | requires a passing Phase 0 first. Not claimed as ready; the full-generation button stays disabled. |

**What "verified for Phase 0" means and does NOT mean.** The remote box can now *host* the Wan2.2-Animate stack — the driver/toolkit/torch are in place and CUDA is live. It does **not** yet prove Wan2.2-Animate Replacement Mode runs end-to-end, fits in 16 GB, preserves the background, or holds identity. Those are exactly what Phase 0 tests.

**The 16 GB constraint is real.** Wan2.2-Animate video replacement is memory-hungry; 16 GB VRAM is on the low side for the 14B model on video. That is precisely why the next step is a **3–5 second, low-resolution single segment only** — short frames + low res to fit memory and confirm the pipeline runs at all. Full 27 s generation likely needs memory optimisation (frame batching, offload/quantisation, or a smaller model variant) and is **not** enabled until Phase 0 passes and a memory budget is established.

**Next step (only this):**
1. On `w33108` in env `modec`, install Wan2.2-Animate + checkpoints and DWPose/mask deps.
2. Run the `PerformanceReplacementBackend.check_availability()` + **one 3–5 s low-res segment** through the adapter.
3. Measure: does it run, peak VRAM, background preserved outside the mask, identity from the Look, pose followed. Record in the decision log.
4. Only if that passes: plan the segment budget for longer clips. Do **not** jump to 27 s.

**Scope honesty (unchanged):** Mode C is still a genuinely new subsystem (second generation backend + masking + compositing + temporal fusion), listed as future work in the project instructions. The remote GPU removes the *hardware* blocker for a feasibility test; it does not remove the *timeline/scope* question. Recommend: build the non-generation Phase 1 scaffold ($0) + run the GPU Phase 0 test, then decide based on the Phase 0 result whether the full loop is worth the remaining dissertation time.

### Phase 0 kit (prepared, ready to run on `w33108`)

`pipeline/modes/mode_c/phase0/` — `README_PHASE0.md`, `setup_phase0.sh`, `run_phase0.sh` (CONFIRM_RUN-gated), `measure_phase0.py`.
Inputs in `outputs/runs/mode_c_phase0/mode_c_condition_a/input/`: `driving_segment_phase0.mp4` (512×912 portrait, 4 s, cut from `mode_c.MP4` @ 17.5 s — a steady full-body window chosen by optical-flow analysis), a full-res copy for measurement, and `target_look_reference.png` (Look 1 activewear full-body front — matches the workout driving video).
Uses the real Wan2.2-Animate CLI (`preprocess_data.py --replace_flag` → `generate.py --task animate-14B --replace_flag --use_relighting_lora`, low `--resolution_area`, offload flags). Records VRAM peak, motion-follow (optical-flow proxy), background-preservation (masked diff), identity (insightface, optional). **16 GB on a 14B model is tight → OOM is a valid Phase 0 result; `Wan2GP` is the low-VRAM fallback.**

---

## 1. Current architecture map

```
Flask dashboard (pipeline/app.py, :5001)
  state:    load_state / save_state / mutate_state (atomic, RLock, last-valid snapshot)   [app.py]
            decision log lives INSIDE project_state.json  -> state["decision_log"]
  jobs:     start_job(cmd, label) + /api/job/<id> polling                                  [app.py:130]
  looks:    Look Library + _resolve_look(look_id)                                          [app.py:9597]
  media:    /media/run/<run_id>/<path:sub>  already serves outputs/runs/<run_id>/**
  stages (Mode A, subprocess):  STAGE_CMDS -> pipeline/stage1_analyze .. stage5_repair
  policies: pipeline/policies/{reference,motion,evaluation,backend_limits}.py
            pipeline/mode_a_policy_service.py + /api/apply-mode-a-policies
  Mode B:   /api/mode-b/*  (story -> panel plan -> sheet -> json)

Generators:  pipeline/generators/{base,api_gen,chatgpt_gen,local_gen}.py   (image/video)
Analysis:    stage1_analyze.py (PySceneDetect, MediaPipe pose via models/pose_landmarker_full.task, beats)
Motion:      Farnebäck optical-flow logic EXISTS but is DUPLICATED inside standalone scripts
             (promote_motion_v2.py, rerun_street_kling_001_003.py, generate_street_run.py) — not a shared util
Driving vid: mode_c.MP4  — ffprobe: 1464×822, ~30 fps, 27.15 s, has audio
             (thumbnail looks portrait; ffprobe reports landscape + no rotation tag — confirm orientation in preflight)
```

## 2. Files / infrastructure that can be reused (do NOT duplicate)

| Need in Mode C | Reuse | Location |
|---|---|---|
| Atomic state + locked read-modify-write | `load_state` / `save_state` / `mutate_state` | app.py |
| Background jobs (no long-held request) | `start_job` + `/api/job/<id>` | app.py:130 |
| Look selection / resolution | `_resolve_look`, Look Library routes | app.py:9597, `/api/looks` |
| Decision log | `state["decision_log"]` list (+ export routes) | app.py |
| Media serving | `/media/run/<run_id>/<sub>` | app.py |
| JSON error contract | global `@app.errorhandler` + `apiJson()` (added this session) | app.py |
| Optical-flow / motion-energy | logic exists — **extract** from scripts into `pipeline/utils/motion.py` | promote_motion_v2.py etc. |
| Pose extraction | MediaPipe task model | pipeline/models/pose_landmarker_full.task |
| ffmpeg concat / probe patterns | used throughout | stage/scripts |
| Honest status labels (available/experimental/planned/unavailable) | `.hb-*` badge system (added this session) | app.py |

**Refactor opportunity:** the optical-flow code is copy-pasted across three scripts. Before Mode C reuses it, lift it into one shared module and have C6 evaluation import it (satisfies "reuse existing optical-flow utilities").

## 3. Missing dependencies / checkpoints

**On the remote GPU host `w33108` (env `modec`):** CUDA 12.9 + `torch 2.9.1+cu128` present and working. Still to install there: Wan2.2-Animate package + **model checkpoints**, DWPose/`mmpose`, a segmentation/matting model (SAM/RVM) for mask + background, and `diffusers`/`insightface` as needed. These are the Phase 0 install list.

**On the local dashboard host** (unchanged) — not present anywhere:
- **GPU/driver:** no CUDA, no `nvidia-smi`.
- **Frameworks:** `torch`, `torchvision`, `diffusers`.
- **Wan2.2‑Animate:** package + model checkpoints (none on disk; only `pose_landmarker_full.task` exists).
- **Pose for replacement:** `dwpose`/`mmpose` (Mode A uses MediaPipe, which is fine for analysis but Wan expects DWPose-style input).
- **Masking / background:** no segmentation model (SAM/RVM/matting) present — required for foreground mask + background preservation.
- **MimicMotion:** not installed (and must remain a labelled *Animation Mode* fallback, never a silent substitute).

## 4. Implementation plan (phased, hardware-gated)

- **Phase 1 — scaffold (buildable here, safe, $0):** Mode C state schema under `state["mode_c"]` with migration/defaults (existing Mode A/B projects must still load); nav entry + honest status; Condition A = *Experimental/backend_unavailable*, Condition B = *Planned/disabled*; driving-video upload; Look selection (reuse Look Library); **C0 preflight** (probe video, pose/face coverage via MediaPipe, camera-motion via the extracted optical-flow util, backend availability check → `backend_unavailable`); **C1 analysis**; **C3 segment planner** that proves the 27 s timeline reconstructs with **zero** generation. All display/analysis only.
- **Phase 0 (Mode C) — backend feasibility (BLOCKED here):** on a real GPU env, install Wan2.2‑Animate + checkpoints, run `check_availability()` and **one 3–5 s segment** through the `PerformanceReplacementBackend` interface. Gate everything else on this passing — same discipline as Mode A's Phase 0.
- **Phase 2 — preprocessing:** pose/face/mask/background extraction + preview contact sheet (needs the seg/pose models; partial on CPU, slow).
- **Phase 3–6:** segment generation → overlap fusion → C6 evaluation (pose similarity, motion-energy reuse, background preservation, identity where face is detectable, timing) → targeted per-segment repair → 27 s assembly + audio restore + report. **Only after Phase 0 passes.**

## 5. Exact files proposed (create / modify) — for approval, not yet written

**Create:**
```
pipeline/modes/mode_c/{__init__,service,preflight,driving_analysis,preprocessing,
                       segment_planner,generation,assembly,evaluation,repair,schemas}.py
pipeline/backends/{base_performance_backend,wan_animate_backend}.py   # wan adapter may be a guarded stub until GPU exists
pipeline/policies/performance_policy.py
pipeline/utils/motion.py            # extracted shared optical-flow/motion-energy (refactor)
docs/MODE_C_STATUS.md               # live implemented/experimental/planned/unavailable ledger
```
**Modify (surgically, no Mode A/B behaviour change):**
```
pipeline/app.py        # thin /api/mode-c/* routes -> service.py ; nav + Mode C page (honest status) ;
                       # state migration defaults for state["mode_c"] ; reuse start_job/_resolve_look/mutate_state
project_state.json     # additive: state["mode_c"] block (migration, never a minimal replace)
pipeline/policies/backend_limits.py   # add Wan/MimicMotion capability + "no silent fallback" record
```

**Explicitly NOT touched:** stage1–5, generators/*, Mode A/B routes, completed outputs.

---

### Recommended next decision
1. Confirm a **GPU environment** (school box specs or a cloud plan) and that Wan2.2‑Animate is obtainable there. Without it, Condition A generation cannot be demonstrated.
2. If yes → I build **Phase 1 scaffold only** (schema + honest UI + preflight/analysis/segment-planner, all $0, no generation), then we do the Mode C Phase 0 backend test on the GPU box before anything heavier.
3. If the GPU/timeline isn't there → keep Mode C as a **documented, honestly-labelled Planned mode** and put the dissertation energy into the reference-vs-generated evidence you already have.
