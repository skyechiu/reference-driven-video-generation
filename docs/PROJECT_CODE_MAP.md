# Project Code Map

Architecture summary by functional category, cross-referenced to `docs/CODE_INVENTORY.md`
(which is the authoritative per-file list). This document groups the same 97
files by what they *do* rather than by directory.

---

## 1. Dashboard (Flask, read-only evidence viewer)

- `pipeline/app.py` — single-file Flask app (routes, HTML/CSS/JS inline).
  `ONLINE_DEMO_READ_ONLY` guard; all state-mutating routes (upload/generate/
  reset/repair) return HTTP 403 regardless of caller.
- `pipeline/state.py` — reads/writes `project_state.json`; the dashboard's
  only route into pipeline state.
- `pipeline/config.py` — central config (paths, API key env-var names,
  thresholds, backend switch). Contains one legacy hardcoded local path —
  see `docs/GITHUB_PREP_REPORT.md`.
- 12 root-level `patch_*.py` scripts — mechanical find/replace edits applied
  to `app.py` over time (CSS, layout, mobile fixes, playsinline attribute,
  etc.), each self-backing-up before writing. These are the dashboard's
  edit history, not part of the running app.
- `pipeline/app.py.backup_*` (~55 files) — byproduct snapshots from the
  patch scripts above. Not source; superseded once real git history exists.

## 2. Static export

- `export.py` — flattens the Flask app into a static HTML site using
  Flask's test client (no network calls out). Explicitly excludes
  `mode_c.MP4` / raw control video from the export.
- `readme_and_zip.py` — builds the README for the static export and zips
  it; documents the same privacy exclusions (`mode_c.MP4`,
  `reference_videos/`, `video_ref/`).
- `outputs/huggingface_static_site/index*.html` — generated output of the
  above; not source, not itemized as code.

## 3. Evaluation / diagnostic scripts (no generation, read existing evidence)

- `pipeline/stage4_evaluate.py` — five-metric evaluator (identity, pose,
  framing, beat, look).
- `pipeline/evaluation/` package: `identity_evaluator.py` (reuses recorded
  ArcFace numbers, never runs a face model itself), `pose_evaluator.py`
  (reports pose-evidence availability, doesn't run pose estimation),
  `framing_evaluator.py` (reads human-coded acceptance from the decision
  log), `timing_evaluator.py` (ffprobe duration comparison against
  existing clips), `metric_status.py` (shared
  VERIFIED/COMPUTED_LOCAL/PENDING schema), `auto_repair_harness.py`
  (dry-run harness, no writes), `repair_planner.py` (produces proposals
  only, never executes them).
- `ablation_analyze.py` — computes Farnebäck optical flow, builds the
  contact sheet and CSV/summary/LaTeX table for the small controlled
  repair ablation. No API calls.

## 4. Generation / orchestration scripts (call OpenAI / Kling)

- `pipeline/stage3_generate.py` — backend-agnostic per-shot generation
  orchestrator (the pipeline's normal entry point for Mode A/B).
- `pipeline/generators/` package: `base.py` (abstract interface),
  `api_gen.py` (OpenAI Images + Kling — the path actually used for the
  completed evidence), `local_gen.py` (InstantID + CogVideoX/Wan2.1
  local-GPU alternative), `chatgpt_gen.py` (deprecated stub, raises on
  import).
- `generate_shot001.py` … `generate_shot004.py` — per-shot keyframe
  generation for the beach run.
- `generate_street_run.py` — the main street-scene 4-shot keyframe + Kling
  pipeline. **`RUN_MODE` defaults to `"full_auto"`** — running this file
  as-is triggers real, paid API calls; flagged in the inventory.
- `generate_street_start_end.py` — archived pose-guided start/end
  keyframe experiment for the street scene.
- `run_kling_i2v.py` — submits the four beach keyframes to Kling I2V.
- `regen_anchor.py`, `regen_shot001_004_v2.py`, `regen_shot001_3q.py`,
  `regen_shot002_004.py`, `regen_two_anchors.py` — targeted single-shot
  keyframe repairs (the "targeted repair" arm of the project's own
  evaluation-repair loop, and of the ablation).
- `rerun_street_kling_001_003.py` — targeted motion repair for street
  shot_001/shot_003. **`CONFIRM_RUN = True` is currently hardcoded** —
  flag before anyone clones and runs it unmodified.
- `promote_motion_v2.py` — promotes the repaired motion clips to become
  the official street run output; rewrites the final video + decision log.
- `ablation_blind_reroll_generate.py` — generates the blind-reroll
  condition for the small controlled repair ablation. Defaults to a
  dry-run (`CONFIRM_RUN = "--confirm" in sys.argv`).
- `extract_start_end_poses.py` — local-only MediaPipe pose extraction from
  the reference video.

## 5. Pipeline core (Stage 1/2, schema, policy)

- `pipeline/run.py` — CLI entry point (`phase0`/`init`/`analyze`/
  `template`/`generate`/`evaluate`/`repair`/`all`).
- `pipeline/stage1_analyze.py` — shot-cut detection (PySceneDetect), beat
  detection (librosa), pose (MediaPipe).
- `pipeline/stage2_template.py` — beat-aligned enriched storyboard JSON
  builder.
- `pipeline/stage5_repair.py` — evaluate → diagnose → repair →
  re-evaluate loop; the project's agentic core.
- `pipeline/generation_unit_schema.py` — canonical generation-unit schema
  shared across Mode A/B/C.
- `pipeline/mode_a_policy_service.py` — wires `pipeline/policies/` into
  per-shot decisions; makes no API calls.
- `pipeline/policies/` package: `backend_limits.py`, `evaluation_policy.py`,
  `motion_policy.py` (the Kling motion-prompt damping-words fix,
  generalised), `reference_policy.py` (reference-image slot ordering /
  identity-anchor rules).
- `pipeline/dance_analyzer.py` — v0.1 dance/motion detection and key-pose
  segmentation.

## 6. Mode-specific files

**Mode A** (reference-video-driven; beach = A-1 completed evidence, street
= A-2 stress test) is implemented across the generation/orchestration and
pipeline-core files above — there is no separate `mode_a/` directory; the
main pipeline *is* Mode A.

**Mode B** (storyboard-prompt extension) — no dedicated Python module found
in the 97-file scan; represented by ComfyUI/visual planning assets
(non-code, not itemized here).

**Mode C** (driving-video backend, Wan2.2 Animate):
- `pipeline/modes/mode_c/phase0/` — `measure_phase0.py` (measurement
  script), `run_phase0.sh` / `setup_phase0.sh` (remote-GPU entry points),
  `README_PHASE0.md` (setup doc, names `test2.mov`/`mode_c.MP4` by
  filename only — the media itself is excluded from the repo, see
  `docs/GITHUB_PREP_REPORT.md`).
- `pipeline/phase0_test.py` — identity-vs-pose feasibility test (the
  make-or-break Phase 0 experiment referenced in `CLAUDE.md`).

**Mode D** (planned extension) — no implementation files; referenced only
in docs.

## 7. Dissertation / report files

- `dissertation/paper.tex`, `dissertation/references.bib` — source of
  truth.
- `dissertation/dissertation_ch3-4_cvpr.tex` — earlier draft, superseded.
- `dissertation/chapters/00_abstract.md` … `07_appendix.md` — parallel
  Markdown chapter drafts.
- `dissertation/README.md`, `dissertation/论文检查报告_20260805.md` —
  folder readme and a paper QA/consistency working note.
- `pipeline/PIPELINE_README.md`, `docs/PROJECT_RUN_INSTRUCTIONS.md`,
  `docs/MODE_A_REUSABLE_POLICIES.md`, `docs/MODE_C_CONDITION_A_AUDIT.md` —
  architecture and run documentation.
- `CLAUDE.md`, `DEV_NOTES.md`, `MASTER_INSTRUCTIONS_20260805.md`,
  `README_SUBMISSION.md` — project-level handoff and submission docs.

## 8. Deployment / GitHub-prep files (new, this pass)

- `docs/CODE_INVENTORY.md` — Step 1 deliverable (this pass).
- `docs/PROJECT_CODE_MAP.md` — this file.
- `docs/GITHUB_PREP_REPORT.md` — Step 2 deliverable (security/size audit).
- `.gitignore` — Step 5 deliverable.

## 9. Files that should NOT be pushed

See `docs/GITHUB_PREP_REPORT.md` for the full reasoning and file sizes;
short list here for orientation:

- `.env` (contains real API key values)
- `project_state.json`, `project_state.last_valid.json` (hardcoded local
  `/Users/test/...` paths)
- `pipeline/app.py.backup_*` (~55 redundant snapshots, ~90MB+)
- `mode_c.MP4`, `reference_videos/`, `video_ref/`, `test2.mov`,
  `reference/video_dance_test_00001v2_.mp4` (unredacted/private source
  footage — the project's own `export.py`/`readme_and_zip.py` already
  treat these as private)
- `_archive/`, `_export_tmp/`, `_to_delete/` (superseded backups, vendored
  third-party library copies, and files already staged for deletion —
  13GB combined in `_to_delete/` alone)
- `.claude/settings.local.json` (machine-local tool permissions)
- Any file over GitHub's 100MB hard limit (`demo_de.mov` at 181MB appears
  in ~20 locations; a 649MB unnamed file and a 467MB file named `corrupt`
  also exist under output/temp folders)
