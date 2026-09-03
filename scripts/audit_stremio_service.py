#!/usr/bin/env python3
"""Reject upstream x86 Linux binaries and audit the prepared Vero runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct


ELF_MACHINES = {3: "x86", 40: "ARM", 62: "x86-64", 183: "AArch64"}
UPSTREAM_NODE_VERSION = b"node.js/v18.12.1"


def elf_details(path: Path) -> dict[str, object]:
    payload = path.read_bytes()
    if len(payload) < 20 or payload[:4] != b"\x7fELF":
        raise ValueError(f"not an ELF executable: {path}")
    elf_class = {1: 32, 2: 64}.get(payload[4])
    byte_order = {1: "<", 2: ">"}.get(payload[5])
    if elf_class is None or byte_order is None:
        raise ValueError(f"unsupported ELF encoding: {path}")
    machine = struct.unpack_from(f"{byte_order}H", payload, 18)[0]
    return {
        "path": str(path),
        "bits": elf_class,
        "machine": ELF_MACHINES.get(machine, f"unknown-{machine}"),
    }


def audit(upstream: Path, prepared: Path) -> dict[str, object]:
    upstream_files = [upstream / name for name in ("stremio-runtime", "ffmpeg", "ffprobe")]
    for path in upstream_files:
        if not path.is_file():
            raise ValueError(f"missing upstream Linux bundle input: {path}")
    prepared_files = [prepared / name for name in ("stremio-runtime", "ffmpeg", "ffprobe")]
    manifest_path = prepared / "runtime-manifest.json"
    if any(not path.is_file() for path in prepared_files) or not manifest_path.is_file():
        raise ValueError("prepared ARM runtime is incomplete")

    upstream_details = [elf_details(path) for path in upstream_files]
    if any(item["machine"] != "x86-64" for item in upstream_details):
        raise ValueError("upstream Linux bundle architecture changed; review required")
    if UPSTREAM_NODE_VERSION not in upstream_files[0].read_bytes():
        raise ValueError("upstream Stremio runtime no longer identifies as Node.js 18.12.1")
    prepared_details = [elf_details(path) for path in prepared_files]
    if any(item["machine"] != "ARM" or item["bits"] != 32 for item in prepared_details):
        raise ValueError("prepared runtime contains a non-armhf executable")

    prepared_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = {
        "upstreamRejected": True,
        "upstreamRuntimeNodeVersion": "18.12.1",
        "upstreamExecutables": upstream_details,
        "preparedExecutables": prepared_details,
        "preparedRuntimeImageEligible": prepared_manifest["imageEligible"],
        "remainingBlockers": prepared_manifest["remainingBlockers"],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--prepared", type=Path, required=True)
    args = parser.parse_args()
    audit(args.upstream, args.prepared)


if __name__ == "__main__":
    main()
