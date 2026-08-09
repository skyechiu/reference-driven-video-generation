import sys, os, re, json, shutil, mimetypes, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(".").resolve()
sys.path.insert(0, str(ROOT / "_export_tmp" / "vendor2_ready_v2" / "vendor2_ready"))
sys.path.insert(0, str(ROOT / "pipeline"))
os.environ.setdefault("ONLINE_DEMO_READ_ONLY", "1")

import app as pipeline_app

client = pipeline_app.app.test_client()

OUT = ROOT / "outputs" / "huggingface_static_site"
ASSETS = OUT / "assets"
PAGES = OUT / "pages"

# ---------------------------------------------------------------------------
# 1. Fetch homepage
# ---------------------------------------------------------------------------
r = client.get("/")
assert r.status_code == 200, f"homepage fetch failed: {r.status_code}"
html = r.data.decode("utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 2. Discover referenced resource paths
# ---------------------------------------------------------------------------
quoted = set(re.findall(r'''["'](/(?:media|evidence|api)/[^"'<>\s]*)["']''', html))
quoted |= set(re.findall(r'''url\((/(?:media|evidence|api)/[^)'"]+)\)''', html))

SAFE_API_PREFIXES = ("/api/state", "/api/looks", "/api/char-refs",
                      "/api/look-image/", "/api/mode-b/panel-plan")

def is_template(p):
    return "${" in p or "%7B" in p

concrete = set()
skipped_template = set()
skipped_unsafe_api = set()
for p in quoted:
    if is_template(p):
        skipped_template.add(p)
        continue
    if p.startswith("/api/"):
        if not any(p.startswith(pref) for pref in SAFE_API_PREFIXES):
            skipped_unsafe_api.add(p)
            continue
    # strip query string for the fetch/storage key, remember original for HTML replace
    concrete.add(p)

# ---------------------------------------------------------------------------
# 3. Fetch the 4 read-only data APIs explicitly (always, even if not literally
#    quoted with a fixed string) and expand look-image references.
# ---------------------------------------------------------------------------
data_endpoints = {
    "/api/state": "state.json",
    "/api/looks": "looks.json",
    "/api/char-refs": "char_refs.json",
    "/api/mode-b/panel-plan": "mode_b_panel_plan.json",
}

fetched = {}         # original_path (no query) -> bytes
content_types = {}   # original_path -> content_type
statuses = {}        # original_path -> status_code

def fetch(path):
    clean = path.split("?", 1)[0]
    if clean in fetched:
        return statuses[clean]
    resp = client.get(clean)
    statuses[clean] = resp.status_code
    if resp.status_code == 200:
        fetched[clean] = resp.data
        content_types[clean] = resp.content_type or ""
    return resp.status_code

for path in data_endpoints:
    fetch(path)

# expand look-image references from looks.json
look_image_targets = set()
if "/api/looks" in fetched:
    try:
        looks_obj = json.loads(fetched["/api/looks"])
        for lk in looks_obj.get("looks", []):
            lid = lk.get("look_id")
            if not lid:
                continue
            names = set()
            if lk.get("main_thumbnail"):
                names.add(lk["main_thumbnail"])
            for ref in lk.get("references", []) or []:
                if isinstance(ref, dict) and ref.get("filename"):
                    names.add(ref["filename"])
            for name in names:
                look_image_targets.add(f"/api/look-image/{lid}/{name}")
    except Exception as e:
        print("WARN: could not parse looks.json", e)

concrete |= look_image_targets

# ---------------------------------------------------------------------------
# 4. Fetch every concrete target
# ---------------------------------------------------------------------------
missing = []
for p in sorted(concrete):
    code = fetch(p)
    if code != 200:
        missing.append((p, code))

for p in data_endpoints:
    if p not in fetched:
        missing.append((p, statuses.get(p, "n/a")))

print(f"Discovered quoted refs: {len(quoted)}")
print(f"  concrete (fetchable): {len(concrete)}")
print(f"  skipped template refs: {len(skipped_template)}")
print(f"  skipped unsafe/mutating api refs: {len(skipped_unsafe_api)}")
print(f"Fetched OK: {len(fetched)}   Missing/failed: {len(missing)}")
for p, c in missing:
    print("  MISSING", p, c)

# ---------------------------------------------------------------------------
# 5. Classify + build new relative path for each fetched resource
# ---------------------------------------------------------------------------
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
VID_EXT = {".mp4", ".mov", ".webm"}
REPORT_EXT = {".md", ".csv", ".pdf", ".txt"}
DATA_EXT = {".json"}
DOWNLOAD_EXT = {".zip"}

def ext_category(ext):
    if ext in IMG_EXT: return "images"
    if ext in VID_EXT: return "videos"
    if ext in REPORT_EXT: return "reports"
    if ext in DATA_EXT: return "data"
    if ext in DOWNLOAD_EXT: return "downloads"
    return None

def ext_from_content_type(ct):
    ct = (ct or "").split(";")[0].strip()
    return mimetypes.guess_extension(ct) or ""

def strip_known_prefix(path):
    for pref in ("/media/", "/evidence/", "/api/look-image/"):
        if path.startswith(pref):
            return path[len(pref):]
    return path.lstrip("/")

path_map = {}   # original clean path -> new relative path (posix, relative to OUT)
excluded_private = []

for orig in sorted(fetched.keys()):
    data = fetched[orig]
    subpath = strip_known_prefix(orig)
    # `orig` is the *percent-encoded* href exactly as it appeared in the HTML
    # (e.g. spaces/CJK filenames like "ChatGPT%20Image%202026%E5%B9%B4...").
    # Flask's test client URL-decodes it internally to find the real file on
    # disk, so `fetch()` succeeds — but if we then use the still-encoded
    # string verbatim as the *destination filename*, we write a file whose
    # name literally contains "%20"/"%E5%B9%B4" characters instead of a
    # space/CJK text. A real static host later decodes the request path to
    # look up the file, finds no match, and serves 404 (broken image). Decode
    # here so the file we write on disk has the same real name the browser
    # will resolve its request to.
    subpath = urllib.parse.unquote(subpath)
    ext = Path(subpath).suffix.lower()
    if not ext:
        ext = ext_from_content_type(content_types.get(orig, ""))
        if ext:
            subpath = subpath + ext
    cat = ext_category(ext) or "downloads"
    new_rel = f"assets/{cat}/{subpath}"
    path_map[orig] = new_rel

# explicit data endpoint aliases -> assets/data/<friendly-name>.json (in addition
# to the assets/media-style mapping already computed above)
for api_path, fname in data_endpoints.items():
    if api_path in fetched:
        path_map[api_path] = f"assets/data/{fname}"

# ---------------------------------------------------------------------------
# 6. Write files to disk
# ---------------------------------------------------------------------------
for orig, rel in path_map.items():
    dest = OUT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(fetched[orig])

print(f"Wrote {len(path_map)} asset files")

# ---------------------------------------------------------------------------
# 7. Rewrite HTML: longest concrete strings first, then generic prefixes for
#    templated JS references (defensive - current live state has 0 shots so
#    these templates do not render anything today, but keep them consistent).
# ---------------------------------------------------------------------------
replacements = []
for orig, rel in path_map.items():
    replacements.append((orig, rel))
    # also cover the "?query" variant (e.g. /media/reference-video?t=...)
    replacements.append((orig + "?", rel + "?"))

PREFIX_GENERALIZATIONS = [
    ("/media/keyframes/", "assets/images/keyframes/"),
    ("/media/ref-keyframes/", "assets/images/ref-keyframes/"),
    ("/media/thumbs/", "assets/images/thumbs/"),
    ("/media/dance-keyposes/", "assets/images/dance-keyposes/"),
    ("/media/character-look/", "assets/images/character-look/"),
    ("/media/mb-panels/", "assets/images/mb-panels/"),
    ("/media/mb-sheet/", "assets/images/mb-sheet/"),
    ("/media/ip-ref/", "assets/images/ip-ref/"),
    ("/media/mode-b-ip/", "assets/images/mode-b-ip/"),
    ("/media/scene/", "assets/images/scene/"),
    ("/media/pose-overlay/", "assets/images/pose-overlay/"),
    ("/media/clips/", "assets/videos/clips/"),
    ("/media/characters/", "assets/images/characters/"),
    ("/media/reference-video", "assets/videos/reference-video.mp4"),
    ("/api/look-image/", "assets/images/look-image/"),
    ("/api/state", "assets/data/state.json"),
    ("/api/looks", "assets/data/looks.json"),
    ("/api/char-refs", "assets/data/char_refs.json"),
    ("/api/mode-b/panel-plan", "assets/data/mode_b_panel_plan.json"),
]
replacements.extend(PREFIX_GENERALIZATIONS)

# sort longest-first so we never partially clobber a longer, more specific match
replacements.sort(key=lambda t: -len(t[0]))

new_html = html
for old, new in replacements:
    new_html = new_html.replace(old, new)

# ---------------------------------------------------------------------------
# 8. Static safety net: block any residual write-method fetch calls, and
#    remove server dependency messaging.
# ---------------------------------------------------------------------------
SAFETY_SNIPPET = """
<script id="static-export-safety-net">
(function () {
  var ORIGINAL_FETCH = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function (input, init) {
    var method = ((init && init.method) || "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      console.warn("[static export] blocked " + method + " request — disabled in static read-only export:", input);
      return Promise.resolve(new Response(
        JSON.stringify({ ok: false, error: "Disabled in static read-only export" }),
        { status: 403, headers: { "Content-Type": "application/json" } }
      ));
    }
    if (!ORIGINAL_FETCH) return Promise.reject(new Error("Disabled in static read-only export"));
    return ORIGINAL_FETCH(input, init).catch(function (err) {
      console.warn("[static export] fetch unavailable in static hosting:", input, err);
      throw err;
    });
  };
})();
</script>
</body>"""

if "</body>" in new_html:
    new_html = new_html.replace("</body>", SAFETY_SNIPPET, 1)
else:
    new_html += SAFETY_SNIPPET

# ---------------------------------------------------------------------------
# 9. Write index.html + pages/ note + README + reports
# ---------------------------------------------------------------------------
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "index.html").write_text(new_html, encoding="utf-8")

PAGES.mkdir(parents=True, exist_ok=True)
(PAGES / "README.txt").write_text(
    "This dashboard is implemented as a single-page application: every "
    "curated section (overview, reference analysis, Mode A/B/C/D, repair, "
    "evaluation, limitations, evidence index, decision log, etc.) is "
    "rendered inside index.html and switched client-side via in-page "
    "navigation/hash routing, exactly as in the live read-only dashboard. "
    "No separate page files were generated because the source app has a "
    "single '/' route (render_template_string(HTML)); all other Flask "
    "routes are /api/* and /media/* data/asset endpoints, not pages. This "
    "matches the export brief's fallback instruction for single-page apps: "
    "export the rendered homepage with all internal sections preserved and "
    "keep internal navigation working, rather than fabricate separate page "
    "files.\n",
    encoding="utf-8",
)

missing_lines = ["# Missing public media report\n",
                  f"_Generated {datetime.now(timezone.utc).isoformat()}_\n\n",
                  "The static export renders the full dashboard from a live in-process "
                  "request against `pipeline/app.py` (Flask test client, no network, "
                  "no generation). The following resources were referenced by the "
                  "rendered page (or by its read-only JSON state) but could not be "
                  "fetched — usually because the underlying file is not present in "
                  "this checkout (e.g. `character_look/` lives outside the project "
                  "folder) or the route itself is a pre-existing gap "
                  "(`/media/look-ref-front`, tracked separately in "
                  "`codex_dashboard_patch_instructions.md` item 17). No backend logic "
                  "was changed to work around these; the corresponding elements in "
                  "the static page will show broken media rather than a fabricated "
                  "placeholder image, since no placeholder asset exists in the source "
                  "app.\n\n"]
if missing:
    missing_lines.append("| Path | Status |\n|---|---|\n")
    for p, c in missing:
        missing_lines.append(f"| `{p}` | {c} |\n")
else:
    missing_lines.append("None. Every resource referenced by the rendered homepage "
                          "and its read-only JSON state was fetched successfully.\n")
(OUT / "missing_files_report.md").write_text("".join(missing_lines), encoding="utf-8")

excluded_private = [
    "mode_c.MP4 (root-level raw 27.15s Mode C driving/control source video — not linked by the live dashboard; excluded)",
    "reference_videos/ and video_ref/ raw working folders (not linked by the live dashboard; excluded)",
    ".env (API keys / secrets — excluded)",
    "project_state.json / project_state.last_valid.json raw files (server-local state with absolute local paths — only the sanitized /api/state JSON actually served by the read-only route is included)",
    "pipeline/app.py.backup_* development backups (not part of the deployed site)",
    "_archive/, _to_delete/, __pycache__/ working/cache folders (excluded)",
]

# count pages: single-page export = 1
summary = {
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "source": "pipeline/app.py rendered in-process via Flask test client (no network, no generation, ONLINE_DEMO_READ_ONLY=1)",
    "pages_exported": 1,
    "pages_note": "Single-page app: all curated sections live inside index.html (see pages/README.txt).",
    "assets_copied_total": len(path_map),
    "assets_by_category": {
        cat: sum(1 for v in path_map.values() if v.startswith(f"assets/{cat}/"))
        for cat in ["images", "videos", "reports", "data", "downloads"]
    },
    "videos_copied": sum(1 for v in path_map.values() if v.startswith("assets/videos/")),
    "reports_or_data_files_copied": sum(1 for v in path_map.values() if v.startswith("assets/reports/") or v.startswith("assets/data/")),
    "excluded_private_files": excluded_private,
    "missing_public_files": [{"path": p, "status": str(c)} for p, c in missing],
    "raw_private_control_videos_included": False,
    "post_generation_routes_reachable": False,
    "online_demo_read_only_flag_at_export_time": True,
    "deployable": True,
}
(OUT / "export_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("DONE")
print(json.dumps(summary, indent=2))
