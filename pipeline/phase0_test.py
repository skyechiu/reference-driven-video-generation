"""
phase0_test.py — Phase 0 Feasibility Test

The make-or-break risk: can we preserve IP character identity
while following pose conditioning?

Test protocol:
  1. Pick 3 distinct poses (standing, seated, profile)
  2. Generate keyframe for each using your chosen backend
  3. Score identity against IP reference (ArcFace)
  4. Define PASS as: all 3 shots score >= threshold

Run this BEFORE building the full pipeline.
If it fails → downgrade to keyframe-remake approach (documented in config).

Usage:
  python phase0_test.py                        # uses GENERATOR_BACKEND from config
  python phase0_test.py --backend api           # force api backend
  python phase0_test.py --backend local        # force local (InstantID) backend
  python phase0_test.py --calibrate            # calibrate threshold from results
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from config import (
    IP_REFERENCE_IMAGES,
    IP_CHARACTER_DESCRIPTION,
    IDENTITY_THRESHOLD,
    OUTPUT_DIR,
)
import stage4_evaluate as evaluator


# ─── Test Poses ───────────────────────────────────────────────────────────
# Three poses that stress-test identity vs pose conditioning trade-off.
# Provide your own pose skeleton images, or leave pose_image as None
# to test generation without pose control (useful baseline).

TEST_POSES = [
    {
        "pose_id": "pose_A_standing_front",
        "framing": "medium",
        "description": "Character stands upright, facing camera directly, arms at sides.",
        "pose_image_path": None,   # ← swap in skeleton image if you have one
    },
    {
        "pose_id": "pose_B_profile_turn",
        "framing": "medium-close-up",
        "description": "Character turns 45 degrees, looking over shoulder, slight chin tilt.",
        "pose_image_path": None,
    },
    {
        "pose_id": "pose_C_seated_low",
        "framing": "medium-wide",
        "description": "Character seated, knees slightly bent, hands in lap, looking up.",
        "pose_image_path": None,
    },
]

SCENE_PROMPT = "A woman stands in a sunlit greenhouse surrounded by white orchids, soft morning light"


# ─── Run Phase 0 ─────────────────────────────────────────────────────────

def run_phase0(backend: str = None) -> dict:
    from config import GENERATOR_BACKEND
    backend = backend or GENERATOR_BACKEND

    print("\n" + "="*60)
    print(f"PHASE 0 — FEASIBILITY TEST")
    print(f"Backend: {backend}")
    print(f"Pass threshold (IDENTITY): {IDENTITY_THRESHOLD}")
    print(f"IP references: {len(IP_REFERENCE_IMAGES)} images")
    print("="*60 + "\n")

    # Load generator
    if backend == "api":
        from generators.api_gen import APIGenerator
        gen = APIGenerator()
    elif backend == "local":
        from generators.local_gen import LocalGenerator
        gen = LocalGenerator()
    else:
        raise ValueError(f"Unknown backend: {backend}")

    phase0_dir = OUTPUT_DIR / "phase0"
    phase0_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for pose in TEST_POSES:
        print(f"\n── {pose['pose_id']} ──────────────────────────────")

        # Build a fake shot dict (same schema as pipeline)
        shot = {
            "shot_id": pose["pose_id"],
            "framing": pose["framing"],
            "description": pose["description"],
            "pose_keypoints": None,
            "pose_image_path": pose.get("pose_image_path"),
            "beat_time_s": 0.0,
            "duration_s": 3.0,
        }

        try:
            img_path = gen.generate_keyframe(
                shot=shot,
                ip_images=IP_REFERENCE_IMAGES,
                character_description=IP_CHARACTER_DESCRIPTION,
                scene_prompt=SCENE_PROMPT,
                repair_hints=None,
            )
            print(f"  generated → {img_path}")

            # Score identity
            identity = evaluator.compute_identity_score(img_path, IP_REFERENCE_IMAGES)
            passed = identity >= IDENTITY_THRESHOLD

            result = {
                "pose_id": pose["pose_id"],
                "image_path": img_path,
                "identity_score": identity,
                "threshold": IDENTITY_THRESHOLD,
                "passed": passed,
                "status": "PASS ✓" if passed else "FAIL ✗",
            }
            results.append(result)

            print(f"  identity score: {identity:.4f} (threshold={IDENTITY_THRESHOLD})")
            print(f"  result: {result['status']}")

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "pose_id": pose["pose_id"],
                "error": str(e),
                "passed": False,
                "status": "ERROR",
            })

    # Overall verdict
    all_passed = all(r["passed"] for r in results)
    pass_count = sum(1 for r in results if r["passed"])

    print("\n" + "="*60)
    print(f"PHASE 0 RESULT: {'PASS ✓' if all_passed else 'FAIL ✗'}")
    print(f"  {pass_count}/{len(results)} poses passed")
    print("="*60)

    if not all_passed:
        print("\n⚠️  FALLBACK RECOMMENDATION:")
        print("  Identity does not hold across all poses at current threshold.")
        print("  Options:")
        print("  1. Lower IDENTITY_THRESHOLD in config.py (document tradeoff)")
        print("  2. Strengthen IP conditioning (ip_adapter_scale ↑ to 0.9)")
        print("  3. Downgrade to keyframe-remake approach (valid dissertation scope)")
        print("  Document your choice and rationale in the dissertation.\n")
    else:
        print("\n✓ Phase 0 passed. Proceed to full pipeline build.\n")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "backend": backend,
        "identity_threshold": IDENTITY_THRESHOLD,
        "scene_prompt": SCENE_PROMPT,
        "results": results,
        "overall_pass": all_passed,
        "pass_count": f"{pass_count}/{len(results)}",
    }
    report_path = phase0_dir / "phase0_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved → {report_path}")

    return report


# ─── Threshold Calibration ────────────────────────────────────────────────

def calibrate_threshold() -> None:
    """
    Helper: generate multiple samples of the same character in the same pose
    (same scene, no pose change), measure their ArcFace distribution,
    and suggest a threshold.

    Run this to set IDENTITY_THRESHOLD empirically rather than guessing.
    """
    print("\n── Threshold Calibration ──────────────────────────────")
    print("Generating 5 samples of pose_A for threshold calibration...")

    from generators.api_gen import APIGenerator
    gen = APIGenerator()

    phase0_dir = OUTPUT_DIR / "phase0" / "calibration"
    phase0_dir.mkdir(parents=True, exist_ok=True)

    shot = {
        "shot_id": "calibration",
        "framing": "medium-close-up",
        "description": "Character looks directly at camera, neutral expression.",
        "pose_keypoints": None,
        "pose_image_path": None,
        "beat_time_s": 0.0,
        "duration_s": 3.0,
    }

    scores = []
    for i in range(5):
        try:
            img_path = gen.generate_keyframe(
                shot=shot,
                ip_images=IP_REFERENCE_IMAGES,
                character_description=IP_CHARACTER_DESCRIPTION,
                scene_prompt="Character in neutral studio lighting, plain white background",
            )
            score = evaluator.compute_identity_score(img_path, IP_REFERENCE_IMAGES)
            scores.append(score)
            print(f"  sample {i+1}: identity={score:.4f}  ({img_path})")
        except Exception as e:
            print(f"  sample {i+1}: ERROR — {e}")

    if scores:
        import statistics
        mean = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0
        suggested = mean - std  # 1 std below mean as conservative threshold

        print(f"\n  Mean identity across 5 samples: {mean:.4f}")
        print(f"  Std dev: {std:.4f}")
        print(f"  Suggested threshold (mean - 1σ): {suggested:.4f}")
        print(f"\n  → Set IDENTITY_THRESHOLD = {suggested:.2f} in config.py")


# ─── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 0 feasibility test")
    parser.add_argument("--backend", choices=["api", "local"], default=None)
    parser.add_argument("--calibrate", action="store_true",
                        help="Run threshold calibration instead of full Phase 0 test")
    args = parser.parse_args()

    if args.calibrate:
        calibrate_threshold()
    else:
        run_phase0(backend=args.backend)
