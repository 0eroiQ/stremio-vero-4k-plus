#!/usr/bin/env python3
"""Fetch one pinned official Git source into the ignored project cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "upstream"
ALLOWED_REPOSITORIES = {
    "https://github.com/Stremio/stremio-web.git",
    "https://github.com/Stremio/stremio-core.git",
    "https://github.com/Stremio/stremio-linux-shell.git",
    "https://github.com/Stremio/stremio-service.git",
}


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def source_for_name(lock: Path, name: str) -> dict[str, str]:
    data = json.loads(lock.read_text(encoding="utf-8"))
    matches = [source for source in data["sources"] if source["name"] == name]
    if len(matches) != 1:
        raise SystemExit(f"expected one source named {name!r}, found {len(matches)}")
    source = matches[0]
    if source.get("revision_type") != "git":
        raise SystemExit(f"source is not a Git revision: {name}")
    if source["url"] not in ALLOWED_REPOSITORIES:
        raise SystemExit(f"repository is not allowlisted: {source['url']}")
    parsed = urlparse(source["url"])
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise SystemExit("only HTTPS GitHub sources are accepted")
    return source


def fetch(source: dict[str, str], destination: Path) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    resolved = destination.resolve()
    if not resolved.is_relative_to(CACHE.resolve()):
        raise SystemExit(f"destination must stay beneath {CACHE}")

    if not destination.exists():
        run("git", "clone", "--filter=blob:none", "--no-checkout", source["url"], str(destination))
    if not (destination / ".git").is_dir():
        raise SystemExit(f"destination is not a dedicated Git cache: {destination}")
    if run("git", "remote", "get-url", "origin", cwd=destination) != source["url"]:
        raise SystemExit(f"cached origin does not match source lock: {destination}")

    revision = source["revision"]
    run("git", "fetch", "--depth=1", "origin", revision, cwd=destination)
    run("git", "switch", "--detach", revision, cwd=destination)
    actual = run("git", "rev-parse", "HEAD", cwd=destination)
    if actual != revision:
        raise SystemExit(f"Git revision mismatch: expected {revision}, got {actual}")
    print(f"verified Git source: {source['name']} @ {actual}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lock", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()

    destination = CACHE / args.directory
    fetch(source_for_name(args.lock, args.name), destination)


if __name__ == "__main__":
    main()
