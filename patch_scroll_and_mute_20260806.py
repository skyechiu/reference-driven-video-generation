import re, shutil, datetime

SRC = "pipeline/app.py"
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = f"pipeline/app.py.backup_scroll_mute_{ts}"
shutil.copy2(SRC, backup)
print("backup:", backup)

with open(SRC, "r", encoding="utf-8") as f:
    src = f.read()

orig_len = len(src)

# ---- Fix 1: scroll-to-top-on-page-switch, made instant and robust across
# both the desktop .content scroller and the mobile window/body scroller ----
old_scroll = """  // scroll content pane to top on page switch
  const content = document.querySelector('.content');
  if (content) content.scrollTop = 0;
"""
new_scroll = """  // scroll content pane to top on page switch. On narrow viewports .content
  // switches to overflow:visible (see the max-width:980px layout rules) and
  // window/body becomes the real scrolling element instead, so reset all of
  // them defensively rather than assuming which one is active.
  const content = document.querySelector('.content');
  const resetScroll = () => {
    // .content has its own CSS scroll-behavior:smooth (for in-page anchor
    // links), and the scrollTop *property setter* defers to that same CSS
    // behavior when no explicit option is given - so "content.scrollTop = 0"
    // was quietly animating over several hundred ms instead of jumping,
    // same class of bug as the window-level one below. scrollTo({behavior:
    // 'instant'}) is the only form that reliably bypasses it.
    if (content) content.scrollTo({top: 0, left: 0, behavior: 'instant'});
    window.scrollTo({top: 0, left: 0, behavior: 'instant'});
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  };
  resetScroll();
  // Re-apply a frame later: on narrow viewports the just-closed sidebar
  // transition / late image sizing can nudge the scroll position right
  // after this runs, so one more pass catches that instead of a stale
  // reset getting silently overridden.
  requestAnimationFrame(resetScroll);
"""
count1 = src.count(old_scroll)
assert count1 == 1, f"expected exactly 1 match for scroll fix, found {count1}"
src = src.replace(old_scroll, new_scroll)

# ---- Fix 2: mute all <video> tags ----
def add_muted(m):
    tag = m.group(0)
    if re.search(r'\bmuted\b', tag):
        return tag
    return tag.replace('<video', '<video muted', 1)

src, n_video = re.subn(r'<video\b[^>]*>', add_muted, src)

with open(SRC, "w", encoding="utf-8") as f:
    f.write(src)

new_len = len(src)
print("scroll fix applied:", count1 == 1)
print("video tags processed:", n_video)
print("size before/after:", orig_len, "->", new_len)
