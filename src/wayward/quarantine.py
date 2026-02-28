#!/usr/bin/env python3
"""Move CDLC files to quarantine on the NAS, and sync removals/restores to rocksmithytoo."""

import argparse
import shutil
import subprocess
import sys

from wayward.config import LIVE, QUARANTINE, REMOTE_DLC, REMOTE_HOST, STAGING


def rm_from_remote(filename: str):
    """SSH rm a _m.psarc file from rocksmithytoo Steam DLC dir."""
    if not filename.endswith("_m.psarc"):
        return
    remote_path = f"{REMOTE_DLC}{filename}"
    result = subprocess.run(
        ["ssh", REMOTE_HOST, "rm", "-f", remote_path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"  removed from rocksmithytoo: {filename}")
    else:
        print(
            f"  ssh rm failed for {filename}: {result.stderr.strip()}", file=sys.stderr
        )


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
        rm_from_remote(name)


def restore(filenames: list[str]):
    for name in filenames:
        src = QUARANTINE / name
        if not src.exists():
            print(f"Not found in quarantine: {name}", file=sys.stderr)
            continue
        dest = LIVE / name
        shutil.move(str(src), str(dest))
        print(f"Restored to live: {name}")
        scp_to_remote(name)


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
