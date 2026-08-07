"""
generate_street_start_end.py — graded reference-guided START/END keyframes for the
Parisian street scene, Look 3.

This is NO LONGER a purely hand-written street prompt run. It reuses the beach
reference-video structure where the pose is reliable, and falls back to weaker
conditioning where it is not:

  shot_001  head_orientation  — sparse face pose only; use start/end HEAD ORIENTATION
                                (turned away → turning back), NOT body skeleton.
  shot_002  pose_driven       — clean full-body pose (conf ~0.80). Use extracted
                                start/end keypoints as real pose structure.
  shot_003  text_framing      — NO pose detected (feet-only). Text + framing only.
  shot_004  pose_driven       — clean full-body side-profile pose (conf ~0.85).

Conditioning is SOFT (gpt-image-1 is not a ControlNet):
  - pose is guided by (a) a CLEAN skeleton image rendered from keypoints on a
    neutral background — no beach identity/scene leaked — and (b) text derived
    from the keypoints. Identity/look always come from the Look 3 anchors.
  - This is structured reference-GUIDED generation with graded conditioning
    strength. It does NOT claim exact frame-level motion transfer.

LOCAL run, PAID API (OpenAI gpt-image-1). Generates KEYFRAMES ONLY. Does NOT call
Kling. Does NOT modify project_state.json.

Output → outputs/runs/live_test_04_street_look3/keyframes/start_end/
    shot_00X_{START,END}_keyframe.png
    street_start_end_keyframe_contact_sheet.png
    street_start_end_generation_plan.json

Run
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 generate_street_start_end.py
"""

import base64, json, os, sys
from pathlib import Path

ROOT = Path(__file__).parent

# ── Flags ─────────────────────────────────────────────────────────────────────
PREVIEW_ONLY    = False   # True  → render skeletons + derived pose text + prompts and
                          #         build a pose-control preview sheet. NO OpenAI call, $0.
                          #         Review the pose control first, then set False to generate.
ALLOW_OVERWRITE = True    # regenerate keyframes that already exist

# ── Load .env / OpenAI (only needed for real generation) ─────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    print("[env] loaded .env")
except ImportError:
    print("[env] python-dotenv not installed — using system env vars")

client = None
if PREVIEW_ONLY:
    print("[mode] PREVIEW_ONLY=True — no OpenAI calls; rendering pose control + prompts only")
else:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY not set"); sys.exit(1)
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, max_retries=1)

# ── Paths ─────────────────────────────────────────────────────────────────────
LOOK_DIR  = ROOT / "assets/looks/look_3_tailored_self"
SCENE_REF = ROOT / "assets/scenes/built_in/scene_02_modern_street/references"
POSE_META = ROOT / "outputs/runs/live_test_03_4shots/analysis/start_mid_end/start_mid_end_pose_metadata.json"
STATE     = ROOT / "project_state.json"

OUT_DIR = ROOT / "outputs/runs/live_test_04_street_look3/keyframes/start_end"
OUT_DIR.mkdir(parents=True, exist_ok=True)
SKEL_DIR = OUT_DIR / "_pose_control"
SKEL_DIR.mkdir(parents=True, exist_ok=True)

FRONT_ANCHOR   = LOOK_DIR / "look3_identity_anchor_front.png"
PROFILE_ANCHOR = LOOK_DIR / "look3_identity_anchor_profile.png"
LOOK_CLOSEUP   = LOOK_DIR / "look3_closeup.png"
LOOK_FRONT     = LOOK_DIR / "look3_front.png"
LOOK_SHEET     = LOOK_DIR / "look3_sheet.png"
SCENE_BOARD    = SCENE_REF / "main_scene_board_16x9.jpg"
SCENE_ESTAB    = SCENE_REF / "establishing_view_16x9.png"
SCENE_SIDE     = SCENE_REF / "side_view_16x9.png"

for p in [FRONT_ANCHOR, PROFILE_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT, LOOK_SHEET, SCENE_BOARD]:
    if not p.exists():
        print(f"ERROR: missing asset: {p}"); sys.exit(1)
if not POSE_META.exists():
    print(f"ERROR: pose metadata not found at {POSE_META}")
    print("  Run  python3 extract_start_end_poses.py  first.")
    sys.exit(1)

pose_meta = json.loads(POSE_META.read_text())
POSE = {s["shot_id"]: s["frames"] for s in pose_meta["shots"]}

# motion_direction from the reference analysis (supplementary text)
MOTION = {}
try:
    st = json.loads(STATE.read_text())
    for s in st["reference_data"]["shot_cuts"]:
        MOTION[s["shot_id"]] = s.get("motion_direction", "")
except Exception:
    pass

# ── Skeleton rendering (clean, neutral bg — no identity/scene leak) ───────────
from PIL import Image, ImageDraw, ImageFont
CONNECTIONS = [
    ("LEFT_SHOULDER","RIGHT_SHOULDER"),("LEFT_SHOULDER","LEFT_HIP"),("RIGHT_SHOULDER","RIGHT_HIP"),
    ("LEFT_HIP","RIGHT_HIP"),("LEFT_SHOULDER","LEFT_ELBOW"),("LEFT_ELBOW","LEFT_WRIST"),
    ("RIGHT_SHOULDER","RIGHT_ELBOW"),("RIGHT_ELBOW","RIGHT_WRIST"),("LEFT_HIP","LEFT_KNEE"),
    ("LEFT_KNEE","LEFT_ANKLE"),("RIGHT_HIP","RIGHT_KNEE"),("RIGHT_KNEE","RIGHT_ANKLE"),
    ("LEFT_ANKLE","LEFT_FOOT_INDEX"),("RIGHT_ANKLE","RIGHT_FOOT_INDEX"),
    ("NOSE","LEFT_EYE"),("LEFT_EYE","LEFT_EAR"),("NOSE","RIGHT_EYE"),("RIGHT_EYE","RIGHT_EAR"),
]
VIS = 0.3

def render_skeleton(kpts, out_path, W=896, H=1344, src_aspect=16/9, margin=0.14):
    """Clean white stick-figure on neutral grey, portrait canvas for a 9:16 target.

    Keypoints are normalised to a 16:9 source frame. Naively painting x*W, y*H
    stretches the figure tall/thin. Instead convert to aspect-correct real space
    (X in [0, src_aspect], Y in [0, 1]), then fit the pose isotropically (single
    scale) into the canvas and centre it — proportions preserved.
    """
    img = Image.new("RGB", (W, H), (60, 60, 60))
    d = ImageDraw.Draw(img)
    vis = {n: k for n, k in (kpts or {}).items() if k["visibility"] > VIS}
    if vis:
        xs = [k["x"] * src_aspect for k in vis.values()]
        ys = [k["y"] for k in vis.values()]
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        bw = max(maxx - minx, 1e-3)
        bh = max(maxy - miny, 1e-3)
        scale = min(W * (1 - 2*margin) / bw, H * (1 - 2*margin) / bh)
        offx = (W - bw * scale) / 2 - minx * scale
        offy = (H - bh * scale) / 2 - miny * scale
        def px(name):
            k = kpts[name]
            return (k["x"] * src_aspect * scale + offx, k["y"] * scale + offy)
        for a, b in CONNECTIONS:
            if a in vis and b in vis:
                d.line([px(a), px(b)], fill=(255, 255, 255), width=8)
        for name in vis:
            x, y = px(name)
            d.ellipse([x-7, y-7, x+7, y+7], fill=(255, 255, 255))
    img.save(out_path)
    return out_path

def describe_pose(kpts):
    """Short soft text description derived from keypoints — orientation + stride."""
    if not kpts:
        return ""
    parts = []
    nose = kpts.get("NOSE", {}).get("visibility", 0)
    if nose > 0.6:
        parts.append("head/face toward camera")
    elif nose < 0.25:
        parts.append("facing away from camera (back of head toward viewer)")
    else:
        parts.append("head at a three-quarter / profile angle")
    la, ra = kpts.get("LEFT_ANKLE", {}), kpts.get("RIGHT_ANKLE", {})
    if la.get("visibility", 0) > VIS and ra.get("visibility", 0) > VIS:
        dx = abs(la.get("x", 0) - ra.get("x", 0))
        dy = abs(la.get("y", 0) - ra.get("y", 0))
        if dx > 0.05 or dy > 0.05:
            parts.append("mid-stride, one leg forward (walking)")
        else:
            parts.append("feet close, weight transition")
    ls, rs = kpts.get("LEFT_SHOULDER", {}), kpts.get("RIGHT_SHOULDER", {})
    if ls.get("visibility", 0) > VIS and rs.get("visibility", 0) > VIS:
        sw = abs(ls.get("x", 0) - rs.get("x", 0))
        if sw < 0.10:
            parts.append("body turned to the side (narrow shoulder profile)")
        else:
            parts.append("shoulders broad to camera")
    return "; ".join(parts)

# ── Shared prompt blocks ──────────────────────────────────────────────────────
IDENTITY_LOCK = (
    "IDENTITY LOCK: The woman must be the exact same person as the Look 3 identity anchors — "
    "strong defined brows, deep-set almond eyes, high cheekbones, straight narrow nose, full lips, "
    "defined jawline, light olive skin, centre-parted dark hair to the shoulders. "
    "Not a generic brunette, not an averaged face.\n"
)
LOOK_LOCK = (
    "LOOK LOCK (Look 3): cropped charcoal blazer (dark grey, NOT black, natural-waist hem), "
    "white shirt with visible collar, muted olive tie (dusty khaki-green, NOT black/navy), "
    "wide faded blue denim trousers (distinctly wide leg), black leather oxford shoes. "
    "Do not convert to a corporate black suit, school uniform, or slim trousers.\n"
)
STREET = (
    "SCENE: quiet Parisian cobblestone street — limestone Haussmann facades, shuttered windows, "
    "wrought-iron railings, grey cobblestones, soft diffused neutral daylight, background softly out of focus.\n"
)
REALISM = (
    "REALISM: photorealistic cinematic quality, natural skin texture, single subject only, "
    "no extra people, no duplicated face or limbs, no text or watermark.\n"
)
NEG_COMMON = ("different face, changed identity, generic woman, extra person, duplicated body, "
              "bride, wedding, veil, wrong outfit, black tie, slim trousers, corporate suit")

def pose_ref_role():
    return ("A grey image with a white stick-figure skeleton is provided as a POSE GUIDE only. "
            "Match its body orientation, limb configuration and stride as closely as possible. "
            "The skeleton defines pose ONLY — it carries no identity, clothing, or scene information.\n")

# ── Per-shot plan ─────────────────────────────────────────────────────────────
def prompt_head(which):
    turn = ("She is partly turned away from camera in an over-the-shoulder / side-back framing, "
            "face mostly hidden, only a sliver of profile visible."
            if which == "START" else
            "She turns her head back more clearly toward camera in a natural unhurried glance, "
            "now showing a three-quarter to near-front view of her face.")
    return (
        "Medium over-shoulder portrait on a Parisian street, waist-up, vertical 9:16.\n"
        f"HEAD ORIENTATION ({which}): {turn}\n"
        "Quiet, private, unposed expression. Candid street moment.\n"
        + IDENTITY_LOCK + LOOK_LOCK + STREET + REALISM
    )

def prompt_walk_002(which):
    # Reference (beach shot_002): WIDE full-body, three-quarter/side walking, NOT back-view.
    phase = ("at the beginning of her walking stride" if which == "START"
             else "a step further along, mid-stride, continuing through the street")
    return (
        "Wide full-body establishing shot on a Parisian cobblestone street, vertical 9:16, camera at eye level.\n"
        f"POSE ({which}): full body walking through the street in a natural THREE-QUARTER view — "
        f"body angled to camera (not a flat front portrait, not a flat back view), matching the white "
        f"pose skeleton provided. She is {phase}. Relaxed unhurried stride, arms natural at her sides.\n"
        + pose_ref_role()
        + "WIDE framing: the figure sits within the street — limestone Haussmann facades and grey "
          "cobblestones around her, deep perspective behind. Wide denim legs and oxford shoes read clearly.\n"
        + IDENTITY_LOCK + LOOK_LOCK + STREET + REALISM
    )

def prompt_walk_004(which):
    # Reference (beach shot_004): WIDE three-quarter/side walking; at the END a hand lifts toward the face.
    gesture = ("arms relaxed at her sides, mid-stride" if which == "START"
               else "one hand lifting naturally toward her face or hair as she walks")
    return (
        "Wide-to-medium full-body walking shot along a Parisian Haussmann facade, vertical 9:16, camera at eye level.\n"
        f"POSE ({which}): full body walking in a THREE-QUARTER to side view, matching the white pose "
        f"skeleton provided — {gesture}. Preserve the walking body orientation, stride and body scale.\n"
        + pose_ref_role()
        + IDENTITY_LOCK + LOOK_LOCK + STREET + REALISM
    )

def prompt_feet(which):
    foot = "left foot forward, mid-step" if which == "START" else "right foot forward, the next step"
    return (
        "Extreme low-angle close-up on a Parisian cobblestone street, vertical 9:16, camera near ground level.\n"
        f"LOWER-BODY INSERT ({which}): only lower legs and feet in frame — no face, head, torso or arms. "
        f"Walking stride: {foot}.\n"
        "Wide faded blue denim trouser hem draping over black leather oxford shoes, stepping across grey cobblestones.\n"
        "Grey irregular cobblestones fill the frame; soft diffused daylight.\n"
        "Do not show any face or upper body. No bare feet, no white dress hem.\n"
        + REALISM
    )

# strategy, quality, slot-builder, prompt-builder per shot
SHOTS = [
    {
        "shot_id": "shot_001", "strategy": "head_orientation", "quality": "high",
        "neg": NEG_COMMON + ", looking straight into camera, full front-facing portrait",
        "slots": lambda which, skel: [FRONT_ANCHOR, LOOK_CLOSEUP, LOOK_FRONT, PROFILE_ANCHOR],
        "prompt": lambda which: prompt_head(which),
        "uses_pose": False,
    },
    {
        "shot_id": "shot_002", "strategy": "pose_driven", "quality": "medium",
        "neg": NEG_COMMON + ", flat front portrait, flat back view, standing still",
        "slots": lambda which, skel: [skel, SCENE_ESTAB if SCENE_ESTAB.exists() else SCENE_BOARD, FRONT_ANCHOR, LOOK_FRONT],
        "prompt": lambda which: prompt_walk_002(which),
        "uses_pose": True,
    },
    {
        "shot_id": "shot_003", "strategy": "text_framing", "quality": "medium",
        "neg": "face, head, torso, arms, upper body, standing pose, bare feet, white dress hem, "
               "slim trousers, extra legs, duplicated feet",
        "slots": lambda which, skel: [SCENE_BOARD, LOOK_FRONT, LOOK_SHEET],
        "prompt": lambda which: prompt_feet(which),
        "uses_pose": False,
    },
    {
        "shot_id": "shot_004", "strategy": "pose_driven", "quality": "high",
        "neg": NEG_COMMON + ", front-facing full portrait, standing still",
        "slots": lambda which, skel: [FRONT_ANCHOR, skel, PROFILE_ANCHOR, LOOK_FRONT],
        "prompt": lambda which: prompt_walk_004(which),
        "uses_pose": True,
    },
]

FORBIDDEN = ["bride","bridal","wedding","veil","copied source outfit","same outfit as source"]
def guard(p):
    return [w for w in FORBIDDEN if w in p.lower()]

def gen(shot, which, images, prompt, quality, out_path):
    hits = guard(prompt)
    if hits:
        print(f"[{shot}/{which}] forbidden terms {hits} — skip"); return False
    if out_path.exists() and not ALLOW_OVERWRITE:
        print(f"[{shot}/{which}] exists — skip (ALLOW_OVERWRITE=False)"); return True
    print(f"\n[{shot}/{which}] slots: {[Path(p).name for p in images]}")
    handles = []
    try:
        for p in images:
            handles.append(open(p, "rb"))
        resp = client.images.edit(
            model="gpt-image-1", image=handles, prompt=prompt,
            size="1024x1536", quality=quality, input_fidelity="high", n=1,
        )
        data = base64.b64decode(resp.data[0].b64_json)
        out_path.write_bytes(data)
        print(f"[{shot}/{which}] SAVED {out_path.name} ({len(data)//1024} KB)")
        return True
    except Exception as e:
        print(f"[{shot}/{which}] ERROR: {e}"); return False
    finally:
        for h in handles:
            h.close()

# ── Generate ──────────────────────────────────────────────────────────────────
plan = []
made = {}   # (shot_id, which) -> path
for shot in SHOTS:
    sid = shot["shot_id"]
    frames = POSE.get(sid, {})
    motion = MOTION.get(sid, "")
    shot_plan = {"shot_id": sid, "strategy": shot["strategy"],
                 "quality": shot["quality"], "conditioning": "soft_reference_guided",
                 "claims_exact_motion_transfer": False, "frames": {}}
    for which in ("START", "END"):
        # pose source frame: START->start, END->end
        tag = "start" if which == "START" else "end"
        kpts = (frames.get(tag) or {}).get("keypoints") if frames else None
        pose_txt = describe_pose(kpts) if shot["uses_pose"] else ""
        skel_path = None
        if shot["uses_pose"]:
            skel_path = render_skeleton(kpts, SKEL_DIR / f"{sid}_{tag}_skeleton.png")
        images = shot["slots"](which, skel_path)
        prompt = shot["prompt"](which)   # orientation defined by the shot, not by describe_pose
        out_path = OUT_DIR / f"{sid}_{which}_keyframe.png"
        if PREVIEW_ONLY:
            ok = False
            print(f"[{sid}/{which}] [{shot['strategy']}] orientation → defined by shot prompt "
                  f"(pose from skeleton). describe_pose (metadata only): {pose_txt or '(n/a)'}")
            print(f"           slots: {[Path(p).name for p in images]}")
        else:
            ok = gen(sid, which, images, prompt, shot["quality"], out_path)
        if ok:
            made[(sid, which)] = out_path
        shot_plan["frames"][which] = {
            "keyframe": str(out_path),
            "pose_source_frame": (frames.get(tag, {}) or {}).get("frame_index") if shot["uses_pose"] else None,
            "pose_confidence": (frames.get(tag, {}) or {}).get("pose_confidence") if shot["uses_pose"] else None,
            "skeleton_control": str(skel_path) if skel_path else None,
            "derived_pose_text": pose_txt or None,
            "slots": [Path(p).name for p in images],
            "prompt": prompt,
            "ok": ok,
        }
    plan.append(shot_plan)

# ── Generation plan JSON ──────────────────────────────────────────────────────
plan_path = OUT_DIR / "street_start_end_generation_plan.json"
plan_path.write_text(json.dumps({
    "run": "live_test_04_street_look3 · start_end",
    "note": "Graded reference-guided generation, aligned to the beach reference per shot. "
            "shot_002/004 pose-driven via CLEAN skeleton image (three-quarter walking, matching "
            "the reference orientation); shot_001 head-orientation (turn toward camera); shot_003 "
            "feet/text-framing. Orientation is defined by each shot prompt to match the reference; "
            "describe_pose() is kept as metadata only and is NOT injected into prompts (it was "
            "unreliable). Not exact frame-level motion transfer. Kling NOT called.",
    "reference_video": pose_meta.get("reference_video"),
    "shots": plan,
}, indent=2))

# ── Contact sheet: rows = shots, cols = [START | END], labelled ──────────────
def _font(sz):
    for c in ("/System/Library/Fonts/Helvetica.ttc","/Library/Fonts/Arial.ttf"):
        if Path(c).exists():
            try: return ImageFont.truetype(c, sz)
            except Exception: pass
    return ImageFont.load_default()
F = _font(22)

col_h, PAD, LBL = 520, 14, 40

def build_sheet(cell_fn, sheet_path):
    rows = [[cell_fn(shot, which) for which in ("START", "END")] for shot in SHOTS]
    col_w = max(max(im.width for im, _ in r) for r in rows)
    sheet_w = PAD + (col_w + PAD) * 2
    sheet_h = PAD + (LBL + col_h + PAD) * len(rows)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    y = PAD
    for r in rows:
        x = PAD
        for im, lbl in r:
            d.text((x, y), lbl, fill=(120, 180, 255), font=F)
            sheet.paste(im, (x, y + LBL))
            x += col_w + PAD
        y += LBL + col_h + PAD
    sheet.save(sheet_path)
    return sheet_path

def _fit(im):
    w = int(im.width * (col_h / im.height))
    return im.resize((w, col_h))

if PREVIEW_ONLY:
    # Skeleton / pose-control preview — the thing to review before spending.
    def cell_preview(shot, which):
        sid = shot["shot_id"]; tag = "start" if which == "START" else "end"
        lbl = f"{sid} · {shot['strategy']} · {which}"
        if shot["uses_pose"]:
            sp = SKEL_DIR / f"{sid}_{tag}_skeleton.png"
            if sp.exists():
                return _fit(Image.open(sp).convert("RGB")), lbl + " · SKELETON"
        return (Image.new("RGB", (int(col_h*0.66), col_h), (40, 40, 40)),
                lbl + (" · no pose (text-driven)"))
    sheet_path = build_sheet(cell_preview, OUT_DIR / "street_pose_control_preview_sheet.png")

    print("\n" + "=" * 60)
    print("PREVIEW ONLY — NO OpenAI CALL, $0 SPENT")
    print("=" * 60)
    print("  Pose-driven shots (skeleton + derived text to review):")
    for sp in plan:
        if sp["shot_id"] in ("shot_002", "shot_004"):
            for w in ("START", "END"):
                fr = sp["frames"][w]
                print(f"    {sp['shot_id']} {w}: conf={fr['pose_confidence']} "
                      f"src_frame={fr['pose_source_frame']}  text: {fr['derived_pose_text']}")
    print(f"\n  pose-control skeletons : {SKEL_DIR}")
    print(f"  preview sheet          : {sheet_path}")
    print(f"  plan json (+ prompts)  : {plan_path}")
    print("\n  Review the skeletons + derived text. If correct, set PREVIEW_ONLY=False and re-run.")
    print("=" * 60)
else:
    def cell_gen(shot, which):
        sid = shot["shot_id"]
        p = made.get((sid, which))
        lbl = f"{sid} · {shot['strategy']} · {which}"
        if p and Path(p).exists():
            return _fit(Image.open(p).convert("RGB")), lbl
        return (Image.new("RGB", (int(col_h*0.66), col_h), (40, 40, 40)), lbl + " · (failed)")
    sheet_path = build_sheet(cell_gen, OUT_DIR / "street_start_end_keyframe_contact_sheet.png")

    print("\n" + "=" * 60)
    print("STREET START/END KEYFRAMES — GENERATED (KLING NOT CALLED)")
    print("=" * 60)
    for sp in plan:
        st = "  ".join(f"{w}:{'ok' if sp['frames'][w]['ok'] else 'FAIL'}" for w in ("START", "END"))
        print(f"  {sp['shot_id']:9s} [{sp['strategy']:16s}] {st}")
    print(f"\n  keyframes    : {OUT_DIR}")
    print(f"  contact sheet: {sheet_path}")
    print(f"  plan json    : {plan_path}")
    print("\n  Review the contact sheet. Kling was NOT called.")
    print("  Graded conditioning — no exact frame-level motion transfer claimed.")
    print("=" * 60)
