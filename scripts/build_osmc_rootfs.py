#!/usr/bin/env python3
"""Overlay Stremio for Vero services onto the official OSMC rootfs archive."""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def safe_archive_name(name: str) -> str:
    normalized = name.removeprefix("./")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe archive path: {name!r}")
    return path.as_posix()


def load_manifest(path: Path) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    files = list(data.get("files", []))
    symlinks = data.get("symlinks", [])
    trees = data.get("trees", [])
    if not isinstance(files, list) or not isinstance(symlinks, list) or not isinstance(trees, list):
        raise ValueError("overlay manifest requires files, trees and symlinks lists")
    for tree in trees:
        source_root = (ROOT / str(tree["source"])).resolve()
        target_root = safe_archive_name(str(tree["target"]))
        if not source_root.is_relative_to(ROOT.resolve()) or not source_root.is_dir():
            raise ValueError(f"invalid overlay tree: {tree.get('source')}")
        mode = str(tree.get("fileMode", "0644"))
        int(mode, 8)
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            if source.is_symlink():
                raise ValueError(f"overlay tree contains a symlink: {source}")
            relative = source.relative_to(source_root).as_posix()
            files.append({
                "source": source.relative_to(ROOT).as_posix(),
                "target": f"{target_root}/{relative}",
                "mode": mode,
            })
    for entry in files:
        source = (ROOT / str(entry["source"])).resolve()
        if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
            raise ValueError(f"invalid overlay source: {entry.get('source')}")
        safe_archive_name(str(entry["target"]))
        int(str(entry["mode"]), 8)
    for entry in symlinks:
        safe_archive_name(entry["target"])
        link = PurePosixPath(entry["link"])
        if link.is_absolute():
            raise ValueError(f"absolute overlay symlink is not allowed: {link}")
    return files, symlinks


def parent_directories(paths: set[str]) -> list[str]:
    directories: set[str] = set()
    for value in paths:
        parent = PurePosixPath(value).parent
        while parent != PurePosixPath("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return sorted(directories, key=lambda value: (value.count("/"), value))


def add_directory(archive: tarfile.TarFile, name: str) -> None:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    info.mode = 0o755
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = 0
    archive.addfile(info)


def build(base: Path, manifest_path: Path, output: Path) -> dict[str, object]:
    if base.is_symlink() or not base.is_file():
        raise SystemExit(f"base rootfs must be a regular archive: {base}")
    if output.resolve() == OUT.resolve() or not output.resolve().is_relative_to(OUT.resolve()):
        raise SystemExit(f"output must be a file beneath {OUT}")
    files, symlinks = load_manifest(manifest_path)
    replacements = {safe_archive_name(str(entry["target"])) for entry in files}
    replacements.update(safe_archive_name(entry["target"]) for entry in symlinks)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(prefix="rootfs-", suffix=".tar.xz", dir=output.parent, delete=False) as temp:
        temporary = Path(temp.name)
    copied = 0
    skipped = 0
    seen_directories: set[str] = set()
    try:
        with tarfile.open(base, "r:xz") as source, tarfile.open(temporary, "w:xz") as target:
            for member in source:
                name = safe_archive_name(member.name)
                if member.isdir():
                    seen_directories.add(name)
                if name in replacements:
                    skipped += 1
                    continue
                payload = source.extractfile(member) if member.isfile() else None
                target.addfile(copy.copy(member), payload)
                copied += 1

            missing_parents = set(parent_directories(replacements)) - seen_directories
            for directory in sorted(missing_parents, key=lambda value: (value.count("/"), value)):
                add_directory(target, directory)

            for entry in files:
                source_path = ROOT / str(entry["source"])
                payload = source_path.read_bytes()
                info = tarfile.TarInfo(safe_archive_name(str(entry["target"])))
                info.size = len(payload)
                info.mode = int(str(entry["mode"]), 8)
                info.uid = 0
                info.gid = 0
                info.uname = "root"
                info.gname = "root"
                info.mtime = 0
                target.addfile(info, io.BytesIO(payload))

            for entry in symlinks:
                info = tarfile.TarInfo(safe_archive_name(entry["target"]))
                info.type = tarfile.SYMTYPE
                info.linkname = entry["link"]
                info.mode = 0o777
                info.uid = 0
                info.gid = 0
                info.uname = "root"
                info.gname = "root"
                info.mtime = 0
                target.addfile(info)
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)

    report = {
        "base": str(base),
        "baseSha256": digest(base),
        "output": str(output),
        "outputSha256": digest(output),
        "copiedEntries": copied,
        "replacedEntries": skipped,
        "addedFiles": [entry["target"] for entry in files],
        "addedSymlinks": [entry["target"] for entry in symlinks],
    }
    report_path = output.with_suffix(output.suffix + ".json")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "rootfs-overlay" / "manifest.json")
    parser.add_argument("--output", type=Path, default=OUT / "rootfs" / "filesystem.tar.xz")
    args = parser.parse_args()
    build(args.base, args.manifest, args.output)


if __name__ == "__main__":
    main()
