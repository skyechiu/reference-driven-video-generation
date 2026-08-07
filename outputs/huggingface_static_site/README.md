---
title: Reference-Driven Agentic Video Generation — Evidence Dashboard
emoji: 🎬
colorFrom: gray
colorTo: blue
sdk: static
pinned: false
---

# Reference-Driven Agentic Short-Form Video Generation System — static evidence site

This folder is a fully static export of the read-only dashboard (`pipeline/app.py`),
generated on 2026-08-05T19:45:56.346315+00:00 for deployment to a Hugging Face Static Space
(or any static host — GitHub Pages, Netlify, S3, etc.).

## What this is

- A byte-for-byte render of the live dashboard's `/` route (the single-page
  academic evidence viewer), captured in-process via Flask's test client —
  no network calls, no media regeneration, no OpenAI/Kling/Wan/ComfyUI runs.
- All CSS and JS from the live dashboard are preserved inline in `index.html`
  exactly as served; layout, navigation, sidebar and claim-boundary wording
  are unchanged.
- Every image, video, report, CSV, JSON and PDF that the rendered page (and
  its read-only `/api/state`, `/api/looks`, `/api/char-refs`,
  `/api/mode-b/panel-plan` data) actually references has been copied under
  `assets/` and the page has been rewritten to point at the local copies.

## What this is not

- Not a Flask app. There is no backend. `ONLINE_DEMO_READ_ONLY` was `true`
  at export time, and in addition every non-GET `fetch()` call is now
  intercepted client-side by a small safety-net script appended before
  `</body>` — any attempted POST/PUT/DELETE resolves to a synthetic
  `403 Disabled in static read-only export` response instead of hitting the
  network. Generation, upload, reset, repair and other state-mutating
  actions are inert.
- Not a redesign. Nothing about the page content, wording, evidence links
  or claim boundaries was changed — this is a mechanical export.

## Structure

```
index.html                 the full single-page dashboard
pages/README.txt           note on why there are no separate page files
assets/images/              photos, keyframes, contact sheets, look sheets, pose/mask frames
assets/videos/              final/keyframe/clip evidence videos, redacted Mode C audit clips, reference/test clips
assets/reports/             .md / .csv / .pdf evidence (evaluation reports, motion audit report, dissertation PDFs)
assets/data/                .json evidence (decision logs, mode_c metadata, and the 4 read-only API snapshots)
assets/downloads/           .zip evidence (pose/mask audit package)
export_summary.json         machine-readable export manifest (counts, exclusions, missing files)
missing_files_report.md     resources referenced by the page that could not be fetched, and why
```

## Privacy / safety

- No raw or unredacted driving/control video is included. The Mode C
  driving-video audit clips included here (`assets/videos/audit/privacy_redacted_mode_c/...`)
  are the head-pixelated redacted versions already served by the live
  read-only route; the unredacted source files (`mode_c.MP4`, `reference_videos/`,
  `video_ref/`) were never linked by the public page and are not part of this
  export.
- `.env`, `project_state.json` (raw, with local absolute paths),
  `app.py.backup_*` development snapshots, and `_archive/`/`_to_delete/`/
  `__pycache__` working folders are excluded. See `export_summary.json`
  → `excluded_private_files` for the full list.

## Deploying to a Hugging Face Static Space

Unzip `huggingface_static_site.zip` so that `index.html` sits at the **root**
of the Space repo (the zip is built with no enclosing folder). Push the
contents as-is; no build step, `requirements.txt`, or server process is
needed — this is a pure static site.

## Known pre-existing gaps

See `missing_files_report.md`. In short: two `/media/character-look/...`
images and the `/media/look-ref-front` route were already unreachable in the
live app checkout at export time (the former live outside this project
folder; the latter is a documented pre-existing gap, tracked separately in
`codex_dashboard_patch_instructions.md` item 17). No backend logic was
changed to paper over these — the corresponding page elements will show
their broken-media state exactly as they do live today.
