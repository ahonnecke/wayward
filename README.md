# Wayward

**Wayward** is a file-routing daemon that watches `~/Downloads` for new files.
When a file appears, Wayward waits for it to stop changing size (so partial
downloads aren't touched), then files it by type.

## What it routes

| Download            | Destination                                   |
| ------------------- | --------------------------------------------- |
| `shot_*` screenshot | `~/screenshots/YYYY-MM-DD/`                    |
| other images        | `~/Downloads/images/YYYY-MM-DD/`              |
| `*.psarc` (CDLC)    | feedBack, via the `psarc2fb` CLI              |
| `*.stl` (3D print)  | `~/stl/`                                       |

### Rocksmith CDLC → feedBack

A downloaded `.psarc` is handed to **psarc2fb** (`~/src/psarc2feedback`), which
converts it to a `.sloppak` and `POST`s it to feedBack's upload API. feedBack
owns library writes and the scan index, so it installs the song and re-indexes
automatically. Wayward removes the local `.psarc` only after `psarc2fb` exits 0
(which includes the "already in the library" case). The equivalent by hand:

```bash
cd ~/src/psarc2feedback && ./.venv/bin/python psarc2fb.py <file-or-dir>
```

Requires feedBack to be running (default `http://localhost:8001`) and `ffmpeg`
on `PATH`.

## Running it

Wayward runs as a systemd **user** service, so it starts on login/boot and
restarts on failure:

```bash
systemctl --user status wayward       # is it running?
systemctl --user restart wayward      # after a code change / reinstall
journalctl --user -u wayward -f       # follow the log
```

Or run it directly:

```bash
wayward --no-daemon   # foreground, logs to stderr + /tmp/wayward.log + syslog
wayward --daemon      # detach (python-daemon); not used under systemd
```

## Installation

```bash
pipx install -e .     # registers the `wayward` command
```

Then install the service unit at `~/.config/systemd/user/wayward.service` and
`systemctl --user enable --now wayward`.

Dependencies: `watchdog`, `psutil`, `setproctitle`, `python-daemon`.
