"""Streaming readers: one line at a time, the file is never loaded completely."""

from collections.abc import Iterator
from itertools import chain
from pathlib import Path


def read_lines(path: Path) -> Iterator[str]:
    """Yield lines of a text file lazily; the file stays open until iteration ends."""
    with path.open(encoding="utf-8", newline="") as file:
        yield from file


def read_data_lines(path: Path) -> Iterator[str]:
    """Yield lines without the CSV header."""
    lines = read_lines(path)
    next(lines, None)  # skip header
    yield from lines


def read_many(*paths: Path) -> Iterator[str]:
    """Concatenate several files into one stream with itertools.chain."""
    return chain.from_iterable(read_data_lines(path) for path in paths)
