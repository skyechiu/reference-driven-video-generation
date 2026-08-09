import re
from pathlib import Path

APP = Path("pipeline/app.py")
src = APP.read_text(encoding="utf-8")
orig_len = len(src)

# V4: the V3 on-page marker is confirmed visible on live iPhone Safari, so
# deployment/caching is ruled out, but scrolling still doesn't work.
# huggingface.co/spaces/... wraps a Space in an iframe, so the fix needs to
# work for this document's own internal scrolling regardless of what the
# outer HF wrapper page does, since the iframe (if any) has its own
# independent scrolling context. The open question is which element inside
# this document is actually the tall one that needs to scroll, and whether
# it's currently doing so.
#
# DOM check done first: `.layout` is a direct child of <body> (right
# after the topbar) with no other undiscovered fixed-height wrapper in
# between — ruling out an extra hidden shell.
#
# Rather than guess again, add a live on-page readout of the real layout
# numbers (viewport height, .layout height, computed overflow, scroll
# position), replacing the V3 marker.

body_anchor_old = '''<body class="pf-refined-v75">
<div id="mobile-scroll-fix-marker" style="position:fixed;bottom:6px;right:6px;z-index:2147483647;background:rgba(20,20,22,.74);color:#fff;font:600 8px/1.5 -apple-system,BlinkMacSystemFont,sans-serif;letter-spacing:.02em;padding:3px 7px;border-radius:5px;pointer-events:none;user-select:none;">MOBILE_SCROLL_FIX_V3_2026_08_05</div>
<script>
document.addEventListener("DOMContentLoaded", function () {
  var root = document.documentElement, body = document.body;
  ["no-scroll", "scroll-locked", "modal-open"].forEach(function (cls) {
    root.classList.remove(cls);
    if (!body.classList.contains("nav-open")) body.classList.remove(cls);
  });
});
</script>'''
assert src.count(body_anchor_old) == 1, f"body anchor count={src.count(body_anchor_old)}"

body_anchor_new = '''<body class="pf-refined-v75">
<div id="mobile-scroll-fix-marker" style="position:fixed;bottom:6px;right:6px;z-index:2147483647;max-width:78vw;background:rgba(20,20,22,.86);color:#fff;font:600 8px/1.45 -apple-system,BlinkMacSystemFont,monospace;letter-spacing:.01em;padding:5px 8px;border-radius:6px;pointer-events:none;user-select:none;white-space:pre-wrap;">MOBILE_SCROLL_FIX_V4_2026_08_05</div>
<script>
document.addEventListener("DOMContentLoaded", function () {
  var root = document.documentElement, body = document.body;
  ["no-scroll", "scroll-locked", "modal-open"].forEach(function (cls) {
    root.classList.remove(cls);
    if (!body.classList.contains("nav-open")) root.classList.remove(cls);
  });

  function readout() {
    var se = document.scrollingElement || document.documentElement;
    var content = document.querySelector(".content");
    var layout = document.querySelector(".layout");
    var lines = ["MOBILE_SCROLL_FIX_V4_2026_08_05"];
    lines.push("BODY " + se.scrollHeight + "/" + se.clientHeight);
    if (content) {
      lines.push("CONTENT " + content.scrollHeight + "/" + content.clientHeight +
        " ov=" + getComputedStyle(content).overflowY);
    } else {
      lines.push("CONTENT not found");
    }
    if (layout) {
      lines.push("LAYOUT " + layout.scrollHeight + "/" + layout.clientHeight +
        " ov=" + getComputedStyle(layout).overflowY);
    }
    lines.push("html ov=" + getComputedStyle(root).overflowY +
      " body ov=" + getComputedStyle(body).overflowY);
    lines.push("win=" + window.innerWidth + "x" + window.innerHeight);
    var marker = document.getElementById("mobile-scroll-fix-marker");
    if (marker) marker.textContent = lines.join("\\n");
  }
  readout();
  window.addEventListener("resize", readout);
  window.addEventListener("orientationchange", readout);
  setTimeout(readout, 800);
  setTimeout(readout, 2000);
});
</script>'''

src = src.replace(body_anchor_old, body_anchor_new, 1)
print("replaced V3 marker with V4 live diagnostic readout (BODY/CONTENT/LAYOUT scrollHeight vs clientHeight + computed overflow-y)")

APP.write_text(src, encoding="utf-8")
print(f"app.py: {orig_len} -> {len(src)} chars")
