#!/bin/env python3.11
import argparse
import logging
import os
import sys
from pathlib import Path

import pytesseract

NAME = "ocr_image"
logger = logging.getLogger(NAME)


def generate_ocr_image(image_path: Path, output_path: Path):
    ocr = pytesseract.image_to_string(str(image_path))

    with open(output_path, "w") as f:
        f.write(ocr)
    logger.info(f"OCR saved to {output_path}")


def main(image_path: Path, output_path: Path):
    if not os.path.exists(image_path):
        logger.error(f"{image_path}: file not found")
        return

    return generate_ocr_image(image_path, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate OCR of an image and save it to a file."
    )
    parser.add_argument("image_path", help="Path to image")
    parser.add_argument(
        "--verbose",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Get chatty",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    handler = logging.FileHandler(os.path.join("/tmp/", f"{NAME}.log"), "a+")
    logger.addHandler(handler)

    image_path = Path(args.image_path)

    result = main(image_path, image_path.with_suffix(".ocr.txt"))

    sys.stdout.write(str(result))
