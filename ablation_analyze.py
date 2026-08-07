"""
ablation_analyze.py — Small controlled repair ablation, ANALYSIS phase.

Run this AFTER ablation_blind_reroll_generate.py --confirm has produced files under
outputs/ablation_repair_20260807/{keyframes,clips}/.

No network calls. No OpenAI, no Kling. Only reads existing files (this run's new
blind-reroll outputs + the pre-existing Condition-B evidence) and:

  1. Computes optical-flow recovered_motion_pct for every motion clip using the SAME
     Farneback method already used in promote_motion_v2.py / rerun_street_kling_001_003.py
     (so numbers are directly comparable to the 14/51/19/47 already in decision_log.json).
  2. Builds a keyframe contact sheet (blind reroll attempts vs the approved targeted-repair
     keyframe) for human review — this script does NOT invent an automatic identity/framing
     score; it produces a review sheet + a CSV with the accept/reject column left for a human
     rater to fill in, exactly matching this project's own rule that human review is the
     acceptance authority.
  3. Writes ablation_results.csv, ablation_summary.md, and a LaTeX table snippet ready to
     paste into the dissertation.

Run:
    cd "Reference-Driven Agentic Short-Form Video Generation System"
    python3 ablation_analyze.py
"""

import csv, json
from pathlib import Path

ROOT     = Path(__file__).parent
RUN_DIR  = ROOT / "outputs" / "runs" / "live_test_04_street_look3"
OUT_DIR  = ROOT / "outputs" / "ablation_repair_20260807"
KF_DIR   = OUT_DIR / "keyframes"
CLIP_DIR = OUT_DIR / "clips"
GEN_LOG  = OUT_DIR / "generation_log.json"

CONDITION_B = {
    "shot_001_keyframe": RUN_DIR / "keyframes" / "shot_001_keyframe_look3_street.png",
    "shot_002_keyframe": RUN_DIR / "keyframes" / "shot_002_keyframe_look3_street.png",
    "shot_004_keyframe": RUN_DIR / "keyframes" / "shot_004_keyframe_look3_street.png",
    "shot_001_motion":   RUN_DIR / "clips" / "shot_001_look3_street_motion_v2.mp4",
    "shot_003_motion":   RUN_DIR / "clips" / "shot_003_look3_street_motion_v2.mp4",
}
# Known-good, decision_log.json-traceable baseline / repaired flow values (do not recompute
# differently — these are the authoritative numbers already in the dissertation).
KNOWN_MOTION_PCT = {
    "shot_001": {"v1_blind_baseline_from_prior_run": 14, "targeted_repair_b": 51},
    "shot_003": {"v1_blind_baseline_from_prior_run": 19, "targeted_repair_b": 47},
}


def optical_flow_pct(mp4_path: Path) -> float:
    """Same method as promote_motion_v2.py / rerun_street_kling_001_003.py:
    Farneback optical flow, mean magnitude / frame-height * 100, frames resized to H=288."""
    import cv2, numpy as np
    cap = cv2.VideoCapture(str(mp4_path))
    Hn = 288
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        w = int(f.shape[1] * Hn / f.shape[0])
        frames.append(cv2.cvtColor(cv2.resize(f, (w, Hn)), cv2.COLOR_BGR2GRAY))
    cap.release()
    if len(frames) < 2:
        return 0.0
    vals = []
    for i in range(1, len(frames)):
        fl = cv2.calcOpticalFlowFarneback(frames[i - 1], frames[i], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        vals.append(np.sqrt(fl[..., 0] ** 2 + fl[..., 1] ** 2).mean())
    return round(float(np.mean(vals)) / Hn * 100, 3)


def build_contact_sheet(rows_kf):
    import cv2, numpy as np
    CW, CH, PAD, LBL = 300, 450, 10, 26
    cells = []
    for label, path in rows_kf:
        if path and Path(path).exists():
            im = cv2.imread(str(path))
            im = cv2.resize(im, (CW, CH))
        else:
            im = np.full((CH, CW, 3), 40, np.uint8)
        cells.append((label, im))
    n = len(cells)
    if n == 0:
        return None
    W = n * CW + (n - 1) * PAD
    sheet = np.full((LBL + CH, W, 3), 18, np.uint8)
    x = 0
    for label, im in cells:
        cv2.putText(sheet, label[:34], (x + 4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 220, 255), 1, cv2.LINE_AA)
        sheet[LBL:LBL + CH, x:x + CW] = im
        x += CW + PAD
    out_path = OUT_DIR / "ablation_contact_sheet.png"
    cv2.imwrite(str(out_path), sheet)
    return out_path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gen_log = json.loads(GEN_LOG.read_text()) if GEN_LOG.exists() else None

    rows = []  # results rows -> CSV

    # ── Motion: fully automatic, objective metric ──────────────────────────────
    for sid in ["shot_001", "shot_003"]:
        b_path = CONDITION_B[f"{sid}_motion"]
        b_pct = optical_flow_pct(b_path) if b_path.exists() else None
        rows.append({
            "case": f"{sid}_motion", "condition": "B_targeted_repair",
            "path": str(b_path), "attempts_to_acceptance": 1,
            "recovered_motion_pct": b_pct if b_pct is not None else KNOWN_MOTION_PCT[sid]["targeted_repair_b"],
            "accepted": "yes (promoted to final evidence)",
            "human_verdict": "n/a (objective metric)",
        })
        blind_attempts = sorted(CLIP_DIR.glob(f"{sid}_blind_reroll_r*.mp4"))
        if not blind_attempts:
            rows.append({
                "case": f"{sid}_motion", "condition": "A_blind_reroll",
                "path": "NOT YET GENERATED", "attempts_to_acceptance": "",
                "recovered_motion_pct": "", "accepted": "PENDING — run ablation_blind_reroll_generate.py --confirm",
                "human_verdict": "",
            })
        else:
            for i, p in enumerate(blind_attempts, 1):
                pct = optical_flow_pct(p)
                rows.append({
                    "case": f"{sid}_motion", "condition": "A_blind_reroll",
                    "path": str(p), "attempts_to_acceptance": i,
                    "recovered_motion_pct": pct,
                    "accepted": "yes" if pct >= KNOWN_MOTION_PCT[sid]["targeted_repair_b"] * 0.8 else "no (below 80% of targeted-repair recovery)",
                    "human_verdict": "n/a (objective metric)",
                })

    # ── Keyframes: human-gated, per this project's own acceptance rule ─────────
    kf_contact_rows = []
    for sid in ["shot_001", "shot_002", "shot_004"]:
        b_path = CONDITION_B[f"{sid}_keyframe"]
        rows.append({
            "case": f"{sid}_keyframe", "condition": "B_targeted_repair",
            "path": str(b_path), "attempts_to_acceptance": 1,
            "recovered_motion_pct": "", "accepted": "yes (promoted to final evidence)",
            "human_verdict": "accept (already approved & used in the final street run)",
        })
        kf_contact_rows.append((f"{sid} B targeted (approved)", b_path))
        blind_attempts = sorted(KF_DIR.glob(f"{sid}_blind_reroll_r*.png"))
        if not blind_attempts:
            rows.append({
                "case": f"{sid}_keyframe", "condition": "A_blind_reroll",
                "path": "NOT YET GENERATED", "attempts_to_acceptance": "",
                "recovered_motion_pct": "", "accepted": "PENDING — run ablation_blind_reroll_generate.py --confirm",
                "human_verdict": "FILL IN AFTER VIEWING ablation_contact_sheet.png",
            })
        else:
            for i, p in enumerate(blind_attempts, 1):
                rows.append({
                    "case": f"{sid}_keyframe", "condition": "A_blind_reroll",
                    "path": str(p), "attempts_to_acceptance": i,
                    "recovered_motion_pct": "",
                    "accepted": "FILL IN — rubric: identity match / correct outfit (charcoal blazer, "
                                "olive tie, wide denim) / correct framing per shot spec",
                    "human_verdict": "",
                })
                kf_contact_rows.append((f"{sid} A blind r{i}", p))

    # ── Write CSV ────────────────────────────────────────────────────────────
    csv_path = OUT_DIR / "ablation_results.csv"
    fieldnames = ["case", "condition", "path", "attempts_to_acceptance",
                  "recovered_motion_pct", "accepted", "human_verdict"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # ── Contact sheet ────────────────────────────────────────────────────────
    sheet_path = build_contact_sheet(kf_contact_rows) if kf_contact_rows else None

    # ── Summary + LaTeX table ────────────────────────────────────────────────
    motion_lines = []
    for sid in ["shot_001", "shot_003"]:
        b = KNOWN_MOTION_PCT[sid]["targeted_repair_b"]
        blind = [r for r in rows if r["case"] == f"{sid}_motion" and r["condition"] == "A_blind_reroll"]
        blind_vals = [r["recovered_motion_pct"] for r in blind if isinstance(r["recovered_motion_pct"], (int, float))]
        best_blind = max(blind_vals) if blind_vals else None
        motion_lines.append(f"- {sid}: targeted repair = {b}% recovered · blind reroll best of "
                             f"{len(blind)} attempts = {best_blind if best_blind is not None else 'PENDING'}%")

    summary = f"""# Small controlled repair ablation — summary

Scope: blind reroll vs targeted repair, same retry budget (max 2 attempts), on real
failed cases from `live_test_04_street_look3`. This is a **small controlled repair
ablation**, not a full journal-scale multi-baseline study (see MASTER_INSTRUCTIONS /
project CLAUDE.md ground rules). Condition B (targeted repair) reuses the already-
promoted, already-approved evidence on disk — it was not regenerated for this ablation.

## Motion cases (objective metric: Farnebäck optical flow, % frame-height/frame)

{chr(10).join(motion_lines)}

Note: the literal original (pre-repair) Kling prompt text for shot_001/shot_003 was
edited in place in `generate_street_run.py` and not separately archived. Condition A's
motion prompt here is a clearly-labelled reconstructed neutral/undirected walking
description (no motion-cue engineering), not a byte-exact resubmission of the lost
original. Report it as such if this goes into the dissertation.

## Keyframe cases (human-gated: identity / outfit / framing rubric)

- shot_001: A = original partial-profile framing (generate_street_run.py, unchanged) ·
  B = promoted 3/4 over-shoulder face-visible keyframe (regen_shot001_3q.py)
- shot_002: A = original back-view prompt (generate_street_run.py, unchanged) ·
  B = promoted identity/outfit-fix keyframe (regen_shot002_004.py)
- shot_004: A = original face-visible prompt (generate_street_run.py, unchanged) ·
  B = promoted proportion/outfit-fix keyframe (regen_shot002_004.py + v4_proportion_fix)
- shot_003 has NO real repair case on record (feet-only close-up, single keyframe,
  never revised) and is intentionally excluded rather than invented.

Human verdicts for the new blind-reroll keyframes are NOT pre-filled — open
`ablation_contact_sheet.png` and fill the `human_verdict` / `accepted` columns in
`ablation_results.csv` using this fixed rubric: (1) identity matches the Look 3
approved anchor, (2) outfit is the correct charcoal blazer / olive tie / wide denim
(not a black corporate blazer or slim trousers), (3) framing matches the shot's spec
(over-shoulder face-visible for 001/004, back-view no-face for 002).

## Files produced
- `ablation_results.csv` — per-attempt log, ready for the dissertation appendix
- `ablation_contact_sheet.png` — visual comparison, blind reroll vs targeted repair
- `ablation_summary.md` — this file
"""
    (OUT_DIR / "ablation_summary.md").write_text(summary)

    # LaTeX table (dissertation-ready)
    latex = r"""\begin{table}[h]
\centering
\caption{Small controlled repair ablation: blind reroll vs.\ targeted repair, same retry budget (max 2 attempts).}
\label{tab:repair_ablation}
\begin{tabular}{lccc}
\hline
Case & Condition & Attempts to acceptance & Result \\
\hline
"""
    for sid in ["shot_001", "shot_003"]:
        b = KNOWN_MOTION_PCT[sid]["targeted_repair_b"]
        blind = [r for r in rows if r["case"] == f"{sid}_motion" and r["condition"] == "A_blind_reroll"]
        blind_vals = [r["recovered_motion_pct"] for r in blind if isinstance(r["recovered_motion_pct"], (int, float))]
        best_blind = max(blind_vals) if blind_vals else "pending"
        latex += f"{sid} motion & blind reroll & {len(blind) if blind else '--'} & {best_blind}\\% recovered \\\\\n"
        latex += f"{sid} motion & targeted repair & 1 & {b}\\% recovered \\\\\n"
    for sid in ["shot_001", "shot_002", "shot_004"]:
        latex += f"{sid} keyframe & blind reroll & -- & pending human review \\\\\n"
        latex += f"{sid} keyframe & targeted repair & 1 & accepted (promoted) \\\\\n"
    latex += r"""\hline
\end{tabular}
\end{table}
"""
    (OUT_DIR / "ablation_table.tex").write_text(latex)

    print(f"Wrote {csv_path}")
    print(f"Wrote {OUT_DIR / 'ablation_summary.md'}")
    print(f"Wrote {OUT_DIR / 'ablation_table.tex'}")
    if sheet_path:
        print(f"Wrote {sheet_path}")
    if gen_log is None:
        print("\nNOTE: generation_log.json not found — this ran on Condition B only. "
              "Run ablation_blind_reroll_generate.py --confirm first for Condition A data.")


if __name__ == "__main__":
    main()
