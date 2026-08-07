import re
from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# Mobile bug fix: a large near-solid-dark rectangle fills most of the
# viewport below the hero title/subtitle on mobile Safari, reading as
# broken/blocked scrolling even though the page is not actually locked.
#
# Root cause found by auditing every accumulated `.pf-hero-media` /
# `.pf-hero-poster` / `.pf-hero-poster img` CSS rule (15+ of them, written
# across many earlier edit rounds, several with `!important`, none scoped
# with a mobile-appropriate cap): min-height values ranging from 400px up
# to 680px, with backgrounds of #111 / #0b0b0c / #e9e9ed and a
# `linear-gradient(180deg,rgba(0,0,0,.04) 35%,rgba(0,0,0,.48) 100%)`
# darkening overlay meant for desktop-sized hero art. On a ~390px-wide
# phone viewport (~700-850px tall), a 600-680px-tall dark hero block
# dominates virtually the entire screen below the fold, and while its
# poster image is loading (or on a slow connection) it reads as a solid
# dark block that doesn't visibly change while swiping.
#
# Not a `position:fixed` overlay (.sidebar-backdrop, .pf-lightbox, .modal,
# cursor rings are all correctly hidden by default in the exported HTML) —
# it's an ordinary in-flow element that's simply too tall on narrow
# viewports because no responsive cap was ever added.
#
# Fix: append ONE decisive, mobile-scoped override as the very last rule
# in the very last <style> block, so it wins the cascade over every prior
# conflicting min-height/height declaration (including the !important
# ones) regardless of which one would otherwise apply. Caps the hero
# media block to a sane aspect-ratio-driven size on narrow viewports
# instead of a fixed min-height in the hundreds of px.

anchor = "</style>\n\n\n\n</body>\n</html>"
assert src.count(anchor) == 1, f"anchor count={src.count(anchor)}"

fix_css = (
    "<style id=\"pf-mobile-hero-media-scroll-fix-v1\">\n"
    "/* P0 fix: on narrow viewports, every prior .pf-hero-media/.pf-hero-poster\n"
    "   min-height rule (400-680px, several !important) combined to produce a\n"
    "   hero image block taller than the viewport itself, which read as a\n"
    "   stuck dark screen while its poster image loaded. Cap it decisively. */\n"
    "@media (max-width:640px){\n"
    "  .pf-hero-media{\n"
    "    min-height:0!important;\n"
    "    height:auto!important;\n"
    "    max-height:56vh!important;\n"
    "    aspect-ratio:4/5!important;\n"
    "  }\n"
    "  .pf-hero-poster{\n"
    "    min-height:0!important;\n"
    "    height:100%!important;\n"
    "    max-height:56vh!important;\n"
    "  }\n"
    "  .pf-hero-poster img{\n"
    "    min-height:0!important;\n"
    "    max-height:56vh!important;\n"
    "    height:100%!important;\n"
    "  }\n"
    "}\n"
    "</style>\n\n\n\n</body>\n</html>"
)

src = src.replace(anchor, fix_css, 1)
print("added pf-mobile-hero-media-scroll-fix-v1 (caps oversized hero media block to 56vh on <=640px viewports)")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
