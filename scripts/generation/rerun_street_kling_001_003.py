"""
rerun_street_kling_001_003.py
Shot-scoped Kling I2V rerun for the street run — shot_001 and shot_003 ONLY.

Purpose:
  Re-generate ONLY shot_001 and shot_003 with the revised motion prompts, WITHOUT
  touching the approved shot_002 / shot_004 clips, the keyframes, or the current
  final video. New clips are written as *_motion_v2.mp4 and a throwaway preview is
  assembled for review. Nothing original is overwritten.

Hard guarantees:
  - No OpenAI / image generation call of any kind.
  - No keyframe regeneration (existing approved keyframes are read as-is).
  - shot_002 and shot_004 clips are never read for regeneration and never overwritten.
  - Original clips + final_look3_street_demo.mp4 + clip_review_sheet.png are never overwritten.
  - CONFIRM_RUN = False  → prints the full plan (prompts + all paths) and exits. No Kling call.
    Set CONFIRM_RUN = True manually, then run again, to actually submit to Kling.

Run (from project root, in your normal environment with network access):
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 rerun_street_kling_001_003.py
"""

import ast, base64, io, json, os, sys, time
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIRM FLAG — the only switch that enables real Kling submission
# ─────────────────────────────────────────────────────────────────────────────
CONFIRM_RUN = True    # ENABLED by user — the NEXT run WILL submit Kling for shot_001 + shot_003.

# ─────────────────────────────────────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────────────────────────────────────
def _find_repo_root() -> Path:
    """Walk upward from this file until a repository-root marker is found.

    Looks for a .git directory, or the sibling pipeline/ + dissertation/
    directories that mark the top of this project. This makes the script
    location-independent -- it can live at repo root or several levels
    deep under scripts/ and still resolve the same ROOT.
    """
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        if (current / "pipeline").exists() and (current / "dissertation").exists():
            return current
        current = current.parent
    raise RuntimeError("Repository root not found (no .git or pipeline/+dissertation/ marker)")


ROOT      = _find_repo_root()
RUN_ID    = "live_test_04_street_look3"
RUN_DIR   = ROOT / "outputs" / "runs" / RUN_ID
KF_DIR    = RUN_DIR / "keyframes"
CLIP_DIR  = RUN_DIR / "clips"
FINAL_DIR = RUN_DIR / "final"
SRC_SCRIPT = ROOT / "scripts" / "generation" / "generate_street_run.py"   # source of the revised prompts

SHOTS_TO_RERUN = ["shot_001", "shot_003"]

# Keyframes (approved — read only, never regenerated)
KEYFRAMES = {
    "shot_001": KF_DIR / "shot_001_keyframe_look3_street.png",
    "shot_003": KF_DIR / "shot_003_keyframe_look3_street.png",
}
# New versioned clip outputs (do NOT overwrite originals)
NEW_CLIPS = {
    "shot_001": CLIP_DIR / "shot_001_look3_street_motion_v2.mp4",
    "shot_003": CLIP_DIR / "shot_003_look3_street_motion_v2.mp4",
}
# Existing originals reused unchanged in the preview
ORIG_CLIPS = {
    "shot_001": CLIP_DIR / "shot_001_look3_street.mp4",
    "shot_002": CLIP_DIR / "shot_002_look3_street.mp4",
    "shot_003": CLIP_DIR / "shot_003_look3_street.mp4",
    "shot_004": CLIP_DIR / "shot_004_look3_street.mp4",
}
PREVIEW_VIDEO = FINAL_DIR / "final_look3_street_demo_motion_v2_preview.mp4"
PREVIEW_SHEET = FINAL_DIR / "clip_review_sheet_motion_v2_preview.png"

# Files that must NEVER be overwritten by this script
PROTECTED = {
    FINAL_DIR / "final_look3_street_demo.mp4",
    FINAL_DIR / "clip_review_sheet.png",
    CLIP_DIR  / "shot_002_look3_street.mp4",
    CLIP_DIR  / "shot_004_look3_street.mp4",
    CLIP_DIR  / "shot_001_look3_street.mp4",
    CLIP_DIR  / "shot_003_look3_street.mp4",
    KEYFRAMES["shot_001"], KEYFRAMES["shot_003"],
}

# Preview timeline (beat order). v2 for the reran shots, original for the rest.
PREVIEW_TIMELINE = [
    ("shot_001", NEW_CLIPS["shot_001"], "NEW v2"),
    ("shot_002", ORIG_CLIPS["shot_002"], "original"),
    ("shot_003", NEW_CLIPS["shot_003"], "NEW v2"),
    ("shot_004", ORIG_CLIPS["shot_004"], "original"),
]

# ─────────────────────────────────────────────────────────────────────────────
#  Kling settings (identical to generate_street_run.py / run_kling_i2v.py)
# ─────────────────────────────────────────────────────────────────────────────
KLING = dict(model_name="kling-v1-6", mode="std", duration=5, aspect_ratio="9:16", cfg_scale=0.5)

# ─────────────────────────────────────────────────────────────────────────────
#  Safety guard: never target a protected path
# ─────────────────────────────────────────────────────────────────────────────
for _p in list(NEW_CLIPS.values()) + [PREVIEW_VIDEO, PREVIEW_SHEET]:
    if _p.resolve() in {p.resolve() for p in PROTECTED}:
        print(f"FATAL: output path collides with a PROTECTED file: {_p}")
        sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
#  Read the revised prompts straight out of generate_street_run.py (no execution)
# ─────────────────────────────────────────────────────────────────────────────
def load_prompts_from_source(py_path: Path, shot_ids):
    """Parse generate_street_run.py with ast (does NOT run it) and pull
    video_prompt + NEGATIVE_PROMPT for the requested shots."""
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    shots_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "SHOTS" and isinstance(node.value, ast.List):
                    shots_node = node.value
    if shots_node is None:
        raise RuntimeError("Could not find SHOTS list in generate_street_run.py")
    out = {}
    for elt in shots_node.elts:
        if not isinstance(elt, ast.Dict):
            continue
        kv = {}
        for k, v in zip(elt.keys, elt.values):
            if isinstance(k, ast.Constant):
                kv[k.value] = v
        sid_node = kv.get("shot_id")
        if sid_node is None:
            continue
        sid = ast.literal_eval(sid_node)
        if sid in shot_ids:
            out[sid] = {
                "video_prompt":    ast.literal_eval(kv["video_prompt"]),
                "negative_prompt": ast.literal_eval(kv["NEGATIVE_PROMPT"]),
            }
    missing = [s for s in shot_ids if s not in out]
    if missing:
        raise RuntimeError(f"Prompts not found for: {missing}")
    return out

PROMPTS = load_prompts_from_source(SRC_SCRIPT, SHOTS_TO_RERUN)

# ─────────────────────────────────────────────────────────────────────────────
#  Pre-flight checks
# ─────────────────────────────────────────────────────────────────────────────
def preflight():
    problems = []
    for sid in SHOTS_TO_RERUN:
        if not KEYFRAMES[sid].exists():
            problems.append(f"missing keyframe: {KEYFRAMES[sid]}")
    for sid in ("shot_002", "shot_004"):
        if not ORIG_CLIPS[sid].exists():
            problems.append(f"missing original clip needed for preview: {ORIG_CLIPS[sid]}")
    return problems

# ─────────────────────────────────────────────────────────────────────────────
#  Plan print (always)
# ─────────────────────────────────────────────────────────────────────────────
def print_plan():
    print("=" * 74)
    print("SHOT-SCOPED KLING RERUN PLAN  —  shot_001 + shot_003 only")
    print("=" * 74)
    print(f"  CONFIRM_RUN     : {CONFIRM_RUN}")
    print(f"  Kling settings  : {KLING}")
    print(f"  prompt source   : {SRC_SCRIPT.name} (read via AST, not executed)")
    print()
    for sid in SHOTS_TO_RERUN:
        print(f"  ── {sid}")
        print(f"     keyframe (read-only) : {KEYFRAMES[sid]}")
        print(f"     new clip out         : {NEW_CLIPS[sid]}")
        print(f"     video_prompt         :\n       {PROMPTS[sid]['video_prompt']}")
        print(f"     negative_prompt      :\n       {PROMPTS[sid]['negative_prompt'][:160]}...")
        print()
    print("  PREVIEW (throwaway, does NOT replace the real final):")
    print(f"     timeline : " + "  →  ".join(f"{s}[{tag}]" for s, _, tag in PREVIEW_TIMELINE))
    print(f"     video    : {PREVIEW_VIDEO}")
    print(f"     sheet    : {PREVIEW_SHEET}")
    print()
    print("  PROTECTED — never overwritten by this script:")
    for p in sorted({str(p) for p in PROTECTED}):
        print(f"     · {p}")
    print("=" * 74)

# ─────────────────────────────────────────────────────────────────────────────
#  Kling helpers (mirrors run_kling_i2v.py — proven working)
# ─────────────────────────────────────────────────────────────────────────────
def encode_jpeg(path: Path) -> str:
    from PIL import Image as PILImage
    img = PILImage.open(path).convert("RGB")
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=95)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")

def kling_headers(key): return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def submit_and_download(sid, key):
    import requests, httpx
    payload = {
        **KLING,
        "image":           encode_jpeg(KEYFRAMES[sid]),
        "prompt":          PROMPTS[sid]["video_prompt"],
        "negative_prompt": PROMPTS[sid]["negative_prompt"],
    }
    task_id = None
    for attempt in range(4):
        r = requests.post("https://api.klingai.com/v1/videos/image2video",
                          headers=kling_headers(key), json=payload, timeout=30)
        if r.status_code == 429:
            wait = 15 * (2 ** attempt); print(f"  [{sid}] rate limited, waiting {wait}s"); time.sleep(wait); continue
        if not r.ok:
            print(f"  [{sid}] submit error {r.status_code}: {r.text[:200]}"); r.raise_for_status()
        task_id = r.json()["data"]["task_id"]; print(f"  [{sid}] submitted task_id={task_id}"); break
    if not task_id:
        print(f"  [{sid}] FAILED to submit"); return False
    for poll in range(60):
        time.sleep(10)
        d = requests.get(f"https://api.klingai.com/v1/videos/image2video/{task_id}",
                         headers=kling_headers(key), timeout=15).json()["data"]
        st = d["task_status"]; print(f"  [{sid}] status={st} (poll {poll+1})")
        if st == "succeed":
            url = d["task_result"]["videos"][0]["url"]
            with httpx.Client() as hc:
                NEW_CLIPS[sid].write_bytes(hc.get(url, timeout=60).content)
            print(f"  [{sid}] SAVED {NEW_CLIPS[sid].name} ({NEW_CLIPS[sid].stat().st_size//1024} KB)")
            return True
        if st == "failed":
            print(f"  [{sid}] KLING FAILED: {d}"); return False
    print(f"  [{sid}] timed out"); return False

# ─────────────────────────────────────────────────────────────────────────────
#  Preview assembly + review sheet
# ─────────────────────────────────────────────────────────────────────────────
def assemble_preview():
    import subprocess
    concat_txt = FINAL_DIR / "_concat_motion_v2_preview.txt"
    concat_txt.write_text("\n".join(f"file '{clip.resolve()}'" for _, clip, _ in PREVIEW_TIMELINE))
    # try stream copy first, fall back to re-encode for safety
    cmd_copy = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                "-c", "copy", str(PREVIEW_VIDEO)]
    if subprocess.run(cmd_copy, capture_output=True, text=True).returncode != 0 or not PREVIEW_VIDEO.exists():
        cmd_enc = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                   "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(PREVIEW_VIDEO)]
        subprocess.run(cmd_enc, capture_output=True, text=True)
    print(f"  preview video: {PREVIEW_VIDEO} ({'ok' if PREVIEW_VIDEO.exists() else 'FAILED'})")

def build_review_sheet():
    import cv2, numpy as np
    NCOL=10; CW=300; CH=int(CW*1152/768); PAD=6; Hn=288
    def _flow(mp4):
        cap=cv2.VideoCapture(str(mp4)); fr=[]
        while True:
            ok,f=cap.read()
            if not ok: break
            w=int(f.shape[1]*Hn/f.shape[0]); fr.append(cv2.cvtColor(cv2.resize(f,(w,Hn)),cv2.COLOR_BGR2GRAY))
        cap.release()
        if len(fr)<2: return 0.0
        vals=[]
        for k in range(1,len(fr)):
            fl=cv2.calcOpticalFlowFarneback(fr[k-1],fr[k],None,0.5,3,15,3,5,1.2,0)
            vals.append(np.sqrt(fl[...,0]**2+fl[...,1]**2).mean())
        return round(float(np.mean(vals))/Hn*100,3)
    def _strip(mp4):
        cap=cv2.VideoCapture(str(mp4)); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        idx=np.linspace(0,max(n-1,0),NCOL).astype(int); cells=[]
        for j in idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES,int(j)); ok,fr=cap.read()
            cells.append(cv2.resize(fr,(CW,CH)) if ok else np.zeros((CH,CW,3),np.uint8))
        cap.release()
        W=NCOL*CW+(NCOL-1)*PAD; row=np.full((CH,W,3),18,np.uint8); x=0
        for c in cells: row[:,x:x+CW]=c; x+=CW+PAD
        return row
    Wt=NCOL*CW+(NCOL-1)*PAD; blocks=[]
    title=np.full((40,Wt,3),12,np.uint8)
    cv2.putText(title,"MOTION v2 PREVIEW - dense clip review (10 frames/shot)",(8,18),cv2.FONT_HERSHEY_SIMPLEX,0.5,(150,210,255),1,cv2.LINE_AA)
    cv2.putText(title,"flow = optical flow, % of frame height per frame (higher = more motion)",(8,33),cv2.FONT_HERSHEY_SIMPLEX,0.4,(160,160,160),1,cv2.LINE_AA)
    blocks.append(title)
    for sid, clip, tag in PREVIEW_TIMELINE:
        fl=_flow(clip)
        c=(120,255,180) if tag!="original" else (170,170,180)
        lab=np.full((26,Wt,3),30 if tag!="original" else 22,np.uint8)
        cv2.putText(lab,f"{sid}  [{tag}]   flow={fl}%",(8,18),cv2.FONT_HERSHEY_SIMPLEX,0.5,c,1,cv2.LINE_AA)
        blocks.append(lab); blocks.append(_strip(clip)); blocks.append(np.full((8,Wt,3),40,np.uint8))
    cv2.imwrite(str(PREVIEW_SHEET), np.vstack(blocks)); print(f"  preview sheet (dense): {PREVIEW_SHEET}")


def main():
    probs = preflight()
    print_plan()
    if probs:
        print("\nPRE-FLIGHT PROBLEMS (fix before running):")
        for p in probs: print(f"   ! {p}")
        sys.exit(1)

    if not CONFIRM_RUN:
        print("\nDRY RUN — CONFIRM_RUN is False. No Kling call made, nothing written.")
        print("Review the plan above. To actually rerun shot_001 + shot_003:")
        print("  1) open this file, set  CONFIRM_RUN = True")
        print("  2) run again:  python3 rerun_street_kling_001_003.py")
        sys.exit(0)

    # ── real submission ──
    try:
        from dotenv import load_dotenv; load_dotenv(ROOT / ".env")
    except ImportError:
        pass
    key = os.getenv("KLING_API_KEY", "")
    if not key:
        print("ERROR: KLING_API_KEY not set in .env"); sys.exit(1)

    print("\n[kling] submitting shot_001 + shot_003 only ...")
    ok = {}
    for sid in SHOTS_TO_RERUN:
        ok[sid] = submit_and_download(sid, key)
        time.sleep(2)
    if not all(ok.values()):
        print(f"\nNot all shots succeeded: {ok}. Preview NOT assembled. Originals untouched.")
        sys.exit(1)

    print("\n[assembly] building throwaway motion-v2 preview ...")
    assemble_preview()
    build_review_sheet()
    print("\nDONE. New clips saved as *_motion_v2.mp4. Originals, final video, and 002/004 untouched.")
    print("Review the preview, then decide whether to promote v2 → the real clips + final.")

if __name__ == "__main__":
    main()
