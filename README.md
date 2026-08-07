# 🎬 Reference-Driven Short-Form Video Generation
### Auditable Per-Shot Orchestration over Closed Generative APIs

> **MSc Artificial Intelligence for Media Dissertation**  
> Bournemouth University (NCCA), 2026

[![Live Evidence Dashboard](https://img.shields.io/badge/Live-Evidence%20Dashboard-EA8A39)](https://huggingface.co/spaces/skye6/video_driven)
[![Status](https://img.shields.io/badge/Status-Dissertation%20Submission-C65D3D)](#)
[![Python](https://img.shields.io/badge/Python-3.10+-DAA24C)](#)

---

# ✨ Overview

This repository contains the implementation, experimental evidence, and dissertation materials for a research project investigating **reference-driven short-form video regeneration**.

Rather than treating video generation as a single prompt-to-video process, the project explores whether a reference video can be decomposed into **explicit shot-level generation units**, regenerated through separated conditioning, and evaluated using an auditable, human-gated repair workflow.

The contribution is **not a new generative model**.

Instead, the work proposes an orchestration framework that makes generation decisions, failures, repairs, and retained outputs transparent and traceable while operating entirely on **closed commercial generative APIs**.

---

# 🎯 Research Question

> **How can the structure of a reference short-form video be decomposed and reused to guide controllable regeneration while keeping every generation decision, failure, and repair inspectable?**

---

# 🌐 Live Evidence Dashboard

👉 **https://huggingface.co/spaces/skye6/video_driven**

The online dashboard is a **read-only evidence viewer**.

It exposes the experimental evidence supporting the dissertation, including:

- 🎞 Reference analysis
- 🧩 Generation units
- 🎨 Identity / Look / Scene packages
- 📊 Evaluation evidence
- 🛠 Human-gated repair records
- 📑 Decision logs
- 📈 Experimental reports
- ⚖️ Claim boundaries and limitations

State-changing operations (generation, upload, repair, reset, etc.) are intentionally disabled in the public deployment.

---

# 🏗 Method Overview

```text
Reference Video
        │
        ▼
Shot-level Analysis
        │
        ▼
Structured Generation Units
        │
        ▼
Separated Conditioning
(Identity / Look / Scene)
        │
        ▼
Keyframe Generation
        │
        ▼
Image-to-Video Generation
        │
        ▼
Human Review
        │
        ▼
Diagnosis
        │
        ▼
Targeted Repair
        │
        ▼
Decision Log
        │
        ▼
Retained Output
```

Unlike a conventional one-shot workflow, unsuccessful generations are **diagnosed and selectively repaired**, with every decision recorded as part of an auditable evidence trail.

---

# 🧪 Experimental Evidence

The repository contains multiple categories of evidence with different maturity levels.

| Evidence | Status |
|-----------|--------|
| 🟢 Reference-scene preservation (Mode A-1) | Completed |
| 🟢 Scene-package replacement stress test | Completed |
| 🟡 Motion diagnostics & repair | Completed (post-hoc) |
| 🟡 ArcFace identity diagnostics | Completed (post-hoc) |
| 🟡 Pose / mask feasibility audit | Completed |
| 🟠 Driving-video backend (Mode C) | Feasibility / Quality WIP |
| 🔵 Storyboard extension (Mode B) | Experimental |
| ⚪ Hosted-service comparison | Supplementary |
| ⚪ Planned extensions | Not implemented |

The dissertation explicitly distinguishes:

- Executed evidence
- Post-hoc diagnostics
- Log-reconstructed observations
- Feasibility studies
- Planned future work

---

# 📂 Repository Structure

```text
.
├── pipeline/           Core orchestration and dashboard
├── scripts/            Analysis, evaluation and export utilities
├── dissertation/       LaTeX dissertation source
├── docs/               Technical documentation
├── assets/             Public project assets
├── look/               Look conditioning
├── storyboards/        Structured storyboard assets
├── outputs/            Executed evidence
└── README.md
```

### Main Components

| Directory | Description |
|------------|-------------|
| `pipeline/` | Dashboard, orchestration workflow, generation-unit schema |
| `pipeline/generators/` | Image and video generation backends |
| `pipeline/evaluation/` | Evaluation utilities and diagnostics |
| `pipeline/policies/` | Prompt policies and repair rules |
| `scripts/` | Standalone analysis and export scripts |
| `outputs/` | Generated evidence and audit artefacts |
| `dissertation/` | Dissertation source |
| `docs/` | Technical documentation |

---

# 📊 Evaluation

The implemented evaluation considers five control dimensions:

- 👤 Identity consistency
- 🧍 Character pose / motion
- 📐 Framing consistency
- 🎵 Temporal / beat alignment
- 🎨 Look consistency

The repository differentiates between:

- automated diagnostics
- post-hoc analysis
- human review
- targeted repair
- retained evidence

Automatic metric-driven acceptance is **not claimed** as fully executed.

Human review remains the final acceptance authority throughout the completed dissertation evidence.

---

# 📖 Evidence Integrity

Every reported result is expected to trace back to one or more of the following:

- 📄 `decision_log.json`
- 📊 evaluation reports
- 🎬 generated outputs
- 📈 run summaries
- 🔍 audit manifests
- 🔐 SHA-256 evidence packages

Evidence packages are treated as immutable records.

Derived analyses are stored separately rather than modifying existing evidence.

---

# 🚀 Running Locally

Clone the repository:

```bash
git clone https://github.com/skyechiu/reference-driven-video-generation.git
cd reference-driven-video-generation
```

Create the environment:

```bash
python -m venv .venv
source .venv/bin/activate

pip install -r pipeline/requirements_best.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Inspect available commands:

```bash
python pipeline/run.py --help
```

Detailed setup instructions are available in:

- `docs/PROJECT_RUN_INSTRUCTIONS.md`
- `pipeline/PIPELINE_README.md`

---

# ⚖️ Scope

This repository **does not claim**:

- exact frame-level motion transfer
- fully autonomous repair
- production-ready hard video control
- implementation of every planned system extension

The supported claim is narrower:

> **Reference-derived shot structure, separated conditioning packages, and logged human-gated repair provide a more inspectable workflow for short-form video regeneration over closed generative APIs.**

---

# 📄 Dissertation

**MSc Artificial Intelligence for Media**

Bournemouth University (NCCA)

2026

The dissertation source is available under:

```
dissertation/
```

---

# 📌 Citation

If you reference this repository, please cite the accompanying MSc dissertation.

---

Built as a single-author MSc research project.

The dashboard, experimental evidence, and decision logs included in this repository are derived from executed research runs and are accompanied by explicit evidence-status labels where applicable.
