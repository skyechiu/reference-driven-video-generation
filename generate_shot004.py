"""
generate_shot004.py — run from the project root to generate the shot_004 keyframe.

Usage:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 generate_shot004.py

What this does:
  - Uses a hardcoded prompt built for shot_004's actual framing:
    wide shot, full body, walking sideways along beach, three-quarter profile,
    face in partial profile looking down softly, one foot raised mid-stride,
    large sun on frame-left, rocky headland on frame-right
  - Calls OpenAI images.edit with gpt-image-1, 1024x1536, medium quality
  - Passes 4 images in order:
      [0] shot_004_best.png      — source_frame_structural (PRIMARY STRUCTURAL BASE)
      [1] look3_closeup.png      — face / identity reference (face IS visible in this shot)
      [2] look3_front.png        — look front body reference
      [3] look3_sheet.png        — look sheet / overview
  - Saves result to:
      outputs/runs/live_test_03_4shots/keyframes/
      shot_004_keyframe_look3_preserve_scene.png

Constraints enforced:
  - Only shot_004 — no other shots
  - No Kling call
  - No repair
  - Forbidden-word guard scans KEYFRAME_PROMPT only (not NEGATIVE_PROMPT)

Prompt strategy (v1):
  - Source frame is [0] — primary structural anchor
  - shot_004: wide, full body, walking sideways along shoreline, three-quarter profile
  - Face visible but angled down — soft private expression, not looking at camera
  - Right hand holds fabric hem; one foot raised mid-stride
  - Background: large sun on left, ocean, rocky headland on right
  - Look3 tailored outfit replaces source white sheer dress
  - Natural video-frame realism throughout
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

# ── Load state ─────────────────────────────────────────────────────────────
state   = json.loads((ROOT / "project_state.json").read_text())
cfg     = state.get("config", {})
run_id  = cfg.get("run_id", "live_test_03_4shots")
look_id = cfg.get("selected_look_id", "look_3_tailored_self")
shot    = next((s for s in state["shots"] if s["shot_id"] == "shot_004"), None)

if shot is None:
    print("ERROR: shot_004 not found in project_state.json")
    sys.exit(1)

# ── Prompt (v1 — wide / full body / sideways walk / three-quarter profile) ─
KEYFRAME_PROMPT = (
    "The first image is the structural and compositional reference. "
    "Treat it as a locked frame. "
    "Copy its exact body position, walking pose, crop, subject scale, "
    "camera distance, framing, and background without modification. "
    "Only replace the person's identity and outfit — nothing else changes. "
    "Do not repose the subject. "
    "This is a wide video frame of a figure walking sideways along the beach shoreline, "
    "not a posed portrait and not a face-forward shot."
    "\n\n"
    "CHARACTER IDENTITY: "
    "Young woman, mid-twenties, slender tall build. "
    "Deep-set almond-shaped eyes, strong defined brows, high cheekbones, straight nose, full lips. "
    "Light olive skin tone. "
    "Expression: soft and private — a quiet downward gaze, head slightly inclined, "
    "as if in her own world mid-movement. Not looking at the camera. "
    "The feeling is unhurried and natural, not posed."
    "\n\n"
    "LOOK — THE TAILORED SELF: Study the second image carefully — it shows the exact outfit. "
    "BLAZER: Cropped charcoal blazer. Charcoal means dark grey, NOT black. "
    "The hemline ends at the natural waist — very short, not hip-length, not mid-thigh, not full-length. "
    "The shoulders are broad and slightly structured but the overall fit is relaxed, "
    "slightly oversized, deconstructed — NOT a fitted corporate suit jacket, NOT a formal blazer. "
    "TIE: A muted olive tie is clearly visible at the collar — dusty earthy army-green, "
    "NOT black, NOT dark navy, NOT a school uniform tie. The tie should be distinctly visible "
    "as an olive/khaki tone against the white shirt. "
    "SHIRT: White cotton shirt visible at the collar above the blazer lapels. "
    "TROUSERS: Wide faded blue denim trousers. These are jeans — faded mid-blue wash. "
    "The leg cut is distinctly wide and relaxed — the trouser leg should visibly drape and flow, "
    "with a clean break at the ankle. NOT slim fit, NOT straight leg, NOT cropped, "
    "NOT office trousers, NOT suit trousers. The wide leg is the most important visual feature. "
    "SHOES: Black leather oxford shoes — structured, low heel, clean sole. "
    "HAIR: Loose natural dark hair, falls to shoulders, moving slightly with the walk. "
    "SILHOUETTE SUMMARY: Cropped waist-length charcoal blazer over white shirt with olive tie, "
    "topped with wide relaxed denim trousers breaking at the ankle, and black oxfords. "
    "Runway-relaxed tailoring — not a uniform, not office wear, not a corporate look. "
    "Natural fabric drape and wrinkles in both blazer and trousers. "
    "Do not copy the source subject's sheer white fabric or bare feet."
    "\n\n"
    "FRAMING AND POSE — copy from first image exactly: "
    "Wide shot. Full body from head to feet. "
    "Subject is walking sideways along the beach shoreline, moving toward frame-left. "
    "Body is in three-quarter profile — angled sideways to the camera, not facing it. "
    "Face is in partial profile, angled slightly downward toward the ground. "
    "One foot is raised mid-stride — active walking motion, not a static stance. "
    "Arms and hands remain natural and consistent with the walking motion. "
    "Do not invent any fabric-holding gesture that does not make sense for the tailored outfit. "
    "Subject is positioned in the right-centre of the frame. "
    "Preserve the exact body scale, walking angle, and position in frame from the source."
    "\n\n"
    "SCENE — preserve from source frame exactly: "
    "Beach at sunset. Sandy shoreline with shallow water. "
    "Large bright sun low on the horizon on the left side of the frame, "
    "with a sun reflection path across the ocean surface. "
    "Rocky headland or cliff visible in the far right background. "
    "Warm amber-orange sunset atmosphere. "
    "Do not alter the background layout, sun position, or lighting direction. "
    "Natural imperfect lighting — not a poster-perfect or oversaturated sunset."
    "\n\n"
    "REALISM — this must look like a real video frame: "
    "Very subtle motion softness in the raised foot and moving hair, consistent with walking. "
    "The overall figure, outfit silhouette, and scene should remain readable and coherent. "
    "Keep the image natural and grounded, with subtle real video-frame softness and mild natural imperfections. "
    "Preserve the feeling of an extracted reference frame rather than a polished promotional image."
    "\n\n"
    "AVOID: "
    "Do not turn the subject to face the camera. "
    "Do not create a symmetrical portrait or front-facing composition. "
    "Do not add urban rooftop, city skyline, studio lighting, or studio backdrop. "
    "Avoid overly clean AI lighting, overly smooth skin, plastic fabric, "
    "perfect poster composition, hyper-polished colors, and commercial stock-photo aesthetics. "
    "Not a generated advertisement. Not a stock photo. "
    "Do not dress the character in a generic black blazer, full-length blazer, office uniform, "
    "school uniform, corporate suit jacket, black uniform tie, slim trousers, "
    "straight-leg office trousers, or formal business wear of any kind."
    "\n\n"
    "GUARD: "
    "Generate only one visible character. "
    "No extra people, background figures, duplicated bodies, or additional faces. "
    "Do not copy the source subject's sheer white fabric, bare feet, or styling. "
    "Keep the selected tailored look only. "
    "Camera: handheld, low-intensity, stable, eye level."
)

# ── Negative prompt (banned terms — reference/logging only; NOT passed to API) ──
# Guard scans only KEYFRAME_PROMPT above, never this string.
NEGATIVE_PROMPT = (
    "different face, changed identity, distorted face, wrong person, "
    "extra limbs, unstable hands, distorted proportions, "
    "multiple people, extra person, second face, background characters, crowd, duplicated body, "
    "bride, bridal, wedding, wedding dress, bridal gown, veil, cathedral veil, wedding veil, "
    "white beach dress, copied source outfit, same outfit as source, "
    "wrong outfit, wrong hairstyle, different identity, generic woman, random bride, "
    "front-facing portrait, symmetric portrait, editorial fashion pose, "
    "urban rooftop, city skyline, studio lighting, studio backdrop, "
    "generic business suit, school uniform, office uniform, formal office wear, "
    "black tie, black uniform tie, slim trousers, straight trousers, corporate blazer, "
    "full-length blazer, fitted suit jacket, black blazer"
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
    ROOT / "outputs/ref_panels/shot_004_best.png",                    # [0] source_frame_structural (PRIMARY)
    ROOT / "assets/looks/look_3_tailored_self/look3_front.png",      # [1] outfit / full body look reference (PRIMARY LOOK)
    ROOT / "assets/looks/look_3_tailored_self/look3_sheet.png",      # [2] look overview
    ROOT / "assets/looks/look_3_tailored_self/look3_closeup.png",    # [3] face reference
]
SLOTS = [
    "source_frame_structural (PRIMARY)",
    "front_full_body (PRIMARY LOOK REFERENCE)",
    "look_overview",
    "face_closeup",
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
out_path = out_dir / "shot_004_keyframe_look3_preserve_scene.png"

print(f"\n[output]          {out_path}")
print(f"[keyframe_prompt] {len(KEYFRAME_PROMPT)} chars")
print(f"[negative_prompt] {len(NEGATIVE_PROMPT)} chars (reference only — not passed to API)")
print(f"[model]           gpt-image-1 / images.edit / 1024x1536 / medium")
print(f"[look]            {look_id}")
print(f"[shot]            shot_004 only — no other shots")
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
print(f"\nDone. shot_004 only. No other shots generated. No Kling called.")
