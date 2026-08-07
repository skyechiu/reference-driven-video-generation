# Chapter 1 — Introduction

## 1.1 Motivation and background

Short-form vertical video — the 9:16 clips that dominate TikTok, Instagram Reels and YouTube Shorts
— is not usually authored from scratch. Creators study clips that already work and reuse their
*structure*: the number and order of shots, the cut rhythm, the framing of each shot, and the way
motion lands on the beat. What changes between one creator's version and another is the *content* —
the character, the outfit, the location — not the underlying structure. A short is, to a first
approximation, a small set of key poses and framings joined by beat-driven cuts.

Recent text-to-video and image-to-video models make it possible to generate such clips, but they do
not support this reuse-of-structure workflow. A prompt goes in and a clip comes out as a single
opaque unit. If one shot is wrong — the character's identity drifts, the framing is off, a cut
misses the beat — there is no handle to inspect *which* shot failed and no way to regenerate only
that shot; the creator re-rolls the whole clip and hopes. Equally, a naive "AI watches a video and
makes a video" approach either copies the reference too literally, raising derivative-work concerns,
or discards its structure entirely and produces something unrelated. Neither extreme gives a
controllable, auditable path from a reference clip to a new clip that keeps the reference's
*structure* while replacing its *content* with a fixed, creator-owned IP character.

This gap is an *orchestration* problem more than a generative-modelling problem. The individual
capabilities exist — shot detection, beat tracking, pose estimation, identity-conditioned image
generation, image-to-video — but they are not composed into a loop that decomposes a reference,
regenerates content shot by shot, checks the result, and repairs what failed. Building that loop is
the subject of this dissertation.

## 1.2 Problem statement

The problem addressed is: given (i) a reference short-form video, (ii) a fixed IP character, and
(iii) a target scene, produce a new 9:16 short that preserves the reference's shot structure and
action intent while rendering the IP character in the target scene — and do so through a
controllable pipeline that can detect and repair individual failed shots, rather than a single
end-to-end generation. The system must operate on closed generation APIs without training a model,
because model training is out of scope for the timeline and hardware of an MSc project and is not the
intended contribution.

## 1.3 Research question

*Can a reference short-form video be decomposed into a reusable structural template and regenerated
with a fixed IP character — under both scene preservation and scene replacement — using an agentic
evaluation–repair loop built only on closed generation APIs; and does such a loop measurably improve
output acceptance over a one-shot baseline?*

## 1.4 Aims and objectives

The aim is to design, build and honestly evaluate the pipeline above. The objectives are:

1. Decompose a reference clip into a five-track, beat-aligned storyboard (shots, timing, framing,
   camera motion, character motion) using deterministic tools rather than model guessing
   (Stage 1–2).
2. Regenerate each shot with the IP character, keeping identity, look and scene as separate
   conditioning channels, keyframe first and then image-to-video (Stage 3).
3. Implement an agentic evaluation–repair loop that scores each shot, diagnoses failures, repairs
   only the failed shot, and logs every decision to a state file with a `needs_human` terminal state
   (Stage 4).
4. Evaluate identity, pose, framing and beat alignment; compare the loop off versus on; and report
   executed versus pending results honestly.
5. Probe, as future-facing feasibility, a stronger structural backend (driving-video person
   replacement, Mode C).

## 1.5 Contributions

This work contributes: (i) a reference-video decomposition into a five-track, beat-aligned
storyboard representation computed by deterministic tools rather than LLM guessing; (ii) an
IP-conditioned, keyframe-first per-shot regeneration pipeline that separates identity, look and
scene; (iii) an agentic evaluation–repair loop with a per-shot decision log that repairs only the
failed shot and records an explicit `needs_human` terminal state; (iv) a graded
structural-conditioning strategy that matches conditioning strength to the reliability of the
reference pose per shot; and (v) an honest executed-versus-pending evaluation, including a negative
result (skeleton-image guidance is too weak a control signal for the image API) and an
identity-metric audit showing that a face-embedding distance mis-scores a synthetic character.

## 1.6 Scope and boundaries

The system is a proof of concept. It is evaluated on one reference video, four shots, one character
and two scenes; multi-character interaction, fast action, occlusion, long-form and stylised content
are not validated. It performs *reference-structure-guided regeneration*, not pixel-level motion
transfer: the reference supplies shot boundaries, framing, a broad camera-motion class, action
intent and beat timing, but not per-frame limb trajectories. It is built on closed external
services, so the *architecture* is reproducible but the pixel-level output is bound to specific model
versions and the execution date. Reference material is used for structure only and its pixels are not
reproduced in the output.

## 1.7 Dissertation structure

Chapter 2 reviews the background and related work. Chapter 3 details the methodology: the four-stage
agentic architecture, the reference analysis and template representation, IP-conditioned generation,
the evaluation–repair loop, the state file and decision log, and the driving-video backend (Mode C).
Chapter 4 reports the evaluation under the executed-versus-pending rule. Chapter 5 concludes and sets
out future work.
