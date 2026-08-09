"""Safe Stage-4 evaluation/repair dry-run harness.

Reads completed artefacts, reuses verified reports, computes local metadata only,
and writes new audit files outside completed run directories. It never imports a
generation module and cannot execute a repair in its current form.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from evaluation.framing_evaluator import evaluate_framing
    from evaluation.identity_evaluator import evaluate_identity
    from evaluation.metric_status import PENDING, VERIFIED, metric_result
    from evaluation.pose_evaluator import evaluate_pose
    from evaluation.repair_planner import plan_repairs
    from evaluation.timing_evaluator import evaluate_timing
else:
    from .framing_evaluator import evaluate_framing
    from .identity_evaluator import evaluate_identity
    from .metric_status import PENDING, VERIFIED, metric_result
    from .pose_evaluator import evaluate_pose
    from .repair_planner import plan_repairs
    from .timing_evaluator import evaluate_timing


EXECUTE_REPAIR = False
REQUIRED_OUTPUTS = {
    "auto_repair_report.md",
    "auto_repair_summary.json",
    "repair_plan.json",
    "decision_log_auto_repair_dryrun.json",
}


def _assert_safe() -> None:
    if EXECUTE_REPAIR:
        if os.environ.get("CONFIRM_PAID_API") != "1":
            raise RuntimeError("Repair execution is forbidden unless CONFIRM_PAID_API=1")
        raise RuntimeError("Paid repair execution is not implemented in this audit-only harness")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _existing_complete(output_dir: Path) -> bool:
    summary_path = output_dir / "auto_repair_summary.json"
    if not summary_path.exists():
        return False
    try:
        summary = _load_json(summary_path)
    except (OSError, json.JSONDecodeError):
        return False
    return REQUIRED_OUTPUTS.issubset({p.name for p in output_dir.iterdir() if p.is_file()}) and bool(summary.get("shots"))


def _pending_metric(note: str) -> dict[str, Any]:
    return metric_result("pending", source_status=PENDING, source="not available", note=note)


def _overall_verdict(metrics: dict[str, dict], human_approved: bool) -> str:
    if human_approved:
        return "accepted_by_human_review"
    verdicts = {m.get("verdict") for m in metrics.values()}
    if "fail" in verdicts:
        return "fail"
    if "needs_review" in verdicts or "pending" in verdicts:
        return "needs_review"
    return "pass"


def _render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Automatic Stage-4 Evaluation / Repair Harness",
        "",
        "**Status: DESIGNED · NOT FULLY EXECUTED**",
        "",
        "This is a local, audit-only dry run. It reads completed artefacts and proposes repairs; it does not regenerate media.",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Execute repair: `{str(summary['execute_repair']).lower()}`",
        f"- Paid/external calls attempted: `{str(summary['paid_external_call_attempted']).lower()}`",
        f"- Existing completed harness report reused: `{str(summary['reused_complete_harness_report']).lower()}`",
        "",
        "## Shot results",
        "",
        "| Shot | Overall | Identity | Framing | Pose | Timing | Beat alignment |",
        "|---|---|---|---|---|---|---|",
    ]
    for shot in summary["shots"]:
        m = shot["metrics"]
        lines.append(
            f"| {shot['shot_id']} | {shot['overall_verdict']} | {m['identity']['verdict']} | "
            f"{m['framing']['verdict']} | {m['pose']['verdict']} | {m['timing']['verdict']} | "
            f"{m['beat_alignment']['verdict']} |"
        )
    lines += [
        "",
        "## Evidence handling",
        "",
        "- ArcFace values: **VERIFIED FROM EXISTING REPORT**; ArcFace was not rerun.",
        "- Framing acceptance: **VERIFIED FROM EXISTING REPORT**; human-coded, not a numeric automatic score.",
        "- Reference pose availability: **VERIFIED FROM EXISTING REPORT / FILES**.",
        "- Generated-side pose comparison: **PENDING**.",
        "- Clip timing mismatch: **COMPUTED LOCAL / $0** from existing files with `ffprobe`.",
        "- Formal beat-alignment metric: **PENDING**.",
        "",
        "## Interpretation guardrail",
        "",
        "Low ArcFace values do not automatically fail these synthetic-IP shots. Existing approvals are recorded as `accepted_by_human_review`. Repair proposals are plans only.",
        "",
    ]
    return "\n".join(lines)


def run_harness(project_root: Path, run_dir: Path, output_dir: Path) -> dict[str, Any]:
    _assert_safe()
    output_dir.mkdir(parents=True, exist_ok=True)

    if _existing_complete(output_dir):
        summary = _load_json(output_dir / "auto_repair_summary.json")
        summary["verification_status"] = VERIFIED
        summary["reused_complete_harness_report"] = True
        return summary

    source_decision_log = run_dir / "final" / "decision_log.json"
    if not source_decision_log.exists():
        raise FileNotFoundError(f"Required existing decision log not found: {source_decision_log}")
    original_log = _load_json(source_decision_log)
    shot_ids = [s["shot_id"] for s in original_log.get("shots", [])]

    identity = evaluate_identity(shot_ids, project_root / "project_state.json")
    framing = evaluate_framing(source_decision_log)
    pose = evaluate_pose(run_dir, shot_ids)
    timing = evaluate_timing(source_decision_log, project_root)

    shots = []
    plans = []
    dry_log_shots = []
    for source_shot in original_log.get("shots", []):
        shot_id = source_shot["shot_id"]
        metrics = {
            "identity": identity[shot_id],
            "framing": framing[shot_id],
            "pose": pose[shot_id],
            "timing": timing[shot_id],
            "beat_alignment": _pending_metric("Formal beat-boundary alignment has not been computed."),
            "motion_energy": _pending_metric("No beach-run motion-energy report was found; no value was invented."),
        }
        human_approved = (source_shot.get("keyframe_generation") or {}).get("status") == "approved"
        plan = plan_repairs(shot_id, metrics)
        overall = _overall_verdict(metrics, human_approved)
        shot_result = {
            "shot_id": shot_id,
            "overall_verdict": overall,
            "human_review_status": "accepted_by_human_review" if human_approved else "pending",
            "metrics": metrics,
            "repair_plan": plan,
        }
        shots.append(shot_result)
        plans.append(plan)
        dry_log_shots.append({
            "shot_id": shot_id,
            "verdict": overall,
            "attempt": 0,
            "mode": "dry_run",
            "metrics": metrics,
            "proposed_repairs": plan["proposals"],
            "repair_executed": False,
        })

    summary = {
        "schema": "auto_repair_harness_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "source_decision_log": str(source_decision_log),
        "source_decision_log_modified": False,
        "execute_repair": EXECUTE_REPAIR,
        "confirm_paid_api": os.environ.get("CONFIRM_PAID_API") == "1",
        "paid_external_call_attempted": False,
        "generation_modules_imported": False,
        "reused_complete_harness_report": False,
        "automatic_stage4_status": "DESIGNED · NOT FULLY EXECUTED",
        "shots": shots,
    }
    dry_log = {
        "schema": "decision_log_auto_repair_dryrun_v1",
        "run_id": run_dir.name,
        "source_log": str(source_decision_log),
        "source_log_modified": False,
        "execute_repair": False,
        "paid_external_call_attempted": False,
        "shots": dry_log_shots,
    }
    repair_plan = {
        "schema": "repair_plan_v1",
        "run_id": run_dir.name,
        "execute_repair": False,
        "plans": plans,
    }

    (output_dir / "auto_repair_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "repair_plan.json").write_text(json.dumps(repair_plan, indent=2), encoding="utf-8")
    (output_dir / "decision_log_auto_repair_dryrun.json").write_text(json.dumps(dry_log, indent=2), encoding="utf-8")
    (output_dir / "auto_repair_report.md").write_text(_render_markdown(summary), encoding="utf-8")
    return summary


def main() -> int:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Run the local-only Stage-4 dry-run harness")
    parser.add_argument("--project-root", type=Path, default=default_root)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    run_dir = (args.run_dir or project_root / "outputs" / "runs" / "live_test_03_4shots").resolve()
    output_dir = (args.output_dir or project_root / "outputs" / "audits" / "auto_repair_harness").resolve()
    result = run_harness(project_root, run_dir, output_dir)
    print(json.dumps({
        "ok": True,
        "run_id": result["run_id"],
        "execute_repair": result["execute_repair"],
        "paid_external_call_attempted": result["paid_external_call_attempted"],
        "reused_complete_harness_report": result["reused_complete_harness_report"],
        "verification_status": result.get("verification_status"),
        "output_dir": str(output_dir),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
