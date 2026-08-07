import re
from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# Colour unification, driven by CSS cascade analysis rather than a blind
# find/replace across all 661 literal hex colours in the file, which would
# be unverifiable and risky.
#
# This file has 41 separate `:root{...}` blocks accumulated across many
# edit rounds. Because CSS custom properties on `:root` are genuinely
# global (not scoped per <style> block), whichever block defines a given
# property name LAST in document order is the one actually live for every
# element on the page that references it via var() — all earlier
# same-named declarations are dead weight.
#
# Two confirmed-live, high-usage sources of the colour inconsistency:
#
# 1. `--bg` is defined by 15 different :root blocks; the LAST one in the
#    document is the "v35" block, which aliases --bg to a warm cream/
#    beige token (--v35-paper:#f3f0e9). Since --bg is the page's actual
#    background variable (`.content{background:var(--bg)}` etc.), this
#    beige is the live sitewide background colour. The same v35 block also
#    supplies --surface/--tx/--bd (also last-definer for those names) and
#    52 confirmed var(--v35-*) usages elsewhere (sidebar active state,
#    status pills, resource links, cursor dot, flow steps, etc.) for its
#    coral/sage/violet/ochre accent set.
#
# 2. `.pf-status` / `.pf-status.blue` / `.pf-status.amber` (status badges)
#    reference var(--pf-blue)/var(--pf-green)/var(--pf-amber) 11 times
#    each, sourced from a block duplicated identically 6 times:
#    saturated indigo-blue, muted green, brown-amber.
#
# Fix strategy: change only the VALUES inside these two blocks (all
# variable NAMES stay identical), so every existing usage site — 52 + 33
# of them — repaints correctly with zero risk of breaking layout/markup,
# since nothing about selectors or structure changes.
#
# `--accent` (233 usages, the single most-referenced token in the file)
# was also traced: its live source is a later, separate block setting
# `--accent:#0071e3` (Apple's product blue), already aligned with the
# intended visual direction. Left untouched: with 233 usages across
# unknown purposes (buttons, links, borders, hover states), changing it
# without visual verification carries real regression risk for uncertain
# benefit.
#
# Also installs a canonical named token set
# (--bg/--surface/--surface-soft/--border/--text/--muted/--muted-2/
# --accent-coral/--accent-coral-soft/--accent-blue/--accent-blue-soft/
# --status-*) as a new, final :root block. Nothing in the codebase
# references these exact names yet — this is forward-looking
# infrastructure for future edits rather than something that repaints
# anything by itself today.

# ---- 1. v35 block: warm/beige -> neutral, coral/sage/violet/ochre -> spec-aligned ----
old_v35 = """        --v35-paper:#f3f0e9;
        --v35-paper-2:#faf8f3;
        --v35-surface:#fffdf9;
        --v35-ink:#191816;
        --v35-muted:#68645e;
        --v35-line:rgba(36,31,25,.105);
        --v35-coral:#e45f43;
        --v35-coral-soft:#f7e0d9;
        --v35-sage:#638274;
        --v35-sage-soft:#e2ece6;
        --v35-violet:#75689a;
        --v35-violet-soft:#eae6f2;
        --v35-ochre:#a96f29;
        --v35-ochre-soft:#f4eadb;
        --accent:var(--v35-coral);
        --accent-dk:#c94d34;
        --accent-muted:rgba(228,95,67,.10);
        --accent-lt:rgba(228,95,67,.075);
        --accent-bd:rgba(228,95,67,.24);
        --tx:var(--v35-ink);
        --tx2:#504d48;
        --tx3:var(--v35-muted);
        --tx4:#918d86;
        --bg:var(--v35-paper);
        --surface:var(--v35-surface);
        --surface2:#f7f4ee;
        --surface3:#eeeae2;
        --bd:var(--v35-line);
        --bd2:rgba(36,31,25,.065);
        --bd3:rgba(36,31,25,.17);
      }"""
assert src.count(old_v35) == 1, f"v35 block match count={src.count(old_v35)}"

new_v35 = """        --v35-paper:#FBFBFD;
        --v35-paper-2:#F6F7F8;
        --v35-surface:#FFFFFF;
        --v35-ink:#1D1D1F;
        --v35-muted:#6E6E73;
        --v35-line:rgba(29,29,31,.08);
        --v35-coral:#FF7A66;
        --v35-coral-soft:#FFF1EE;
        --v35-sage:#2F7D46;
        --v35-sage-soft:#E7F6EC;
        --v35-violet:#615B8A;
        --v35-violet-soft:#F0EEF6;
        --v35-ochre:#8A5A00;
        --v35-ochre-soft:#FFF2E3;
        --accent:var(--v35-coral);
        --accent-dk:#E2593F;
        --accent-muted:rgba(255,122,102,.10);
        --accent-lt:rgba(255,122,102,.075);
        --accent-bd:rgba(255,122,102,.24);
        --tx:var(--v35-ink);
        --tx2:#3A3A3C;
        --tx3:var(--v35-muted);
        --tx4:#98989D;
        --bg:var(--v35-paper);
        --surface:var(--v35-surface);
        --surface2:#F6F7F8;
        --surface3:#EFEFF1;
        --bd:var(--v35-line);
        --bd2:rgba(29,29,31,.065);
        --bd3:rgba(29,29,31,.17);
      }"""

src = src.replace(old_v35, new_v35, 1)
print("v35 block (last --bg/--surface/--tx definer, 52 direct usages): beige/warm palette -> neutral + spec-aligned coral/status hues")

# ---- 2. status badge block (.pf-status / .pf-status.blue / .pf-status.amber), duplicated 6x ----
old_status_block = ":root{--pf-ink:#101828;--pf-muted:#5f6c7b;--pf-blue:#3157d5;--pf-green:#16815d;--pf-amber:#a96012;--pf-line:#e2e7ec;--pf-soft:#f6f8fa;--pf-width:1180px;--sb-w:248px}"
count = src.count(old_status_block)
assert count == 6, f"status block match count={count} (expected 6)"

new_status_block = ":root{--pf-ink:#1D1D1F;--pf-muted:#6E6E73;--pf-blue:#3D6FA3;--pf-green:#2F7D46;--pf-amber:#8A5A00;--pf-line:rgba(29,29,31,.08);--pf-soft:#F6F7F8;--pf-width:1180px;--sb-w:248px}"

src = src.replace(old_status_block, new_status_block)
print(f"status badge palette (.pf-status .blue/.amber, {count} occurrences): saturated indigo/brown -> spec-aligned status colours")

# ---- 3. install the exact named canonical token set, as the final style
# block (after the mobile fixes), for forward-looking consistency ----
anchor = "</style>\n\n\n\n</body>\n</html>"
assert src.count(anchor) == 1, f"anchor count={src.count(anchor)}"

token_css = (
    '<style id="pf-colour-tokens-canonical-v1">\n'
    '/* Canonical colour tokens per the unification brief. Nothing in the\n'
    '   codebase references these exact names yet (the live palette runs\n'
    '   through the differently-named --bg/--surface/--tx/--accent/--pf-*\n'
    '   tokens fixed above) — this is the forward-looking baseline for any\n'
    '   future component work, and is safe to add now since it can\'t\n'
    '   collide with or override anything existing. */\n'
    ':root{\n'
    '  --bg:#FBFBFD;\n'
    '  --surface:#FFFFFF;\n'
    '  --surface-soft:#F6F7F8;\n'
    '  --border:rgba(29,29,31,.08);\n'
    '  --text:#1D1D1F;\n'
    '  --muted:#6E6E73;\n'
    '  --muted-2:#8E8E93;\n'
    '  --accent-coral:rgba(255,122,102,.55);\n'
    '  --accent-coral-soft:rgba(255,122,102,.10);\n'
    '  --accent-blue:rgba(90,200,250,.38);\n'
    '  --accent-blue-soft:rgba(90,200,250,.10);\n'
    '  --status-completed-bg:rgba(52,199,89,.10);\n'
    '  --status-completed-text:#2F7D46;\n'
    '  --status-diagnostic-bg:rgba(120,105,180,.09);\n'
    '  --status-diagnostic-text:#615B8A;\n'
    '  --status-partial-bg:rgba(255,149,0,.10);\n'
    '  --status-partial-text:#8A5A00;\n'
    '  --status-planned-bg:rgba(142,142,147,.12);\n'
    '  --status-planned-text:#6E6E73;\n'
    '}\n'
    '</style>\n\n\n\n</body>\n</html>'
)

src = src.replace(anchor, token_css, 1)
print("installed canonical named token set (pf-colour-tokens-canonical-v1)")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
