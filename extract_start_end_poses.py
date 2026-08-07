"""
extract_start_end_poses.py — extract START / MIDDLE / END frame poses for every
shot in the beach reference video, for driving per-shot first/last keyframes.

LOCAL ONLY. No paid API.
  - Does NOT call OpenAI.
  - Does NOT call Kling.
  - Does NOT generate keyframes.
  - Does NOT modify project_state.json.

Uses the existing beach reference video and the existing shot cuts from
project_state.json (reference_data.shot_cuts), and the SAME MediaPipe pose model
and 33-point layout as stage1_analyze.py.

Per shot:
  1. Extract start frame
  2. Extract middle frame
  3. Extract end frame
  4. Run MediaPipe pose extraction on each
  5. Save raw frames
  6. Save pose overlays
  7. Record metadata (frame index, timestamp, pose confidence, keypoints count)

Output → outputs/runs/live_test_03_4shots/analysis/start_mid_end/
    shot_001_start.png       shot_001_start_pose.png
    shot_001_mid.png         shot_001_mid_pose.png
    shot_001_end.png         shot_001_end_pose.png
    ...
    start_mid_end_pose_contact_sheet.png
    start_mid_end_pose_metadata.json

Run
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 extract_start_end_poses.py
"""

import json, sys
from pathlib import Path

import numpy as np
import cv2

ROOT  = Path(__file__).parent
STATE = ROOT / "project_state.json"
OUT_DIR = ROOT / "outputs" / "runs" / "live_test_03_4shots" / "analysis" / "start_mid_end"

# ── MediaPipe (same model + layout as stage1_analyze.py) ─────────────────────
_MP_MODEL = ROOT / "pipeline" / "models" / "pose_landmarker_full.task"
_landmarker_options = None
try:
    import mediapipe as mp
    from mediapipe.tasks import python as _mp_python
    from mediapipe.tasks.python import vision as _mp_vision
    if not _MP_MODEL.exists():
        print(f"ERROR: pose model not found at {_MP_MODEL}")
        sys.exit(1)
    _base_opts = _mp_python.BaseOptions(model_asset_path=str(_MP_MODEL))
    _landmarker_options = _mp_vision.PoseLandmarkerOptions(
        base_options=_base_opts,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
    )
    print("[pose] MediaPipe Tasks API ready")
except Exception as e:
    print(f"ERROR: mediapipe unavailable ({e}). Cannot extract poses.")
    sys.exit(1)

# 33-point layout — identical order to stage1_analyze.py
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

CONNECTIONS = [
    ("LEFT_SHOULDER","RIGHT_SHOULDER"),
    ("LEFT_SHOULDER","LEFT_HIP"), ("RIGHT_SHOULDER","RIGHT_HIP"),
    ("LEFT_HIP","RIGHT_HIP"),
    ("LEFT_SHOULDER","LEFT_ELBOW"), ("LEFT_ELBOW","LEFT_WRIST"),
    ("RIGHT_SHOULDER","RIGHT_ELBOW"), ("RIGHT_ELBOW","RIGHT_WRIST"),
    ("LEFT_HIP","LEFT_KNEE"), ("LEFT_KNEE","LEFT_ANKLE"),
    ("RIGHT_HIP","RIGHT_KNEE"), ("RIGHT_KNEE","RIGHT_ANKLE"),
    ("LEFT_ANKLE","LEFT_FOOT_INDEX"), ("RIGHT_ANKLE","RIGHT_FOOT_INDEX"),
    ("NOSE","LEFT_EYE"), ("LEFT_EYE","LEFT_EAR"),
    ("NOSE","RIGHT_EYE"), ("RIGHT_EYE","RIGHT_EAR"),
]

VIS_THRESH = 0.3

def extract_keypoints(frame_bgr):
    """Return (kpts_dict_or_None, pose_confidence, keypoints_count)."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    with _mp_vision.PoseLandmarker.create_from_options(_landmarker_options) as lm:
        result = lm.detect(mp_image)
    if not result.pose_landmarks:
        return None, 0.0, 0
    kpts = {}
    vis_vals = []
    for name, l in zip(NAMES, result.pose_landmarks[0]):
        kpts[name] = {"x": l.x, "y": l.y, "z": l.z, "visibility": l.visibility}
        vis_vals.append(l.visibility)
    # pose_confidence = mean landmark visibility (proxy; MediaPipe Tasks has no scalar score)
    confidence = round(float(np.mean(vis_vals)), 4) if vis_vals else 0.0
    count = sum(1 for v in vis_vals if v > VIS_THRESH)
    return kpts, confidence, count

def draw_overlay(frame_bgr, kpts, label):
    img = frame_bgr.copy()
    h, w = img.shape[:2]
    if kpts:
        for a, b in CONNECTIONS:
            ka, kb = kpts.get(a), kpts.get(b)
            if ka and kb and ka["visibility"] > VIS_THRESH and kb["visibility"] > VIS_THRESH:
                pa = (int(ka["x"] * w), int(ka["y"] * h))
                pb = (int(kb["x"] * w), int(kb["y"] * h))
                cv2.line(img, pa, pb, (0, 220, 255), 3)
        for kpt in kpts.values():
            if kpt["visibility"] > VIS_THRESH:
                cv2.circle(img, (int(kpt["x"] * w), int(kpt["y"] * h)), 5, (0, 255, 0), -1)
    else:
        cv2.putText(img, "NO POSE DETECTED", (30, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.rectangle(img, (0, 0), (w, 46), (18, 18, 18), -1)
    cv2.putText(img, label, (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (230, 230, 230), 2)
    return img

def read_frame(cap, frame_idx, total):
    idx = max(0, min(int(frame_idx), total - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ret, frame = cap.read()
    return (frame, idx) if ret else (None, idx)

# ── Load state + locate reference video ──────────────────────────────────────
state = json.loads(STATE.read_text())
shot_cuts = state["reference_data"]["shot_cuts"]

stored = state.get("reference_video", "")
video_path = ROOT / "test" / Path(stored).name if stored else None
if not video_path or not video_path.exists():
    cands = list((ROOT / "test").glob("*.mp4")) if (ROOT / "test").exists() else []
    if not cands:
        print(f"ERROR: reference video not found. Looked for {video_path}")
        sys.exit(1)
    video_path = cands[0]
print(f"[video] {video_path}")

cap   = cv2.VideoCapture(str(video_path))
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps   = cap.get(cv2.CAP_PROP_FPS) or 24.0
print(f"[video] total_frames={total}  fps={fps:.2f}")

OUT_DIR.mkdir(parents=True, exist_ok=True)

meta_shots = []
overlays   = []   # (shot_id, [start_ov, mid_ov, end_ov])

for s in shot_cuts:
    sid = s["shot_id"]
    sf  = int(s["start_frame"])
    ef  = int(s["end_frame"])
    mf  = (sf + ef) // 2
    # end_frame is the cut boundary (next shot's first frame) → step back one
    positions = {"start": sf, "mid": mf, "end": max(ef - 1, sf)}

    shot_meta = {"shot_id": sid, "start_frame": sf, "end_frame": ef, "frames": {}}
    ovs = []
    for tag, fidx in positions.items():
        frame, used_idx = read_frame(cap, fidx, total)
        if frame is None:
            print(f"[{sid}] WARNING: could not read {tag} frame {fidx}")
            ovs.append(None)
            continue

        kpts, conf, count = extract_keypoints(frame)

        raw_path = OUT_DIR / f"{sid}_{tag}.png"
        ov_path  = OUT_DIR / f"{sid}_{tag}_pose.png"
        cv2.imwrite(str(raw_path), frame)
        overlay = draw_overlay(frame, kpts, f"{sid}  {tag.upper()}  f{used_idx}  conf={conf:.2f}  pts={count}")
        cv2.imwrite(str(ov_path), overlay)
        ovs.append(overlay)

        shot_meta["frames"][tag] = {
            "frame_index":     used_idx,
            "timestamp_s":     round(used_idx / fps, 4),
            "pose_confidence": conf,
            "keypoints_count": count,
            "raw_image":       str(raw_path),
            "pose_image":      str(ov_path),
            "keypoints":       kpts,
        }
        print(f"[{sid}] {tag:5s} f{used_idx}: conf={conf:.2f}  pts={count}")

    meta_shots.append(shot_meta)
    overlays.append((sid, ovs))

cap.release()

# ── Metadata JSON ─────────────────────────────────────────────────────────────
meta_path = OUT_DIR / "start_mid_end_pose_metadata.json"
meta_path.write_text(json.dumps({
    "reference_video": str(video_path),
    "fps": fps,
    "total_frames": total,
    "note": "Local START/MID/END pose extraction. project_state.json NOT modified. No paid API called.",
    "shots": meta_shots,
}, indent=2))

# ── Contact sheet: rows = shots, cols = [start | mid | end] overlays ──────────
sheet_path = None
valid = [(sid, ovs) for sid, ovs in overlays if any(o is not None for o in ovs)]
if valid:
    from PIL import Image
    PAD = 12
    col_h = 420
    def to_pil(bgr):
        if bgr is None:
            return Image.new("RGB", (int(col_h * 1.6), col_h), (40, 40, 40))
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(rgb)
        w = int(im.width * (col_h / im.height))
        return im.resize((w, col_h))

    rows = [[to_pil(o) for o in ovs] for _, ovs in valid]
    col_w = max(max(im.width for im in row) for row in rows)
    sheet_w = PAD + (col_w + PAD) * 3
    sheet_h = PAD + (col_h + PAD) * len(rows)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 18))
    y = PAD
    for row in rows:
        x = PAD
        for im in row:
            sheet.paste(im, (x, y))
            x += col_w + PAD
        y += col_h + PAD
    sheet_path = OUT_DIR / "start_mid_end_pose_contact_sheet.png"
    sheet.save(sheet_path)

# ── Report ────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("START / MID / END POSE EXTRACTION COMPLETE")
print("=" * 60)
for sm in meta_shots:
    parts = " | ".join(
        f"{tag}:conf{sm['frames'][tag]['pose_confidence']:.2f}/pts{sm['frames'][tag]['keypoints_count']}"
        for tag in ("start", "mid", "end") if tag in sm["frames"]
    )
    print(f"  {sm['shot_id']}: {parts}")
print(f"\n  frames + overlays : {OUT_DIR}")
print(f"  metadata json     : {meta_path}")
if sheet_path:
    print(f"  contact sheet     : {sheet_path}")
print("\n  project_state.json NOT modified. No paid API called.")
print("  Review the skeletons before any generation step.")
print("=" * 60)
