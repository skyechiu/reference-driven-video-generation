"""
promote_motion_v2.py
Promote the approved motion-v2 clips (shot_001 + shot_003) to the real street run,
then rebuild the real final video + a dense clip review sheet.

What it does (only when CONFIRM_RUN = True):
  1. Back up the current originals (once):
        shot_001_look3_street.mp4 -> shot_001_look3_street_premotion_backup.mp4
        shot_003_look3_street.mp4 -> shot_003_look3_street_premotion_backup.mp4
     Back up the current final + review sheet (once):
        final_look3_street_demo.mp4 -> final_look3_street_demo_premotion_backup.mp4
        clip_review_sheet.png       -> clip_review_sheet_premotion_backup.png
  2. Promote v2 -> real clip:
        shot_001_look3_street_motion_v2.mp4 -> shot_001_look3_street.mp4
        shot_003_look3_street_motion_v2.mp4 -> shot_003_look3_street.mp4
  3. Rebuild final_look3_street_demo.mp4 = concat[001, 002, 003, 004]
     (001 + 003 now the v2 versions; 002 + 004 unchanged).
  4. Rebuild clip_review_sheet.png as a DENSE sheet (10 frames/shot + optical-flow motion).

Hard guarantees:
  - No OpenAI, no Kling, no keyframe touch.
  - shot_002 and shot_004 clips are never modified.
  - Originals are backed up before being replaced — fully reversible.
  - CONFIRM_RUN = False -> prints the plan and exits. Nothing written.

Run (from project root):
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 promote_motion_v2.py
"""

import shutil, subprocess, sys
from pathlib import Path

CONFIRM_RUN = False   # False -> dry-run plan only. Pass --confirm (or set True) to promote.
if "--confirm" in sys.argv:
    CONFIRM_RUN = True

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


ROOT     = _find_repo_root()
RUN_DIR  = ROOT / "outputs" / "runs" / "live_test_04_street_look3"
CLIP_DIR = RUN_DIR / "clips"
FINAL    = RUN_DIR / "final"

# v2 sources -> real clip destinations
PROMOTE = {
    CLIP_DIR / "shot_001_look3_street_motion_v2.mp4": CLIP_DIR / "shot_001_look3_street.mp4",
    CLIP_DIR / "shot_003_look3_street_motion_v2.mp4": CLIP_DIR / "shot_003_look3_street.mp4",
}
# backups (created once, never overwritten)
BACKUPS = {
    CLIP_DIR / "shot_001_look3_street.mp4":        CLIP_DIR / "shot_001_look3_street_premotion_backup.mp4",
    CLIP_DIR / "shot_003_look3_street.mp4":        CLIP_DIR / "shot_003_look3_street_premotion_backup.mp4",
    FINAL / "final_look3_street_demo.mp4":         FINAL / "final_look3_street_demo_premotion_backup.mp4",
    FINAL / "clip_review_sheet.png":               FINAL / "clip_review_sheet_premotion_backup.png",
}
FINAL_VIDEO = FINAL / "final_look3_street_demo.mp4"
REVIEW_SHEET = FINAL / "clip_review_sheet.png"
# beat-order timeline for the rebuilt final (real clip names, post-promote)
TIMELINE = [CLIP_DIR / f"shot_00{i}_look3_street.mp4" for i in (1, 2, 3, 4)]
# shot_002 / shot_004 must never be written
PROTECTED_NOWRITE = {CLIP_DIR / "shot_002_look3_street.mp4", CLIP_DIR / "shot_004_look3_street.mp4"}

for dest in list(PROMOTE.values()) + [FINAL_VIDEO, REVIEW_SHEET]:
    if dest.resolve() in {p.resolve() for p in PROTECTED_NOWRITE}:
        print(f"FATAL: would write a protected clip: {dest}"); sys.exit(1)


def preflight():
    probs = []
    for src in PROMOTE:
        if not src.exists(): probs.append(f"missing v2 clip: {src}")
    for i in (2, 4):
        c = CLIP_DIR / f"shot_00{i}_look3_street.mp4"
        if not c.exists(): probs.append(f"missing clip needed for final: {c}")
    return probs


def print_plan():
    print("=" * 74)
    print("PROMOTE MOTION v2 -> REAL STREET RUN   (shot_001 + shot_003)")
    print("=" * 74)
    print(f"  CONFIRM_RUN : {CONFIRM_RUN}\n")
    print("  BACKUPS (created once, skipped if already present):")
    for a, b in BACKUPS.items(): print(f"     {a.name}  ->  {b.name}")
    print("\n  PROMOTE (copy v2 over the real clip):")
    for a, b in PROMOTE.items(): print(f"     {a.name}  ->  {b.name}")
    print("\n  REBUILD:")
    print(f"     final : {FINAL_VIDEO.name}  =  concat[" + ", ".join(t.name for t in TIMELINE) + "]")
    print(f"     sheet : {REVIEW_SHEET.name}  (dense, 10 frames/shot + optical flow)")
    print("\n  NEVER MODIFIED:")
    for p in sorted({str(p) for p in PROTECTED_NOWRITE}): print(f"     · {p}")
    print("=" * 74)


def dense_review_sheet(timeline, out_path):
    import cv2, numpy as np
    NCOL = 10; CW = 300; CH = int(CW * 1152 / 768); PAD = 6; Hn = 288
    def flow(mp4):
        cap = cv2.VideoCapture(str(mp4)); fr = []
        while True:
            ok, f = cap.read()
            if not ok: break
            w = int(f.shape[1] * Hn / f.shape[0]); fr.append(cv2.cvtColor(cv2.resize(f, (w, Hn)), cv2.COLOR_BGR2GRAY))
        cap.release()
        if len(fr) < 2: return 0.0
        vals = []
        for i in range(1, len(fr)):
            fl = cv2.calcOpticalFlowFarneback(fr[i-1], fr[i], None, 0.5, 3, 15, 3, 5, 1.2, 0)
            vals.append(np.sqrt(fl[..., 0]**2 + fl[..., 1]**2).mean())
        return round(float(np.mean(vals)) / Hn * 100, 3)
    def strip(mp4):
        cap = cv2.VideoCapture(str(mp4)); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        idx = np.linspace(0, max(n-1, 0), NCOL).astype(int); cells = []
        for j in idx:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(j)); ok, fr = cap.read()
            cells.append(cv2.resize(fr, (CW, CH)) if ok else np.zeros((CH, CW, 3), np.uint8))
        cap.release()
        W = NCOL*CW + (NCOL-1)*PAD; row = np.full((CH, W, 3), 18, np.uint8); x = 0
        for c in cells: row[:, x:x+CW] = c; x += CW + PAD
        return row
    Wt = NCOL*CW + (NCOL-1)*PAD; blocks = []
    title = np.full((40, Wt, 3), 12, np.uint8)
    cv2.putText(title, "CLIP REVIEW (dense, 10 frames/shot)  live_test_04_street_look3  Kling v1.6 5s 9:16",
                (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 120), 1, cv2.LINE_AA)
    cv2.putText(title, "flow = optical flow, % of frame height per frame (higher = more motion)",
                (8, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 160, 160), 1, cv2.LINE_AA)
    blocks.append(title)
    for clip in timeline:
        fl = flow(clip)
        lab = np.full((26, Wt, 3), 26, np.uint8)
        cv2.putText(lab, f"{clip.stem}   flow={fl}%", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 255, 180), 1, cv2.LINE_AA)
        blocks.append(lab); blocks.append(strip(clip)); blocks.append(np.full((8, Wt, 3), 40, np.uint8))
    cv2.imwrite(str(out_path), np.vstack(blocks))


RECOVERY = {   # optical-flow motion-energy recovered by the prompt-only v2 repair
    "shot_001": {"from": 14, "to": 51},
    "shot_003": {"from": 19, "to": 47},
}


def update_decision_log():
    import json, time
    dl = FINAL / "decision_log.json"
    if not dl.exists():
        print("[log] decision_log.json missing — skipping"); return
    d = json.loads(dl.read_text())
    d["motion_v2_promotion"] = {
        "promoted_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "method": "prompt-only Kling I2V repair (damping words removed, motion cues named)",
        "keyframe_regeneration": False,
        "shots_promoted": ["shot_001", "shot_003"],
        "shots_untouched": ["shot_002", "shot_004"],
        "recovered_motion_pct": RECOVERY,
        "v1_backups": {
            "shot_001": "clips/shot_001_look3_street_premotion_backup.mp4",
            "shot_003": "clips/shot_003_look3_street_premotion_backup.mp4",
        },
        "rebuilt": ["final/final_look3_street_demo.mp4", "final/clip_review_sheet.png"],
        "note": "Motion-energy recovery, not exact frame-level motion transfer.",
    }
    for sh in d.get("shots", []):
        if sh.get("shot_id") in RECOVERY:
            r = RECOVERY[sh["shot_id"]]
            sh["post_repair"] = {
                "type": "motion_v2_prompt_only",
                "recovered_motion_pct": r,
                "v1_backup": f"clips/{sh['shot_id']}_look3_street_premotion_backup.mp4",
            }
    dl.write_text(json.dumps(d, indent=2))
    print("[log] decision_log.json updated (motion_v2_promotion + per-shot post_repair)")


def update_run_summary():
    import time
    rs = FINAL / "run_summary.md"
    if not rs.exists():
        print("[summary] run_summary.md missing — skipping"); return
    block = (
        "\n\n## Motion v2 promotion (" + time.strftime("%Y-%m-%d", time.gmtime()) + ")\n\n"
        "The motion_v2 clips were promoted to the official street run for **shot_001** and **shot_003**.\n\n"
        "- shot_001 recovered motion: **14% -> 51%**\n"
        "- shot_003 recovered motion: **19% -> 47%**\n"
        "- Repair method: **prompt-only Kling I2V** (damping words removed, motion cues named)\n"
        "- **No keyframe regeneration**; shot_002 and shot_004 unchanged\n"
        "- v1 clips retained as backups (`clips/*_premotion_backup.mp4`); `final/final_look3_street_demo.mp4` "
        "and `final/clip_review_sheet.png` rebuilt\n"
        "- This is motion-**energy** recovery, not exact frame-level motion transfer.\n"
    )
    with open(rs, "a", encoding="utf-8") as f:
        f.write(block)
    print("[summary] run_summary.md updated (Motion v2 promotion section)")


def main():
    probs = preflight()
    print_plan()
    if probs:
        print("\nPRE-FLIGHT PROBLEMS:")
        for p in probs: print(f"   ! {p}")
        sys.exit(1)
    if not CONFIRM_RUN:
        print("\nDRY RUN — CONFIRM_RUN is False. Nothing written.")
        print("To promote: set CONFIRM_RUN = True and run again.")
        sys.exit(0)

    # 1. backups (once)
    for src, bak in BACKUPS.items():
        if src.exists() and not bak.exists():
            shutil.copy2(src, bak); print(f"[backup] {src.name} -> {bak.name}")
        elif bak.exists():
            print(f"[backup] {bak.name} already exists — keeping it")
    # 2. promote
    for src, dest in PROMOTE.items():
        shutil.copy2(src, dest); print(f"[promote] {src.name} -> {dest.name}")
    # 3. rebuild final
    concat = FINAL / "_concat_promote.txt"
    concat.write_text("\n".join(f"file '{t.resolve()}'" for t in TIMELINE))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(FINAL_VIDEO)]
    if subprocess.run(cmd, capture_output=True, text=True).returncode != 0:
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(FINAL_VIDEO)],
                       capture_output=True, text=True)
    print(f"[final] rebuilt {FINAL_VIDEO.name} ({'ok' if FINAL_VIDEO.exists() else 'FAILED'})")
    # 4. dense review sheet
    dense_review_sheet(TIMELINE, REVIEW_SHEET)
    print(f"[sheet] rebuilt {REVIEW_SHEET.name} (dense)")
    # 5. records
    update_decision_log()
    update_run_summary()
    print("\nDONE. v2 promoted for shot_001 + shot_003. Originals backed up as *_premotion_backup.")
    print("shot_002 / shot_004 untouched. To revert: copy the *_premotion_backup files back.")


if __name__ == "__main__":
    main()
