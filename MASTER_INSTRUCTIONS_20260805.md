# Master Instruction Sheet — dissertation + dashboard
> Consolidated from the Claude working session of 3–5 Aug 2026.
> Submission deadline: ~10 Aug 2026. Source of truth: `dissertation/paper.tex`.

---

## 0. Ground rules (do not violate)

1. Executed-versus-pending: no number enters the dissertation unless traceable to a log, ffprobe, metrics file, or `decision_log.json`.
2. ArcFace values are **cosine similarity**, never "distance". 0.374 / 0.227 / mean 0.301.
3. Motion-repair values are **14→51% and 19→47%** (authority: `decision_log.json` → `recovered_motion_pct`). 52/48 was a transcription error, already corrected everywhere.
4. The completed street video is **scene-package replacement**, never "reference-structure transfer". The start/end skeleton branch is a **tested + archived negative result**.
5. The beach reference is the **author-created AI-generated clip**, a structural source only. "What Is Light" must not appear anywhere (verified 0 hits in all sources).
6. Never edit files inside hash-manifested evidence packages. Fixes are display-layer or paper-layer only.
7. Never claim: exact frame-level motion transfer · production-ready hard control · skeleton/mask drove final outputs · Mode D implemented.

---

## 1. Dissertation — already completed (record; no action)

All in `dissertation/paper.tex`, compiles clean (45 pp, v15):

- Placeholders removed: student-number line deleted, supervisor name genericised, §3.2.1 author-note (What Is Light) deleted.
- Abstract: "cross-scene structure transfer" → "scene-package replacement"; face-embedding metric wording.
- ArcFace terminology standardised in §1.5, §2.5, §3.1, §3.6 table, §4.8 (defs + headers, higher-is-better), §4.8.1, §4.15.1, §6.2.
- §3.6.3, §4.7, §4.10, §4.16 rewritten to: in-loop scoring pending; ArcFace computed **post-hoc** (§4.8.1); DWPose/framing/beat pending; §4.9 is a log reconstruction.
- §4.2 status table: ArcFace row = Executed (post-hoc diagnostic).
- Figure 3.10 text/caption: "risk assessed; scoped fallback adopted" (PNG already correct).
- §4.13 "(real footage)" → "(the author-created reference clip)"; §5.3 consent paragraph rewritten (Mode C driving video = only real-person material, consented, anonymised).
- **§4.11.1 added**: Reference-control pose/mask audit (12 samples, 9/12, shot_003 `unavailable_no_pose_seed`, MediaPipe reuse + pose-seeded OpenCV GrabCut, SHA-256-manifested, post-hoc label). + Table 4.18 + new Figure 4.2 (contact sheet; old 4.2→4.3, 4.3→4.4, refs updated). + §3.5.5 paragraph + §4.14 note + §6.4 clause.
- Motion-repair numbers corrected to 51/47 in six places, provenance note added in §4.13.
- `chapters/03_methodology.md:139` patched (What Is Light removed, replacement sentence in place).
- Fresh PDF: `dissertation/dissertation_full_draft_v15_20260804.pdf` (45 pp, two-pass).

## 2. Dissertation — REQUIRED before submission (yours)

| # | Action | Note |
|---|--------|------|
| 2.1 | Insert real student number on the title page | Line was removed; BU cover sheets normally require it |
| 2.2 | Recompile in your own environment (Overleaf/local) | Sandbox build is content-identical but confirm layout/fonts |
| 2.3 | Delete/rename stale `dissertation_full_draft.pdf` (30 Jul) in Finder | Still contains 1 "What Is Light" hit; mount blocks deletion from here |
| 2.4 | Decide §3 optional edit below | Only if you want the 4 Aug runs in the paper |
| 2.5 | Final read of §4.11.1 + §4.17 in the compiled PDF | New content; check page breaks and figure placement |

## 3. Dissertation — OPTIONAL edit (your decision): 4 Aug Mode C extension

The three completed 7 s replacement runs (4 Aug) predate submission, so they MAY be reported. If yes, append to §4.17 (after the Condition A findings paragraph):

> **Extension run (executed 4 August 2026).** The Condition A backend was subsequently exercised on the full 7 s driving clip (`test2.mov`, 209 frames at 30 fps) via the Wan2GP low-VRAM path (Wan2.2-Animate 14B, int8, replacement mode with automatic relighting LoRA), completing three end-to-end generations at 544\(\times\)960 across three 81-frame sliding windows (\(\approx\)2 h 55 m per run on the 16 GB RTX 4080). Motion following and background preservation held under human review; identity and proportion distortion on extreme poses persists (quality WIP), and window-boundary continuity is a new observed artefact. The full 27.15 s driving video remains \textbf{not validated}. The session ended with a GPU driver fault on the remote host, recorded as an operational risk of long 14B runs on 16 GB.

And add one row to Table 4.14: `Mode C full-7s replacement ×3 & 544×960, 209 f, 3 windows & Executed (Wan2GP, 4 Aug) \\`

If you do this: rename the archive folder `post_submission_full7s_20260804` → `extension_full7s_20260804` and update its README first line accordingly (currently says "NOT dissertation evidence" — flip to "Reported in §4.17 extension paragraph"). If you skip this edit, change nothing; the folder stays labelled post-submission.

Do NOT add: Mode D, the VACE skeleton attempt, or the crashed runs — zero completed outputs, nothing reportable.

## 4. Dashboard / code (Codex) — status + remaining

**Applied + verified (no action):** `apply_claude_review_v15.py` ran clean; 13/13 checks pass (v15 PDF link + confined allowlist, ArcFace card, 14–64% headline, 25%→100% on repair page, GrabCut/MediaPipe sentence, 10 dissertation chips, architecture rationale ×2, Mode A-1 note, 9↔4-stage mapping, real-footage caveat, 51/47 intact, read-only guard intact). Backup: `pipeline/app.py.backup_claude_v15_20260804_134321`.

**Remaining for Codex** (full text already in `codex_dashboard_patch_instructions.md`):

| # | Item | Status |
|---|------|--------|
| 13 | `reference_control_pose_mask_audit.zip` — deliver the ZIP back into the audit folder; serve it; verify entries + SHA-256 against manifest | **Still owed** |
| 14 | Anchor-system module (multi-view anchor set §3.2.1 · locked slot order §3.5.2 · `street_identity_anchor_comparison.png` embedded in repair story ep. 01) | Pending execution |
| 15 (new) | Mode C page: add a dated card for the 4 Aug 7 s runs. Label depends on your §3 decision: "Extension run (§4.17)" if added to paper, else "Post-submission demo — not dissertation evidence". Media: one of the three mp4s + README link | Pending |
| 16 (new) | If paper gets the §4.17 extension paragraph, re-export the PDF again and re-swap the served copy (v15 → v16) | Conditional |

Rules for Codex unchanged: display layer only, no evidence edits, keep 51/47, keep read-only guard, no claim escalation.

## 5. Evidence archiving rules (all future runs)

- One dated folder per run family under `outputs/runs/...`, e.g. `extension_full7s_20260804/`.
- Every folder gets a README.txt: date, backend+version, model+quant, mode, inputs, resolution/frames/steps/seed, generation time, honest status label.
- WanGP outputs embed full settings in mp4 metadata — "Load Settings From Media File" restores them; never rename away the timestamp prefix.
- Online-service outputs (wan.video / Viggle): screenshot the settings page, record site+date+mode in the README; treat as demos unless parameters are fully recorded.

## 6. Remote GPU (w33108) — state + standing lessons

- **Current state: GPU driver fault** (`nvidia-smi: No devices were found`). Admin reboot requested; nothing GPU-side works until then. SSH/disk fine.
- The crashed Mode D (gown) and VACE skeleton runs produced no output; re-queue after reboot.
- Standing rules: ① draft with lightx2v 4-step (or 81-frame single window) before any full-step run; ② one lane at a time — never run wan2gp env and modec bundle concurrently on the 16 GB card; ③ the official Wan2.2 CLI bundle is a dead end on this box (flash-attn ABI + no offload) — Wan2GP is the working path, stop reinstalling the bundle; ④ long queues: clear duplicates before Generate (the 3× identical runs were an accidental triple-queue).
- Mode D online fallback: wan.video (official, ✦10 free credits — use the 4 s segment to fit budget) or viggle.ai (5 free relaxed videos/day).

## 7. Key numbers (copy from here, not from memory)

| Item | Value |
|------|-------|
| ArcFace cosine similarity | shot_001 0.374 · shot_004 0.227 · mean 0.301 · shots 002/003 n/a |
| Motion repair | shot_001 14→51% · shot_003 19→47% (decision_log.json) |
| Motion capture range | 14–64% (001:14, 002:37, 003:19, 004:64) |
| Loop reconstruction | 25% → 100%, 8 attempts (1/2/2/3) |
| Pose/mask audit | 12 samples, 9/12 usable, shot_003 ×3 no pose; conf 0.44–0.47 vs ≥0.80 |
| mode_c.MP4 | 27.15 s, 1464×822, ~30 fps |
| test2.mov | 6.97 s, 1080×1924, 30 fps · 4 s segments: 512×912 |
| 4 Aug runs | 3× 544×960, 209 f, 60 steps, seed 630814980, ~2h55m each |
| Final beach video | 768×1152, 20.4 s · street: final_look3_street_demo.mp4 |
