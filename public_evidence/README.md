# 📂 Public Evidence

This directory contains a small, curated subset of the project evidence selected for public inspection by reviewers, researchers, and recruiters.

It is **not a copy of the complete experimental record**. Full run histories, rejected generations, intermediate artefacts, raw control material, and internal audit packages are retained separately in the project archive and are not published in this repository.

## Included evidence

| Path | Evidence | Purpose |
|---|---|---|
| `beach/final_look3_reference_driven_demo.mp4` | Completed Mode A-1 reference-scene-preservation output | Primary end-to-end Mode A evidence |
| `beach/keyframes/` | Four approved beach keyframes | Shows the per-shot keyframes used for I2V generation |
| `beach/decision_log.json` | Per-shot decision history | Records attempts, review outcomes, diagnoses, and retained results |
| `beach/evaluation_report.md` | Evaluation summary | Supports the reported repair history and run-level evidence |
| `beach/run_summary.md` | Run metadata | Documents the executed configuration and outputs |
| `street/final_look3_street_demo.mp4` | Completed street scene-package output | Evidence for the identity-and-scene stress test |
| `street/identity_anchor_before_after.png` | Identity-anchor comparison | Shows the identity-repair intervention used in the street experiment |
| `street/motion_repair_before_after.png` | Motion-repair comparison | Shows the before/after evidence for shot_001 (14→51%) and shot_003 (19→47%) |
| `street/decision_log.json` | Street decision history | Records the corresponding review and repair decisions |
| `street/evaluation_report.md` | Street evaluation summary | Supports the reported repair history and run-level evidence |
| `street/run_summary.md` | Street run metadata | Documents the executed configuration and outputs |
| `mode_c/redacted_input_sample.mp4` | Privacy-redacted driving-video sample | Demonstrates the Mode C control input without exposing unredacted real-person footage |
| `mode_c/selected_output_seed630814980.mp4` | Selected Wan2.2-Animate output | Evidence from the 7-second Mode C extension run |
| `pose_mask_audit/contact_sheet.jpg` | Pose/mask audit contact sheet | Visual summary of the 12-sample control-signal audit |
| `pose_mask_audit/README.md` | Pose/mask audit summary | Documents the 9/12 usable-sample result and its limitations |

## Evidence boundaries

The public evidence is intentionally selective.

The following material is **not published**:

- rejected and intermediate generations
- full raw run directories
- duplicate previews and backups
- raw LoRA face-training datasets
- unredacted real-person driving footage
- private development files
- local caches and temporary artefacts
- credentials or environment files

The public repository is intended to make the main research claims inspectable without publishing unnecessary private or redundant material.

## Provenance

Some original evidence files contain machine-specific absolute paths generated during execution.

For the public copies in this directory, those paths may be replaced with:

```text
<PROJECT_ROOT>
```

These sanitised files are public derivatives of the original evidence records.
The original, unmodified evidence remains in the private project archive and is retained as the canonical record for provenance and integrity verification. Any SHA-256 manifests associated with the original evidence therefore apply to the archived originals, not to sanitised public copies.

## Privacy

Mode C uses a real-person driving performance as a motion-control source.
Only privacy-redacted versions are included here. Raw or unredacted driving footage is deliberately excluded from the public repository.
