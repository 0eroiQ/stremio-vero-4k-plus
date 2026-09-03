#!/usr/bin/env python3
"""Inspect the official Vero Android boot image without extracting it to disk."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import struct


ANDROID_MAGIC = b"ANDROID!"
GZIP_MAGIC = b"\x1f\x8b"
AML_MAGIC = b"AML_"
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_ROOT = (ROOT / "out").resolve()


def load_artifact_helpers():
    helper_path = pathlib.Path(__file__).with_name("build_safe_dtb.py")
    spec = importlib.util.spec_from_file_location("vero_artifact_helpers", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Vero artifact helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def align(value: int, boundary: int) -> int:
    return ((value + boundary - 1) // boundary) * boundary


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_output(path: pathlib.Path) -> pathlib.Path:
    resolved_parent = path.parent.resolve()
    if OUT_ROOT != resolved_parent and OUT_ROOT not in resolved_parent.parents:
        raise ValueError("output must be inside the repository out directory")
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise ValueError("existing output is not a regular file")
    return path


def parse_boot_image(blob: bytes) -> dict[str, object]:
    if len(blob) < 1648 or not blob.startswith(ANDROID_MAGIC):
        raise ValueError("input is not a supported Android boot image")
    values = struct.unpack_from("<10I", blob, 8)
    (
        kernel_size,
        kernel_address,
        ramdisk_size,
        ramdisk_address,
        second_size,
        second_address,
        tags_address,
        page_size,
        header_version,
        os_version,
    ) = values
    if header_version != 1:
        raise ValueError(f"expected Android boot header v1, got {header_version}")
    header_size = struct.unpack_from("<I", blob, 1644)[0]
    if header_size != 1648:
        raise ValueError(f"unexpected Android boot header size: {header_size}")
    if page_size < 2048 or page_size & (page_size - 1):
        raise ValueError(f"invalid Android boot page size: {page_size}")

    kernel_offset = page_size
    ramdisk_offset = kernel_offset + align(kernel_size, page_size)
    second_offset = ramdisk_offset + align(ramdisk_size, page_size)
    recovery_size = struct.unpack_from("<I", blob, 1632)[0]
    recovery_offset = struct.unpack_from("<Q", blob, 1636)[0]
    expected_end = second_offset + align(second_size, page_size)
    if recovery_size:
        expected_end += align(recovery_size, page_size)
    if expected_end > len(blob):
        raise ValueError("Android boot components exceed the input size")

    kernel = blob[kernel_offset : kernel_offset + kernel_size]
    ramdisk = blob[ramdisk_offset : ramdisk_offset + ramdisk_size]
    second = blob[second_offset : second_offset + second_size]
    if not kernel.startswith(GZIP_MAGIC):
        raise ValueError("Vero kernel component is not gzip-compressed")
    if not ramdisk.startswith(GZIP_MAGIC):
        raise ValueError("Vero ramdisk component is not gzip-compressed")
    if not second.startswith(AML_MAGIC):
        raise ValueError("Vero second component is not an Amlogic multi-DTB")

    name = blob[48:64].split(b"\0", 1)[0].decode("ascii")
    command_line = (blob[64:576] + blob[608:1632]).split(b"\0", 1)[0]
    return {
        "header": {
            "version": header_version,
            "size": header_size,
            "page_size": page_size,
            "os_version": os_version,
            "name": name,
            "command_line": command_line.decode("ascii"),
            "kernel_address": f"0x{kernel_address:08x}",
            "ramdisk_address": f"0x{ramdisk_address:08x}",
            "second_address": f"0x{second_address:08x}",
            "tags_address": f"0x{tags_address:08x}",
            "recovery_dtbo_size": recovery_size,
            "recovery_dtbo_offset": recovery_offset,
        },
        "kernel": kernel,
        "ramdisk": ramdisk,
        "second": second,
    }


def parse_newc(blob: bytes) -> dict[str, dict[str, object]]:
    entries: dict[str, dict[str, object]] = {}
    cursor = 0
    while cursor + 110 <= len(blob):
        header = blob[cursor : cursor + 110]
        if header[:6] not in (b"070701", b"070702"):
            raise ValueError(f"invalid newc header at byte {cursor}")
        try:
            values = [int(header[index : index + 8], 16) for index in range(6, 110, 8)]
        except ValueError as error:
            raise ValueError("invalid hexadecimal newc field") from error
        mode = values[1]
        file_size = values[6]
        name_size = values[11]
        if name_size < 1:
            raise ValueError("invalid empty newc name")
        cursor += 110
        name_end = cursor + name_size
        if name_end > len(blob) or blob[name_end - 1] != 0:
            raise ValueError("truncated newc name")
        name = blob[cursor : name_end - 1].decode("utf-8")
        cursor = align(name_end, 4)
        data_end = cursor + file_size
        if data_end > len(blob):
            raise ValueError(f"truncated newc data: {name}")
        data = blob[cursor:data_end]
        cursor = align(data_end, 4)
        if name == "TRAILER!!!":
            return entries
        if name.startswith("/") or ".." in pathlib.PurePosixPath(name).parts:
            raise ValueError(f"unsafe newc path: {name}")
        if name in entries:
            raise ValueError(f"duplicate newc entry: {name}")
        entries[name] = {
            "inode": values[0],
            "mode": mode,
            "uid": values[2],
            "gid": values[3],
            "links": values[4],
            "mtime": values[5],
            "size": file_size,
            "dev_major": values[7],
            "dev_minor": values[8],
            "rdev_major": values[9],
            "rdev_minor": values[10],
            "data": data,
        }
    raise ValueError("newc archive has no trailer")


def ramdisk_rejection(entries: dict[str, dict[str, object]]) -> dict[str, object]:
    if "init" not in entries:
        raise ValueError("official ramdisk has no init")
    init = entries["init"]["data"]
    assert isinstance(init, bytes)
    internal_device_prefix = b"/dev/" + b"mmc" + b"blk"
    repair_tools = sorted(
        name
        for name in entries
        if pathlib.PurePosixPath(name).name
        in {"e2fsck", "fsck.ext2", "fsck.ext3", "fsck.ext4"}
    )
    findings = {
        "internal_device_default": internal_device_prefix in init,
        "filesystem_repair_tools": repair_tools,
        "writable_root_logic": b'OPTION_MOUNT_OPTIONS="rw' in init,
        "interactive_rescue_shell": b"busybox_shell" in init,
    }
    if not all(
        (
            findings["internal_device_default"],
            findings["filesystem_repair_tools"],
            findings["writable_root_logic"],
            findings["interactive_rescue_shell"],
        )
    ):
        raise ValueError("expected OSMC ramdisk safety findings were not all detected")
    return {
        "entry_count": len(entries),
        "reuse_for_external_boot": "rejected",
        "findings": findings,
    }


def component_manifest(blob: bytes, artifact_format: str) -> dict[str, object]:
    return {
        "size": len(blob),
        "sha256": sha256_bytes(blob),
        "format": artifact_format,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-deb", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    output = safe_output(
        (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output
    )

    helpers = load_artifact_helpers()
    package = args.kernel_deb.read_bytes()
    data_tar = helpers.ar_member(package, "data.tar.xz")
    image = helpers.tar_member_xz(data_tar, "boot/kernel-4.9.269-62-osmc.img")
    parsed = parse_boot_image(image)
    ramdisk = parsed.pop("ramdisk")
    kernel = parsed.pop("kernel")
    second = parsed.pop("second")
    assert isinstance(ramdisk, bytes)
    assert isinstance(kernel, bytes)
    assert isinstance(second, bytes)
    ramdisk_entries = parse_newc(gzip.decompress(ramdisk))

    manifest = {
        "schema": 1,
        "source_package_sha256": sha256_bytes(package),
        "source_boot_image_sha256": sha256_bytes(image),
        **parsed,
        "components": {
            "kernel": component_manifest(kernel, "gzip"),
            "ramdisk": component_manifest(ramdisk, "gzip+newc"),
            "second": component_manifest(second, "Amlogic multi-DTB v2"),
        },
        "official_ramdisk": ramdisk_rejection(ramdisk_entries),
        "physical_boot_tested": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("official Vero Android boot contract: PASS")
    print("official OSMC ramdisk reuse: REJECTED")
    print(f"manifest: {output}")
    print("physical boot status: NOT TESTED")


if __name__ == "__main__":
    main()
