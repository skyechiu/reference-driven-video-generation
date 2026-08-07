# Abstract

Short-form vertical video is produced at scale by reusing the structure of successful clips — their
shot rhythm, framing and pacing — rather than their pixels. End-to-end text-to-video models cannot
support this workflow: they are one-shot black boxes with no per-shot control and no way to repair a
single failed shot. This dissertation presents a *reference-driven, agentic* system for short-form
video regeneration. A reference clip is decomposed by deterministic tools into a five-track,
beat-aligned storyboard (shots, timing, framing, camera motion, character motion); a fixed
intellectual-property (IP) character is then regenerated per shot with identity, look and scene held
as separate conditioning channels, keyframe first and then image-to-video. An agentic
evaluation–repair loop scores each shot, diagnoses failures and regenerates only the failed shot,
recording every decision in a state file with an explicit `needs_human` terminal state. The system
is built entirely on closed image and video generation APIs, with no model training. It is evaluated
on a four-shot reference under two settings — reference-scene preservation and cross-scene structure
transfer — with an executed-versus-pending reporting rule throughout. Executed results include a
successful end-to-end run under human review, a log-reconstructed loop-off-versus-loop-on comparison
(25% to 100% acceptance), a motion-energy audit, and an identity-metric audit which finds that a
face-embedding distance under-scores a human-approved synthetic character — an argued reason to gate
acceptance on human review rather than a single metric. Two honest negative results (skeleton-image
guidance is too weak a control signal for the image API; single-keyframe animation under-conditions
the temporal sequence) are reported as engineering findings. The system is positioned as a proof of
concept for auditable, reference-structured and selectively-repairable generation, not
general-purpose motion transfer or autonomous cinematic production.
