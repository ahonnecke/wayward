#!/usr/bin/env python3
"""Move CDLC files from staging to live on the NAS."""

import argparse
import shutil
import sys
from pathlib import Path

CDLC_ROOT = Path("/home/ahonnecke/nasty/music/Rocksmith_CDLC")
STAGING = CDLC_ROOT / "staging"
LIVE = CDLC_ROOT / "live"


def list_staging():
    files = sorted(STAGING.glob("*.psarc"))
    if not files:
        print("No files in staging.")
        return
    for f in files:
        print(f.name)


def promote(filenames: list[str]):
    for name in filenames:
        src = STAGING / name
        if not src.exists():
            print(f"Not found in staging: {name}", file=sys.stderr)
            continue
        dest = LIVE / name
        if dest.exists():
            print(f"Already in live (skipping): {name}", file=sys.stderr)
            continue
        shutil.move(str(src), str(dest))
        print(f"Promoted: {name}")


def promote_all():
    files = list(STAGING.glob("*.psarc"))
    if not files:
        print("No files in staging.")
        return
    promote([f.name for f in files])


def main():
    parser = argparse.ArgumentParser(description="Promote CDLC from staging to live.")
    parser.add_argument(
        "files", nargs="*", help="Filenames to promote (omit for --list or --all)"
    )
    parser.add_argument("--all", action="store_true", help="Promote all staging files")
    parser.add_argument("--list", "-l", action="store_true", help="List staging files")
    args = parser.parse_args()

    if args.list:
        list_staging()
    elif args.all:
        promote_all()
    elif args.files:
        promote(args.files)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
