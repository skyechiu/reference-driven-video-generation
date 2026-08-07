# Chapter 2 — Background and Related Work

## 2.1 Structure in short-form video: a keyframing view

Short-form vertical video is characterised by rapid, beat-aligned cutting and a small number of
strong key poses per clip. This structure is not incidental to the medium; it is a contemporary,
algorithmically-distributed instance of principles that classical animation formalised decades ago,
and reading it through that lens is what motivates the whole pipeline. Traditional animation
distinguishes *pose-to-pose* construction — the animator first establishes the defining extreme
poses, the *keyframes*, and only then fills the in-betweens — from *straight-ahead* action drawn
frame by frame (Thomas & Johnston, 1981). Lasseter's foundational transfer of Disney's twelve principles to
computer animation keeps that distinction central and adds *timing* (how many frames a motion
occupies, which sets its weight and legibility) and *staging* (framing and composition that direct
the viewer's attention to one idea at a time) as the levers that make a pose read on screen
(Lasseter, 1987; Williams, 2001). Viewed this way, a short-form clip is close to a pure pose-to-pose
sequence: a few readable key poses, each staged by its framing, joined by cuts whose timing is locked
to a musical beat.

This framing does two things for the system. First, it makes the structure *recoverable* by
signal-level tools — shot boundaries by content-based cut detection (Castellano, n.d.), beats by onset
and tempo tracking (McFee et al., 2015), and character pose by 2D keypoint estimation (Lugaresi et al., 2019; Yang et al., 2023).
Second, and more importantly, it dictates *how to regenerate*. Rather than treating a clip as an
indivisible sequence, the pipeline of Chapter 3 generates the defining keyframe of each shot first (a
computational analogue of blocking key poses), aligns the cuts to a beat grid (timing), and carries
an explicit per-shot framing track (staging) before any image-to-video in-betweening. The
keyframe-first, beat-aligned design is therefore a direct, tool-driven realisation of pose-to-pose
animation with explicit timing and staging, rather than an ad-hoc engineering convenience — a point
returned to when the creative-design intent of the system is set out in §3.2.1.

## 2.2 Identity-preserving image generation

Preserving a fixed character across generations is the central difficulty, and the methods that
address it form a clear historical progression in which each generation removes one cost and incurs
another. The first generation was *training-based*: DreamBooth (Ruiz et al., 2023) fine-tunes a whole
diffusion model to bind a subject to a rare token, Textual Inversion (Gal et al., 2023) learns only a
new embedding, and low-rank adaptation (LoRA) (Hu et al., 2022) learns a compact weight delta. These achieve
strong, durable identity, but each requires per-subject optimisation, GPU training time and stored
weights — an awkward fit when the subject or the "look" changes frequently, as it does across an
iterative creative project. The second generation was *encoder-based* and training-free at inference:
IP-Adapter (Ye et al., 2023) injects an image prompt through decoupled cross-attention, and InstantID
(Wang et al., 2024), IP-Adapter FaceID and PhotoMaker (Li et al., 2024) specialise the idea for facial identity
from as little as one reference. This removed per-subject training, but it introduced a second, and
for this project decisive, assumption: every one of these methods needs *access to the model's
internals* — its cross-attention layers, or a ControlNet/adapter hook — that is, an open-weight
checkpoint.

The present system deliberately operates one step removed from all of them, on a *closed* image API
(`gpt-image-1`) exposed only through an image-edit primitive with an `input_fidelity` control
(OpenAI, 2025) and no access to weights, embeddings or attention. None of the methods above can be
applied directly. Identity must instead be pursued through the only levers the API exposes —
reference-image selection and ordering, prompt design, and fidelity control — which is at once the
constraint this dissertation works within (§3.9) and a faithful model of how most applied teams
actually consume generative models today: through a vendor endpoint rather than a checkpoint. The
stronger open-weight methods are therefore positioned as future work rather than omitted. Face
identity is measured here with a face-recognition embedding (Deng et al., 2019); Chapter 4 audits — and partly
rejects — its reliability on a stylised synthetic character.

## 2.3 Structural and pose conditioning

Hard spatial control of diffusion generation is typically obtained with ControlNet (Zhang et al., 2023) or
T2I-Adapter (Mou et al., 2024), which condition on a pose skeleton, depth or edge map. These require a
model that exposes a control interface. A closed image-edit API does not: a skeleton supplied only as
an image reference is a weak, soft signal, which the present work confirms as a negative result
(§3.5.5, §4.12). This motivates the *graded structural conditioning* of Chapter 3, where conditioning
strength is matched to the per-shot reliability of the extracted pose rather than applied uniformly.

## 2.4 Image-to-video and driving-video animation

Image-to-video models animate a still frame into a short clip; commercial systems (used here for
assembly, §3.5) and open models such as Stable Video Diffusion (Blattmann et al., 2023) and AnimateDiff (Guo et al., 2024)
exemplify the class. A related line drives a target appearance with an explicit motion source:
Animate Anyone (Hu et al., 2024) and MagicAnimate (Xu et al., 2024) animate a reference person from a
driving pose sequence, and recent driving-video systems (Wan2.2-Animate, run here via Wan2GP
(Cheng et al., 2025)) replace a performer with a target character while following the driving motion. These
provide much stronger structural control than a single-keyframe image-to-video path, at the cost of
local GPU hardware; the present work probes one such backend as a feasibility extension (Mode C,
§3.10, §4.17) rather than as the main pipeline.

## 2.5 Reference-analysis tooling

The reference-analysis stage composes established tools: content-based shot detection (Castellano, n.d.),
beat and tempo estimation (McFee et al., 2015), 2D pose estimation (Lugaresi et al., 2019; Yang et al., 2023), dense optical flow for a
motion-energy audit (Farnebäck, 2003), and a face-recognition embedding for identity (Deng et al., 2019). The
contribution is not these tools individually — they are deterministic and well established — but their
*synchronisation* into a single beat-aligned storyboard and their use as computed evidence rather
than model guesses (§3.3–3.4). One caveat from this literature is load-bearing for the evaluation:
ArcFace (Deng et al., 2019) is calibrated on real human faces, so its embedding distance is not
well-defined for a synthetic, stylised character. This project treats that as a hypothesis to test
rather than an assumption, and confirms it empirically (§4.8.1) — a deliberately reflective use of the
tooling rather than an uncritical one.

## 2.6 Agentic LLM workflows and evaluation–repair loops

The system is framed as an agentic workflow: tools compute and agents decide. This follows a line of
work on tool-augmented reasoning and self-correction — reasoning-and-acting agents (Yao et al., 2023),
self-refinement (Madaan et al., 2023) and reflexion-style feedback (Shinn et al., 2023) — in which a model inspects the
result of an action and revises. The distinguishing feature here is that the loop is made *auditable*:
rather than an implicit chain of thought, every per-shot decision (scores, verdict, diagnosis, repair
action, whether the retry improved) is written to a readable state file with an explicit
`needs_human` terminal state (§3.7). This makes the "agentic" claim inspectable and turns the decision
log into evaluation data. The present implementation is deliberately reported as a *partially
automated, human-gated* loop (§4.15.1); a fully automatic scoring-driven loop is identified as future
work.

## 2.7 Research gap

Prior work clusters at two poles. One pole trains or fine-tunes generative models for identity or
pose control, which requires GPU-scale training and targets model quality. The other pole performs
uncontrolled end-to-end text-to-video generation with no per-shot handle. Comparatively little work
composes *deterministic reference decomposition* + *IP-conditioned per-shot regeneration* + an
*auditable agentic repair loop* over *closed* generation APIs, and evaluates it under an honest
executed-versus-pending rule. That composition, and its honest evaluation, is the space this
dissertation occupies.
