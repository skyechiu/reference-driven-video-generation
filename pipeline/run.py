"""
run.py — Main Pipeline CLI

Usage:
  # Set up API keys first:
  export OPENAI_API_KEY=sk-...
  export KLING_ACCESS_KEY=...
  export KLING_SECRET_KEY=...

  # Phase 0 feasibility test (RUN THIS FIRST):
  python run.py phase0

  # Full pipeline (best backend, with reference video):
  python run.py init --video ref.mp4 --scene "Character walks through a greenhouse at dawn"
  python run.py analyze
  python run.py template
  python run.py generate
  python run.py evaluate
  python run.py repair

  # OR run everything in sequence:
  python run.py all --video ref.mp4 --scene "..."

  # Skip reference video (hand-authored storyboard):
  python run.py init --scene "..."
  python run.py template --manual storyboard.json
  python run.py generate
  python run.py evaluate
  python run.py repair

  # Ablation: run WITHOUT repair loop (for comparison):
  python run.py all --video ref.mp4 --scene "..." --baseline

  # Use free backend:
  GENERATOR_BACKEND=local VIDEO_BACKEND=cogvideox python run.py all --video ref.mp4 --scene "..."
"""

import argparse
import sys

from config import (
    IP_REFERENCE_IMAGES, IP_CHARACTER_DESCRIPTION,
    GENERATOR_BACKEND, VIDEO_BACKEND,
    ensure_dirs,
)
import state as st


def cmd_phase0(args):
    from phase0_test import run_phase0
    run_phase0(backend=getattr(args, "backend", None))


def cmd_init(args):
    ensure_dirs()
    scene = args.scene or input("Scene prompt: ")
    s = st.init_state(
        reference_video=getattr(args, "video", "") or "",
        ip_images=IP_REFERENCE_IMAGES,
        scene_prompt=scene,
        character_description=IP_CHARACTER_DESCRIPTION,
    )
    print(f"[run] State initialised → {st.STATE_FILE}")
    print(f"  Backend: {GENERATOR_BACKEND} + {VIDEO_BACKEND}")
    print(f"  IP refs: {IP_REFERENCE_IMAGES}")


def cmd_analyze(args):
    s = st.load()
    video = getattr(args, "video", None) or s.get("reference_video", "")
    if not video:
        print("ERROR: no reference video. Provide --video or use --manual storyboard.")
        sys.exit(1)
    import stage1_analyze
    stage1_analyze.run(video, s)


def cmd_template(args):
    s = st.load()
    manual = getattr(args, "manual", None)
    import stage2_template
    if manual:
        stage2_template.load_manual_storyboard(manual, s)
        st.save(s)
    else:
        stage2_template.run(s, scene_prompt=getattr(args, "scene", None))


def cmd_generate(args):
    s = st.load()
    shot_ids = getattr(args, "shots", None)
    import stage3_generate
    stage3_generate.run(s, shot_ids=shot_ids)


def cmd_evaluate(args):
    s = st.load()
    import stage4_evaluate
    stage4_evaluate.run(s)
    st.print_summary(s)


def cmd_repair(args):
    s = st.load()
    import stage5_repair
    if getattr(args, "baseline", False):
        stage5_repair.run_baseline(s)
    else:
        stage5_repair.run(s)


def cmd_all(args):
    """Run the full pipeline end-to-end."""
    print(f"\n{'='*60}")
    print(f"FULL PIPELINE — {GENERATOR_BACKEND.upper()} backend")
    print(f"{'='*60}\n")

    cmd_init(args)
    s = st.load()

    manual = getattr(args, "manual", None)
    if manual:
        import stage2_template
        stage2_template.load_manual_storyboard(manual, s)
        st.save(s)
    else:
        cmd_analyze(args)
        cmd_template(args)

    cmd_generate(args)
    cmd_evaluate(args)

    if not getattr(args, "baseline", False):
        cmd_repair(args)
    else:
        s = st.load()
        import stage5_repair
        stage5_repair.run_baseline(s)

    st.print_summary(st.load())


# ─── CLI Parser ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Reference-Driven Video Pipeline")
    sub = parser.add_subparsers(dest="command")

    # phase0
    p0 = sub.add_parser("phase0", help="Run Phase 0 feasibility test")
    p0.add_argument("--backend", choices=["api", "local"])
    p0.add_argument("--calibrate", action="store_true")

    # init
    pi = sub.add_parser("init", help="Initialise project state")
    pi.add_argument("--video", help="Path to reference video")
    pi.add_argument("--scene", help="Scene prompt for new video")

    # analyze
    pa = sub.add_parser("analyze", help="Run Stage 1: reference analysis")
    pa.add_argument("--video", help="Path to reference video")

    # template
    pt = sub.add_parser("template", help="Run Stage 2: template builder")
    pt.add_argument("--scene", help="Override scene prompt")
    pt.add_argument("--manual", help="Path to manual storyboard JSON (skip Stage 1)")

    # generate
    pg = sub.add_parser("generate", help="Run Stage 3: generation")
    pg.add_argument("--shots", nargs="*", help="Specific shot IDs to generate")

    # evaluate
    sub.add_parser("evaluate", help="Run Stage 4: evaluation")

    # repair
    pr = sub.add_parser("repair", help="Run Stage 5: repair loop")
    pr.add_argument("--baseline", action="store_true", help="Skip repair (ablation baseline)")

    # all
    pall = sub.add_parser("all", help="Run full pipeline end-to-end")
    pall.add_argument("--video", help="Path to reference video")
    pall.add_argument("--scene", required=True, help="Scene prompt for new video")
    pall.add_argument("--manual", help="Manual storyboard JSON (skips Stage 1-2)")
    pall.add_argument("--baseline", action="store_true", help="Skip repair loop (ablation)")

    args = parser.parse_args()

    commands = {
        "phase0": cmd_phase0,
        "init": cmd_init,
        "analyze": cmd_analyze,
        "template": cmd_template,
        "generate": cmd_generate,
        "evaluate": cmd_evaluate,
        "repair": cmd_repair,
        "all": cmd_all,
    }

    if args.command not in commands:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
