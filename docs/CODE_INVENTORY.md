# Code Inventory

Generated 2026-08-07. Scope: full repository at
`~/Desktop/Reference-Driven Agentic Short-Form Video Generation System`.

Method: `find` over the whole tree for the requested extensions, with the
known media/output/cache/vendor directories pruned from the primary scan,
then a second pass specifically inside those pruned directories to catch any
stray code files (see §3). File-by-file purposes below are based on reading
each file's header/docstring and, for the smaller ones, the full source.

- **In-scope code/config/doc files found: 97**
- Everything else in the repo (images, video, model checkpoints, zips, PDFs,
  generated HTML exports, `.DS_Store`, etc.) is media/binary/generated and is
  not itemized file-by-file here — see `docs/GITHUB_PREP_REPORT.md` for the
  size and privacy audit of those.

Legend for **Class**: `source` (hand-written code), `script` (one-off/CLI
utility), `config` (settings/deps), `generated` (produced by running the
pipeline, not hand-authored), `doc` (markdown/docs), `archive` (superseded
copy kept for reference).

---

## 1. Project root

| Path | Type | Purpose | Class | Commit? | Reason |
|---|---|---|---|---|---|
| `CLAUDE.md` | md | Session handoff / project instructions | doc | yes | Core project doc |
| `DEV_NOTES.md` | md | Same byte size as `CLAUDE.md` — appears to be a duplicate copy | doc | maybe | Confirm it isn't stale duplicate before committing both |
| `MASTER_INSTRUCTIONS_20260805.md` | md | Working instruction sheet from an earlier session (submission checklist, key numbers, remote-GPU notes) | doc | maybe | Useful provenance record, but written as internal working notes, not a public-facing doc — your call |
| `README_SUBMISSION.md` | md | Repo layout guide for submission | doc | yes | |
| `codex_dashboard_patch_instructions.md` | md | Instructions written for a different coding assistant to patch the dashboard | doc | maybe | Reveals internal multi-agent workflow; not sensitive, but you may not want it public |
| `codex_text_selfcheck_20260805.md` | md | Self-check notes on wording/claims | doc | maybe | Same as above |
| `ablation_analyze.py` | py | Optical-flow metrics + CSV/summary/table generator for the repair ablation | source | yes | No secrets, no hardcoded paths of concern |
| `ablation_blind_reroll_generate.py` | py | Generates the blind-reroll condition for the repair ablation (gpt-image-1 + Kling) | source | yes | Reads keys from `.env`, no hardcoded secrets |
| `export.py` | py | Flattens the read-only Flask dashboard into a static site via Flask's test client (no network calls) | source | yes | Explicitly excludes `mode_c.MP4`/raw control video from the export (see line ~313) |
| `extract_start_end_poses.py` | py | Extracts start/mid/end pose frames from the reference video (local only, MediaPipe) | source | yes | |
| `generate_shot001.py` / `002` / `003` / `004.py` | py | Per-shot keyframe generation for the beach run (`live_test_03_4shots`) | source | yes | Hardcoded prompts, no secrets |
| `generate_street_run.py` | py | Main street-scene 4-shot keyframe + Kling pipeline (`dry_run`/`keyframes_only`/`full_auto`) | source | yes | `RUN_MODE` defaults to `full_auto` — reviewers should notice this runs real API calls if executed as-is |
| `generate_street_start_end.py` | py | Graded pose-guided start/end keyframes for the street scene (archived experiment) | source | yes | |
| `patch_color_unification.py`, `patch_h1_letterspacing.py`, `patch_interaction_polish_round2.py`, `patch_metric_motion_v7_20260806.py`, `patch_mobile_hero_scroll_fix.py`, `patch_mobile_html_body_root_fix.py`, `patch_mobile_layout_clip_fix.py`, `patch_mobile_scroll_debug_v4.py`, `patch_modeD_and_mapbg.py`, `patch_playsinline_20260806.py`, `patch_quality_pass.py`, `patch_scroll_and_mute_20260806.py` (12 files) | py | One-off mechanical find/replace patches against `pipeline/app.py`; each writes its own timestamped backup before editing | script | maybe | Legitimate change history, but redundant once the changes are actually in `app.py` — keeping them documents *how* the dashboard evolved; fine to commit if you want that history, fine to drop if you'd rather just have the current `app.py` |
| `project_state.json` | json | Live pipeline state / decision log | generated | **no** | Contains ~20 hardcoded `/Users/test/...` absolute paths (see report) |
| `project_state.last_valid.json` | json | Backup of the above | generated | **no** | Same issue |
| `promote_motion_v2.py` | py | Promotes the repaired motion clips to the official street run, rebuilds the final video | source | yes | |
| `readme_and_zip.py` | py | Builds the README for the static-site export and zips it | source | yes | Itself documents the privacy exclusions (mode_c.MP4, reference_videos/, video_ref/) |
| `regen_anchor.py`, `regen_shot001_004_v2.py`, `regen_shot001_3q.py`, `regen_shot002_004.py`, `regen_two_anchors.py` | py | Targeted keyframe repair scripts for specific shots | source | yes | |
| `rerun_street_kling_001_003.py` | py | Shot-scoped Kling motion rerun (the "targeted repair" for street shot_001/003) | source | yes | `CONFIRM_RUN = True` is currently hardcoded — flag before anyone else clones and runs it |
| `run_kling_i2v.py` | py | Submits the 4 beach keyframes to Kling I2V | source | yes | |
| `pipeline_overview.html` | html | Standalone HTML overview/diagram of the pipeline | generated or source (unconfirmed) | maybe | Not opened in full during this audit — check whether it's hand-authored or a one-time export before committing |
| `.claude/settings.local.json` | json | Local Claude Code tool-permission settings | config | **no** | Machine-local settings, not project source |
| `tech_stack.xlsx`, `tech_stack_EN.xlsx` | xlsx | Tech stack spreadsheet | doc | yes | Not a code file per your extension list, listed for completeness |
| `dissertation deck academic 1.pptx` | pptx | Slide deck | doc | maybe | Same |

---

## 2. `dissertation/`

| Path | Type | Purpose | Class | Commit? | Reason |
|---|---|---|---|---|---|
| `dissertation/paper.tex` | tex | Dissertation source of truth | source | maybe | Your academic work — your call whether to publish the thesis text alongside the code |
| `dissertation/references.bib` | bib | Bibliography | source | maybe | Same |
| `dissertation/dissertation_ch3-4_cvpr.tex` | tex | Earlier chapter draft in a different (CVPR) template | archive | maybe | Superseded by `paper.tex`; keep only if you want the history |
| `dissertation/README.md` | md | Dissertation folder readme | doc | yes | |
| `dissertation/chapters/00_abstract.md` … `07_appendix.md` (8 files) | md | Chapter drafts in Markdown (predate/parallel the LaTeX) | doc | maybe | Same call as `paper.tex` |
| `dissertation/论文检查报告_20260805.md` | md | Paper QA/consistency report (Chinese) | doc | maybe | Internal working note |

---

## 3. `docs/`

| Path | Type | Purpose | Class | Commit? | Reason |
|---|---|---|---|---|---|
| `docs/MODE_A_REUSABLE_POLICIES.md` | md | Documents the `pipeline/policies/` extraction | doc | yes | |
| `docs/MODE_C_CONDITION_A_AUDIT.md` | md | Audit trail for the Mode C feasibility probe, references `mode_c.MP4` by name | doc | yes | Referencing the filename is fine; the file itself must not be committed (see report) |
| `docs/PROJECT_RUN_INSTRUCTIONS.md` | md | How to run the pipeline | doc | yes | |

---

## 4. `pipeline/` — core pipeline + dashboard

| Path | Type | Purpose | Class | Commit? | Reason |
|---|---|---|---|---|---|
| `pipeline/app.py` | py | 1.85MB single-file Flask dashboard (dissertation evidence viewer). `ONLINE_DEMO_READ_ONLY` guard; state-mutating routes return 403 | source | yes | Large but is real source, not generated — fine for git (see report for the *backups*, which are not fine) |
| `pipeline/app.py.backup_*` (~55 files, ~1.6–1.85MB each) | py | Auto-generated timestamped snapshots from the `patch_*.py` scripts | generated | **no** | ~90MB+ of redundant snapshots; git history replaces this once the repo exists |
| `pipeline/_gen_shot001.py` | py | Small draft/scratch script, appears to duplicate `generate_shot001.py`/`outputs/_generate_shot001.py` | script | no | Looks like a leftover draft; recommend confirming it's not needed and removing rather than committing |
| `pipeline/config.py` | py | Central config: paths, `.env`-sourced API keys, thresholds, backend selection | source | yes | Contains one hardcoded `/Users/test/...` path (line 36, legacy/unused field) — see report |
| `pipeline/state.py` | py | Reads/writes `project_state.json`, decision-log manager | source | yes | |
| `pipeline/run.py` | py | CLI entry point (`phase0`/`init`/`analyze`/`template`/`generate`/`evaluate`/`repair`/`all`) | source | yes | |
| `pipeline/stage1_analyze.py` | py | Shot cuts (PySceneDetect) + beats (librosa) + pose (MediaPipe) | source | yes | |
| `pipeline/stage2_template.py` | py | Beat-aligned enriched storyboard JSON builder | source | yes | |
| `pipeline/stage3_generate.py` | py | Per-shot generation orchestrator, backend-agnostic | source | yes | |
| `pipeline/stage4_evaluate.py` | py | Five-metric evaluator (identity/pose/framing/beat/look) | source | yes | |
| `pipeline/stage5_repair.py` | py | Evaluate→diagnose→repair→re-evaluate loop — the agentic core | source | yes | |
| `pipeline/generation_unit_schema.py` | py | Canonical generation-unit schema shared across Mode A/B/C | source | yes | |
| `pipeline/mode_a_policy_service.py` | py | Wires `policies/` into per-shot decisions; makes no API calls | source | yes | |
| `pipeline/dance_analyzer.py` | py | v0.1 dance/motion detection & key-pose segmentation | source | yes | |
| `pipeline/phase0_test.py` | py | Identity-vs-pose feasibility test | source | yes | |
| `pipeline/PIPELINE_README.md` | md | Architecture doc: quick start, two backends, metrics, ablation instructions | doc | yes | |
| `pipeline/requirements_best.txt`, `pipeline/requirements_free.txt` | txt | Dependencies for the API backend vs. the local-GPU backend | config | yes | |
| `pipeline/models/pose_landmarker_full.task` | binary | MediaPipe pose model (9.4MB) | generated/vendor | maybe | Not a code file; consider Git LFS or a download-on-setup step instead of committing the binary |

### `pipeline/generators/`
| Path | Purpose | Class | Commit? |
|---|---|---|---|
| `__init__.py` | package marker | source | yes |
| `base.py` | Abstract `GeneratorBase` interface | source | yes |
| `api_gen.py` | OpenAI Images API + Kling backend (main path) | source | yes |
| `local_gen.py` | InstantID + CogVideoX/Wan2.1 local-GPU backend | source | yes |
| `chatgpt_gen.py` | Deprecated stub — raises `ImportError` on import, points to `api_gen.py` | source | yes |

### `pipeline/evaluation/`
| Path | Purpose | Class | Commit? |
|---|---|---|---|
| `__init__.py` | package marker | source | yes |
| `auto_repair_harness.py` | Safe dry-run harness for Stage-4 eval/repair; reads existing artefacts only | source | yes |
| `framing_evaluator.py` | Reads human-coded framing acceptance from the decision log | source | yes |
| `identity_evaluator.py` | Reuses recorded ArcFace diagnostics; never runs a face model | source | yes |
| `metric_status.py` | Shared metric-result schema (VERIFIED/COMPUTED_LOCAL/PENDING) | source | yes |
| `pose_evaluator.py` | Reports pose-evidence availability without running pose estimation | source | yes |
| `repair_planner.py` | Produces non-executing repair proposals only | source | yes |
| `timing_evaluator.py` | Compares recorded shot durations against existing clip metadata via ffprobe | source | yes |

### `pipeline/policies/`
| Path | Purpose | Class | Commit? |
|---|---|---|---|
| `__init__.py` | package marker | source | yes |
| `backend_limits.py` | Documents honest capability limits of current backends | source | yes |
| `evaluation_policy.py` | Motion-evaluation & repair-priority thresholds | source | yes |
| `motion_policy.py` | Kling motion-prompt policy (the damping-words fix, generalised) | source | yes |
| `reference_policy.py` | Reference-image slot ordering & identity-anchor policy | source | yes |

### `pipeline/modes/mode_c/phase0/`
| Path | Purpose | Class | Commit? |
|---|---|---|---|
| `README_PHASE0.md` | Explains the Phase 0 driving-segment setup, names `test2.mov`/`mode_c.MP4` by filename | doc | yes | Filenames-as-text are fine; the referenced media itself is excluded |
| `measure_phase0.py` | Phase 0 measurement script | source | yes | |
| `run_phase0.sh` | Shell entry point for the Phase 0 run | source | yes | |
| `setup_phase0.sh` | Environment setup for Phase 0 | source | yes | |

---

## 5. Excluded-but-contains-code-like-files (directories you told me to exclude from the inventory, flagged here per your instructions because they do contain code)

| Directory | What's actually in there | Recommendation |
|---|---|---|
| `_archive/app_py_backups/` | 2 more `app.py` snapshots | Superseded backups — don't commit |
| `_archive/scratch/` | 3 scratch `.py` files (`_dry_run_test.py`, `patch_ref_tmpl.py`, `stress_test_state.py`) | Scratch/experimental — don't commit unless you want the history |
| `_export_tmp/vendor2_ready/` and `_export_tmp/vendor2_ready_v2/` | Full vendored copies of Flask, Jinja2, Werkzeug, Click, itsdangerous, blinker, markupsafe (~150 files) | Third-party library source bundled for the static export step. Should be a `pip install` step, not committed source — these are other projects' code with their own licenses |
| `_to_delete/` | 13GB: duplicate vendored libs (same as above, twice more), ~19 stale `huggingface_static_site_pre_*` export snapshots, a handful of `patch_*_tmp_used.py`/`lora_readme_tmp*.py` one-off scripts, a 649MB unnamed file (`zid9czoN`) | Everything here was already moved aside for you to delete per your own earlier request — none of it should be committed |
| `outputs/_gen001.py`, `outputs/_generate_shot001.py` | Stray early-draft scripts sitting inside the output/data folder | Don't commit — duplicates of root-level `generate_shot001.py`; recommend moving out of `outputs/` if you want to keep them |
| `outputs/huggingface_static_site/index*.html` | Generated static-site output (3 HTML files) | Generated, not source — don't commit (the *script* that generates them, `export.py`, is already in the main inventory) |

---

## 6. Notable non-code content (for context, not itemized individually)

`outputs/` (2.2GB), `assets/` (40MB), `look/` (26MB), `reference/` (61MB), `reference_videos/` (59MB), `video_ref/` (470MB), `scenes_sources/` (8MB), `test/` (37MB), `mode_d/` (4.9MB), `mode_c.MP4` (44MB) — all media/generated evidence, not source code. Full privacy/size treatment is in `docs/GITHUB_PREP_REPORT.md`.
