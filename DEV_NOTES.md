# DEV_NOTES — Session Handoff Document
> Last updated: 2026-07-01. Read this before touching any file.

---

## What this project is

**Reference-Driven Agentic Short-Form Video Generation System** — MSc AI for Media dissertation (NCCA Bournemouth, graduating Sept 2026).

One-line: Takes a reference short video + fixed IP character + new scene prompt → decomposes reference into a structured template → regenerates a new 9:16 vertical short using the IP character with an automated evaluation–repair loop.

Two separate input modes (NOT two separate systems — one Flask dashboard):
- **Mode A**: Reference video → shot analysis → IP-conditioned regeneration (photoreal)
- **Mode B**: Natural language → animated storyboard sheet → panel review → JSON → video (animation only)

**The artistic short film *What Is Light* is a separate project — never merge with this system.**

---

## Locked architecture (do not redesign)

Four-stage pipeline around `project_state.json`:
1. Reference Analysis — deterministic tools (PySceneDetect, librosa, MediaPipe)
2. Template Builder — beat-aligned storyboard JSON
3. IP-Conditioned Generation — per-shot, keyframe-first
4. Evaluation & Repair — identity/pose/framing/beat scoring → selective regeneration loop

Tools compute. Agents decide. The feedback loop (Evaluation → Generation) is what makes it agentic.

---

## Critical coding rules — NEVER violate these

| Rule | Detail |
|------|--------|
| Port | **5001** (macOS AirPlay uses 5000) |
| Image model | **`gpt-image-1`** — not gpt-image-2 |
| API keys | Always from `.env` via `python-dotenv`. Never hardcoded. |
| Theme | Light CSS theme everywhere. No `rgba(30,40,60,X)` fills. SVG text must be dark-on-light. |
| Flask routes | Function names must be unique. **Always `grep -n "def <name>" app.py` before adding a route.** Duplicate name → `AssertionError` on startup. |
| Run command | `cd pipeline && python app.py` — NOT `python pipeline/app.py` |
| Mode B scope | Animation only · single character · no photoreal · no multi-strategy analysis |

---

## File structure

```
project_root/
├── CLAUDE.md                   ← this file
├── project_state.json          ← central state (the pipeline's core)
├── pipeline/
│   ├── app.py                  ← entire Flask app + HTML/CSS/JS (~8500+ lines), port 5001
│   ├── stage1_analyze.py       ← Mode A reference analyzer (conservative multi-signal merge)
│   └── .env                    ← API keys (never commit)
├── outputs/
│   └── mode_b/
│       ├── panel_plan.json     ← LLM-generated panel plan
│       └── generated.png       ← Mode B storyboard sheet
├── look/
│   ├── mode_b_ip/
│   │   ├── ip_formal_gown.png     ← Black gown character sheet (hero pose, turnaround, expressions)
│   │   ├── ip_casual_blazer.png   ← Casual blazer character sheet
│   │   └── mode_b_ip.json         ← manifest
│   ├── look2_darkening-self/   ← look2_01 through look2_05
│   └── look3_tailored-self/    ← look3_01 through look3_03
├── reference/
├── reference_videos/
└── assets/
```

---

## CSS theme variables

```css
--bg: #F7F7F5        /* page background */
--surface: #FFFFFF   /* card/panel background */
--tx: #1F1F1F        /* primary text */
--tx2: #4B4B4B       /* secondary text */
--tx3: #8B8B8B       /* muted text */
--accent: #5B5BEF    /* purple accent (Mode B) */
--pass: #1A9C5A      /* green (pass/success) */
--bd: #E5E5E3        /* border */
--r: 8px             /* border radius */
--r-sm: 6px
```

---

## What's been built (as of 2026-07-01)

### Flask dashboard (`pipeline/app.py`)

**System Overview page:**
- SVG flowchart with Mode A and Mode B flows (light theme — all fills are white or accent-tinted)
- 4 clickable expandable stat cards: 8 Models & Tools / 2 Input Modes / 6 Pipeline Steps / 5 Eval Metrics

**Mode A — 6-stage pipeline (nav: s0 through s5):**
- s0: Upload (with run_id isolation — clears state on new upload)
- s1: Reference Analyze (strategy router: Auto / Conservative / Aggressive / Manual)
- s2: Semantic Enrichment (`/api/run-semantic-enrichment`)
- s3: Cut Validation UI
- s4: Storyboard
- s5: Generate

**Mode B — 5 steps:**
- `mb1`: Story Prompt & Template (story textarea + Section B style + C panels + D length + E template cards + **F IP character reference with lightbox**)
- `mb3`: Generate Sheet (Step A: GPT-4o panel plan → Step B: gpt-image-1 sheet)
- `mb4`: Panel Review
- `mb5`: Storyboard JSON
- `mb6`: Run Core Loop
- Hidden stubs: `page-mb2`, `page-mbT` (kept for JS compat, not in nav)

**Mode B templates (JS `ANIM_TEMPLATES` object):**
- `slapstick_6panel` — Slapstick Mischief, rough animation, 6 panels, 9s
- `anime_emotional_4panel` — Anime Emotional Beat, clean anime, 4 panels, 8s
- `animated_dance_8panel` — Dance Pose Sheet, pose storyboard, 8 panels, 8s

**Mode B backend endpoints:**
- `POST /api/mode-b/generate-panel-plan` — GPT-4o; story + template → `outputs/mode_b/panel_plan.json`
- `POST /api/mode-b/generate-sheet` — gpt-image-1 (size=1024x1024, quality=medium); → `outputs/mode_b/generated.png`
- `GET /media/mode-b-ip/<filename>` — serves `look/mode_b_ip/` images

**Key JS globals:**
- `_state` — mirrors project_state.json
- `_selectedAnimTemplate` — currently selected Mode B template ID
- `_state._mbPanelPlan` — in-memory panel plan
- `ANIM_TEMPLATES` — 3 template definitions

---

## Debug history — don't repeat these

**1. Duplicate Flask endpoint (AssertionError on startup)**
Old `mb_generate_sheet` existed at line ~8454; new one added → crash.
Fix: one definition only. Rule: grep before adding.

**2. SVG dark fills on light dashboard**
`rgba(30,40,60,0.9)` fills looked black. Replaced with `#FFFFFF` or `rgba(91,91,239,0.09)`.
Rule: SVG fills must be light. Text must be dark-on-light.

**3. `rm` fails on Desktop mount**
`/sessions/.../mnt/Desktop/` is read-only for delete. `cp` works; user deletes originals in Finder.

---

## Pending tasks

| # | Task | Notes |
|---|------|-------|
| 8 | Cut Validation UI redesign | Suggestion language + per-boundary action buttons + Conservative/Balanced/Aggressive mode switch |
| 9 | Storyboard page redesign | Frame Strip as primary tab, 2–3 keyframes per shot with color |

Phase 0 feasibility test (pose control vs identity) is still the make-or-break technical risk — not yet run.

---

## How to help

- Default: concise, prose answers in casual Chinese for discussion
- English for deliverable text (PPT, resume, docs, code)
- Push back when something is a bad idea; don't just agree
- Flag scope creep and pull back to locked architecture
- When design is good enough → say so and tell to stop planning and build
- Keep dissertation system and *What Is Light* completely separate
