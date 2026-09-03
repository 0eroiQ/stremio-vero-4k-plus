#!/usr/bin/env python3
"""Fetch explicitly checksummed official inputs into the ignored cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import tempfile
import urllib.parse
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "downloads"
ALLOWED_HOSTS = {
    "apt.osmc.tv",
    "dl.strem.io",
    "ftp.fau.de",
    "johnvansickle.com",
    "nodejs.org",
}


def digest(path: pathlib.Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def safe_name(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"host is not allowlisted: {url}")
    name = pathlib.PurePosixPath(parsed.path).name
    if not name or name in {".", ".."}:
        raise ValueError(f"URL has no safe filename: {url}")
    return name


def fetch(source: dict[str, str]) -> None:
    expected = source["sha256"]
    target = CACHE / safe_name(source["url"])
    if target.exists() and digest(target) == expected:
        print(f"verified cached input: {target.name}")
        return

    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=CACHE, prefix="download-", delete=False) as temp:
        temporary = pathlib.Path(temp.name)
        try:
            with urllib.request.urlopen(source["url"], timeout=60) as response:
                while block := response.read(1024 * 1024):
                    temp.write(block)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    actual = digest(temporary)
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise SystemExit(
            f"checksum mismatch for {source['name']}: expected {expected}, got {actual}"
        )
    temporary.replace(target)
    print(f"downloaded and verified: {target.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lock", type=pathlib.Path)
    parser.add_argument("--name", help="fetch one exact source name")
    args = parser.parse_args()

    data = json.loads(args.lock.read_text(encoding="utf-8"))
    sources = [source for source in data["sources"] if "sha256" in source]
    if args.name:
        sources = [source for source in sources if source["name"] == args.name]
        if not sources:
            raise SystemExit(f"no checksummed source named: {args.name}")
    for source in sources:
        fetch(source)


if __name__ == "__main__":
    main()
