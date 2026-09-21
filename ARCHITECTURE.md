# Wayward - File Routing Daemon

## Core Purpose

Wayward watches `~/Downloads` via `watchdog` and routes files to handlers based
on type/extension. It keeps the Downloads folder tidy without manual sorting.

## Architecture

```
~/Downloads (watched via watchdog.Observer, non-recursive)
    │
    ▼
Handler (FileSystemEventHandler)
    ├─ Filters: created/modified events only, skips *.part
    ├─ wait_for_file(): polls until file size stabilizes (1s intervals)
    └─ Dispatches to each registered FileTypeHandler
           │
           ├─ ScreenshotHandler  (shot_*.{png,jpg,...})  → ~/screenshots/YYYY-MM-DD/
           ├─ ImageHandler       (other images)          → ~/Downloads/images/YYYY-MM-DD/
           ├─ PsarcHandler       (*.psarc)               → feedBack via psarc2fb
           └─ STL lambda         (*.stl)                 → ~/stl/
```

## Key components (all in `main.py`)

| Component           | Function                                                    |
| ------------------- | ----------------------------------------------------------- |
| `main()`            | CLI entrypoint: arg parsing, logging, daemon/foreground     |
| `run()`             | Builds the Watcher + handler list, enters the event loop    |
| `Watcher`           | Observer lifecycle, 5s health-check loop, auto-restart      |
| `Handler`           | Event filtering, file stabilization, exception guarding     |
| `FileTypeHandler`   | Base class: `handle()`, `is_image()`, `is_screen_shot()`    |
| `PsarcHandler`      | Runs `psarc2fb` to convert + upload the CDLC to feedBack    |
| `ScreenshotHandler` | Date-organized screenshots                                  |

## PsarcHandler → feedBack

`PsarcHandler` shells out to psarc2fb's own venv:

```
<PSARC2FB_DIR>/.venv/bin/python psarc2fb.py <downloaded.psarc>
```

psarc2fb (a separate repo, `~/src/psarc2feedback`) converts the psarc to a
`.sloppak` and POSTs it to feedBack's upload API; feedBack writes it to the
library and re-indexes. Wayward has no filesystem access to the library and no
container coupling — it just runs the tool and deletes the local file on
success. Paths live in `config.py` (`PSARC2FB_DIR`, `PSARC2FB_PYTHON`).

## Observer resilience

The Watcher polls `observer.is_alive()` every 5s and restarts a dead observer.
`handle_created` wraps all processing in try/except so one bad file can't crash
the observer thread. `wait_for_file` handles `FileNotFoundError` for files that
vanish mid-download. Downloads is watched non-recursively to avoid inotify
flooding from subdirectories.

## Process management

Runs as a systemd user service (`~/.config/systemd/user/wayward.service`,
`Type=simple`, `ExecStart=wayward --no-daemon`), which owns the lifecycle,
restarts on failure, and starts at boot (user lingering is enabled). Logs go to
journald (plus `/tmp/wayward.log` and syslog).
