#!/usr/bin/env python3
import argparse
from datetime import datetime
import logging
from os import getpid
from typing import List
import psutil
import os
import shutil
import subprocess
import sys
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
        self.observer.schedule(self.event_handler, self.dirpath, recursive=False)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
                if not self.observer.is_alive():
                    logger.error("Observer thread died, restarting...")
                    self.observer = Observer()
                    self.observer.schedule(
                        self.event_handler, self.dirpath, recursive=False
                    )
                    self.observer.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            self.observer.stop()
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
            try:
                return self.file_handler(path)
            except RuntimeError as e:
                logger.error(f"Failed to handle file ({path}) with {self}.")
                logger.exception(e)

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


class PsarcHandler(FileTypeHandler):
    """Ingest a downloaded .psarc into feedBack via the psarc2fb CLI.

    psarc2fb converts the psarc to a .sloppak and POSTs it to feedBack's upload
    API, which writes it into the library and re-indexes. wayward just hands it
    each downloaded psarc and removes the local copy once the upload succeeds.
    """

    def __init__(self):
        from wayward.config import PSARC2FB_DIR, PSARC2FB_PYTHON

        self.PSARC2FB_DIR = Path(PSARC2FB_DIR)
        self.PSARC2FB_PYTHON = Path(PSARC2FB_PYTHON)

    def file_filter(self, path) -> bool:
        return path.suffix == ".psarc"

    def file_handler(self, path):
        src = Path(path)

        result = subprocess.run(
            [str(self.PSARC2FB_PYTHON), "psarc2fb.py", str(src)],
            cwd=str(self.PSARC2FB_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"psarc2fb failed for {src.name} (rc={result.returncode}): {detail}")

        logger.info(f"Ingested {src.name} into feedBack")
        if result.stdout.strip():
            logger.info(result.stdout.strip())
        src.unlink()  # only remove local copy after a successful upload
        logger.info(f"Removed local {src}")


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
        shutil.move(path, new_path)


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
        shutil.move(path, new_path)


class QmkHandler(FileTypeHandler):
    def __init__(self):
        self.DEST = Path("/home/ahonnecke/qmk/")

    def file_filter(self, path) -> bool:
        # TODO: figure out how to filter for qmk files, not just .bin
        return path.suffix == ".bin"

    def file_handler(self, path):
        return shutil.move(path, os.path.join(self.DEST, path.name))


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

    def wait_for_file(self, file_path):
        """Wait for file size to stabilize, return final size."""
        historical_size = -1
        while True:
            try:
                current_size = os.path.getsize(str(file_path))
            except FileNotFoundError:
                return 0
            if current_size == historical_size:
                return historical_size
            historical_size = current_size
            time.sleep(1)

    def handle_created(self, event):
        try:
            file_path = Path(event.src_path).resolve()
            if not file_path.is_file():
                return

            if file_path.suffix == ".part" or file_path.name.endswith(".part"):
                return

            historical_size = self.wait_for_file(file_path)
            logger.info(f"File {file_path} has stabilized at {historical_size}")

            if historical_size < 1:
                return

            for handler in self.file_handlers:
                handler.handle(file_path)
        except Exception as e:
            logger.error(f"Error handling {event.src_path}: {e}")
            logger.exception(e)


def ensure_process_is_not_running(process_name: str) -> None:
    mypid = getpid()
    for process in psutil.process_iter():
        if process.pid != mypid:
            try:
                cmdline = process.cmdline()
            except psutil.NoSuchProcess:
                continue

            for path in cmdline:
                if process_name == path:
                    msg = f"daemon already running (pid {process.pid}), exiting..."
                    logger.info(msg)
                    print(msg, file=sys.stderr)
                    exit(-2)


def setup_logging(foreground=False):
    """Configure logging handlers. Must be called after DaemonContext."""
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.handlers.SysLogHandler(address="/dev/log"))
    logger.addHandler(logging.FileHandler(os.path.join("/tmp/", f"{NAME}.log"), "a+"))

    if foreground:
        logger.addHandler(logging.StreamHandler(sys.stderr))


def run():
    """Watch for file events and dispatch to handlers."""
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
                    file_handler=lambda path: shutil.move(
                        path, f"/home/ahonnecke/stl/{path.name}"
                    ),
                ),
            ]
        ),
    )

    try:
        w.run()
    except RuntimeError as e:
        logger.error("Failed to process file.")
        logger.error(e)


def main():
    """Entrypoint for wayward, file download handler."""
    parser = argparse.ArgumentParser(
        description="Watch for new files in a directory and process them accordingly."
    )
    parser.add_argument(
        "--daemon",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run as background daemon.",
    )
    args = parser.parse_args()

    setproctitle.setproctitle(NAME)
    ensure_process_is_not_running(NAME)

    if args.daemon:
        with daemon.DaemonContext():
            setup_logging()
            run()
    else:
        setup_logging(foreground=True)
        run()
