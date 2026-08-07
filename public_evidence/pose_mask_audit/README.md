# Local Pose/Mask Audit Package

Source scope: four validated reference shots, sampled at start/mid/end (12 samples). Generation API calls: **0**.

- Pose controls reuse the project's prior local MediaPipe extraction from the same source frames and bundled model.
- Person masks were derived in this run with local OpenCV pose-seeded GrabCut (5 iterations), then exported as binary and soft-edge masks.
- `contact_sheet.jpg` pairs pose and mask overlays; `audit.csv` contains compact metrics; `manifest.json` records provenance and hashes.

This is an audit package, not a claim that every control is production-ready. Shot 003 has no detected pose; its masks are intentionally empty and labelled unavailable. Low-confidence/cropped poses and GrabCut boundaries around hair, loose clothing, motion blur, or low-contrast edges require human review. Do not promote a mask downstream without reviewing its overlay.
