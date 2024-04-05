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
        dirname = current.parent
        new = Path(re.sub(r"[^\w_. -]", "_", current.name).replace(" ", "_"))
        from_path = Path(f"{dirname}/{current.name}")
        to_path = Path(f"{dirname}/{new}")

        if from_path != to_path:
            print(f"Renaming {from_path} => {to_path}")
            os.rename(from_path, to_path)
            return to_path

    def sanitize_psarcs_in_dir(self, dirpath):
        print(f"Sanitizing filenames in {dirpath}")
        for file in dirpath.glob("*.psarc*"):
            if new_path := self.sanitize_file(file):
                return new_path

    def remote_move_cdlc(self, event):
        print("Moving CDLC to remote host")
        REMOTE_DEST = Path("ahonnecke@rocksmithytoo:/Users/ahonnecke/dlc/")
        BACKUP_DEST = Path("/home/ahonnecke/nasty/music/Rocksmith_CDLC/unverified")

        for filename in os.listdir(self.BUILDSPACE):
            filepath = f"{self.BUILDSPACE}/{filename}"

            result = subprocess.run(
                ["scp", filepath, f"{REMOTE_DEST}/{filename}"],
                stdout=subprocess.PIPE,
            )
            result = subprocess.run(
                ["cp", filepath, f"{BACKUP_DEST}/{filename}"],
                stdout=subprocess.PIPE,
            )
            print(f"Copied {filepath} to remote host {REMOTE_DEST}.")
            os.remove(filepath)
            print(f"Removed {filepath}.")

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

        fullpath = f"{self.BUILDSPACE}/{file_path.name}"
        os.rename(event.src_path, fullpath)
        self.sanitize_psarcs_in_dir(self.BUILDSPACE)
        result = subprocess.run(
            [PYROCKSMITH, "--convert", fullpath],
            stdout=subprocess.PIPE,
        )
        print(f"Processed {fullpath} with pyrocksmith.")
        self.remote_move_cdlc(event)

    def handle_touchterrain(self, event):
        TOUCH_TERRAIN = Path("/home/ahonnecke/stl/USGS/touchterrain/")

        # if file of the form "757876378581.zip"
        # extract file number
        destination = Path(TOUCH_TERRAIN + "/" + zip_number)
        # mkdir destination
        # extract zip to destination
        # rm zip

    def handle_created(self, event):
        file_path = Path(event.src_path)
        if not file_path.is_file():
            # event was deletion or move
            return

        if file_path.suffix == ".part":
            # Firefox partial download, ignore.
            return

        self.wait_for_file(file_path)

        # Wait for file to stabilize
        historical_size = -1
        while historical_size != os.path.getsize(file_path):
            historical_size = os.path.getsize(file_path)
            time.sleep(1)

        print(f"File file_path has stabilized at {historical_size}")

        if historical_size < 1:
            return

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
