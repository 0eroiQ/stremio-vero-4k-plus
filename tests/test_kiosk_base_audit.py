from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_script():
    path = ROOT / "scripts" / "audit_kiosk_base.py"
    spec = importlib.util.spec_from_file_location("audit_kiosk_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class KioskBaseAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit_module = load_script()

    def fixture(self, *, mali: bytes = b"MALI_FBDEV\0/dev/fb0\0") -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        output = Path(directory.name) / "filesystem.tar.xz"
        entries = {
            "boot/config-4.9.269-62-osmc": (
                b"CONFIG_USER_NS=y\n"
                b"# CONFIG_DRM is not set\n"
                b"CONFIG_FB=y\n"
                b"CONFIG_MALI400=m\n"
            ),
            "etc/ld.so.conf.d/000-vero3.conf": b"/opt/vero3/lib\n",
            "opt/vero3/lib/libEGL.so.1": b"egl",
            "opt/vero3/lib/libGLESv2.so.2": b"gles",
            "opt/vero3/lib/libMali.so": mali,
            "usr/lib/kodi/kodi.bin": b"kodi",
            "usr/share/wayland-sessions/kodi-gbm.desktop": b"Exec=kodi-standalone",
            "var/lib/dpkg/status": (
                b"Package: vero3-userland-osmc\n"
                b"Status: install ok installed\n"
                b"Version: 2.0.5\n\n"
                b"Package: vero3-mediacenter-osmc\n"
                b"Status: install ok installed\n"
                b"Version: 21.1.0-9\n\n"
                b"Package: libamcodec-osmc\n"
                b"Status: install ok installed\n"
                b"Version: 2.3.0-1\n"
            ),
        }
        with tarfile.open(output, "w:xz") as archive:
            for name, payload in entries.items():
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        return output

    def test_fbdev_base_blocks_wayland_and_selects_eglfs_probe(self) -> None:
        report = self.audit_module.audit(self.fixture())
        self.assertEqual(report["selectedNextProbe"], "qt-webengine-eglfs")
        self.assertFalse(report["bootChanges"])
        self.assertFalse(report["deviceAccess"])
        self.assertTrue(report["capabilities"]["maliFbdevMarker"])
        self.assertTrue(report["capabilities"]["kernelFramebuffer"])
        self.assertFalse(report["capabilities"]["kernelDrm"])
        self.assertEqual(
            report["candidates"]["cog-wpe-wayland"]["decision"],
            "blocked-on-pinned-base",
        )
        self.assertIn(
            "Wayland compositor",
            report["candidates"]["cog-wpe-wayland"]["missing"],
        )
        self.assertIn(
            "DRM kernel API",
            report["candidates"]["cog-wpe-wayland"]["missing"],
        )

    def test_changed_vendor_contract_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "vendor EGL/fbdev contract changed"):
            self.audit_module.audit(self.fixture(mali=b"different driver"))

    def test_package_parser_ignores_uninstalled_entries(self) -> None:
        packages = self.audit_module.installed_packages(
            "Package: present\nStatus: install ok installed\nVersion: 1\n\n"
            "Package: absent\nStatus: deinstall ok config-files\nVersion: 2\n"
        )
        self.assertEqual(packages, {"present": "1"})
