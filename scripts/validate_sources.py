#!/usr/bin/env python3
"""Validate the source lock without downloading or changing external state."""

from __future__ import annotations

import json
import pathlib
import re
import sys


SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str) -> None:
    raise SystemExit(f"source lock: FAIL: {message}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("expected path to sources.lock.json")

    path = pathlib.Path(sys.argv[1])
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        fail("unsupported schema")
    if data.get("status") not in {"research", "locked"}:
        fail("status must be research or locked")

    sources = data.get("sources")
    if not isinstance(sources, list):
        fail("sources must be a list")

    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        for field in ("name", "url", "license", "revision"):
            if not isinstance(source.get(field), str) or not source[field]:
                fail(f"{prefix}.{field} is required")
        revision = source["revision"]
        if source.get("revision_type") == "git" and not COMMIT.fullmatch(revision):
            fail(f"{prefix}.revision must be a full Git commit")
        checksum = source.get("sha256")
        if checksum is not None and not SHA256.fullmatch(checksum):
            fail(f"{prefix}.sha256 must be lowercase SHA-256")

    if data["status"] == "locked":
        if data.get("unresolved"):
            fail("locked source file cannot contain unresolved items")
        if not sources:
            fail("locked source file must contain sources")

    print(f"source lock: PASS ({data['status']}, {len(sources)} locked sources)")


if __name__ == "__main__":
    main()

