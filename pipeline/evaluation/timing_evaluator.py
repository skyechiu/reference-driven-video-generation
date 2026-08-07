"""Compare recorded reference-shot durations with existing clip metadata."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .metric_status import COMPUTED_LOCAL, VERIFIED, metric_result


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return float(result.stdout.strip())


def evaluate_timing(decision_log_path: Path, project_root: Path) -> dict[str, dict]:
    data = json.loads(decision_log_path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for shot in data.get("shots", []):
        shot_id = shot.get("shot_id", "")
        target = float(shot.get("duration_s", 0.0))
        raw_clip_path = (shot.get("kling_i2v") or {}).get("clip_path", "")
        clip_path = Path(raw_clip_path)
        if not clip_path.is_absolute():
            clip_path = project_root / clip_path
        if not clip_path.exists():
            out[shot_id] = metric_result(
                "pending",
                source_status="PENDING · FILE MISSING",
                source=str(clip_path),
                note="Existing clip was not found; no timing value was invented.",
            )
            continue
        actual = _probe_duration(clip_path)
        mismatch = actual - target
        mismatch_ms = round(mismatch * 1000.0)
        out[shot_id] = metric_result(
            "pass" if abs(mismatch) <= 0.25 else "fail",
            value={
                "reference_shot_duration_s": round(target, 4),
                "existing_clip_duration_s": round(actual, 4),
                "mismatch_s": round(mismatch, 4),
                "mismatch_ms": mismatch_ms,
            },
            source_status=COMPUTED_LOCAL,
            source=str(clip_path),
            note="Container duration read from the existing clip with ffprobe; no media was changed.",
            reference_duration_source_status=VERIFIED,
            tolerance_ms=250,
        )
    return out
