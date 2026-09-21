"""Configuration for wayward.

Every path has a sensible default and can be overridden with an env var, so
moving a destination (or running on another machine) needs no code edit.
"""

import os
from pathlib import Path

HOME = Path.home()


def _path(env: str, default: Path) -> Path:
    """Env-overridable path, with ~ expansion."""
    return Path(os.environ.get(env, str(default))).expanduser()


# --- watched folder ---
DOWNLOADS_DIR = _path("WAYWARD_DOWNLOADS", HOME / "Downloads")

# --- routing destinations ---
SCREENSHOTS_DIR = _path("WAYWARD_SCREENSHOTS", HOME / "screenshots")
IMAGES_DIR = _path("WAYWARD_IMAGES", HOME / "Downloads" / "images")
QMK_DIR = _path("WAYWARD_QMK", HOME / "qmk")
STL_DIR = _path("WAYWARD_STL", HOME / "stl")

# --- psarc → feedBack ingest ---
# A downloaded .psarc is handed to the psarc2fb CLI, which converts it to a
# .sloppak and POSTs it to feedBack's upload API (POST /api/songs/upload).
# feedBack owns library writes and the scan index, so it installs + reindexes.
# Canonical command: `cd ~/src/psarc2feedback && ./.venv/bin/python psarc2fb.py <file>`
PSARC2FB_DIR = os.environ.get("WAYWARD_PSARC2FB_DIR", str(HOME / "src" / "psarc2feedback"))
PSARC2FB_PYTHON = os.environ.get("WAYWARD_PSARC2FB_PYTHON", f"{PSARC2FB_DIR}/.venv/bin/python")
