# 🎬 Reference-Driven Agentic Short-Form Video Generation System

**An MSc dissertation project that turns a reference video into a controllable, repairable generation pipeline — not just another prompt-to-video demo.**

[![Live Dashboard](https://img.shields.io/badge/live%20demo-huggingface.co-orange)](https://huggingface.co/spaces/skye6/video_driven)
[![Status](https://img.shields.io/badge/status-dissertation%20submission-blue)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-green)](#)

---

## 👋 What is this?

Most "video generation" demos are one-shot: type a prompt, get a clip, hope it's good. This project asks a different question — **can a system look at a reference video, understand its structure, and use that understanding to control generation, evaluate its own output, and repair what fails?**

The answer here isn't "yes, perfectly." It's something more honest and more interesting: a working pipeline that decomposes a reference video into inspectable shot-level data, recombines it with a chosen identity/look/scene, generates keyframes and video clips per shot, scores the result on five metrics, and — when something fails — diagnoses *why* and applies a targeted fix instead of just rerolling blindly. Every one of those decisions is logged, so the dissertation's claims are traceable back to real evidence, not vibes.

## 🔴 Live Demo

**→ [huggingface.co/spaces/skye6/video_driven](https://huggingface.co/spaces/skye6/video_driven)**

This is a **read-only evidence dashboard**, not a "type a prompt, get a video" toy. Every state-changing route (upload / generate / reset / repair) is hard-disabled and returns `403` no matter who calls it. It exists so you can click through and see exactly what backs up every number and claim in the dissertation: decision logs, run summaries, generated media, audit manifests.

## 🧩 How it works

```
reference video
     │
     ▼
shot / camera / pose / framing / timing analysis   (Stage 1)
     │
     ▼
beat-aligned, enriched storyboard                  (Stage 2)
     │
     ▼
per-shot generation: keyframe → I2V clip           (Stage 3)
     │
     ▼
five-metric evaluation (identity / pose / framing /
beat alignment / look consistency)                 (Stage 4)
     │
     ▼
diagnose → targeted repair → re-evaluate loop       (Stage 5)
     │
     ▼
final video + decision log (the evidence trail)
```

The Stage 5 loop is the part that makes this "agentic" rather than a linear script: a failed shot doesn't just get rerolled with a new random seed. The system classifies *what* failed — identity drift, weak motion, wrong framing — and applies the matching fix, recording the whole observed-issue → diagnosis → repair-action → retained-result chain in a decision log.

## 🏖️ Two case studies

| | Mode A-1 · Beach | Mode A-2 · Street |
|---|---|---|
| **Question it answers** | Can the system preserve a reference scene while replacing the character/look? | Can reference-derived shot structure be recomposed with a *different* scene? |
| **Status** | Completed evidence | Completed as an identity-and-scene stress test |
| **Reference video** | Yes | No (`reference_video = None` — scene-package replacement) |

Both runs are backed by real decision logs, real generated keyframes and clips, and honest post-hoc diagnostics (ArcFace identity similarity, optical-flow motion energy) — reported as diagnostics, not as automatic pass/fail thresholds.

## 📁 Repository structure

| Path | What's in it |
|---|---|
| `pipeline/` | The four-stage pipeline + the dashboard (`app.py`) + generation-unit schema + mode policies |
| `pipeline/generators/` | The two generation backends: OpenAI Images API + Kling (default), and a free local-GPU path |
| `pipeline/evaluation/` | The five evaluation metrics + repair planner |
| `pipeline/policies/` | Reusable rules extracted from the runs: reference-slot ordering, motion-prompt repair, honest backend-capability limits |
| `outputs/` | Executed evidence — runs, SHA-256-manifested audits, keyframes, clips, analysis |
| `assets/`, `look/`, `storyboards/` | Identity / look / scene conditioning packages |
| `dissertation/` | Paper source (`paper.tex`), chapters, references |
| `docs/` | Architecture notes, run instructions, audit reports |
| `generate_*.py`, `regen_*.py`, `rerun_*.py`, `promote_*.py`, `ablation_*.py` | Dated working scripts, kept as a work record. Every one of them defaults to a dry-run / plan-only mode — nothing spends real API credit without an explicit confirmation flag |

## 📏 Evidence-first, on principle

This isn't a formality — it's the actual design constraint the whole codebase is built around. Every number that appears in the paper or on the dashboard has to trace back to something concrete: a decision-log entry, a run summary, `ffprobe` output, a metrics file, or an audit manifest. Hash-manifested evidence packages are never edited in place — if something in one turns out to be wrong, a new package gets created rather than quietly patching the old one. The dashboard's own safety guard (`ONLINE_DEMO_READ_ONLY`) enforces the same discipline in code: it's a viewer for evidence that already exists, not a live generator.

## 🚀 Running it locally

```bash
git clone https://github.com/skyechiu/reference-driven-video-generation.git
cd reference-driven-video-generation
cp .env.example .env        # fill in your own API keys
pip install -r pipeline/requirements_best.txt
python pipeline/run.py phase0   # feasibility check — run this first
```

Full setup, backend selection (API vs. local GPU), and the evaluation-repair loop are documented in [`docs/PROJECT_RUN_INSTRUCTIONS.md`](docs/PROJECT_RUN_INSTRUCTIONS.md) and [`pipeline/PIPELINE_README.md`](pipeline/PIPELINE_README.md).

## 📄 Dissertation

Full write-up, methodology, and evaluation live in [`dissertation/paper.tex`](dissertation/paper.tex). MSc AI for Media, August 2026.

---

*Built as a single-author MSc dissertation project. The dashboard, pipeline, and every case study in this repo are real, executed, and logged — not mockups.*
