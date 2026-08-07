"""
shot_001 keyframe generation — approved 2026-07-17.
Writes all status/logs to /tmp to avoid mounted-filesystem write issues.
Copies final image to mounted output path on success.
"""
import sys, os, json, base64, shutil
from pathlib import Path

# All temp output to /tmp — avoids any mounted-path write restriction in nohup
LOG_F  = open("/tmp/gen001_v2.log", "w", buffering=1)  # line-buffered

def log(msg):
    print(msg, flush=True)
    LOG_F.write(msg + "\n"); LOG_F.flush()

def done(ok, msg, out=""):
    payload = json.dumps({"ok": ok, "msg": msg, "out_path": out})
    Path("/tmp/gen001_status.json").write_text(payload)
    log(f"STATUS: ok={ok}  msg={msg[:120]}")

log("== _gen001_v2 starting ==")

try:
    from dotenv import load_dotenv
    env = Path("/sessions/stoic-busy-pascal/mnt/Desktop/Reference-Driven Agentic Short-Form Video Generation System/.env")
    if env.exists():
        load_dotenv(env); log(f"loaded .env")
    else:
        log("no .env — using system env")
except Exception as e:
    log(f"dotenv error: {e}")

api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key:
    done(False, "OPENAI_API_KEY not set"); sys.exit(1)
log(f"API key: ...{api_key[-6:]}")

BASE = Path("/sessions/stoic-busy-pascal/mnt/Desktop/Reference-Driven Agentic Short-Form Video Generation System")
LOOK = BASE / "assets/looks/look_3_tailored_self"

image_paths = [
    str(LOOK / "look3_closeup.png"),
    str(LOOK / "look3_front.png"),
    str(LOOK / "look3_sheet.png"),
    str(BASE / "outputs/ref_panels/shot_001_best.png"),
]
for p in image_paths:
    if not Path(p).exists():
        done(False, f"image missing: {p}"); sys.exit(1)
    log(f"  image ok: {Path(p).name}")

gen_data    = json.loads((BASE / "outputs/_gen_shot001_inputs.json").read_text())
kp          = gen_data["keyframe_prompt"]
run_id      = gen_data["run_id"]
final_dir   = BASE / "outputs/runs" / run_id / "keyframes"
final_dir.mkdir(parents=True, exist_ok=True)
final_path  = final_dir / "shot_001_keyframe_look3_preserve_scene_test.png"
tmp_path    = Path("/tmp/shot_001_keyframe.png")

log(f"final output: {final_path}")
log(f"prompt length: {len(kp)} chars")
log("calling openai images.edit ...")

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    handles = [open(p, "rb") for p in image_paths]
    try:
        log("  request sent — waiting for response ...")
        response = client.images.edit(
            model="gpt-image-1",
            image=handles,
            prompt=kp,
            size="1024x1536",
            quality="medium",
            n=1,
        )
        log("  response received")
    finally:
        for h in handles: h.close()

    img_data = base64.b64decode(response.data[0].b64_json)
    tmp_path.write_bytes(img_data)
    log(f"  saved to /tmp: {len(img_data)//1024}KB")

    shutil.copy2(str(tmp_path), str(final_path))
    log(f"  copied to final path")

    done(True, f"saved {len(img_data)//1024}KB", str(final_path))

except Exception as e:
    import traceback
    tb = traceback.format_exc()
    log(f"ERROR: {e}")
    log(tb)
    done(False, str(e))
    sys.exit(1)
finally:
    LOG_F.close()
