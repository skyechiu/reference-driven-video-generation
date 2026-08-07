from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# Two small, targeted interaction refinements on top of the existing
# interaction system (scripts/styles tagged v85 through v122+), which
# already covers: line-draw section reveals + staggered card entry
# (pf-line-interaction-v104's setupSections), scroll-driven stage lighting
# (setupStages / pf-story-stage-v85), creative per-content-type hover
# (setupCards/addTrace border-trace, setupMedia glass-label overlay),
# editorial sidebar rail (pf-sidebar-editorial-rail-v107), Mode A-D map
# relational hover (setupModeMap, with the shared-core dimming already
# fixed at line ~3395's opacity:.92!important override), repair
# decision-chain hover (setupRepair/pf-chain-trace-v104), a before/after
# with 14->51%/19->47% evidence markers on the repair page, refined media
# reveal, and an accessible status-tooltip system (setupStatuses) — all
# using the same easing curve (cubic-bezier(.2,.8,.2,1)) and timing bands
# (180ms hover / 520ms reveal), plus full prefers-reduced-motion / touch /
# focus-visible handling.
#
# Given that coverage, this patch makes two small, precise, additive
# refinements rather than rebuilding anything (rebuilding risks duplicate
# or conflicting interaction systems coexisting on the same elements).

# ── FIX 1: status-tooltip wording — "PLANNED" currently shares one merged
# message with "DESIGNED"/"NOT FULLY EXECUTED" ("Architecture or extension
# exists conceptually but was not completed as evidence"). PLANNED should
# read as its own, blunter category ("not implemented") distinct from
# "DESIGNED / PARTIALLY TESTED" (design exists but incomplete). Split it
# into its own line so a "PLANNED EXTENSION" badge (e.g. Mode D) reads
# more precisely than a "DESIGNED" one (e.g. Mode A-2).
old_status_line = (
    "    [/DESIGNED|NOT FULLY EXECUTED|PLANNED/,'Architecture or extension exists conceptually but was not completed as evidence.'],\n"
)
assert src.count(old_status_line) == 1, f"status line count={src.count(old_status_line)}"
new_status_lines = (
    "    [/PLANNED/,'Not implemented. Architecture or extension exists conceptually only.'],\n"
    "    [/DESIGNED|NOT FULLY EXECUTED/,'Design exists but was not fully completed as evidence.'],\n"
)
src = src.replace(old_status_line, new_status_lines, 1)
print("status-tooltip wording: split PLANNED from DESIGNED/NOT FULLY EXECUTED into two distinct messages")

# ── FIX 2: a small "scan" accent riding the tip of each section's eyebrow
# line as it draws in on scroll — literally a point of light traveling
# along the line, reinforcing the "revealed like a scan" read the spec
# asks for (vs. a plain fade), without touching layout, without adding a
# second competing reveal system, and fully covered by the same
# prefers-reduced-motion / touch guards the rest of pf-line-interaction-
# style-v104 already uses for this exact class.
anchor = '<style id="pf-map-gradient-refresh-v1">'
assert src.count(anchor) == 1
scan_css = (
    '<style id="pf-section-scan-accent-v1">\n'
    '/* A point of light riding the tip of the eyebrow line as it draws in\n'
    '   on scroll (pf-line-interaction-v104 already animates the line itself\n'
    '   via transform:scaleX on .is-section-visible-v104; this only adds a\n'
    '   decorative marker to the same element, no new observer/class). */\n'
    'html.pf-line-motion-v104 .pf-section-line-v104{position:relative}\n'
    'html.pf-line-motion-v104 .pf-section-line-v104::after{\n'
    '  content:"";position:absolute;right:-1.5px;top:50%;width:3px;height:3px;\n'
    '  margin-top:-1.5px;border-radius:50%;\n'
    '  background:var(--pf-v104-coral,rgba(255,112,88,.7));\n'
    '  box-shadow:0 0 4px 0 rgba(255,112,88,.5);\n'
    '  opacity:0;\n'
    '}\n'
    'html.pf-line-motion-v104 .pf-line-section-v104.is-section-visible-v104 .pf-section-line-v104::after{\n'
    '  animation:pfScanDotV1 460ms cubic-bezier(.2,.8,.2,1) both;\n'
    '}\n'
    '@keyframes pfScanDotV1{\n'
    '  0%{opacity:0}\n'
    '  10%{opacity:1}\n'
    '  85%{opacity:1}\n'
    '  100%{opacity:0}\n'
    '}\n'
    '@media(prefers-reduced-motion:reduce){\n'
    '  html.pf-line-motion-v104 .pf-section-line-v104::after{display:none!important}\n'
    '}\n'
    '</style>\n\n'
)
src = src.replace(anchor, scan_css + anchor, 1)
print("added pf-section-scan-accent-v1 (traveling point-of-light on eyebrow line reveal)")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
