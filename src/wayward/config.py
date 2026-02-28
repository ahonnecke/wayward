"""Shared paths and constants for wayward CDLC management."""

from pathlib import Path

CDLC_ROOT = Path("/home/ahonnecke/nasty/music/Rocksmith_CDLC")
STAGING = CDLC_ROOT / "staging"
LIVE = CDLC_ROOT / "live"
QUARANTINE = CDLC_ROOT / "quarantine"

REMOTE_HOST = "ahonnecke@rocksmithytoo"
REMOTE_DLC = "~/Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc/"
