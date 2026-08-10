# Reference-Driven Short-Form Video Generation with Auditable Per-Shot Orchestration

**MSc AI for Media dissertation project investigating reference-structured video regeneration, separated conditioning, and human-gated targeted repair over closed generative APIs.**

[![Live Evidence Dashboard](https://img.shields.io/badge/evidence%20dashboard-Hugging%20Face-EA8A39)](https://huggingface.co/spaces/skye6/video_driven)
[![Project Status](https://img.shields.io/badge/status-MSc%20dissertation-CC6654)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-DAA24C)](#)

---

## Live evidence dashboard

**[Open the read-only dashboard →](https://huggingface.co/spaces/skye6/video_driven)**

The deployed website is an **evidence viewer**, not a public generation service.

It exposes curated dissertation evidence including:

- reference-video analysis
- generated keyframes and clips
- scene and identity packages
- decision-log records
- post-hoc evaluation results
- repair evidence
- limitations and claim boundaries

State-changing operations such as generation, upload, reset, and repair are disabled in the public deployment.

The dashboard is intended to make the dissertation's claims traceable to the corresponding artefacts rather than to provide an unrestricted generation interface.

---

## Overview

This repository contains the implementation and supporting evidence for an MSc dissertation on **reference-driven short-form video generation**.

The project investigates whether a reference video can be decomposed into inspectable shot-level structure and then regenerated using separately controlled identity, look, scene, framing, and action information.

Rather than treating generation as a single prompt-to-video operation, the system represents each shot as an explicit generation unit, records intermediate decisions, and supports human-gated diagnosis and targeted repair when generated outputs fail to satisfy the intended structure or appearance.

The primary research contribution is therefore not a new generative model. It is an **auditable orchestration workflow for controlling and evaluating generation over closed image and video APIs**.

### Research question

> How can the structure of a reference short-form video be decomposed and reused to guide character-consistent regeneration while keeping generation decisions, failures, and repairs inspectable?

---

## Method

The primary workflow can be summarised as:

```text
Reference video
      │
      ▼
Shot-level structural analysis
      │
      ├── shot boundaries
      ├── framing
      ├── camera motion
      ├── character motion
      ├── timing / beat information
      └── semantic shot description
      │
      ▼
Structured generation units
      │
      ├── reference structure
      ├── identity package
      ├── look package
      └── scene package
      │
      ▼
Approved keyframe generation
      │
      ▼
Image-to-video generation
      │
      ▼
Human review + diagnostic evidence
      │
      ▼
Diagnosis-specific repair where required
      │
      ▼
Retained output + decision log
```

The implemented workflow is **human-gated**.
Automatic metric-driven acceptance and fully autonomous repair were designed and partially instrumented, but are not claimed as fully executed in the dissertation evidence.

---

## Auditable generation units

A central design decision is to avoid representing the project as a single monolithic generation prompt.

Each shot retains explicit provenance for:

* reference-derived structure
* identity conditioning
* look conditioning
* scene conditioning
* prompt construction
* generation attempts
* review outcome
* diagnosis
* repair action
* retained result

This makes it possible to inspect why a shot was regenerated and what changed between attempts.

The decision log therefore functions as both:

1. runtime state for the orchestration workflow; and
2. an evidence record for post-hoc analysis.

---

## Primary experimental evidence

### Reference-scene preservation

The main completed dissertation case uses an author-created AI-generated beach reference clip as the structural source.

The workflow decomposes the reference into four shot-level generation units and regenerates the sequence using a selected synthetic identity and look while preserving reference-derived shot order, framing logic, timing, and action intent.

This case provides the primary end-to-end evidence for the dissertation.

### Scene-package replacement

A separate street experiment evaluates the use of a different environment package while retaining controlled identity and look information.

This result is reported as **scene-package replacement evidence and a stress test of identity/scene conditioning**.
It is not presented as a completed reference-video structure-transfer run.

### Driving-video backend

A separate Mode C branch investigates person replacement using driving-video conditioning through a Wan2.2/Wan2GP backend.

This branch is treated as **feasibility / quality-WIP evidence**, not as part of the keyframe-first Mode A/B orchestration core.

### Planned and experimental extensions

Additional storyboard-driven and hosted-service branches are retained in the repository and dashboard where relevant, but their status is explicitly distinguished from completed dissertation evidence.

---

## Evaluation and repair evidence

The evaluation design considers five control dimensions:

* identity consistency
* pose / character-motion correspondence
* framing consistency
* timing / beat alignment
* look consistency

Not all of these were executed as automatic in-loop acceptance metrics.

The dissertation distinguishes between:

* **executed generation evidence**
* **post-hoc diagnostics**
* **log-reconstructed observations**
* **feasibility evidence**
* **planned or partially instrumented evaluation**

Executed post-hoc diagnostics include, where applicable:

* ArcFace cosine similarity for face-visible shots
* optical-flow motion-energy comparison
* pose / mask feasibility audits
* human-gated visual review

These metrics are used as diagnostic evidence rather than being presented as a fully automatic acceptance authority.

---

## Human-gated targeted repair

A failed shot is not treated simply as a request for another random sample.

The workflow records a repair chain of the form:

```text
Observed issue
    ↓
Diagnosis
    ↓
Targeted intervention
    ↓
Re-generated candidate
    ↓
Human review
    ↓
Retained result / further action
```

Examples of recorded failure classes include:

* identity drift
* incorrect look or outfit
* framing mismatch
* weak character motion
* prompt contamination
* scene inconsistency

The implemented dissertation workflow retains **human review as the final acceptance authority**.

This distinction is important: the project demonstrates inspectable diagnosis and selective repair, but does not claim a fully autonomous metric-driven repair agent.

---

## Evidence integrity

The repository follows an evidence-first reporting policy.

Quantitative values included in the dissertation must be traceable to an artefact such as:

* `decision_log.json`
* generated run metadata
* evaluation output
* `ffprobe` results
* audit reports
* SHA-256 manifests

Hash-manifested evidence packages are not edited in place.
Where additional analysis is required, a new derived artefact or package is created so that the original evidence remains reproducible.

This policy also defines the public dashboard boundary: the deployed site serves curated evidence but does not expose private working files or enable state-changing generation operations.

---

## Repository structure

```text
.
├── pipeline/              Core orchestration and dashboard source
├── scripts/               Generation, export, maintenance and analysis scripts,
│                          organised by purpose (single-file categories kept bare)
├── docs/                  Architecture, execution and audit documentation
├── assets/                Public project assets
├── look/                  Look-conditioning material
├── storyboards/           Structured storyboard assets
├── public_evidence/       Curated evidence set (full raw runs kept out of this
│                          public repository -- see its own README)
├── README.md
├── requirements...
└── .gitignore
```

### Main components

| Path | Purpose |
| ---- | ------- |
| `pipeline/` | Core orchestration logic, dashboard, generation-unit schema and mode policies |
| `pipeline/generators/` | Image/video generation backend interfaces |
| `pipeline/evaluation/` | Evaluation and diagnostic utilities |
| `pipeline/policies/` | Reusable conditioning and repair policies |
| `scripts/generation/` | Per-shot keyframe/clip generation and targeted-repair scripts, dry-run by default |
| `scripts/export/` | Static dashboard/export tooling (`export.py`, `readme_and_zip.py`) |
| `scripts/maintenance/` | Dated one-off dashboard patch scripts |
| `scripts/ablation_analyze.py`, `scripts/extract_start_end_poses.py` | Single-purpose evaluation/analysis scripts, kept at the top of `scripts/` rather than in a one-file subfolder |
| `public_evidence/` | Curated evidence set: final videos, approved keyframes, decision logs, evaluation summaries, and the pose/mask audit contact sheet for both main runs. The complete raw run archive (every attempt, intermediate file, and full audit) is kept locally / in the university submission rather than published here. |
| `docs/` | Architecture, reproducibility and project documentation |

The repository also contains dated experimental scripts where they are required to preserve the provenance of executed runs. These are retained as research records rather than presented as the primary public API.

---

## Running locally

### 1. Clone the repository

```bash
git clone https://github.com/skyechiu/reference-driven-video-generation.git
cd reference-driven-video-generation
```

### 2. Create the environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r pipeline/requirements_best.txt
```

`requirements_best.txt` is the API-based backend (gpt-image-1 + Kling) that the
dissertation evidence was generated with, and needs no local GPU. A separate
`pipeline/requirements_free.txt` documents an alternative local-GPU backend
(InstantID + CogVideoX/Wan2.1); see that file's header for its own setup steps.

### 3. Configure credentials

```bash
cp .env.example .env
```

Add only the credentials required for the backend you intend to use.
Do not commit `.env`.

### 4. Inspect the available pipeline commands

```bash
python pipeline/run.py --help
```

Where supported, dry-run or planning modes should be used before invoking paid or remote generation backends.

Detailed execution instructions are available in:

* [`docs/PROJECT_RUN_INSTRUCTIONS.md`](docs/PROJECT_RUN_INSTRUCTIONS.md)
* [`pipeline/PIPELINE_README.md`](pipeline/PIPELINE_README.md)

---

## Reproducibility boundary

Several generation stages depend on closed or hosted APIs.
Consequently, exact bitwise reproduction of every generated frame cannot be guaranteed.

The repository instead preserves:

* prompts and structured conditioning
* reference-slot order
* model/backend information where available
* run settings
* timestamps
* generation attempts
* retained outputs
* evaluation artefacts
* decision records

The aim is **procedural and evidential reproducibility** rather than deterministic reproduction of stochastic closed-model outputs.

---

## Scope and limitations

This repository should not be interpreted as evidence of:

* exact frame-level motion transfer
* fully autonomous metric-driven repair
* production-ready hard video control
* use of skeleton/mask conditioning in the final beach or street outputs
* implementation of every planned system extension

The implemented evidence supports a narrower claim:

> reference-derived shot structure, separated conditioning packages, per-shot generation, and logged human-gated repair can provide a more inspectable and controllable workflow for short-form video regeneration over closed generative APIs.

---

## Dissertation

The dissertation manuscript itself is submitted separately to the university and is not
included in this public repository. This repository documents the implementation,
evidence, and evaluation infrastructure that the dissertation's claims are traced back to.

**MSc Artificial Intelligence for Media**
Bournemouth University / NCCA
2026

---

## Project status

This repository represents the research implementation associated with the MSc dissertation.

Evidence is deliberately labelled according to its maturity:

* **Completed evidence**
* **Post-hoc diagnostic**
* **Log-reconstructed evidence**
* **Feasibility / quality WIP**
* **Experimental extension**
* **Planned / not implemented**

These labels should be used when interpreting both the repository and the public evidence dashboard.
