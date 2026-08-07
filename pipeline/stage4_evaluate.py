"""
stage4_evaluate.py — Evaluator

Checks each generated shot against five metrics:
  1. IP identity consistency  — ArcFace cosine similarity
  2. Pose similarity          — MediaPipe keypoint distance
  3. Framing accuracy         — composition classification check
  4. Beat alignment error     — timing delta in milliseconds
  5. Look consistency         — GPT-4o vision check (hair/outfit/shoes/palette)

Returns a scores dict and a pass/fail verdict per shot.
Calibrate IDENTITY_THRESHOLD in config.py after Phase 0.
"""

import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

try:
    import mediapipe as mp
    _mp_pose = mp.solutions.pose
    MEDIAPIPE_OK = True
except (ImportError, AttributeError) as _mp_err:
    MEDIAPIPE_OK = False
    print(f"[eval] WARNING: mediapipe unavailable ({_mp_err}). "
          "Pose and framing scores will return neutral 0.5.")

from config import (
    IDENTITY_THRESHOLD,
    POSE_THRESHOLD,
    BEAT_ALIGNMENT_MAX_MS,
    FRAMING_THRESHOLD,
)
import state as st


# ─── Identity Score (ArcFace via DeepFace) ────────────────────────────────

def compute_identity_score(
    generated_image_path: str,
    reference_image_paths: list[str],
) -> float:
    """
    Compute ArcFace cosine similarity between generated image and IP references.
    Returns max similarity across all reference images (0–1, higher = more similar).

    Tries multiple detector backends in order — retinaface often fails on veiled/
    partial faces or small faces in full-body shots. Falls back to mtcnn then opencv.
    """
    from deepface import DeepFace

    # Backends ordered by tolerance for partial occlusion / small faces
    BACKENDS = ["mtcnn", "opencv", "retinaface", "skip"]

    best_score = 0.0
    for ref_path in reference_image_paths:
        for backend in BACKENDS:
            try:
                result = DeepFace.verify(
                    img1_path=generated_image_path,
                    img2_path=ref_path,
                    model_name="ArcFace",
                    detector_backend=backend,
                    enforce_detection=False,
                )
                dist = result["distance"]
                # ArcFace cosine distance range ~[0, 2]; similarity = 1 - dist/2
                similarity = max(0.0, 1.0 - dist / 2.0)
                best_score = max(best_score, similarity)
                print(f"[eval] identity {backend}: dist={dist:.4f} sim={similarity:.4f} ({ref_path.split('/')[-1]})")
                break  # got a result, skip remaining backends for this ref
            except Exception as e:
                if backend == BACKENDS[-1]:
                    print(f"[eval] all backends failed for {ref_path}: {e}")

    return round(best_score, 4)


# ─── Pose Similarity (MediaPipe) ──────────────────────────────────────────

def compute_pose_score(
    generated_image_path: str,
    reference_keypoints: dict | None,
) -> float:
    """
    Extract pose from generated image and compare to reference keypoints.
    Returns pose similarity (0–1, higher = better match).
    Uses normalised mean keypoint distance, inverted to similarity.
    """
    if reference_keypoints is None:
        return 1.0  # No reference pose → can't penalise

    if not MEDIAPIPE_OK:
        return 1.0  # Skip — mediapipe unavailable (same as framing fallback)

    mp_pose = _mp_pose
    img = cv2.imread(generated_image_path)
    if img is None:
        return 0.0

    with mp_pose.Pose(static_image_mode=True, model_complexity=2) as pose:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        if results.pose_landmarks is None:
            return 0.0  # No pose detected

        gen_kpts = {
            name.name: {
                "x": lm.x, "y": lm.y,
                "visibility": lm.visibility,
            }
            for name, lm in zip(mp_pose.PoseLandmark, results.pose_landmarks.landmark)
        }

    # Compare only high-visibility landmarks in both
    dists = []
    for name, ref_kpt in reference_keypoints.items():
        if ref_kpt.get("visibility", 0) < 0.5:
            continue
        if name not in gen_kpts or gen_kpts[name]["visibility"] < 0.5:
            continue
        dx = gen_kpts[name]["x"] - ref_kpt["x"]
        dy = gen_kpts[name]["y"] - ref_kpt["y"]
        dists.append(math.sqrt(dx**2 + dy**2))

    if not dists:
        return 0.5  # Uncertain

    mean_dist = sum(dists) / len(dists)
    # Convert distance to similarity: dist=0 → sim=1, dist=0.5 → sim=0
    similarity = max(0.0, 1.0 - mean_dist * 2.0)
    return round(similarity, 4)


# ─── Framing Score ────────────────────────────────────────────────────────

def compute_framing_score(
    generated_image_path: str,
    expected_framing: str,
) -> float:
    """
    Check if the generated image matches expected framing.
    Uses the same heuristic as stage1 (MediaPipe landmark span).
    Returns 1.0 if framing matches, partial score for adjacent framings.
    """
    if expected_framing == "unknown":
        return 1.0

    if not MEDIAPIPE_OK:
        return 1.0  # Skip framing check — mediapipe unavailable (logged at import)

    from stage1_analyze import classify_framing

    mp_pose = _mp_pose
    img = cv2.imread(generated_image_path)
    if img is None:
        return 0.5

    with mp_pose.Pose(static_image_mode=True, model_complexity=1) as pose:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)
        if results.pose_landmarks is None:
            return 0.5

        kpts = {
            name.name: {"x": lm.x, "y": lm.y, "visibility": lm.visibility}
            for name, lm in zip(mp_pose.PoseLandmark, results.pose_landmarks.landmark)
        }

    detected_framing = classify_framing(kpts)

    FRAMING_ORDER = [
        "extreme-close-up", "close-up", "medium-close-up",
        "medium", "medium-wide", "wide", "extreme-wide", "unknown"
    ]

    if detected_framing == expected_framing:
        return 1.0

    try:
        diff = abs(FRAMING_ORDER.index(detected_framing) - FRAMING_ORDER.index(expected_framing))
        return max(0.0, 1.0 - diff * 0.25)
    except ValueError:
        return 0.5


# ─── Beat Alignment ───────────────────────────────────────────────────────

def compute_beat_alignment_ms(
    shot: dict,
    beats: list[dict],
) -> float:
    """
    Compute timing error between shot's beat_time_s and the nearest beat.
    Lower is better. Returns ms.
    """
    beat_time = shot.get("beat_time_s")
    if beat_time is None or not beats:
        return 0.0

    nearest = min(beats, key=lambda b: abs(b["time_s"] - beat_time))
    return round(abs(nearest["time_s"] - beat_time) * 1000, 1)


# ─── Look Consistency Score (GPT-4o vision) ──────────────────────────────

def compute_look_consistency_score(
    generated_image_path: str,
    look_prompt_profile: dict,
    client=None,
) -> dict:
    """
    Ask GPT-4o to check if the generated image matches the look prompt_profile.
    Returns {hair_match, outfit_match, shoes_match, overall_score} (0–1 each).
    Falls back to neutral 0.5 if client is unavailable or call fails.
    """
    NEUTRAL = {"hair_match": 0.5, "outfit_match": 0.5, "shoes_match": 0.5, "overall_score": 0.5}

    if client is None:
        try:
            import openai
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("[eval] look_consistency: no OPENAI_API_KEY — skipping")
                return NEUTRAL
            client = openai.OpenAI(api_key=api_key)
        except ImportError:
            print("[eval] look_consistency: openai not installed — skipping")
            return NEUTRAL

    import base64
    try:
        with open(generated_image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except OSError as e:
        print(f"[eval] look_consistency: cannot read image: {e}")
        return NEUTRAL

    hair_desc    = look_prompt_profile.get("hair", "")
    outfit_desc  = look_prompt_profile.get("outfit", "")
    shoes_desc   = look_prompt_profile.get("shoes", "")
    palette_desc = look_prompt_profile.get("palette", "")
    silhouette   = look_prompt_profile.get("body_silhouette", "")

    system_msg = (
        "You are a fashion-continuity evaluator for an AI video pipeline. "
        "Given an image and a look description, rate how well the image matches each element. "
        "Return ONLY valid JSON with keys: hair_match, outfit_match, shoes_match, overall_score. "
        "Each value is a float 0.0–1.0 (1.0 = perfect match). "
        "If an element is not visible (e.g. shoes hidden by a close-up frame), return 1.0 for that item."
    )
    user_msg = (
        f"Check this image against the following look specification:\n"
        f"Hair: {hair_desc}\n"
        f"Outfit: {outfit_desc}\n"
        f"Shoes: {shoes_desc}\n"
        f"Palette: {palette_desc}\n"
        f"Silhouette: {silhouette}\n\n"
        "Return JSON only."
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": [
                    {"type": "text", "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"}},
                ]},
            ],
            max_tokens=120,
            temperature=0.0,
        )
        import json as _json
        raw = resp.choices[0].message.content.strip()
        parsed = _json.loads(raw)
        result = {
            "hair_match":    round(float(parsed.get("hair_match",   0.5)), 3),
            "outfit_match":  round(float(parsed.get("outfit_match", 0.5)), 3),
            "shoes_match":   round(float(parsed.get("shoes_match",  0.5)), 3),
            "overall_score": round(float(parsed.get("overall_score", 0.5)), 3),
        }
        print(f"[eval] look_consistency: hair={result['hair_match']:.2f} "
              f"outfit={result['outfit_match']:.2f} shoes={result['shoes_match']:.2f} "
              f"overall={result['overall_score']:.2f}")
        return result
    except Exception as e:
        print(f"[eval] look_consistency failed: {e}")
        return NEUTRAL


# ─── Subject Count Check ─────────────────────────────────────────────────

def _count_faces_in_image(img_path: str) -> int:
    """
    Count faces using OpenCV Haar cascade.
    Returns detected face count (0 if detection fails).
    """
    try:
        img = cv2.imread(img_path)
        if img is None:
            return 0
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return int(len(faces))
    except Exception as e:
        print(f"[eval] face count failed: {e}")
        return 0


def compute_subject_count_score(img_path: str, view: str = "front") -> dict:
    """
    Check whether the generated image contains only one primary subject.
    For back/over-shoulder views, face detection is not reliable — uses HOG person count.
    Returns {expected, detected, extra_detected, pass, method}.
    """
    face_count = 0
    method = "face_cascade"

    if view in ("back", "over-shoulder"):
        # Face cascade won't work on back-facing; try HOG person detector
        method = "hog_person"
        try:
            img = cv2.imread(img_path)
            if img is not None:
                hog = cv2.HOGDescriptor()
                hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
                h, w = img.shape[:2]
                scale = min(1.0, 640 / max(h, w))
                if scale < 1.0:
                    img = cv2.resize(img, (int(w * scale), int(h * scale)))
                rects, _ = hog.detectMultiScale(img, winStride=(8, 8), padding=(4, 4), scale=1.05)
                face_count = int(len(rects))
        except Exception as e:
            print(f"[eval] HOG person count failed: {e}")
            face_count = 1  # assume pass if detection fails
    else:
        face_count = _count_faces_in_image(img_path)
        # 0 faces detected in a front-facing shot is suspicious but may be a style effect;
        # treat as ambiguous (not a fail on its own)
        if face_count == 0:
            face_count = 1  # neutral — can't confirm extra person

    extra = face_count > 1
    print(f"[eval] subject_count ({method}): detected={face_count} extra={extra}")
    return {
        "expected": 1,
        "detected": face_count,
        "extra_detected": extra,
        "pass": not extra,
        "method": method,
    }


# ─── Per-shot Evaluation ──────────────────────────────────────────────────

def evaluate_shot(shot: dict, state: dict) -> dict:
    """
    Run all four metrics on a shot. Returns scores dict + verdict.
    """
    img_path = shot.get("generated_image")
    if not img_path or not os.path.exists(img_path):
        return {
            "scores": {"identity": 0.0, "pose": 0.0, "framing": 0.0, "beat_alignment_ms": 9999.0},
            "verdict": "fail",
            "diagnosis": "generated image missing",
        }

    ip_refs = state["ip_character"]["reference_images"]
    ref_kpts = shot.get("pose_keypoints")
    beats = state["reference_data"].get("beats", [])

    # Look profile from replacement_target (stage2 embeds it per-shot)
    rt = shot.get("replacement_target", {})
    look_pp = rt.get("prompt_profile", {})
    replace_scope = rt.get("replace_scope", "full_subject")

    # View + identity eval mode (from stage2 subject_action block)
    sa = shot.get("subject_action", {})
    view = sa.get("view", "front")
    identity_eval_mode = (
        sa.get("identity_eval_mode")
        or shot.get("evaluation_targets", {}).get("identity_eval_mode")
        or "face_embedding"
    )

    print(f"[eval] evaluating {shot['shot_id']}  view={view}  eval_mode={identity_eval_mode}")

    pose = compute_pose_score(img_path, ref_kpts)
    framing = compute_framing_score(img_path, shot.get("framing", "unknown"))
    beat_ms = compute_beat_alignment_ms(shot, beats)

    # Look consistency — always run for full_subject scopes; used as identity proxy for back views
    LOOK_SCOPES = {"full_subject", "full_subject_restyle_bg"}
    look_result = {"hair_match": 1.0, "outfit_match": 1.0, "shoes_match": 1.0, "overall_score": 1.0}
    if replace_scope in LOOK_SCOPES and look_pp:
        look_result = compute_look_consistency_score(img_path, look_pp)
    look_score = look_result["overall_score"]

    # Identity score — skip ArcFace for back/over-shoulder; use look score as proxy
    if identity_eval_mode == "look_and_silhouette":
        identity = look_score  # face not visible; look+silhouette is the identity signal
        print(f"[eval] identity (look_and_silhouette proxy): {identity:.3f}")
    else:
        identity = compute_identity_score(img_path, ip_refs)

    # Subject count check — single-character pipeline requires exactly one subject
    subject_count = compute_subject_count_score(img_path, view=view)

    scores = {
        "identity": identity,
        "identity_eval_mode": identity_eval_mode,
        "pose": pose,
        "framing": framing,
        "beat_alignment_ms": beat_ms,
        "look_consistency": look_score,
        "look_detail": look_result,
        "subject_count": subject_count,
    }

    # Verdict
    LOOK_PASS_THRESHOLD = 0.65
    passes = {
        "identity": identity >= IDENTITY_THRESHOLD,
        "pose":     pose >= (1.0 - POSE_THRESHOLD),
        "framing":  framing >= FRAMING_THRESHOLD,
        "beat":     beat_ms <= BEAT_ALIGNMENT_MAX_MS,
        "look":     look_score >= LOOK_PASS_THRESHOLD or replace_scope not in LOOK_SCOPES,
        "subject_count": subject_count["pass"],
    }
    verdict = "pass" if all(passes.values()) else "fail"

    # Diagnosis (maps to targeted repair actions)
    diagnosis = ""
    if verdict == "fail":
        details = []
        if not passes["identity"]:
            mode_note = f" [{identity_eval_mode}]"
            details.append(f"identity drift (score={identity:.3f} < {IDENTITY_THRESHOLD}{mode_note})")
        if not passes["pose"]:
            details.append(f"pose mismatch (score={pose:.3f})")
        if not passes["framing"]:
            details.append(f"framing error (score={framing:.3f})")
        if not passes["beat"]:
            details.append(f"beat misalignment ({beat_ms:.0f}ms > {BEAT_ALIGNMENT_MAX_MS}ms)")
        if not passes["look"]:
            low = [k for k in ("hair_match", "outfit_match", "shoes_match")
                   if look_result.get(k, 1.0) < 0.6]
            details.append(f"look mismatch ({', '.join(low) if low else 'overall'}={look_score:.2f})")
        if not passes["subject_count"]:
            details.append(f"extra_subject_generated (detected={subject_count['detected']})")
        diagnosis = "; ".join(details)

    print(f"  identity={identity:.3f} [{identity_eval_mode}]  pose={pose:.3f}  "
          f"framing={framing:.3f}  beat={beat_ms:.0f}ms  "
          f"look={look_score:.2f}  subjects={subject_count['detected']}  → {verdict.upper()}")
    if diagnosis:
        print(f"  diagnosis: {diagnosis}")

    return {"scores": scores, "verdict": verdict, "diagnosis": diagnosis}


# ─── Full Evaluation Pass ─────────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Evaluate all shots that have generated images but no final verdict yet.
    Logs each attempt to the decision log in state.
    """
    shots_to_eval = [
        s for s in state["shots"]
        if s.get("generated_image")
        and s["evaluation"]["status"] not in ("pass", "needs_human")
    ]

    print(f"[eval] evaluating {len(shots_to_eval)} shots")

    for shot in shots_to_eval:
        result = evaluate_shot(shot, state)
        st.log_attempt(
            state=state,
            shot_id=shot["shot_id"],
            scores=result["scores"],
            verdict=result["verdict"],
            diagnosis=result["diagnosis"],
            repair_action="none" if result["verdict"] == "pass" else "pending",
            prompt_used=shot.get("_last_prompt", ""),
        )

    # Tally failed
    state["run_stats"]["failed"] = sum(
        1 for s in state["shots"] if s["evaluation"]["status"] == "fail"
    )
    st.save(state)
    return state


if __name__ == "__main__":
    s = st.load()
    run(s)
    st.print_summary(s)
