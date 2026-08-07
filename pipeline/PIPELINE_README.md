# pipeline/

Reference-Driven Agentic Short-Form Video Generation — pipeline code.

Takes a reference short video + IP character images + a new scene prompt, breaks the reference into a shot/beat/pose template, regenerates per-shot with the IP character, then runs an automatic evaluation-repair loop until everything passes or hits the retry limit.

Mac orchestrates, APIs generate, local tools evaluate. No local GPU needed for the main path.

---

## quick start

```bash
# prerequisites (mac)
brew install ffmpeg
pip install -r requirements_best.txt

# set keys
export OPENAI_API_KEY=sk-...
export KLING_ACCESS_KEY=...
export KLING_SECRET_KEY=...

# phase 0 first — do not skip this
python run.py phase0

# then full pipeline
python run.py all \
  --video path/to/reference.mp4 \
  --scene "character walks through a greenhouse at dawn"
```

If you don't have a reference video yet, you can hand-author a storyboard JSON and skip stages 1-2:

```bash
python run.py all --manual storyboard.json --scene "..."
```

---

## file structure

```
pipeline/
├── config.py              — thresholds, api keys, model names, backend selection
├── state.py               — reads/writes project_state.json, logs every attempt
├── run.py                 — cli entry point
├── phase0_test.py         — feasibility test: identity vs pose control
│
├── stage1_analyze.py      — shot cuts (PySceneDetect) + beats (librosa) + poses (MediaPipe)
├── stage2_template.py     — beat alignment + storyboard JSON
├── stage3_generate.py     — per-shot generation orchestrator
├── stage4_evaluate.py     — identity / pose / framing / beat scoring
├── stage5_repair.py       — agentic repair loop
│
├── generators/
│   ├── base.py            — shared prompt builder, abstract interface
│   ├── api_gen.py         — OpenAI Images API + Kling (main path)
│   └── local_gen.py       — InstantID + CogVideoX/Wan2.1 (school GPU)
│
├── requirements_best.txt  — mac / api pipeline
└── requirements_free.txt  — linux / school 4080s
```

---

## two backends

### api (default, mac)
```
GENERATOR_BACKEND=api   VIDEO_BACKEND=kling
```
OpenAI Images API for keyframes — same model as ChatGPT image generation, face consistency is genuinely better than most specialised local models for zero-shot use. Model is configurable via `OPENAI_IMAGE_MODEL` in config.py (default: `gpt-image-2`, override to `gpt-image-1` if you don't have access yet).

Kling 1.6 for image-to-video. Submits a task, polls every 10s, downloads the clip when done. Typical wait: 2-4 min per clip.

### local (school 4080s, 16GB VRAM)
```
GENERATOR_BACKEND=local   VIDEO_BACKEND=cogvideox
```
InstantID for keyframes — extracts ArcFace embedding from the IP reference image and injects it directly into the diffusion process. Requires `pip install -r requirements_free.txt` on the school machine (Linux, CUDA).

CogVideoX-5b-I2V for video — fits in 16GB VRAM fine. Wan2.1-I2V-14B-480P also fits on 4080s (the 480P variant was designed for lower VRAM). Both are open source on HuggingFace.

Switching backend doesn't change evaluation or repair — those always run locally.

---

## project_state.json

Everything lives in one JSON file. Every shot has a decision log that records every generation attempt:

```json
{
  "shot_id": "shot_003",
  "evaluation": {
    "status": "pass",
    "attempts": [
      {
        "attempt_num": 1,
        "scores": {
          "identity": 0.51,
          "pose": 0.74,
          "framing": 0.82,
          "beat_alignment_ms": 140.0
        },
        "verdict": "fail",
        "diagnosis": "identity drift (score=0.51 < 0.60)",
        "repair_action": "targeted repair for identity_drift + seed change"
      },
      {
        "attempt_num": 2,
        "scores": {
          "identity": 0.67,
          "pose": 0.78,
          "framing": 0.85,
          "beat_alignment_ms": 95.0
        },
        "verdict": "pass",
        "diagnosis": "",
        "repair_action": "none"
      }
    ]
  }
}
```

Shots that hit `MAX_REPAIR_ATTEMPTS` (default: 3) without passing get status `needs_human` instead of staying on `fail`. The decision log is the main dissertation evidence that the system is agentic and not just a linear generation pipeline.

---

## evaluation metrics

| metric | tool | pass threshold | file |
|---|---|---|---|
| IP identity | ArcFace via DeepFace | ≥ 0.60 (calibrate first) | stage4_evaluate.py |
| pose similarity | MediaPipe keypoints | ≥ 0.85 | stage4_evaluate.py |
| framing accuracy | landmark span heuristic | ≥ 0.75 | stage4_evaluate.py |
| beat alignment | cut-to-beat delta | ≤ 250ms | stage4_evaluate.py |

Calibrate `IDENTITY_THRESHOLD` in config.py after running Phase 0 — don't leave it at 0.60 without checking it makes sense for your character's face embedding distribution.

```bash
python run.py phase0 --calibrate   # generates 5 samples, tells you mean ± std
```

---

## repair logic

Base layer (always runs): seed change + stronger prompt emphasis, up to `MAX_REPAIR_ATTEMPTS` times.

Enhanced layer: classifies the failure type first, then targets the fix.
- identity drift → increase IP adapter scale in prompt emphasis
- pose mismatch → strengthen pose description
- framing error → rewrite framing instruction
- beat misalignment → adjust cut timing (no regeneration needed)

The diagnosis can misclassify — that's expected and worth documenting honestly in the dissertation. The ablation comparison (repair ON vs OFF) will show whether the targeted diagnosis actually helps vs just doing a random seed change.

---

## ablation experiment

Run the baseline (no repair) first, copy the state file, then run with repair:

```bash
# baseline — single pass, no retry
python run.py all --video ref.mp4 --scene "..." --baseline
cp project_state.json project_state_baseline.json

# with repair loop
python run.py all --video ref.mp4 --scene "..."
cp project_state.json project_state_repair.json
```

Compare: pass rate, total attempts, identity scores across attempts.

---

## phase 0

Run this before building anything else. It generates 3 keyframes with different poses using your IP character images and scores face identity on each one.

```bash
python run.py phase0             # uses OPENAI_IMAGE_MODEL from config
python run.py phase0 --backend local   # test InstantID on school machine
```

If ≥1 pose fails the identity threshold: either lower `IDENTITY_THRESHOLD` (document the tradeoff) or bump `ip_adapter_scale` in the generator. If all 3 fail badly, downgrade scope to keyframe-remake — author consistent keyframes manually and use the pipeline only for evaluation and assembly. That's still a valid dissertation.

---

## config

Key things to set in config.py before running:

```python
OPENAI_IMAGE_MODEL = "gpt-image-2"   # or "gpt-image-1" if you don't have gpt-image-2 access

IDENTITY_THRESHOLD = 0.60   # SET THIS after running phase0 --calibrate
MAX_REPAIR_ATTEMPTS = 3

IP_REFERENCE_IMAGES = [...]   # currently pointing to desktop/character_look/look4b_*.png
IP_CHARACTER_DESCRIPTION = "..."   # update if you switch looks
```

---

## running on school machine

```bash
# check cuda
nvcc --version
nvidia-smi

# pytorch with cuda (adjust cu121 to your version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

pip install -r requirements_free.txt

export GENERATOR_BACKEND=local
export VIDEO_BACKEND=cogvideox   # 4080s (16GB) — fits fine
# VIDEO_BACKEND=wan also works on 4080s with 480P variant

python run.py phase0 --backend local
python run.py all --scene "..." --manual storyboard.json
```

The evaluation and repair stages run the same on both machines — same ArcFace scores, same decision log format, same state file. So results are directly comparable across backends.
