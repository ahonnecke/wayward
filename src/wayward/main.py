#!/usr/bin/env python3
import logging
import os
import re
import subprocess
import time
from pathlib import Path

from devtools import debug
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class Watcher:
    def __init__(self, dirpath, handler):
        self.observer = Observer()
        self.dirpath = dirpath
        self.event_handler = handler

    def run(self):
        self.observer.schedule(self.event_handler, self.dirpath, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print("Error")

        self.observer.join()


class Handler(FileSystemEventHandler):
    def __init__(self, onchange):
        self.onchange = onchange
        self.BUILDSPACE = Path("/home/ahonnecke/cdlc_buildspace")

    def on_any_event(self, event):
        if event.is_directory:
            return None

        elif event.event_type == "created" or event.event_type == "modified":
            # Take any action here when a file is first created.
            print(f"Received created or modified - {event.src_path}.")
            return self.handle_created(event)

        def sanitize_file(self, current):
            new = re.sub(r"[^\w_. -]", "_", current).replace(" ", "_")
            if new != current:
                print(f"{current} => {new}")
                os.rename(current, new)

        def sanitize_psarcs_in_dir(self, dirpath):
            print(f"Sanitizing filenames in {dirpath}")
            for file in dirpath.glob("*.psarc*"):
                self.sanitize_file(file.name)

    def remote_move_cdlc(self, event):
        REMOTE_DEST = Path("ahonnecke@rocksmithy:/Users/ahonnecke/dlc/")
        BACKUP_DEST = Path("/home/ahonnecke/cldc/shipped/")

        for filename in os.listdir(self.BUILDSPACE):
            result = subprocess.run(
                [
                    "scp",
                    filename,
                    f"{REMOTE_DEST}/{filename}",
                    "&&",
                    "mv",
                    f"{self.BUILDSPACE}/{filename}",
                    BACKUP_DEST,
                ],
                stdout=subprocess.PIPE,
            )
            print(result.stdout)

    def wait_for_file(self, file_path):
        # Wait for file to stabilized
        historicalSize = -1
        while historicalSize != os.path.getsize(file_path):
            historicalSize = os.path.getsize(file_path)
            time.sleep(1)
        return True

    def handle_psarc(self, event):
        file_path = Path(event.src_path)

        PYROCKSMITH = Path("/home/ahonnecke/.pyenv/shims/pyrocksmith")

        os.rename(event.src_path, f"{self.BUILDSPACE}/{file_path.name}")
        self.sanitize_psarcs_in_dir(self.BUILDSPACE)
        result = subprocess.run(
            [PYROCKSMITH, "--convert", f"{self.BUILDSPACE}/{file_path.name}"],
            stdout=subprocess.PIPE,
        )
        print(result.stdout)
        self.remote_move(event)

    def handle_created(self, event):
        file_path = Path(event.src_path)
        if not file_path.is_file():
            # event was deletion or move
            return

        self.wait_for_file(file_path)

        if file_path.suffix == ".part":
            #Firefox partial download, ignore.
            return

        # Wait for file to stabilize
        historicalSize = -1
        while historicalSize != os.path.getsize(file_path):
            historicalSize = os.path.getsize(file_path)
            time.sleep(1)

        print("File file_path has stabilized")

        # TODO: make the file handler dynamic
        # TODO: make simple move file behavior dict based
        # ie. return self.handle_{file_path.suffix}

        if file_path.suffix == ".bin":
            os.rename(file_path, f"/home/ahonnecke/qmk/{file_path.name}")
        elif file_path.suffix == ".psarc":
            self.handle_psarc(event)
        elif file_path.suffix in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"]:
            os.rename(file_path, f"/home/ahonnecke/Downloads/images/{file_path.name}")
        elif file_path.suffix in [".stl"]:
            os.rename(file_path, f"/home/ahonnecke/stl/{file_path.name}")


class FileSorter:
    def __init__(self, rules: dict):
        self.rules = rules

    def handle_file(self):
        pass


def main():
    """Entrypoint for AWS lambda hot reloader, CLI args in signature."""
    ROOT = Path.cwd()
    observed = Path("/home/ahonnecke/Downloads/")

    # todo: if dir, move file, if executable execute executable on file
    rules = {"bin": "/home/ahonnecke/qmk"}
    sorter = FileSorter(rules)

    w = Watcher(observed, Handler(onchange=sorter.handle_file()))

    w.run()


if __name__ == "__main__":
    main()
