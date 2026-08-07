# Chapter 6 — Conclusion and Future Work

## 6.1 Summary

This dissertation set out to determine whether a reference short-form video can be decomposed into a
reusable structural template and regenerated with a fixed IP character, under both scene preservation
and scene replacement, using an agentic evaluation–repair loop built only on closed generation APIs.
A four-stage pipeline was designed and built to do this: deterministic reference analysis, a
five-track beat-aligned storyboard, IP-conditioned keyframe-first per-shot regeneration with
identity, look and scene separated, and an agentic evaluation–repair loop that repairs only the
failed shot and logs every decision. The pipeline was demonstrated end to end on a four-shot beach
reference under human review, with a decision log providing real evidence of self-correcting
generation, and was exercised again under scene replacement into a Parisian street scene.

## 6.2 What the evaluation showed

Reported under an executed-versus-pending rule, the executed results include a complete end-to-end
run (four keyframes generated and human-approved across eight logged attempts, assembled into a
768×1152, 20.4 s vertical short); a log-reconstructed loop-off-versus-loop-on comparison in which
first-attempt acceptance rose from 25% to 100% under gated repair; a motion-energy audit quantifying
that single-keyframe animation reproduces 14–64% of the reference's per-frame motion, improved on the
two weakest shots by a prompt-only repair; and an identity-metric audit. The identity audit is the
most instructive result: a face-embedding distance under-scored keyframes that human review accepted
as the same synthetic character, empirically confirming that a single embedding distance is
mis-calibrated for a stylised IP identity and justifying the decision to gate acceptance on human
review rather than one metric. A Phase 0 driving-video backend (Mode C) was shown to run on available
hardware and to follow driving motion while preserving the background, confirming the reference-role
boundary argued throughout (driving supplies motion and body; reference supplies appearance).

## 6.3 Reflection: negative results as findings

Two negative results are reported as engineering contributions rather than hidden. First, a pose
skeleton supplied only as an image reference is too weak a control signal for the closed image-edit
API, so the start/end-keyframe pose branch was tested and archived; reliable pose control requires a
pose-conditioned backend. Second, single-keyframe image-to-video under-conditions the temporal
sequence, since only the start frame is controlled. Both are direct evidence for *why* an explicit
orchestration and repair layer is needed rather than a direct API call, and, unlike a hosted
interface, the pipeline's behaviour is recorded, evaluable and reproducible.

## 6.4 Limitations

The limitations are stated in full in §4.15 and are not repeated here beyond their headline: the loop
that operated was human-gated rather than fully automatic; the evaluation rests on one reference video
and one character; there is no equal-budget baseline; automated framing and beat-alignment scores
remain uncomputed; and pixel-level output is bound to specific closed-model versions. These bound the
claim to a proof of concept.

## 6.5 Future work

Several extensions follow directly from the limitations. (1) *Complete the automated metrics*:
framing-accuracy and beat-alignment scores are computable at zero cost from the already-logged cut and
beat timestamps, closing the last pending cells. (2) *Close the automatic loop*: replace the human
gate with automatic scoring→diagnosis→targeted repair, and run the controlled loop-off-versus-loop-on
ablation with a matched attempt budget and a blind reviewer (§4.12). (3) *Stronger identity*: adopt
IP-Adapter FaceID, InstantID or a trained LoRA to reduce identity drift beyond what reference-image
ordering achieves on a closed API. (4) *Stronger structural control*: move per-shot generation onto a
pose-conditioned backend (ControlNet-style or a driving-video model), which the negative results
identify as the route to reliable motion. (5) *Mode C to completion*: full-length driving-video
generation and the scene-regenerating Condition B. (6) *Generalisation and a user study*: multiple
characters, scenes and reference clips, evaluated with independent raters against matched baselines.

## 6.6 Closing

The system is best understood as a proof of concept for auditable, reference-structured and
selectively-repairable short-form video generation, not a system for exact motion transfer or
autonomous cinematic production. Its contribution is an orchestration layer — deterministic reference
decomposition, identity/look/scene-separated per-shot regeneration, and an auditable agentic repair
loop with a decision log — reported with an honest account, negative results included, of where it
works and where it does not.
