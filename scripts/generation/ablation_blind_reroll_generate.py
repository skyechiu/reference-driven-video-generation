"""
ablation_blind_reroll_generate.py — Small controlled repair ablation, GENERATION phase.

Purpose
  Test: under the SAME retry budget, does targeted (diagnosis-driven) repair recover
  a failed shot better than a blind reroll (same prompt/reference, no diagnosis)?

  This script generates ONLY the missing arm: Condition A "blind reroll".
  Condition B "targeted repair" already exists as real archived evidence on disk —
  it is NOT regenerated here (saves cost, avoids re-litigating already-accepted output):

    keyframe cases (gpt-image-1):
      shot_001  A = original face_visible KEYFRAME_PROMPT (generate_street_run.py, unchanged)
                B = outputs/runs/live_test_04_street_look3/keyframes/shot_001_keyframe_look3_street_3q.png
                    (already promoted to the approved shot_001 keyframe)
      shot_002  A = original back_view KEYFRAME_PROMPT (generate_street_run.py, unchanged)
                B = outputs/runs/live_test_04_street_look3/keyframes/shot_002_keyframe_look3_street.png
                    (already the approved keyframe — regen_shot002_004.py v2 was promoted in place)
      shot_004  A = original face_visible KEYFRAME_PROMPT (generate_street_run.py, unchanged)
                B = outputs/runs/live_test_04_street_look3/keyframes/shot_004_keyframe_look3_street.png
                    (already the approved keyframe — v4_proportion_fix was promoted in place)

    motion cases (Kling I2V, street run):
      shot_001  A = same approved keyframe + a neutral/undirected walk-motion prompt (see note below)
                B = outputs/.../clips/shot_001_look3_street_motion_v2.mp4 (already on disk, flow 51%)
      shot_003  A = same approved keyframe + a neutral/undirected walk-motion prompt
                B = outputs/.../clips/shot_003_look3_street_motion_v2.mp4 (already on disk, flow 47%)

  IMPORTANT — ground-truth correction vs the original ask:
    shot_003's KEYFRAME is an extreme low-angle FEET-ONLY close-up (no face, ever —
    see generate_street_run.py SHOTS[shot_003], slot_mode="lower_body"). It has no v2/v3
    keyframe file on disk and decision_log.json never recorded a repair for it. There is
    no real "targeted repair" counterpart for a shot_003 keyframe case, so it is EXCLUDED
    from the keyframe ablation rather than invented. shot_003 DOES have a real motion
    repair case (14->51 is shot_001, 19->47 is shot_003) and that IS included above.

  IMPORTANT — motion Condition A prompt provenance:
    The literal original (pre-repair) Kling video_prompt for shot_001/shot_003 was edited
    in place in generate_street_run.py and was not separately archived; only the *result*
    (14%, 19% flow, saved as *_premotion_backup.mp4) survived. So Condition A here is NOT
    a byte-exact resubmission of the lost original text. It is a clearly-labelled, generic,
    non-diagnostic walking-motion prompt (no "damping words removed / motion cues named"
    engineering applied) submitted from the SAME approved keyframe. Report this honestly as
    "reconstructed blind-reroll prompt", not as the literal v1 prompt.

Safety (matches this project's existing script convention)
  - CONFIRM_RUN = False by default -> prints the full plan (prompts, paths, budget) and
    makes NO API calls, writes NOTHING.
  - Writes ONLY under outputs/ablation_repair_20260807/ — never touches any existing
    keyframe, clip, final video, or decision_log.json.
  - Max 2 attempts per shot per condition (MAX_RETRIES), matching the requested budget.

Run (from project root, in your normal environment with network + .env):
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 ablation_blind_reroll_generate.py            # dry run — plan only
    python3 ablation_blind_reroll_generate.py --confirm   # real generation (spends API credit)

Cost/time (rough, at MAX_RETRIES=2, before any early accept):
    up to 6 gpt-image-1 calls (shot_001/002/004 x 2 attempts)
    up to 4 Kling v1.6 std 5s calls (street shot_001/003 x 2 attempts)
  Kling polls every 10s up to 10min/clip; budget ~30-45 min wall time if all attempts run.
"""

import ast, base64, io, json, os, sys, time
from pathlib import Path
from datetime import datetime

CONFIRM_RUN = "--confirm" in sys.argv
MAX_RETRIES = 2

def _find_repo_root() -> Path:
    """Walk upward from this file until a repository-root marker is found.

    Looks for a .git directory, or the sibling pipeline/ + dissertation/
    directories that mark the top of this project. This makes the script
    location-independent -- it can live at repo root or several levels
    deep under scripts/ and still resolve the same ROOT.
    """
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        if (current / "pipeline").exists() and (current / "dissertation").exists():
            return current
        current = current.parent
    raise RuntimeError("Repository root not found (no .git or pipeline/+dissertation/ marker)")


ROOT       = _find_repo_root()
RUN_DIR    = ROOT / "outputs" / "runs" / "live_test_04_street_look3"
KF_DIR     = RUN_DIR / "keyframes"
CLIP_DIR   = RUN_DIR / "clips"
SRC_SCRIPT = ROOT / "scripts" / "generation" / "generate_street_run.py"

OUT_DIR      = ROOT / "outputs" / "ablation_repair_20260807"
OUT_KF_DIR   = OUT_DIR / "keyframes"
OUT_CLIP_DIR = OUT_DIR / "clips"
OUT_LOG      = OUT_DIR / "generation_log.json"

SCENE_REF  = ROOT / "assets/scenes/built_in/scene_02_modern_street/references"
LOOK_DIR   = ROOT / "assets/looks/look_3_tailored_self"

# Files that must NEVER be written by this script
PROTECTED = {
    KF_DIR / "shot_001_keyframe_look3_street.png",
    KF_DIR / "shot_002_keyframe_look3_street.png",
    KF_DIR / "shot_004_keyframe_look3_street.png",
    CLIP_DIR / "shot_001_look3_street.mp4",
    CLIP_DIR / "shot_003_look3_street.mp4",
    RUN_DIR / "final" / "final_look3_street_demo.mp4",
    RUN_DIR / "final" / "decision_log.json",
}

# ── Condition B (targeted repair) — pointers to EXISTING evidence, not regenerated ──
CONDITION_B = {
    "shot_001_keyframe": KF_DIR / "shot_001_keyframe_look3_street.png",  # promoted 3q version
    "shot_002_keyframe": KF_DIR / "shot_002_keyframe_look3_street.png",
    "shot_004_keyframe": KF_DIR / "shot_004_keyframe_look3_street.png",
    "shot_001_motion":   CLIP_DIR / "shot_001_look3_street_motion_v2.mp4",
    "shot_003_motion":   CLIP_DIR / "shot_003_look3_street_motion_v2.mp4",
    "shot_001_motion_v1_baseline": CLIP_DIR / "shot_001_look3_street_premotion_backup.mp4",  # flow=14%
    "shot_003_motion_v1_baseline": CLIP_DIR / "shot_003_look3_street_premotion_backup.mp4",  # flow=19%
}

# ── Pull the ORIGINAL (pre-repair) keyframe prompts straight from generate_street_run.py ──
def load_original_keyframe_prompts(py_path: Path, shot_ids):
    """Static (non-executing) extraction. KEYFRAME_PROMPT/NEGATIVE_PROMPT in
    generate_street_run.py are built as `_VAR_A + "\\n" + _VAR_B + ...` — string
    concatenation of module-level constants, not plain literals — so plain
    ast.literal_eval() fails on the BinOp(Add) nodes. Resolve module-level string
    vars first, then walk the concatenation tree. Never imports/executes the file
    (it would trigger real asset checks and, in full_auto mode, real API calls)."""
    tree = ast.parse(py_path.read_text(encoding="utf-8"))

    # Pass 1: resolve every top-level `NAME = <string literal(s)>` assignment.
    string_vars = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    try:
                        val = ast.literal_eval(node.value)
                    except Exception:
                        continue
                    if isinstance(val, str):
                        string_vars[t.id] = val

    def resolve(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in string_vars:
                return string_vars[node.id]
            raise ValueError(f"Unresolved name while reconstructing prompt: {node.id}")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return resolve(node.left) + resolve(node.right)
        return ast.literal_eval(node)  # fallback for anything else literal-evaluable

    # Pass 2: find SHOTS and resolve KEYFRAME_PROMPT/NEGATIVE_PROMPT per shot.
    shots_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "SHOTS" and isinstance(node.value, ast.List):
                    shots_node = node.value
    if shots_node is None:
        raise RuntimeError("Could not find SHOTS list in generate_street_run.py")
    out = {}
    for elt in shots_node.elts:
        if not isinstance(elt, ast.Dict):
            continue
        kv = {k.value: v for k, v in zip(elt.keys, elt.values) if isinstance(k, ast.Constant)}
        sid_node = kv.get("shot_id")
        if sid_node is None:
            continue
        sid = ast.literal_eval(sid_node)
        if sid in shot_ids:
            out[sid] = {
                "keyframe_prompt": resolve(kv["KEYFRAME_PROMPT"]),
                "negative_prompt":  resolve(kv["NEGATIVE_PROMPT"]),
                "slot_mode":        ast.literal_eval(kv["slot_mode"]),
            }
    missing = [s for s in shot_ids if s not in out]
    if missing:
        raise RuntimeError(f"Original prompts not found for: {missing}")
    return out

ORIGINAL = load_original_keyframe_prompts(SRC_SCRIPT, ["shot_001", "shot_002", "shot_004"])

# ── Reference images per shot (mirrors generate_street_run.py's real slot logic) ──
FRONT_ANCHOR   = LOOK_DIR / "look3_identity_anchor_front.png"
PROFILE_ANCHOR = LOOK_DIR / "look3_identity_anchor_profile.png"
LOOK_CLOSEUP   = LOOK_DIR / "look3_closeup.png"
LOOK_FRONT     = LOOK_DIR / "look3_front.png"
LOOK_SHEET     = LOOK_DIR / "look3_sheet.png"
ESTABLISHING   = SCENE_REF / "establishing_view_16x9.png"

KEYFRAME_JOBS = {
    # shot_id : (images_in_order, quality, input_fidelity)
    "shot_001": ([FRONT_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT, PROFILE_ANCHOR], "high", "high"),
    "shot_002": ([ESTABLISHING, FRONT_ANCHOR, LOOK_FRONT, PROFILE_ANCHOR], "medium", "high"),
    "shot_004": ([FRONT_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT, PROFILE_ANCHOR], "high", "high"),
}

# ── Motion (Kling) blind-reroll prompt — clearly labelled reconstruction, see docstring ──
MOTION_BLIND_PROMPT = {
    "shot_001": (
        "The woman walks naturally along the Paris cobblestone street in the approved Look 3 "
        "outfit. Natural walking motion. Preserve the street, the outfit, and her identity."
    ),
    "shot_003": (
        "Low-angle view of the approved Look 3 lower body — wide denim and black oxford shoes — "
        "walking across the Paris cobblestones. Natural walking motion. Do not show face, torso, "
        "arms, or upper body."
    ),
}
MOTION_NEGATIVE = "static, frozen, no movement, identity drift, extra people"
KLING_SETTINGS = dict(model_name="kling-v1-6", mode="std", duration=5, aspect_ratio="9:16", cfg_scale=0.5)
MOTION_KEYFRAMES = {
    "shot_001": KF_DIR / "shot_001_keyframe_look3_street.png",
    "shot_003": KF_DIR / "shot_003_keyframe_look3_street.png",
}


def print_plan():
    print("=" * 78)
    print("SMALL CONTROLLED REPAIR ABLATION — blind reroll generation (Condition A only)")
    print("=" * 78)
    print(f"CONFIRM_RUN = {CONFIRM_RUN}   MAX_RETRIES = {MAX_RETRIES}\n")
    print("KEYFRAME cases (gpt-image-1) — resubmitting the ORIGINAL unmodified prompt:")
    for sid, (imgs, q, fid) in KEYFRAME_JOBS.items():
        print(f"  {sid}: quality={q} fidelity={fid} images={[p.name for p in imgs]}")
        print(f"    prompt chars: {len(ORIGINAL[sid]['keyframe_prompt'])}")
    print("\nMOTION cases (Kling v1.6) — reconstructed neutral/undirected motion prompt:")
    for sid, kf in MOTION_KEYFRAMES.items():
        print(f"  {sid}: keyframe={kf.name}")
        print(f"    prompt: {MOTION_BLIND_PROMPT[sid]}")
    print(f"\nCondition B (targeted repair) — NOT regenerated, reused as-is:")
    for k, v in CONDITION_B.items():
        print(f"  {k}: {v}  (exists={v.exists()})")
    print(f"\nOutput dir (new, never overwrites existing evidence): {OUT_DIR}")
    print("=" * 78)


def preflight():
    probs = []
    for sid, (imgs, _, _) in KEYFRAME_JOBS.items():
        for p in imgs:
            if not p.exists():
                probs.append(f"missing reference image for {sid}: {p}")
    for sid, kf in MOTION_KEYFRAMES.items():
        if not kf.exists():
            probs.append(f"missing keyframe for {sid} motion reroll: {kf}")
    for k, v in CONDITION_B.items():
        if not v.exists():
            probs.append(f"MISSING Condition-B evidence file (expected already on disk): {v}")
    for p in list(OUT_KF_DIR.glob("*")) + list(OUT_CLIP_DIR.glob("*")):
        if p.resolve() in {q.resolve() for q in PROTECTED}:
            probs.append(f"FATAL: output path collides with protected file: {p}")
    return probs


def gen_keyframe(client, sid, images, prompt, quality, fidelity, attempt):
    out_path = OUT_KF_DIR / f"{sid}_blind_reroll_r{attempt}.png"
    if out_path.resolve() in {p.resolve() for p in PROTECTED}:
        raise RuntimeError(f"refusing to write protected path {out_path}")
    handles = [open(p, "rb") for p in images]
    try:
        resp = client.images.edit(
            model="gpt-image-1", image=handles, prompt=prompt,
            size="1024x1536", quality=quality, input_fidelity=fidelity, n=1,
        )
    finally:
        for h in handles:
            h.close()
    data = base64.b64decode(resp.data[0].b64_json)
    out_path.write_bytes(data)
    print(f"  [{sid}] attempt {attempt}: SAVED {out_path.name} ({len(data)//1024} KB)")
    return out_path


def encode_jpeg(path: Path) -> str:
    from PIL import Image as PILImage
    img = PILImage.open(path).convert("RGB")
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=95)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def gen_motion(sid, key, attempt):
    import requests, httpx
    out_path = OUT_CLIP_DIR / f"{sid}_blind_reroll_r{attempt}.mp4"
    if out_path.resolve() in {p.resolve() for p in PROTECTED}:
        raise RuntimeError(f"refusing to write protected path {out_path}")
    payload = {
        **KLING_SETTINGS,
        "image": encode_jpeg(MOTION_KEYFRAMES[sid]),
        "prompt": MOTION_BLIND_PROMPT[sid],
        "negative_prompt": MOTION_NEGATIVE,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    task_id = None
    for a in range(4):
        r = requests.post("https://api.klingai.com/v1/videos/image2video", headers=headers, json=payload, timeout=30)
        if r.status_code == 429:
            wait = 15 * (2 ** a); print(f"  [{sid}] rate limited, waiting {wait}s"); time.sleep(wait); continue
        r.raise_for_status()
        task_id = r.json()["data"]["task_id"]; break
    if not task_id:
        print(f"  [{sid}] attempt {attempt}: FAILED to submit"); return None
    for poll in range(60):
        time.sleep(10)
        d = requests.get(f"https://api.klingai.com/v1/videos/image2video/{task_id}", headers=headers, timeout=15).json()["data"]
        st = d["task_status"]
        if st == "succeed":
            url = d["task_result"]["videos"][0]["url"]
            with httpx.Client() as hc:
                out_path.write_bytes(hc.get(url, timeout=60).content)
            print(f"  [{sid}] attempt {attempt}: SAVED {out_path.name} ({out_path.stat().st_size//1024} KB)")
            return out_path
        if st == "failed":
            print(f"  [{sid}] attempt {attempt}: KLING FAILED: {d}"); return None
    print(f"  [{sid}] attempt {attempt}: timed out"); return None


def main():
    print_plan()
    probs = preflight()
    if probs:
        print("\nPRE-FLIGHT PROBLEMS:")
        for p in probs:
            print(f"   ! {p}")
        sys.exit(1)
    if not CONFIRM_RUN:
        print("\nDRY RUN — CONFIRM_RUN is False. No API calls made, nothing written.")
        print("Review the plan above, then run again with --confirm to actually generate.")
        sys.exit(0)

    OUT_KF_DIR.mkdir(parents=True, exist_ok=True)
    OUT_CLIP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from dotenv import load_dotenv; load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    openai_key = os.getenv("OPENAI_API_KEY", "")
    kling_key  = os.getenv("KLING_API_KEY", "")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY not set"); sys.exit(1)
    if not kling_key:
        print("ERROR: KLING_API_KEY not set"); sys.exit(1)
    from openai import OpenAI
    client = OpenAI(api_key=openai_key)

    log = {"generated_at": datetime.utcnow().isoformat() + "Z", "max_retries": MAX_RETRIES,
           "condition_b_reused": {k: str(v) for k, v in CONDITION_B.items()},
           "keyframe_attempts": {}, "motion_attempts": {}}

    print("\n[keyframes] generating blind-reroll attempts ...")
    for sid, (imgs, quality, fidelity) in KEYFRAME_JOBS.items():
        log["keyframe_attempts"][sid] = []
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                out = gen_keyframe(client, sid, imgs, ORIGINAL[sid]["keyframe_prompt"], quality, fidelity, attempt)
                log["keyframe_attempts"][sid].append(str(out))
            except Exception as e:
                print(f"  [{sid}] attempt {attempt}: ERROR {e}")
                log["keyframe_attempts"][sid].append(f"ERROR: {e}")
            time.sleep(5)

    print("\n[motion] generating blind-reroll attempts ...")
    for sid in MOTION_KEYFRAMES:
        log["motion_attempts"][sid] = []
        for attempt in range(1, MAX_RETRIES + 1):
            out = gen_motion(sid, kling_key, attempt)
            log["motion_attempts"][sid].append(str(out) if out else "FAILED")
            time.sleep(2)

    OUT_LOG.write_text(json.dumps(log, indent=2))
    print(f"\nDONE. Log written: {OUT_LOG}")
    print("Next: run ablation_analyze.py to compute metrics and build the summary/table/contact sheet.")


if __name__ == "__main__":
    main()
