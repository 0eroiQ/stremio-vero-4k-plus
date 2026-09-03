#!/usr/bin/env python3
"""Prepare the architecture-neutral Stremio server with a verified ARM runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import tarfile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
EM_ARM = 40
NODE_MEMBER = "node-v18.12.1-linux-armv7l/bin/node"
NODE_LICENSE_MEMBER = "node-v18.12.1-linux-armv7l/LICENSE"
FFMPEG_MEMBER = "ffmpeg-4.4.1-armhf-static/ffmpeg"
FFPROBE_MEMBER = "ffmpeg-4.4.1-armhf-static/ffprobe"
FFMPEG_LICENSE_MEMBER = "ffmpeg-4.4.1-armhf-static/GPLv3.txt"
ARMHF_INTERPRETER = b"/lib/ld-linux-armhf.so.3"
FFMPEG_VERSION = b"FFmpeg version 4.4.1-static https://johnvansickle.com/ffmpeg/"
GLIBC_VERSION = re.compile(rb"GLIBC_([0-9]+)\.([0-9]+)")


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def verify_digest(path: Path, expected: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"input must be a regular file: {path}")
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"checksum mismatch for {path.name}: expected {expected}, got {actual}")


def safe_tar_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def read_exact_member(archive_path: Path, name: str) -> bytes:
    with tarfile.open(archive_path, "r:xz") as archive:
        for member in archive:
            if not safe_tar_member(member.name):
                raise ValueError(f"unsafe path in Node archive: {member.name!r}")
            if member.name != name:
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"required Node archive entry is not a regular file: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"could not read Node archive entry: {name}")
            return stream.read()
    raise ValueError(f"Node archive entry is missing: {name}")


def verify_armhf_node(payload: bytes) -> dict[str, object]:
    if len(payload) < 52 or payload[:4] != b"\x7fELF":
        raise ValueError("Node runtime is not an ELF executable")
    if payload[4] != 1:
        raise ValueError("Node runtime is not a 32-bit ELF")
    if payload[5] != 1:
        raise ValueError("Node runtime is not little-endian")
    machine = struct.unpack_from("<H", payload, 18)[0]
    if machine != EM_ARM:
        raise ValueError(f"Node runtime has wrong ELF machine: {machine}")
    if ARMHF_INTERPRETER not in payload:
        raise ValueError("Node runtime does not use the ARM hard-float loader")

    versions = {
        (int(match.group(1)), int(match.group(2)))
        for match in GLIBC_VERSION.finditer(payload)
    }
    if not versions:
        raise ValueError("Node runtime exposes no GLIBC compatibility information")
    maximum = max(versions)
    if maximum > (2, 31):
        raise ValueError(
            f"Node runtime requires GLIBC {maximum[0]}.{maximum[1]}, newer than OSMC 2.31"
        )
    return {
        "elfClass": 32,
        "endianness": "little",
        "machine": "ARM",
        "abi": "armhf",
        "interpreter": ARMHF_INTERPRETER.decode("ascii"),
        "maximumGlibc": f"{maximum[0]}.{maximum[1]}",
    }


def verify_server_js(payload: bytes) -> dict[str, object]:
    required = (b"EngineFS", b"FFMPEG_BIN", b"FFPROBE_BIN", b"11470")
    missing = [marker.decode("ascii") for marker in required if marker not in payload]
    if missing:
        raise ValueError(f"Stremio server.js is missing expected markers: {', '.join(missing)}")
    if len(payload) < 1024 * 1024:
        raise ValueError("Stremio server.js is unexpectedly small")
    return {
        "sha256": digest_bytes(payload),
        "bytes": len(payload),
        "httpPort": 11470,
    }


def verify_armhf_ffmpeg(payload: bytes, program: str) -> dict[str, object]:
    if len(payload) < 52 or payload[:4] != b"\x7fELF":
        raise ValueError(f"{program} is not an ELF executable")
    if payload[4] != 1 or payload[5] != 1:
        raise ValueError(f"{program} is not a 32-bit little-endian ELF")
    machine = struct.unpack_from("<H", payload, 18)[0]
    if machine != EM_ARM:
        raise ValueError(f"{program} has wrong ELF machine: {machine}")
    if b"/ld-linux" in payload:
        raise ValueError(f"{program} is unexpectedly dynamically linked")
    if FFMPEG_VERSION not in payload:
        raise ValueError(f"{program} is not the expected FFmpeg 4.4.1 static build")
    return {
        "sha256": digest_bytes(payload),
        "elfClass": 32,
        "endianness": "little",
        "machine": "ARM",
        "abi": "armhf",
        "linkage": "static",
        "version": "4.4.1-static",
    }


def guarded_output(path: Path) -> Path:
    resolved = path.resolve()
    if resolved == OUT.resolve() or not resolved.is_relative_to(OUT.resolve()):
        raise ValueError(f"output must be a directory beneath {OUT}")
    return resolved


def write_file(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    path.chmod(mode)


def prepare(
    node_archive: Path,
    server_js: Path,
    ffmpeg_archive: Path,
    output: Path,
    expected_node_sha256: str,
    expected_server_sha256: str,
    expected_ffmpeg_sha256: str,
) -> dict[str, object]:
    output = guarded_output(output)
    verify_digest(node_archive, expected_node_sha256)
    verify_digest(server_js, expected_server_sha256)
    verify_digest(ffmpeg_archive, expected_ffmpeg_sha256)

    node = read_exact_member(node_archive, NODE_MEMBER)
    license_text = read_exact_member(node_archive, NODE_LICENSE_MEMBER)
    server = server_js.read_bytes()
    ffmpeg = read_exact_member(ffmpeg_archive, FFMPEG_MEMBER)
    ffprobe = read_exact_member(ffmpeg_archive, FFPROBE_MEMBER)
    ffmpeg_license = read_exact_member(ffmpeg_archive, FFMPEG_LICENSE_MEMBER)
    node_details = verify_armhf_node(node)
    server_details = verify_server_js(server)
    ffmpeg_details = verify_armhf_ffmpeg(ffmpeg, "ffmpeg")
    ffprobe_details = verify_armhf_ffmpeg(ffprobe, "ffprobe")

    write_file(output / "stremio-runtime", node, 0o755)
    write_file(output / "server.js", server, 0o644)
    write_file(output / "LICENSE.node", license_text, 0o644)
    write_file(output / "ffmpeg", ffmpeg, 0o755)
    write_file(output / "ffprobe", ffprobe, 0o755)
    write_file(output / "LICENSE.ffmpeg", ffmpeg_license, 0o644)

    report: dict[str, object] = {
        "target": "OSMC Bullseye armhf on Vero 4K+",
        "nodeArchiveSha256": expected_node_sha256,
        "nodeRuntimeSha256": digest_bytes(node),
        "node": node_details,
        "server": server_details,
        "ffmpegArchiveSha256": expected_ffmpeg_sha256,
        "ffmpeg": ffmpeg_details,
        "ffprobe": ffprobe_details,
        "upstreamLinuxBundleAccepted": False,
        "upstreamLinuxBundleReason": "official bundled executables are x86-64",
        "imageEligible": False,
        "remainingBlockers": [
            "ARM service and media-tool smoke test",
            "Vero playback integration test",
        ],
    }
    report_path = output / "runtime-manifest.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-archive", type=Path, required=True)
    parser.add_argument("--server-js", type=Path, required=True)
    parser.add_argument("--ffmpeg-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUT / "stremio-service-armhf")
    parser.add_argument("--expected-node-sha256", required=True)
    parser.add_argument("--expected-server-sha256", required=True)
    parser.add_argument("--expected-ffmpeg-sha256", required=True)
    args = parser.parse_args()
    prepare(
        args.node_archive,
        args.server_js,
        args.ffmpeg_archive,
        args.output,
        args.expected_node_sha256,
        args.expected_server_sha256,
        args.expected_ffmpeg_sha256,
    )


if __name__ == "__main__":
    main()
