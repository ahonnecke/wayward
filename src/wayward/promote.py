#!/usr/bin/env python3
"""Move CDLC files from staging to live on the NAS, then sync _m.psarc to rocksmithytoo."""

import argparse
import shutil
import subprocess
import sys

from wayward.config import LIVE, REMOTE_DLC, REMOTE_HOST, STAGING


def scp_to_remote(filename: str):
    """SCP a single _m.psarc file to the rocksmithytoo Steam DLC dir."""
    if not filename.endswith("_m.psarc"):
        return
    src = LIVE / filename
    dest = f"{REMOTE_HOST}:{REMOTE_DLC}"
    result = subprocess.run(
        ["scp", str(src), dest],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  synced to rocksmithytoo: {filename}")
    else:
        print(f"  scp failed for {filename}: {result.stderr.strip()}", file=sys.stderr)


def sync_all():
    """Rsync all _m.psarc files from live/ to rocksmithytoo Steam DLC dir."""
    src = str(LIVE) + "/"
    dest = f"{REMOTE_HOST}:{REMOTE_DLC}"
    cmd = [
        "rsync",
        "-av",
        "--progress",
        "--include=*_m.psarc",
        "--exclude=*",
        src,
        dest,
    ]
    print(f"Syncing _m.psarc files from {LIVE} to rocksmithytoo...")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("rsync failed", file=sys.stderr)
        sys.exit(1)
    print("Sync complete.")


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
        scp_to_remote(name)


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
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Rsync all _m.psarc from live/ to rocksmithytoo Steam DLC dir",
    )
    args = parser.parse_args()

    if args.sync:
        sync_all()
    elif args.list:
        list_staging()
    elif args.all:
        promote_all()
    elif args.files:
        promote(args.files)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
