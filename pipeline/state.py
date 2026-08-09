"""
state.py — Central project_state.json manager.

The state file is the single source of truth for the whole pipeline.
Every shot records all attempts in a decision log — this is the evidence
that the system is agentic, and it doubles as dissertation evaluation data.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import STATE_FILE, MAX_REPAIR_ATTEMPTS, ROOT_DIR


# ─── State Schema ─────────────────────────────────────────────────────────

def make_initial_state(
    reference_video: str,
    ip_images: list[str],
    scene_prompt: str,
    character_description: str,
) -> dict:
    return {
        "schema_version": "1.0",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "reference_video": reference_video,
        "ip_character": {
            "reference_images": ip_images,
            "description": character_description,
        },
        "scene_prompt": scene_prompt,
        "pipeline_stage": "init",
        # init → analyzed → templated → generating → evaluating → done
        "reference_data": {
            "shot_cuts": [],          # [{"frame": int, "time_s": float}]
            "beats": [],              # [{"time_s": float, "strength": float}]
            "bpm": None,
            "duration_s": None,
            "fps": None,
        },
        "shots": [],                  # list of shot dicts (see make_shot below)
        "run_stats": {
            "total_shots": 0,
            "passed": 0,
            "failed": 0,
            "needs_human": 0,
            "total_attempts": 0,
        },
    }


def make_shot(
    shot_id: str,
    beat_time_s: float,
    duration_s: float,
    framing: str,
    description: str,
    pose_keypoints: Optional[dict] = None,
    pose_image_path: Optional[str] = None,
) -> dict:
    return {
        "shot_id": shot_id,
        "beat_time_s": beat_time_s,
        "duration_s": duration_s,
        "framing": framing,
        "description": description,
        "pose_keypoints": pose_keypoints,   # MediaPipe landmark dict
        "pose_image_path": pose_image_path, # skeleton overlay image for ControlNet
        "generated_image": None,            # path to keyframe image
        "video_clip": None,                 # path to rendered clip
        "evaluation": {
            "status": "pending",            # pending | pass | fail | needs_human
            "attempts": [],                 # decision log (see log_attempt)
        },
    }


def make_attempt(
    attempt_num: int,
    scores: dict,
    verdict: str,
    diagnosis: str,
    repair_action: str,
    prompt_used: str = "",
) -> dict:
    """
    scores = {
        "identity": float,   # ArcFace cosine similarity (0-1)
        "pose": float,       # 1 - mean_keypoint_distance (0-1, higher = better)
        "framing": float,    # composition score (0-1)
        "beat_alignment_ms": float,  # ms error (lower = better)
    }
    verdict = "pass" | "fail"
    diagnosis = human-readable string explaining why it failed
    repair_action = what the system will do next
    """
    return {
        "attempt_num": attempt_num,
        "timestamp": datetime.now().isoformat(),
        "prompt_used": prompt_used,
        "scores": scores,
        "verdict": verdict,
        "diagnosis": diagnosis,
        "repair_action": repair_action,
    }


# ─── Read / Write ──────────────────────────────────────────────────────────

# ── Path re-anchoring: any stored absolute path that points inside the project
# folder is re-based onto the CURRENT project root on every load, so state stays
# portable across machines / locations (no more stale /sessions/... paths). ──
_PROJECT_NAME = "Reference-Driven Agentic Short-Form Video Generation System"

def _reanchor(obj):
    if isinstance(obj, dict):
        return {k: _reanchor(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_reanchor(v) for v in obj]
    if isinstance(obj, str) and _PROJECT_NAME in obj and ("/" in obj or "\\" in obj):
        tail = obj.rsplit(_PROJECT_NAME, 1)[-1].lstrip("/\\")
        return str(ROOT_DIR / tail) if tail else str(ROOT_DIR)
    return obj


def load() -> dict:
    if not STATE_FILE.exists():
        raise FileNotFoundError(f"State file not found: {STATE_FILE}")
    with open(STATE_FILE) as f:
        return _reanchor(json.load(f))


def save(state: dict) -> None:
    state["updated_at"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"[state] saved → {STATE_FILE}")


def init_state(
    reference_video: str,
    ip_images: list[str],
    scene_prompt: str,
    character_description: str,
) -> dict:
    state = make_initial_state(reference_video, ip_images, scene_prompt, character_description)
    save(state)
    return state


# ─── Shot helpers ──────────────────────────────────────────────────────────

def get_shot(state: dict, shot_id: str) -> Optional[dict]:
    for s in state["shots"]:
        if s["shot_id"] == shot_id:
            return s
    return None


def log_attempt(state: dict, shot_id: str, scores: dict, verdict: str,
                diagnosis: str, repair_action: str, prompt_used: str = "") -> dict:
    """Append an attempt to the shot's decision log. Updates shot status."""
    shot = get_shot(state, shot_id)
    if shot is None:
        raise ValueError(f"Shot {shot_id} not found in state")

    attempt_num = len(shot["evaluation"]["attempts"]) + 1
    attempt = make_attempt(attempt_num, scores, verdict, diagnosis, repair_action, prompt_used)
    shot["evaluation"]["attempts"].append(attempt)

    # Update status
    if verdict == "pass":
        shot["evaluation"]["status"] = "pass"
        state["run_stats"]["passed"] += 1
    elif attempt_num >= MAX_REPAIR_ATTEMPTS:
        shot["evaluation"]["status"] = "needs_human"
        state["run_stats"]["needs_human"] += 1
        print(f"[state] Shot {shot_id} hit max retries → needs_human")
    else:
        shot["evaluation"]["status"] = "fail"

    state["run_stats"]["total_attempts"] += 1
    save(state)
    return shot


def update_shot_output(state: dict, shot_id: str,
                       generated_image: Optional[str] = None,
                       video_clip: Optional[str] = None) -> None:
    shot = get_shot(state, shot_id)
    if shot is None:
        raise ValueError(f"Shot {shot_id} not found")
    if generated_image:
        shot["generated_image"] = generated_image
    if video_clip:
        shot["video_clip"] = video_clip
    save(state)


def set_stage(state: dict, stage: str) -> None:
    state["pipeline_stage"] = stage
    save(state)
    print(f"[state] pipeline_stage → {stage}")


# ─── Summary ──────────────────────────────────────────────────────────────

def print_summary(state: dict) -> None:
    stats = state["run_stats"]
    shots = state["shots"]
    print("\n" + "="*50)
    print(f"PIPELINE SUMMARY  ({state['pipeline_stage']})")
    print("="*50)
    print(f"  Total shots    : {stats['total_shots']}")
    print(f"  Passed         : {stats['passed']}")
    print(f"  Failed         : {stats['failed']}")
    print(f"  Needs human    : {stats['needs_human']}")
    print(f"  Total attempts : {stats['total_attempts']}")
    print("─"*50)
    for s in shots:
        ev = s["evaluation"]
        n = len(ev["attempts"])
        print(f"  {s['shot_id']:12s}  {ev['status']:12s}  attempts={n}")
    print("="*50 + "\n")
