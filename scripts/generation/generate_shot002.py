"""
generate_shot002.py — run from the project root to generate the shot_002 keyframe.

Usage:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 generate_shot002.py

What this does:
  - Uses a hardcoded prompt built for shot_002's wide, full-body, back-view walking framing
  - Calls OpenAI images.edit with gpt-image-1, 1024x1536, medium quality
  - Passes 4 images in order:
      [0] shot_002_best.png      — source_frame_structural (PRIMARY STRUCTURAL BASE)
      [1] look3_closeup.png      — face / identity reference
      [2] look3_front.png        — look front body reference
      [3] look3_sheet.png        — look sheet / overview
  - Saves result to:
      outputs/runs/live_test_03_4shots/keyframes/
      shot_002_keyframe_look3_preserve_scene.png

Constraints enforced:
  - Only shot_002 — no other shots
  - No Kling call
  - No repair
  - Forbidden-word guard checked before any API call (blocks on violation)

Prompt strategy (v1):
  - Source frame is [0] so images.edit treats it as the primary structural anchor
  - shot_002 is wide / full body / back view — subject walking away from camera
  - Do NOT force a face turn — back silhouette is the composition
  - Full tailored outfit visible from behind
  - Static camera, beach, warm sunset
"""

import base64, json, os, sys
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
# ── Load .env ─────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    print("[env] loaded .env")
except ImportError:
    print("[env] python-dotenv not installed — using system env vars")

# ── Forbidden-word guard ───────────────────────────────────────────────────
FORBIDDEN = [
    "bride", "bridal", "wedding", "wedding dress", "bridal gown",
    "cathedral veil", "white lace wedding gown",
    "copied source outfit", "same outfit as source",
]

def check_forbidden(prompt: str, look_id: str = "") -> tuple[bool, list]:
    if any(w in look_id.lower() for w in ("bridal", "bride", "wedding")):
        return True, []
    hits = [t for t in FORBIDDEN if t in prompt.lower()]
    return (len(hits) == 0), hits

# ── Load state (for run_id, look_id only) ─────────────────────────────────
state   = json.loads((ROOT / "project_state.json").read_text())
cfg     = state.get("config", {})
run_id  = cfg.get("run_id", "live_test_03_4shots")
look_id = cfg.get("selected_look_id", "look_3_tailored_self")
shot    = next((s for s in state["shots"] if s["shot_id"] == "shot_002"), None)

if shot is None:
    print("ERROR: shot_002 not found in project_state.json")
    sys.exit(1)

# ── Prompt (v2 — wide / full back view / walking away / natural video-frame realism) ──
KEYFRAME_PROMPT = (
    "The first image is the structural and compositional reference. "
    "Treat it as a locked frame. "
    "Copy its exact body position, walking pose, crop, subject scale, "
    "camera distance, framing, and background without modification. "
    "Only replace the person's identity and outfit — nothing else changes. "
    "Do not repose the subject. "
    "Do not turn the subject to face the camera. "
    "Do not create a portrait. "
    "This is a wide video frame of a figure walking away, not a face reveal."
    "\n\n"
    "CHARACTER IDENTITY: "
    "Young woman, mid-twenties, slender tall build. "
    "Deep-set almond-shaped eyes, strong defined brows, high cheekbones, straight nose, full lips. "
    "Light olive skin tone. "
    "The face is mostly or fully turned away from the camera — preserve this exactly as in the source frame. "
    "The silhouette and posture carry the identity in this shot."
    "\n\n"
    "LOOK — THE TAILORED SELF: "
    "Charcoal tailored cropped blazer, white cotton shirt, muted olive tie, "
    "wide faded blue denim trousers with clean break at ankle, "
    "black leather oxford shoes. "
    "Hair: loose natural dark hair, centre part, slightly undone texture, falls to shoulders. "
    "Silhouette: relaxed broad-shoulder tailored, wide trouser leg, cropped blazer waist. "
    "The full outfit is visible from behind and the side — shoulders, blazer back, trousers, shoes. "
    "The wide-leg denim and oxford shoes should be clearly legible. "
    "Natural fabric wrinkles on the blazer and trousers — not plasticky or overly smooth."
    "\n\n"
    "FRAMING AND POSE — copy from first image exactly: "
    "Wide shot. Full body from head to feet. "
    "Subject is walking away from camera, along the beach, toward the sunset horizon. "
    "Back view. The character's back, shoulders, and walking stride dominate the frame. "
    "Legs in natural walking stride — one foot forward, weight in motion. "
    "Do not stop the stride or plant both feet. "
    "Preserve the exact body scale, position in frame, and walking angle from the source frame. "
    "Both feet must remain fully visible in frame. Do not crop the shoes or lower legs. "
    "Realistic beach sand and uneven foot placement — not a flat studio floor. "
    "Maintain a real walking action, not a posed standing shot."
    "\n\n"
    "SCENE — preserve from source frame exactly: "
    "Seaside sunset. Beach, ocean horizon, natural warm sunset light, coastal atmosphere. "
    "The horizon and sky fill the upper portion of the frame behind the walking figure. "
    "Do not alter the background, lighting direction, or atmosphere. "
    "Natural imperfect lighting — not a poster-perfect or oversaturated sky."
    "\n\n"
    "REALISM — this must look like a real video frame: "
    "Very subtle motion softness only where natural movement would cause it, "
    "especially in the walking legs or trailing foot. "
    "The overall figure, outfit silhouette, and scene should remain readable and coherent. "
    "Use subtle natural video-frame softness and imperfect detail, rather than hyper-sharp studio clarity. "
    "Preserve the original reference frame texture and natural imperfections. "
    "It should look like a real frame extracted from a reference video, not a generated image. "
    "Keep the image grounded and documentary-like. "
    "It should look like the original reference frame was edited, not like a newly generated campaign."
    "\n\n"
    "AVOID: "
    "Avoid overly clean AI lighting, overly smooth skin, plastic fabric, "
    "perfect poster composition, hyper-polished colors, and commercial stock-photo aesthetics. "
    "Not a generated advertisement. Not a stock photo. Not a perfect sunset poster."
    "\n\n"
    "GUARD: "
    "Generate only one visible character. "
    "No extra people, background figures, duplicated bodies, or additional faces. "
    "Do not copy the source subject's clothing, hairstyle, or styling. "
    "Camera: static, stable. "
    "Do not add front-facing portrait energy. "
    "Do not stop the motion into a static pose. Do not turn this into a posed stance. "
    "Do not copy the source subject's outfit, hairstyle, or styling. "
    "Keep the selected tailored look only."
)

# ── Negative prompt (banned terms — for reference/logging only; NOT passed to API) ──
# Guard scans only KEYFRAME_PROMPT above, never this string.
NEGATIVE_PROMPT = (
    "different face, changed identity, distorted face, wrong person, "
    "extra limbs, unstable hands, distorted proportions, "
    "multiple people, extra person, second face, background characters, crowd, duplicated body, "
    "bride, bridal, wedding, wedding dress, bridal gown, veil, cathedral veil, wedding veil, "
    "white beach dress, copied source outfit, same outfit as source, "
    "wrong outfit, wrong hairstyle, different identity, generic woman, random bride, "
    "front-facing portrait, symmetric portrait, editorial fashion pose, "
    "urban rooftop, city skyline, studio lighting, studio backdrop"
)

# ── Guard check — scans KEYFRAME_PROMPT only, never NEGATIVE_PROMPT ───────
ok, violations = check_forbidden(KEYFRAME_PROMPT, look_id)
if not ok:
    print(f"BLOCKED by forbidden-word guard: {violations}")
    print("Fix the prompt before generating.")
    sys.exit(1)
print(f"[guard] CLEAN — no forbidden terms in KEYFRAME_PROMPT")

# ── Image inputs (source frame FIRST) ────────────────────────────────────
IMAGES = [
    ROOT / "outputs/ref_panels/shot_002_best.png",                    # [0] source_frame_structural (PRIMARY)
    ROOT / "assets/looks/look_3_tailored_self/look3_closeup.png",    # [1] face / identity reference
    ROOT / "assets/looks/look_3_tailored_self/look3_front.png",      # [2] look front body reference
    ROOT / "assets/looks/look_3_tailored_self/look3_sheet.png",      # [3] look sheet / overview
]
SLOTS = [
    "source_frame_structural (PRIMARY)",
    "face_closeup",
    "front_full_body",
    "look_overview",
]

print(f"\n[images] {len(IMAGES)} inputs:")
for i, p in enumerate(IMAGES):
    exists = p.exists()
    print(f"  [{i}] {p.name}  slot={SLOTS[i]}  exists={exists}")
    if not exists:
        print(f"ERROR: missing image: {p}")
        sys.exit(1)

# ── Output path ────────────────────────────────────────────────────────────
out_dir  = ROOT / "outputs" / "runs" / run_id / "keyframes"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "shot_002_keyframe_look3_preserve_scene.png"

print(f"\n[output]          {out_path}")
print(f"[keyframe_prompt] {len(KEYFRAME_PROMPT)} chars")
print(f"[negative_prompt] {len(NEGATIVE_PROMPT)} chars (reference only — not passed to API)")
print(f"[model]           gpt-image-1 / images.edit / 1024x1536 / medium")
print(f"[look]            {look_id}")
print(f"[shot]            shot_002 only — no other shots")
print(f"[scene]           preserve_reference_scene\n")

# ── API key check ──────────────────────────────────────────────────────────
api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    print("ERROR: OPENAI_API_KEY not set in .env or environment")
    sys.exit(1)

# ── Generate ───────────────────────────────────────────────────────────────
from openai import OpenAI
client  = OpenAI(api_key=api_key, max_retries=1)

print("Calling OpenAI images.edit ... (this may take 60–90 seconds)")
handles = []
try:
    for p in IMAGES:
        handles.append(open(p, "rb"))
    response = client.images.edit(
        model="gpt-image-1",
        image=handles,
        prompt=KEYFRAME_PROMPT,
        size="1024x1536",
        quality="medium",
        n=1,
    )
except Exception as e:
    print(f"\nERROR during images.edit: {e}")
    sys.exit(1)
finally:
    for h in handles:
        h.close()

# ── Save ───────────────────────────────────────────────────────────────────
img_data = base64.b64decode(response.data[0].b64_json)
out_path.write_bytes(img_data)

print(f"\n✓ SAVED: {out_path}")
print(f"  File size: {len(img_data) // 1024} KB")
print(f"\nDone. shot_002 only. No other shots generated. No Kling called.")
