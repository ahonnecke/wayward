# Wayward TODO

## Bugs

- [x] Duplicate stabilization logic - `wait_for_file()` called, then same logic repeated inline
- [x] `sanitize_file()` duplication - removed from Handler class (kept in FileTypeHandler)
- [x] `sanitize_psarcs_in_dir()` returns on first rename - now sanitizes all files, tracks target
- [x] `remote_move_cdlc()` parameter named `event` but receives a path - removed unused param
- [x] File deleted even if scp/cp fails - added error handling, skip delete on failure
- [x] `handle_touchterrain()` is dead code - removed
- [x] Bare `except:` in Watcher.run() - now catches KeyboardInterrupt and Exception separately
- [x] pyrocksmith runs on pre-sanitized path - now uses returned sanitized path

## Design Issues

- [ ] Hardcoded paths everywhere - no config file, no env vars
- [ ] No graceful shutdown - no SIGTERM handling
- [ ] Inheritance model confused - subclasses don't call super().**init**()
- [ ] No early return on handler match - all handlers called even after success
