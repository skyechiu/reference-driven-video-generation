import re
from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# Fixes over-tight letter-spacing on large English headings (Mode A / Mode B
# hero h1s), where negative tracking makes characters visibly crowd/overlap.
#
# Root cause: many page-scoped, mutually-duplicated CSS blocks throughout
# this file each set their own h1{...letter-spacing:...} rule, ranging from
# -.035em up to -.07em, several with !important. At the huge clamp() display
# sizes used for these h1s (54-112px), a value like -.065em is ~5-6px of
# negative tracking *per character*.
#
# Implementation note: running the h1-matching regex over the *entire*
# 1.7MB app.py source (including large non-CSS JSON/JS/HTML stretches with
# long runs containing no "{"/"}" at all) triggers catastrophic backtracking
# in the `[^{}]*?` selector-prefix group and hangs indefinitely. Fixed by
# first slicing out just the <style>...</style> blocks (a much smaller,
# brace-dense text where the same regex is safe and fast) and only running
# the substitution on that.

# ---- 1. Locate every <style ...>...</style> block with plain string scans
# (no regex over the whole file) ----
style_spans = []  # (start_of_open_tag, end_of_close_tag, inner_start, inner_end)
pos = 0
while True:
    open_start = src.find("<style", pos)
    if open_start == -1:
        break
    open_tag_end = src.find(">", open_start)
    assert open_tag_end != -1, f"unterminated <style tag at {open_start}"
    inner_start = open_tag_end + 1
    close_start = src.find("</style>", inner_start)
    assert close_start != -1, f"no matching </style> for <style at {open_start}"
    close_end = close_start + len("</style>")
    style_spans.append((open_start, close_end, inner_start, close_start))
    pos = close_end

print(f"found {len(style_spans)} <style> blocks")
total_css_chars = sum(e - s for (_, _, s, e) in style_spans)
print(f"total CSS content: {total_css_chars} chars (vs {orig_len} total file)")

# ---- 2. Run the h1-letter-spacing softening only within each block's inner
# CSS text (dense with braces -> regex is fast and safe here) ----
rule_re = re.compile(r'([^{}]*?\bh1\b[^{}]*)\{([^{}]*)\}')


def is_heading_selector(selector):
    parts = [p.strip() for p in selector.split(',')]
    return bool(parts) and all(re.search(r'(^|[\s>+~])h1$', p) for p in parts)


LS_RE = re.compile(r'letter-spacing:-\.(\d+)em(!important)?')

count_rules = 0
count_props = 0
seen_values = []


def soften(m):
    global count_props
    digits = m.group(1)
    important = m.group(2) or ''
    val = float('-.' + digits)
    new_val = max(val * 0.34, -0.028)
    count_props += 1
    seen_values.append((val, new_val))
    return f'letter-spacing:{new_val:.3f}em{important}'


def repl_rule(m):
    global count_rules
    selector, body = m.group(1), m.group(2)
    if not is_heading_selector(selector):
        return m.group(0)
    new_body, n = LS_RE.subn(soften, body)
    if n:
        count_rules += 1
        return selector + '{' + new_body + '}'
    return m.group(0)


# ---- 3. Rebuild the file: walk style blocks in order, patch each inner
# text, splice back into the untouched surrounding source ----
out_parts = []
cursor = 0
for (_, _, inner_start, inner_end) in style_spans:
    out_parts.append(src[cursor:inner_start])
    inner = src[inner_start:inner_end]
    new_inner = rule_re.sub(repl_rule, inner)
    out_parts.append(new_inner)
    cursor = inner_end
out_parts.append(src[cursor:])
new_src = "".join(out_parts)

print(f"h1 rules touched: {count_rules}")
print(f"letter-spacing properties softened: {count_props}")
for old, new in seen_values:
    print(f"  {old:+.3f}em -> {new:+.3f}em")

assert count_props >= 10, f"expected to touch a good number of rules, only found {count_props} — investigate before writing"

APP.write_text(new_src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(new_src)} chars")
