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
  the two extra console-script entrypoints. What's left is the router:
  Screenshot / Image / Psarc / Qmk / STL handlers.
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

## Improvement ideas (see chat)
- Hardcoded paths → config file / env (Downloads dir, feedBack URL, dest dirs).
- QmkHandler filters *all* `.bin` (too broad); ImageHandler moves *every* image
  out of Downloads (aggressive — may surprise).
- No early-return on handler match (every handler runs on every file).
- SIGTERM handling is implicit via systemd; graceful stop could be explicit.
