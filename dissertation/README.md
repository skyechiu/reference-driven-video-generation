# Dissertation — Reference-Driven Agentic Short-Form Video Generation System

MSc AI for Media · NCCA, Bournemouth University · graduating Sept 2026

## Folder structure

```
dissertation/
├── README.md            ← this index
├── chapters/            ← per-chapter markdown drafts (compile to docx once firm)
│   ├── 03_methodology.md   ← Chapter 3 (v0.1) — 8 figures wired in (Fig 3.1–3.8)
│   └── 04_evaluation.md    ← Chapter 4 (v0.1) — executed results + pending placeholders
├── optimized_diagrams_cs_paper/  ← 8 paper diagrams (PNG+SVG), referenced by Ch3
└── dissertation.docx    ← final compiled document (not created yet)
```

## Writing order (rationale: write where material is ready; Abstract last)

1. **Chapter 3 — Methodology** ✔ draft v0.1 — architecture locked, 8 figures wired in.
2. **Chapter 4 — Evaluation & Results** ✔ draft v0.1 — executed results (schema / keyframe /
   Kling / assembly / human review) reported; automated Stage-4 scores (ArcFace / DWPose /
   framing / beat) and loop ON-vs-OFF ablation are PENDING placeholders, no invented numbers.
   To finalise: run automated scoring on `live_test_03_4shots`, fill Tables 4.6–4.7.
3. **Chapter 2 — Related Work / Background** — reference-driven generation, IP conditioning,
   agentic pipelines, evaluation of generative video.
4. **Chapter 1 — Introduction** — problem, contribution, scope.
5. **Chapter 5 — Conclusion & Future Work** — incl. Phase 0 pose-vs-identity + full pose transfer.
6. **Abstract** — written LAST.

## Honesty ledger (do not let claims outrun evidence)

- Motion is **prompt-level I2V, not frame-level pose transfer.** Always pair the claim-clarity
  sentence with any demo.
- Automated evaluation + repair loop is **designed and implemented in schema, but not yet run**
  on `live_test_03_4shots`. Methodology may describe the design; Results may not report scores
  that were never computed.
- Phase 0 (pose vs identity) **not run** → pipeline scoped to keyframe-first. This is a scoping
  decision, framed as such.
- **Aspect ratio: ffprobe-confirmed 768×1152 (2:3 portrait)**, NOT 9:16. Several diagrams/configs
  still label "9:16" — nominal only. Either re-render at true 9:16 or restate deliverable as
  768×1152 vertical, and make it consistent everywhere.
```
```
