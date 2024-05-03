#!/usr/bin/env python3
from datetime import datetime
import logging
from os import getpid
from sys import argv, exit
from typing import List
import psutil
import os
import re
import subprocess
import time
from pathlib import Path
import setproctitle
from devtools import debug
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import logging
import logging.handlers
import daemon


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
            logger.error("Error")

        self.observer.join()


class FileTypeHandler:
    def __init__(self, file_filter, file_handler):
        self.file_filter = file_filter
        self.file_handler = file_handler

    def handle(self, path):
        if self.file_filter(path):
            logger.info(f"Handling file... {path}.")
            return self.file_handler(path)


class Handler(FileSystemEventHandler):
    def __init__(self, file_handlers: List[FileTypeHandler]):
        self.file_handlers = file_handlers
        self.BUILDSPACE = Path("/home/ahonnecke/cdlc_buildspace")

    def on_any_event(self, event):
        if event.is_directory:
            return None

        elif event.event_type == "created" or event.event_type == "modified":
            # Take any action here when a file is first created.
            logger.info(f"Received created or modified - {event.src_path}.")
            return self.handle_created(event)

    def sanitize_file(self, current):
        dirname = current.parent.absolute()
        new = Path(re.sub(r"[^\w_. -]", "_", current.name).replace(" ", "_"))
        from_path = Path(f"{dirname}/{current.name}")
        to_path = Path(f"{dirname}/{new}")

        if from_path != to_path:
            logger.info(f"Renaming {from_path} => {to_path}")
            os.rename(from_path, to_path)
            return to_path

    def sanitize_psarcs_in_dir(self, dirpath):
        logger.info(f"Sanitizing filenames in {dirpath}")
        for file in dirpath.glob("*.psarc*"):
            if new_path := self.sanitize_file(file):
                return new_path

    def remote_move_cdlc(self, event):
        psarc_pattern = "_m.psarc"

        logger.info("Moving CDLC to remote host")
        REMOTE_DEST = Path("ahonnecke@rocksmithytoo:/Users/ahonnecke/dlc/")
        BACKUP_DEST = Path("/home/ahonnecke/nasty/music/Rocksmith_CDLC/unverified")

        for filename in os.listdir(self.BUILDSPACE):
            filepath = f"{self.BUILDSPACE}/{filename}"

            if psarc_pattern in filename:
                result = subprocess.run(
                    ["scp", filepath, f"{REMOTE_DEST}/{filename}"],
                    stdout=subprocess.PIPE,
                )
                result = subprocess.run(
                    ["cp", filepath, f"{BACKUP_DEST}/{filename}"],
                    stdout=subprocess.PIPE,
                )
                logger.info(f"Copied {filepath} to remote host {REMOTE_DEST}.")

            os.remove(filepath)
            logger.info(f"Removed {filepath}.")

    def wait_for_file(self, file_path):
        # Wait for file to stabilized
        historicalSize = -1
        while historicalSize != os.path.getsize(str(file_path)):
            historicalSize = os.path.getsize(str(file_path))
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
        logger.info(f"Processed {fullpath} with pyrocksmith.")
        self.remote_move_cdlc(event)

    def handle_touchterrain(self, event):
        TOUCH_TERRAIN = Path("/home/ahonnecke/stl/USGS/touchterrain/")
        file_path = Path(event.src_path)

        destination = os.path.join(TOUCH_TERRAIN, os.path.basename(file_path))
        os.rename(event.src_path, destination)

    def rename_picture_from_contents(self, path: Path):
        logger.info("Renaming picture from contents...")
        RENAMER = "/home/ahonnecke/bin/rename_picure_from_contents.py"
        cmd = [
            RENAMER,
            str(path),
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,  # Capture stdout
            stderr=subprocess.PIPE,  # Capture stderr
        )
        stdout, stderr = proc.communicate()

        if not stdout:
            raise RuntimeError(stderr.decode())

        return stdout.decode().strip()

    def handle_created(self, event):
        file_path = Path(event.src_path).resolve()
        if not file_path.is_file():
            # event was deletion or move
            return

        if file_path.suffix == ".part" or file_path.name.endswith(".part"):
            # Firefox partial download, ignore.
            return

        self.wait_for_file(file_path)

        # Wait for file to stabilize
        historical_size = -1
        while historical_size != os.path.getsize(file_path):
            historical_size = os.path.getsize(file_path)
            time.sleep(1)

        logger.info(f"File {file_path} has stabilized at {historical_size}")

        if historical_size < 1:
            return

        # TODO: make the file handler dynamic
        # TODO: make simple move file behavior dict based
        # ie. return self.handle_{file_path.suffix}

        if file_path.suffix == ".bin":
            os.rename(file_path, f"/home/ahonnecke/qmk/{file_path.name}")
        elif file_path.suffix == ".psarc":
            self.handle_psarc(event)
        elif file_path.suffix.lower() in [
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".bmp",
            ".gif",
        ]:
            if "shot_" == file_path.name.lower()[0:5]:
                ymd = datetime.today().strftime("%Y-%m-%d")
                dirname = os.path.join("/home/ahonnecke/screenshots", ymd)
                Path(dirname).mkdir(parents=True, exist_ok=True)

                new_path = Path(os.path.join(dirname, file_path.name))
                os.rename(file_path, new_path)

                # Screenshot from flameshot
                self.rename_picture_from_contents(new_path)
            else:
                os.rename(
                    file_path, f"/home/ahonnecke/Downloads/images/{file_path.name}"
                )
        # elif file_path.suffix.lower() in [".stl"]:
        #     os.rename(file_path, f"/home/ahonnecke/stl/{file_path.name}")

        for handler in self.file_handlers:
            handler.handle(file_path)


class FileSorter:
    def __init__(self, rules: dict):
        self.rules = rules

    def handle_file(self):
        pass


def ensure_process_is_not_running(process_name: str) -> None:
    mypid = getpid()
    for process in psutil.process_iter():
        if process.pid != mypid:
            try:
                _ = process.cmdline()
            except psutil.NoSuchProcess:
                continue

            for path in _:
                if process_name in path:
                    logger.info("process found, terminating...")
                    process.terminate()


def main():
    """Entrypoint for wayward, file download handler."""

    setproctitle.setproctitle("wayward")
    ensure_process_is_not_running("wayward")
    ROOT = Path.cwd()

    observed = Path("/home/ahonnecke/Downloads/")

    w = Watcher(
        observed,
        Handler(
            file_handlers=[
                FileTypeHandler(
                    file_filter=lambda path: path.suffix == ".stl",
                    file_handler=lambda path: os.rename(
                        path, f"/home/ahonnecke/stl/{path.name}"
                    ),
                ),
            ]
        ),
    )

    w.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    handler = logging.handlers.SysLogHandler(address="/dev/log")
    logger.addHandler(handler)
    with daemon.DaemonContext():
        main()
