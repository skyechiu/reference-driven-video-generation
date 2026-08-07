"""
regen_shot002_004.py — Targeted identity-fix regeneration for shot_002 and shot_004

Constraints:
  - Do NOT touch shot_001 or shot_003
  - Do NOT call Kling
  - Use specified slot orders (different from the main pipeline logic)
  - Output: shot_002_keyframe_look3_street_v2.png
            shot_004_keyframe_look3_street_v2.png
            street_identityfix_shot002_004_comparison.png
"""

import base64, io, json, os, sys, time
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from PIL import Image

ROOT = Path(__file__).parent

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
client = OpenAI(api_key=OPENAI_API_KEY)

# ── Paths ─────────────────────────────────────────────────────────────────────
RUN_ID   = "live_test_04_street_look3"
RUN_DIR  = ROOT / "outputs" / "runs" / RUN_ID
KF_DIR   = RUN_DIR / "keyframes"
KF_DIR.mkdir(parents=True, exist_ok=True)

SCENE_REF = ROOT / "assets/scenes/built_in/scene_02_modern_street/references"
LOOK_DIR  = ROOT / "assets/looks/look_3_tailored_self"

# Reference files
ESTABLISHING = SCENE_REF / "establishing_view_16x9.png"
SIDE_VIEW    = SCENE_REF / "side_view_16x9.png"
SHEET        = LOOK_DIR  / "look3_sheet.png"
CLOSEUP      = LOOK_DIR  / "look3_closeup.png"
FRONT        = LOOK_DIR  / "look3_front.png"
SHOT001_KF   = KF_DIR    / "shot_001_keyframe_look3_street.png"

# Old keyframes (for comparison sheet)
OLD_KF_002   = KF_DIR / "shot_002_keyframe_look3_street.png"
OLD_KF_004   = KF_DIR / "shot_004_keyframe_look3_street.png"

# New output keyframes
NEW_KF_002   = KF_DIR / "shot_002_keyframe_look3_street_v2.png"
NEW_KF_004   = KF_DIR / "shot_004_keyframe_look3_street_v2.png"

# Verify required assets
for p in [ESTABLISHING, SIDE_VIEW, SHEET, CLOSEUP, FRONT, SHOT001_KF]:
    if not p.exists():
        print(f"ERROR: missing asset: {p}"); sys.exit(1)
print("[assets] all 6 required assets verified")
print(f"  shot_001 approved kf : {SHOT001_KF.name}")


# ── Forbidden-word guard ──────────────────────────────────────────────────────
FORBIDDEN = [
    "bride", "bridal", "wedding", "wedding dress", "bridal gown",
    "cathedral veil", "white lace wedding gown",
    "copied source outfit", "same outfit as source",
]

def check_forbidden(prompt: str) -> tuple[bool, list]:
    hits = [t for t in FORBIDDEN if t in prompt.lower()]
    return (len(hits) == 0), hits


# ── Shared blocks ─────────────────────────────────────────────────────────────
_LOOK = (
    "LOOK — THE TAILORED SELF: "
    "Study the look references carefully — do not invent a different outfit. "
    "BLAZER: Cropped charcoal blazer. Charcoal = dark grey, NOT black. "
    "Hemline ends at the natural waist — very short, not hip-length, not full-length. "
    "Relaxed broad-shoulder silhouette, slightly oversized, deconstructed. "
    "NOT a fitted corporate suit jacket, NOT formal businesswear, NOT a black blazer. "
    "TIE: Muted olive tie — dusty earthy army-green, NOT black, NOT dark navy. Distinctly olive/khaki. "
    "SHIRT: White cotton shirt, visible at collar above blazer lapels. "
    "TROUSERS: Wide faded blue denim trousers. Faded mid-blue wash. "
    "The leg cut is distinctly wide and relaxed — trouser leg visibly drapes. "
    "NOT slim fit, NOT straight leg, NOT cropped, NOT office trousers, NOT suit trousers. "
    "The wide leg is the most important visual feature of this outfit. "
    "SHOES: Black leather oxford shoes — structured, low heel, clean sole. "
    "HAIR: Loose natural dark hair, falls to shoulders. "
    "SILHOUETTE: Cropped charcoal blazer, wide relaxed denim, black oxfords. "
    "Runway-relaxed tailoring — not corporate, not smart-casual. "
    "Natural fabric drape and wrinkles visible."
)

_REALISM = (
    "REALISM — must look like a real extracted video frame: "
    "Subtle natural motion softness consistent with walking. "
    "Slight film-grain texture, not clean digital advertising output. "
    "Not a fashion editorial, not a stock photo, not a commercial poster."
)

_AVOID_DRIFT = (
    "CRITICAL AVOIDS — in this image do NOT generate: "
    "a black business blazer or formal suit jacket; "
    "slim-cut or straight-leg office trousers; "
    "a dark or black tie; "
    "extra people or pedestrians in the scene; "
    "any text, graphic overlays, or watermarks."
)


# ══════════════════════════════════════════════════════════════════════════════
# SHOT_002 — Wide full-body back-view walk away
# Slot order (user-specified, differs from pipeline default):
#   [0] establishing_view_16x9.png    — back-view vanishing-point composition
#   [1] shot_001 approved keyframe    — continuity anchor (hair, outfit, lighting)
#   [2] look3_sheet.png               — outfit + identity reference
#   [3] look3_front.png               — full-body outfit reference
# ══════════════════════════════════════════════════════════════════════════════

_SHOT002_SLOT_HEADER = """\
IMAGE REFERENCES FOR THIS SHOT (shot_002):
  Image 1 — establishing_view_16x9.png: COMPOSITION REFERENCE.
    This is the back-view street perspective. The vanishing-point depth, cobblestone
    paving, and building flanks in this image define the camera position and framing.
    Use this to set the street angle, depth, and background architecture.

  Image 2 — approved shot_001 keyframe: CONTINUITY ANCHOR.
    This is the approved keyframe for the same character in the same street scene.
    Use it to match: hair colour and length, body proportion and silhouette,
    outfit visible from back (blazer back, wide denim), and street lighting quality.
    Do not alter the character's hair or body proportions relative to this reference.

  Image 3 — look3_sheet.png: OUTFIT AND IDENTITY REFERENCE.
    This shows the exact woman and exact outfit from multiple angles.
    Use it to confirm the charcoal blazer back, wide denim trouser legs, and
    black oxford shoes from a walking-away perspective.

  Image 4 — look3_front.png: FULL-BODY OUTFIT CONFIRMATION.
    Confirms trousers width, hem length, shoe style, blazer cut.
    Use for lower-body accuracy.

CRITICAL: This is a BACK-VIEW shot. Do NOT show the character's face.
Do NOT turn her toward camera. The identity is communicated through:
hair (dark, shoulder-length, centre-part visible from behind), body proportion,
outfit silhouette, and continuity from the approved shot_001 keyframe.

"""

PROMPT_SHOT002 = _SHOT002_SLOT_HEADER + """\
SHOT DESCRIPTION — shot_002: Wide full-body back-view walk away.

The character walks away from camera down the quiet Parisian cobblestone street.
Camera is behind her, at eye level or slightly above, capturing her full body.

COMPOSITION:
- Camera faces down the street toward the vanishing point (deep perspective)
- Character is centered or slightly left of center
- Full body visible head to shoes — do not cut off feet or top of head
- Street recedes into distance behind her
- Cobblestone paving fills the foreground and middle-ground
- Haussmann limestone facades on both sides create the narrow-street canyon
- Soft diffused daylight from above — no harsh shadows

CHARACTER — BACK VIEW:
- We see her from directly behind, walking away
- Dark shoulder-length hair visible from behind — matches the approved shot_001
- Centre-part and natural hair movement consistent with walking pace
- Back of the charcoal blazer visible — notice the cropped waist-length hemline
- Wide faded blue denim trouser legs clearly visible — the wide relaxed silhouette
  is the defining visual of this outfit from behind; trouser legs should drape wide
- Black leather oxford shoes on the cobblestone surface — heel to toe visible
- Her posture: relaxed, unhurried, absorbed in thought — not rushing
- Arms hang naturally at sides, slight natural walk movement

WHAT NOT TO DO:
- Do not show her face
- Do not show a side-profile or three-quarter view of her face
- Do not show a black corporate blazer — the back of the blazer is charcoal grey
- Do not show slim or straight-leg trousers from behind
- Do not add extra people
- Do not generate a generic woman — the silhouette, hair, and outfit must match
  the approved shot_001 and the look references

""" + _LOOK + "\n\n" + _REALISM + "\n\n" + _AVOID_DRIFT


# ══════════════════════════════════════════════════════════════════════════════
# SHOT_004 — Wide side-profile walk along facade
# Slot order (user-specified):
#   [0] look3_sheet.png       — PRIMARY identity and outfit reference
#   [1] look3_closeup.png     — face/profile fidelity reference
#   [2] shot_001 approved kf  — continuity anchor
#   [3] side_view_16x9.png    — street environment only
# ══════════════════════════════════════════════════════════════════════════════

_SHOT004_SLOT_HEADER = """\
IMAGE REFERENCES FOR THIS SHOT (shot_004):
  Image 1 — look3_sheet.png: PRIMARY IDENTITY AND OUTFIT REFERENCE.
    This is the most important input for this shot.
    It shows the exact same woman from multiple angles — front, side, three-quarter.
    Use the side-view angle in this sheet to confirm what her side profile looks like.
    Her face in this image is the target identity. Match it precisely.
    Also use it to confirm the exact outfit from a side-view perspective.

  Image 2 — look3_closeup.png: FACE AND PROFILE FIDELITY REFERENCE.
    This confirms the precise facial features at close range.
    When rendering the side profile, match:
      - nose bridge shape (straight, narrow)
      - brow shape (strong, defined, horizontal arch)
      - lip fullness from profile
      - jawline and chin angle
      - hairline and centre-part direction from the side
      - cheekbone prominence visible in profile
    Do not generate a different side profile. Do not invent a new face shape.

  Image 3 — approved shot_001 keyframe: CONTINUITY ANCHOR.
    The same character in the same street scene, one moment earlier.
    Use to match: hair colour and length, overall impression, street lighting quality.

  Image 4 — side_view_16x9.png: STREET ENVIRONMENT ONLY.
    This defines the camera position and background architecture for this shot.
    The Haussmann facade, iron railings, pavement, and lighting quality come from here.
    This image does NOT define the character's face or outfit.

CRITICAL: This is a SIDE-PROFILE shot where facial identity matters.
The character's face and profile must come from Image 1 and Image 2.
The street scene (Image 4) controls ONLY the environment and composition.

"""

_SHOT004_PROFILE_FACE = (
    "IDENTITY — SIDE PROFILE: "
    "The character is seen in clean side-profile, walking left to right. "
    "Her face in side profile must match the woman shown in image 1 (look sheet) "
    "and image 2 (look closeup). "
    "Match these profile features precisely: "
    "straight narrow nose bridge visible in profile; "
    "strong defined horizontal brow visible from the side; "
    "full lips in profile; "
    "defined jawline and chin shape; "
    "high cheekbone prominence visible in profile; "
    "centre-parted dark hair falling to shoulders, hairline visible from the side. "
    "Light olive skin tone. "
    "Expression: quiet and introspective, gaze directed forward or gently downward. "
    "Not looking at the camera. "
    "Do not invent a new side-profile face. "
    "Do not generate a generic woman's profile. "
    "The profile silhouette must be consistent with the same woman approved in shot_001."
)

PROMPT_SHOT004 = _SHOT004_SLOT_HEADER + """\
SHOT DESCRIPTION — shot_004: Wide or medium-wide side-profile walk along facade.

The character walks left to right along the quiet Parisian cobblestone street,
parallel to the Haussmann facade. Camera is stationary, level, capturing her
in clean side profile as she moves through frame.

COMPOSITION:
- Camera faces the facade, character walks perpendicular to camera axis
- Medium-wide or wide framing — full body head to shoes visible
- Haussmann limestone facade and wrought iron railings fill the background
- Cobblestone pavement at her feet
- Soft diffused natural daylight — consistent with the other shots in this sequence
- Character positioned slightly left-of-center walking toward center or right

""" + _SHOT004_PROFILE_FACE + "\n\n" + """\
OUTFIT FROM SIDE VIEW:
- Cropped charcoal blazer: hemline clearly ends at waist from the side
- White shirt collar and muted olive tie subtly visible at the front
- Wide faded blue denim trousers: the wide trouser leg drapes clearly in side profile
- Black leather oxford shoes on the cobblestone
- Hair falls to shoulders, moves slightly with her walking

WHAT NOT TO DO:
- Do not generate a frontal or three-quarter face — side profile only
- Do not generate a black corporate blazer — it is charcoal grey
- Do not generate fitted office trousers — the denim is distinctly wide-leg
- Do not generate slim trousers, straight-leg trousers, or suit trousers
- Do not generate extra people
- Do not alter the Haussmann architecture, iron railings, or cobblestone from the street reference

""" + _LOOK + "\n\n" + _REALISM + "\n\n" + _AVOID_DRIFT


# ══════════════════════════════════════════════════════════════════════════════
# Guard checks
# ══════════════════════════════════════════════════════════════════════════════
print("\n[guard] Checking prompts for forbidden words ...")
for label, p in [("shot_002", PROMPT_SHOT002), ("shot_004", PROMPT_SHOT004)]:
    ok, hits = check_forbidden(p)
    if ok:
        print(f"  ✓ {label}: CLEAN ({len(p)} chars)")
    else:
        print(f"  ✗ {label}: FORBIDDEN WORDS FOUND: {hits}")
        sys.exit(1)
print("[guard] All prompts CLEAN — proceeding to API calls\n")


# ══════════════════════════════════════════════════════════════════════════════
# Generation function
# ══════════════════════════════════════════════════════════════════════════════
def generate_keyframe(shot_id: str, images_in: list[Path], prompt: str,
                      out_path: Path, slot_notes: str) -> bool:
    print(f"[gen] Generating {shot_id} keyframe ...")
    print(f"  slots   : {slot_notes}")
    print(f"  output  : {out_path.name}")
    print(f"  prompt  : {len(prompt)} chars")

    handles = []
    try:
        for p in images_in:
            handles.append(open(p, "rb"))
        response = client.images.edit(
            model="gpt-image-1",
            image=handles,
            prompt=prompt,
            size="1024x1536",
            quality="medium",
            n=1,
        )
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    finally:
        for h in handles:
            h.close()

    img_data = base64.b64decode(response.data[0].b64_json)
    out_path.write_bytes(img_data)
    size_kb = len(img_data) // 1024
    print(f"  ✓ SAVED: {out_path.name}  ({size_kb} KB)")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# Run shot_002
# ══════════════════════════════════════════════════════════════════════════════
images_002 = [
    ESTABLISHING,   # [0] back-view street vanishing-point composition
    SHOT001_KF,     # [1] approved continuity anchor
    SHEET,          # [2] outfit + identity reference
    FRONT,          # [3] full-body outfit confirmation
]
slots_002 = "establishing[0·comp] · shot001_kf[1·continuity] · look3_sheet[2·outfit+id] · look3_front[3·outfit]"

ok_002 = generate_keyframe("shot_002", images_002, PROMPT_SHOT002, NEW_KF_002, slots_002)
if not ok_002:
    print("ERROR: shot_002 generation failed"); sys.exit(1)

print("\n[pause] Waiting 5s between OpenAI calls ...")
time.sleep(5)


# ══════════════════════════════════════════════════════════════════════════════
# Run shot_004
# ══════════════════════════════════════════════════════════════════════════════
images_004 = [
    SHEET,          # [0] PRIMARY identity + outfit reference
    CLOSEUP,        # [1] face/profile fidelity reference
    SHOT001_KF,     # [2] continuity anchor
    SIDE_VIEW,      # [3] street environment only
]
slots_004 = "look3_sheet[0·PRIMARY id] · look3_closeup[1·face fidelity] · shot001_kf[2·continuity] · side_view[3·env]"

ok_004 = generate_keyframe("shot_004", images_004, PROMPT_SHOT004, NEW_KF_004, slots_004)
if not ok_004:
    print("ERROR: shot_004 generation failed"); sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# Comparison sheet
# 7-panel layout:
#   Row 1: [approved shot_001] [old 002] [new 002_v2]
#   Row 2: [look3_sheet]      [old 004] [new 004_v2]  [look3_closeup]
# ══════════════════════════════════════════════════════════════════════════════
print("\n[sheet] Creating comparison sheet ...")

def load_img(path: Path):
    """Load image as RGBA numpy array."""
    img = Image.open(path).convert("RGBA")
    return np.array(img)

imgs = {
    "shot_001 (approved anchor)": load_img(SHOT001_KF),
    "shot_002 OLD":               load_img(OLD_KF_002) if OLD_KF_002.exists() else None,
    "shot_002 v2 (new)":          load_img(NEW_KF_002),
    "shot_004 OLD":               load_img(OLD_KF_004) if OLD_KF_004.exists() else None,
    "shot_004 v2 (new)":          load_img(NEW_KF_004),
    "look3_sheet (ref)":          load_img(SHEET),
    "look3_closeup (ref)":        load_img(CLOSEUP),
}

# Layout: 2 rows × 4 cols
# Row 0 (keyframe story): shot_001 | old_002 | new_002 | [look3_sheet]
# Row 1 (profile story):  look3_sheet | old_004 | new_004 | look3_closeup
panel_rows = [
    ["shot_001 (approved anchor)", "shot_002 OLD", "shot_002 v2 (new)", "look3_sheet (ref)"],
    ["look3_sheet (ref)",          "shot_004 OLD", "shot_004 v2 (new)", "look3_closeup (ref)"],
]

PANEL_W_PX = 420
PANEL_H_PX = 630  # 1024x1536 → aspect ~0.667 → 420×630
GAP = 20
HEADER_H = 60
LABEL_H  = 36

n_rows = 2
n_cols = 4
fig_w = n_cols * PANEL_W_PX + (n_cols + 1) * GAP
fig_h = HEADER_H + n_rows * (PANEL_H_PX + LABEL_H) + (n_rows + 1) * GAP

fig_dpi = 150
fig, ax_master = plt.subplots(
    figsize=(fig_w / fig_dpi, fig_h / fig_dpi),
    dpi=fig_dpi,
)
ax_master.set_facecolor("#0e0e10")
fig.patch.set_facecolor("#0e0e10")
ax_master.axis("off")

# Draw header
ax_master.text(
    0.5, 1.0 - (HEADER_H * 0.4 / fig_h),
    "Identity Fix · shot_002 & shot_004 · v2 Comparison",
    transform=ax_master.transAxes,
    fontsize=11, fontweight="bold", color="white",
    ha="center", va="top",
)
ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
ax_master.text(
    0.5, 1.0 - (HEADER_H * 0.75 / fig_h),
    f"live_test_04_street_look3 · {ts}",
    transform=ax_master.transAxes,
    fontsize=7, color="#aaaaaa", ha="center", va="top",
)

# Draw panels
for r_idx, row in enumerate(panel_rows):
    for c_idx, label in enumerate(row):
        img_arr = imgs.get(label)

        x = GAP + c_idx * (PANEL_W_PX + GAP)
        y = HEADER_H + GAP + r_idx * (PANEL_H_PX + LABEL_H + GAP)

        left   = x / fig_w
        bottom = 1.0 - (y + PANEL_H_PX) / fig_h
        width  = PANEL_W_PX / fig_w
        height = PANEL_H_PX / fig_h

        ax = fig.add_axes([left, bottom, width, height])
        ax.set_facecolor("#1a1a1e")
        ax.axis("off")

        if img_arr is not None:
            ax.imshow(img_arr, aspect="auto")
        else:
            ax.text(0.5, 0.5, "missing", transform=ax.transAxes,
                    color="#666666", ha="center", va="center", fontsize=8)

        # Colour-code border
        is_new = "v2" in label
        is_ref = "ref" in label
        is_anchor = "approved" in label
        edge_color = ("#22c55e" if is_new else
                      "#f97316" if is_anchor else
                      "#818cf8" if is_ref else
                      "#ef4444")
        for spine in ax.spines.values():
            spine.set_edgecolor(edge_color)
            spine.set_linewidth(2.5 if is_new or is_anchor else 1.5)

        # Label below panel
        lx = (x + PANEL_W_PX / 2) / fig_w
        ly = 1.0 - (y + PANEL_H_PX + LABEL_H * 0.55) / fig_h
        ax_master.text(
            lx, ly, label,
            transform=ax_master.transAxes,
            fontsize=6.5, color=("#22c55e" if is_new else
                                  "#f97316" if is_anchor else
                                  "#818cf8" if is_ref else "#ff6b6b"),
            ha="center", va="center", fontweight="bold" if is_new else "normal",
        )

# Legend
legend_items = [
    ("#f97316", "approved anchor"),
    ("#ef4444", "OLD (rejected)"),
    ("#22c55e", "v2 NEW"),
    ("#818cf8", "look reference"),
]
lx_start = 0.02
for i, (color, text) in enumerate(legend_items):
    ax_master.text(
        lx_start + i * 0.24,
        0.012,
        f"■ {text}",
        transform=ax_master.transAxes,
        fontsize=6, color=color, va="bottom",
    )

comp_path = KF_DIR / "street_identityfix_shot002_004_comparison.png"
plt.savefig(comp_path, dpi=fig_dpi, bbox_inches="tight",
            facecolor="#0e0e10", edgecolor="none")
plt.close()
print(f"  ✓ SAVED: {comp_path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# Log
# ══════════════════════════════════════════════════════════════════════════════
log = {
    "run_id":        "live_test_04_street_look3",
    "script":        "regen_shot002_004.py",
    "timestamp":     datetime.utcnow().isoformat() + "Z",
    "shots_regenerated": ["shot_002", "shot_004"],
    "shots_unchanged":   ["shot_001 (approved)", "shot_003 (approved)"],
    "kling_called":  False,
    "outputs": {
        "shot_002_v2": str(NEW_KF_002),
        "shot_004_v2": str(NEW_KF_004),
        "comparison":  str(comp_path),
    },
    "slot_orders": {
        "shot_002": "establishing[0] · shot001_kf[1] · look3_sheet[2] · look3_front[3]",
        "shot_004": "look3_sheet[0·PRIMARY] · look3_closeup[1] · shot001_kf[2] · side_view[3·env]",
    },
}
log_path = KF_DIR / "regen_shot002_004_log.json"
log_path.write_text(json.dumps(log, indent=2, ensure_ascii=False))
print(f"  ✓ LOG:   {log_path.name}")

print("\n" + "=" * 60)
print("DONE — Kling NOT called")
print(f"  new shot_002 : {NEW_KF_002.name}")
print(f"  new shot_004 : {NEW_KF_004.name}")
print(f"  comparison   : {comp_path.name}")
print("=" * 60)
