#!/usr/bin/env python3
"""Create and verify the deterministic storage-blind probe initramfs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_ROOT = (ROOT / "out").resolve()
S_IFDIR = 0o040000
S_IFCHR = 0o020000
S_IFREG = 0o100000


def load_sibling(name: str):
    path = pathlib.Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"vero_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load helper: {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_output(path: pathlib.Path) -> pathlib.Path:
    resolved_parent = path.parent.resolve()
    if OUT_ROOT != resolved_parent and OUT_ROOT not in resolved_parent.parents:
        raise ValueError("output must be inside the repository out directory")
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise ValueError("existing output is not a regular file")
    return path


def newc_entry(
    name: str,
    inode: int,
    mode: int,
    data: bytes = b"",
    *,
    links: int = 1,
    rdev_major: int = 0,
    rdev_minor: int = 0,
) -> bytes:
    encoded_name = name.encode("ascii") + b"\0"
    fields = (
        inode,
        mode,
        0,
        0,
        links,
        0,
        len(data),
        0,
        0,
        rdev_major,
        rdev_minor,
        len(encoded_name),
        0,
    )
    header = b"070701" + b"".join(f"{field:08x}".encode("ascii") for field in fields)
    named = header + encoded_name
    named += bytes((-len(named)) % 4)
    return named + data + bytes((-len(data)) % 4)


def build_newc(init: bytes) -> bytes:
    return b"".join(
        (
            newc_entry(".", 1, S_IFDIR | 0o755, links=2),
            newc_entry("dev", 2, S_IFDIR | 0o755, links=2),
            newc_entry(
                "dev/console",
                3,
                S_IFCHR | 0o600,
                rdev_major=5,
                rdev_minor=1,
            ),
            newc_entry("init", 4, S_IFREG | 0o755, init),
            newc_entry("TRAILER!!!", 5, 0),
        )
    )


def deterministic_gzip(blob: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=9) as stream:
        stream.write(blob)
    compressed = output.getvalue()
    if compressed[:3] != b"\x1f\x8b\x08" or compressed[3] != 0 or compressed[9] != 255:
        raise ValueError("initramfs gzip header is not deterministic")
    return compressed


def verify_archive(compressed: bytes, init: bytes, boot_helpers) -> list[dict[str, object]]:
    if compressed != deterministic_gzip(build_newc(init)):
        raise ValueError("initramfs is not the canonical deterministic gzip artifact")
    uncompressed = gzip.decompress(compressed)
    if uncompressed != build_newc(init):
        raise ValueError("initramfs bytes differ from the deterministic four-entry archive")
    entries = boot_helpers.parse_newc(uncompressed)
    expected_names = [".", "dev", "dev/console", "init"]
    if list(entries) != expected_names:
        raise ValueError(f"initramfs entry allowlist mismatch: {list(entries)}")
    expected = {
        ".": {"mode": S_IFDIR | 0o755, "links": 2},
        "dev": {"mode": S_IFDIR | 0o755, "links": 2},
        "dev/console": {
            "mode": S_IFCHR | 0o600,
            "links": 1,
            "rdev_major": 5,
            "rdev_minor": 1,
        },
        "init": {"mode": S_IFREG | 0o755, "links": 1},
    }
    manifest_entries: list[dict[str, object]] = []
    for name in expected_names:
        entry = entries[name]
        for key, value in expected[name].items():
            if entry.get(key) != value:
                raise ValueError(f"unsafe initramfs metadata for {name}: {key}")
        if entry.get("uid") != 0 or entry.get("gid") != 0 or entry.get("mtime") != 0:
            raise ValueError(f"non-deterministic initramfs ownership/time for {name}")
        data = entry["data"]
        if not isinstance(data, bytes):
            raise ValueError(f"invalid initramfs data for {name}")
        if name == "init" and data != init:
            raise ValueError("initramfs /init differs from the verified probe binary")
        if name != "init" and data:
            raise ValueError(f"initramfs metadata entry unexpectedly has data: {name}")
        manifest_entries.append(
            {
                "path": f"/{name}" if name != "." else "/",
                "mode": f"0o{entry['mode']:06o}",
                "size": len(data),
                **(
                    {"device": "char 5:1"}
                    if name == "dev/console"
                    else {}
                ),
            }
        )
    return manifest_entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    output = safe_output(
        (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output
    )
    init_path = (ROOT / args.init).resolve() if not args.init.is_absolute() else args.init.resolve()
    if OUT_ROOT != init_path.parent and OUT_ROOT not in init_path.parents:
        raise ValueError("probe init input must be inside the repository out directory")
    init = init_path.read_bytes()

    init_helpers = load_sibling("build_probe_init")
    boot_helpers = load_sibling("inspect_boot_image")
    init_details = init_helpers.verify_probe_elf(init)
    first = deterministic_gzip(build_newc(init))
    second = deterministic_gzip(build_newc(init))
    if first != second:
        raise ValueError("probe initramfs is not reproducible")
    entries = verify_archive(first, init, boot_helpers)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(first)
    manifest = {
        "schema": 1,
        "artifact": output.name,
        "sha256": sha256_bytes(first),
        "format": "gzip+newc",
        "init_sha256": init_details["sha256"],
        "entries": entries,
        "storage_access": "none",
        "physical_boot_tested": False,
    }
    output.with_suffix(output.suffix + ".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"storage-blind initramfs: PASS ({manifest['sha256']})")
    print("archive allowlist: /, /dev, /dev/console, /init")
    print("physical boot status: NOT TESTED")


if __name__ == "__main__":
    main()
