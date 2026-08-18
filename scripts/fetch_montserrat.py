#!/usr/bin/env python3
"""Fetch the pinned Montserrat inputs used by the proof and audits."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path
from typing import NamedTuple


MONTSERRAT_VERSION = "9.000"
DEFAULT_OUTPUT_DIR = Path("vendor/montserrat")


class DownloadSpec(NamedTuple):
    filename: str
    url: str
    sha256: str


SOURCES = (
    DownloadSpec(
        "Montserrat-VariableFont_wght.ttf",
        "https://fonts.gstatic.com/s/montserrat/v31/"
        "JTUSjIg1_i6t8kCHKm45xW5rygbi49c.ttf",
        "498dc34d0fa45288e0ac5345bd385c98bf81c56ee70209aacfb4a22a6510697c",
    ),
    DownloadSpec(
        "Montserrat-Italic-VariableFont_wght.ttf",
        "https://fonts.gstatic.com/s/montserrat/v31/"
        "JTUQjIg1_i6t8kCHKm459WxhziTn89dtpQ.ttf",
        "225da7d3255aaac9ab6bef71bf27ccbfab0b65a58a6b0a3d5c14c26cdd988691",
    ),
    DownloadSpec(
        "OFL.txt",
        "https://raw.githubusercontent.com/google/fonts/"
        "76fca9fd0bb4ea46583f92e978660f3984ab9442/"
        "ofl/montserrat/OFL.txt",
        "8b7141c03fa4f8d44e6345d5d4931709290f0f67875e452e95ac1fd3a027802e",
    ),
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_source(source: DownloadSpec, output_dir: Path) -> bool:
    destination = output_dir / source.filename
    if destination.is_file() and file_sha256(destination) == source.sha256:
        print(f"Using verified Montserrat input: {destination}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{source.filename}.",
        dir=output_dir,
    )
    temporary_path = Path(temporary_name)
    digest = hashlib.sha256()
    try:
        print(f"Downloading {source.url}")
        with os.fdopen(file_descriptor, "wb") as destination_file:
            with urllib.request.urlopen(source.url, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    destination_file.write(chunk)
                    digest.update(chunk)

        actual_sha256 = digest.hexdigest()
        if actual_sha256 != source.sha256:
            raise RuntimeError(
                f"Checksum mismatch for {source.filename}: "
                f"expected {source.sha256}, got {actual_sha256}"
            )
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Fetch the pinned Montserrat {MONTSERRAT_VERSION} inputs."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    for source in SOURCES:
        fetch_source(source, args.output_dir)
    print(f"Montserrat {MONTSERRAT_VERSION} is ready in {args.output_dir}")


if __name__ == "__main__":
    main()
