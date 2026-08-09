"""Report pose evidence availability without running pose estimation."""

from __future__ import annotations

from pathlib import Path

from .metric_status import VERIFIED, metric_result


def evaluate_pose(run_dir: Path, shot_ids: list[str]) -> dict[str, dict]:
    reference_dir = run_dir / "analysis" / "pose_overlay"
    generated_candidates = [
        run_dir / "evaluation" / "generated_pose",
        run_dir / "analysis" / "generated_pose",
        run_dir / "generated_pose",
    ]
    out: dict[str, dict] = {}
    for shot_id in shot_ids:
        ref = reference_dir / f"{shot_id}_pose_overlay.png"
        generated = next(
            (d / f"{shot_id}_pose.json" for d in generated_candidates if (d / f"{shot_id}_pose.json").exists()),
            None,
        )
        if generated:
            out[shot_id] = metric_result(
                "pending",
                source_status=VERIFIED,
                source=str(generated),
                note="Generated-side pose data exists, but numeric comparison is not implemented in this dry-run.",
                reference_pose_exists=ref.exists(),
                generated_pose_exists=True,
            )
        else:
            out[shot_id] = metric_result(
                "pending" if ref.exists() else "not_applicable",
                source_status=VERIFIED if ref.exists() else "PENDING · FILE MISSING",
                source=str(ref),
                note=(
                    "Reference pose exists; generated-side DWPose is unavailable, so pose similarity remains pending."
                    if ref.exists() else
                    "No usable reference or generated-side pose evidence was found."
                ),
                reference_pose_exists=ref.exists(),
                generated_pose_exists=False,
            )
    return out
