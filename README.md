# Wayward

**Wayward** is an automated file processing daemon that watches a designated directory (e.g., `~/Downloads`) for newly created or modified files. When a file is detected, Wayward waits for it to stabilize (i.e., stop changing in size), then processes it based on its type — such as `.psarc` CDLC files or screenshots — using a handler pipeline.

<img width="1681" height="398" alt="Image" src="https://github.com/user-attachments/assets/e94a8029-9198-4279-beb9-822376c30a2f" />

## Features

- 📂 **Automatic file detection** in `~/Downloads`
- ⏳ **Waits for file stabilization** to avoid processing incomplete downloads
- 🎸 **Processes Rocksmith CDLC** with `pyrocksmith`, including renaming, moving, and remote deployment
- 🖼️ **Renames screenshots** using OCR to generate human-readable filenames
- 📤 **Moves processed files** to a remote host (e.g., a Rocksmith machine)
- 🧹 **Cleans up local files** after processing to keep things tidy

## Example Output

```shell
INFO:wayward:Received created or modified - ~/Downloads/Tears-For-Fears_Change_v3_p.psarc.
INFO:wayward:File has stabilized at 3920142
INFO:wayward:Handling file with PsarcHandler
INFO:wayward:Processed with pyrocksmith.
INFO:wayward:Moved CDLC to remote host
INFO:wayward:Removed local copy
```

## Usage

```bash
wayward --no-daemon   # Run in foreground, logs to console
wayward --daemon      # Run in background (default)
```

You can also simulate a new file event by "touching" an existing file:

```bash
touch ~/Downloads/somefile.psarc
```

## Installation

Clone the repository and ensure dependencies are installed (such as `pyrocksmith`, `pytesseract`, etc.)
