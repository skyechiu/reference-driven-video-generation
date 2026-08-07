"""
shot_001 keyframe generation — approved single-shot run.
gpt-image-1 / images.edit / 1024x1536 / medium quality
4 images: look3_closeup, look3_front, look3_sheet, shot_001_best (source_frame_structural)
"""
import base64, json, os, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

STATUS = ROOT / "outputs" / "_gen_shot001_status.json"
LOG    = ROOT / "outputs" / "_gen_shot001.log"

def write_status(ok, msg, out_path=""):
    STATUS.write_text(json.dumps({"ok": ok, "msg": msg, "out_path": out_path}, indent=2))

def log(msg):
    print(msg, flush=True)
    with open(LOG, "a") as f:
        f.write(msg + "\n")

# Clear old status
STATUS.unlink(missing_ok=True)
LOG.unlink(missing_ok=True)

log("=== shot_001 generation start ===")

api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    write_status(False, "OPENAI_API_KEY not set")
    log("ERROR: OPENAI_API_KEY not set")
    sys.exit(1)
log(f"API key: ...{api_key[-6:]}")

# Load state for prompt and run_id
state = json.loads((ROOT / "project_state.json").read_text())
shot  = next(s for s in state["shots"] if s["shot_id"] == "shot_001")
brief = shot["generation_brief"]
keyframe_prompt = brief["keyframe_prompt"]
run_id = state.get("config", {}).get("run_id", "live_test_03_4shots")
log(f"run_id: {run_id}")
log(f"prompt length: {len(keyframe_prompt)} chars")

# Image inputs — exact order
IMAGES = [
    ROOT / "assets/looks/look_3_tailored_self/look3_closeup.png",   # [0] face_closeup
    ROOT / "assets/looks/look_3_tailored_self/look3_front.png",     # [1] front_full_body
    ROOT / "assets/looks/look_3_tailored_self/look3_sheet.png",     # [2] overview
    ROOT / "outputs/ref_panels/shot_001_best.png",                  # [3] source_frame_structural
]
for i, p in enumerate(IMAGES):
    if not p.exists():
        write_status(False, f"Image missing: {p}")
        log(f"ERROR: missing {p}")
        sys.exit(1)
    log(f"  [{i}] {p.name} ✓")

# Output path
out_dir  = ROOT / "outputs" / "runs" / run_id / "keyframes"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "shot_001_keyframe_look3_preserve_scene_test.png"
log(f"output: {out_path}")

# Generate
from openai import OpenAI
client = OpenAI(api_key=api_key)

log("calling images.edit (model=gpt-image-1, size=1024x1536, quality=medium) ...")
handles = []
try:
    for p in IMAGES:
        handles.append(open(p, "rb"))
    response = client.images.edit(
        model="gpt-image-1",
        image=handles,
        prompt=keyframe_prompt,
        size="1024x1536",
        quality="medium",
        n=1,
    )
finally:
    for h in handles:
        h.close()

img_data = base64.b64decode(response.data[0].b64_json)
out_path.write_bytes(img_data)
sz_kb = len(img_data) // 1024
log(f"SAVED: {out_path}  ({sz_kb} KB)")
write_status(True, f"saved {sz_kb}KB", str(out_path))
log("=== DONE ===")
