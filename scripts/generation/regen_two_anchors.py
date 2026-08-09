"""
regen_two_anchors.py — Generate TWO separate Look 3 identity anchors for the
street-scene run, then STOP for human review.

Purpose
    Replace the single look3_identity_anchor_street.png with two purpose-built
    anchors so face-visible shots (shot_001, shot_004) get both a clean front
    identity and a clean profile identity:

      1. look3_identity_anchor_front.png
         - clear front-facing / slight three-quarter face
         - Look 3 outfit, neutral Parisian street lighting
         - PRIMARY facial identity reference

      2. look3_identity_anchor_profile.png
         - clean side-profile / three-quarter profile face
         - Look 3 outfit, neutral Parisian street lighting
         - side / profile consistency for shot_001 and shot_004

Identity inputs (per instruction)
    Use look3_closeup.png + look3_profile_crop.png as the identity references.
    Do NOT use look3_sheet as the primary identity reference.
    look3_front.png is used ONLY as a secondary OUTFIT reference (set
    INCLUDE_OUTFIT_REF = False to drop it and rely on the text LOOK LOCK only).
    The scene board is used ONLY for lighting mood — never for the face.

Settings
    quality="high", input_fidelity="high", size="1024x1536" for both anchors.

Behaviour
    Generates both anchors, builds a side-by-side contact sheet, prints a review
    message, and EXITS. This script never calls Kling and never touches keyframes.

Run
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 regen_two_anchors.py
"""

import base64, os, sys
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
# ── Flags ─────────────────────────────────────────────────────────────────────
ALLOW_OVERWRITE   = False   # True → regenerate anchors even if they already exist
                            # (both anchors already saved — False just rebuilds the contact sheet)
INCLUDE_OUTFIT_REF = True   # True → include look3_front.png as a secondary OUTFIT ref
                            # False → identity crops only; outfit from text LOOK LOCK

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    print("[env] loaded .env")
except ImportError:
    print("[env] python-dotenv not installed — using system env vars")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set"); sys.exit(1)

from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, max_retries=1)

# ── Paths ─────────────────────────────────────────────────────────────────────
LOOK_DIR  = ROOT / "assets/looks/look_3_tailored_self"
SCENE_REF = ROOT / "assets/scenes/built_in/scene_02_modern_street/references"
RUN_DIR   = ROOT / "outputs" / "runs" / "live_test_04_street_look3"
REVIEW_DIR = RUN_DIR / "anchor_review"
REVIEW_DIR.mkdir(parents=True, exist_ok=True)

CLOSEUP       = LOOK_DIR / "look3_closeup.png"       # front face identity
PROFILE_CROP  = LOOK_DIR / "look3_profile_crop.png"  # profile face identity
FRONT_OUTFIT  = LOOK_DIR / "look3_front.png"         # secondary outfit ref only
SCENE_BOARD   = SCENE_REF / "main_scene_board_16x9.jpg"

FRONT_ANCHOR   = LOOK_DIR / "look3_identity_anchor_front.png"
PROFILE_ANCHOR = LOOK_DIR / "look3_identity_anchor_profile.png"
CONTACT_SHEET  = REVIEW_DIR / "anchor_contact_sheet.png"

# ── Verify required assets ────────────────────────────────────────────────────
required = [CLOSEUP, PROFILE_CROP, SCENE_BOARD]
if INCLUDE_OUTFIT_REF:
    required.append(FRONT_OUTFIT)
for p in required:
    if not p.exists():
        print(f"ERROR: missing asset: {p}"); sys.exit(1)
print(f"[assets] {len(required)} reference assets verified")

# ── Forbidden-word guard (copyright / scope) ─────────────────────────────────
FORBIDDEN = [
    "bride", "bridal", "wedding", "wedding dress", "bridal gown",
    "cathedral veil", "white lace wedding gown",
    "copied source outfit", "same outfit as source",
]
def check_forbidden(prompt: str) -> list:
    return [t for t in FORBIDDEN if t in prompt.lower()]

# ── Shared LOOK LOCK block ────────────────────────────────────────────────────
_LOOK_LOCK = (
    "LOOK LOCK — LOOK 3 · THE TAILORED SELF\n"
    "The exact same outfit, do not invent variations:\n"
    "- cropped charcoal blazer (dark grey, NOT black, hemline at natural waist,\n"
    "  relaxed broad-shoulder slightly oversized silhouette)\n"
    "- white cotton shirt, collar visible above the lapels\n"
    "- muted olive tie (dusty khaki army-green, NOT black, NOT dark navy)\n"
    "- wide faded blue denim trousers (distinctly wide, relaxed leg)\n"
    "- black leather oxford shoes\n"
    "Do not convert to: corporate black suit, school uniform, slim trousers.\n"
)

_IDENTITY_LOCK = (
    "IDENTITY LOCK\n"
    "The visible character must be the exact same woman shown in the identity crops.\n"
    "Do not generate a similar woman, a generic elegant brunette, or an averaged face.\n"
    "Do not soften or reinterpret the facial structure. Preserve exactly:\n"
    "- strong defined brows, horizontal arch\n"
    "- deep-set almond-shaped eyes, same spacing\n"
    "- high cheekbones\n"
    "- straight narrow nose bridge\n"
    "- full lips\n"
    "- defined jawline and chin\n"
    "- light olive skin tone\n"
    "- centre-parted dark hair, falls to shoulders\n"
)

_SCENE = (
    "SCENE (mood only)\n"
    "Quiet Parisian cobblestone street. Limestone Haussmann facades, shuttered windows,\n"
    "wrought-iron railings, grey cobblestones, soft diffused neutral daylight. Background may be\n"
    "softly out of focus. Use the scene reference ONLY for lighting mood and atmosphere —\n"
    "never to create or alter the face.\n"
)

_REALISM = (
    "REALISM\n"
    "Photorealistic, cinematic quality. Natural skin texture, no plastic skin, no AI-smoothed\n"
    "fabric, no over-polished commercial lighting, no poster composition. Single subject only —\n"
    "no extra people, no duplicated face or body.\n"
)

def _roles(primary_desc: str) -> str:
    lines = ["ROLE OF REFERENCE IMAGES", primary_desc]
    if INCLUDE_OUTFIT_REF:
        lines.append(
            "Outfit image (look3_front.png): SECONDARY OUTFIT REFERENCE ONLY.\n"
            "Use it to confirm the Look 3 garments and body proportions. It is NOT the primary\n"
            "identity source — do not copy a different face from it.")
    lines.append(
        "Scene image (main_scene_board): STREET MOOD REFERENCE ONLY. Lighting and atmosphere only.\n"
        "Never use it to create or alter the character's face.")
    return "\n".join(lines) + "\n"

FRONT_PROMPT = (
    _roles(
        "Identity crop 1 (look3_closeup.png): PRIMARY FRONT IDENTITY REFERENCE.\n"
        "This defines the target face. Preserve it exactly.\n"
        "Identity crop 2 (look3_profile_crop.png): SAME WOMAN, alternate angle. Reinforce the\n"
        "same identity — do not treat the two crops as different people.")
    + "\nCORE TASK\n"
    "Generate a clean FRONT identity anchor. Show the exact same woman, front-facing or a slight\n"
    "three-quarter angle, face fully visible and sharp, wearing the exact Look 3 outfit, placed\n"
    "naturally into a quiet Parisian street with neutral daylight. This is an identity-lock\n"
    "reference image, not a fashion editorial and not a new character design.\n\n"
    "COMPOSITION\n"
    "Waist-up frame. Head and face front / slight three-quarter, both eyes visible, sharp focus\n"
    "on the face. Quiet, introspective expression. Simple stable pose, not an action frame.\n\n"
    + _IDENTITY_LOCK + "\n" + _LOOK_LOCK + "\n" + _SCENE + "\n" + _REALISM
)

PROFILE_PROMPT = (
    _roles(
        "Identity crop 1 (look3_profile_crop.png): PRIMARY PROFILE IDENTITY REFERENCE.\n"
        "This defines the target profile — nose line, brow, jaw, chin. Preserve it exactly.\n"
        "Identity crop 2 (look3_closeup.png): SAME WOMAN, front angle. Reinforce the same identity —\n"
        "do not treat the two crops as different people.")
    + "\nCORE TASK\n"
    "Generate a clean PROFILE identity anchor. Show the exact same woman from a clean side-profile\n"
    "or near-profile three-quarter angle, the face turned to the side so the nose line, brow, jaw\n"
    "and chin profile read clearly, wearing the exact Look 3 outfit, in a quiet Parisian street\n"
    "with neutral daylight. This is an identity-lock reference for side/profile consistency in\n"
    "shot_001 and shot_004.\n\n"
    "COMPOSITION\n"
    "Waist-up frame. Head turned to a clean side profile / near-profile three-quarter. Jawline,\n"
    "nose bridge and chin silhouette sharp and clearly readable. Quiet expression, stable pose.\n\n"
    + _IDENTITY_LOCK + "\n" + _LOOK_LOCK + "\n" + _SCENE + "\n" + _REALISM
)

def generate_anchor(label: str, prompt: str, refs: list, out_path: Path) -> bool:
    if out_path.exists() and not ALLOW_OVERWRITE:
        kb = out_path.stat().st_size // 1024
        print(f"[{label}] existing anchor found — skipping ({kb} KB) "
              f"(set ALLOW_OVERWRITE=True to regenerate)")
        return True

    hits = check_forbidden(prompt)
    if hits:
        print(f"[{label}] ERROR: forbidden terms in prompt: {hits}"); return False

    print("\n" + "=" * 60)
    print(f"{label.upper()} ANCHOR — generating {out_path.name}")
    print("=" * 60)
    print(f"[{label}] inputs:")
    for i, p in enumerate(refs):
        print(f"  image[{i}] : {p.name}")

    handles = []
    try:
        for p in refs:
            handles.append(open(p, "rb"))
        resp = client.images.edit(
            model="gpt-image-1",
            image=handles,
            prompt=prompt,
            size="1024x1536",
            quality="high",
            input_fidelity="high",
            n=1,
        )
        img = base64.b64decode(resp.data[0].b64_json)
        out_path.write_bytes(img)
        print(f"[{label}] ✓ SAVED: {out_path.name} ({len(img)//1024} KB)")
        return True
    except Exception as e:
        print(f"[{label}] ERROR: {e}")
        return False
    finally:
        for h in handles:
            h.close()

# ── Reference sets ────────────────────────────────────────────────────────────
FRONT_REFS   = [CLOSEUP, PROFILE_CROP]      # primary: front, then profile
PROFILE_REFS = [PROFILE_CROP, CLOSEUP]      # primary: profile, then front
if INCLUDE_OUTFIT_REF:
    FRONT_REFS.append(FRONT_OUTFIT)
    PROFILE_REFS.append(FRONT_OUTFIT)
FRONT_REFS.append(SCENE_BOARD)
PROFILE_REFS.append(SCENE_BOARD)

# ── Generate both anchors ─────────────────────────────────────────────────────
ok_front   = generate_anchor("front",   FRONT_PROMPT,   FRONT_REFS,   FRONT_ANCHOR)
ok_profile = generate_anchor("profile", PROFILE_PROMPT, PROFILE_REFS, PROFILE_ANCHOR)

if not (ok_front and ok_profile):
    print("\nERROR: one or both anchors failed. Not building contact sheet.")
    sys.exit(1)

# ── Build side-by-side contact sheet ──────────────────────────────────────────
from PIL import Image as _Img, ImageDraw as _Draw, ImageFont as _Font

_BG   = (18, 18, 18)
_FG   = (230, 230, 230)
_ACC  = (120, 180, 255)
_PAD  = 24
_LBL_H = 44

def _font(sz):
    for cand in ("/System/Library/Fonts/Helvetica.ttc",
                 "/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/Library/Fonts/Arial.ttf"):
        if Path(cand).exists():
            try:
                return _Font.truetype(cand, sz)
            except Exception:
                pass
    return _Font.load_default()

_TITLE_F = _font(22)
_LBL_F   = _font(20)

panels = [
    (FRONT_ANCHOR,   "look3_identity_anchor_front.png  ·  FRONT identity"),
    (PROFILE_ANCHOR, "look3_identity_anchor_profile.png  ·  PROFILE identity"),
]

imgs = [_Img.open(p).convert("RGB") for p, _ in panels]
cell_h = min(im.height for im in imgs)
cell_h = min(cell_h, 900)
scaled = []
for im in imgs:
    w = int(im.width * (cell_h / im.height))
    scaled.append(im.resize((w, cell_h)))

title_h = 40
sheet_w = _PAD + sum(im.width + _PAD for im in scaled)
sheet_h = title_h + _LBL_H + cell_h + _PAD
sheet = _Img.new("RGB", (sheet_w, sheet_h), _BG)
draw = _Draw.Draw(sheet)
draw.text((_PAD, 10), "IDENTITY ANCHOR REVIEW — Look 3 · street  (HUMAN REVIEW REQUIRED)",
          fill=_ACC, font=_TITLE_F)

x = _PAD
for im, (_, lbl) in zip(scaled, panels):
    y_lbl = title_h
    draw.text((x, y_lbl + 10), lbl, fill=_FG, font=_LBL_F)
    sheet.paste(im, (x, title_h + _LBL_H))
    x += im.width + _PAD

sheet.save(CONTACT_SHEET)

# ── Stop for human review ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("TWO ANCHORS COMPLETE — STOPPING FOR HUMAN REVIEW")
print("=" * 60)
print(f"  front   : {FRONT_ANCHOR}")
print(f"  profile : {PROFILE_ANCHOR}")
print(f"  contact : {CONTACT_SHEET}")
print("\n  Review both anchors: same Look 3 woman, correct outfit, neutral street light.")
print("  Front  → should be used as slot[0] identity for face-visible shots.")
print("  Profile→ should be used as the profile/side support (e.g. slot[3]).")
print("\n  This script does NOT run Kling and does NOT touch keyframes.")
print("  Approve the anchors first, then wire them into the keyframe run.")
print("=" * 60)
sys.exit(0)
