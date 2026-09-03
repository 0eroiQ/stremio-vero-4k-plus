#!/usr/bin/env python3
"""Reject Stremio Web builds labeled with any commit except the source lock."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


COMMIT_PATH = re.compile(rb"(?<![0-9a-f])([0-9a-f]{40})/(?:scripts|styles|binaries)/")


def verify(build: Path, expected_commit: str) -> set[str]:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("expected commit must be a lowercase 40-character Git hash")
    index = build / "index.html"
    if not index.is_file():
        raise ValueError(f"Stremio Web index is missing: {index}")
    commits = {match.decode("ascii") for match in COMMIT_PATH.findall(index.read_bytes())}
    if commits != {expected_commit}:
        raise ValueError(
            f"Stremio Web build is labeled with {sorted(commits)}, expected {expected_commit}"
        )
    commit_directory = build / expected_commit
    for relative in ("scripts/main.js", "styles/main.css", "binaries/stremio_core_web_bg.wasm"):
        if not (commit_directory / relative).is_file():
            raise ValueError(f"expected Stremio Web asset is missing: {relative}")
    print(f"Stremio Web build commit: PASS ({expected_commit})")
    return commits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    verify(args.build, args.expected_commit)


if __name__ == "__main__":
    main()
