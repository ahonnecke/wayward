#!/usr/bin/env python3
import logging
import os
import shutil
import time
from functools import cached_property
from pathlib import Path

import boto3
import requests
from argdantic import ArgParser
from botocore.exceptions import ClientError
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

    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None

        elif event.event_type == "created":
            # Take any action here when a file is first created.
            print(f"Received created event - {event.src_path}.")

        elif event.event_type == "modified":
            # Taken any action here when a file is modified.
            print(f"Received modified event - {event.src_path}.")

        onchange()


class LambdaWrapper:
    def __init__(self, profile_name, function_name, local_root):
        self.profile_name = profile_name
        self.function_name = function_name
        self.local_root = local_root

    @cached_property
    def session(self):
        return boto3.Session(profile_name=self.profile_name)

    @cached_property
    def lambda_client(self):
        return self.session.client("lambda")


class LambdaReloader(LambdaWrapper):
    @property
    def archive(self):
        return ".".join([self.function_name, "zip"])

    def is_downloaded(self):
        return os.path.isdir(self.function_name)

    def download_function_code(self):
        response = self.lambda_client.get_function(FunctionName=self.function_name)
        zip_url = response["Code"]["Location"]

        r = requests.get(zip_url, allow_redirects=True)
        open(self.archive, "wb").write(r.content)

        shutil.unpack_archive(self.archive, self.function_name)

    def update_function_code(self):
        """
        Updates the code for a Lambda function by submitting a .zip archive that contains
        the code for the function.

        :param deployment_package: The function code to update, packaged as bytes in
                                   .zip format.
        :return: Data about the update, including the status.
        """
        deployment_package = self.make_archive(self.function_name)

        try:
            response = self.lambda_client.update_function_code(
                FunctionName=self.function_name, ZipFile=deployment_package
            )
        except ClientError as err:
            logger.error(
                "Couldn't update function %s. Here's why: %s: %s",
                self.function_name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return response

    def make_archive(self, name):
        shutil.make_archive(name, "zip", name)
        with open(self.archive, "rb") as file_data:
            return file_data.read()


parser = ArgParser()


@parser.command()
def main(
    profile_name: str,
    function_name: str,
    hot_reload: bool = False,
):
    """Entrypoint for AWS lambda hot reloader, CLI args in signature."""
    ROOT = Path.cwd()

    PROFILE = profile_name

    reloader = LambdaReloader(PROFILE, function_name, ROOT)

    # TODO: perform the download and compare
    if not reloader.is_downloaded():
        # If there no code, then the user likely wants to download the lambda
        reloader.download_function_code()
    elif hot_reload:
        pass
        # # If there IS code, then the user likely wants to upload the lambda
        # # TODO: implement dir watching
        # project = ROOT + function_name

        # w = Watcher(project, Handler(onchange = reloader.update_function_code(function_name)))
        # w.run()

    elif not hot_reload:
        reloader.update_function_code()


if __name__ == "__main__":
    parser()
