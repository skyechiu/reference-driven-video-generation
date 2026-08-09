"""
stage1_analyze.py — Reference Video Analyzer

Extracts from the reference video:
  - Shot cuts (PySceneDetect)
  - Audio beats + BPM (librosa)
  - Pose keypoints per shot (MediaPipe)
  - Framing classification per shot

All deterministic tool outputs. No LLM guessing here.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import librosa
import numpy as np

import base64
from pathlib import Path as _Path

# MediaPipe — try new Tasks API (0.10.30+), fall back gracefully
MEDIAPIPE_OK = False
_landmarker_options = None
_MP_MODEL = _Path(__file__).parent / "models" / "pose_landmarker_full.task"

try:
    import mediapipe as mp
    from mediapipe.tasks import python as _mp_python
    from mediapipe.tasks.python import vision as _mp_vision

    if _MP_MODEL.exists():
        _base_opts = _mp_python.BaseOptions(model_asset_path=str(_MP_MODEL))
        _landmarker_options = _mp_vision.PoseLandmarkerOptions(
            base_options=_base_opts,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
        )
        MEDIAPIPE_OK = True
        print("[analyze] MediaPipe Tasks API ready")
    else:
        print(f"[analyze] WARNING: model not found at {_MP_MODEL}. "
              "Run: curl -L https://storage.googleapis.com/.../pose_landmarker_full.task -o pipeline/models/pose_landmarker_full.task")
except (ImportError, AttributeError, Exception) as _mp_err:
    print(f"[analyze] WARNING: mediapipe unavailable ({_mp_err}). Pose extraction skipped.")

from config import OUTPUT_DIR
import state as st


# ─── Shot Detection ───────────────────────────────────────────────────────

def detect_shots(video_path: str, threshold: float = 27.0) -> list[dict]:
    """
    Use PySceneDetect ContentDetector to find shot cuts.
    Returns list of {frame, time_s}.
    """
    from scenedetect import open_video, SceneManager
    from scenedetect.detectors import ContentDetector

    print(f"[analyze] detecting shots in {video_path}")
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()

    shots = []
    for i, (start, end) in enumerate(scene_list):
        shots.append({
            "shot_index": i,
            "start_frame": start.get_frames(),
            "start_time_s": start.get_seconds(),
            "end_frame": end.get_frames(),
            "end_time_s": end.get_seconds(),
            "duration_s": end.get_seconds() - start.get_seconds(),
        })

    print(f"[analyze] found {len(shots)} candidate cuts")
    return shots


# ─── Cut Validation & False-Cut Merge ─────────────────────────────────────

def _luma_at_boundary(video_path: str, boundary_time_s: float, fps: float) -> tuple[float, float]:
    """
    Read one frame just before and just after a cut boundary.
    Returns (luma_before, luma_after).
    """
    cap = cv2.VideoCapture(video_path)
    fn = int(boundary_time_s * fps)

    def read_luma(frame_n):
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_n))
        ret, f = cap.read()
        if not ret:
            return 128.0
        return float(np.mean(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)))

    lb = read_luma(fn - 2)
    la = read_luma(fn + 1)
    cap.release()
    return lb, la


def _is_hard_cut(video_path: str, shot_a: dict, shot_b: dict, fps: float) -> tuple[bool, str]:
    """
    Returns (is_hard_cut, reason).
    A hard cut has: near-black boundary frame OR luma jump > 40.
    """
    boundary = shot_b["start_time_s"]
    try:
        lb, la = _luma_at_boundary(video_path, boundary, fps)
    except Exception:
        return False, "boundary_read_failed"

    if min(lb, la) < 12:
        return True, f"near_black_frame (luma {min(lb,la):.0f})"
    jump = abs(la - lb)
    if jump > 45:
        return True, f"luma_jump_{jump:.0f}"
    return False, f"luma_ok ({lb:.0f}→{la:.0f})"


def _pose_present(shot: dict) -> bool:
    kpts = shot.get("pose_keypoints")
    if not kpts:
        return False
    visible = [v for v in kpts.values() if isinstance(v, dict) and v.get("visibility", 0) > 0.4]
    return len(visible) >= 5


def _subject_motion_low(shot: dict) -> bool:
    """True if the subject is relatively static (low motion_direction count)."""
    dirs = shot.get("motion_direction") or []
    # motion_direction is a list of detected motion classes; 0-1 = static/minimal
    return len(dirs) <= 1


def _framing_label_to_scale(framing: str) -> int:
    """Map framing label to an integer scale for jump detection (lower = tighter)."""
    scale = {
        "extreme-close-up": 0, "close-up": 1, "medium-close-up": 2,
        "medium": 3, "medium-wide": 4, "wide": 5, "extreme-wide": 6,
    }
    return scale.get(framing, 3)


def _luma_jump_at_boundary(video_path: str, shot_a: dict, shot_b: dict, fps: float) -> float:
    """Return normalised luminance jump 0–1 at the cut boundary."""
    try:
        lb, la = _luma_at_boundary(video_path, shot_b["start_time_s"], fps)
        return min(abs(la - lb) / 255.0, 1.0)
    except Exception:
        return 0.0


def score_merge_candidate(
    video_path: str,
    shot_a: dict,
    shot_b: dict,
    fps: float,
) -> tuple[float, list[str], str]:
    """
    Multi-signal merge scoring. Returns (merge_score 0–1, why_list, cam_type).

    merge_score > threshold → suggest merge
    merge_score < threshold → suggest keep cut

    Signals that RAISE the merge score (false-cut evidence):
      + subject pose appears in both shots
      + subject is stationary (camera orbit / slow pan)
      + luma jump is small (no flash cut)

    Signals that LOWER the merge score (real-cut evidence):
      − large luminance jump at boundary
      − framing / shot-scale changes significantly
      − subject position jumps
      − gap between shots (> 0.1s)
    """
    why:     list[str] = []
    cam_type = "unknown"
    score    = 0.0

    # ── Hard veto: never merge if gap > 0.3 s ─────────────────────
    gap = shot_b["start_time_s"] - shot_a["end_time_s"]
    if gap > 0.3:
        return 0.0, [f"gap_{gap:.2f}s — hard boundary"], "gap"

    # ── Hard veto: obvious hard cut ────────────────────────────────
    hard, hard_reason = _is_hard_cut(video_path, shot_a, shot_b, fps)
    if hard:
        return 0.0, [f"hard_cut: {hard_reason}"], "hard_cut"

    # ── Signal: luminance jump ─────────────────────────────────────
    luma_jump = _luma_jump_at_boundary(video_path, shot_a, shot_b, fps)
    if luma_jump < 0.10:
        score += 0.15
        why.append(f"smooth_luminance_transition ({luma_jump:.2f})")
    elif luma_jump > 0.25:
        score -= 0.20
        why.append(f"luminance_jump ({luma_jump:.2f}) — composition change")

    # ── Signal: pose continuity ────────────────────────────────────
    pose_a = _pose_present(shot_a)
    pose_b = _pose_present(shot_b)

    if pose_a and pose_b:
        score += 0.20
        why.append("pose_detected_in_both")
    elif not pose_a and not pose_b:
        # Can't verify subject — lean conservative (keep cut)
        score -= 0.10
        why.append("no_pose_in_either — uncertain")
    else:
        # One shot has pose, one doesn't → subject likely changed
        score -= 0.30
        why.append("pose_only_in_one_shot — subject likely changed")

    # ── Signal: subject motion level ──────────────────────────────
    if pose_a and pose_b:
        low_a = _subject_motion_low(shot_a)
        low_b = _subject_motion_low(shot_b)
        if low_a and low_b:
            score += 0.35
            cam_type = "orbit"
            why.append("subject_stationary_in_both — likely camera orbit")
        else:
            # Subject is moving in both — could be real cut or false cut.
            # CONSERVATIVE: do NOT boost score just because subject continues.
            # In real multi-shot edits, the subject often appears in adjacent shots.
            score += 0.05
            why.append("subject_moving_in_both — insufficient for merge alone")

    # ── Signal: framing / shot-scale change ───────────────────────
    scale_a = _framing_label_to_scale(shot_a.get("framing", "unknown"))
    scale_b = _framing_label_to_scale(shot_b.get("framing", "unknown"))
    scale_delta = abs(scale_a - scale_b)
    if scale_delta == 0:
        score += 0.05
        why.append("framing_unchanged")
    elif scale_delta == 1:
        score -= 0.05
        why.append(f"framing_minor_change ({shot_a.get('framing','?')} → {shot_b.get('framing','?')})")
    elif scale_delta >= 2:
        score -= 0.30
        why.append(f"framing_jump ({shot_a.get('framing','?')} → {shot_b.get('framing','?')}) — real cut")

    return max(0.0, min(1.0, score)), why, cam_type


# Merge threshold per mode. Score must EXCEED this to trigger a merge suggestion.
_MERGE_THRESHOLDS = {
    "conservative": 0.75,   # hard to merge — prefer to keep raw cuts
    "balanced":     0.55,   # default
    "aggressive":   0.40,   # merge more false cuts (good for single-take)
}

_DEFAULT_MERGE_MODE = "conservative"   # Multi-shot default: keep raw cuts


def suggest_merge(
    video_path: str,
    shot_a: dict,
    shot_b: dict,
    fps: float,
    merge_mode: str = _DEFAULT_MERGE_MODE,
) -> tuple[bool, float, list[str], str]:
    """
    Returns (should_merge: bool, confidence: float, why: list[str], cam_type: str).
    Does NOT hard-merge — returns a suggestion that the UI can override.
    """
    score, why, cam_type = score_merge_candidate(video_path, shot_a, shot_b, fps)
    threshold = _MERGE_THRESHOLDS.get(merge_mode, 0.55)
    return score >= threshold, round(score, 3), why, cam_type


def merge_false_cuts(
    candidates: list[dict],
    video_path: str,
    fps: float,
    merge_mode: str = _DEFAULT_MERGE_MODE,
) -> tuple[list[dict], list[dict]]:
    """
    Pass over candidate cuts and merge those that score above threshold.

    Returns:
        merged_shots  — final shot list
        merge_log     — per-boundary record with suggestion + confidence
                        (NOT a hard decision — UI can override via Restore Split)
    """
    if len(candidates) <= 1:
        for c in candidates:
            c.setdefault("shot_type", "single_take" if len(candidates) == 1 else "cut")
            c.setdefault("camera_motion_type", "unknown")
            c.setdefault("key_moments", [])
        return list(candidates), []

    merge_log: list[dict] = []
    groups:    list[list[dict]] = [[candidates[0]]]

    for i in range(1, len(candidates)):
        prev = groups[-1][-1]
        curr = candidates[i]
        do_merge, confidence, why, cam_type = suggest_merge(
            video_path, prev, curr, fps, merge_mode
        )

        merge_log.append({
            "boundary_s":         curr["start_time_s"],
            "candidates":         [prev["shot_index"], curr["shot_index"]],
            # ── NEW VOCABULARY ──────────────────────────────────────────
            "suggestion":         "merge" if do_merge else "keep",
            "confidence":         confidence,
            "merge_mode":         merge_mode,
            "why":                why,
            "camera_motion_type": cam_type,
            # ── LEGACY COMPAT (kept for any old code) ──────────────────
            "merge_decision":     do_merge,
            "reason":             " | ".join(why),
            # User override — None = not yet reviewed
            "user_decision":      None,
        })

        effective_merge = do_merge   # user_decision can override in UI
        if effective_merge:
            groups[-1].append(curr)
            print(f"  [merge] suggest MERGE cand_{prev['shot_index']:03d}+{curr['shot_index']:03d} "
                  f"(score={confidence:.2f}, mode={merge_mode})")
        else:
            groups.append([curr])
            print(f"  [merge] suggest KEEP  cand_{prev['shot_index']:03d}|{curr['shot_index']:03d} "
                  f"(score={confidence:.2f}, mode={merge_mode})")

    # Build merged shot dicts
    merged_shots: list[dict] = []
    for g_idx, group in enumerate(groups):
        if len(group) == 1:
            s = group[0].copy()
            s["shot_type"] = "hard_cut"
            s["camera_motion_type"] = "unknown"
            s["key_moments"] = []
            s["merged_from"] = [s["shot_index"]]
            s["shot_index"] = g_idx
            merged_shots.append(s)
        else:
            # Merge the group
            base = group[0].copy()
            base["end_time_s"]       = group[-1]["end_time_s"]
            base["end_frame"]        = group[-1].get("end_frame", group[-1]["shot_index"])
            base["duration_s"]       = round(base["end_time_s"] - base["start_time_s"], 3)
            base["shot_type"]        = "single_take"
            base["camera_motion_type"] = "orbit"  # most common reason for merge

            # Inherit best pose from group
            best_pose = next((s for s in group if _pose_present(s)), group[0])
            base["pose_keypoints"]   = best_pose.get("pose_keypoints")
            base["pose_image"]       = best_pose.get("pose_image")
            base["framing"]          = best_pose.get("framing", "unknown")

            # Combine motion directions
            all_dirs = []
            for s in group:
                all_dirs.extend(s.get("motion_direction") or [])
            base["motion_direction"] = list(dict.fromkeys(all_dirs))[:4]

            # Description from best-pose segment
            base["description"] = best_pose.get("description", group[0].get("description", ""))

            # Key moments = each original candidate becomes a moment
            base["key_moments"] = [
                {
                    "moment_id":   f"m{j+1:02d}",
                    "time_s":      s["start_time_s"],
                    "end_time_s":  s["end_time_s"],
                    "source_panel": s.get("source_panel", ""),
                    "framing":     s.get("framing", "unknown"),
                    "view":        "unknown",     # filled by VLM in stage2
                    "pose_keypoints": s.get("pose_keypoints"),
                }
                for j, s in enumerate(group)
            ]
            base["merged_from"] = [s["shot_index"] for s in group]
            base["shot_index"]  = g_idx
            merged_shots.append(base)

    return merged_shots, merge_log


# ─── Beat Detection ───────────────────────────────────────────────────────

def detect_beats(video_path: str) -> dict:
    """
    Extract audio from video, detect beats + BPM with librosa.
    Returns {bpm, beats: [{time_s, strength}], duration_s}.
    """
    print(f"[analyze] extracting beats from audio")
    try:
        y, sr = librosa.load(video_path, mono=True)
    except Exception as e:
        print(f"[analyze] WARNING: no audio track or audio unreadable ({e}). "
              "Beat alignment will be skipped.")
        dur = float(subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True,
        ).stdout.strip() or "0")
        return {"bpm": 0.0, "beats": [], "duration_s": dur}
    duration_s = librosa.get_duration(y=y, sr=sr)

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    # librosa ≥0.10 returns tempo as a 1-element ndarray; extract scalar
    import numpy as _np
    tempo_val = float(_np.asarray(tempo).ravel()[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Get onset strength at each beat for relative strength
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    beat_strengths = onset_env[beat_frames] if len(beat_frames) > 0 else []
    if len(beat_strengths) > 0:
        beat_strengths = (beat_strengths / beat_strengths.max()).tolist()

    beats = [
        {"time_s": float(t), "strength": float(s)}
        for t, s in zip(beat_times, beat_strengths)
    ]

    print(f"[analyze] BPM={tempo_val:.1f}, {len(beats)} beats, duration={duration_s:.1f}s")
    return {
        "bpm": tempo_val,
        "beats": beats,
        "duration_s": float(duration_s),
    }


# ─── Frame Extraction ─────────────────────────────────────────────────────

def extract_frames_for_shot(video_path: str, shot: dict, n: int = 3) -> list:
    """
    Extract n evenly spaced frames from a shot.
    Returns list of BGR numpy arrays.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    start = shot["start_time_s"]
    end = shot["end_time_s"]
    frames = []
    for i in range(n):
        t = start + (end - start) * (i / max(n - 1, 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    cap.release()
    return frames


# ─── MediaPipe Tasks API Pose Extraction ─────────────────────────────────

def _extract_keypoints_tasks(frame_bgr) -> Optional[dict]:
    """Extract pose keypoints from one frame using MediaPipe Tasks API."""
    if not MEDIAPIPE_OK:
        return None
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with _mp_vision.PoseLandmarker.create_from_options(_landmarker_options) as landmarker:
        result = landmarker.detect(mp_image)
    if not result.pose_landmarks:
        return None
    # Landmark names from PoseLandmark enum
    NAMES = [
        "NOSE","LEFT_EYE_INNER","LEFT_EYE","LEFT_EYE_OUTER",
        "RIGHT_EYE_INNER","RIGHT_EYE","RIGHT_EYE_OUTER",
        "LEFT_EAR","RIGHT_EAR","MOUTH_LEFT","MOUTH_RIGHT",
        "LEFT_SHOULDER","RIGHT_SHOULDER","LEFT_ELBOW","RIGHT_ELBOW",
        "LEFT_WRIST","RIGHT_WRIST","LEFT_PINKY","RIGHT_PINKY",
        "LEFT_INDEX","RIGHT_INDEX","LEFT_THUMB","RIGHT_THUMB",
        "LEFT_HIP","RIGHT_HIP","LEFT_KNEE","RIGHT_KNEE",
        "LEFT_ANKLE","RIGHT_ANKLE","LEFT_HEEL","RIGHT_HEEL",
        "LEFT_FOOT_INDEX","RIGHT_FOOT_INDEX",
    ]
    kpts = {}
    for name, lm in zip(NAMES, result.pose_landmarks[0]):
        kpts[name] = {"x": lm.x, "y": lm.y, "z": lm.z, "visibility": lm.visibility}
    return kpts


def get_motion_direction(keypoints_start: Optional[dict], keypoints_end: Optional[dict]) -> str:
    """
    Infer motion direction by comparing start vs end frame keypoints.
    Returns a short description string, e.g. 'moving left, approaching camera'.
    """
    if keypoints_start is None or keypoints_end is None:
        return ""

    parts = []

    # Horizontal direction — use nose or mid-shoulder
    def mid_x(kpts):
        ls = kpts.get("LEFT_SHOULDER", {}).get("x")
        rs = kpts.get("RIGHT_SHOULDER", {}).get("x")
        if ls and rs:
            return (ls + rs) / 2
        return kpts.get("NOSE", {}).get("x")

    sx, ex = mid_x(keypoints_start), mid_x(keypoints_end)
    if sx is not None and ex is not None:
        dx = ex - sx
        if abs(dx) > 0.04:
            parts.append("moving right" if dx > 0 else "moving left")

    # Camera distance — shoulder width (larger = closer to camera)
    def shoulder_width(kpts):
        ls = kpts.get("LEFT_SHOULDER")
        rs = kpts.get("RIGHT_SHOULDER")
        if ls and rs:
            return abs(rs["x"] - ls["x"])
        return None

    sw_s, sw_e = shoulder_width(keypoints_start), shoulder_width(keypoints_end)
    if sw_s is not None and sw_e is not None:
        dw = sw_e - sw_s
        if abs(dw) > 0.03:
            parts.append("approaching camera" if dw > 0 else "moving away from camera")

    # Camera orientation — nose visibility vs back of head heuristic
    nose_s = keypoints_start.get("NOSE", {}).get("visibility", 0)
    nose_e = keypoints_end.get("NOSE", {}).get("visibility", 0)
    if nose_s < 0.3 and nose_e < 0.3:
        parts.append("back to camera")
    elif nose_s > 0.7 and nose_e > 0.7:
        parts.append("facing camera")
    elif nose_s > 0.5 and nose_e < 0.3:
        parts.append("turning away from camera")
    elif nose_s < 0.3 and nose_e > 0.5:
        parts.append("turning toward camera")

    return ", ".join(parts)


def extract_pose_for_shot(video_path: str, shot: dict, output_dir: Path) -> dict:
    """
    Extract pose keypoints and motion direction for a shot.
    Uses MediaPipe Tasks API on start + end frames.
    Returns keypoints (mid frame) + motion_direction string.
    """
    frames = extract_frames_for_shot(video_path, shot, n=3)
    if not frames:
        return {"keypoints": None, "pose_image": None, "motion_direction": ""}

    # Save skeleton overlay from mid frame (for ControlNet / visual reference)
    pose_img_path = None
    mid_frame = frames[len(frames) // 2]
    kpts_mid = _extract_keypoints_tasks(mid_frame) if MEDIAPIPE_OK else None

    if MEDIAPIPE_OK and kpts_mid:
        h, w = mid_frame.shape[:2]
        skeleton_img = np.zeros((h, w, 3), dtype=np.uint8)
        # Draw landmarks manually (Tasks API doesn't have drawing_utils)
        for kpt in kpts_mid.values():
            if kpt["visibility"] > 0.3:
                px, py = int(kpt["x"] * w), int(kpt["y"] * h)
                cv2.circle(skeleton_img, (px, py), 5, (0, 255, 0), -1)
        pose_img_path = output_dir / f"pose_{shot['shot_index']:03d}.png"
        cv2.imwrite(str(pose_img_path), skeleton_img)

    # Motion direction from start vs end frame
    kpts_start = _extract_keypoints_tasks(frames[0]) if MEDIAPIPE_OK else None
    kpts_end = _extract_keypoints_tasks(frames[-1]) if MEDIAPIPE_OK else None
    motion = get_motion_direction(kpts_start, kpts_end)

    return {
        "keypoints": kpts_mid,
        "pose_image": str(pose_img_path) if pose_img_path else None,
        "motion_direction": motion,
    }


# ─── Framing Classification ───────────────────────────────────────────────

def classify_framing(keypoints: Optional[dict]) -> str:
    """
    Heuristic framing classification from pose keypoints.
    Returns one of: extreme-close-up | close-up | medium-close-up |
                    medium | medium-wide | wide | extreme-wide
    """
    if keypoints is None:
        return "unknown"

    # Use vertical span of visible landmarks to estimate framing
    visible = [v for v in keypoints.values() if v["visibility"] > 0.5]
    if not visible:
        return "unknown"

    ys = [v["y"] for v in visible]
    span = max(ys) - min(ys)

    if span < 0.15:
        return "extreme-close-up"
    elif span < 0.30:
        return "close-up"
    elif span < 0.45:
        return "medium-close-up"
    elif span < 0.60:
        return "medium"
    elif span < 0.75:
        return "medium-wide"
    elif span < 0.90:
        return "wide"
    else:
        return "extreme-wide"


# ─── GPT-4o Vision Shot Description ─────────────────────────────────────

def describe_shot_gpt4o(frames: list, client=None) -> str:
    """
    Send 1-3 frames to GPT-4o and get a concise shot description.
    Returns a short string describing what the person is doing.
    """
    if not frames:
        return ""
    try:
        from openai import OpenAI
        from config import OPENAI_API_KEY
        if client is None:
            client = OpenAI(api_key=OPENAI_API_KEY)

        # Encode frames as base64 JPEG
        content = [{
            "type": "text",
            "text": (
                "These are sequential frames from one shot of a short film. "
                "In 15 words or less, describe: body orientation relative to camera, "
                "direction of movement, and main action. "
                "Example: 'person walking away from camera through corridor' or "
                "'woman facing camera, standing still, gentle smile'."
            )
        }]
        for frame in frames[:3]:
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            b64 = base64.b64encode(buf).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"}
            })

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=60,
        )
        desc = response.choices[0].message.content.strip()
        print(f"    GPT-4o: {desc}")
        return desc
    except Exception as e:
        print(f"    [warn] GPT-4o description failed: {e}")
        return ""


def generate_shot_description(frames: list, motion_direction: str, gpt4o_client=None) -> str:
    """
    Combine GPT-4o semantic description + MediaPipe motion direction
    into a single shot description for the storyboard.
    """
    gpt_desc = describe_shot_gpt4o(frames, client=gpt4o_client)
    parts = [p for p in [gpt_desc, motion_direction] if p]
    return "; ".join(parts) if parts else ""


# ─── Unified Storyboard Builder ──────────────────────────────────────────

def build_storyboard(
    shots: list,
    dance_segments: list,
    motion_analysis: dict,
    recommended_strategy: str,
    beat_data: dict,
    video_path: str,
    output_dir: Path,
    key_moments: list = None,
    reference_type: str = "multi_shot",
) -> dict:
    """
    Build the unified storyboard JSON from analysis results.

    Strategy routing:
      shot_storyboard        → Strategy A: shots array, unit_type="shot"
      single_take_key_moments→ Strategy B: shots array of key moments, unit_type="key_moment_clip"
      key_pose_sequence      → Strategy C: segments array, unit_type="dance_segment"

    All generation_units downstream share the same core loop.
    """
    motion_type = motion_analysis.get("category", "unknown")

    # Normalise strategy value from dance_analyzer naming
    _norm = {
        "shot_based":    "shot_storyboard",
        "shot":          "shot_storyboard",
        "storyboard":    "shot_storyboard",
        "key_pose":      "key_pose_sequence",
        "dance":         "key_pose_sequence",
        "dance_key_pose":"key_pose_sequence",
    }
    strategy = _norm.get(recommended_strategy, recommended_strategy)
    known = ("shot_storyboard", "key_pose_sequence", "single_take_key_moments")
    if strategy not in known:
        strategy = "key_pose_sequence" if (motion_type in ("dance", "high")) else "shot_storyboard"

    panels_dir   = output_dir / "ref_panels"
    pose_ref_dir = output_dir / "pose_refs"
    panels_dir.mkdir(parents=True, exist_ok=True)
    pose_ref_dir.mkdir(parents=True, exist_ok=True)

    total_dur = beat_data.get("duration_s", 0.0)
    beats     = beat_data.get("beats", [])

    def snap_beat(t: float, max_snap: float = 0.15) -> Optional[float]:
        """Return nearest beat time within max_snap seconds, else None."""
        if not beats:
            return None
        nb = min(beats, key=lambda b: abs(b["time_s"] - t))
        return nb["time_s"] if abs(nb["time_s"] - t) <= max_snap else None

    # ── Strategy B: Single-take key moments ──────────────────────────────
    if strategy == "single_take_key_moments":
        moments = key_moments or []
        # Assign clip durations: gap between consecutive moments, capped at 2s
        units = []
        for i, m in enumerate(moments):
            t_start = m["time_s"]
            t_end   = moments[i + 1]["time_s"] if i + 1 < len(moments) else total_dur
            clip_dur = min(round(t_end - t_start, 3), 2.0)
            units.append({
                "shot_id":      f"shot_{i+1:03d}",
                "unit_id":      m["moment_id"],
                "unit_type":    "key_moment_clip",
                "start":        t_start,
                "end":          t_start + clip_dur,
                "duration_s":   clip_dur,
                "source_panel": m["source_panel"],
                "pose_ref":     "",
                "sampling_reason": m.get("reason", "interval"),
                "framing_target": {"shot_type": "unknown", "description": ""},
                "motion_prompt":  "short clip from continuous single-take, subtle camera motion",
                "beat_cut":       None,
                "continuity_note": "part of a continuous single-take; camera or subject may move between moments",
            })
        return {
            "input_type":        "reference_video",
            "reference_type":    "single_take",
            "motion_type":       motion_type,
            "strategy":          "single_take_key_moments",
            "character_mode":    "single_primary_subject",
            "total_duration_s":  total_dur,
            "shots":             units,
            "continuity_context": {
                "raw_candidate_cuts":       len(shots) if shots else 0,
                "final_shots_after_merge":  1,
                "merge_applied":            True,
                "subject_motion":           "continuous",
                "camera_motion":            "continuous",
            },
        }

    # ── Strategy C: Dance / key-pose path ────────────────────────────────
    if strategy == "key_pose_sequence" and dance_segments:
        units = []
        for i, seg in enumerate(dance_segments):
            seg_id = seg.get("segment_id") or f"dance_seg_{i+1:03d}"
            start  = float(seg.get("start_time_s", seg.get("start", 0.0)))
            end    = float(seg.get("end_time_s",   seg.get("end",   0.0)))
            units.append({
                "unit_id":       seg_id,
                "unit_type":     "dance_segment",
                "segment_id":    seg_id,
                "start":         start,
                "end":           end,
                "duration_s":    round(end - start, 3),
                "source_panel":  seg.get("pose_ref") or seg.get("source_panel") or "",
                "pose_sequence": seg.get("pose_sequence", ""),
                "main_pose":     seg.get("pose_ref") or "",
                "beat_target":   seg.get("beat_target", start),
                "framing_target": {
                    "shot_type":   "full_body",
                    "description": "full body visible, person centred, stable camera",
                },
                "motion_prompt":   seg.get("motion_prompt")
                                   or "short controlled dance movement, full body visible, stable camera",
                "dominant_motion": seg.get("dominant_motion", ""),
                "priority":        ["pose", "body_integrity", "identity", "framing"],
                "backend_config": {
                    "type": "pose_guided_human_animation",
                    "name": "mimicmotion",
                    "status": "placeholder",
                },
                "risk_flags": ["high_motion", "hand_deformation_risk", "identity_drift_risk"],
            })
        return {
            "input_type":       "reference_video",
            "reference_type":   "driving_performance",
            "motion_type":      motion_type,
            "strategy":         "key_pose_sequence",
            "character_mode":   "single_primary_subject",
            "sampling_fps":     8,
            "total_duration_s": total_dur,
            "segments":         units,
        }

    # ── Strategy A: Normal shot-storyboard path ──────────────────────────
    cap    = cv2.VideoCapture(video_path)
    fps_v  = cap.get(cv2.CAP_PROP_FPS) or 25.0
    units  = []
    for shot in shots:
        i       = shot.get("shot_index", 0)
        shot_id = f"shot_{i+1:03d}"
        start   = float(shot["start_time_s"])
        end     = float(shot["end_time_s"])

        # Save best (middle) frame as source panel
        mid_t = (start + end) / 2.0
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(mid_t * fps_v))
        ret, frame = cap.read()
        panel_path = ""
        if ret:
            panel_path = str(panels_dir / f"{shot_id}_best.png")
            cv2.imwrite(panel_path, frame)

        # Save pose keypoints as companion JSON
        pose_ref_path = ""
        kpts = shot.get("pose_keypoints")
        if kpts:
            pose_ref_path = str(pose_ref_dir / f"{shot_id}_pose.json")
            with open(pose_ref_path, "w") as pf:
                json.dump(kpts, pf)

        # Beat-snap the cut point
        beat_cut = snap_beat(end)

        units.append({
            "shot_id":    shot_id,
            "unit_id":    shot_id,
            "unit_type":  "shot",
            "start":      start,
            "end":        end,
            "duration_s": round(end - start, 3),
            "source_panel": panel_path,
            "pose_ref":     pose_ref_path,
            "framing_target": {
                "shot_type":   shot.get("framing", "unknown"),
                "description": shot.get("description", ""),
            },
            "motion_prompt": shot.get("description", ""),
            "beat_cut":      beat_cut,
        })
    cap.release()

    return {
        "input_type":       "reference_video",
        "reference_type":   reference_type,
        "motion_type":      motion_type,
        "strategy":         "shot_storyboard",
        "character_mode":   "single_primary_subject",
        "total_duration_s": total_dur,
        "shots":            units,
    }


# ─── Key Moment Sampler (Single-take Strategy B) ─────────────────────────

def _sample_key_moments(video_path: str, duration_s: float, beats: list, fps: float,
                        interval_s: float = 2.0, output_dir: Path = None) -> list:
    """
    Extract key moments from a single-take video.
    Samples at fixed intervals + beat-near frames + start/end.
    Returns list of {time_s, reason, source_panel}.
    """
    import cv2 as _cv2
    panels_dir = (output_dir if output_dir is not None else OUTPUT_DIR) / "ref_panels"
    panels_dir.mkdir(parents=True, exist_ok=True)

    # Build candidate timestamps: every interval_s, plus start and end
    times: list[float] = [0.0]
    t = interval_s
    while t < duration_s - 0.5:
        times.append(round(t, 3))
        t += interval_s
    times.append(round(duration_s, 3))

    # Add beat-near frames (snap within 0.2s that aren't already close to a sampled time)
    for b in beats:
        bt = b["time_s"]
        if not any(abs(bt - existing) < 0.4 for existing in times):
            times.append(round(bt, 3))

    times = sorted(set(times))

    cap = _cv2.VideoCapture(video_path)
    moments = []
    for i, t_s in enumerate(times):
        frame_idx = int(t_s * fps)
        cap.set(_cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        panel_path = ""
        if ret:
            panel_path = str(panels_dir / f"moment_{i+1:03d}_t{t_s:.1f}s.png")
            _cv2.imwrite(panel_path, frame)
        reason = "interval"
        if t_s == 0.0:        reason = "start"
        elif t_s >= duration_s - 0.1: reason = "end"
        elif any(abs(t_s - b["time_s"]) < 0.25 for b in beats): reason = "beat"
        moments.append({
            "moment_id":    f"m{i+1:02d}",
            "time_s":       t_s,
            "reason":       reason,
            "source_panel": panel_path,
            "unit_type":    "key_moment_clip",
        })
    cap.release()
    print(f"[analyze] single-take: sampled {len(moments)} key moments at {[m['time_s'] for m in moments]}")
    return moments


# ─── Main Analyzer ───────────────────────────────────────────────────────

def run(video_path: str, state: dict) -> dict:
    """
    Full reference analysis. Updates state with all extracted data.

    Reference Strategy routing (set by user in Setup or auto-detected):
      multi_shot  → Strategy A: shot cut detection + storyboard
      single_take → Strategy B: continuity merge + key moment sampling
      dance       → Strategy C: pose sequence extraction (key_pose_sequence)
      auto        → let analysis decide (dance_analyzer + merge logic)
    """
    # Use per-run output dir if available (set by upload route), else fall back to global OUTPUT_DIR
    _run_dir_str = (state.get("config") or {}).get("run_dir", "")
    _run_dir = Path(_run_dir_str) if _run_dir_str else OUTPUT_DIR
    pose_dir = _run_dir / "analysis"
    pose_dir.mkdir(parents=True, exist_ok=True)

    # Read user-selected reference type from state config
    user_video_type = (state.get("config") or {}).get("video_type", "auto")
    print(f"[analyze] reference_type from setup: {user_video_type}")

    # 1. Shot cuts
    shots = detect_shots(video_path)

    # 2. Audio beats
    beat_data = detect_beats(video_path)

    # Clamp shot end times to actual video duration (PySceneDetect can overshoot)
    video_dur = beat_data["duration_s"]
    if not video_dur:  # beat_data has no audio fallback, get from ffprobe
        import subprocess as _sp
        video_dur = float(_sp.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True).stdout.strip() or "0")
    for sh in shots:
        sh["end_time_s"]  = min(sh["end_time_s"],  video_dur)
        sh["duration_s"]  = max(0.0, sh["end_time_s"] - sh["start_time_s"])

    # 3. Video FPS
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    # 4. Pose + GPT-4o description per CANDIDATE shot
    from openai import OpenAI
    from config import OPENAI_API_KEY
    gpt4o_client = OpenAI(api_key=OPENAI_API_KEY)

    print(f"[analyze] extracting poses + descriptions for {len(shots)} candidates...")
    for shot in shots:
        frames = extract_frames_for_shot(video_path, shot, n=3)
        pose_result = extract_pose_for_shot(video_path, shot, pose_dir)
        shot["pose_keypoints"] = pose_result["keypoints"]
        shot["pose_image"] = pose_result["pose_image"]
        shot["framing"] = classify_framing(pose_result["keypoints"])
        shot["motion_direction"] = pose_result["motion_direction"]
        shot["description"] = generate_shot_description(
            frames, pose_result["motion_direction"], gpt4o_client
        )
        print(f"  cand_{shot['shot_index']:03d}  framing={shot['framing']:15s}  "
              f"t={shot['start_time_s']:.2f}-{shot['end_time_s']:.2f}s")

    # 4b. Merge false cuts (camera motion ≠ actual edit)
    _orig_candidates = [s.copy() for s in shots]   # preserve raw candidates before merge

    # Pick merge_mode from state: conservative for multi-shot, aggressive for single-take
    _strategy = (state.get("config") or {}).get("reference_strategy", "auto")
    _ui_merge_mode = (state.get("config") or {}).get("cut_merge_mode", None)
    if _ui_merge_mode in ("conservative", "balanced", "aggressive"):
        _merge_mode = _ui_merge_mode
    elif _strategy in ("single_take_key_moments", "key_pose_sequence"):
        _merge_mode = "aggressive"
    else:
        _merge_mode = "conservative"   # default: keep raw cuts for multi-shot

    print(f"[analyze] validating {len(shots)} candidate cuts (merge_mode={_merge_mode})...")
    final_shots, merge_log = merge_false_cuts(shots, video_path, float(fps), merge_mode=_merge_mode)
    n_suggested = sum(1 for m in merge_log if m.get("suggestion") == "merge")
    n_kept      = len(merge_log) - n_suggested
    print(f"[analyze] merge suggestions: {n_suggested} merge / {n_kept} keep "
          f"→ {len(final_shots)} final shot(s)")

    # Rename to final shots for downstream use
    shots = final_shots

    # ── Zero-cut fallback ─────────────────────────────────────────
    # PySceneDetect may find 0 scene cuts for single-take references
    # (static camera with subject movement, or slow continuous takes).
    # This is valid — treat the whole video as one continuous shot.
    # Do NOT let 0 shots become a "blocked" preflight; create shot_001.
    _zero_cut_fallback = False
    if not shots:
        print("[analyze] 0 cuts detected — treating reference as one continuous single-take shot (shot_001)")
        shots = [{
            "shot_index":        0,
            "shot_id":           "shot_001",
            "start_frame":       0,
            "start_time_s":      0.0,
            "end_frame":         int(float(fps) * video_dur),
            "end_time_s":        round(video_dur, 3),
            "duration_s":        round(video_dur, 3),
            "shot_type":         "single_take",
            "source":            "single_shot_fallback",
            "framing":           "medium",
            "motion_direction":  [],
            "motion_category":   "low",
            "mean_displacement": 0.0,
            "beat_aligned":      False,
            "semantic":          {},
            "description":       "No cuts detected — continuous single take",
            "pose_keypoints":    None,
            "pose_image":        None,
        }]
        _zero_cut_fallback = True

    # 5. Dance / motion category analysis
    # Skip dance analysis if user explicitly selected single_take or multi_shot
    skip_dance = user_video_type in ("single_take", "multi_shot")
    if skip_dance:
        print(f"[analyze] skipping dance analysis (user selected: {user_video_type})")
        dance_result = {
            "motion_analysis":      {"category": "normal", "confidence": 1.0, "suitability": {}},
            "dance_segments":       [],
            "recommended_strategy": "shot_storyboard",
        }
    else:
        print("[analyze] running motion analysis (dance detection)...")
        try:
            from dance_analyzer import run_dance_analysis
            dance_result = run_dance_analysis(
                video_path,
                extract_fn=_extract_keypoints_tasks,
                beats=beat_data["beats"],
                output_dir=_run_dir,
            )
        except Exception as e:
            print(f"[analyze] WARNING: dance analysis failed ({e}). Skipping.")
            dance_result = {
                "motion_analysis":      {"category": "unknown", "confidence": 0.0, "suitability": {}},
                "dance_segments":       [],
                "recommended_strategy": "shot_based",
            }

    # 6. Determine strategy and reference type
    motion_cat = dance_result["motion_analysis"].get("category", "unknown")
    raw_strategy = dance_result["recommended_strategy"]

    # Determine if all cuts were merged into one (orbit / single-take)
    all_single_take = (len(shots) == 1 and shots[0].get("shot_type") == "single_take")

    # User override takes precedence over auto-detection
    if user_video_type == "dance":
        raw_strategy = "key_pose_sequence"
        reference_type = "driving_performance"
    elif user_video_type == "single_take":
        raw_strategy = "single_take_key_moments"
        reference_type = "single_take"
    elif user_video_type == "multi_shot":
        raw_strategy = "shot_storyboard"
        reference_type = "multi_shot"
    else:
        # Auto: use analysis results
        if all_single_take:
            raw_strategy = "single_take_key_moments"
            reference_type = "single_take"
        elif raw_strategy == "key_pose_sequence":
            reference_type = "driving_performance"
        else:
            reference_type = "multi_shot"

    reference_type_source = "user_selected" if user_video_type != "auto" else "auto_detected"
    print(f"[analyze] reference_type={reference_type}  strategy={raw_strategy}  source={reference_type_source}")

    # 6b. For single_take strategy: sample key moments
    key_moments = []
    if raw_strategy == "single_take_key_moments":
        video_dur_for_moments = beat_data.get("duration_s", 0.0) or float(fps) and 0.0
        key_moments = _sample_key_moments(
            video_path=video_path,
            duration_s=video_dur_for_moments,
            beats=beat_data.get("beats", []),
            fps=float(fps),
            output_dir=_run_dir,
        )

    # Write reference_type to state root (used by downstream stages)
    state["reference_type"]        = reference_type
    state["reference_type_source"] = reference_type_source

    state["reference_data"] = {
        "candidate_cuts":       _orig_candidates,
        "shot_cuts":            shots,
        "beats":                beat_data["beats"],
        "bpm":                  beat_data["bpm"],
        "duration_s":           beat_data["duration_s"],
        "fps":                  float(fps),
        "motion_analysis":      dance_result["motion_analysis"],
        "dance_segments":       dance_result["dance_segments"],
        "recommended_strategy": raw_strategy,
        "reference_type":       reference_type,
        "reference_type_source": reference_type_source,
        "key_moments":          key_moments,
        "cut_validation": {
            "candidate_count":    len(_orig_candidates),
            "final_shot_count":   len(shots),
            # max(0,...) guards against the zero-cut fallback case where a
            # synthetic shot_001 is created from 0 candidates (not a merge).
            "false_cuts_merged":  max(0, len(_orig_candidates) - len(shots)),
            "zero_cut_fallback":  _zero_cut_fallback,
            "merge_log":          merge_log,
            "all_single_take":    all_single_take,
        },
    }

    # 7. Build unified storyboard JSON and write to state + disk
    print("[analyze] building unified storyboard JSON...")
    storyboard = build_storyboard(
        shots=shots,
        dance_segments=dance_result["dance_segments"],
        motion_analysis=dance_result["motion_analysis"],
        recommended_strategy=raw_strategy,
        beat_data=beat_data,
        video_path=video_path,
        output_dir=_run_dir,
        key_moments=key_moments,
        reference_type=reference_type,
    )
    state["storyboard"] = storyboard
    # Also mirror normalised strategy into reference_data for UI convenience
    state["reference_data"]["recommended_strategy"] = storyboard["strategy"]

    storyboard_path = _run_dir / "storyboard" / "storyboard.json"
    storyboard_path.parent.mkdir(parents=True, exist_ok=True)
    with open(storyboard_path, "w") as f:
        json.dump(storyboard, f, indent=2)
    # Store path in state so downstream stages can find it without guessing
    if "config" not in state:
        state["config"] = {}
    state["config"]["storyboard_path"] = str(storyboard_path)
    state["config"]["ref_panels_dir"]  = str(_run_dir / "ref_panels")
    unit_count = len(storyboard.get("shots", storyboard.get("segments", [])))
    print(f"[analyze] storyboard → {storyboard_path}  "
          f"strategy={storyboard['strategy']}  units={unit_count}")

    st.set_stage(state, "analyzed")
    st.save(state)

    print(f"[analyze] done — {len(shots)} shots, {len(beat_data['beats'])} beats, "
          f"motion={motion_cat}, strategy={storyboard['strategy']}")
    return state


if __name__ == "__main__":
    import sys
    s = st.load()

    if len(sys.argv) >= 2:
        video = sys.argv[1]
    else:
        # Fall back to video path stored in state (set by dashboard upload)
        video = (s.get("config", {}).get("reference_video", "")
                 or s.get("reference_video", ""))
        if not video:
            print("Usage: python stage1_analyze.py <video_path>")
            print("  (or set config.reference_video in project_state.json)")
            sys.exit(1)
        print(f"[analyze] using video from state: {video}")

    run(video, s)
