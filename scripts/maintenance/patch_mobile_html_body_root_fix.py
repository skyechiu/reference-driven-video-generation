import re
from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# Complete root cause of the mobile scroll lock (previous patches fixed
# part of it but not the full chain).
#
# Base (unconditional, not desktop-scoped) rule found at the top of the
# stylesheet:
#     html, body { height: 100%; overflow: hidden }
# This is a deliberate app-shell pattern: html/body never scroll; only
# `.content` (overflow-y:auto) is meant to be the one scrolling pane.
#
# An earlier patch fixed `.content` for mobile to flow freely instead
# (@media max-width:980px: height:auto; overflow:visible), and
# pf-mobile-layout-clip-fix-v1 did the same for `.layout`, its parent. But
# `html`/`body` sit above BOTH of them with `overflow:hidden` always on —
# so regardless of what .layout/.content do, anything taller than one
# viewport was still being clipped by body itself and was completely
# unreachable by any scroll gesture. This is the complete explanation for
# "hero appears, nothing below it, swiping does nothing" on every
# device/mode (not a caching or per-browser quirk).
#
# Fix: on mobile, un-clip html/body so the *document* itself becomes the
# scroll container (the standard, native mobile pattern), matching the
# mobile .content/.layout changes that were already half-applied.
#
# Also adds:
#   1. A small fixed, non-interactive on-page marker
#      (MOBILE_SCROLL_FIX_V3_2026_08_05) so the fix's presence on the live
#      deployed page can be visually confirmed independently.
#   2. A defensive runtime script that strips generic lock/overlay classes
#      in case any exist under a naming convention not covered by the
#      CSS-only audit above (the audit found none of those class names in
#      this codebase — only the real .layout/.content/html/body issue —
#      but this is cheap, harmless insurance).

# ---- 1. the real fix: un-clip html/body on mobile ----
anchor = '</style>\n\n\n\n</body>\n</html>'
assert src.count(anchor) == 1, f"anchor count={src.count(anchor)}"

fix_css = (
    '<style id="pf-mobile-html-body-root-fix-v1">\n'
    '/* P0 root fix: the base `html, body { height:100%; overflow:hidden }`\n'
    '   rule (an app-shell pattern where only .content was meant to scroll)\n'
    '   is unconditional. On mobile, .content/.layout were already patched\n'
    '   to flow freely, but html/body above them were still clipping\n'
    '   everything past one viewport with overflow:hidden, making that\n'
    '   content permanently unreachable by any scroll gesture. Let the\n'
    '   document itself scroll natively on mobile instead. */\n'
    '@media (max-width:980px){\n'
    '  html, body{\n'
    '    height:auto!important;\n'
    '    min-height:100%!important;\n'
    '    overflow-y:auto!important;\n'
    '    overflow-x:hidden!important;\n'
    '    position:relative!important;\n'
    '    -webkit-overflow-scrolling:touch!important;\n'
    '  }\n'
    '  html.no-scroll, body.no-scroll,\n'
    '  html.scroll-locked, body.scroll-locked,\n'
    '  html.modal-open, body.modal-open{\n'
    '    overflow-y:auto!important;\n'
    '    height:auto!important;\n'
    '    position:relative!important;\n'
    '  }\n'
    '  body.nav-open{\n'
    '    overflow-y:hidden!important;\n'
    '  }\n'
    '}\n'
    '</style>\n\n\n\n</body>\n</html>'
)

src = src.replace(anchor, fix_css, 1)
print("added pf-mobile-html-body-root-fix-v1 (html/body no longer clip on <=980px viewports)")

# ---- 2. visible deployment marker + defensive runtime script, right
# after <body ...> so it renders unconditionally and is easy to spot ----
body_anchor = '<body class="pf-refined-v75">'
assert src.count(body_anchor) == 1, f"body anchor count={src.count(body_anchor)}"

marker_and_script = (
    body_anchor + "\n"
    '<div id="mobile-scroll-fix-marker" '
    'style="position:fixed;bottom:6px;right:6px;z-index:2147483647;'
    'background:rgba(20,20,22,.74);color:#fff;'
    'font:600 8px/1.5 -apple-system,BlinkMacSystemFont,sans-serif;'
    'letter-spacing:.02em;padding:3px 7px;border-radius:5px;'
    'pointer-events:none;user-select:none;">'
    'MOBILE_SCROLL_FIX_V3_2026_08_05</div>\n'
    '<script>\n'
    'document.addEventListener("DOMContentLoaded", function () {\n'
    '  var root = document.documentElement, body = document.body;\n'
    '  ["no-scroll", "scroll-locked", "modal-open"].forEach(function (cls) {\n'
    '    root.classList.remove(cls);\n'
    '    if (!body.classList.contains("nav-open")) body.classList.remove(cls);\n'
    '  });\n'
    '});\n'
    '</script>'
)
src = src.replace(body_anchor, marker_and_script, 1)
print("added visible MOBILE_SCROLL_FIX_V3_2026_08_05 marker + defensive runtime lock-class stripper")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
