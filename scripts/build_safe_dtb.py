#!/usr/bin/env python3
"""Create and verify a Vero multi-DTB with eMMC disabled in every entry."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import shutil
import struct
import subprocess
import tarfile
import tempfile
from collections.abc import Callable


AR_MAGIC = b"!<arch>\n"
AML_MAGIC = b"AML_"
FDT_MAGIC = b"\xd0\x0d\xfe\xed"
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9
AML_VERSION = 2
PAGE_SIZE = 2048
ENTRY_SIZE = 56
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_ROOT = (ROOT / "out").resolve()
EMMC_STATUS = ("/emmc@d0074000", "status")
SD_STATUS = ("/sd@d0072000", "status")
SDIO_STATUS = ("/sdio@d0070000", "status")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ar_member(archive: bytes, wanted: str) -> bytes:
    if not archive.startswith(AR_MAGIC):
        raise ValueError("input is not a Unix ar archive")
    cursor = len(AR_MAGIC)
    while cursor < len(archive):
        header = archive[cursor : cursor + 60]
        if len(header) != 60 or header[58:60] != b"`\n":
            raise ValueError("invalid ar member header")
        raw_name = header[:16].decode("ascii").strip()
        name = raw_name[:-1] if raw_name.endswith("/") else raw_name
        try:
            size = int(header[48:58].decode("ascii").strip())
        except ValueError as error:
            raise ValueError("invalid ar member size") from error
        start = cursor + 60
        end = start + size
        if end > len(archive):
            raise ValueError("truncated ar member")
        if name == wanted:
            return archive[start:end]
        cursor = end + (size % 2)
    raise ValueError(f"ar member not found: {wanted}")


def tar_member_xz(archive: bytes, wanted: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:xz") as tar:
        candidates = (wanted, f"./{wanted}")
        for name in candidates:
            try:
                member = tar.getmember(name)
            except KeyError:
                continue
            stream = tar.extractfile(member)
            if stream is None:
                raise ValueError(f"tar member is not a regular file: {name}")
            return stream.read()
    raise ValueError(f"tar member not found: {wanted}")


def decode_id(raw: bytes) -> str:
    if len(raw) != 16:
        raise ValueError("Amlogic identifier must be 16 bytes")
    restored = b"".join(raw[index : index + 4][::-1] for index in range(0, 16, 4))
    return restored.rstrip(b" \0").decode("ascii")


def encode_id(value: str) -> bytes:
    encoded = value.encode("ascii")
    if len(encoded) > 16:
        raise ValueError("Amlogic identifier is longer than 16 bytes")
    padded = encoded.ljust(16, b" ")
    return b"".join(padded[index : index + 4][::-1] for index in range(0, 16, 4))


def fdt_size(blob: bytes) -> int:
    if not blob.startswith(FDT_MAGIC) or len(blob) < 8:
        raise ValueError("multi-DTB entry is not a flattened device tree")
    size = struct.unpack(">I", blob[4:8])[0]
    if size < 40 or size > len(blob):
        raise ValueError("invalid flattened device tree size")
    return size


def align4(value: int) -> int:
    return (value + 3) & ~3


def fdt_snapshot(blob: bytes) -> tuple[set[str], dict[tuple[str, str], bytes]]:
    """Return a semantic node/property snapshot without rewriting the vendor DTB."""
    total_size = fdt_size(blob)
    if len(blob) < 40:
        raise ValueError("flattened device tree header is truncated")
    (
        _magic,
        _total_size,
        struct_offset,
        strings_offset,
        _reserve_offset,
        _version,
        _last_compatible_version,
        _boot_cpu,
        strings_size,
        struct_size,
    ) = struct.unpack_from(">10I", blob)
    struct_end = struct_offset + struct_size
    strings_end = strings_offset + strings_size
    if struct_end > total_size or strings_end > total_size:
        raise ValueError("flattened device tree blocks exceed the declared size")

    strings = blob[strings_offset:strings_end]
    cursor = struct_offset
    stack: list[str] = []
    nodes: set[str] = set()
    properties: dict[tuple[str, str], bytes] = {}

    while cursor + 4 <= struct_end:
        token = struct.unpack_from(">I", blob, cursor)[0]
        cursor += 4
        if token == FDT_BEGIN_NODE:
            end = blob.find(b"\0", cursor, struct_end)
            if end < 0:
                raise ValueError("unterminated device-tree node name")
            name = blob[cursor:end].decode("ascii")
            cursor = align4(end + 1)
            stack.append(name)
            path = "/" + "/".join(part for part in stack if part)
            nodes.add(path)
        elif token == FDT_END_NODE:
            if not stack:
                raise ValueError("unbalanced device-tree end-node token")
            stack.pop()
        elif token == FDT_PROP:
            if cursor + 8 > struct_end or not stack:
                raise ValueError("invalid device-tree property token")
            length, name_offset = struct.unpack_from(">II", blob, cursor)
            cursor += 8
            value_end = cursor + length
            if value_end > struct_end or name_offset >= len(strings):
                raise ValueError("invalid device-tree property bounds")
            name_end = strings.find(b"\0", name_offset)
            if name_end < 0:
                raise ValueError("unterminated device-tree property name")
            name = strings[name_offset:name_end].decode("ascii")
            path = "/" + "/".join(part for part in stack if part)
            key = (path, name)
            if key in properties:
                raise ValueError(f"duplicate device-tree property: {path}/{name}")
            properties[key] = blob[cursor:value_end]
            cursor = align4(value_end)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if stack:
                raise ValueError("device-tree ended with open nodes")
            return nodes, properties
        else:
            raise ValueError(f"unknown device-tree token: {token}")
    raise ValueError("flattened device tree has no end token")


def parse_multidtb(blob: bytes) -> list[dict[str, object]]:
    if len(blob) < 16:
        raise ValueError("multi-DTB is truncated")
    magic, version, count = struct.unpack_from("<4sII", blob)
    if magic != AML_MAGIC or version != AML_VERSION:
        raise ValueError("unsupported Amlogic multi-DTB header")
    table_end = 12 + count * ENTRY_SIZE
    if table_end + 4 > len(blob):
        raise ValueError("multi-DTB index is truncated")
    if struct.unpack_from("<I", blob, table_end)[0] != 0:
        raise ValueError("multi-DTB index terminator is invalid")

    entries: list[dict[str, object]] = []
    for index in range(count):
        start = 12 + index * ENTRY_SIZE
        chipset = decode_id(blob[start : start + 16])
        platform = decode_id(blob[start + 16 : start + 32])
        revision = decode_id(blob[start + 32 : start + 48])
        offset, padded_size = struct.unpack_from("<II", blob, start + 48)
        end = offset + padded_size
        if offset % PAGE_SIZE or padded_size % PAGE_SIZE or end > len(blob):
            raise ValueError("invalid multi-DTB entry bounds")
        padded = blob[offset:end]
        actual_size = fdt_size(padded)
        entries.append(
            {
                "chipset": chipset,
                "platform": platform,
                "revision": revision,
                "dtb": padded[:actual_size],
            }
        )
    return entries


def pad_block(blob: bytes) -> bytes:
    padding = PAGE_SIZE - (len(blob) % PAGE_SIZE)
    return blob + bytes(padding)


def pack_multidtb(entries: list[dict[str, object]]) -> bytes:
    header_size = 12 + ENTRY_SIZE * len(entries) + 4
    first_offset = header_size + (PAGE_SIZE - (header_size % PAGE_SIZE))
    payloads = [pad_block(entry["dtb"]) for entry in entries]
    output = bytearray(struct.pack("<4sII", AML_MAGIC, AML_VERSION, len(entries)))
    offset = first_offset
    for entry, payload in zip(entries, payloads, strict=True):
        output.extend(encode_id(str(entry["chipset"])))
        output.extend(encode_id(str(entry["platform"])))
        output.extend(encode_id(str(entry["revision"])))
        output.extend(struct.pack("<II", offset, len(payload)))
        offset += len(payload)
    output.extend(struct.pack("<I", 0))
    output.extend(bytes(first_offset - len(output)))
    for payload in payloads:
        output.extend(payload)
    return bytes(output)


def fdt_status(fdtget: str, source: pathlib.Path, node: str) -> str:
    result = subprocess.run(
        [fdtget, "-t", "s", str(source), f"/{node}", "status"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"fdtget failed for {node}: {result.stderr.strip()}")
    return result.stdout.strip()


def set_fdt_status(fdtput: str, source: pathlib.Path, node: str, status: str) -> None:
    result = subprocess.run(
        [fdtput, "-t", "s", str(source), f"/{node}", "status", status],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"fdtput failed for {node}: {result.stderr.strip()}")


def assert_storage_statuses(blob: bytes, *, emmc: bytes, context: str) -> None:
    _nodes, properties = fdt_snapshot(blob)
    expected = {
        EMMC_STATUS: emmc,
        SD_STATUS: b"okay\0",
        SDIO_STATUS: b"okay\0",
    }
    for key, value in expected.items():
        if properties.get(key) != value:
            path, name = key
            expected_text = value.rstrip(b"\0").decode("ascii")
            raise ValueError(
                f"{context} {path}/{name} is not {expected_text}"
            )


def assert_only_emmc_changed(original: bytes, patched: bytes) -> None:
    original_nodes, original_properties = fdt_snapshot(original)
    patched_nodes, patched_properties = fdt_snapshot(patched)
    if original_nodes != patched_nodes:
        raise ValueError("device-tree node set changed unexpectedly")
    if original_properties.keys() != patched_properties.keys():
        raise ValueError("device-tree property set changed unexpectedly")
    differences = {
        key
        for key in original_properties
        if original_properties[key] != patched_properties[key]
    }
    expected = {EMMC_STATUS}
    if differences != expected:
        raise ValueError(f"unexpected device-tree property changes: {sorted(differences)}")
    assert_storage_statuses(original, emmc=b"okay\0", context="official")
    assert_storage_statuses(patched, emmc=b"disabled\0", context="patched")


def entry_identity(entry: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(entry["chipset"]),
        str(entry["platform"]),
        str(entry["revision"]),
    )


def assert_all_entries_safely_patched(
    official_entries: list[dict[str, object]],
    patched_entries: list[dict[str, object]],
) -> None:
    if not official_entries:
        raise ValueError("multi-DTB has no device-tree entries")
    if len(official_entries) != len(patched_entries):
        raise ValueError("patched multi-DTB entry count changed")
    if [entry_identity(entry) for entry in official_entries] != [
        entry_identity(entry) for entry in patched_entries
    ]:
        raise ValueError("patched multi-DTB index changed")
    for index, (official, patched) in enumerate(
        zip(official_entries, patched_entries, strict=True)
    ):
        try:
            assert_only_emmc_changed(bytes(official["dtb"]), bytes(patched["dtb"]))
        except (TypeError, ValueError) as error:
            identity = "/".join(entry_identity(official))
            raise ValueError(
                f"unsafe multi-DTB entry {index} ({identity}): {error}"
            ) from error


def patch_all_entries(
    official_entries: list[dict[str, object]],
    patcher: Callable[[int, dict[str, object]], bytes],
) -> list[dict[str, object]]:
    patched_entries: list[dict[str, object]] = []
    for index, official in enumerate(official_entries):
        patched = dict(official)
        patched["dtb"] = patcher(index, official)
        patched_entries.append(patched)
    assert_all_entries_safely_patched(official_entries, patched_entries)
    return patched_entries


def patch_entry_storage(
    fdtget: str,
    fdtput: str,
    work: pathlib.Path,
    index: int,
    entry: dict[str, object],
) -> bytes:
    identity = "/".join(entry_identity(entry))
    original_dtb = work / f"entry-{index}-official.dtb"
    safe_dtb = work / f"entry-{index}-external-only.dtb"
    original_dtb.write_bytes(bytes(entry["dtb"]))
    shutil.copyfile(original_dtb, safe_dtb)
    if fdt_status(fdtget, original_dtb, "emmc@d0074000") != "okay":
        raise ValueError(f"official {identity} eMMC node is not enabled")
    if fdt_status(fdtget, original_dtb, "sd@d0072000") != "okay":
        raise ValueError(f"official {identity} SD node is not enabled")
    if fdt_status(fdtget, original_dtb, "sdio@d0070000") != "okay":
        raise ValueError(f"official {identity} SDIO node is not enabled")
    set_fdt_status(fdtput, safe_dtb, "emmc@d0074000", "disabled")
    if fdt_status(fdtget, safe_dtb, "emmc@d0074000") != "disabled":
        raise ValueError(f"safe {identity} eMMC node was not disabled")
    if fdt_status(fdtget, safe_dtb, "sd@d0072000") != "okay":
        raise ValueError(f"safe {identity} SD node was changed")
    if fdt_status(fdtget, safe_dtb, "sdio@d0070000") != "okay":
        raise ValueError(f"safe {identity} SDIO node was changed")
    patched_dtb = safe_dtb.read_bytes()
    assert_only_emmc_changed(bytes(entry["dtb"]), patched_dtb)
    return patched_dtb


def safe_output(path: pathlib.Path) -> pathlib.Path:
    resolved_parent = path.parent.resolve()
    if OUT_ROOT != resolved_parent and OUT_ROOT not in resolved_parent.parents:
        raise ValueError("output must be inside the repository out directory")
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise ValueError("existing output is not a regular file")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-deb", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    fdtget = shutil.which("fdtget")
    fdtput = shutil.which("fdtput")
    if fdtget is None or fdtput is None:
        raise SystemExit("fdtget and fdtput are required to build the safe device tree")
    output = safe_output((ROOT / args.output).resolve() if not args.output.is_absolute() else args.output)

    deb = args.kernel_deb.read_bytes()
    data_tar = ar_member(deb, "data.tar.xz")
    original = tar_member_xz(data_tar, "boot/dtb-4.9.269-62-osmc.img")
    official_entries = parse_multidtb(original)
    matches = [entry for entry in official_entries if entry["platform"] == "p231"]
    if len(matches) != 1:
        raise ValueError("expected exactly one Vero 4K+ p231 device tree")

    with tempfile.TemporaryDirectory(prefix="stremio-vero-dtb-") as directory:
        work = pathlib.Path(directory)
        entries = patch_all_entries(
            official_entries,
            lambda index, entry: patch_entry_storage(
                fdtget, fdtput, work, index, entry
            ),
        )

    rebuilt = pack_multidtb(entries)
    reparsed = parse_multidtb(rebuilt)
    assert_all_entries_safely_patched(official_entries, reparsed)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(rebuilt)
    manifest = {
        "schema": 1,
        "artifact": output.name,
        "sha256": sha256_bytes(rebuilt),
        "source_sha256": sha256_bytes(original),
        "source_package_sha256": sha256_bytes(deb),
        "entries": [
            {
                "chipset": entry["chipset"],
                "platform": entry["platform"],
                "revision": entry["revision"],
                "emmc": "disabled",
                "sd": "okay",
                "sdio": "okay",
            }
            for entry in entries
        ],
        "physical_boot_tested": False,
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"all-entry eMMC-disabled Vero multi-DTB: PASS ({manifest['sha256']})")
    print(f"artifact: {output}")
    print("physical boot status: NOT TESTED")


if __name__ == "__main__":
    main()
