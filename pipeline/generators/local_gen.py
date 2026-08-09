"""
generators/local_gen.py — FREE PIPELINE

Keyframe generation: InstantID via diffusers (HuggingFace, free)
  - Specifically designed for face identity preservation
  - Runs locally, requires ~16GB VRAM (or 8GB with quantization)
  - Falls back to IP-Adapter FaceID if InstantID unavailable

Video generation: CogVideoX-5b (HuggingFace, free) or Wan2.1
  - CogVideoX: ~20GB VRAM, good quality
  - Wan2.1 (recommended): better quality, also free on HF

Requirements: pip install diffusers transformers accelerate
              pip install insightface onnxruntime
Hardware: CUDA GPU with 12GB+ VRAM recommended.
          M1/M2 Mac: use device="mps" (slower but works)
"""

import os
import time
import uuid
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from config import HF_TOKEN, OUTPUT_DIR, VIDEO_DURATION_S, VIDEO_FPS
from .base import GeneratorBase


def _get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class LocalGenerator(GeneratorBase):
    """
    Free pipeline: InstantID + CogVideoX (or Wan2.1).
    Models are loaded lazily on first use.
    """

    def __init__(self, video_backend: str = "cogvideox"):
        """
        video_backend: "cogvideox" | "wan"
        """
        self.device = _get_device()
        self.video_backend = video_backend
        self._image_pipeline = None
        self._video_pipeline = None
        self._face_analysis = None

        self.keyframe_dir = OUTPUT_DIR / "keyframes"
        self.clip_dir = OUTPUT_DIR / "clips"
        self.keyframe_dir.mkdir(parents=True, exist_ok=True)
        self.clip_dir.mkdir(parents=True, exist_ok=True)

        print(f"[local_gen] device={self.device}, video_backend={video_backend}")

    # ── Image Pipeline (InstantID) ─────────────────────────────────────────

    def _load_image_pipeline(self):
        if self._image_pipeline is not None:
            return

        print("[local_gen] loading InstantID pipeline...")
        from diffusers import StableDiffusionXLPipeline
        from huggingface_hub import hf_hub_download

        # InstantID uses SDXL + face ControlNet + IP-Adapter
        # Model: InstantX/InstantID
        try:
            from pipeline_stable_diffusion_xl_instantid import StableDiffusionXLInstantIDPipeline
        except ImportError:
            # Download the pipeline script from InstantID repo
            import subprocess
            subprocess.run([
                "wget", "-q",
                "https://huggingface.co/InstantX/InstantID/resolve/main/pipeline_stable_diffusion_xl_instantid.py"
            ], cwd=str(OUTPUT_DIR.parent))
            import sys
            sys.path.insert(0, str(OUTPUT_DIR.parent))
            from pipeline_stable_diffusion_xl_instantid import StableDiffusionXLInstantIDPipeline

        from diffusers.models import ControlNetModel

        # Load ControlNet for identity
        controlnet_path = hf_hub_download(
            repo_id="InstantX/InstantID",
            filename="ControlNetModel/diffusion_pytorch_model.safetensors",
            token=HF_TOKEN or None,
        )
        controlnet = ControlNetModel.from_pretrained(
            "InstantX/InstantID",
            subfolder="ControlNetModel",
            torch_dtype=torch.float16,
        )

        self._image_pipeline = StableDiffusionXLInstantIDPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            controlnet=controlnet,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        self._image_pipeline.to(self.device)

        # Load IP-Adapter face
        ip_adapter_path = hf_hub_download(
            repo_id="InstantX/InstantID",
            filename="ip-adapter.bin",
            token=HF_TOKEN or None,
        )
        self._image_pipeline.load_ip_adapter_instantid(ip_adapter_path)
        print("[local_gen] InstantID loaded ✓")

    def _load_face_analysis(self):
        if self._face_analysis is not None:
            return
        from insightface.app import FaceAnalysis
        self._face_analysis = FaceAnalysis(name="antelopev2", root="./insightface_models")
        self._face_analysis.prepare(ctx_id=0 if self.device == "cuda" else -1, det_size=(640, 640))
        print("[local_gen] FaceAnalysis loaded ✓")

    # ── Video Pipeline (CogVideoX / Wan) ──────────────────────────────────

    def _load_video_pipeline(self):
        if self._video_pipeline is not None:
            return

        if self.video_backend == "cogvideox":
            print("[local_gen] loading CogVideoX-5b-I2V...")
            from diffusers import CogVideoXImageToVideoPipeline

            self._video_pipeline = CogVideoXImageToVideoPipeline.from_pretrained(
                "THUDM/CogVideoX-5b-I2V",
                torch_dtype=torch.bfloat16,
                token=HF_TOKEN or None,
            )
            self._video_pipeline.enable_model_cpu_offload()
            self._video_pipeline.vae.enable_tiling()
            print("[local_gen] CogVideoX loaded ✓")

        elif self.video_backend == "wan":
            print("[local_gen] loading Wan2.1-I2V-14B...")
            # Wan2.1 requires ~22GB VRAM or CPU offload
            from diffusers import WanImageToVideoPipeline
            from diffusers.schedulers import UniPCMultistepScheduler

            self._video_pipeline = WanImageToVideoPipeline.from_pretrained(
                "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
                torch_dtype=torch.float16,
                token=HF_TOKEN or None,
            )
            self._video_pipeline.enable_model_cpu_offload()
            print("[local_gen] Wan2.1 loaded ✓")

    # ── Public Interface ───────────────────────────────────────────────────

    def generate_keyframe(
        self,
        shot: dict,
        ip_images: list[str],
        character_description: str,
        scene_prompt: str,
        repair_hints: dict | None = None,
    ) -> str:
        self._load_face_analysis()
        self._load_image_pipeline()

        prompt = self.build_prompt(shot, character_description, scene_prompt, repair_hints)
        negative_prompt = (
            "blurry, deformed face, changed identity, wrong person, "
            "different nose, different eyes, different bone structure, "
            "mutation, extra limbs, low quality, watermark"
        )

        # Extract face embedding from primary IP reference
        ref_img = Image.open(ip_images[0]).convert("RGB")
        ref_arr = np.array(ref_img)
        faces = self._face_analysis.get(ref_arr)
        if not faces:
            raise RuntimeError(f"No face detected in IP reference: {ip_images[0]}")
        face_info = sorted(faces, key=lambda x: x.bbox[2] - x.bbox[0], reverse=True)[0]

        # Use pose image if available (passed as ControlNet condition)
        pose_cond = None
        if shot.get("pose_image_path") and os.path.exists(shot["pose_image_path"]):
            pose_cond = Image.open(shot["pose_image_path"]).convert("RGB")

        print(f"[local_gen] generating keyframe for {shot['shot_id']}")

        result = self._image_pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image_embeds=face_info,
            image=pose_cond,          # ControlNet condition
            controlnet_conditioning_scale=0.8 if pose_cond else 0.0,
            ip_adapter_scale=0.8,
            num_inference_steps=30,
            guidance_scale=5.0,
            height=1792,
            width=1024,
        )

        out_path = self.keyframe_dir / f"{shot['shot_id']}.png"
        result.images[0].save(str(out_path))
        print(f"[local_gen] keyframe saved → {out_path}")
        return str(out_path)

    def generate_video_clip(
        self,
        keyframe_path: str,
        shot: dict,
        scene_prompt: str,
    ) -> str:
        self._load_video_pipeline()

        motion_prompt = (
            f"{scene_prompt}. {shot.get('description', '')}. "
            "Slow cinematic camera. Subtle natural movement. "
            "Maintain character identity throughout clip."
        )

        keyframe = Image.open(keyframe_path).convert("RGB").resize((480, 854))  # 9:16 at 480p

        duration_s = min(shot.get("duration_s", VIDEO_DURATION_S), 6)
        num_frames = int(duration_s * VIDEO_FPS)

        print(f"[local_gen] generating {duration_s}s clip for {shot['shot_id']}")

        if self.video_backend == "cogvideox":
            result = self._video_pipeline(
                prompt=motion_prompt,
                image=keyframe,
                num_videos_per_prompt=1,
                num_inference_steps=50,
                num_frames=num_frames,
                guidance_scale=6.0,
                generator=torch.Generator(device="cpu").manual_seed(42),
            )
            frames = result.frames[0]

        elif self.video_backend == "wan":
            result = self._video_pipeline(
                prompt=motion_prompt,
                image=keyframe,
                num_frames=num_frames,
                guidance_scale=5.0,
                num_inference_steps=40,
            )
            frames = result.frames[0]

        # Save as MP4
        clip_path = self.clip_dir / f"{shot['shot_id']}.mp4"
        self._save_frames_as_video(frames, str(clip_path), fps=VIDEO_FPS)
        print(f"[local_gen] clip saved → {clip_path}")
        return str(clip_path)

    @staticmethod
    def _save_frames_as_video(frames, out_path: str, fps: int = 24):
        """Convert PIL frame list to MP4 using imageio."""
        import imageio
        writer = imageio.get_writer(out_path, fps=fps, codec="libx264", quality=8)
        for frame in frames:
            if isinstance(frame, Image.Image):
                writer.append_data(np.array(frame))
            else:
                writer.append_data(frame)
        writer.close()
