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


def execute_version(emulator: Path, executable: Path, expected: str) -> str:
    probe = subprocess.run(
        [str(emulator), str(executable), "-version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    output = probe.stdout.decode("utf-8", "replace")
    if probe.returncode != 0:
        raise RuntimeError(
            f"{executable.name} probe exited with status {probe.returncode}: {output}"
        )
    first_line = output.splitlines()[0] if output.splitlines() else ""
    if expected not in first_line:
        raise RuntimeError(f"unexpected {executable.name} version: {first_line!r}")
    return first_line


def smoke(
    runtime: Path,
    server: Path,
    ffmpeg: Path,
    ffprobe: Path,
    emulator: Path,
    sysroot: Path,
) -> dict[str, object]:
    for path in (runtime, server, ffmpeg, ffprobe, emulator):
        if not path.is_file():
            raise ValueError(f"required input is missing: {path}")
    if not sysroot.is_dir():
        raise ValueError(f"ARM sysroot is missing: {sysroot}")

    environment = os.environ.copy()
    environment.update(
        {
            "CASTING_DISABLED": "1",
            "FFMPEG_BIN": "/bin/false",
            "FFPROBE_BIN": "/bin/false",
            "NO_HTTPS_SERVER": "1",
        }
    )
    prefix = [str(emulator), "-L", str(sysroot), str(runtime)]
    version_probe = subprocess.run(
        [*prefix, "--version"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=10,
    )
    version_output = version_probe.stdout.decode("utf-8", "replace").strip()
    if version_probe.returncode != 0:
        raise RuntimeError(
            f"ARM Node version probe exited with status {version_probe.returncode}: "
            f"{version_output}"
        )
    if version_output != "v18.12.1":
        raise RuntimeError(f"unexpected ARM Node version: {version_output!r}")
    ffmpeg_version = execute_version(emulator, ffmpeg, "ffmpeg version 4.4.1-static")
    ffprobe_version = execute_version(emulator, ffprobe, "ffprobe version 4.4.1-static")

    environment["FFMPEG_BIN"] = str(ffmpeg.resolve())
    environment["FFPROBE_BIN"] = str(ffprobe.resolve())

    command = [*prefix, str(server)]
    process = subprocess.Popen(
        command,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    failure: BaseException | None = None
    status: int | None = None
    try:
        status = wait_for_http(process, 20)
    except BaseException as error:
        failure = error
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            output = process.communicate(timeout=5)[0]
        except subprocess.TimeoutExpired:
            process.kill()
            output = process.communicate(timeout=5)[0]
    decoded_output = output.decode("utf-8", "replace")
    if failure is not None:
        raise RuntimeError(f"{failure}; service output: {decoded_output[-4000:]}") from failure
    if status is None:
        raise RuntimeError("service probe completed without an HTTP status")

    report = {
        "armRuntimeExecuted": True,
        "nodeVersion": version_output,
        "ffmpegVersion": ffmpeg_version,
        "ffprobeVersion": ffprobe_version,
        "serverPort": 11470,
        "httpStatus": status,
        "mediaToolsExecuted": True,
        "scope": "startup and version probes only; no streaming or playback",
        "logTail": decoded_output[-2000:],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--ffprobe", type=Path, required=True)
    parser.add_argument("--emulator", type=Path, required=True)
    parser.add_argument("--sysroot", type=Path, required=True)
    args = parser.parse_args()
    smoke(
        args.runtime,
        args.server,
        args.ffmpeg,
        args.ffprobe,
        args.emulator,
        args.sysroot,
    )


if __name__ == "__main__":
    main()
