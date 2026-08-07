"""
config.py — Central configuration for the pipeline.
All thresholds, API keys, and backend selection live here.
Calibrate IDENTITY_THRESHOLD after Phase 0 test.

v0.1 Architecture:
  Mac orchestrates → APIs generate → local tools evaluate
  - Orchestration + evaluation: runs on Mac (CPU, no GPU needed)
  - Keyframe generation: OpenAI Images API (configurable model)
  - Video generation: Kling AI API
  - Local GPU path (school machine): set GENERATOR_BACKEND=local
"""

import os
from pathlib import Path

# Load .env file if present (project root or pipeline dir)
try:
    from dotenv import load_dotenv
    _env = Path(__file__).parent.parent / ".env"
    if not _env.exists():
        _env = Path(__file__).parent / ".env"
    if _env.exists():
        load_dotenv(_env)
        print(f"[config] loaded env from {_env}")
except ImportError:
    pass  # python-dotenv not installed — use system env vars

# ─── Paths ─────────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent.parent
PIPELINE_DIR = Path(__file__).parent
OUTPUT_DIR = ROOT_DIR / "outputs"
STATE_FILE = ROOT_DIR / "project_state.json"

IP_CHARACTER_DIR = Path("/Users/test/Desktop/character_look")

# LEGACY — only used when no look package is selected (generation is blocked in that case).
# Active generation resolves reference images via the selected look package.
# Do NOT add outfit-specific images here — identity references must be face/body only.
IP_REFERENCE_IMAGES: list[str] = []

# ─── Look Search Paths (resolution order) ─────────────────────────────────
# _resolve_look() checks these in order. First match with a look_package.json wins.
# look/ subdirs are also auto-scanned for folders that contain image files.
LOOK_SEARCH_PATHS = [
    ROOT_DIR / "assets" / "looks",    # built-in packages with look_package.json
    ROOT_DIR / "uploads" / "looks",   # user-uploaded custom looks
    ROOT_DIR / "look",                # project look/ directory (look1, look2_darkening-self, etc.)
]

# ─── API Keys (set via environment variables) ──────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
KLING_API_KEY = os.getenv("KLING_API_KEY", "")   # format: api-key-kling-xxxx
HF_TOKEN = os.getenv("HF_TOKEN", "")              # for free pipeline HuggingFace models

# ─── Backend Selection ─────────────────────────────────────────────────────

# "api"    → OpenAI Images API (keyframes) + Kling AI (video)  [v0.1 default, Mac]
# "local"  → InstantID (keyframes) + CogVideoX/Wan (video)     [school GPU machine]
GENERATOR_BACKEND = os.getenv("GENERATOR_BACKEND", "api")
VIDEO_BACKEND = os.getenv("VIDEO_BACKEND", "kling")  # "kling" | "cogvideox" | "wan"

# ─── OpenAI Image Model ────────────────────────────────────────────────────
# Configurable — do not hardcode in generation code.
# gpt-image-1: required model for this project
# Override via .env: OPENAI_IMAGE_MODEL=gpt-image-1
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

# ─── Evaluation Thresholds ─────────────────────────────────────────────────
# !!! Calibrate IDENTITY_THRESHOLD after Phase 0 test !!!
# Start with 0.60 and adjust based on your IP character's face embedding distribution.
# ArcFace cosine similarity: 1.0 = identical, lower = more different

IDENTITY_THRESHOLD = 0.80          # ArcFace cosine similarity — calibrated from Phase 0
                                   # Phase 0 results: pose_A=0.9549, pose_B=0.8540, pose_C=0.8488
                                   # All well above 0.80; threshold set at 0.80 to allow for
                                   # harder poses / scene changes while still catching real drift
POSE_THRESHOLD = 0.15              # Mean normalised keypoint distance (lower = stricter)
BEAT_ALIGNMENT_MAX_MS = 250        # Max allowed beat misalignment in milliseconds
BEAT_MAX_SNAP_DISTANCE_MS = 500    # If cut is >500ms from nearest beat, keep original cut
FRAMING_THRESHOLD = 0.75           # Composition/framing score (0-1)

# ─── Repair Settings ──────────────────────────────────────────────────────

MAX_REPAIR_ATTEMPTS = 3            # Per shot. After this → status = "needs_human"

# ─── Generation Settings ──────────────────────────────────────────────────

IMAGE_SIZE = "1024x1536"           # 9:16 portrait for short-form video (gpt-image-1 max portrait; 1024x1792 is not a valid size for this model)
IMAGE_QUALITY = os.getenv("IMAGE_QUALITY", "medium")  # "medium" for smoke test / fast demo; "high" for final production render
VIDEO_DURATION_S = 5               # Target clip duration in seconds
VIDEO_FPS = 24

# ─── IP Character Description (face / body ONLY — no outfit) ─────────────
# Describes ONLY the fixed physical identity: face, build, skin tone, hair texture.
# Outfit / hair styling / makeup / shoes come exclusively from the selected look package.
# NEVER add outfit, clothing, or look-specific wording here.

IP_CHARACTER_DESCRIPTION = (
    "The character is a young woman in her mid-twenties. "
    "She has a slender, tall build. Her face features: deep-set almond-shaped eyes, "
    "strong defined brows, high cheekbones, a straight nose, and full lips. "
    "Her skin tone is light olive. Her expression is composed, introspective, and quietly intense."
)

# ─── Forbidden Outfit Terms (generation guard) ────────────────────────────
# If any of these appear in a keyframe prompt AND the selected look is not
# explicitly bridal, generation is blocked before any API call is made.
# Only bridal-specific compound phrases are blocked.
# Generic words like "gown", "dress", or "veil" alone are NOT blocked —
# they are legitimate fashion/look terms. Only explicitly bridal phrasing is forbidden.
FORBIDDEN_OUTFIT_TERMS = [
    "bride",
    "bridal",
    "wedding",
    "wedding dress",
    "bridal gown",
    "cathedral veil",
    "white lace wedding gown",
    "copied source outfit",
    "same outfit as source",
]

# ─── Output dirs ──────────────────────────────────────────────────────────

def ensure_dirs():
    for d in [OUTPUT_DIR, OUTPUT_DIR / "keyframes", OUTPUT_DIR / "clips", OUTPUT_DIR / "poses"]:
        d.mkdir(parents=True, exist_ok=True)
