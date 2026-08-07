"""
generators/api_gen.py — API PIPELINE (v0.1 default)

Mac orchestrates, APIs generate, local tools evaluate.

Keyframe generation: OpenAI Images API
  - Model configurable via OPENAI_IMAGE_MODEL in config.py
    (default: gpt-image-2, override to gpt-image-1 if needed)
  - Passes IP reference images as input to the edit endpoint
  - Face consistency is its proven strength vs specialised local models

Video generation: Kling AI image-to-video API
  - Competitive quality, reasonable cost, good motion coherence

Cost reference (approx, may change):
  - gpt-image-2 high quality: check OpenAI pricing page
  - Kling 1.6 standard: ~$0.28 per 5s clip
"""

import base64
import os
import time
from pathlib import Path

import httpx
import requests
from openai import OpenAI

from config import (
    OPENAI_API_KEY, OPENAI_IMAGE_MODEL,
    KLING_API_KEY,
    OUTPUT_DIR, IMAGE_SIZE, IMAGE_QUALITY, VIDEO_DURATION_S,
)
from .base import GeneratorBase


def _encode_image(path: str) -> str:
    """Encode image as base64. Converts to JPEG RGB first (Kling rejects RGBA/PNG)."""
    from PIL import Image as PILImage
    import io
    img = PILImage.open(path).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def _kling_headers() -> dict:
    """Kling API now uses a single API key as Bearer token."""
    return {
        "Authorization": f"Bearer {KLING_API_KEY}",
        "Content-Type": "application/json",
    }


class APIGenerator(GeneratorBase):
    """
    v0.1 default pipeline: OpenAI Images API + Kling AI.
    All generation is API-based — no local GPU required.
    """

    def __init__(self):
        self._client = None  # Lazy-init — only needed for keyframe generation
        self.model = OPENAI_IMAGE_MODEL
        self.keyframe_dir = OUTPUT_DIR / "keyframes"
        self.clip_dir = OUTPUT_DIR / "clips"
        self.keyframe_dir.mkdir(parents=True, exist_ok=True)
        self.clip_dir.mkdir(parents=True, exist_ok=True)
        print(f"[api_gen] OpenAI image model: {self.model}")

    @property
    def client(self):
        if self._client is None:
            if not OPENAI_API_KEY:
                raise RuntimeError("OPENAI_API_KEY not set. Export it or add it to your environment.")
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        return self._client

    def generate_keyframe(
        self,
        shot: dict,
        ip_images: list[str],
        character_description: str,
        scene_prompt: str,
        repair_hints: dict | None = None,
    ) -> str:
        """
        Generate keyframe via OpenAI Images API.

        Uses images.edit() when IP reference images are available — this gives
        the model direct visual grounding on the character's appearance,
        which is why face consistency is stronger than text-only prompting.

        Pose skeleton image (if extracted) is included as an additional reference.
        """
        prompt = self.build_prompt(shot, character_description, scene_prompt, repair_hints)

        ref_images = list(ip_images)
        if shot.get("pose_image_path") and os.path.exists(shot["pose_image_path"]):
            ref_images.append(shot["pose_image_path"])

        print(f"[api_gen] generating keyframe for {shot['shot_id']} via {self.model}")
        print(f"  prompt: {prompt[:120]}...")

        if ref_images:
            # gpt-image-1 supports up to 16 input images.
            # Slot layout: look refs first (IP conditioning), source frame last (structural).
            # Cap at 4: 3 look refs + 1 source frame (or fewer if not all present).
            capped = ref_images[:4]
            extra_files = []
            with open(capped[0], "rb") as primary_img:
                for path in capped[1:]:
                    extra_files.append(open(path, "rb"))
                try:
                    all_images = [primary_img] + extra_files
                    print(f"  [api_gen] images.edit inputs ({len(all_images)}):")
                    for i, p in enumerate(capped):
                        print(f"    [{i}] {os.path.basename(p)}")
                    response = self.client.images.edit(
                        model=self.model,
                        image=all_images[0] if len(all_images) == 1 else all_images,
                        prompt=prompt,
                        size=IMAGE_SIZE,
                        quality=IMAGE_QUALITY,
                        n=1,
                    )
                finally:
                    for f in extra_files:
                        f.close()
        else:
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=IMAGE_SIZE,
                quality=IMAGE_QUALITY,
                n=1,
            )

        img_data = base64.b64decode(response.data[0].b64_json)
        out_path = self.keyframe_dir / f"{shot['shot_id']}.png"
        out_path.write_bytes(img_data)
        print(f"[api_gen] keyframe saved → {out_path}")
        return str(out_path)

    def generate_video_clip(
        self,
        keyframe_path: str,
        shot: dict,
        scene_prompt: str,
    ) -> str:
        """
        Generate video clip via Kling AI image-to-video. Polls until complete.
        """
        print(f"[kling] generating clip for {shot['shot_id']}")

        # ── Motion prompt: prefer 5-track generation_brief.video_prompt ──
        # generation_brief is written by api_run_semantic_enrichment (Mode A)
        # or mb_build_json (Mode B). Falls back to legacy flat assembly.
        brief         = shot.get("generation_brief", {})
        brief_prompt  = brief.get("video_prompt", "")
        if brief_prompt:
            motion_prompt = brief_prompt
            print(f"  [kling] using generation_brief.video_prompt")
        else:
            motion_prompt = (
                f"{scene_prompt}. "
                f"{shot.get('description', '')}. "
                "Slow, cinematic motion. Subtle movement only. "
                "Preserve character appearance throughout."
            )
            print(f"  [kling] using legacy motion_prompt (no generation_brief)")

        # ── Negative prompt: merge brief.negative_prompt with baseline ──
        _base_negative = "face change, identity change, morphing, distortion, blur"
        brief_negative = brief.get("negative_prompt", "")
        if brief_negative:
            negative_prompt = f"{_base_negative}, {brief_negative}"
        else:
            negative_prompt = _base_negative

        headers = _kling_headers()
        payload = {
            "model_name": "kling-v1-6",
            "mode": "std",
            "image": _encode_image(keyframe_path),
            "prompt": motion_prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": 0.5,
            "duration": 10 if shot.get("duration_s", VIDEO_DURATION_S) > 7 else 5,  # Kling only accepts 5 or 10
            "aspect_ratio": "9:16",
        }

        # Retry submit up to 4 times with exponential backoff (handles 429 rate limits)
        for attempt in range(4):
            resp = requests.post(
                "https://api.klingai.com/v1/videos/image2video",
                headers=headers, json=payload, timeout=30,
            )
            if resp.status_code == 429:
                wait = 15 * (2 ** attempt)
                print(f"[kling] rate limited (429), waiting {wait}s before retry {attempt+1}/4...")
                time.sleep(wait)
                continue
            if not resp.ok:
                print(f"[kling] error {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
            break
        else:
            raise RuntimeError("Kling submit failed after 4 retries (persistent 429)")

        task_id = resp.json()["data"]["task_id"]
        print(f"[kling] task submitted: {task_id}")

        for attempt in range(60):
            time.sleep(10)
            poll = requests.get(
                f"https://api.klingai.com/v1/videos/image2video/{task_id}",
                headers=_kling_headers(), timeout=15,
            )
            data = poll.json()["data"]
            status = data["task_status"]
            print(f"[kling] status={status} ({attempt+1}/60)")

            if status == "succeed":
                video_url = data["task_result"]["videos"][0]["url"]
                clip_path = self.clip_dir / f"{shot['shot_id']}.mp4"
                with httpx.Client() as client:
                    r = client.get(video_url, timeout=60)
                    clip_path.write_bytes(r.content)
                print(f"[kling] clip saved → {clip_path}")
                return str(clip_path)
            elif status == "failed":
                raise RuntimeError(f"Kling task failed: {data}")

        raise TimeoutError(f"Kling task {task_id} timed out after 10 min")
