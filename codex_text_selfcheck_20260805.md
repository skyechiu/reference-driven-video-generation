# Codex Instruction — Dashboard Text Self-Check & Fix (5 Aug 2026)

You are checking the accuracy of all user-facing text in `pipeline/app.py`.
Display layer only. Do not touch evidence files, do not run generation, keep
`ONLINE_DEMO_READ_ONLY = True`, POST routes stay 403.

Workflow: run every check below → produce a report (format in §6) → apply
SAFE fixes directly (wording, stale labels, numbers listed here) → list
RISKY changes (anything not covered by this sheet) for approval instead of
applying them. Back up `app.py` before editing.

---

## 1. Absolute claim rules (grep the whole file; each must return ZERO hits)

Forbidden phrases / claims, in any wording:

- "What Is Light"
- "face embedding distance" / ArcFace described as a distance
- street final described as completed reference-video transfer /
  completed Mode A-2 final / reference-structure transfer achieved
- "exact frame-level motion transfer" claimed as achieved
- fully automatic Stage-4 described as executed
- Mode C described as full production / validated 27 s run
- pose/mask/skeleton described as having driven or generated the final
  beach or street outputs
- Mode D described as implemented / executed / validated
- Mode D online demos described as dissertation evidence
- motion repair values 52 / 48 (correct values are 51 / 47)
- equal-budget ablation described as independently run

Also verify these REQUIRED wordings still exist:
- ArcFace = "cosine similarity", "higher means closer", "post-hoc
  diagnostic", never an automatic acceptance threshold
- Loop OFF/ON comparison described as reconstructed from the same logged
  run, not an independent equal-budget ablation

## 2. Ground-truth numbers (any other value is a bug)

| Item | Value |
|---|---|
| ArcFace | shot_001 0.374 · shot_004 0.227 · mean face-visible 0.301 · shots 002/003 n/a (no face) |
| Motion repair | shot_001 14→51% · shot_003 19→47% |
| Motion range | 001:14 · 002:37 · 003:19 · 004:64 (14–64%) |
| Loop reconstruction | 25% → 100% · 8 attempts · 1/2/2/3 |
| Pose/mask audit | 12 samples · 9/12 usable · shot_003 no pose seed |
| Beach final | 768×1152 · 20.4 s |
| Mode C 4 Aug run | 544×960 · 209 frames · 60 steps · seed 630814980 · ~2h55m · RTX 4080 16 GB |
| test2.mov | 6.97 s · 1080×1924 · 30 fps |
| mode_c.MP4 | 27.15 s · 1464×822 · ~30 fps |
| Mode D Viggle demos | 7.0 s · 718×1280 (scene preserved) / 720×1280 (scene replaced) · 25 fps · viggle.ai watermark |
| Mode D wan.video demos | Transfer (scene preserved) 4.0 s · 720×1280 · 30 fps; Edit (scene replaced, pose/motion only) 4.8 s · 718×1280 · 30 fps · Wan watermark |
| Mode B ComfyUI final | 71.6 s · 3840×2160 · 30 fps · completed 4 Aug 2026 |
| Overview stat "12 named models and tools" | must equal the names printed in the five stack cards: PySceneDetect, OpenCV, MediaPipe, librosa, gpt-image-1, Kling, ArcFace, InsightFace, DWPose, SAM3, Wan2GP, Wan2.2 |
| Overview stat "105 linked media / report paths" | STALE. Recount unique `/media/...` (+`/report/...`) hrefs actually rendered (last count: 115) and update the stat |

## 3. Known stale items to fix (SAFE fixes, apply directly)

1. Overview Extension card badge `PHASE 0 ONLY` → `FEASIBILITY BRANCH`
   (or `PHASE 0 + 7s WINDOW`); card text may add: "extended by a 7 s
   replacement window (4 Aug); full production was not validated."
2. System-map Mode D card is inconsistent with the Mode D page:
   - badge `NOT IMPLEMENTED` → `PLANNED · HOSTED DEMOS ONLY`
   - subtitle `Future architecture only` → `Planned extension ·
     hosted-service demos only`
   - bullets: person+background replacement concept · hosted demos executed
     4 Aug (viggle.ai / wan.video), no evidential weight · no local
     implementation, bounded design extension
   - page-bottom caption: "Mode D remains planned" → "Mode D remains
     planned, with exploratory hosted demos only"
3. System-map Mode B card and Mode B page: "display-only" /
   "EXPERIMENTAL"-only framing is outdated. Correct status:
   `EXECUTED · SEPARATE COMFYUI PATH` — Mode B was executed end to end on a
   separate ComfyUI path and edited into a 71.6 s final video (4 Aug 2026).
   Required boundary (must appear wherever the run is described): not
   routed through the shared generation-unit pipeline; no per-shot decision
   logging or human-gated repair records; reported as a completed creative
   extension, not at Mode A evidence maturity.
   Do NOT write "uses the downstream keyframe-first logic" — use
   "designed to feed the same downstream keyframe-first logic".
4. If the paper gains the §3.8 Mode B addition / §4.17 Mode C extension,
   the served PDF version label must match the newest compiled PDF.
5. Update Evidence Index rows for Mode B (executed ComfyUI run) and Mode D
   (four hosted demos, no evidential weight) to match the above.

## 4. Mode D page — required content (verify present and consistent)

- Hero: planned extension; hosted demos only; none of it is dissertation
  evidence.
- Motivation: local Mode C = Wan2.2-Animate 14B on 16 GB RTX 4080 at the
  model's minimum VRAM boundary; ~2h55m for a 7 s window; GPU driver
  faults twice (`nvidia-smi: No devices were found`). Do NOT write that the
  GPU "cannot run" Wan (a 7 s window did complete locally). Do NOT state a
  numeric VRAM requirement.
- 2×2 demo grid: each service once scene-preserved, once scene-replaced,
  same AI-generated reference image; clip durations differ between
  services. Every demo card carries `ONLINE DEMO — NOT DISSERTATION
  EVIDENCE` + "service parameters not fully recorded".
- Qualitative comparison section: identity drift and lighting mismatch
  observations labelled `QUALITATIVE HUMAN REVIEW · NO METRICS COMPUTED`;
  no numeric scores for Mode D; keep the trade-off sentence (hosted demos
  are faster and need no local GPU).
- Ethics & consent: beach reference and Mode D reference image are
  AI-generated, no real person; Mode C/D driving recordings from a
  consenting collaborator; identity replaced in published outputs; raw
  driving footage not served anywhere on the site.

## 5. Cross-page consistency sweep

- Same fact, same wording everywhere: if a number or status appears on
  multiple pages (Overview, system map, mode pages, Evidence Index,
  Limitations), all instances must agree after the fixes above.
- Only one sidebar item active; no duplicate "Reference analysis" entries.
- No `/media/look-ref-front` broken reference.
- SVG vs page text: if the full-size project-structure SVG still shows old
  Mode B/D labels, flag it in the report (do not edit hash-manifested
  evidence; regenerate a display copy instead).

## 6. Verification & report

Run: `python3 -m py_compile pipeline/app.py`; confirm homepage and all
public routes return 200; confirm POST routes return 403.

Then output a report:

```
SELF-CHECK REPORT <date>
A. Forbidden-claim greps: PASS/FAIL per pattern (+line numbers)
B. Number audit: each §2 row PASS/FIXED/FAIL (+line numbers)
C. Stale items §3: FIXED/ALREADY-OK/NEEDS-APPROVAL each
D. Mode D page checklist §4: item-by-item PASS/FAIL
E. Consistency sweep §5: findings
F. Routes: 200 count, 403 count, py_compile result
G. Changes applied (with backup filename) + changes proposed but NOT
   applied (risky, need approval)
```

Never escalate a claim to make text read better. When unsure whether a
sentence overclaims, weaken it or flag it — do not guess upward.
