"""
dance_analyzer.py — v0.1  Dance Detection & Key-Pose Segmentation

Called from stage1_analyze.py after shot/beat detection.
Adds to state:
  reference_data.motion_analysis   — category, intensity, suitability
  reference_data.dance_segments    — key-pose segments (replaces shot_cuts for dance)

Design constraints:
  - Uses MediaPipe from stage1_analyze (no separate model load)
  - No DWPose / RTMPose yet — that's v0.2
  - v0.1 goal: detect dance, extract key poses, build dance storyboard JSON
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional


# ─── Constants ────────────────────────────────────────────────────────────────

MOTION_THRESHOLDS = {
    "low":    0.03,   # <3% average keypoint displacement per frame
    "medium": 0.07,   # 3–7%
    "high":   0.12,   # 7–12%
    "dance":  0.12,   # >12% sustained — combined with arm/leg range
}

DANCE_ARM_RANGE_MIN   = 0.25  # wrist y-range > 25% frame height → arms active
DANCE_LEG_RANGE_MIN   = 0.15  # ankle y-range > 15% frame height → legs active
DANCE_PEAK_COUNT_MIN  = 4     # at least 4 motion peaks → rhythmic movement

MAX_BEAT_SNAP_MS      = 150   # ms — max distance to snap a segment cut to a beat
MIN_SEGMENT_S         = 0.4   # minimum segment duration
MAX_SEGMENT_S         = 1.5   # maximum segment duration

SAMPLE_FPS            = 8     # frames per second to sample for motion analysis


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _kpt_xy(keypoints: dict, name: str) -> Optional[tuple]:
    kpt = keypoints.get(name)
    if kpt and kpt.get("visibility", 0) > 0.3:
        return (kpt["x"], kpt["y"])
    return None


def _pose_displacement(kpts_a: Optional[dict], kpts_b: Optional[dict]) -> float:
    """
    Mean Euclidean displacement of shared visible keypoints between two frames.
    Returns normalised value in [0, 1] (fraction of frame).
    """
    if not kpts_a or not kpts_b:
        return 0.0
    shared = set(kpts_a) & set(kpts_b)
    dists = []
    for name in shared:
        a, b = _kpt_xy(kpts_a, name), _kpt_xy(kpts_b, name)
        if a and b:
            dists.append(np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2))
    return float(np.mean(dists)) if dists else 0.0


def _motion_blur_score(frame_bgr) -> float:
    """Laplacian variance — higher = sharper. Dance frames are often blurry."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _full_body_check(keypoints: Optional[dict]) -> dict:
    """
    Check how much of the body is visible.
    Returns {full_body_visible, hands_visible, feet_visible, visibility_score}.
    """
    if not keypoints:
        return {
            "full_body_visible": False,
            "hands_visible": False,
            "feet_visible": False,
            "visibility_score": 0.0,
        }

    def vis(name):
        return keypoints.get(name, {}).get("visibility", 0.0)

    shoulder_ok  = vis("LEFT_SHOULDER") > 0.5 and vis("RIGHT_SHOULDER") > 0.5
    hip_ok       = vis("LEFT_HIP")      > 0.5 and vis("RIGHT_HIP")      > 0.5
    knee_ok      = vis("LEFT_KNEE")     > 0.4 and vis("RIGHT_KNEE")     > 0.4
    ankle_ok     = vis("LEFT_ANKLE")    > 0.3 and vis("RIGHT_ANKLE")    > 0.3
    wrist_ok     = vis("LEFT_WRIST")    > 0.3 or  vis("RIGHT_WRIST")    > 0.3
    foot_ok      = ankle_ok

    full_body = shoulder_ok and hip_ok and knee_ok
    vis_landmarks = [v["visibility"] for v in keypoints.values() if "visibility" in v]
    vis_score = float(np.mean(vis_landmarks)) if vis_landmarks else 0.0

    return {
        "full_body_visible": full_body,
        "hands_visible": wrist_ok,
        "feet_visible": foot_ok,
        "visibility_score": round(vis_score, 3),
    }


# ─── Motion Sampling ──────────────────────────────────────────────────────────

def _sample_video_poses(video_path: str, extract_fn, sample_fps: int = SAMPLE_FPS) -> list:
    """
    Sample frames at `sample_fps` and extract pose keypoints.
    Returns list of {time_s, frame_bgr, keypoints, blur_score}.
    Skips frames where no person is detected.
    """
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(video_fps / sample_fps))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    samples = []
    frame_idx = 0
    while frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
        kpts = extract_fn(frame)
        t = frame_idx / video_fps
        samples.append({
            "time_s":     round(t, 3),
            "frame_bgr":  frame,
            "keypoints":  kpts,
            "blur_score": _motion_blur_score(frame),
        })
        frame_idx += step
    cap.release()
    print(f"[dance] sampled {len(samples)} frames at ~{sample_fps}fps")
    return samples


# ─── Motion Category Detection ────────────────────────────────────────────────

def detect_motion_category(video_path: str, extract_fn) -> dict:
    """
    Analyse overall motion intensity and categorise as low / medium / high / dance.

    Parameters
    ----------
    video_path : path to video
    extract_fn : function (frame_bgr) -> keypoints dict | None
                 (re-uses MediaPipe from stage1_analyze)

    Returns
    -------
    {
        "category":        "dance" | "high" | "medium" | "low",
        "mean_displacement": float,
        "arm_range":         float,
        "leg_range":         float,
        "peak_count":        int,
        "confidence":        float,
        "suitability":       {...},
    }
    """
    samples = _sample_video_poses(video_path, extract_fn)
    if len(samples) < 2:
        return {"category": "low", "mean_displacement": 0.0,
                "arm_range": 0.0, "leg_range": 0.0,
                "peak_count": 0, "confidence": 0.0,
                "suitability": {"full_body_visible": False,
                                "single_person": False,
                                "suitable_for_pose_transfer": False}}

    # ── Displacement series ──────────────────────────────────────────────────
    displacements = []
    for i in range(1, len(samples)):
        d = _pose_displacement(samples[i-1]["keypoints"], samples[i]["keypoints"])
        displacements.append(d)

    mean_disp  = float(np.mean(displacements)) if displacements else 0.0
    disp_array = np.array(displacements)

    # ── Arm range (wrist y) ──────────────────────────────────────────────────
    wrist_ys = []
    for s in samples:
        kpts = s["keypoints"]
        if kpts:
            for name in ("LEFT_WRIST", "RIGHT_WRIST"):
                pt = _kpt_xy(kpts, name)
                if pt:
                    wrist_ys.append(pt[1])
    arm_range = (max(wrist_ys) - min(wrist_ys)) if len(wrist_ys) > 1 else 0.0

    # ── Leg range (ankle y) ──────────────────────────────────────────────────
    ankle_ys = []
    for s in samples:
        kpts = s["keypoints"]
        if kpts:
            for name in ("LEFT_ANKLE", "RIGHT_ANKLE"):
                pt = _kpt_xy(kpts, name)
                if pt:
                    ankle_ys.append(pt[1])
    leg_range = (max(ankle_ys) - min(ankle_ys)) if len(ankle_ys) > 1 else 0.0

    # ── Motion peaks (rhythmic indicator) ────────────────────────────────────
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(disp_array, height=mean_disp * 0.8, distance=2)
    peak_count = int(len(peaks))

    # ── Suitability ──────────────────────────────────────────────────────────
    # Check mid-video frame for full-body visibility
    mid_idx    = len(samples) // 2
    mid_kpts   = samples[mid_idx]["keypoints"]
    suitability_raw = _full_body_check(mid_kpts)

    # Person count heuristic: if poses detected in > 60% of sampled frames → single person likely
    detected_count = sum(1 for s in samples if s["keypoints"] is not None)
    single_person  = detected_count / len(samples) > 0.6

    # Camera stability: low displacement variance → stable camera
    disp_std = float(np.std(displacements)) if displacements else 0.0
    cam_stability = "stable" if disp_std < 0.04 else "medium" if disp_std < 0.09 else "unstable"

    suitability = {
        **suitability_raw,
        "single_person":              single_person,
        "camera_stability":           cam_stability,
        "occlusion":                  "low" if suitability_raw["visibility_score"] > 0.65 else "medium",
        "motion_blur":                "low" if samples[mid_idx]["blur_score"] > 200 else "medium",
        "suitable_for_pose_transfer": (
            suitability_raw["full_body_visible"]
            and single_person
            and cam_stability in ("stable", "medium")
        ),
    }

    # ── Category decision ────────────────────────────────────────────────────
    is_dance = (
        mean_disp > MOTION_THRESHOLDS["dance"]
        and arm_range > DANCE_ARM_RANGE_MIN
        and peak_count >= DANCE_PEAK_COUNT_MIN
    )
    if is_dance:
        category   = "dance"
        confidence = min(1.0, (mean_disp / 0.20 + arm_range / 0.50 + peak_count / 12) / 3)
    elif mean_disp > MOTION_THRESHOLDS["high"]:
        category, confidence = "high", 0.7
    elif mean_disp > MOTION_THRESHOLDS["medium"]:
        category, confidence = "medium", 0.7
    else:
        category, confidence = "low", 0.8

    result = {
        "category":          category,
        "mean_displacement": round(mean_disp, 4),
        "arm_range":         round(float(arm_range), 4),
        "leg_range":         round(float(leg_range), 4),
        "peak_count":        peak_count,
        "confidence":        round(float(confidence), 3),
        "suitability":       suitability,
        "_samples":          samples,  # internal — stripped before saving to state
    }
    print(f"[dance] motion category={category}  mean_disp={mean_disp:.3f}  "
          f"arm_range={arm_range:.2f}  peaks={peak_count}  confidence={confidence:.2f}")
    return result


# ─── Key Pose Extraction ──────────────────────────────────────────────────────

def _snap_to_beat(time_s: float, beats: list, max_snap_s: float = MAX_BEAT_SNAP_MS / 1000) -> float:
    """
    Snap a time to the nearest beat if within max_snap_s.
    If no beat is close enough, return the original time.
    """
    if not beats:
        return time_s
    beat_times = [b["time_s"] for b in beats]
    dists      = [abs(t - time_s) for t in beat_times]
    min_dist   = min(dists)
    if min_dist <= max_snap_s:
        return beat_times[dists.index(min_dist)]
    return time_s


def extract_key_poses(
    video_path: str,
    samples: list,
    beats: list,
    output_dir: Path,
) -> list:
    """
    Extract key pose segments from pre-sampled frames.
    Finds motion peaks and selects the sharpest frame near each peak.

    Returns list of {
        "shot_id", "start", "end", "beat_target",
        "source_panel", "pose_ref",
        "framing", "full_body_check",
        "dominant_motion", "motion_intensity",
        "motion_prompt",
    }
    """
    from scipy.signal import find_peaks

    if len(samples) < 3:
        return []

    times       = np.array([s["time_s"]    for s in samples])
    blur_scores = np.array([s["blur_score"] for s in samples])

    # Displacement series
    disps = np.array([
        _pose_displacement(samples[i-1]["keypoints"], samples[i]["keypoints"])
        for i in range(1, len(samples))
    ] + [0.0])  # pad last

    mean_disp = float(np.mean(disps))

    # Find motion peaks — these become segment boundaries
    peaks, _ = find_peaks(disps, height=mean_disp * 0.75, distance=max(1, int(SAMPLE_FPS * MIN_SEGMENT_S)))
    if len(peaks) == 0:
        # Fallback: fixed-interval segmentation
        seg_dur   = 1.0
        peak_times = np.arange(times[0], times[-1], seg_dur)
    else:
        peak_times = times[peaks]

    # Build segments between peaks (peaks = moment of max motion → use as key-pose frame)
    duration = float(times[-1]) if len(times) else 0.0
    seg_times = [float(times[0])] + [float(t) for t in peak_times] + [duration]
    seg_times = sorted(set(seg_times))

    # Enforce min/max segment length
    merged = [seg_times[0]]
    for t in seg_times[1:]:
        if t - merged[-1] >= MIN_SEGMENT_S:
            merged.append(t)
    if merged[-1] < duration - 0.1:
        merged.append(duration)
    seg_times = merged

    keypose_dir = output_dir / "dance_keyposes"
    keypose_dir.mkdir(parents=True, exist_ok=True)
    pose_json_dir = output_dir / "dance_poses"
    pose_json_dir.mkdir(parents=True, exist_ok=True)

    segments = []
    for i in range(len(seg_times) - 1):
        start_s = seg_times[i]
        end_s   = min(seg_times[i+1], duration)
        if end_s - start_s < MIN_SEGMENT_S:
            continue
        if end_s - start_s > MAX_SEGMENT_S:
            end_s = start_s + MAX_SEGMENT_S

        # Snap start to nearest beat
        beat_target = _snap_to_beat(start_s, beats)

        # Find sharpest (lowest blur) frame in this segment
        mask = (times >= start_s) & (times < end_s)
        if not np.any(mask):
            continue
        seg_samples   = [s for s, m in zip(samples, mask) if m]
        seg_blurs     = np.array([s["blur_score"] for s in seg_samples])
        best_idx      = int(np.argmax(seg_blurs))
        best_sample   = seg_samples[best_idx]
        best_frame    = best_sample["frame_bgr"]
        best_kpts     = best_sample["keypoints"]

        # Save key-pose frame
        seg_id         = f"dance_seg_{i+1:03d}"
        panel_filename = f"{seg_id}_pose.png"
        panel_path     = keypose_dir / panel_filename
        cv2.imwrite(str(panel_path), best_frame)

        # Save pose JSON
        pose_json_path = pose_json_dir / f"{seg_id}_pose.json"
        import json
        with open(str(pose_json_path), "w") as f:
            json.dump(best_kpts or {}, f, indent=2)

        # Full-body check on best frame
        fb_check = _full_body_check(best_kpts)

        # Dominant motion (which body parts moved most in this segment)
        dominant = _dominant_motion(seg_samples)

        # Framing
        from stage1_analyze import classify_framing
        framing = classify_framing(best_kpts)

        # Auto motion prompt
        motion_prompt = _build_motion_prompt(dominant, framing, fb_check)

        segments.append({
            "shot_id":       seg_id,
            "start":         round(start_s, 3),
            "end":           round(end_s, 3),
            "duration":      round(end_s - start_s, 3),
            "beat_target":   round(beat_target, 3),
            "source_panel":  str(panel_path),
            "pose_ref":      str(pose_json_path),
            "framing":       framing,
            "full_body_check": fb_check,
            "dominant_motion": dominant,
            "motion_intensity": "high" if disps[mask].mean() > MOTION_THRESHOLDS["high"] else "medium",
            "motion_prompt": motion_prompt,
            "human_motion": {
                "category":         "dance_key_pose",
                "motion_intensity": "high" if disps[mask].mean() > MOTION_THRESHOLDS["high"] else "medium",
                "dominant_motion":  dominant,
                "body_direction":   _body_direction(best_kpts),
            },
            "priority": ["pose", "body_integrity", "identity", "framing"],
            "evaluation": {"status": "pending", "attempts": []},
        })

        print(f"  {seg_id}  {start_s:.2f}s → {end_s:.2f}s  "
              f"beat={beat_target:.2f}  framing={framing}  dominant={dominant}")

    print(f"[dance] extracted {len(segments)} key-pose segments")
    return segments


def _dominant_motion(seg_samples: list) -> list:
    """Return which body parts had the most movement in a segment."""
    PART_GROUPS = {
        "arms":  ["LEFT_WRIST", "RIGHT_WRIST", "LEFT_ELBOW", "RIGHT_ELBOW"],
        "hips":  ["LEFT_HIP", "RIGHT_HIP"],
        "legs":  ["LEFT_ANKLE", "RIGHT_ANKLE", "LEFT_KNEE", "RIGHT_KNEE"],
        "torso": ["LEFT_SHOULDER", "RIGHT_SHOULDER"],
    }
    part_scores = {}
    for part, names in PART_GROUPS.items():
        total = 0.0
        count = 0
        for i in range(1, len(seg_samples)):
            ka, kb = seg_samples[i-1]["keypoints"], seg_samples[i]["keypoints"]
            if not ka or not kb:
                continue
            for n in names:
                a, b = _kpt_xy(ka, n), _kpt_xy(kb, n)
                if a and b:
                    total += np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
                    count += 1
        part_scores[part] = total / count if count else 0.0

    if not part_scores:
        return []
    max_score = max(part_scores.values())
    if max_score < 0.01:
        return []
    threshold  = max_score * 0.4
    return [p for p, s in sorted(part_scores.items(), key=lambda x: -x[1]) if s >= threshold]


def _body_direction(keypoints: Optional[dict]) -> str:
    if not keypoints:
        return "unknown"
    nose = keypoints.get("NOSE", {}).get("visibility", 0)
    if nose > 0.7:
        return "front"
    elif nose > 0.4:
        return "three_quarter"
    else:
        return "back"


def _build_motion_prompt(dominant: list, framing: str, fb_check: dict) -> str:
    body_str  = ", ".join(dominant) if dominant else "full body"
    full_body = "full body visible" if fb_check.get("full_body_visible") else "upper body"
    return (
        f"short controlled dance movement focusing on {body_str}, "
        f"{full_body}, stable camera, preserve pose direction and character identity, "
        f"{framing} framing"
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def run_dance_analysis(video_path: str, extract_fn, beats: list, output_dir: Path) -> dict:
    """
    Full dance analysis pass.
    Returns {motion_analysis, dance_segments} to merge into state["reference_data"].

    motion_analysis.category == 'dance' triggers dance storyboard mode in the dashboard.
    """
    print("[dance] running motion category detection...")
    motion = detect_motion_category(video_path, extract_fn)

    # Strip internal _samples from the saved result
    samples = motion.pop("_samples", [])

    result = {"motion_analysis": motion}

    if motion["category"] in ("dance", "high"):
        print(f"[dance] {motion['category']} motion detected — extracting key poses...")
        segments = extract_key_poses(video_path, samples, beats, output_dir)
        result["dance_segments"] = segments
        result["recommended_strategy"] = "key_pose_segmentation" if motion["category"] == "dance" else "shot_based"
    else:
        result["dance_segments"]       = []
        result["recommended_strategy"] = "shot_based"

    return result
