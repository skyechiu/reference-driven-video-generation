"""
measure_phase0.py — score the ONE Phase 0 replacement segment on the 4 dimensions.
Deterministic where possible (cv2/numpy); identity is optional (insightface).
Writes phase0_out/phase0_metrics.json with per-metric {value, source, status}.
Statuses follow the project's evaluation vocabulary: pass|warning|fail|not_applicable|unavailable.
Run AFTER run_phase0.sh (CONFIRM_RUN=1).
"""
import glob, json, os
import numpy as np
try:
    import cv2
except Exception as e:
    raise SystemExit("cv2 required: " + str(e))

OUT   = os.environ.get("OUT", os.path.join(os.getcwd(), "phase0_out"))
IN    = os.environ.get("IN_DIR", os.path.join(os.getcwd(), "input"))
GEN   = os.path.join(OUT, "phase0_replacement.mp4")
DRIVE = os.path.join(IN, "driving_segment_phase0.mp4")
REF   = os.path.join(IN, "target_look_reference.png")
PROC  = os.path.join(OUT, "process_results")


def frames(path, max_n=64, h=256):
    cap = cv2.VideoCapture(path); out = []
    while len(out) < max_n:
        ok, f = cap.read()
        if not ok: break
        w = int(f.shape[1] * h / f.shape[0])
        out.append(cv2.resize(f, (w, h)))
    cap.release(); return out


def flow_energy(fr):
    if len(fr) < 2: return 0.0
    g = [cv2.cvtColor(x, cv2.COLOR_BGR2GRAY) for x in fr]
    v = [np.sqrt((lambda fl: (fl[..., 0]**2 + fl[..., 1]**2))(
        cv2.calcOpticalFlowFarneback(g[i-1], g[i], None, 0.5, 3, 15, 3, 5, 1.2, 0)).mean())
        for i in range(1, len(g))]
    return float(np.mean(v)) / fr[0].shape[0] * 100.0


def find_mask_video():
    for pat in ("*mask*.mp4", "*bg*mask*.mp4", "src_mask*.mp4", "*/mask*.mp4"):
        hit = glob.glob(os.path.join(PROC, pat)) + glob.glob(os.path.join(PROC, "**", pat), recursive=True)
        if hit: return hit[0]
    return None


metrics = {}

# --- 0. VRAM peak (from runtime.json) ---
rt = os.path.join(OUT, "runtime.json")
if os.path.exists(rt):
    d = json.load(open(rt)); peak = d.get("vram_peak_mib")
    metrics["vram_peak"] = {
        "value_mib": peak, "res_hxw": d.get("res_hxw"), "offload": d.get("offload"),
        "source": "deterministic (nvidia-smi sampler)",
        "status": "pass" if (peak and peak < 16000) else ("fail" if peak else "unavailable"),
    }
else:
    metrics["vram_peak"] = {"status": "unavailable", "source": "deterministic", "note": "run_phase0.sh not completed"}

if not os.path.exists(GEN):
    metrics["_note"] = "generated video missing — generation did not complete (likely OOM). Other metrics not_applicable."
    json.dump(metrics, open(os.path.join(OUT, "phase0_metrics.json"), "w"), indent=2)
    print(json.dumps(metrics, indent=2)); raise SystemExit(0)

gen = frames(GEN); drv = frames(DRIVE)

# --- 1. motion follows (proxy: optical-flow energy ratio) ---
ge, de = flow_energy(gen), flow_energy(drv)
ratio = (ge / de) if de > 1e-6 else 0.0
metrics["motion_follows"] = {
    "generated_energy_pct_h": round(ge, 3), "driving_energy_pct_h": round(de, 3),
    "recovered_ratio": round(ratio, 3),
    "source": "deterministic (optical-flow proxy; DWPose keypoint match is the stronger follow-up)",
    "status": "pass" if ratio >= 0.5 else ("warning" if ratio >= 0.25 else "fail"),
}

# --- 2. background preserved (diff OUTSIDE the foreground mask) ---
maskv = find_mask_video()
if maskv:
    mf = frames(maskv, max_n=len(gen), h=gen[0].shape[0])
    n = min(len(gen), len(drv), len(mf)); diffs = []
    for i in range(n):
        m = cv2.cvtColor(mf[i], cv2.COLOR_BGR2GRAY) if mf[i].ndim == 3 else mf[i]
        m = cv2.resize(m, (gen[i].shape[1], gen[i].shape[0]))
        bg = (m < 128)  # outside person
        if bg.sum() == 0: continue
        d = cv2.absdiff(gen[i], cv2.resize(drv[i], (gen[i].shape[1], gen[i].shape[0]))).mean(axis=2)
        diffs.append(float(d[bg].mean()))
    bgd = float(np.mean(diffs)) if diffs else None
    metrics["background_preserved"] = {
        "mean_bg_pixel_diff_0_255": round(bgd, 3) if bgd is not None else None,
        "source": "deterministic (masked pixel diff outside foreground)",
        "status": "pass" if (bgd is not None and bgd < 8) else ("warning" if (bgd is not None and bgd < 20) else "fail"),
    }
else:
    metrics["background_preserved"] = {
        "status": "unavailable", "source": "deterministic",
        "note": "foreground mask video not found in process_results — confirm its filename and set find_mask_video().",
    }

# --- 3. identity holds (optional: insightface face embedding) ---
try:
    from insightface.app import FaceAnalysis
    fa = FaceAnalysis(name="buffalo_l"); fa.prepare(ctx_id=0, det_size=(640, 640))
    def emb(img):
        fs = fa.get(img)
        return fs[0].normed_embedding if fs else None
    ref_img = cv2.imread(REF); re = emb(ref_img)
    sims = []
    for fr in gen[:: max(1, len(gen)//12)]:
        e = emb(fr)
        if e is not None and re is not None:
            sims.append(float(np.dot(e, re)))
    if sims:
        ms = float(np.mean(sims))
        metrics["identity_holds"] = {
            "mean_cosine_to_look_ref": round(ms, 3), "faces_scored": len(sims),
            "source": "model-assisted (insightface buffalo_l)",
            "status": "pass" if ms >= 0.35 else ("warning" if ms >= 0.2 else "fail"),
        }
    else:
        metrics["identity_holds"] = {"status": "not_applicable", "source": "model-assisted",
                                     "note": "no face detected in generated frames (may be small/occluded)"}
except Exception as e:
    metrics["identity_holds"] = {"status": "unavailable", "source": "model-assisted",
                                 "note": "insightface not installed: " + str(e)}

json.dump(metrics, open(os.path.join(OUT, "phase0_metrics.json"), "w"), indent=2)
print(json.dumps(metrics, indent=2))
print("\nwrote", os.path.join(OUT, "phase0_metrics.json"))
