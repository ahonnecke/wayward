#!/bin/env python
import argparse
import collections
from hmac import new
import subprocess
import os
from typing import Tuple


def is_good_fileword(word: str) -> bool:
    _word = word.lower().replace("...", "")
    if _word in ["the", "image", "has"]:
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

    GRAMMAR = "root ::= [a-z]+ ([a-z]+)+"

    cmd = [
        "/bin/bash",
        LLAVA,
        "--image",
        path,
        "--temp",
        "0.2",
        "-ngl",
        "0",
        "-n",
        "10",
        "-p",
        "'### User: The image has...\n### Assistant:'",
        "--silent-prompt",
        "--simple-io",
        "--log-disable",
    ]
    print(" ".join(cmd))

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


def main(raw_path):
    filepath = os.path.abspath(raw_path)
    if not os.path.exists(filepath):
        print(f"{filepath}: file not found")
        return

    newname, desription = llm_generate_image_description(filepath)

    if newname:
        newname = newname.split(".")[0].replace(" ", "_")
        newname += f".{filepath.split('.')[-1]}"
        newpath = os.path.join(os.path.dirname(filepath), newname)
        print(newpath)

    print(newname)

    if newpath != filepath:
        print(f"Renaming {filepath} to {newpath}")
        os.rename(filepath, newpath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rename pictures using LLAVA and Mistral models"
    )
    parser.add_argument("path", help="Paths to file")
    args = parser.parse_args()
    main(args.path)
