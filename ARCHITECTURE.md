# Wayward - File Processing Daemon

## Core Purpose

Wayward is a daemon that watches `~/Downloads` via `watchdog` and automatically routes files to handlers based on type/extension. It solves the problem of manually organizing downloads.

## Architecture

```
~/Downloads (watched via watchdog.Observer)
    │
    ▼
Handler (FileSystemEventHandler)
    ├─ Filters: created/modified events only, skips .part files
    ├─ wait_for_file(): Polls until file size stabilizes (1s intervals)
    └─ Routes to registered FileTypeHandlers
           │
           ├─ ScreenshotHandler  (shot_*.{png,jpg,...})
           │     └─ ~/screenshots/YYYY-MM-DD/
           │
           ├─ ImageHandler  (*.{png,jpg,...} except screenshots)
           │     └─ ~/Downloads/images/YYYY-MM-DD/
           │
           ├─ PsarcHandler  (*.psarc - Rocksmith CDLC)
           │     └─ pyrocksmith --convert → NAS staging/
           │
           ├─ QmkHandler  (*.bin - keyboard firmware)
           │     └─ ~/qmk/
           │
           └─ STL lambda  (*.stl - 3D prints)
                 └─ ~/stl/
```

## Key Implementation Details

| Component           | Location  | Function                                                 |
| ------------------- | --------- | -------------------------------------------------------- |
| `main()`            | `main.py` | CLI entrypoint: arg parsing, logging, daemon/foreground  |
| `run()`             | `main.py` | Creates Watcher + handlers, starts event loop            |
| `Watcher`           | `main.py` | Observer lifecycle, 5s health-check loop, auto-restart   |
| `Handler`           | `main.py` | Event filtering, file stabilization, exception guarding  |
| `FileTypeHandler`   | `main.py` | Base class with `sanitize_file()`, `is_image()`, helpers |
| `PsarcHandler`      | `main.py` | CDLC: pyrocksmith convert → NAS staging                  |
| `ScreenshotHandler` | `main.py` | Date-organized screenshots                               |

## Entrypoint Structure

`pyproject.toml` registers `wayward = "wayward.main:main"`. The `main()` function handles
arg parsing (`--daemon`/`--no-daemon`), logging setup, and daemon context. The `run()`
function creates the Watcher and enters the event loop. Logging must be set up inside
`DaemonContext` to survive the fork's fd cleanup.

## Observer Resilience

The Watcher polls `observer.is_alive()` every 5 seconds and auto-restarts a dead observer.
The `handle_created` method wraps all processing in a try/except so a single file error
cannot crash the observer thread. `wait_for_file` handles `FileNotFoundError` for files
that vanish mid-download. Downloads is watched non-recursively to avoid inotify flooding
from subdirectories.

## File Stabilization Logic

Polls file size at 1-second intervals until stable. Returns 0 if the file disappears.
Firefox `.part` files are explicitly skipped.

## External Dependencies

- **pyrocksmith**: CDLC conversion (`~/.pyenv/shims/pyrocksmith`)
- **watchdog**: Filesystem events
- **psutil**: Duplicate process detection

## Remote Integration

CDLC files are staged to `~/nasty/music/Rocksmith_CDLC/staging/`, then promoted to `live/` via `wayward-promote` which SCPs `_m.psarc` files to rocksmithytoo's local Steam DLC dir.

## Usage

```bash
wayward --no-daemon   # foreground, logs to stderr + file + syslog
wayward               # default, daemonized, logs to file + syslog
```

Logs to `/dev/log` (syslog) and `/tmp/wayward.log`. `--no-daemon` additionally logs to stderr.
