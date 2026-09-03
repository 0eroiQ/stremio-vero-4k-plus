#!/usr/bin/env python3
"""Reject device-writing code from the external-boot prototype tree."""

from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {pathlib.Path(__file__).resolve(), ROOT / "docs" / "SAFETY.md"}
TEXT_SUFFIXES = {"", ".md", ".py", ".sh", ".json", ".toml", ".yml", ".yaml"}
FORBIDDEN = {
    "raw block-device path": re.compile(r"/dev/(?:mmcblk|sd[a-z]|disk[0-9]|rdisk[0-9])"),
    "eMMC command": re.compile(r"\b(?:mmc\s+(?:write|erase)|flash_erase|nandwrite)\b"),
    "bootloader write command": re.compile(r"\b(?:fastboot\s+(?:flash|erase)|rkdeveloptool\s+w[blp])\b"),
    "direct dd output": re.compile(r"\bdd\b[^\n]*\bof=/dev/"),
}


def main() -> None:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.resolve() in SKIP or ".git" in path.parts:
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {"Makefile"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            failures.append(f"binary-like tracked input: {path.relative_to(ROOT)}")
            continue
        for label, pattern in FORBIDDEN.items():
            if pattern.search(text):
                failures.append(f"{path.relative_to(ROOT)}: {label}")

    if failures:
        print("safety lint: FAIL")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("safety lint: PASS (no internal-storage write paths found)")


if __name__ == "__main__":
    main()

