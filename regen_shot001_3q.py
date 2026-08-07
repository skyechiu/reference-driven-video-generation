"""
regen_shot001_3q.py — regenerate ONLY shot_001 as a 3/4 over-shoulder, face-visible
single keyframe for the street run.

Why: the current shot_001 keyframe is a near-full side profile with lowered eyes.
For the final street video, the face must be given in the keyframe (Kling is not an
identity inference engine — a front/near-front face not present in the keyframe will
be invented). So shot_001 needs a THREE-QUARTER over-shoulder keyframe with the face
clearly visible, eyes open, only a subtle glance — no full profile, no eyes closed,
no straight-to-camera.

Single keyframe, paid (gpt-image-1). Does NOT touch Kling. Writes a NEW file
(shot_001_keyframe_look3_street_3q.png) + an old|new comparison; the original is
left untouched until you approve the swap.

Run
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 regen_shot001_3q.py
"""

import base64, os, sys
from pathlib import Path

ROOT = Path(__file__).parent
ALLOW_OVERWRITE = True

# ── .env / OpenAI ─────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env"); print("[env] loaded .env")
except ImportError:
    print("[env] python-dotenv not installed — using system env vars")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not set"); sys.exit(1)
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY, max_retries=1)

# ── Paths ─────────────────────────────────────────────────────────────────────
LOOK_DIR = ROOT / "assets/looks/look_3_tailored_self"
KF_DIR   = ROOT / "outputs/runs/live_test_04_street_look3/keyframes"
KF_DIR.mkdir(parents=True, exist_ok=True)

FRONT_ANCHOR   = LOOK_DIR / "look3_identity_anchor_front.png"
PROFILE_ANCHOR = LOOK_DIR / "look3_identity_anchor_profile.png"
LOOK_CLOSEUP   = LOOK_DIR / "look3_closeup.png"
LOOK_FRONT     = LOOK_DIR / "look3_front.png"

OLD_KF = KF_DIR / "shot_001_keyframe_look3_street.png"          # current profile version (kept)
NEW_KF = KF_DIR / "shot_001_keyframe_look3_street_3q.png"       # new 3/4 version

for p in [FRONT_ANCHOR, PROFILE_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT]:
    if not p.exists():
        print(f"ERROR: missing asset: {p}"); sys.exit(1)

# ── Slots: identity-primary (face_visible) ───────────────────────────────────
#   [0] front anchor  — PRIMARY 3/4 front identity
#   [1] look3_closeup — high-res face fidelity
#   [2] look3_front   — outfit / body
#   [3] profile anchor— angle support
IMAGES = [FRONT_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT, PROFILE_ANCHOR]

PROMPT = (
    "Medium-close OVER-THE-SHOULDER shot on a quiet Parisian cobblestone street, vertical 9:16, waist-up.\n"
    "\n"
    "HEAD / FACE — this is the key requirement:\n"
    "The woman is turned about THREE-QUARTERS toward camera in a natural, subtle glance back over her shoulder.\n"
    "Her FACE IS CLEARLY VISIBLE at a three-quarter angle — BOTH eyes open and visible, looking softly off to the\n"
    "side in a calm unposed glance. This is NOT a full side profile. This is NOT eyes-closed. This is NOT looking\n"
    "straight down the lens. The three-quarter face must clearly show her identity (both brows, both eyes, nose, lips).\n"
    "Camera is slightly behind and to one side; a sliver of her shoulder/upper back reads in the foreground as\n"
    "'over the shoulder'. Quiet, private, unposed expression. A gentle glance, not a dramatic turn.\n"
    "\n"
    "IDENTITY LOCK: exactly the same woman as the Look 3 identity anchors — strong defined brows, deep-set almond\n"
    "eyes, high cheekbones, straight narrow nose, full lips, defined jawline, light olive skin, centre-parted dark\n"
    "hair to the shoulders. Not a generic brunette, not an averaged face.\n"
    "\n"
    "LOOK LOCK (Look 3): cropped charcoal blazer (dark grey, NOT black, natural-waist hem), white shirt with visible\n"
    "collar, muted olive tie (dusty khaki-green, NOT black/navy), wide faded blue denim trousers, black leather\n"
    "oxford shoes. Do not convert to a corporate black suit, school uniform, or slim trousers.\n"
    "\n"
    "SCENE: quiet Parisian cobblestone street — limestone Haussmann facades, shuttered windows, wrought-iron\n"
    "railings, grey cobblestones, soft diffused neutral daylight, background softly out of focus.\n"
    "\n"
    "REALISM: photorealistic cinematic quality, natural skin texture, single subject only, no extra people,\n"
    "no duplicated face or limbs, no text or watermark.\n"
)

if NEW_KF.exists() and not ALLOW_OVERWRITE:
    print(f"[shot_001] {NEW_KF.name} exists — skip (ALLOW_OVERWRITE=False)"); sys.exit(0)

print("[shot_001] slots:", [p.name for p in IMAGES])
handles = []
try:
    for p in IMAGES:
        handles.append(open(p, "rb"))
    resp = client.images.edit(
        model="gpt-image-1", image=handles, prompt=PROMPT,
        size="1024x1536", quality="high", input_fidelity="high", n=1,
    )
    data = base64.b64decode(resp.data[0].b64_json)
    NEW_KF.write_bytes(data)
    print(f"[shot_001] SAVED {NEW_KF.name} ({len(data)//1024} KB)")
finally:
    for h in handles:
        h.close()

# ── old | new comparison ──────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
    H, PAD, LBL = 820, 16, 34
    def fit(im):
        w = int(im.width * (H / im.height)); return im.resize((w, H))
    panels = []
    if OLD_KF.exists():
        panels.append(("shot_001 OLD (profile, eyes down)", fit(Image.open(OLD_KF).convert("RGB"))))
    panels.append(("shot_001 NEW (3/4 over-shoulder, face visible)", fit(Image.open(NEW_KF).convert("RGB"))))
    cw = max(im.width for _, im in panels)
    sheet = Image.new("RGB", (PAD + (cw + PAD) * len(panels), PAD + LBL + H + PAD), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    try: F = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except Exception: F = ImageFont.load_default()
    x = PAD
    for lbl, im in panels:
        d.text((x, PAD), lbl, fill=(120, 180, 255), font=F)
        sheet.paste(im, (x, PAD + LBL)); x += cw + PAD
    cmp_path = KF_DIR / "shot_001_3q_comparison.png"
    sheet.save(cmp_path)
    print(f"[shot_001] comparison: {cmp_path}")
except Exception as e:
    print(f"[shot_001] comparison sheet skipped: {e}")

print("\nReview shot_001_3q_comparison.png. If the NEW 3/4 version is good, it becomes the\n"
      "final shot_001 (swap it in as shot_001_keyframe_look3_street.png). Kling NOT called.")
