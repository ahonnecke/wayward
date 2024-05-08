#!/usr/bin/env python3
import argparse
from datetime import datetime
import logging
from os import getpid
from typing import List
import psutil
import os
import re
import subprocess
import time
from pathlib import Path
import setproctitle
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import logging.handlers
import daemon


NAME = "wayward"
logger = logging.getLogger(NAME)


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
        except:  # noqa: E722
            self.observer.stop()
            logger.error("Error")

        self.observer.join()


class FileTypeHandler:
    def __init__(self, file_filter, file_handler):
        self.file_filter = file_filter
        self.file_handler = file_handler

    def __str__(self) -> str:
        return f"{self.__class__.__name__}: {self.file_filter.__name__}"

    def handle(self, path):
        if self.file_filter(path):
            logger.info(f"Handling file... {path} with {self}")
            return self.file_handler(path)

    def sanitize_file(self, current):
        dirname = current.parent.absolute()
        new = Path(re.sub(r"[^\w_. -]", "_", current.name).replace(" ", "_"))
        from_path = Path(f"{dirname}/{current.name}")
        to_path = Path(f"{dirname}/{new}")

        if from_path != to_path:
            logger.info(f"Renaming {from_path} => {to_path}")
            os.rename(from_path, to_path)
            return to_path

    def is_image(self, path) -> bool:
        return path.suffix.lower() in [
            ".png",
            ".jpg",
            ".jpeg",
            ".tiff",
            ".bmp",
            ".gif",
        ]

    def is_screen_shot(self, path) -> bool:
        return self.is_image(path) and "shot_" == path.name.lower()[0:5]

    def rename_picture_from_contents(self, path: Path) -> Path:
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

        return Path(stdout.decode().strip())

    def ocr_picture(self, path: Path):
        OCR_BIN = "/home/ahonnecke/bin/ocr_image.py"
        logger.info(f"OCRing image:{path}")
        cmd = [OCR_BIN, str(path)]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,  # Capture stdout
            stderr=subprocess.PIPE,  # Capture stderr
        )
        stdout, stderr = proc.communicate()

        if not stdout:
            raise RuntimeError(stderr.decode())

        return stdout.decode().strip()


class PsarcHandler(FileTypeHandler):
    def __init__(self):
        self.BUILDSPACE = Path("/home/ahonnecke/cdlc_buildspace")
        self.PYROCKSMITH = Path("/home/ahonnecke/.pyenv/shims/pyrocksmith")

    def file_filter(self, path) -> bool:
        return path.suffix == ".psarc"

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
                subprocess.run(
                    ["scp", filepath, f"{REMOTE_DEST}/{filename}"],
                    stdout=subprocess.PIPE,
                )
                subprocess.run(
                    ["cp", filepath, f"{BACKUP_DEST}/{filename}"],
                    stdout=subprocess.PIPE,
                )
                logger.info(f"Copied {filepath} to remote host {REMOTE_DEST}.")

            os.remove(filepath)
            logger.info(f"Removed {filepath}.")

    def file_handler(self, path):
        file_path = Path(path)

        filename = os.path.basename(file_path)

        fullpath = f"{self.BUILDSPACE}/{filename}"
        os.rename(path, fullpath)
        self.sanitize_psarcs_in_dir(self.BUILDSPACE)
        subprocess.run(
            [self.PYROCKSMITH, "--convert", fullpath],
            stdout=subprocess.PIPE,
        )
        logger.info(f"Processed {fullpath} with pyrocksmith.")
        self.remote_move_cdlc(fullpath)


class ScreenshotHandler(FileTypeHandler):
    def __init__(self):
        self.DEST = Path("/home/ahonnecke/screenshots")

    def file_filter(self, path) -> bool:
        return self.is_screen_shot(path)

    def file_handler(self, path):
        ymd = datetime.today().strftime("%Y-%m-%d")
        dirname = os.path.join(self.DEST, ymd)
        Path(dirname).mkdir(parents=True, exist_ok=True)

        new_path = Path(os.path.join(dirname, path.name))
        os.rename(path, new_path)

        # Screenshot from flameshot
        better_name = self.rename_picture_from_contents(new_path)
        self.ocr_picture(better_name)


class ImageHandler(FileTypeHandler):
    def __init__(self):
        self.DEST = Path("/home/ahonnecke/Downloads/images")

    def file_filter(self, path) -> bool:
        return self.is_image(path) and not self.is_screen_shot(path)

    def file_handler(self, path):
        ymd = datetime.today().strftime("%Y-%m-%d")
        dirname = os.path.join(self.DEST, ymd)
        Path(dirname).mkdir(parents=True, exist_ok=True)

        new_path = Path(os.path.join(dirname, path.name))
        os.rename(path, new_path)


class QmkHandler(FileTypeHandler):
    def __init__(self):
        self.DEST = Path("/home/ahonnecke/qmk/")

    def file_filter(self, path) -> bool:
        # TODO: figure out how to filter for qmk files, not just .bin
        return path.suffix == ".bin"

    def file_handler(self, path):
        return os.rename(path, os.path.join(self.DEST, path.name))


class Handler(FileSystemEventHandler):
    def __init__(self, file_handlers: List[FileTypeHandler]):
        self.file_handlers = file_handlers

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

    def wait_for_file(self, file_path):
        # Wait for file size to stabilize
        historicalSize = -1
        while historicalSize != os.path.getsize(str(file_path)):
            historicalSize = os.path.getsize(str(file_path))
            time.sleep(1)
        return True

    def handle_touchterrain(self, event):
        TOUCH_TERRAIN = Path("/home/ahonnecke/stl/USGS/touchterrain/")
        file_path = Path(event.src_path)

        destination = os.path.join(TOUCH_TERRAIN, os.path.basename(file_path))
        os.rename(event.src_path, destination)

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

        for handler in self.file_handlers:
            handler.handle(file_path)


def ensure_process_is_not_running(process_name: str) -> None:
    mypid = getpid()
    for process in psutil.process_iter():
        if process.pid != mypid:
            try:
                _ = process.cmdline()
            except psutil.NoSuchProcess:
                continue

            for path in _:
                if process_name == path:
                    logger.info("daemon already running, exiting...")
                    exit(-2)


def main():
    """Entrypoint for wayward, file download handler."""

    setproctitle.setproctitle(NAME)
    ensure_process_is_not_running(NAME)

    w = Watcher(
        Path("/home/ahonnecke/Downloads/"),
        Handler(
            file_handlers=[
                ScreenshotHandler(),
                ImageHandler(),
                PsarcHandler(),
                QmkHandler(),
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

    tmphandler = logging.FileHandler(os.path.join("/tmp/", f"{NAME}.log"), "a+")
    logger.addHandler(tmphandler)

    parser = argparse.ArgumentParser(
        description="Watch for new files in a directory and process them accoringly."
    )
    parser.add_argument(
        "--daemon",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run as background daemon.",
    )
    args = parser.parse_args()

    if args.daemon:
        with daemon.DaemonContext():
            main()
    else:
        main()
