"""
regen_shot001_004_v2.py
Regenerate shot_001 (v2) and shot_004 (v3) using the new identity-first slot logic.

Slot order for both (face_visible mode):
  [0] look3_identity_anchor_street.png  — PRIMARY identity in street lighting
  [1] scene_ref                         — composition / architecture
  [2] look3_front.png                   — outfit / body
  [3] look3_profile_crop.png            — profile / 3-quarter angle support

Outputs:
  outputs/runs/live_test_04_street_look3/keyframes/shot_001_keyframe_look3_street_v2.png
  outputs/runs/live_test_04_street_look3/keyframes/shot_004_keyframe_look3_street_v3.png
  outputs/runs/live_test_04_street_look3/keyframes/street_shot001v2_004v3_comparison.png

Run:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 regen_shot001_004_v2.py
"""

import base64, io, os, sys, time
from pathlib import Path

ROOT = Path(__file__).parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set"); sys.exit(1)

from openai import OpenAI
from PIL import Image as PILImage, ImageDraw, ImageFont

client = OpenAI(api_key=OPENAI_API_KEY, max_retries=1)

# ── Paths ─────────────────────────────────────────────────────────────────────
LOOK_DIR    = ROOT / "assets/looks/look_3_tailored_self"
SCENE_REF   = ROOT / "assets/scenes/built_in/scene_02_modern_street/references"
KF_DIR      = ROOT / "outputs/runs/live_test_04_street_look3/keyframes"
KF_DIR.mkdir(parents=True, exist_ok=True)

IDENTITY_ANCHOR = LOOK_DIR / "look3_identity_anchor_street.png"
PROFILE_CROP    = LOOK_DIR / "look3_profile_crop.png"
LOOK_FRONT      = LOOK_DIR / "look3_front.png"
LOOK_CLOSEUP    = LOOK_DIR / "look3_closeup.png"
BEHIND_CROP     = LOOK_DIR / "_crop_behind_3q_figure.png"

# Verify required assets
for p in [IDENTITY_ANCHOR, PROFILE_CROP, LOOK_FRONT, LOOK_CLOSEUP,
          SCENE_REF / "main_scene_board_16x9.jpg",
          SCENE_REF / "establishing_view_16x9.png",
          SCENE_REF / "side_view_16x9.png"]:
    if not p.exists():
        print(f"ERROR: missing asset: {p}"); sys.exit(1)

print("[assets] all reference assets verified")
print(f"  identity_anchor : {IDENTITY_ANCHOR.stat().st_size // 1024} KB")
print(f"  profile_crop    : {PROFILE_CROP.stat().st_size // 1024} KB")

# ── Shared prompt blocks ──────────────────────────────────────────────────────

_ROLE_REF_FACE_VISIBLE = (
    "ROLE OF REFERENCE IMAGES:\n"
    "  Image 1 — identity_anchor_street.png: PRIMARY IDENTITY REFERENCE.\n"
    "    Approved identity anchor — the same woman in the same street environment.\n"
    "    Her face, bone structure, and presence define the target identity.\n"
    "    This is the most important input. Do not generate a different woman.\n"
    "  Image 2 — street scene reference: COMPOSITION AND STRUCTURE ONLY.\n"
    "    Defines camera angle, street architecture, background layout, and lighting quality.\n"
    "    Does NOT define the character's face or outfit.\n"
    "  Image 3 — look3_front.png: OUTFIT AND BODY REFERENCE.\n"
    "    Confirms the exact Look 3 outfit. Copy from this image — do not invent variations.\n"
    "  Image 4 — look3_profile_crop.png: PROFILE / ANGLE SUPPORT.\n"
    "    Same woman in 3-quarter profile — reinforces nose bridge angle, brow arch, jawline,\n"
    "    cheekbone structure, and hairline from the side.\n"
)

_ROLE_REF_BACK_VIEW = (
    "ROLE OF REFERENCE IMAGES:\n"
    "  Image 1 — street scene reference: PRIMARY COMPOSITION REFERENCE.\n"
    "    Defines camera angle, street depth/perspective, architecture, and background layout.\n"
    "    This is a back-view shot — composition and depth are the primary concern.\n"
    "  Image 2 — identity_anchor_street.png: SILHOUETTE AND CONTINUITY REFERENCE.\n"
    "    Same woman in the same street. Use for hair silhouette, body proportion, outfit continuity.\n"
    "    Back of the head and hair must match.\n"
    "  Image 3 — look3_front.png: OUTFIT SILHOUETTE REFERENCE.\n"
    "    Confirms the exact outfit — pay attention to the back of the blazer (cropped hem)\n"
    "    and wide denim trouser leg shape, which read clearly in back view.\n"
    "  Image 4 — back-angle crop: SUPPLEMENTAL BACK-VIEW REFERENCE.\n"
    "    Shows the back/3-quarter silhouette. Confirms hair, head, and outfit from this angle.\n"
)

_CORE_INSTRUCTION = (
    "CORE INSTRUCTION:\n"
    "Generate the exact same woman as shown in Image 1, wearing the exact same Look 3 outfit\n"
    "as shown in Image 3, placed into the scene and composition defined by Image 2.\n"
    "Do not generate a similar woman. Do not average the references into a generic face.\n"
    "Do not simplify or soften the facial structure.\n"
    "This must remain the same identifiable person across all shots.\n"
)

_IDENTITY_LOCK = (
    "IDENTITY LOCK:\n"
    "The visible character must be the exact same woman shown in Image 1 (identity anchor).\n"
    "Preserve precisely:\n"
    "  — strong defined brows, horizontal arch\n"
    "  — deep-set almond-shaped eyes\n"
    "  — high pronounced cheekbones\n"
    "  — straight narrow nose bridge\n"
    "  — full lips\n"
    "  — defined jawline and chin\n"
    "  — light olive skin tone\n"
    "  — centre-parted dark hair falling to shoulders\n"
    "The character must look like the exact woman in Image 1, not a generic elegant brunette.\n"
    "If there is any conflict between references, prioritise:\n"
    "  1. Image 1 for identity\n"
    "  2. Image 3 for outfit\n"
    "  3. Image 2 for scene and framing\n"
    "  4. Image 4 for side-angle facial continuity\n"
)

_LOOK_LOCK = (
    "LOOK LOCK — LOOK 3 (The Tailored Self):\n"
    "Copy the exact outfit from Image 3. Do not invent variations.\n"
    "  BLAZER: Cropped charcoal blazer. Charcoal = dark grey, NOT black. Hemline at natural waist.\n"
    "    Relaxed broad-shoulder silhouette, slightly oversized, deconstructed.\n"
    "    NOT a fitted corporate suit jacket, NOT a full-length blazer, NOT black.\n"
    "  TIE: Muted olive tie — dusty earthy army-green. NOT black, NOT dark navy.\n"
    "  SHIRT: White cotton shirt, collar visible above the blazer lapels.\n"
    "  TROUSERS: Wide faded blue denim. Distinctly wide and relaxed — drapes and flows.\n"
    "    NOT slim fit, NOT straight leg, NOT office trousers. Wide leg is the key visual.\n"
    "  SHOES: Black leather oxford shoes — structured, low heel.\n"
    "  HAIR: Loose natural dark hair, falls to shoulders.\n"
    "Do NOT convert the outfit into: black business suit, corporate uniform, school uniform,\n"
    "slim trousers, straight-leg office pants, a full-length blazer.\n"
)

_SCENE_DETAIL = (
    "Quiet Parisian cobblestone street. Limestone Haussmann-style facades with shuttered windows\n"
    "and wrought iron balcony railings. Grey irregular cobblestone paving. Black wrought iron\n"
    "bollards along the kerb. Gas-style street lamp. Soft diffused natural daylight — cool-warm\n"
    "neutral, no harsh shadows, overcast or early-morning quality. Empty and serene.\n"
)

_REALISM = (
    "REALISM:\n"
    "This should look like a real photographic / cinematic frame, not a fashion catalogue image.\n"
    "Subtle natural motion softness consistent with walking. Slight film-grain texture.\n"
    "Avoid plastic skin, AI-smoothed fabric, over-clean lighting, commercial stock-photo styling.\n"
)

_GUARD = (
    "GUARD:\n"
    "Generate only one visible character. No extra people, no duplicated faces, no crowd.\n"
    "No outfit drift. No identity drift. No text, watermarks, or graphic overlays.\n"
)

# ── Shot configs ──────────────────────────────────────────────────────────────
SHOTS_TO_REGEN = [
    {
        "shot_id":   "shot_001",
        "out_path":  KF_DIR / "shot_001_keyframe_look3_street_v2.png",
        "scene_ref": SCENE_REF / "main_scene_board_16x9.jpg",
        "slot_notes": "identity_anchor[0] · main_scene[1] · look_front[2] · profile_crop[3]",
        "PROMPT": (
            _ROLE_REF_FACE_VISIBLE
            + "\n"
            + _CORE_INSTRUCTION
            + "\n"
            + _IDENTITY_LOCK
            + "\n"
            + _LOOK_LOCK
            + "\n"
            "SHOT — shot_001: Medium over-shoulder, face partially visible in natural glance.\n"
            "\n"
            "FRAMING:\n"
            "Medium over-shoulder shot. Camera is behind and slightly to the right of the character,\n"
            "shooting over her right shoulder into the cobblestone street ahead.\n"
            "Upper body visible from approximately mid-back upward.\n"
            "She turns her head slightly in a natural, unhurried glance — as if noticing something in passing.\n"
            "Not a dramatic turn. Not looking at the camera.\n"
            "The side of her face and partial profile are just visible in this glance.\n"
            "The visible face and profile must match the exact same woman from Image 1 and Image 4.\n"
            "Candid and observational — a quiet moment of street movement.\n"
            "\n"
            "EXPRESSION: Quiet, private, natural. A soft unposed glance. Not looking at camera.\n"
            "\n"
            "SCENE:\n"
            + _SCENE_DETAIL
            + "\n"
            + _REALISM
            + "\n"
            + _GUARD
        ),
    },
    {
        "shot_id":   "shot_004",
        "out_path":  KF_DIR / "shot_004_keyframe_look3_street_v3.png",
        "scene_ref": SCENE_REF / "side_view_16x9.png",
        "slot_notes": "identity_anchor[0] · side_view[1] · look_front[2] · profile_crop[3]",
        "PROMPT": (
            _ROLE_REF_FACE_VISIBLE
            + "\n"
            + _CORE_INSTRUCTION
            + "\n"
            + _IDENTITY_LOCK
            + "\n"
            + _LOOK_LOCK
            + "\n"
            "SHOT — shot_004: Wide side-profile walk along Haussmann facade.\n"
            "\n"
            "FRAMING:\n"
            "Wide to medium-wide side-profile shot. Camera at eye level, facing along the building wall.\n"
            "The character walks from left to right — body in true side profile, not facing the camera.\n"
            "Full body visible from head to feet. One foot slightly raised mid-stride, natural walking motion.\n"
            "Head inclined slightly downward — soft private gaze toward the cobblestone, not looking at camera.\n"
            "\n"
            "PROFILE IDENTITY:\n"
            "The profile of her face must match Image 1 (identity anchor) and Image 4 (profile crop).\n"
            "Same nose bridge angle, brow projection, lip shape, and jaw structure from the side.\n"
            "Do not generate a different person's profile.\n"
            "\n"
            "The limestone building facade fills the background behind the character.\n"
            "Wrought iron railings visible in the near foreground.\n"
            "Arms and hands relaxed at sides — natural walking movement.\n"
            "\n"
            "SCENE:\n"
            + _SCENE_DETAIL
            + "\n"
            + _REALISM
            + "\n"
            "GUARD:\n"
            "Do not turn the subject to face the camera.\n"
            "Do not create a symmetrical portrait or front-facing composition.\n"
            "No extra people, no crowd. No outfit drift. No identity drift.\n"
            "No text, watermarks, or graphic overlays.\n"
        ),
    },
    # ── shot_002: back_view ────────────────────────────────────────────────
    {
        "shot_id":   "shot_002",
        "slot_mode": "back_view",
        "out_path":  KF_DIR / "shot_002_keyframe_look3_street_v4.png",
        "scene_ref": SCENE_REF / "establishing_view_16x9.png",
        "slot_notes": "scene[0] · identity_anchor[1] · look_front[2] · behind_crop[3]",
        "PROMPT": (
            _ROLE_REF_BACK_VIEW
            + "\n"
            "CORE INSTRUCTION (back view):\n"
            "Generate the same woman as Image 2 (identity anchor), now walking away from camera.\n"
            "No face visible. Preserve her silhouette, hair, and outfit from the anchor.\n"
            "Composition is driven by Image 1 (street depth and perspective).\n"
            "\n"
            + _LOOK_LOCK
            + "\n"
            "SHOT — shot_002: Wide full-body walk away, cobblestone street depth.\n"
            "\n"
            "FRAMING:\n"
            "Wide full-body shot. Camera is behind the character at eye level.\n"
            "She walks away from camera toward the vanishing point of the narrow street.\n"
            "Full body from head to feet — do not crop at shoes.\n"
            "Back of the cropped charcoal blazer visible. Wide faded denim trouser legs prominent —\n"
            "the leg width should read clearly against the narrow cobblestone street.\n"
            "Black oxford shoes stepping across the cobblestone.\n"
            "Loose dark hair moving slightly with the walking stride.\n"
            "Natural unhurried walking stride. Arms relaxed at sides.\n"
            "Character centered in frame, street perspective stretching ahead.\n"
            "\n"
            "HAIR (back view): Centre-parted dark hair, falls to mid-back/shoulder length.\n"
            "The clean dark centre part and hair silhouette are the key identity markers from this angle.\n"
            "\n"
            "SCENE:\n"
            + _SCENE_DETAIL
            + "\n"
            + _REALISM
            + "\n"
            "GUARD:\n"
            "Do not turn the character toward the camera. Keep back-view throughout.\n"
            "No face visible from the front. No extra people, no crowd. No outfit drift.\n"
            "No text, watermarks, or graphic overlays.\n"
        ),
    },
]

# ── Generate ──────────────────────────────────────────────────────────────────
results = []

for i, s in enumerate(SHOTS_TO_REGEN):
    sid       = s["shot_id"]
    out_path  = s["out_path"]
    slot_mode = s.get("slot_mode", "face_visible")

    # Per-mode slot logic and quality settings
    if slot_mode == "face_visible":
        images_in      = [IDENTITY_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT, PROFILE_CROP]
        slot_notes     = "identity_anchor[0] · closeup[1] · look_front[2] · profile_crop[3]  [scene→text]"
        quality_val    = "high"
        fidelity_val   = "high"
    elif slot_mode == "back_view":
        behind_ref     = BEHIND_CROP if BEHIND_CROP.exists() else PROFILE_CROP
        images_in      = [s["scene_ref"], IDENTITY_ANCHOR, LOOK_FRONT, behind_ref]
        slot_notes     = f"scene[0] · identity_anchor[1] · look_front[2] · {behind_ref.name}[3]"
        quality_val    = "medium"
        fidelity_val   = "high"
    else:
        images_in      = [IDENTITY_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT, PROFILE_CROP]
        slot_notes     = "fallback face_visible slots"
        quality_val    = "high"
        fidelity_val   = "high"

    print(f"\n{'='*60}")
    print(f"[{i+1}/{len(SHOTS_TO_REGEN)}] Generating {sid} → {out_path.name}")
    print(f"  slot_mode      : {slot_mode}")
    print(f"  slots          : {slot_notes}")
    print(f"  quality        : {quality_val}")
    print(f"  input_fidelity : {fidelity_val}")
    for idx, p in enumerate(images_in):
        print(f"  img[{idx}]       : {p.name}")
    print(f"  prompt         : {len(s['PROMPT'])} chars")

    handles = []
    try:
        for p in images_in:
            handles.append(open(p, "rb"))
        response = client.images.edit(
            model="gpt-image-1",
            image=handles,
            prompt=s["PROMPT"],
            size="1024x1536",
            quality=quality_val,
            input_fidelity=fidelity_val,
            n=1,
        )
        img_data = base64.b64decode(response.data[0].b64_json)
        out_path.write_bytes(img_data)
        size_kb = len(img_data) // 1024
        print(f"  ✓ SAVED: {out_path.name}  ({size_kb} KB)")
        results.append({"sid": sid, "path": out_path, "ok": True, "size_kb": size_kb})
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        results.append({"sid": sid, "path": out_path, "ok": False})
    finally:
        for h in handles:
            h.close()

    if i < len(SHOTS_TO_REGEN) - 1:
        print("  (waiting 3s before next call...)")
        time.sleep(3)

# ── Comparison sheet ──────────────────────────────────────────────────────────
# Layout: 3 columns × 2 rows
# Row 0 (old): shot_001_v1 | shot_002_v3 | shot_004_v2
# Row 1 (new): shot_001_v2 | shot_002_v4 | shot_004_v3
print("\n[comparison] building comparison sheet...")

BG = (18, 18, 18); FG = (230, 230, 230); ACC = (100, 200, 120)

def _font(sz: int):
    for p in ["/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()

THUMB_W = 280
PAD     = 14
LABEL_H = 34

panels = [
    # (label, path)
    ("shot_001 · v1 (old)", KF_DIR / "shot_001_keyframe_look3_street.png"),
    ("shot_002 · v3 (old)", KF_DIR / "shot_002_keyframe_look3_street_v3.png"),
    ("shot_004 · v2 (old)", KF_DIR / "shot_004_keyframe_look3_street_v2.png"),
    ("shot_001 · v2 (NEW)", KF_DIR / "shot_001_keyframe_look3_street_v2.png"),
    ("shot_002 · v4 (NEW)", KF_DIR / "shot_002_keyframe_look3_street_v4.png"),
    ("shot_004 · v3 (NEW)", KF_DIR / "shot_004_keyframe_look3_street_v3.png"),
]

thumbs = []
for label, path in panels:
    if path.exists():
        img = PILImage.open(path).convert("RGB")
        h = int(THUMB_W * img.height / img.width)
        thumbs.append((label, img.resize((THUMB_W, h), PILImage.LANCZOS)))
    else:
        thumbs.append((label, None))

max_h  = max(t[1].height if t[1] else 120 for t in thumbs)
n_cols = 3
n_rows = (len(thumbs) + n_cols - 1) // n_cols

HEADER_H = 36
cw = n_cols * (THUMB_W + PAD) + PAD
ch = HEADER_H + n_rows * (LABEL_H + max_h + PAD) + PAD

canvas = PILImage.new("RGB", (cw, ch), BG)
draw   = ImageDraw.Draw(canvas)
draw.text((PAD, 8), "REGEN: shot_001 v2 · shot_002 v4 · shot_004 v3  ·  new anchor (high+high)",
          fill=ACC, font=_font(13))

for idx, (label, th) in enumerate(thumbs):
    col = idx % n_cols
    row = idx // n_cols
    x   = PAD + col * (THUMB_W + PAD)
    y   = HEADER_H + row * (LABEL_H + max_h + PAD)

    draw.rectangle([x, y, x + THUMB_W, y + LABEL_H - 4], fill=(35, 35, 45))
    draw.text((x + 8, y + 8), label, fill=FG, font=_font(16))

    if th:
        canvas.paste(th, (x, y + LABEL_H))
    else:
        draw.rectangle([x, y + LABEL_H, x + THUMB_W, y + LABEL_H + max_h], fill=(50, 30, 30))
        draw.text((x + 10, y + LABEL_H + 10), "MISSING", fill=(200, 80, 80), font=_font(18))

comp_path = KF_DIR / "street_regen_3shot_comparison.png"
canvas.save(str(comp_path))
print(f"  ✓ comparison sheet saved: {comp_path.name}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("REGEN COMPLETE")
print("=" * 60)
for r in results:
    status = f"✓  {r['size_kb']} KB" if r["ok"] else "✗  FAILED"
    print(f"  {r['sid']}: {r['path'].name}  [{status}]")
print(f"\n  comparison : {comp_path.name}")
print("=" * 60)
