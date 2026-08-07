# Reference-Driven Agentic Short-Form Video Generation System

MSc AI for Media engineering dissertation artefact (August 2026).

**Live evidence dashboard:** https://huggingface.co/spaces/skye6/video_driven
(direct: https://skye6-video-driven.static.hf.space/index.html)

The dashboard is a **read-only evidence viewer**, not an online generation
product — every state-mutating route (upload / generate / reset / repair) is
disabled and returns HTTP 403 regardless of caller. It exists to let a
reader inspect every claim in the dissertation against its underlying
evidence: decision logs, run summaries, generated media, and audit
manifests.

## Overview

This dissertation presents a reference-driven agentic short-form video
generation workflow. The contribution is not a general video generator, but
a traceable pipeline that decomposes reference structure into inspectable
generation units, recombines them with separated identity/look/scene
packages, generates per-shot keyframes and I2V clips, and records
human-gated diagnosis and repair decisions. The completed evidence preserves
shot structure and action intent, while explicitly not claiming exact
frame-level motion transfer or fully automatic metric-driven acceptance.

## Key entry points

- `dissertation/paper.tex` — dissertation source of truth
- `pipeline/app.py` — the dashboard above, as source (Flask, single file)
- `pipeline/PIPELINE_README.md` — pipeline architecture, stage-by-stage
- `docs/PROJECT_RUN_INSTRUCTIONS.md` — how to run the pipeline locally
- `project_state.json` — central decision-log / state file (not committed
  here — see `.gitignore`; every dashboard number traces back to it)

## System

Four-stage pipeline (`pipeline/stage1_analyze.py` → `stage5_repair.py`):
reference-video analysis → beat-aligned enriched storyboard → per-shot
generation (keyframe + I2V clip) → five-metric evaluation → diagnose-and-repair
loop. Every generation attempt is logged with its diagnosis, repair action,
and scores — that decision log is the dissertation's primary evidence.

Two reference-video runs demonstrate the pipeline: a beach scene (Mode A-1,
reference-scene preservation) and a street scene (Mode A-2 stress test,
scene-package replacement). A separate driving-video backend (Mode C, Wan2.2
Animate) was tested as a feasibility probe.

## Structure

- `pipeline/` — four-stage pipeline, dashboard, generation-unit schema, mode
  policies (`pipeline/generators/`, `pipeline/evaluation/`,
  `pipeline/policies/`)
- `outputs/` — executed evidence: runs, audits (SHA-256-manifested where
  noted), keyframes, clips, analysis
- `assets/`, `look/`, `storyboards/` — identity / look / scene packages used
  for conditioning
- `dissertation/` — paper source, chapters, references
- `docs/` — architecture notes, run instructions, audits
- `scripts/generation/` — dated generation/regeneration working scripts,
  retained as a work record; each defaults to a dry-run / plan-only mode and
  requires an explicit confirmation flag before making any paid API call
- `scripts/export/` — static-site exporter (`export.py`, `readme_and_zip.py`)
  that produces the Hugging Face static deployment from `pipeline/app.py`
- `scripts/maintenance/` — dated one-off dashboard patch scripts
- `scripts/extract_start_end_poses.py`, `scripts/ablation_analyze.py` —
  single-purpose analysis/evaluation scripts

## Evidence rules

Every number in the paper and dashboard traces to decision log entries, run
summaries, ffprobe output, metrics files, or audit manifests. Hash-manifested
evidence packages are never edited in place — a correction creates a new,
separately labelled package rather than altering the old one.

## Running locally

See `docs/PROJECT_RUN_INSTRUCTIONS.md` and `pipeline/PIPELINE_README.md` for
setup, backend selection (API vs. local GPU), and the evaluation-repair loop.
`.env.example` lists the required API key names; the pipeline never runs
generation calls without an explicit confirmation step.
