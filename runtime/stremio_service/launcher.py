#!/usr/bin/env python3
"""Prepare private Stremio Server state and replace this process with Node."""

from __future__ import annotations

import argparse
import errno
import json
import os
from pathlib import Path
import stat
from typing import NoReturn, Optional


DEFAULT_RUNTIME = Path("/usr/lib/stremio-vero/service/stremio-runtime")
DEFAULT_SERVER = Path("/usr/share/stremio-vero/service/server.js")
DEFAULT_FFMPEG = Path("/usr/lib/stremio-vero/service/ffmpeg")
DEFAULT_FFPROBE = Path("/usr/lib/stremio-vero/service/ffprobe")
DEFAULT_SETTINGS = Path("/usr/share/stremio-vero/service/default-server-settings.json")
DEFAULT_STATE = Path("/var/lib/stremio-vero/service")
DEFAULT_CACHE = Path("/var/cache/stremio-vero/service")
DEFAULT_WEB_UI = "http://127.0.0.1:8765/"


def require_regular_file(path: Path) -> None:
    details = path.lstat()
    if not stat.S_ISREG(details.st_mode) or path.is_symlink():
        raise ValueError(f"required input is not a regular file: {path}")


def require_private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    details = path.lstat()
    if not stat.S_ISDIR(details.st_mode) or path.is_symlink():
        raise ValueError(f"state path is not a real directory: {path}")
    path.chmod(0o700)


def load_defaults(path: Path, cache: Path) -> bytes:
    require_regular_file(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"cacheRoot", "cacheSize", "localAddonEnabled", "remoteHttps"}
    if set(data) != allowed:
        raise ValueError("default Stremio Server settings have an unexpected schema")
    if not isinstance(data["cacheSize"], int) or data["cacheSize"] < 0:
        raise ValueError("default Stremio Server cache size is invalid")
    if not isinstance(data["localAddonEnabled"], bool) or not isinstance(data["remoteHttps"], str):
        raise ValueError("default Stremio Server settings have invalid values")
    data["cacheRoot"] = str(cache)
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")


def create_initial_settings(state: Path, defaults: Path, cache: Path) -> Path:
    require_private_directory(state)
    require_private_directory(cache)
    target = state / "server-settings.json"
    payload = load_defaults(defaults, cache)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags, 0o600)
    except OSError as error:
        if error.errno != errno.EEXIST:
            raise
        require_regular_file(target)
        return target
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return target


def service_environment(
    state: Path,
    cache: Path,
    ffmpeg: Path,
    ffprobe: Path,
    web_ui: str,
) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "APP_PATH": str(state),
            "SETTINGS_PATH": str(state),
            "HOME": str(state),
            "XDG_CACHE_HOME": str(cache),
            "FFMPEG_BIN": str(ffmpeg),
            "FFPROBE_BIN": str(ffprobe),
            "WEBUI_LOCATION": web_ui,
            "CASTING_DISABLED": "1",
            "NO_HTTPS_SERVER": "1",
            "NO_CORS": "1",
        }
    )
    return environment


def service_command(
    runtime: Path,
    server: Path,
    emulator: Optional[Path] = None,
    sysroot: Optional[Path] = None,
) -> tuple[Path, tuple[str, ...]]:
    if (emulator is None) != (sysroot is None):
        raise ValueError("emulator and sysroot must be provided together")
    if emulator is None:
        return runtime, (str(runtime), str(server))
    require_regular_file(emulator)
    if not sysroot.is_dir() or sysroot.is_symlink():
        raise ValueError(f"emulator sysroot is not a real directory: {sysroot}")
    return emulator, (
        str(emulator),
        "-L",
        str(sysroot),
        str(runtime),
        str(server),
    )


def launch(
    runtime: Path,
    server: Path,
    ffmpeg: Path,
    ffprobe: Path,
    defaults: Path,
    state: Path,
    cache: Path,
    web_ui: str,
    emulator: Optional[Path] = None,
    sysroot: Optional[Path] = None,
) -> NoReturn:
    for path in (runtime, server, ffmpeg, ffprobe):
        require_regular_file(path)
    create_initial_settings(state, defaults, cache)
    environment = service_environment(state, cache, ffmpeg, ffprobe, web_ui)
    program, command = service_command(runtime, server, emulator, sysroot)
    os.execve(program, command, environment)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--server", type=Path, default=DEFAULT_SERVER)
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--ffprobe", type=Path, default=DEFAULT_FFPROBE)
    parser.add_argument("--defaults", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--web-ui", default=DEFAULT_WEB_UI)
    parser.add_argument("--emulator", type=Path)
    parser.add_argument("--sysroot", type=Path)
    args = parser.parse_args()
    launch(
        args.runtime,
        args.server,
        args.ffmpeg,
        args.ffprobe,
        args.defaults,
        args.state,
        args.cache,
        args.web_ui,
        args.emulator,
        args.sysroot,
    )


if __name__ == "__main__":
    main()
