# Missing public media report
_Generated 2026-08-06T18:35:12.521607+00:00_

The static export renders the full dashboard from a live in-process request against `pipeline/app.py` (Flask test client, no network, no generation). The following resources were referenced by the rendered page (or by its read-only JSON state) but could not be fetched — usually because the underlying file is not present in this checkout (e.g. `character_look/` lives outside the project folder) or the route itself is a pre-existing gap (`/media/look-ref-front`, tracked separately in `codex_dashboard_patch_instructions.md` item 17). No backend logic was changed to work around these; the corresponding elements in the static page will show broken media rather than a fabricated placeholder image, since no placeholder asset exists in the source app.

| Path | Status |
|---|---|
| `/media/character-look/scene_dressing_room.png` | 404 |
| `/media/character-look/scene_studio.png` | 404 |
| `/media/look-ref-front` | 404 |
| `/media/test/` | 404 |
