"""
regen_anchor.py — Regenerate identity anchor with quality="high" + input_fidelity="high"

Overwrites look3_identity_anchor_street.png unconditionally.
Run this before regen_shot001_004_v2.py.

Usage:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 regen_anchor.py
"""

import base64
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

LOOK_DIR   = Path(__file__).parent / "assets" / "looks" / "look_3_tailored_self"
SCENE_REF  = Path(__file__).parent / "assets" / "scenes" / "built_in" / "scene_02_modern_street" / "references"
ANCHOR_OUT = LOOK_DIR / "look3_identity_anchor_street.png"

PROMPT = """
ROLE OF REFERENCE IMAGES

Image A (first image) is the PRIMARY identity reference.
Preserve the exact same woman — facial structure, brow shape, eye shape, nose, lips, jawline, skin tone, hair.

Image B (second image) is the outfit and body reference.
Preserve the Look 3 outfit, body proportions, garment silhouette, and styling.

Image C (third image) is the supplemental profile/look reference.
Reinforce the same woman from an alternate angle. Do not treat it as a collage of different people.

Image D (fourth image) is the street-scene mood reference.
Use it only for lighting mood, Parisian street atmosphere, limestone architecture, and cobblestone.
Do not use Image D to create or alter the character's face.

CORE TASK

Generate a clean identity anchor image for the street-scene run.
Show the exact same woman from Image A, wearing the exact same Look 3 outfit from Image B,
placed naturally into a quiet Parisian cobblestone street environment.

This is not a fashion editorial. This is not a new character design.
This is an identity-lock reference image for use as slot[0] in subsequent shots.

IDENTITY LOCK

The visible character must be the exact same woman shown in Image A.
Do not generate a similar woman. Do not generate a generic elegant brunette.
Do not average the references into a new face. Do not soften or reinterpret the facial structure.

Preserve exactly:
- strong defined brows, horizontal arch
- deep-set almond-shaped eyes, same spacing
- high cheekbones
- straight narrow nose bridge
- full lips
- defined jawline and chin
- light olive skin tone
- centre-parted dark hair, falls to shoulders
- same overall facial proportions as Image A

LOOK LOCK — LOOK 3 · THE TAILORED SELF

Exact outfit from Image B:
- cropped charcoal blazer (dark grey, NOT black, hemline at natural waist)
- white cotton shirt, collar visible
- muted olive tie (dusty khaki-green, NOT black, NOT dark navy)
- wide faded blue denim trousers (distinctly wide and relaxed leg)
- black leather oxford shoes

Do not invent variations. Do not convert to: corporate black suit, school uniform, slim trousers.

COMPOSITION

Waist-up or upper-thigh frame, natural three-quarter angle.
Face clearly visible and sharp — this image will be used as identity reference for later shots.
Quiet, introspective expression. She may look slightly off-camera.
Simple, stable pose — this is not an action frame.

SCENE

Quiet Parisian cobblestone street. Limestone Haussmann facades, shuttered windows, wrought iron
railings, grey cobblestones, soft diffused daylight. Background may be softly out of focus.

REALISM

Photorealistic, cinematic quality. Natural skin texture. No plastic skin. No over-polished
commercial lighting. No AI-smoothed fabric. No poster composition.

GUARD

One visible character only. No extra people. No duplicated faces. No identity drift.
No outfit drift. No text. No watermarks.
"""


def main():
    # ── Resolve input images ──────────────────────────────────────────────────
    profile_crop = LOOK_DIR / "look3_profile_crop.png"
    profile_ref  = profile_crop if profile_crop.exists() else LOOK_DIR / "look3_sheet.png"

    scene_ref = SCENE_REF / "main_scene_board_16x9.jpg"
    if not scene_ref.exists():
        available = list(SCENE_REF.glob("*")) if SCENE_REF.exists() else []
        print(f"[regen_anchor] ERROR: scene ref not found: {scene_ref}")
        print(f"  Available: {[p.name for p in available]}")
        sys.exit(1)

    anchor_inputs = [
        LOOK_DIR / "look3_closeup.png",   # [0] PRIMARY face
        LOOK_DIR / "look3_front.png",     # [1] outfit / body
        profile_ref,                       # [2] profile angle
        scene_ref,                         # [3] scene mood only
    ]

    print("=" * 60)
    print("REGEN ANCHOR — look3_identity_anchor_street.png")
    print("  quality=high  |  input_fidelity=high")
    print("=" * 60)
    for i, p in enumerate(anchor_inputs):
        exists = "✓" if p.exists() else "✗ MISSING"
        print(f"  image[{i}] {p.name}  {exists}")

    missing = [p for p in anchor_inputs if not p.exists()]
    if missing:
        print(f"\nERROR: missing input(s): {[p.name for p in missing]}")
        sys.exit(1)

    print("\n[regen_anchor] calling OpenAI images.edit ...")
    handles = []
    try:
        for p in anchor_inputs:
            handles.append(open(p, "rb"))
        response = client.images.edit(
            model="gpt-image-1",
            image=handles,
            prompt=PROMPT,
            size="1024x1536",
            quality="high",
            input_fidelity="high",
            n=1,
        )
        img_data = base64.b64decode(response.data[0].b64_json)
        ANCHOR_OUT.write_bytes(img_data)
        size_kb = len(img_data) // 1024
        print(f"\n[regen_anchor] ✓ SAVED: {ANCHOR_OUT.name}  ({size_kb} KB)")
    except Exception as e:
        print(f"\n[regen_anchor] ERROR: {e}")
        raise
    finally:
        for h in handles:
            h.close()


if __name__ == "__main__":
    main()
