# Wayward

**Wayward** is an automated file processing daemon that watches a designated directory (e.g., `~/Downloads`) for newly created or modified files. When a file is detected, Wayward waits for it to stabilize (i.e., stop changing in size), then processes it based on its type — such as `.psarc` CDLC files or screenshots — using a handler pipeline.

<img width="1681" height="398" alt="Image" src="https://github.com/user-attachments/assets/e94a8029-9198-4279-beb9-822376c30a2f" />

## Features

- 📂 **Automatic file detection** in `~/Downloads`
- ⏳ **Waits for file stabilization** to avoid processing incomplete downloads
- 🎸 **Processes Rocksmith CDLC** with `pyrocksmith`, converts and stages to NAS
- 🖼️ **Renames screenshots** using OCR to generate human-readable filenames
- 📦 **NAS-based CDLC pipeline** with staging/live/quarantine lifecycle
- 🧹 **Cleans up local files** after processing to keep things tidy

## CDLC Pipeline

The NAS (`nasty`) is the source of truth for Rocksmith CDLC. The pipeline:

1. **Download** — `.psarc` lands in `~/Downloads`
2. **wayward** — detects, converts with `pyrocksmith`, moves both `_m.psarc` and `_p.psarc` to NAS `staging/`
3. **Play-test** — try songs in Rocksmith after promoting to `live/`
4. **Promote** — `wayward-promote` moves files from `staging/` to `live/`, then SCPs `_m.psarc` to rocksmithytoo
5. **Quarantine** — `wayward-quarantine` isolates bad files and removes them from rocksmithytoo

### NAS Directory Structure

```
/nasty/music/Rocksmith_CDLC/
├── live/           # Verified, game-ready — NAS is source of truth
├── staging/        # New downloads awaiting play-test
└── quarantine/     # Files that crashed the game
```

### rocksmithytoo Sync

NFS mount over WiFi is too slow (~540 KB/s) for Rocksmith to read psarcs directly. Instead, `_m.psarc` files are synced to rocksmithytoo's local Steam DLC dir via SCP/rsync:

- **On promote** — each `_m.psarc` is SCPed to `~/Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc/`
- **On quarantine** — the file is SSH-removed from rocksmithytoo
- **On restore** — the file is SCPed back
- **Catchup** — `wayward-promote --sync` rsyncs all `_m.psarc` files from `live/` to rocksmithytoo

The NFS mount remains at `~/mnt/nasty_cdlc_live` on rocksmithytoo for browsing, but Rocksmith reads from the local Steam DLC dir.

## Usage

```bash
wayward --no-daemon   # Run in foreground, logs to console
wayward --daemon      # Run in background (default)

# Promote CDLC from staging to live (+ sync to rocksmithytoo)
wayward-promote --list              # List staging files
wayward-promote <filename>          # Promote specific file, SCP _m.psarc to Mac
wayward-promote --all               # Promote everything
wayward-promote --sync              # Rsync all _m.psarc from live/ to rocksmithytoo

# Quarantine bad CDLC (+ remove from rocksmithytoo)
wayward-quarantine <filename>       # Move to quarantine, rm from Mac
wayward-quarantine --list           # List quarantined files
wayward-quarantine --restore <file> # Restore to live, SCP back to Mac
```

## Installation

Clone the repository and install with pip:

```bash
pip install -e .
```

This registers `wayward`, `wayward-promote`, and `wayward-quarantine` as CLI commands.

Dependencies: `pyrocksmith`, `watchdog`, `psutil`, `setproctitle`, `python-daemon`.
