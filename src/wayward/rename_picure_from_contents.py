#!/bin/env python3.11
import argparse
import collections
import logging
from logging.handlers import SysLogHandler
import subprocess
import os
import sys
from typing import Tuple

NAME = "rename_picture_from_contents"
logger = logging.getLogger(NAME)


def is_good_fileword(word: str) -> bool:
    _word = word.lower().replace("...", "")
    if _word in [
        "the",
        "image",
        "has",
        "for",
        "and",
        "with",
        "from",
        "this",
        "that",
        "and",
        "but",
        "not",
        "are",
        "you",
        "your",
        "our",
        "all",
        "any",
        "can",
        "may",
        "will",
        "was",
        "were",
        "has",
        "had",
        "have",
        "been",
        "being",
        "does",
        "did",
        "doing",
        "done",
        ",",
        ".",
        '"',
    ]:
        return False
    if len(_word) < 3:
        return False
    return True


def llm_generate_image_description(path) -> Tuple[str, str]:
    LLAVA = "/home/ahonnecke/local/bin/llava-v1.5-7b-q4.llamafile"

    if not os.path.exists(LLAVA):
        raise RuntimeError(
            f"{LLAVA} not found. Please download and specify the correct path."
        )

    TEMP = 0.2
    NGL = 999
    TOKENS = 64
    cmd = [
        "/bin/bash",
        LLAVA,
        "--image",
        path,
        "--temp",
        str(TEMP),
        "-ngl",
        str(NGL),
        "-n",
        str(TOKENS),
        "-p",
        "'### User: The image has...\n### Assistant:'",
        "--silent-prompt",
        "--simple-io",
        "--log-disable",
    ]
    logger.debug("\n\n--------------------------------------------------")
    logger.debug(" \\\n".join(cmd))
    logger.debug("--------------------------------------------------\n\n")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,  # Capture stdout
        stderr=subprocess.PIPE,  # Capture stderr
    )
    stdout, stderr = proc.communicate()

    if not stdout:
        raise RuntimeError(stderr.decode())

    description = stdout.decode().strip()
    words = [x for x in description.split(" ") if is_good_fileword(x)]
    sorted = collections.Counter(words).most_common()
    unzipped = [x for x, y in sorted]

    return ("_".join(unzipped), description)


def main(args) -> str | None:
    raw_path = args.path
    filepath = os.path.abspath(raw_path)
    if not os.path.exists(filepath):
        logger.debug(f"{filepath}: file not found")
        return

    newname, description = llm_generate_image_description(filepath)
    newpath = False

    if newname:
        newname = newname.split(".")[0].replace(" ", "_")
        newname += f".{filepath.split('.')[-1]}"
        newpath = os.path.join(os.path.dirname(filepath), newname)
        logger.debug(newpath)

    if newpath and newpath != filepath:
        logger.debug(f"Renaming {filepath} to {newpath}")
        os.rename(filepath, newpath)

    if args.description:
        # Write the contents to a file
        description_file = f"{newpath}.txt"
        logger.debug(f"Writing description: {description} to ({description_file})")
        with open(description_file, "w") as f:
            f.write(description)

    return str(newpath)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    handler = SysLogHandler(address="/dev/log")
    logger.addHandler(handler)

    tmphandler = logging.FileHandler(os.path.join("/tmp/", f"{NAME}.log"), "a+")
    logger.addHandler(tmphandler)

    parser = argparse.ArgumentParser(
        description="Rename pictures using LLAVA and Mistral models"
    )
    parser.add_argument("path", help="Paths to file")
    parser.add_argument(
        "--description",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create a text file with the full description of the image.",
    )
    args = parser.parse_args()
    try:
        if out := main(args):
            sys.stdout.write(out)
    except RuntimeError as e:
        logger.error("Failed to rename picture.")
        logger.exception(e)
