Pre-submission hosted-service comparison runs (reported in dissertation §4.18) — 2026-08-04/05
Reported in dissertation §4.18. Runs predate submission. Same driving performance as the local local_animate_full7s_20260804 runs; character reference
differs (hosted runs: Look 2 gown-in-dressing-room; local runs: Look 1 activewear), so the
quality comparison is indicative, not controlled. Pushed through hosted one-click services.

wan.video (official Tongyi, "Transfer" function, Wan2.7, 720P 9:16):
1. wan_video_transfer_wan27_gown_4s_20260805.mp4 — NO PROMPT. The service silently applied
   replace-style semantics: kept the DRIVING VIDEO's room, discarded the reference image's
   dressing-room background. Identity/outfit carried over; background control was implicit.
2. wan_video_transfer_prompted_gown_dressingroom_5s_20260805.mp4 — WITH EXPLICIT PROMPT
   ("Transfer only the pose and body motion ... Keep the image's background completely
   unchanged: the dim vintage dressing room ... Do not use the video's room.").
   Dressing-room background correctly preserved -> explicit instruction restored control.

Viggle AI (free tier, 7s full driving clip):
3. viggle_gown_dressingroom_bg_7s_20260804.mp4 — image-background mode
4. viggle_gown_video_bg_7s_20260804.mp4 — video-background mode
   Visible identity drift, garment simplification, weaker motion/contact fidelity vs local runs.

Reading: the wan.video pair demonstrates the CONTROL axis (implicit default vs explicit
instruction); the Viggle pair and the local-vs-hosted comparison demonstrate the QUALITY axis.
Both mirror the dissertation's §3.1.1 argument for an explicit orchestration layer.
