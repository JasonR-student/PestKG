from __future__ import annotations

import csv
import gzip
import io
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO, TextIO


def archive_names(archive: Path) -> list[str]:
    result = subprocess.run(
        ["tar", "-tf", str(archive)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


class ArchiveStream:
    def __init__(self, archive: Path, member: str) -> None:
        self.process = subprocess.Popen(
            ["tar", "-xOf", str(archive), member],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if self.process.stdout is None:
            raise RuntimeError(f"Unable to read archive member: {member}")
        self.binary: BinaryIO = self.process.stdout

    def close(self) -> None:
        self.binary.close()
        return_code = self.process.wait()
        if return_code not in {0, -15, 1}:
            raise RuntimeError(f"tar exited with code {return_code}")

    def __enter__(self) -> BinaryIO:
        return self.binary

    def __exit__(self, *_: object) -> None:
        self.close()


def open_text(archive: Path, member: str, gzipped: bool = False) -> tuple[ArchiveStream, TextIO]:
    stream = ArchiveStream(archive, member)
    binary: BinaryIO
    if gzipped:
        binary = gzip.GzipFile(fileobj=stream.binary)
    else:
        binary = stream.binary
    return stream, io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")


def read_json(archive: Path, member: str) -> Any:
    stream, text = open_text(archive, member)
    try:
        return json.load(text)
    finally:
        text.close()
        stream.close()


def read_csv_rows(archive: Path, member: str, gzipped: bool = False) -> Iterator[dict[str, str]]:
    stream, text = open_text(archive, member, gzipped=gzipped)
    try:
        yield from csv.DictReader(text)
    finally:
        text.close()
        stream.close()
