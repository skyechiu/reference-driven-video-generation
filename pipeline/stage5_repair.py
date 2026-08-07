"""
stage5_repair.py — Evaluation-Repair Loop

This is the agentic core of the dissertation.
The loop: Evaluate → Diagnose → Repair → Re-evaluate → repeat until pass or needs_human.

Two-layer repair:
  Base layer  (always active):   change seed / strengthen prompt / regenerate
  Enhanced layer (bonus):        classify failure type → targeted fix

The decision log in project_state.json records every attempt,
giving the system its "agentic" character and providing dissertation evaluation data.
"""

import random
from typing import Optional

from config import MAX_REPAIR_ATTEMPTS
import state as st
import stage3_generate as gen_stage
import stage4_evaluate as eval_stage


# ─── Failure Diagnosis ────────────────────────────────────────────────────

def classify_failure(scores: dict) -> dict:
    """
    Enhanced layer: classify the primary failure mode and suggest repair action.
    Returns repair_hints dict for the generator.

    Uses 5-track failure naming to match generation_unit.repair_strategy:
      identity_failed, look_failed, framing_failed, camera_motion_failed,
      character_motion_failed, timing_failed, extra_subject_failed.

    Honest caveat: diagnosis can be imperfect. The dissertation should evaluate
    where targeted repair helps vs misjudges compared to the base layer.
    Note: camera_motion_failed and character_motion_match are "planned" metrics —
    stage4_evaluate.py does not yet compute them; these branches are present for
    future compatibility and dissertation completeness.
    """
    from config import IDENTITY_THRESHOLD, POSE_THRESHOLD, BEAT_ALIGNMENT_MAX_MS, FRAMING_THRESHOLD

    hints = {
        # 5-track failure flags (all False by default)
        "identity_failed":          False,
        "look_failed":              False,
        "framing_failed":           False,
        "camera_motion_failed":     False,   # planned — stage4 not yet measuring this
        "character_motion_failed":  False,   # planned — stage4 not yet measuring this
        "timing_failed":            False,
        "extra_subject_failed":     False,
        # Base layer (always active)
        "seed_change":              True,
        # Repair notes
        "pose_note":                "",
        "framing_note":             "",
        "primary_failure":          "unknown",
    }

    # Determine primary failure (ordered by severity for IP consistency)
    if scores.get("identity", 1.0) < IDENTITY_THRESHOLD:
        hints["identity_failed"] = True
        hints["primary_failure"] = "identity_failed"
        # Targeted fix: strengthen IP conditioning
        hints["ip_scale_boost"] = 0.1         # increase ip_adapter_scale by this
        hints["identity_emphasis"] = True
        hints["repair_action"] = "raise_lora_weight"

    elif scores.get("pose", 1.0) < (1.0 - POSE_THRESHOLD):
        hints["character_motion_failed"] = True
        hints["primary_failure"] = "character_motion_failed"
        hints["pose_note"] = "Match the skeleton pose exactly — body position, arm angles, head tilt"
        hints["controlnet_scale_boost"] = 0.1   # increase controlnet scale
        hints["repair_action"] = "strengthen_pose_conditioning"

    elif scores.get("framing", 1.0) < FRAMING_THRESHOLD:
        hints["framing_failed"] = True
        hints["primary_failure"] = "framing_failed"
        hints["framing_note"] = "Reframe the shot to match the specified camera distance"
        hints["repair_action"] = "rewrite_framing_prompt"

    elif scores.get("beat_alignment_ms", 0) > BEAT_ALIGNMENT_MAX_MS:
        hints["timing_failed"] = True
        hints["primary_failure"] = "timing_failed"
        # Beat errors are timing issues, not generation issues — adjust cut point
        hints["adjust_cut"] = True
        hints["repair_action"] = "adjust_cut_timing"

    # camera_motion_failed — placeholder for when stage4 implements this metric
    # Currently never triggered (score key absent); added for future compatibility.
    elif scores.get("camera_motion_match") is False:
        hints["camera_motion_failed"] = True
        hints["primary_failure"] = "camera_motion_failed"
        hints["camera_motion_note"] = (
            "Generated clip camera motion does not match the classified reference type. "
            "Rewrite the camera_motion block of the prompt with stronger explicit direction tokens."
        )
        hints["repair_action"] = "rewrite_camera_block"

    # Look consistency failures (enhanced layer, applies on top of primary failure)
    look_score = scores.get("look_consistency", 1.0)
    look_detail = scores.get("look_detail", {})
    LOOK_PASS = 0.65
    if look_score < LOOK_PASS:
        hints["look_failed"] = True
        if hints["primary_failure"] == "unknown":
            hints["primary_failure"] = "look_failed"
        hints["repair_action"] = hints.get("repair_action") or "strengthen_look_conditioning"
        # Fine-grained look diagnosis → targeted prompt additions
        if look_detail.get("hair_match", 1.0) < 0.55:
            hints["look_repair"] = "hair_wrong"
            hints["look_note"] = "Reinforce hair description: add explicit hair constraint to prompt"
        elif look_detail.get("outfit_match", 1.0) < 0.55:
            hints["look_repair"] = "outfit_wrong"
            hints["look_note"] = "Use full-body look reference image; strengthen outfit tokens in prompt"
        elif look_detail.get("shoes_match", 1.0) < 0.55:
            hints["look_repair"] = "shoes_missing"
            hints["look_note"] = "Widen framing to show feet; add shoe description to prompt"
        else:
            hints["look_repair"] = "body_silhouette_wrong"
            hints["look_note"] = "Reduce stylisation strength; re-emphasise body_silhouette in prompt"

    # Extra subject detected (single-character constraint violation)
    subject_count = scores.get("subject_count", {})
    if subject_count and not subject_count.get("pass", True):
        hints["extra_subject_failed"] = True
        if hints["primary_failure"] == "unknown":
            hints["primary_failure"] = "extra_subject_failed"
        hints["repair_action"] = hints.get("repair_action") or "strengthen_negative_prompt"
        hints["extra_subject_note"] = (
            "Extra person detected in generated image. "
            "Regenerate with maximum single-character constraint: "
            "explicitly state 'only one person in frame, no background figures, no crowd'. "
            "Remove any reference images that show group scenes. "
            "Increase negative prompt weight for 'multiple people'."
        )

    return hints


# ─── Repair a Single Shot ─────────────────────────────────────────────────

def repair_shot(shot: dict, state: dict) -> bool:
    """
    Attempt repair on a failed shot.
    Returns True if the repaired shot passes evaluation.
    """
    shot_id = shot["shot_id"]
    attempts = shot["evaluation"]["attempts"]

    if not attempts:
        print(f"[repair] {shot_id}: no prior attempts found, skipping")
        return False

    latest = attempts[-1]
    scores = latest["scores"]
    attempt_num = len(attempts) + 1

    print(f"\n[repair] {shot_id} — attempt {attempt_num}/{MAX_REPAIR_ATTEMPTS}")
    print(f"  prior scores: {scores}")

    # Classify failure → repair hints
    hints = classify_failure(scores)
    print(f"  primary failure: {hints['primary_failure']}")
    print(f"  repair hints: {hints}")

    # Update state: record what we're about to do
    # (actual logging happens after the attempt in evaluate)

    # Re-generate with hints
    success = gen_stage.run_repair(state, shot_id, repair_hints=hints)
    if not success:
        st.log_attempt(
            state=state,
            shot_id=shot_id,
            scores={"identity": 0, "pose": 0, "framing": 0, "beat_alignment_ms": 9999,
                    "look_consistency": 0,
                    "subject_count": {"expected": 1, "detected": 0, "extra_detected": False, "pass": True}},
            verdict="fail",
            diagnosis="generation failed during repair",
            repair_action=f"attempted repair for {hints['primary_failure']}",
        )
        return False

    # Re-evaluate
    result = eval_stage.evaluate_shot(shot, state)
    repair_action = _repair_action_label(hints)
    st.log_attempt(
        state=state,
        shot_id=shot_id,
        scores=result["scores"],
        verdict=result["verdict"],
        diagnosis=result["diagnosis"],
        repair_action=repair_action,
    )

    improved = result["verdict"] == "pass"
    print(f"  result: {'PASS ✓' if improved else 'FAIL ✗'}")
    return improved


def _repair_action_label(hints: dict) -> str:
    """Human-readable label for the decision log — uses 5-track repair_action field."""
    base = hints.get("repair_action", f"seed_change for {hints.get('primary_failure', 'unknown')}")
    look_note = hints.get("look_note", "")
    if look_note:
        base += f" + {look_note}"
    return base


# ─── Full Repair Loop ─────────────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    The agentic evaluation-repair loop.
    Runs until all shots pass or hit MAX_REPAIR_ATTEMPTS.

    Loop:
      1. Find all failed shots
      2. For each: diagnose + repair + re-evaluate
      3. Repeat until no more repairable shots
    """
    print("\n" + "="*50)
    print("REPAIR LOOP STARTING")
    print("="*50)

    max_iterations = MAX_REPAIR_ATTEMPTS
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        # Find shots that can still be repaired
        repairable = [
            s for s in state["shots"]
            if s["evaluation"]["status"] == "fail"
            and len(s["evaluation"]["attempts"]) < MAX_REPAIR_ATTEMPTS
        ]

        if not repairable:
            print(f"\n[repair] no repairable shots left after iteration {iteration}")
            break

        print(f"\n[repair] iteration {iteration}: {len(repairable)} shots to repair")

        for shot in repairable:
            repair_shot(shot, state)

        st.save(state)

    # Final pass — update any shots still at fail status but at max attempts
    for shot in state["shots"]:
        if (shot["evaluation"]["status"] == "fail"
                and len(shot["evaluation"]["attempts"]) >= MAX_REPAIR_ATTEMPTS):
            shot["evaluation"]["status"] = "needs_human"
            print(f"[repair] {shot['shot_id']} → needs_human (max attempts reached)")

    # Final stats
    state["run_stats"]["passed"] = sum(
        1 for s in state["shots"] if s["evaluation"]["status"] == "pass"
    )
    state["run_stats"]["failed"] = sum(
        1 for s in state["shots"] if s["evaluation"]["status"] == "fail"
    )
    state["run_stats"]["needs_human"] = sum(
        1 for s in state["shots"] if s["evaluation"]["status"] == "needs_human"
    )

    st.set_stage(state, "done")
    st.print_summary(state)
    return state


# ─── Baseline (repair OFF) ────────────────────────────────────────────────

def run_baseline(state: dict) -> dict:
    """
    Run WITHOUT repair loop — single-pass generation only.
    Used for the ablation experiment: compare with vs without repair.
    """
    print("[repair] BASELINE MODE — repair loop disabled")
    st.set_stage(state, "done")
    st.print_summary(state)
    return state


if __name__ == "__main__":
    import sys
    s = st.load()
    if "--baseline" in sys.argv:
        run_baseline(s)
    else:
        run(s)
