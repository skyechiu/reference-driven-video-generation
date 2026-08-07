"""
generate_shot003.py — run from the project root to generate the shot_003 keyframe.

Usage:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 generate_shot003.py

What this does:
  - Uses a hardcoded prompt built for shot_003's actual framing:
    extreme low-angle close-up of lower legs and feet walking along wet beach sand
    at the shoreline — NO face, NO upper body, NO turning, NO smile in frame
  - Calls OpenAI images.edit with gpt-image-1, 1024x1536, medium quality
  - Passes 4 images in order:
      [0] shot_003_best.png      — source_frame_structural (PRIMARY STRUCTURAL BASE)
      [1] look3_closeup.png      — face / identity reference (identity anchor only)
      [2] look3_front.png        — look front body reference (outfit detail only)
      [3] look3_sheet.png        — look sheet / overview
  - Saves result to:
      outputs/runs/live_test_03_4shots/keyframes/
      shot_003_keyframe_look3_preserve_scene.png

Constraints enforced:
  - Only shot_003 — no other shots
  - No Kling call
  - No repair
  - Forbidden-word guard scans KEYFRAME_PROMPT only (not NEGATIVE_PROMPT)

Prompt strategy (v2 — corrected after source frame inspection):
  - Source frame confirmed: extreme low angle, camera at ground level
  - Only lower legs (mid-calf down) and feet visible — face completely out of frame
  - Source subject: bare feet, white flowy fabric at ankle
  - IP character replacement: wide-leg denim trouser hem + black leather oxford shoes
  - Scene: wet sand, shallow water at shoreline, sunset light on sand
  - No face, no upper body, no smile — lower-body detail shot only
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

# ── Load state ─────────────────────────────────────────────────────────────
state   = json.loads((ROOT / "project_state.json").read_text())
cfg     = state.get("config", {})
run_id  = cfg.get("run_id", "live_test_03_4shots")
look_id = cfg.get("selected_look_id", "look_3_tailored_self")
shot    = next((s for s in state["shots"] if s["shot_id"] == "shot_003"), None)

if shot is None:
    print("ERROR: shot_003 not found in project_state.json")
    sys.exit(1)

# ── Prompt (v2 — corrected: low-angle feet/lower-leg close-up only) ──────
KEYFRAME_PROMPT = (
    "The first image is the structural and compositional reference. "
    "Treat it as a locked frame. "
    "Copy its exact camera angle, crop, ground perspective, foot position, "
    "and background without modification. "
    "Only replace the lower legs and footwear — nothing else changes. "
    "Do not add or show any part of the body above mid-calf. "
    "Do not show a face, head, torso, arms, or upper body. "
    "This is a low-angle close-up of lower legs and feet walking along wet beach sand — nothing more."
    "\n\n"
    "WHAT IS VISIBLE IN THIS FRAME: "
    "Lower legs from mid-calf down. Feet and footwear only. "
    "The camera is at ground level, extremely low angle, looking along the wet sand. "
    "The legs are mid-stride — one foot forward, weight in motion. "
    "Wet sand and shallow water at the shoreline fill the foreground and background. "
    "Footprints in the wet sand behind the feet. "
    "Sunset light reflects off the wet sand surface."
    "\n\n"
    "LOOK — LOWER BODY ONLY (what replaces the source): "
    "Wide faded blue denim trousers — the trouser hem and lower leg only, "
    "with the clean break at the ankle just visible. "
    "Black leather oxford shoes on wet sand at the water's edge. "
    "The trouser fabric drapes naturally over the shoe — slight natural wrinkle at the break. "
    "Do not copy the source subject's white fabric or bare feet. "
    "Replace only with the denim trouser hem and black oxford shoes."
    "\n\n"
    "FRAMING — copy from first image exactly: "
    "Extreme low angle, camera nearly at sand level. "
    "The feet and lower legs are the entire subject of the frame — no upper body visible. "
    "The walking stride is active — mid-step, not standing still. "
    "Preserve the exact ground perspective, foot scale, and position in frame from the source. "
    "Wet sand, shallow water lapping at the shoreline, and footprints behind — all preserved."
    "\n\n"
    "SCENE — preserve from source frame exactly: "
    "Beach at sunset. Wet sand, shallow water at the shoreline, natural warm sunset light "
    "reflecting off the sand surface. Coastal atmosphere. "
    "Do not alter the ground texture, water position, lighting direction, or atmosphere. "
    "Natural imperfect lighting — not a poster-perfect or oversaturated sunset."
    "\n\n"
    "REALISM — this must look like a real video frame: "
    "Very subtle motion softness in the moving foot and lower leg consistent with walking. "
    "Natural sand texture, wet surface reflections, and water detail. "
    "Use subtle natural video-frame softness and imperfect detail, rather than hyper-sharp studio clarity. "
    "Preserve the original reference frame texture and natural imperfections. "
    "Keep the image grounded and documentary-like. "
    "It should look like the original reference frame was edited, not like a newly generated image."
    "\n\n"
    "AVOID: "
    "Do not show any face, head, torso, arms, smile, or upper body. "
    "Do not turn this into a full-body shot or add body parts not in the source frame. "
    "Avoid overly clean AI lighting, plastic fabric, perfect poster composition, "
    "hyper-polished colors, and commercial stock-photo aesthetics. "
    "Not a generated advertisement. Not a stock photo."
    "\n\n"
    "GUARD: "
    "Only one person's lower legs and feet in frame. "
    "No other people, no extra legs, no duplicated feet. "
    "Do not copy the source subject's white fabric or bare feet. "
    "Keep the selected look's denim and oxford shoes only. "
    "Camera: very low to the ground, close to sand level, with slight natural handheld instability consistent with a real moving video frame."
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
    ROOT / "outputs/ref_panels/shot_003_best.png",                    # [0] source_frame_structural (PRIMARY)
    ROOT / "assets/looks/look_3_tailored_self/look3_front.png",      # [1] lower-body outfit reference
    ROOT / "assets/looks/look_3_tailored_self/look3_sheet.png",      # [2] look overview
    ROOT / "assets/looks/look_3_tailored_self/look3_closeup.png",    # [3] weak identity anchor only (face not in frame)
]
SLOTS = [
    "source_frame_structural (PRIMARY)",
    "front_full_body (lower-body outfit reference)",
    "look_overview",
    "face_closeup (weak anchor — face not in frame)",
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
out_path = out_dir / "shot_003_keyframe_look3_preserve_scene.png"

print(f"\n[output]          {out_path}")
print(f"[keyframe_prompt] {len(KEYFRAME_PROMPT)} chars")
print(f"[negative_prompt] {len(NEGATIVE_PROMPT)} chars (reference only — not passed to API)")
print(f"[model]           gpt-image-1 / images.edit / 1024x1536 / medium")
print(f"[look]            {look_id}")
print(f"[shot]            shot_003 only — no other shots")
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
print(f"\nDone. shot_003 only. No other shots generated. No Kling called.")
