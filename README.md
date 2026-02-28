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
4. **Promote** — `wayward-promote` moves files from `staging/` to `live/`
5. **Quarantine** — `wayward-quarantine` isolates bad files

### NAS Directory Structure

```
/nasty/music/Rocksmith_CDLC/
├── live/           # Verified, game-ready — rocksmithytoo mounts this via NFS
├── staging/        # New downloads awaiting play-test
└── quarantine/     # Files that crashed the game
```

rocksmithytoo mounts `live/` directly via NFS, so promoted files are immediately available to Rocksmith.

## Usage

```bash
wayward --no-daemon   # Run in foreground, logs to console
wayward --daemon      # Run in background (default)

# Promote CDLC from staging to live
wayward-promote --list              # List staging files
wayward-promote <filename>          # Promote specific file
wayward-promote --all               # Promote everything

# Quarantine bad CDLC
wayward-quarantine <filename>       # Move to quarantine (checks live/ then staging/)
wayward-quarantine --list           # List quarantined files
wayward-quarantine --restore <file> # Restore from quarantine to live
```

## Installation

Clone the repository and install with pip:

```bash
pip install -e .
```

This registers `wayward`, `wayward-promote`, and `wayward-quarantine` as CLI commands.

Dependencies: `pyrocksmith`, `watchdog`, `psutil`, `setproctitle`, `python-daemon`.
