from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_launcher():
    path = ROOT / "runtime" / "kiosk" / "launcher.py"
    spec = importlib.util.spec_from_file_location("kiosk_launcher", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KioskLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.launcher = load_launcher()

    def test_environment_uses_vendor_fbdev_egl_without_desktop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = self.launcher.kiosk_environment(
                root / "state", root / "cache", root / "runtime"
            )
            expected = {
                "QT_QPA_PLATFORM": "eglfs",
                "QT_QPA_EGLFS_INTEGRATION": "none",
                "QT_QPA_EGLFS_FB": "/dev/fb0",
                "QT_QPA_EGLFS_FORCEVSYNC": "1",
            }
            for name, value in expected.items():
                self.assertEqual(environment[name], value)
            self.assertNotIn("DISPLAY", environment)
            self.assertNotIn("WAYLAND_DISPLAY", environment)
            for name in ("state", "cache", "runtime"):
                self.assertEqual((root / name).stat().st_mode & 0o777, 0o700)

    def test_command_rejects_symlinks_and_missing_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "qmlscene"
            executable.write_bytes(b"fixture")
            executable.chmod(0o755)
            qml = root / "main.qml"
            qml.write_text("fixture", encoding="utf-8")
            self.assertEqual(
                self.launcher.kiosk_command(executable, qml),
                (str(executable), str(qml)),
            )
            linked = root / "linked.qml"
            linked.symlink_to(qml)
            with self.assertRaisesRegex(ValueError, "regular file"):
                self.launcher.kiosk_command(executable, linked)
            with self.assertRaisesRegex(ValueError, "regular file"):
                self.launcher.kiosk_command(root / "missing", qml)

    def test_launcher_parses_as_osmc_python_3_9(self) -> None:
        source = (ROOT / "runtime" / "kiosk" / "launcher.py").read_text()
        ast.parse(source, feature_version=(3, 9))

    def test_probe_is_packaged_but_cannot_start_or_autostart(self) -> None:
        manifest = json.loads((ROOT / "rootfs-overlay" / "manifest.json").read_text())
        files = {entry["target"] for entry in manifest["files"]}
        links = {entry["target"] for entry in manifest["symlinks"]}
        unit_target = "etc/systemd/system/stremio-vero-kiosk-probe.service"
        self.assertIn(unit_target, files)
        self.assertNotIn(
            "etc/systemd/system/multi-user.target.wants/"
            "stremio-vero-kiosk-probe.service",
            links,
        )
        unit = (
            ROOT / "rootfs-overlay" / "stremio-vero-kiosk-probe.service"
        ).read_text()
        self.assertIn("RefuseManualStart=yes", unit)
        self.assertIn("ConditionPathExists=/usr/lib/qt5/bin/qmlscene", unit)
        self.assertIn("User=osmc", unit)

    def test_qml_loads_only_the_local_official_web_bundle(self) -> None:
        qml = (ROOT / "runtime" / "kiosk" / "main.qml").read_text()
        self.assertIn('url: "http://127.0.0.1:8765/"', qml)
        self.assertIn("Window.FullScreen", qml)
        self.assertNotIn("https://", qml)


if __name__ == "__main__":
    unittest.main()
