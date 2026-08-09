import re
from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# Quality/substance pass — three concrete, verified issues fixed below,
# focused on load performance, broken-media handling, and accessibility.

# ── FIX 1: the Mode B "demo_de.mov" video is 180.9MB — by far the largest
# single file on the site — yet was set to preload="auto", which tells the
# browser to start downloading the *entire* file as soon as the page with
# it in the DOM loads (not just metadata). On a media-heavy static site
# this is the single worst first-load-weight offender found in the audit.
old = '<video src="/media/mode-b-assets/demo_de.mov" controls preload="auto" playsinline aria-label="Mode B animated demo; actual video frame'
assert src.count(old) == 1, f"demo_de.mov tag count={src.count(old)}"
src = src.replace(
    '<video src="/media/mode-b-assets/demo_de.mov" controls preload="auto" playsinline',
    '<video src="/media/mode-b-assets/demo_de.mov" controls preload="none" playsinline',
    1,
)
print("demo_de.mov (180.9MB, largest file on the site): preload auto -> none")

# ── FIX 2: openLookRefs() renders look-reference thumbnails with
# onerror="this.style.opacity=0.3" — on a broken/missing image this still
# shows the native broken-image icon, just dimmed. Every other broken-media
# fallback on the site swaps in a text placeholder instead ("Media
# unavailable in static export"); bring this one in line so a missing
# look-reference reads the same as every other missing-media case on the
# site rather than as a rendering bug.
old_onerror = 'onerror="this.style.opacity=0.3"'
assert src.count(old_onerror) == 1, f"onerror count={src.count(old_onerror)}"
new_onerror = (
    "onerror=\"this.outerHTML='<div class=\\'compare-img-ph\\' "
    "style=\\'width:80px;height:110px;display:flex;align-items:center;"
    "justify-content:center;text-align:center;font-size:8px;line-height:1.3;"
    "padding:4px;box-sizing:border-box\\'>Media unavailable in static export</div>'\""
)
src = src.replace(old_onerror, new_onerror, 1)
print("openLookRefs broken-image fallback: dimmed broken-icon -> 'Media unavailable in static export' placeholder")

# ── FIX 3: accessibility — 50 of 153 <img> tags in the exported homepage
# had no alt attribute at all (evidence keyframes, pose/mask audit frames,
# filmstrip crops, thumbnails, etc.). Scope: only *static* <img> tags whose
# src is a fixed string (not a JS template literal like src="${thumb}" —
# those belong to the Mode B look-picker's dynamically-rendered markup and
# would need a per-case JS variable, not a filename, to derive sensible alt
# text from; left alone here rather than guessing). For every static tag
# missing alt, derive a short, meaningful description from its path and
# insert it as a new leading attribute — attribute order doesn't matter to
# HTML parsing, so this is safe regardless of what other attributes
# (style, loading, onerror...) the tag already carries.
IMG_TAG_RE = re.compile(r'<img\b[^>]*>')


def humanize_alt(src_path):
    name = src_path.rsplit('/', 1)[-1]
    name = re.sub(r'\.(png|jpe?g|gif|webp)$', '', name, flags=re.I)
    name = re.sub(r'[_\-]+', ' ', name).strip()
    name = re.sub(r'\bshot (\d+)\b', lambda m: f'Shot {int(m.group(1))}', name, flags=re.I)
    if not name:
        name = 'evidence image'
    return name[0].upper() + name[1:]


SRC_RE = re.compile(r'\bsrc="([^"]*)"')
count = 0
skipped_dynamic = 0


def repl(m):
    global count, skipped_dynamic
    tag = m.group(0)
    if 'alt=' in tag:
        return tag
    src_m = SRC_RE.search(tag)
    if not src_m:
        return tag
    src_val = src_m.group(1)
    if '${' in src_val:
        skipped_dynamic += 1
        return tag
    alt = humanize_alt(src_val)
    count += 1
    return tag.replace('<img ', f'<img alt="{alt}" ', 1)


src = IMG_TAG_RE.sub(repl, src)
print(f"added alt text to {count} static <img> tags; left {skipped_dynamic} JS-template-literal <img> tags untouched")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
