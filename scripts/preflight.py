#!/usr/bin/env python3
"""Check build prerequisites without installing or changing the host."""

from __future__ import annotations

import argparse
import pathlib
import platform
import shutil


ROOT = pathlib.Path(__file__).resolve().parents[1]
PROFILES = {
    "kernel": {"free_gib": 20, "tools": ("git", "python3")},
    "osmc": {"free_gib": 4, "tools": ("git", "python3", "node")},
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=PROFILES, required=True)
    args = parser.parse_args()
    profile = PROFILES[args.profile]

    failures: list[str] = []
    free = shutil.disk_usage(ROOT).free
    required = profile["free_gib"] * 1024**3
    if free < required:
        failures.append(
            f"free storage is {free / 1024**3:.1f} GiB; "
            f"{args.profile} build requires at least {profile['free_gib']} GiB"
        )
    for tool in profile["tools"]:
        if shutil.which(tool) is None:
            failures.append(f"required tool is missing: {tool}")

    print(f"host: {platform.system()} {platform.machine()}")
    if failures:
        print(f"{args.profile} preflight: BLOCKED")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(2)
    print(f"{args.profile} preflight: PASS")


if __name__ == "__main__":
    main()
