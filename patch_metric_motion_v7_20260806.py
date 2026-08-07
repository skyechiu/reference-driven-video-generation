import shutil, datetime

SRC = "pipeline/app.py"
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = f"pipeline/app.py.backup_metricmotion_v7_{ts}"
shutil.copy2(SRC, backup)
print("backup:", backup)

with open(SRC, "r", encoding="utf-8") as f:
    src = f.read()
orig_len = len(src)

anchor = """  ready(function(){
    wireBorderTrace();
    wireMediaInspect();
    wireRouteHoverPath();
    wireSemanticAliases();
  });
})();
</script>
</body>
</html>"""

assert src.count(anchor) == 1, f"anchor count={src.count(anchor)}"

addition = """  ready(function(){
    wireBorderTrace();
    wireMediaInspect();
    wireRouteHoverPath();
    wireSemanticAliases();
  });
})();
</script>

<style id="pf-metric-motion-v7">
/* ============================================================
   v7 — headline-metric motion. Narrow, additive: the two genuine
   "hero number" components (.pf-stat strong, .pf-metric-value b)
   count up from zero the first time they scroll into view, and the
   four shot values inside the street motion-repair audit settle in
   with a brief per-item stagger instead of appearing all at once.
   Everything else - dense <td> table cells, "01/02/03" step-list
   markers that happen to share the same <strong>/<b> tags, every
   other existing v6/v85/v104 system - is untouched. Both effects are
   opt-in via a JS-added class, so if JS never runs the elements sit
   at their normal, fully-visible default - no flash-of-invisible.
   ============================================================ */
.pf-stat strong,.pf-metric-value b{font-variant-numeric:tabular-nums}
.pf-motion-metrics article.pf-pre-settle-v7{opacity:0;transform:translateY(4px)}
.pf-motion-metrics article.pf-settle-v7{
  opacity:1;transform:none;
  transition:opacity 480ms cubic-bezier(.2,.8,.2,1),transform 480ms cubic-bezier(.2,.8,.2,1);
}
@media(prefers-reduced-motion:reduce){
  .pf-motion-metrics article.pf-pre-settle-v7{opacity:1!important;transform:none!important}
}
</style>

<script id="pf-metric-motion-v7">
(function(){
  "use strict";
  if (window.__pfMetricMotionV7Init) return;
  window.__pfMetricMotionV7Init = true;

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function ready(fn){
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  /* ---- 1. Count-up on genuine headline-metric tiles only. Parses a
     clean "123", "12.3" or "64%" - anything else (arrows, ranges, "9:16
     format", ordinal step markers) is left exactly as written. ---- */
  var COUNT_SELECTOR = ".pf-stat strong, .pf-metric-value b";

  function parseSimple(text){
    var m = /^(\\d+(?:\\.\\d+)?)(%?)$/.exec(text.trim());
    if (!m) return null;
    return {value: parseFloat(m[1]), decimals: (m[1].split(".")[1] || "").length, suffix: m[2]};
  }

  function countUp(el){
    var raw = el.textContent;
    var parsed = parseSimple(raw);
    if (!parsed || reduce) return;
    var start = null, dur = 640;
    function tick(ts){
      if (start === null) start = ts;
      var t = Math.min(1, (ts - start) / dur);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = (parsed.value * eased).toFixed(parsed.decimals) + parsed.suffix;
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = raw;
    }
    requestAnimationFrame(tick);
  }

  /* ---- 2. Motion-metric stagger: settle the four shot values in one
     at a time rather than as a single flat block. ---- */
  function wireSettle(){
    if (reduce || !("IntersectionObserver" in window)) return;
    var rows = document.querySelectorAll(".pf-motion-metrics");
    if (!rows.length) return;
    rows.forEach(function(row){
      Array.prototype.forEach.call(row.children, function(child){ child.classList.add("pf-pre-settle-v7"); });
    });
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (!e.isIntersecting) return;
        var row = e.target;
        Array.prototype.forEach.call(row.children, function(child, idx){
          child.style.transitionDelay = (idx * 70) + "ms";
          child.classList.remove("pf-pre-settle-v7");
          child.classList.add("pf-settle-v7");
        });
        io.unobserve(row);
      });
    }, {threshold: .35});
    rows.forEach(function(row){ io.observe(row); });
  }

  function wireCountUp(){
    var targets = document.querySelectorAll(COUNT_SELECTOR);
    if (!targets.length || !("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting){ countUp(e.target); io.unobserve(e.target); }
      });
    }, {threshold: .6});
    targets.forEach(function(t){ io.observe(t); });
  }

  ready(function(){
    wireCountUp();
    wireSettle();
  });
})();
</script>
</body>
</html>"""

src = src.replace(anchor, addition, 1)

with open(SRC, "w", encoding="utf-8") as f:
    f.write(src)

print("size:", orig_len, "->", len(src))
print("added pf-metric-motion-v7 (count-up + motion-metrics stagger)")
