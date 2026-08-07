# Reference-Driven Agentic Short-Form Video Generation System — submission layout

MSc AI for Media engineering dissertation artefact (August 2026).

## Key entry points
- `dissertation/paper.tex` — dissertation source of truth
- `dissertation/dissertation_full_draft_v18_20260805.pdf` — current compiled PDF
- `pipeline/app.py` — read-only evidence dashboard (Flask). Run and open the
  homepage; generation and all state-changing routes are disabled (HTTP 403).
- `project_state.json` — central decision-log / state file

## Structure
- `pipeline/` — four-stage pipeline (stage1_analyze … stage5_repair), dashboard,
  generation-unit schema, mode policies
- `outputs/` — executed evidence: runs (`runs/live_test_03_4shots` = Mode A-1
  beach; `runs/mode_c_phase0` = Mode C), audits (pose/mask audit,
  hash-manifested), keyframes, clips, analysis, Mode B assets
  (`outputs/mode_b/`, incl. the ComfyUI-path creative run)
- `reference/`, `reference_videos/`, `video_ref/` — author-created reference
  material and analysis inputs
- `assets/` — identity / look / scene packages used for conditioning
- `scenes_sources/` — raw scene-reference source images
- `mode_d/` — hosted-service demo clips (viggle.ai / wan.video, 4 Aug 2026);
  demos only, not dissertation evidence
- `look/`, `storyboards/`, `docs/` — look packages, storyboard JSON, docs
- root `generate_*.py`, `regen_*.py`, `rerun_*.py`, `promote_*.py` — dated
  working scripts retained as a work record
- `_archive/` — superseded backups and scratch (safe to delete; see its README)

## Evidence rules
Every number in the paper and dashboard traces to decision_log entries,
run summaries, ffprobe output, metrics files or audit manifests.
Hash-manifested evidence packages are never edited in place.
