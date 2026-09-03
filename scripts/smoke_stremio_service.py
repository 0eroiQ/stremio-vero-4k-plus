#!/usr/bin/env python3
"""Smoke-test the ARM Stremio server under QEMU without touching a device."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.request


def wait_for_http(process: subprocess.Popen[bytes], timeout: float) -> int:
    deadline = time.monotonic() + timeout
    last_error = "service did not open port 11470"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"service exited early with status {process.returncode}")
        try:
            with urllib.request.urlopen("http://127.0.0.1:11470/", timeout=1) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
        except (urllib.error.URLError, TimeoutError, socket.timeout) as error:
            last_error = str(error)
            time.sleep(0.25)
    raise RuntimeError(last_error)


def smoke(runtime: Path, server: Path, emulator: Path, sysroot: Path) -> dict[str, object]:
    for path in (runtime, server, emulator):
        if not path.is_file():
            raise ValueError(f"required input is missing: {path}")
    if not sysroot.is_dir():
        raise ValueError(f"ARM sysroot is missing: {sysroot}")

    environment = os.environ.copy()
    environment.update(
        {
            "FFMPEG_BIN": "/bin/false",
            "FFPROBE_BIN": "/bin/false",
            "NO_HTTPS_SERVER": "1",
        }
    )
    command = [str(emulator), "-L", str(sysroot), str(runtime), str(server)]
    process = subprocess.Popen(
        command,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        status = wait_for_http(process, 20)
    finally:
        process.terminate()
        try:
            output = process.communicate(timeout=5)[0]
        except subprocess.TimeoutExpired:
            process.kill()
            output = process.communicate(timeout=5)[0]

    report = {
        "armRuntimeExecuted": True,
        "serverPort": 11470,
        "httpStatus": status,
        "ffmpegUsed": False,
        "ffprobeUsed": False,
        "scope": "startup only; no streaming or playback",
        "logTail": output.decode("utf-8", "replace")[-2000:],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--emulator", type=Path, required=True)
    parser.add_argument("--sysroot", type=Path, required=True)
    args = parser.parse_args()
    smoke(args.runtime, args.server, args.emulator, args.sysroot)


if __name__ == "__main__":
    main()
