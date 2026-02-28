#!/usr/bin/env python3
"""Move CDLC files to quarantine on the NAS."""

import argparse
import shutil
import sys
from pathlib import Path

CDLC_ROOT = Path("/home/ahonnecke/nasty/music/Rocksmith_CDLC")
STAGING = CDLC_ROOT / "staging"
LIVE = CDLC_ROOT / "live"
QUARANTINE = CDLC_ROOT / "quarantine"


def list_quarantined():
    files = sorted(QUARANTINE.glob("*.psarc"))
    if not files:
        print("No quarantined files.")
        return
    for f in files:
        print(f.name)


def quarantine(filenames: list[str]):
    for name in filenames:
        src = LIVE / name
        if not src.exists():
            src = STAGING / name
        if not src.exists():
            print(f"Not found in live or staging: {name}", file=sys.stderr)
            continue
        dest = QUARANTINE / name
        shutil.move(str(src), str(dest))
        print(f"Quarantined: {name} (from {src.parent.name}/)")


def restore(filenames: list[str]):
    for name in filenames:
        src = QUARANTINE / name
        if not src.exists():
            print(f"Not found in quarantine: {name}", file=sys.stderr)
            continue
        dest = LIVE / name
        shutil.move(str(src), str(dest))
        print(f"Restored to live: {name}")


def main():
    parser = argparse.ArgumentParser(description="Quarantine or restore CDLC files.")
    parser.add_argument("files", nargs="*", help="Filenames to quarantine")
    parser.add_argument(
        "--restore", "-r", action="store_true", help="Restore from quarantine to live"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List quarantined files"
    )
    args = parser.parse_args()

    if args.list:
        list_quarantined()
    elif args.restore and args.files:
        restore(args.files)
    elif args.files:
        quarantine(args.files)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
