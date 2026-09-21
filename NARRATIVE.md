# Wayward — Narrative

## Goal
A daemon that watches `~/Downloads` and files new downloads by type — the thing
that keeps the Downloads folder monitored and tidy. The live concern: Rocksmith
`.psarc` CDLC downloads get ingested into feedBack automatically.

## Arc
Wayward's original CDLC path (`pyrocksmith --convert` → NAS `Rocksmith_CDLC`
staging → `promote`/`quarantine` → SCP to a Mac) fully bit-rotted: `pyrocksmith`
is gone, the NAS tree is gone, and the CDLC pipeline moved to **feedBack**
(successor to slopsmith) with **psarc2fb** (`~/src/psarc2feedback`) as the
converter/uploader.

Rather than restore the old machinery, wayward was **trimmed to a clean
file-router** and its one live pipeline (psarc → feedBack) rewired.

## State (2026-09-21)
- **PsarcHandler → feedBack.** Runs
  `<psarc2feedback>/.venv/bin/python psarc2fb.py <file>` per download; deletes
  local only on exit 0. Config: `PSARC2FB_DIR` / `PSARC2FB_PYTHON`.
- **Trimmed.** Deleted `promote.py`, `quarantine.py`, `ocr_image.py`,
  `rename_picure_from_contents.py`, the dead `sanitize_file`/`ocr_picture`/
  `rename_picture_from_contents` methods, stale NAS/rocksmithytoo config, and
  the two extra console-script entrypoints. Also removed **QmkHandler** — QMK
  firmware is handled by a separate LLM-driven process now. What's left is the
  router: Screenshot / Image / Psarc / STL handlers.
- **Config.** All paths (Downloads, screenshots, images, stl, psarc2fb) live in
  `config.py` with `WAYWARD_*` env overrides + sensible defaults; `main.py`
  reads them via `config.*`. No code edit needed to move a destination.
- **Installed + supervised.** `pyproject.toml` deps declared
  (watchdog/psutil/setproctitle/python-daemon); `pipx install -e .`. Runs as a
  systemd **user** service (`wayward.service`, enabled, lingering on) →
  auto-start at boot, restart on failure. Full watch path verified under
  systemd (create → stabilize → psarc2fb → feedBack → local rm).
- **Backlog cleared.** The 10 stranded `~/Downloads` psarcs are in feedBack.
- **Docs** (README, ARCHITECTURE) rewritten to match the trimmed reality.

## Cleanup owed
- **10 redundant psarc copies still sit in slopsmith staging**
  (`nasty:/volume1/slopsmith/cdlc/staging`) from the first (wrong) routing pass.
  Harmless (only `cdlc/live` is served) but clutter. Not deleted — `scp` may
  have overwritten pre-existing entries there, so a blind delete risks removing
  a legit one. Purge only if slopsmith staging is defunct.

## Improvement ideas (remaining)
- No early-return on handler match (every handler's filter runs on every file).
- SIGTERM handling is implicit via systemd; graceful stop could be explicit.
- `python-daemon` / `--daemon` path is now dead weight under systemd.
- ImageHandler moves *every* non-screenshot image into `~/Downloads/images/
  YYYY-MM-DD/` — kept deliberately (user: fine as long as easy to reach).
