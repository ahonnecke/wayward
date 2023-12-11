#!/usr/bin/env python3
import logging
import os
import shutil
import time
from functools import cached_property
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

    def on_any_event(self, event):
        if event.is_directory:
            return None

        elif event.event_type == "created":
            # Take any action here when a file is first created.
            print(f"Received created event - {event.src_path}.")
            return self.handle_created(event)

        elif event.event_type == "modified":
            # Taken any action here when a file is modified.
            print(f"Received modified event - {event.src_path}.")

    def handle_created(self, event):
        debug(event)

        file_path = Path(event.src_path)
        print(file_path.suffix)
        if file_path.suffix == ".bin":
            print("found bin file")
            os.rename(event.src_path, f"/home/ahonnecke/qmk/{file_path.name}")
        elif file_path.suffix == ".cdlc":
            os.system("convert_rocksmith.sh")
        elif file_path.suffix in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"]:
            os.rename(
                event.src_path, f"/home/ahonnecke/Downloads/images/{file_path.name}"
            )


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
