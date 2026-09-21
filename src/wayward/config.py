"""Shared configuration for wayward."""

# --- psarc → feedBack ingest ---
# A downloaded .psarc is handed to the psarc2fb CLI, which converts it to a
# .sloppak and POSTs it to feedBack's upload API (POST /api/songs/upload).
# feedBack owns library writes and the scan index, so it installs + reindexes.
# wayward needs no NFS/library access — just runs the tool via its own venv.
# Canonical command: `cd ~/src/psarc2feedback && ./.venv/bin/python psarc2fb.py <file>`
PSARC2FB_DIR = "/home/ahonnecke/src/psarc2feedback"
PSARC2FB_PYTHON = f"{PSARC2FB_DIR}/.venv/bin/python"
