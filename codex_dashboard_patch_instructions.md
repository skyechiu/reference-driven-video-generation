# Dashboard patch instructions (v14 → v15)

Scope: patch the case-study/evidence pages in `pipeline/app.py` only. Do not redesign pages. Do not add claims beyond what is written here. All numbers below are verified against the dissertation source (`dissertation/paper.tex`) and the evidence packages.

## Global rules

- Never edit files inside evidence packages (they are hash-manifested). All fixes are display-layer text in `app.py`.
- Keep every existing claim-boundary sentence ("exact frame-level motion transfer is not claimed", "reference_video = None", "diagnostic, not production hard control"). Nothing below weakens them.
- Keep the read-only 403 guard as is.

## P0 — blocking issues

### 1. Motion-repair numbers: RESOLVE 51/47 vs 52/48 (decision pending)
- Site and `run_summary.md` say shot_001 14%→51%, shot_003 19%→47%.
- Dissertation (§4.13 Table 4.11, §4.14, §4.16) says 14%→52%, 19%→48%.
- ACTION for Codex: locate the post-repair (motion_v2) optical-flow metrics output that produced your 51/47 (the file analogous to `street_motion_metrics.json` for the v2 clips) and report its exact per-shot captured-% values back. Do NOT change the site numbers yet. The dissertation and site will then be aligned to whichever value the logged metrics file actually contains.

### 2. Replace the stale dissertation PDF
- The served `dissertation_full_draft.pdf` is the 30 Jul build. It predates: ArcFace terminology standardisation, §4.11.1 pose/mask audit, renumbered Figures 4.2–4.4, Table 4.18, §5.3 consent rewrite, Figure 3.10 caption fix, removal of all "What Is Light" references.
- ACTION: replace with the freshly compiled PDF from `dissertation/` (ask for it; do not re-serve the old file). Also update `dissertation_ch3-4_cvpr.pdf` link label to "(superseded draft)" or remove it.

## P1 — missing content (add; text supplied)

### 3. ArcFace identity card (page-case-summary or page-case-limitations)
Add one card. Exact text:
> **Identity diagnostic — executed post-hoc (dissertation §4.8.1).** ArcFace (buffalo_l) cosine similarity of each approved beach keyframe to the Look 3 front anchor: shot_001 = 0.374, shot_004 = 0.227 (mean 0.301); shot_002 (back view) and shot_003 (feet detail) = not applicable, no face. All four keyframes were accepted as the same character at human review. The low similarities are evidence that a single face-embedding metric is mis-calibrated for a synthetic, stylised character — this is why human review, not ArcFace, is the acceptance authority.
Values are cosine similarity. Never label them distance.

### 4. Motion-energy headline (page-case-street, motion section)
Add before the per-shot filmstrips:
> **Headline finding (dissertation §4.13).** Across all four shots the generated clips reproduce only 14–64% of the reference's per-frame motion energy (shot_001 14%, shot_003 19%, shot_004 64%); both beach and street generations under-animate relative to the reference. The prompt-only repair below acts on the two weakest shots.

### 5. Loop-value number on the repair page (page-case-repair-story)
The 25%→100% figure currently appears only on page-eval-report. Add to the repair-story header:
> Reconstructed from the decision log: first-attempt acceptance 25% (1 of 4 shots) → 100% after human-gated repair, across 8 logged attempts (1/2/2/3 per shot). This is a log reconstruction, not a controlled ablation (dissertation §4.9).

### 6. Method names on the pose/mask audit block (page-case-archived)
Add one sentence:
> Pose reuses the project's local MediaPipe Pose Landmarker outputs (shot_001 confidence 0.44–0.47, partial upper body; shot_002/004 ≥ 0.80, near-complete keypoints); masks are pose-seeded OpenCV GrabCut (5 iterations); shot_003 samples are labelled `unavailable_no_pose_seed`. Package is SHA-256 hash-manifested. (Dissertation §4.11.1, Table 4.18.)

### 7. Dissertation section mapping (all case pages)
Add a small "Dissertation:" footer chip per page:
beach → §4.3–4.7 · street & archived skeleton branch → §4.12 · motion audit → §4.13 · pose/mask audit → §4.11.1 · repair story → §4.9, §4.14 · ArcFace → §4.8.1 · limitations → §4.15 · Mode C → §3.10, §4.17 · architecture → §3.2–3.7 · assets → §3.2.1, §3.5.1.

### 8. Two missing rationale sentences (page-case-architecture)
- After the "Implemented evidence path" intro: "Deterministic tools compute measurable signals; language-model agents decide from them — 'tools compute, agents decide' is the system's core design principle."
- In the keyframe-first stage description: "Keyframe-first follows the pose-to-pose principle of classical animation (dissertation §2.1): a short-form clip is a few readable key poses joined by beat-timed cuts, so the pipeline fixes the pose first and delegates in-betweens to I2V."

## P2 — consistency fixes

### 9. "Mode A-1" label
Keep the label if you want, but add once on page-case-beach: "Mode A-1 = the dissertation's 'reference-scene preservation' setting (§4.3–4.7); the dissertation itself does not use the A-1 label."

### 10. 9-stage vs 4-stage mapping (page-case-walkthrough)
Add one line: "These nine inspectable stages are a finer-grained view of the dissertation's four-stage architecture (§3.2): stages 01–03 = Reference Analysis + Template Builder, 04–06 = IP-Conditioned Generation, 07–09 = Evaluation & Repair + assembly."

### 11. "real footage" caveat where motion-audit files are exposed
Where `motion_audit_report.md` / metrics JSON are linked, add: "Note: 'real footage' in the archived audit log is shorthand for the motion-target role. The reference clip is the author-created AI-generated beach performance clip (dissertation §5.3); the logs are preserved unedited."

### 12. Verify the "27-second" Mode C claim
Confirm 27 s is the actual duration of `mode_c.MP4` (ffprobe). If not, correct the number or say "the full-length driving video".

### 13. Evidence inventory: ZIP presence
The pose/mask inventory row promises "12 samples, contact sheet, manifest, ZIP". `reference_control_pose_mask_audit.zip` must actually be served/downloadable, and its entry count and SHA-256 must match the manifest. Also deliver a copy of this ZIP back to the project owner (it is still missing from the audit folder shared with the dissertation side).

## P1 addendum (from v15 review follow-up)

### 14. Anchor system module — the anchor design rationale is currently missing as a system
"Anchor" appears 22× in the site but only as fragments (keyframe-as-anchor, one repair episode, two thumbnails). Add one module, suggested location: page-case-architecture (after the Separated Conditioning Inputs block) or page-case-assets (before the Look packages). Three parts, exact text:

(a) **Multi-view anchor set (dissertation §3.2.1).**
> The Look 3 identity is not one image but a purpose-built anchor set: a front-facing facial anchor, a side/profile anchor and outfit references — each authored to control a specific axis of appearance. Identity is anchored per view, so a profile shot is conditioned by the profile anchor rather than a stretched frontal reference.
Reuse the existing thumbnails `look3_identity_anchor_front.png` / `look3_identity_anchor_profile.png` beside this text.

(b) **Locked slot order (dissertation §3.5.2).**
> Keyframe generation supplies four reference images in a locked slot order: slot [0] the source frame (primary structural anchor for framing, body scale and camera distance), then identity anchor, look reference and scene reference. Slot priority is shot-type-specific: face-visible shots promote the identity anchor; back-view and feet-detail shots promote the scene/source references. This ordering is a tested heuristic, not a model guarantee.

(c) **Anchor-repair evidence figure.**
Serve `dissertation/figures/street_identity_anchor_comparison.png` (add it to an existing media route or the linked-media package — do NOT widen the dissertation PDF allowlist) and embed it on page-case-repair-story episode 01 with caption:
> Identity-anchor repair (dissertation §4.12, Figure 4.3). Left: front and profile identity anchors. Middle: earlier street keyframes that kept outfit and scene but drifted to a generic face. Right: after the reference-ordering policy promoted the identity anchor for face-visible shots. Qualitative human-review evidence; identity is improved, not solved.

Constraint: keep all existing claim boundaries; this module explains design rationale already documented in the dissertation and adds no new claims.

### 15. Post-submission hosted-service comparison block (boundary/negative evidence — dated, quarantined)
New media in `outputs/runs/mode_c_phase0/hosted_comparison_20260805/` (4 videos + README) and the local runs in `outputs/runs/mode_c_phase0/local_animate_full7s_20260804/` (3 videos + README). Add ONE block, suggested location: bottom of page-case-mode-c, visually separated, with a distinct badge `LATE COMPARISON RUNS · 4–5 AUG 2026 · REPORTED IN DISSERTATION §4.18`.

Block title: "Hosted one-click services vs the orchestrated pipeline (§4.18 comparison)"

Body text (use verbatim):
> In the final pre-submission week, the same driving performance and driving performance were run through hosted one-click services (wan.video "Transfer" on Wan2.7; Viggle AI free tier) and through the locally orchestrated Wan2.2-Animate backend. The results are shown as boundary evidence along two axes, not to disparage the services. **Control axis (wan.video pair):** with no prompt, the service silently applied replace-style semantics — it kept the driving video's room and discarded the reference image's dressing-room background; re-run with an explicit instruction ("keep the image's background... do not use the video's room"), the dressing-room background was correctly preserved. Implicit control chose for the user; explicit instruction restored control. **Quality axis (Viggle pair vs local):** identity drift, garment simplification and weaker motion/contact fidelity are visible against the locally orchestrated runs. Both axes are empirical illustrations of the dissertation's core argument (§3.1.1): hosted interfaces trade away explicit control, auditability and targeted repair; the pipeline's contribution is precisely that explicit control layer.

Media layout: 5 cards in two labelled sub-rows — Row "Control (wan.video)": (a) Transfer no-prompt 4s [video's room], (b) Transfer prompted 5s [dressing room preserved]. Row "Quality (vs local)": (c) local Wan2.2-Animate int8 run (pick one from local_animate_full7s_20260804), (d) Viggle image-bg 7s, (e) Viggle video-bg 7s. Card sublabels must state service, prompt/no-prompt, date, duration.

Rules:
- The badge and the date must appear ON the block, not only in a tooltip.
- Do not use words like "failure of these products", "旗鼓相当", or superiority claims beyond the body text above.
- Do not link this block from the evidence inventory as dissertation evidence; if listed there, list under a separate "Post-submission demos" row with the same badge.
- Serve the videos via the existing run-media route from the two folders above; do not move or rename the files (names carry provenance).
- Everything else (51/47, claim boundaries, read-only guard) untouched.

### 16. Mode C / Mode D status addenda (dated; dissertation-era labels must NOT change)
Principle: the dissertation-era status stays as the PRIMARY label everywhere; tonight's progress appears only as a dated secondary chip with the same `POST-SUBMISSION` badge style as item 15. Never flip Mode D to "implemented".

(a) page-case-mode-c — add one addendum card under the existing content:
> **Post-submission addendum (4 Aug 2026).** Three full 7 s driving-segment replacements were completed locally via WanGP (Wan2.2 Animate 14B, int8, 544×960, 60 steps, 3 sliding windows, ≈2 h 55 m each, RTX 4080 16 GB). This extends the dissertation's Phase 0 (≈2.7 s) result; the full 27 s production run remains unattempted. The session ended with a GPU driver fault on the remote host (recorded in the run README).

(b) System Modes Map, card C — keep "Phase 0 passed · quality WIP" as primary; add chip:
> Post-submission: 7 s segments completed locally (4 Aug 2026); 27 s still pending.

(c) System Modes Map, card D — keep "Planned · not implemented" as primary (this matches the dissertation); add chip:
> Post-submission demo (5 Aug 2026): first person+background replacement executed via hosted Wan2.7 Transfer with an explicit background-preservation prompt (see comparison block); local backend run pending.

Rules: primary labels unchanged; every addendum carries its date; do not use "implemented", "completed", or "validated" for Mode D anywhere; do not touch the dissertation-era wording of the Mode C Phase 0 story.

## Out of scope for Codex

- Any change to dissertation LaTeX (handled on the dissertation side).
- Any edit inside evidence packages, decision logs, or audit files.
- New experiments, new metrics, new claims.
