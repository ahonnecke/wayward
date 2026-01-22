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
           │     └─ ~/screenshots/YYYY-MM-DD/ + LLM rename + OCR
           │
           ├─ ImageHandler  (*.{png,jpg,...} except screenshots)
           │     └─ ~/Downloads/images/YYYY-MM-DD/
           │
           ├─ PsarcHandler  (*.psarc - Rocksmith CDLC)
           │     └─ pyrocksmith --convert → scp to rocksmithytoo + NAS backup
           │
           ├─ QmkHandler  (*.bin - keyboard firmware)
           │     └─ ~/qmk/
           │
           └─ STL lambda  (*.stl - 3D prints)
                 └─ ~/stl/
```

## Key Implementation Details

| Component                        | Location          | Function                                                 |
| -------------------------------- | ----------------- | -------------------------------------------------------- |
| `Watcher`                        | `main.py:24-40`   | Observer lifecycle, 5s poll loop                         |
| `Handler`                        | `main.py:224-288` | Event filtering, file stabilization                      |
| `FileTypeHandler`                | `main.py:43-120`  | Base class with `sanitize_file()`, `is_image()`, helpers |
| `PsarcHandler`                   | `main.py:122-174` | CDLC processing pipeline                                 |
| `ScreenshotHandler`              | `main.py:176-194` | Date-organized screenshots with AI rename                |
| `ocr_image.py`                   | `/src/wayward/`   | pytesseract wrapper → `.ocr.txt` sidecar                 |
| `rename_picure_from_contents.py` | `/src/wayward/`   | LLaVA 7B image captioning → filename                     |

## File Stabilization Logic

```python
# main.py:248-254
while historicalSize != os.path.getsize(file_path):
    historicalSize = os.path.getsize(file_path)
    time.sleep(1)
```

This prevents processing incomplete downloads. Firefox `.part` files are also explicitly skipped.

## External Dependencies

- **pyrocksmith**: CDLC conversion (`~/.pyenv/shims/pyrocksmith`)
- **llava-v1.5-7b-q4.llamafile**: Local LLM for image description (`~/local/bin/`)
- **pytesseract**: OCR (Tesseract wrapper)
- **watchdog**: Filesystem events
- **psutil**: Duplicate process detection

## Remote Integration

CDLC files get `scp`'d to `ahonnecke@rocksmithytoo:/Users/ahonnecke/dlc/` and backed up to `~/nasty/music/Rocksmith_CDLC/unverified`.

## Usage

```bash
wayward --no-daemon   # foreground, stdout logging
wayward --daemon      # default, daemonized
```

Logs to `/dev/log` (syslog) and `/tmp/wayward.log`.
