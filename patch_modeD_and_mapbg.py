from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# FIX A: mute the 4 Mode D hosted-demo comparison videos (Viggle x2,
# wan.video x2). They currently have no `muted` attribute, so opening the
# Mode D page can start playing audio from an unrelated hosted-service demo
# clip.
moded_video_srcs = [
    "/media/run/mode_c_phase0/hosted_comparison_20260805/viggle_gown_video_bg_7s_20260804.mp4",
    "/media/run/mode_c_phase0/hosted_comparison_20260805/viggle_gown_dressingroom_bg_7s_20260804.mp4",
    "/media/run/mode_c_phase0/hosted_comparison_20260805/wan_video_transfer_wan27_gown_4s_20260805.mp4",
    "/media/run/mode_c_phase0/hosted_comparison_20260805/wan_video_transfer_prompted_gown_dressingroom_5s_20260805.mp4",
]
muted_count = 0
for s in moded_video_srcs:
    old = f'<video src="{s}" controls preload="metadata" playsinline></video>'
    new = f'<video src="{s}" controls preload="metadata" playsinline muted></video>'
    n = src.count(old)
    assert n == 1, f"expected 1 match for {s!r}, found {n}"
    src = src.replace(old, new, 1)
    muted_count += 1
print(f"muted {muted_count} Mode D hosted-demo videos")

# FIX B: Mode D "Reference image" card sits on a flat solid near-black
# fill (#251c19) as a fallback while the image itself was 404ing (see FIX C
# in export.py, separately). Swap the flat fill for a quiet dark gradient
# in the same family as the rest of the dark media placeholders on this
# page (not a bright/loud gradient — this box sits behind a photo).
old_visual_bg = '#page-case-mode-d .pf-moded-reference-visual-v97{margin:0;min-width:0;background:#251c19}'
assert src.count(old_visual_bg) == 1
new_visual_bg = (
    '#page-case-mode-d .pf-moded-reference-visual-v97{'
    'margin:0;min-width:0;'
    'background:linear-gradient(160deg,#2c211d 0%,#231a17 46%,#1a1310 100%)'
    '}'
)
src = src.replace(old_visual_bg, new_visual_bg, 1)
print("Mode D reference-image panel: flat #251c19 -> subtle dark gradient")

# FIX C: the Overview "Mode A-D" system map section (pf-overview-system-map /
# pf-map-layer-v69 / pf-map-modes-v69 / pf-map-core-v69 / pf-map-controls-v69)
# was pinned to flat, near-identical light greys with `background-image:
# none!important` by an earlier "restrained palette" pass (v120), producing
# a flat/jarring grey panel inconsistent with the rest of the page. Add a
# later block (wins the cascade at equal specificity/!important by source
# order) that reuses the same warm cream gradient family already used for
# the Overview editorial hero (#FAF9F7 / #F8F7F4 / #F3E8D8), toned down,
# and scoped to light mode only so the separately-tuned dark-mode
# system-map surfaces are untouched.
anchor = '<style id="pf-system-map-palette-v120">'
assert src.count(anchor) == 1
insert_after_this_style_close = True
start = src.index(anchor)
close = src.index("</style>", start) + len("</style>")
gradient_css = (
    '\n\n<style id="pf-map-gradient-refresh-v1">\n'
    '/* Soften the Mode A-D map from flat grey panels to the same quiet warm\n'
    '   gradient family used elsewhere on Overview (light mode only; dark mode\n'
    '   keeps its own tuned flat night surfaces). */\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map{\n'
    '  background:linear-gradient(150deg,#FDFDFC 0%,#F8F8F6 55%,#F3ECE1 100%)!important;\n'
    '}\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map .pf-native-map-section-v69,\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map .pf-native-system-map-v69{\n'
    '  background:transparent!important;\n'
    '  background-image:none!important;\n'
    '}\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map .pf-map-layer-v69{\n'
    '  background:linear-gradient(150deg,#FBFBF9 0%,#F5F5F2 60%,#F1E7DA 100%)!important;\n'
    '  background-image:linear-gradient(150deg,#FBFBF9 0%,#F5F5F2 60%,#F1E7DA 100%)!important;\n'
    '}\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map .pf-map-modes-v69,\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map .pf-map-core-v69{\n'
    '  background:linear-gradient(150deg,#FCFCFB 0%,#F8F8F6 100%)!important;\n'
    '  background-image:linear-gradient(150deg,#FCFCFB 0%,#F8F8F6 100%)!important;\n'
    '}\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map .pf-map-controls-v69{\n'
    '  background:linear-gradient(150deg,#FDFDFC 0%,#F8F8F6 100%)!important;\n'
    '  background-image:linear-gradient(150deg,#FDFDFC 0%,#F8F8F6 100%)!important;\n'
    '}\n'
    'html:not([data-theme="dark"]) .pf-overview-system-map .pf-mode-card-v69{\n'
    '  background:linear-gradient(150deg,#FFFFFF 0%,#FCFBF9 100%)!important;\n'
    '  background-image:linear-gradient(150deg,#FFFFFF 0%,#FCFBF9 100%)!important;\n'
    '}\n'
    '</style>\n'
)
src = src[:close] + gradient_css + src[close:]
print("inserted pf-map-gradient-refresh-v1 (warm gradient override for the Mode A-D map, light mode only)")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
