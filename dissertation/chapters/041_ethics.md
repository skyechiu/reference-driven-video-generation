# Chapter 5 — Professional and Ethical Considerations

This chapter sets out the professional and ethical considerations that shaped the system's design
and evaluation. Several are not incidental to the project but central to it: a system that
regenerates video with a fixed character, and — in Mode C — replaces a filmed performer with a
target character, sits close to well-known copyright and synthetic-media concerns, and the design
choices in Chapters 3–4 were made partly to keep the work on the right side of those lines.

## 5.1 Copyright and the extract-structure principle

The system is built on a single copyright-aware principle: **extract structure, regenerate content**
(§3.8). Reference clips are analysed only for *formal structure* — shot boundaries, cut rhythm,
framing, a broad camera-motion class, body orientation and beat timing — and none of the reference's
pixels appear in the output. Reference audio is used solely to derive a beat grid and is never
reproduced. The generated output uses an original, project-owned IP character, new scene prompts and
royalty-free or self-created assets. Reference material is authorised, self-created or royalty-free.

This distinction matters because structure and expression are treated differently under copyright: a
shot rhythm or a generic "walk toward the sunset" is closer to an unprotectable idea, whereas the
literal footage is protected expression. The pipeline is deliberately confined to the former. This is
stated in the dissertation as **risk reduction, not a legal guarantee** (§4.15.1): a highly
distinctive sequence of shots could still carry protectable selection-and-arrangement, character
reference images must be owned or licensed, and the training data of the closed third-party models is
not transparent. Where doubt exists, the safe reading is that the system reuses *generic* structure,
not a specific creative arrangement.

## 5.2 Synthetic media, likeness and person replacement

Person-replacement generation is adjacent to the misuse space commonly labelled "deepfakes". The
project addresses this directly rather than by omission.

First, the target character is a **fictional, project-owned IP identity**, not a real, named person.
The system is not designed to impersonate a real individual, and the identity references are original
assets. Second, in Mode C the *driving* performance video does contain a real person (a consenting
volunteer performing simple movements); that person's face is **pixelated/anonymised in every figure**
in this dissertation (e.g. Figures 3.9 and 4.3), and the driving video supplies motion and body
silhouette only — not the performer's identity, which is replaced. Third, the honest finding that the
system's identity control is *imperfect* on a closed API (identity is "similar, not exact", §4.12,
§4.17) is, in this context, a safety-relevant property rather than only a limitation: the system does
not produce a convincing likeness of any specific real person.

The responsible-use position is therefore explicit: the appropriate applications are creator-owned
character content and previsualisation, not the non-consensual replacement or impersonation of real
people. A production version should add provenance signalling (for example, content credentials or
visible synthetic-media labelling) and a consent record for any driving performer. These are noted as
requirements for any deployment beyond this proof of concept.

## 5.3 Data and consent

The project uses no personal or sensitive datasets. The materials are: original IP character
references, self-created or royalty-free reference clips, a static scene-asset package, and a short
driving performance recorded with the performer's consent for this use. No third-party personal data
is collected, stored or processed, and no human-subject study was run — the evaluation's "human
review" is author-conducted inspection (§4.15.2), which is disclosed as such rather than presented as
an independent user study.

## 5.4 Honesty, reproducibility and professional practice

A professional-practice commitment runs through the evaluation: an **executed-versus-pending**
reporting rule under which no metric is invented, every number is traceable to an execution log,
`ffprobe`, an optical-flow or ArcFace computation, or the decision log, and results the system did not
produce are labelled pending rather than filled in. Negative results (the archived skeleton-guidance
branch, §4.12; the residual motion gap, §4.13) are reported as findings, not hidden. This discipline
is itself an ethical stance: it prevents the over-claiming that is common around generative-AI
demonstrations and keeps the contribution defensible.

Two further professional considerations follow. The pipeline keeps a **human in the loop** at
acceptance (§4.15.1): generation is gated on human review rather than delegated wholly to an automatic
metric that the identity audit (§4.8.1) shows can misjudge a synthetic character. And the system is
built for **auditability** — every per-shot decision is written to a readable state file with an
explicit `needs_human` terminal state — so that its behaviour can be inspected and reproduced rather
than trusted blindly.

## 5.5 Environmental and cost considerations

The system performs no model training; it composes closed inference APIs and local CPU analysis. Its
compute footprint is therefore modest and dominated by a small number of image- and video-generation
API calls per shot, plus zero-cost local analysis (segmentation, pose, optical flow, ArcFace). The
agentic repair loop increases the number of generation calls, which is both a cost and an
environmental consideration; the dissertation reports attempt counts (eight generations for four
approved shots, §4.4) precisely so that this cost is visible rather than hidden, and identifies an
equal-budget baseline as necessary future work (§4.15.2).
