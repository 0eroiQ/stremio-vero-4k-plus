#!/usr/bin/env python3
"""Describe the display capabilities present in the pinned OSMC rootfs.

This is an archive-only audit.  It does not mount an image, run target code or
change service enablement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


BASE_REQUIRED_PATHS = {
    "boot/config-4.9.269-62-osmc",
    "etc/ld.so.conf.d/000-vero3.conf",
    "opt/vero3/lib/libEGL.so.1",
    "opt/vero3/lib/libGLESv2.so.2",
    "opt/vero3/lib/libMali.so",
    "usr/lib/kodi/kodi.bin",
    "usr/share/wayland-sessions/kodi-gbm.desktop",
    "var/lib/dpkg/status",
}


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def normalized_name(name: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe rootfs archive path: {name}")
    return str(path).removeprefix("./")


def member_bytes(archive: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    source = archive.extractfile(member)
    if source is None:
        raise ValueError(f"rootfs entry is not a regular file: {member.name}")
    return source.read()


def installed_packages(status: str) -> dict[str, str]:
    packages: dict[str, str] = {}
    for paragraph in status.split("\n\n"):
        fields: dict[str, str] = {}
        for line in paragraph.splitlines():
            if ": " in line and not line.startswith((" ", "\t")):
                key, value = line.split(": ", 1)
                fields[key] = value
        if fields.get("Status") == "install ok installed":
            name = fields.get("Package")
            version = fields.get("Version")
            if name and version:
                packages[name] = version
    return packages


def has_library(paths: set[str], stem: str) -> bool:
    return any(PurePosixPath(path).name.startswith(stem) for path in paths)


def audit(rootfs: Path) -> dict[str, object]:
    if not rootfs.is_file():
        raise ValueError(f"rootfs archive does not exist: {rootfs}")

    members: dict[str, tarfile.TarInfo] = {}
    with tarfile.open(rootfs, mode="r:xz") as archive:
        for member in archive:
            name = normalized_name(member.name)
            if name in members:
                raise ValueError(f"duplicate rootfs archive path: {name}")
            members[name] = member

        missing_base = sorted(BASE_REQUIRED_PATHS.difference(members))
        if missing_base:
            raise ValueError(
                "rootfs is missing required Vero display files: "
                + ", ".join(missing_base)
            )

        status = member_bytes(archive, members["var/lib/dpkg/status"]).decode(
            "utf-8", errors="strict"
        )
        ld_path = member_bytes(
            archive, members["etc/ld.so.conf.d/000-vero3.conf"]
        ).decode("utf-8", errors="strict").splitlines()
        mali = member_bytes(archive, members["opt/vero3/lib/libMali.so"])
        kernel_config = member_bytes(
            archive, members["boot/config-4.9.269-62-osmc"]
        ).decode("utf-8", errors="strict").splitlines()

    paths = set(members)
    packages = installed_packages(status)
    capabilities = {
        "architecture": "armhf",
        "vendorEgl": "opt/vero3/lib/libEGL.so.1" in paths,
        "vendorGles2": "opt/vero3/lib/libGLESv2.so.2" in paths,
        "vendorMali": "opt/vero3/lib/libMali.so" in paths,
        "vendorLibrarySearchPath": "/opt/vero3/lib" in ld_path,
        "maliFbdevMarker": b"MALI_FBDEV" in mali and b"/dev/fb0" in mali,
        "kernelFramebuffer": "CONFIG_FB=y" in kernel_config,
        "kernelDrm": "CONFIG_DRM=y" in kernel_config,
        "kernelMali400Module": "CONFIG_MALI400=m" in kernel_config,
        "kernelUserNamespaces": "CONFIG_USER_NS=y" in kernel_config,
        "gbmRuntime": has_library(paths, "libgbm.so"),
        "waylandClientRuntime": has_library(paths, "libwayland-client.so"),
        "waylandCompositor": any(
            PurePosixPath(path).name in {"weston", "cage"} for path in paths
        ),
        "wpeBackendFdo": has_library(paths, "libWPEBackend-fdo"),
        "wpeWebKit": has_library(paths, "libWPEWebKit"),
        "cogLauncher": "usr/bin/cog" in paths,
        "qtEglfsPlugin": has_library(paths, "libqeglfs.so"),
        "qtWebEngine": has_library(paths, "libQt5WebEngineCore.so"),
    }

    if not all(
        capabilities[key]
        for key in (
            "vendorEgl",
            "vendorGles2",
            "vendorMali",
            "vendorLibrarySearchPath",
            "maliFbdevMarker",
            "kernelFramebuffer",
            "kernelMali400Module",
        )
    ):
        raise ValueError("Vero vendor EGL/fbdev contract changed; review required")

    wpe_requirements = {
        "Cog": capabilities["cogLauncher"],
        "WPE WebKit": capabilities["wpeWebKit"],
        "WPEBackend-fdo": capabilities["wpeBackendFdo"],
        "Wayland client": capabilities["waylandClientRuntime"],
        "Wayland compositor": capabilities["waylandCompositor"],
        "GBM runtime": capabilities["gbmRuntime"],
        "DRM kernel API": capabilities["kernelDrm"],
    }
    qt_requirements = {
        "Qt EGLFS plugin": capabilities["qtEglfsPlugin"],
        "Qt WebEngine": capabilities["qtWebEngine"],
        "Vero vendor EGL": capabilities["vendorEgl"],
        "Vero vendor GLES2": capabilities["vendorGles2"],
        "Vero fbdev EGL marker": capabilities["maliFbdevMarker"],
        "Framebuffer kernel API": capabilities["kernelFramebuffer"],
    }

    report: dict[str, object] = {
        "schema": 1,
        "archive": str(rootfs),
        "archiveSha256": digest(rootfs),
        "entryCount": len(paths),
        "basePackages": {
            name: packages.get(name)
            for name in (
                "vero3-userland-osmc",
                "vero3-mediacenter-osmc",
                "libamcodec-osmc",
            )
        },
        "capabilities": capabilities,
        "candidates": {
            "cog-wpe-wayland": {
                "decision": "blocked-on-pinned-base",
                "requirements": wpe_requirements,
                "missing": sorted(
                    name for name, present in wpe_requirements.items() if not present
                ),
                "reason": (
                    "The Debian Cog/WPE path requires a Wayland/GBM display stack "
                    "which is absent from the pinned Vero rootfs."
                ),
            },
            "qt-webengine-eglfs": {
                "decision": "next-disabled-probe",
                "requirements": qt_requirements,
                "missing": sorted(
                    name for name, present in qt_requirements.items() if not present
                ),
                "reason": (
                    "EGLFS can own one fullscreen EGL surface without X11 or "
                    "Wayland and matches the vendor fbdev evidence, but the Qt "
                    "runtime, memory use and Vero rendering are not proven."
                ),
            },
        },
        "selectedNextProbe": "qt-webengine-eglfs",
        "bootChanges": False,
        "deviceAccess": False,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.rootfs)
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
