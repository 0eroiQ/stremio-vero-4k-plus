#!/usr/bin/env python3
"""Create a reviewable Stremio Web source tree with the Vero overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
IGNORED_SOURCE_PARTS = {".git", "build", "dist", "node_modules"}


def git_head(source: Path) -> str:
    result = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=source,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def ignored(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_SOURCE_PARTS}


def prepare(source: Path, overlay: Path, output: Path, revision: str) -> None:
    if git_head(source) != revision:
        raise SystemExit(f"Stremio Web checkout is not pinned to {revision}")
    if not overlay.is_dir():
        raise SystemExit(f"overlay directory is missing: {overlay}")
    if output.resolve() == OUT.resolve() or not output.resolve().is_relative_to(OUT.resolve()):
        raise SystemExit(f"output must stay beneath {OUT}")
    if output.exists():
        shutil.rmtree(output)

    shutil.copytree(source, output, ignore=ignored, symlinks=True)
    overlay_files: list[dict[str, str]] = []
    for source_path in sorted(path for path in overlay.rglob("*") if path.is_file()):
        relative = source_path.relative_to(overlay)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        overlay_files.append({"path": relative.as_posix(), "sha256": digest(source_path)})

    manifest = {
        "product": "Stremio for Vero 4K+",
        "upstream": "https://github.com/Stremio/stremio-web.git",
        "revision": revision,
        "overlayFiles": overlay_files,
    }
    (output / "stremio-vero-source-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"prepared Stremio Web source: {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--overlay", type=Path, default=ROOT / "web-overlay")
    parser.add_argument("--output", type=Path, default=OUT / "stremio-web-src")
    parser.add_argument("--expected-commit", required=True)
    args = parser.parse_args()
    prepare(args.source, args.overlay, args.output, args.expected_commit)


if __name__ == "__main__":
    main()
