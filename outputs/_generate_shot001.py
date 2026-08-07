"""
Standalone shot_001 keyframe generation script.
Run once; outputs result to outputs/runs/<run_id>/keyframes/shot_001_keyframe_look3_preserve_scene_test.png
and writes a status file to outputs/_gen_shot001_status.json when done.
"""
import json, os, sys, base64
from pathlib import Path

ROOT = Path(__file__).parent.parent

try:
    from dotenv import load_dotenv
    env_file = ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

STATUS_FILE = ROOT / "outputs" / "_gen_shot001_status.json"

def write_status(ok, msg, out_path=""):
    STATUS_FILE.write_text(json.dumps({"ok": ok, "msg": msg, "out_path": out_path}, indent=2))

api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    write_status(False, "OPENAI_API_KEY not set")
    sys.exit(1)

gen_data = json.loads((ROOT / "outputs" / "_gen_shot001_inputs.json").read_text())
keyframe_prompt = gen_data["keyframe_prompt"]
ref_paths       = gen_data["ref_paths"]
source_frame    = gen_data["source_frame"]
run_id          = gen_data["run_id"]

all_images = ref_paths + [source_frame]
for p in all_images:
    if not Path(p).exists():
        write_status(False, f"Image missing: {p}")
        sys.exit(1)

out_dir  = ROOT / "outputs" / "runs" / run_id / "keyframes"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "shot_001_keyframe_look3_preserve_scene_test.png"

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    file_handles = []
    try:
        for p in all_images:
            file_handles.append(open(p, "rb"))

        response = client.images.edit(
            model="gpt-image-1",
            image=file_handles[0] if len(file_handles) == 1 else file_handles,
            prompt=keyframe_prompt,
            size="1024x1536",
            quality="medium",
            n=1,
        )
    finally:
        for f in file_handles:
            f.close()

    img_data = base64.b64decode(response.data[0].b64_json)
    out_path.write_bytes(img_data)
    write_status(True, f"saved {len(img_data)//1024}KB", str(out_path))
    print(f"DONE: {out_path}")

except Exception as e:
    import traceback
    err = traceback.format_exc()
    write_status(False, str(e) + "\n" + err)
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
