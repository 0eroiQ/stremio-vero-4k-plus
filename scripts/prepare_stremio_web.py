#!/usr/bin/env python3
"""Create a reviewable Stremio Web source tree with the Vero overlay."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
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


def copy_source(source: Path, output: Path) -> None:
    jobs: list[tuple[Path, Path]] = []
    for directory, names, files in os.walk(source):
        names[:] = [name for name in names if name not in IGNORED_SOURCE_PARTS]
        source_directory = Path(directory)
        relative = source_directory.relative_to(source)
        target_directory = output / relative
        target_directory.mkdir(parents=True, exist_ok=True)
        for name in files:
            if name in IGNORED_SOURCE_PARTS:
                continue
            jobs.append((source_directory / name, target_directory / name))

    def copy_one(job: tuple[Path, Path]) -> None:
        source_path, target_path = job
        if source_path.is_symlink():
            target_path.symlink_to(os.readlink(source_path))
        else:
            shutil.copy2(source_path, target_path)

    with ThreadPoolExecutor(max_workers=min(16, max(1, len(jobs)))) as executor:
        list(executor.map(copy_one, jobs))


def prepare(source: Path, overlay: Path, output: Path, revision: str) -> None:
    if git_head(source) != revision:
        raise SystemExit(f"Stremio Web checkout is not pinned to {revision}")
    if not overlay.is_dir():
        raise SystemExit(f"overlay directory is missing: {overlay}")
    if output.resolve() == OUT.resolve() or not output.resolve().is_relative_to(OUT.resolve()):
        raise SystemExit(f"output must stay beneath {OUT}")
    if output.exists():
        shutil.rmtree(output)

    copy_source(source, output)
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
