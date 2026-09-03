from __future__ import annotations

import importlib.util
import json
import pathlib
import struct
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def sample_fdt(emmc_status: bytes, sd_status: bytes = b"okay\0") -> bytes:
    strings = b"status\0"
    structure = bytearray()

    def token(value: int) -> None:
        structure.extend(struct.pack(">I", value))

    def begin_node(name: str) -> None:
        token(1)
        encoded = name.encode("ascii") + b"\0"
        structure.extend(encoded)
        structure.extend(bytes((-len(encoded)) % 4))

    def status(value: bytes) -> None:
        token(3)
        structure.extend(struct.pack(">II", len(value), 0))
        structure.extend(value)
        structure.extend(bytes((-len(value)) % 4))

    begin_node("")
    for name, value in (
        ("emmc@d0074000", emmc_status),
        ("sd@d0072000", sd_status),
        ("sdio@d0070000", b"okay\0"),
    ):
        begin_node(name)
        status(value)
        token(2)
    token(2)
    token(9)

    reserve_offset = 40
    struct_offset = reserve_offset + 16
    strings_offset = struct_offset + len(structure)
    total_size = strings_offset + len(strings)
    header = struct.pack(
        ">10I",
        0xD00DFEED,
        total_size,
        struct_offset,
        strings_offset,
        reserve_offset,
        17,
        16,
        0,
        len(strings),
        len(structure),
    )
    return header + bytes(16) + structure + strings


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SourceLockTests(unittest.TestCase):
    def test_source_lock_is_valid_json(self) -> None:
        data = json.loads((ROOT / "sources" / "sources.lock.json").read_text())
        self.assertEqual(data["schema"], 1)
        self.assertGreaterEqual(len(data["sources"]), 1)

    def test_every_binary_input_has_sha256(self) -> None:
        data = json.loads((ROOT / "sources" / "sources.lock.json").read_text())
        releases = [s for s in data["sources"] if s["revision_type"] == "release"]
        self.assertTrue(releases)
        self.assertTrue(all(len(source.get("sha256", "")) == 64 for source in releases))


class FetchSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fetch = load_script("fetch_verified")

    def test_only_official_download_hosts_are_allowed(self) -> None:
        self.assertEqual(
            self.fetch.safe_name("https://dl.strem.io/path/app.apk"), "app.apk"
        )
        with self.assertRaises(ValueError):
            self.fetch.safe_name("https://example.com/app.apk")

    def test_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "input"
            path.write_bytes(b"stremio-vero")
            self.assertEqual(
                self.fetch.digest(path),
                "4238de9419224e8813579ab4be59d04a09d3951f030beb87413828d66ed36e05",
            )


class SafeDtbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dtb = load_script("build_safe_dtb")

    def test_multidtb_round_trip(self) -> None:
        fdt = self.dtb.FDT_MAGIC + struct.pack(">I", 40) + bytes(32)
        entries = [
            {"chipset": "gxl", "platform": "p212", "revision": "2g", "dtb": fdt},
            {"chipset": "gxl", "platform": "p231", "revision": "2g", "dtb": fdt},
        ]
        parsed = self.dtb.parse_multidtb(self.dtb.pack_multidtb(entries))
        self.assertEqual(
            [(entry["chipset"], entry["platform"], entry["revision"]) for entry in parsed],
            [("gxl", "p212", "2g"), ("gxl", "p231", "2g")],
        )
        self.assertTrue(all(entry["dtb"] == fdt for entry in parsed))

    def test_binary_snapshot_accepts_only_emmc_status_change(self) -> None:
        original = sample_fdt(b"okay\0")
        patched = sample_fdt(b"disabled\0")
        self.dtb.assert_only_emmc_changed(original, patched)
        with self.assertRaises(ValueError):
            self.dtb.assert_only_emmc_changed(original, sample_fdt(b"broken\0"))
        with self.assertRaises(ValueError):
            self.dtb.assert_only_emmc_changed(
                original, sample_fdt(b"disabled\0", b"disabled\0")
            )


if __name__ == "__main__":
    unittest.main()
