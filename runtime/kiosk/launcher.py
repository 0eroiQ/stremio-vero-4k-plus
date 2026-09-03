#!/usr/bin/env python3
"""Launch the disabled Qt WebEngine/EGLFS compatibility probe."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_QMLSCENE = Path("/usr/lib/qt5/bin/qmlscene")
DEFAULT_QML = Path("/usr/share/stremio-vero/kiosk/main.qml")
DEFAULT_STATE = Path("/var/lib/stremio-vero-kiosk")
DEFAULT_CACHE = Path("/var/cache/stremio-vero-kiosk")


def require_regular(path: Path, description: str, executable: bool = False) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{description} must be a regular file: {path}")
    if executable and not os.access(path, os.X_OK):
        raise ValueError(f"{description} is not executable: {path}")


def kiosk_environment(state: Path, cache: Path, runtime: Path) -> dict[str, str]:
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    for path in (state, cache, runtime):
        path.chmod(0o700)
    environment = os.environ.copy()
    environment.pop("DISPLAY", None)
    environment.pop("WAYLAND_DISPLAY", None)
    environment.update(
        {
            "HOME": str(state),
            "XDG_CACHE_HOME": str(cache),
            "XDG_CONFIG_HOME": str(state / "config"),
            "XDG_DATA_HOME": str(state / "data"),
            "XDG_RUNTIME_DIR": str(runtime),
            "QT_QPA_PLATFORM": "eglfs",
            "QT_QPA_EGLFS_INTEGRATION": "none",
            "QT_QPA_EGLFS_FB": "/dev/fb0",
            "QT_QPA_EGLFS_FORCEVSYNC": "1",
            "QT_QPA_EGLFS_DEBUG": "1",
            "QSG_INFO": "1",
        }
    )
    return environment


def kiosk_command(qmlscene: Path, qml: Path) -> tuple[str, ...]:
    require_regular(qmlscene, "Qt QML scene runner", executable=True)
    require_regular(qml, "kiosk QML")
    return (str(qmlscene), str(qml))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qmlscene", type=Path, default=DEFAULT_QMLSCENE)
    parser.add_argument("--qml", type=Path, default=DEFAULT_QML)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=Path(os.environ.get("RUNTIME_DIRECTORY", "/run/stremio-vero-kiosk")),
    )
    args = parser.parse_args()
    command = kiosk_command(args.qmlscene, args.qml)
    environment = kiosk_environment(args.state, args.cache, args.runtime)
    os.execve(command[0], command, environment)


if __name__ == "__main__":
    main()
