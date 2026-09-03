from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_launcher():
    path = ROOT / "runtime" / "stremio_service" / "launcher.py"
    spec = importlib.util.spec_from_file_location("stremio_service_launcher", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StremioServiceLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.launcher = load_launcher()
        cls.defaults = ROOT / "runtime" / "stremio_service" / "default-server-settings.json"

    def test_initial_settings_use_private_cache_and_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            cache = root / "cache"
            target = self.launcher.create_initial_settings(state, self.defaults, cache)
            data = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(data["cacheRoot"], str(cache))
            self.assertEqual(data["cacheSize"], 2 * 1024 * 1024 * 1024)
            self.assertFalse(data["localAddonEnabled"])
            target.write_text('{"cacheSize":0}\n', encoding="utf-8")
            self.launcher.create_initial_settings(state, self.defaults, cache)
            self.assertEqual(target.read_text(encoding="utf-8"), '{"cacheSize":0}\n')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_launcher_parses_as_osmc_python_3_9(self) -> None:
        source = (
            ROOT / "runtime" / "stremio_service" / "launcher.py"
        ).read_text(encoding="utf-8")
        ast.parse(source, feature_version=(3, 9))

    def test_existing_settings_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            cache = root / "cache"
            state.mkdir()
            destination = root / "outside.json"
            destination.write_text("{}", encoding="utf-8")
            (state / "server-settings.json").symlink_to(destination)
            with self.assertRaisesRegex(ValueError, "not a regular file"):
                self.launcher.create_initial_settings(state, self.defaults, cache)

    def test_environment_is_fixed_to_local_web_and_packaged_media_tools(self) -> None:
        environment = self.launcher.service_environment(
            Path("/state"),
            Path("/cache"),
            Path("/service/ffmpeg"),
            Path("/service/ffprobe"),
            "http://127.0.0.1:8765/",
        )
        expected = {
            "APP_PATH": "/state",
            "SETTINGS_PATH": "/state",
            "HOME": "/state",
            "XDG_CACHE_HOME": "/cache",
            "FFMPEG_BIN": "/service/ffmpeg",
            "FFPROBE_BIN": "/service/ffprobe",
            "WEBUI_LOCATION": "http://127.0.0.1:8765/",
            "CASTING_DISABLED": "1",
            "NO_HTTPS_SERVER": "1",
            "NO_CORS": "1",
        }
        for name, value in expected.items():
            self.assertEqual(environment[name], value)

    def test_native_and_emulated_commands_are_explicit(self) -> None:
        runtime = Path("/service/node")
        server = Path("/service/server.js")
        program, command = self.launcher.service_command(runtime, server)
        self.assertEqual(program, runtime)
        self.assertEqual(command, ("/service/node", "/service/server.js"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            emulator = root / "qemu-arm"
            emulator.write_bytes(b"fixture")
            sysroot = root / "sysroot"
            sysroot.mkdir()
            program, command = self.launcher.service_command(
                runtime, server, emulator, sysroot
            )
            self.assertEqual(program, emulator)
            self.assertEqual(
                command,
                (
                    str(emulator),
                    "-L",
                    str(sysroot),
                    "/service/node",
                    "/service/server.js",
                ),
            )

    def test_service_unit_is_packaged_but_not_enabled(self) -> None:
        manifest = json.loads((ROOT / "rootfs-overlay" / "manifest.json").read_text())
        files = {entry["target"] for entry in manifest["files"]}
        links = {entry["target"] for entry in manifest["symlinks"]}
        self.assertIn("etc/systemd/system/stremio-vero-service.service", files)
        self.assertNotIn(
            "etc/systemd/system/multi-user.target.wants/stremio-vero-service.service",
            links,
        )
        unit = (ROOT / "rootfs-overlay" / "stremio-vero-service.service").read_text()
        for directive in (
            "User=osmc",
            "ProtectSystem=strict",
            "PrivateDevices=true",
            "NoNewPrivileges=true",
            "CapabilityBoundingSet=",
        ):
            self.assertIn(directive, unit)


if __name__ == "__main__":
    unittest.main()
