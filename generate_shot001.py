"""
generate_shot001.py — run from the project root to generate the shot_001 keyframe.

Usage:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 generate_shot001.py

What this does:
  - Uses a hardcoded prompt built for shot_001's over-shoulder MCU framing
  - Calls OpenAI images.edit with gpt-image-1, 1024x1536, medium quality
  - Passes 4 images in order:
      [0] shot_001_best.png      — source_frame_structural (PRIMARY STRUCTURAL BASE)
      [1] look3_closeup.png      — face / identity reference
      [2] look3_front.png        — look front body reference
      [3] look3_sheet.png        — look sheet / overview
  - Saves result to:
      outputs/runs/live_test_03_4shots/keyframes/
      shot_001_keyframe_look3_preserve_scene_test.png

Constraints enforced:
  - Only shot_001 — no other shots
  - No Kling call
  - No repair
  - Forbidden-word guard checked before any API call (blocks on violation)

Prompt strategy (v2):
  - Source frame is [0] so images.edit treats it as the primary structural anchor
  - Prompt opens with explicit "use first image as structural base" instruction
  - Pose described as over-shoulder MCU, not generic standing portrait
  - Expression instruction: follow source frame's natural, softer feeling
  - Hard guard against passport-style front-facing portrait flip
"""

import base64, json, os, sys
from pathlib import Path

ROOT = Path(__file__).parent

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

# ── Load state (for run_id, look_id, negative_prompt only) ────────────────
state     = json.loads((ROOT / "project_state.json").read_text())
cfg       = state.get("config", {})
run_id    = cfg.get("run_id", "live_test_03_4shots")
look_id   = cfg.get("selected_look_id", "look_3_tailored_self")
shot      = next((s for s in state["shots"] if s["shot_id"] == "shot_001"), None)

if shot is None:
    print("ERROR: shot_001 not found in project_state.json")
    sys.exit(1)

negative_prompt = (shot.get("generation_brief") or {}).get("negative_prompt", "")

# ── Prompt (v3 — approved 2026-07-17) ────────────────────────────────────
KEYFRAME_PROMPT = (
    "The first image is the structural and compositional reference. "
    "Treat it as a locked frame. "
    "Copy its exact body orientation, shoulder angle, head turn, crop, subject scale, "
    "camera distance, and background without modification. "
    "Only replace the person's identity and outfit — nothing else changes. "
    "Do not repose the subject. "
    "Do not center the face or create a symmetric portrait. "
    "Do not add fashion shoot energy, editorial stiffness, or studio lighting. "
    "This is a cinematic moment, not a portrait session."
    "\n\n"
    "CHARACTER IDENTITY: "
    "Young woman, mid-twenties, slender tall build. "
    "Deep-set almond-shaped eyes, strong defined brows, high cheekbones, straight nose, full lips. "
    "Light olive skin tone. "
    "Expression: quiet and soft — as if she is mid-movement and has just naturally glanced back, "
    "not posing for the camera. "
    "The feeling is private, unhurried, and slightly caught off-guard. "
    "Not severe, not intense, not editorial. A real, human moment."
    "\n\n"
    "LOOK — THE TAILORED SELF: "
    "Charcoal tailored cropped blazer, white cotton shirt, muted olive tie, "
    "wide faded blue denim trousers with clean break at ankle, "
    "polished black leather oxford shoes. "
    "Hair: loose natural dark hair, centre part, slightly undone texture, falls to shoulders. "
    "Makeup: natural polished, lightly sculpted skin, defined brows, "
    "subtle brown eyeshadow, understated nude lips. "
    "Silhouette: relaxed broad-shoulder tailored, wide trouser leg, cropped blazer waist."
    "\n\n"
    "FRAMING AND POSE — copy from first image exactly: "
    "Over-shoulder composition. The subject's back and shoulder dominate the frame. "
    "Head turned back over the shoulder — the same angle and rotation as the source frame, "
    "no more, no less. "
    "Do not pull the face further toward camera than the source frame shows. "
    "Do not straighten the spine or square the shoulders toward the lens. "
    "Preserve the asymmetry, the partial back view, and the crop from the source frame."
    "\n\n"
    "SCENE — preserve from source frame exactly: "
    "Seaside sunset. Beach, ocean horizon, warm golden sunset light, coastal atmosphere. "
    "Do not alter the background, lighting direction, or atmosphere."
    "\n\n"
    "GUARD: "
    "Generate only one visible character. "
    "No extra people, background figures, duplicated bodies, or additional faces. "
    "Do not copy the source subject's clothing, hairstyle, or styling. "
    "Camera: low-intensity push_in, stable, cinematic."
)

# ── Guard check ────────────────────────────────────────────────────────────
ok, violations = check_forbidden(KEYFRAME_PROMPT, look_id)
if not ok:
    print(f"BLOCKED by forbidden-word guard: {violations}")
    print("Fix the prompt before generating.")
    sys.exit(1)
print(f"[guard] CLEAN — no forbidden terms")

# ── Image inputs (v2 — source frame FIRST) ────────────────────────────────
IMAGES = [
    ROOT / "outputs/ref_panels/shot_001_best.png",                    # [0] source_frame_structural (PRIMARY)
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
out_path = out_dir / "shot_001_keyframe_look3_preserve_scene_test.png"

print(f"\n[output] {out_path}")
print(f"[prompt] {len(KEYFRAME_PROMPT)} chars")
print(f"[model]  gpt-image-1 / images.edit / 1024x1536 / medium")
print(f"[look]   {look_id}")
print(f"[scene]  preserve_reference_scene\n")

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
print(f"\nDone. No other shots generated. No Kling called.")
