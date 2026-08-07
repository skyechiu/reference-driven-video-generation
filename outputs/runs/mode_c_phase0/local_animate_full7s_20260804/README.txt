Pre-submission Mode C demo runs (reported in dissertation §4.18) — 2026-08-04
Reported in dissertation §4.18 as the local baseline of the hosted-service comparison.

Backend: WanGP v12.41, Wan2.2 Animate 14B (quanto int8), remote RTX 4080 16GB (w33108)
Mode: Replace Person in Control Video by Person in Ref Image (Condition A style)
Control video: test2.mov (1080x1924, 30fps, ~7s, 209 frames, 3 sliding windows)
Reference: target_look_reference.png (Look 1 activewear, full-body front)
Settings: 544x960 (540p), 60 steps, unipc, seed 630814980, relighting LoRA auto
Generation time: ~2h55m per run. Three runs: 16h45 / 17h51 / 18h33 (same seed/queue).
Note: session ended with GPU driver fault on w33108 (nvidia-smi: no devices); admin reboot requested.
