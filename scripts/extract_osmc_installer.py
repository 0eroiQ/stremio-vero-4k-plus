#!/usr/bin/env python3
"""Extract the OSMC root filesystem from a verified installer image.

The parser reads a regular image file directly. It never attaches, mounts, or
writes a block device.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
from pathlib import Path
import shutil
import struct
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "downloads"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def checked_regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"input must be a regular file: {path}")


def read_exact(stream, offset: int, size: int) -> bytes:
    stream.seek(offset)
    data = stream.read(size)
    if len(data) != size:
        raise ValueError(f"short read at byte {offset}: expected {size}, got {len(data)}")
    return data


class Fat32:
    def __init__(self, image: Path):
        self.stream = image.open("rb")
        mbr = read_exact(self.stream, 0, 512)
        if mbr[510:512] != b"\x55\xaa":
            raise ValueError("installer has no valid MBR signature")
        partition = mbr[446:462]
        self.partition_offset = struct.unpack_from("<I", partition, 8)[0] * 512
        boot = read_exact(self.stream, self.partition_offset, 512)
        if boot[510:512] != b"\x55\xaa":
            raise ValueError("installer partition has no valid FAT boot signature")
        self.bytes_per_sector = struct.unpack_from("<H", boot, 11)[0]
        self.sectors_per_cluster = boot[13]
        reserved = struct.unpack_from("<H", boot, 14)[0]
        fat_count = boot[16]
        fat_size = struct.unpack_from("<I", boot, 36)[0]
        self.root_cluster = struct.unpack_from("<I", boot, 44)[0]
        if self.bytes_per_sector not in {512, 1024, 2048, 4096}:
            raise ValueError("unsupported FAT sector size")
        if self.sectors_per_cluster == 0 or fat_count == 0 or fat_size == 0:
            raise ValueError("invalid FAT32 geometry")
        self.cluster_size = self.bytes_per_sector * self.sectors_per_cluster
        self.fat_offset = self.partition_offset + reserved * self.bytes_per_sector
        self.data_offset = self.partition_offset + (
            reserved + fat_count * fat_size
        ) * self.bytes_per_sector

    def close(self) -> None:
        self.stream.close()

    def next_cluster(self, cluster: int) -> int:
        entry = read_exact(self.stream, self.fat_offset + cluster * 4, 4)
        return struct.unpack("<I", entry)[0] & 0x0FFFFFFF

    def cluster_chain(self, first: int):
        cluster = first
        seen: set[int] = set()
        while 2 <= cluster < 0x0FFFFFF8:
            if cluster in seen or len(seen) > 2_000_000:
                raise ValueError("invalid or cyclic FAT cluster chain")
            seen.add(cluster)
            yield cluster
            cluster = self.next_cluster(cluster)

    def cluster_bytes(self, cluster: int) -> bytes:
        offset = self.data_offset + (cluster - 2) * self.cluster_size
        return read_exact(self.stream, offset, self.cluster_size)

    @staticmethod
    def long_name_part(entry: bytes) -> str:
        encoded = entry[1:11] + entry[14:26] + entry[28:32]
        return encoded.decode("utf-16-le", errors="strict").rstrip("\uffff\x00")

    def root_files(self) -> dict[str, tuple[int, int]]:
        result: dict[str, tuple[int, int]] = {}
        long_parts: dict[int, str] = {}
        for cluster in self.cluster_chain(self.root_cluster):
            block = self.cluster_bytes(cluster)
            for offset in range(0, len(block), 32):
                entry = block[offset:offset + 32]
                if entry[0] == 0:
                    return result
                if entry[0] == 0xE5:
                    long_parts.clear()
                    continue
                attributes = entry[11]
                if attributes == 0x0F:
                    long_parts[entry[0] & 0x1F] = self.long_name_part(entry)
                    continue
                short_name = (entry[:8].decode("ascii").rstrip() +
                              ("." + entry[8:11].decode("ascii").rstrip() if entry[8:11].strip() else ""))
                name = "".join(long_parts[index] for index in sorted(long_parts)) or short_name
                long_parts.clear()
                if attributes & 0x18:
                    continue
                first_cluster = (
                    struct.unpack_from("<H", entry, 20)[0] << 16
                ) | struct.unpack_from("<H", entry, 26)[0]
                size = struct.unpack_from("<I", entry, 28)[0]
                result[name] = (first_cluster, size)
        return result

    def extract(self, name: str, output) -> int:
        files = self.root_files()
        matches = [details for filename, details in files.items() if filename.casefold() == name.casefold()]
        if len(matches) != 1:
            raise ValueError(f"expected one FAT root file named {name!r}, found {len(matches)}")
        first_cluster, size = matches[0]
        remaining = size
        for cluster in self.cluster_chain(first_cluster):
            block = self.cluster_bytes(cluster)
            chunk = block[:remaining]
            output.write(chunk)
            remaining -= len(chunk)
            if remaining == 0:
                return size
        raise ValueError(f"FAT chain ended with {remaining} bytes missing")


def validate_rootfs(path: Path) -> None:
    required = {
        "etc/os-release",
        "usr/bin/mediacenter",
        "usr/share/kodi/system/settings/settings.xml",
    }
    with tarfile.open(path, "r:xz") as archive:
        names = {member.name.removeprefix("./") for member in archive}
    missing = sorted(required - names)
    if missing:
        raise ValueError(f"OSMC rootfs is missing required paths: {', '.join(missing)}")


def extract(image_gz: Path, output: Path, expected_sha256: str) -> None:
    checked_regular_file(image_gz)
    if digest(image_gz) != expected_sha256:
        raise SystemExit("OSMC installer SHA-256 does not match the source lock")
    if output.resolve() == CACHE.resolve() or not output.resolve().is_relative_to(CACHE.resolve()):
        raise SystemExit(f"output must be a file beneath {CACHE}")
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="osmc-installer-", dir=CACHE) as directory:
        image = Path(directory) / "installer.img"
        with gzip.open(image_gz, "rb") as compressed, image.open("wb") as expanded:
            shutil.copyfileobj(compressed, expanded, length=1024 * 1024)
        fat = Fat32(image)
        temporary = Path(directory) / "filesystem.tar.xz"
        try:
            with temporary.open("wb") as stream:
                size = fat.extract("filesystem.tar.xz", stream)
        finally:
            fat.close()
        validate_rootfs(temporary)
        temporary.replace(output)
    print(f"extracted verified OSMC rootfs ({size} bytes): {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-gz", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=CACHE / "OSMC_TGT_vero3_20250303-rootfs.tar.xz")
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    extract(args.image_gz, args.output, args.expected_sha256)


if __name__ == "__main__":
    main()
