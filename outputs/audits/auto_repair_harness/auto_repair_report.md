# Automatic Stage-4 Evaluation / Repair Harness

**Status: DESIGNED · NOT FULLY EXECUTED**

This is a local, audit-only dry run. It reads completed artefacts and proposes repairs; it does not regenerate media.

- Run: `live_test_03_4shots`
- Execute repair: `false`
- Paid/external calls attempted: `false`
- Existing completed harness report reused: `false`

## Shot results

| Shot | Overall | Identity | Framing | Pose | Timing | Beat alignment |
|---|---|---|---|---|---|---|
| shot_001 | accepted_by_human_review | needs_review | pass | pending | fail | pending |
| shot_002 | accepted_by_human_review | not_applicable | pass | pending | fail | pending |
| shot_003 | accepted_by_human_review | not_applicable | pass | pending | fail | pending |
| shot_004 | accepted_by_human_review | needs_review | pass | pending | fail | pending |

## Evidence handling

- ArcFace values: **VERIFIED FROM EXISTING REPORT**; ArcFace was not rerun.
- Framing acceptance: **VERIFIED FROM EXISTING REPORT**; human-coded, not a numeric automatic score.
- Reference pose availability: **VERIFIED FROM EXISTING REPORT / FILES**.
- Generated-side pose comparison: **PENDING**.
- Clip timing mismatch: **COMPUTED LOCAL / $0** from existing files with `ffprobe`.
- Formal beat-alignment metric: **PENDING**.

## Interpretation guardrail

Low ArcFace values do not automatically fail these synthetic-IP shots. Existing approvals are recorded as `accepted_by_human_review`. Repair proposals are plans only.
