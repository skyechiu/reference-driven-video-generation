import re
from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# Second layer of the mobile scroll bug: the hero-media height cap added
# earlier was a real improvement but not the full blocker.
#
# The base, unconditional (non-@media) rule:
#   .layout { display:grid; grid-template-columns:var(--sb-w) 1fr;
#             height:calc(100vh - 46px); overflow:hidden; }
# was written for the desktop app-shell layout, where .content is its own
# internally-scrolling pane and .layout intentionally clips at one
# viewport-tall box.
#
# An earlier patch correctly changed `.content` inside
# `@media (max-width:980px)` to flow naturally instead
# (height:auto!important; overflow:visible!important) so the page could
# scroll normally with the sidebar becoming an off-canvas drawer — but the
# *parent* `.layout` was never told to stop clipping. `.layout` still
# carries `overflow:hidden` plus a height fixed to ~one viewport
# (reinforced again, unconditionally, by the later
# `pf-mobile-scroll-and-dark-fix-v1` block's
# `.layout{height:calc(100dvh - 58px)}`), so anything below that first
# viewport-tall slice is clipped and unreachable by any scroll gesture,
# because the clipping box itself never grows and is not itself a scroll
# container (overflow:hidden, not auto/scroll). That's the "can only see
# the cover, nothing below it, scrolling does nothing" symptom.
#
# Fix: inside the same `@media (max-width:980px)` breakpoint the rest of
# the mobile layout system already uses, let `.layout` grow to its natural
# content height and stop clipping. Appended last (after the previous
# hero-media fix block) so it wins decisively over every earlier
# unscoped/desktop `.layout` height+overflow declaration.

anchor = '</style>\n\n\n\n</body>\n</html>'
assert src.count(anchor) == 1, f"anchor count={src.count(anchor)}"

fix_css = (
    '<style id="pf-mobile-layout-clip-fix-v1">\n'
    '/* P0 fix: the base (desktop) .layout rule clips at overflow:hidden with\n'
    '   a fixed ~one-viewport height. .content was already patched for mobile\n'
    '   to flow freely, but .layout — its parent — was never told to stop\n'
    '   clipping, so everything past the first screen was invisible and\n'
    '   unreachable by scrolling. Let .layout grow with its content on\n'
    '   mobile instead of clipping it. */\n'
    '@media (max-width:980px){\n'
    '  .layout{\n'
    '    height:auto!important;\n'
    '    min-height:0!important;\n'
    '    overflow:visible!important;\n'
    '  }\n'
    '}\n'
    '</style>\n\n\n\n</body>\n</html>'
)

src = src.replace(anchor, fix_css, 1)
print("added pf-mobile-layout-clip-fix-v1 (.layout no longer clips content on <=980px viewports)")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
