"""
run_kling_i2v.py — submit 4 approved keyframes to Kling I2V, poll until done.

Usage:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 run_kling_i2v.py

What this does:
  - Submits all 4 keyframes to Kling image-to-video in sequence
  - Polls all pending tasks every 10s until all complete or fail
  - Downloads each clip to:
      outputs/runs/live_test_03_4shots/clips/
  - Does NOT call OpenAI image generation
  - Does NOT run repair or evaluation

Keyframes used (approved):
  shot_001_keyframe_look3_preserve_scene_test.png
  shot_002_keyframe_look3_preserve_scene.png
  shot_003_keyframe_look3_preserve_scene.png
  shot_004_keyframe_look3_preserve_scene.png
"""

import base64, io, json, os, sys, time
from pathlib import Path

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


ROOT = _find_repo_root()
# ── Load .env ──────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    print("[env] loaded .env")
except ImportError:
    print("[env] python-dotenv not installed — using system env vars")

KLING_API_KEY = os.getenv("KLING_API_KEY", "")
if not KLING_API_KEY:
    print("ERROR: KLING_API_KEY not set in .env or environment")
    sys.exit(1)

# ── Shot config ────────────────────────────────────────────────────────────
KF_DIR   = ROOT / "outputs/runs/live_test_03_4shots/keyframes"
CLIP_DIR = ROOT / "outputs/runs/live_test_03_4shots/clips"
CLIP_DIR.mkdir(parents=True, exist_ok=True)

# Load video_prompts from project_state.json
state   = json.loads((ROOT / "project_state.json").read_text())
shot_map = {s["shot_id"]: s for s in state["shots"]}

SHOTS = [
    {
        "shot_id": "shot_001",
        "keyframe": KF_DIR / "shot_001_keyframe_look3_preserve_scene_test.png",
        "clip_out": CLIP_DIR / "shot_001_look3.mp4",
        "duration_s": 2.4,
    },
    {
        "shot_id": "shot_002",
        "keyframe": KF_DIR / "shot_002_keyframe_look3_preserve_scene.png",
        "clip_out": CLIP_DIR / "shot_002_look3.mp4",
        "duration_s": 2.267,
    },
    {
        "shot_id": "shot_003",
        "keyframe": KF_DIR / "shot_003_keyframe_look3_preserve_scene.png",
        "clip_out": CLIP_DIR / "shot_003_look3.mp4",
        "duration_s": 2.133,
    },
    {
        "shot_id": "shot_004",
        "keyframe": KF_DIR / "shot_004_keyframe_look3_preserve_scene.png",
        "clip_out": CLIP_DIR / "shot_004_look3.mp4",
        "duration_s": 1.1,
    },
]

# ── Attach video_prompt + negative_prompt from state ──────────────────────
for s in SHOTS:
    brief = shot_map[s["shot_id"]].get("generation_brief", {})
    s["video_prompt"]    = brief.get("video_prompt", "Slow natural motion. Preserve character identity throughout.")
    s["negative_prompt"] = brief.get("negative_prompt", "face change, identity change, morphing, distortion")

# ── Verify all keyframes exist ─────────────────────────────────────────────
print("\n[keyframes]")
for s in SHOTS:
    exists = s["keyframe"].exists()
    print(f"  {s['shot_id']}: {s['keyframe'].name}  exists={exists}")
    if not exists:
        print(f"ERROR: missing keyframe: {s['keyframe']}")
        sys.exit(1)

# ── Helpers ────────────────────────────────────────────────────────────────
import requests, httpx
from PIL import Image as PILImage

def encode_jpeg(path: Path) -> str:
    """Convert to RGB JPEG and base64-encode (Kling rejects RGBA/PNG)."""
    img = PILImage.open(path).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")

def kling_headers() -> dict:
    return {"Authorization": f"Bearer {KLING_API_KEY}", "Content-Type": "application/json"}

# ── Submit all 4 tasks ─────────────────────────────────────────────────────
print("\n[kling] submitting tasks...")
pending = []   # list of {shot_id, task_id, clip_out, duration_s}

for s in SHOTS:
    payload = {
        "model_name":      "kling-v1-6",
        "mode":            "std",
        "image":           encode_jpeg(s["keyframe"]),
        "prompt":          s["video_prompt"],
        "negative_prompt": s["negative_prompt"],
        "cfg_scale":       0.5,
        "duration":        5,          # all shots < 7s → 5s clip
        "aspect_ratio":    "9:16",
    }

    submitted = False
    for attempt in range(4):
        resp = requests.post(
            "https://api.klingai.com/v1/videos/image2video",
            headers=kling_headers(), json=payload, timeout=30,
        )
        if resp.status_code == 429:
            wait = 15 * (2 ** attempt)
            print(f"  [{s['shot_id']}] rate limited (429), waiting {wait}s...")
            time.sleep(wait)
            continue
        if not resp.ok:
            print(f"  [{s['shot_id']}] submit error {resp.status_code}: {resp.text[:300]}")
            resp.raise_for_status()
        task_id = resp.json()["data"]["task_id"]
        print(f"  [{s['shot_id']}] task_id={task_id}")
        pending.append({
            "shot_id":    s["shot_id"],
            "task_id":    task_id,
            "clip_out":   s["clip_out"],
            "duration_s": s["duration_s"],
        })
        submitted = True
        break

    if not submitted:
        print(f"ERROR: could not submit {s['shot_id']} after 4 retries")
        sys.exit(1)

    time.sleep(2)   # small gap between submits to avoid burst rate limit

# ── Poll all tasks until complete ─────────────────────────────────────────
print(f"\n[kling] polling {len(pending)} tasks (every 10s, max 10 min each)...")
results = []
done    = set()

for attempt in range(60):
    time.sleep(10)
    still_pending = [t for t in pending if t["shot_id"] not in done]
    if not still_pending:
        break

    for t in still_pending:
        poll = requests.get(
            f"https://api.klingai.com/v1/videos/image2video/{t['task_id']}",
            headers=kling_headers(), timeout=15,
        )
        data   = poll.json()["data"]
        status = data["task_status"]
        print(f"  [{t['shot_id']}] status={status}  (poll {attempt+1})")

        if status == "succeed":
            video_url = data["task_result"]["videos"][0]["url"]
            with httpx.Client() as client:
                r = client.get(video_url, timeout=60)
                t["clip_out"].write_bytes(r.content)
            size_kb = t["clip_out"].stat().st_size // 1024
            print(f"  [{t['shot_id']}] ✓ SAVED: {t['clip_out'].name}  ({size_kb} KB)")
            results.append({
                "shot_id":    t["shot_id"],
                "task_id":    t["task_id"],
                "clip_path":  str(t["clip_out"]),
                "size_kb":    size_kb,
                "duration_s": t["duration_s"],
            })
            done.add(t["shot_id"])

        elif status == "failed":
            print(f"  [{t['shot_id']}] FAILED: {data}")
            done.add(t["shot_id"])   # stop polling, mark done

# ── Final report ───────────────────────────────────────────────────────────
print("\n" + "="*60)
print("KLING I2V — COMPLETION REPORT")
print("="*60)
for r in results:
    print(f"\n  {r['shot_id']}")
    print(f"    task_id   : {r['task_id']}")
    print(f"    clip_path : {r['clip_path']}")
    print(f"    file_size : {r['size_kb']} KB")
    print(f"    duration_s: {r['duration_s']}s source → 5s Kling clip")

failed = [t["shot_id"] for t in pending if t["shot_id"] not in {r["shot_id"] for r in results}]
if failed:
    print(f"\n  FAILED / TIMEOUT: {failed}")

print(f"\n  Total submitted : {len(pending)}")
print(f"  Completed       : {len(results)}")
print(f"  Failed/timeout  : {len(failed)}")
print("\n  No OpenAI image generation called.")
print("  No repair called.")
print("  No evaluation called.")
print("="*60)
