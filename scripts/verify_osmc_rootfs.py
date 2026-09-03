#!/usr/bin/env python3
"""Prove that a derived OSMC rootfs differs only by its declared overlay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tarfile

import build_osmc_rootfs as overlay


def stream_digest(stream) -> str:
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        result.update(block)
    return result.hexdigest()


def comparable(member: tarfile.TarInfo) -> tuple[object, ...]:
    return (
        overlay.safe_archive_name(member.name),
        member.type,
        member.mode,
        member.uid,
        member.gid,
        member.uname,
        member.gname,
        member.size,
        member.mtime,
        member.linkname,
    )


def verify(base: Path, derived: Path, manifest: Path) -> dict[str, object]:
    files, symlinks = overlay.load_manifest(manifest)
    replacement_names = {overlay.safe_archive_name(str(entry["target"])) for entry in files}
    replacement_names.update(overlay.safe_archive_name(entry["target"]) for entry in symlinks)
    expected_files = {
        overlay.safe_archive_name(str(entry["target"])): ROOT / str(entry["source"])
        for entry in files
    }
    expected_links = {
        overlay.safe_archive_name(entry["target"]): entry["link"]
        for entry in symlinks
    }

    base_count = 0
    unchanged_count = 0
    base_directories: set[str] = set()
    with tarfile.open(base, "r:xz") as original, tarfile.open(derived, "r:xz") as candidate:
        candidate_iterator = iter(candidate)
        for base_member in original:
            base_count += 1
            base_name = overlay.safe_archive_name(base_member.name)
            if base_member.isdir():
                base_directories.add(base_name)
            if base_name in replacement_names:
                continue
            try:
                derived_member = next(candidate_iterator)
            except StopIteration as error:
                raise ValueError("derived rootfs ended before the OSMC base") from error
            if comparable(base_member) != comparable(derived_member):
                raise ValueError(
                    f"undeclared rootfs difference: {base_member.name!r} != {derived_member.name!r}"
                )
            if base_member.isfile():
                base_payload = original.extractfile(base_member)
                derived_payload = candidate.extractfile(derived_member)
                if base_payload is None or derived_payload is None:
                    raise ValueError(f"unable to read regular file: {base_name}")
                if stream_digest(base_payload) != stream_digest(derived_payload):
                    raise ValueError(f"undeclared file content change: {base_name}")
            unchanged_count += 1

        expected_directories = set(overlay.parent_directories(replacement_names)) - base_directories
        expected_additions = expected_directories | set(expected_files) | set(expected_links)
        observed: set[str] = set()
        for member in candidate_iterator:
            name = overlay.safe_archive_name(member.name)
            if name in observed or name not in expected_additions:
                raise ValueError(f"undeclared or duplicate overlay entry: {name}")
            observed.add(name)
            if name in expected_directories:
                if not member.isdir():
                    raise ValueError(f"expected overlay directory: {name}")
            elif name in expected_links:
                if not member.issym() or member.linkname != expected_links[name]:
                    raise ValueError(f"overlay symlink mismatch: {name}")
            else:
                if not member.isfile():
                    raise ValueError(f"expected overlay regular file: {name}")
                payload = candidate.extractfile(member)
                if payload is None or stream_digest(payload) != overlay.digest(expected_files[name]):
                    raise ValueError(f"overlay file content mismatch: {name}")

    missing = sorted(expected_additions - observed)
    if missing:
        raise ValueError(f"derived rootfs is missing overlay entries: {', '.join(missing)}")

    report = {
        "status": "PASS",
        "baseEntries": base_count,
        "unchangedBaseEntries": unchanged_count,
        "declaredOverlayEntries": len(observed),
        "baseSha256": overlay.digest(base),
        "derivedSha256": overlay.digest(derived),
        "kodiAutostartOverridePresent": "etc/systemd/system/mediacenter.service.d/10-stremio-vero.conf" in observed,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "rootfs-overlay" / "manifest.json")
    args = parser.parse_args()
    verify(args.base, args.derived, args.manifest)


if __name__ == "__main__":
    main()
