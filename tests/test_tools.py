from __future__ import annotations

import importlib.util
import gzip
import json
import pathlib
import struct
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def sample_fdt(
    emmc_status: bytes,
    sd_status: bytes = b"okay\0",
    sdio_status: bytes = b"okay\0",
) -> bytes:
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
        ("sdio@d0070000", sdio_status),
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
        self.assertEqual(
            self.fetch.safe_name(
                "https://ftp.fau.de/osmc/osmc/download/installers/diskimages/vero.img.gz"
            ),
            "vero.img.gz",
        )
        self.assertEqual(
            self.fetch.safe_name(
                "https://nodejs.org/dist/v18.12.1/node-v18.12.1-linux-armv7l.tar.xz"
            ),
            "node-v18.12.1-linux-armv7l.tar.xz",
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


class StremioServiceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prepare = load_script("prepare_stremio_service")
        cls.audit = load_script("audit_stremio_service")

    @staticmethod
    def armhf_elf(glibc: bytes = b"GLIBC_2.28") -> bytes:
        payload = bytearray(52)
        payload[:6] = b"\x7fELF\x01\x01"
        struct.pack_into("<H", payload, 18, 40)
        return bytes(payload) + b"/lib/ld-linux-armhf.so.3\0" + glibc

    def test_armhf_node_contract(self) -> None:
        details = self.prepare.verify_armhf_node(self.armhf_elf())
        self.assertEqual(details["machine"], "ARM")
        self.assertEqual(details["abi"], "armhf")
        self.assertEqual(details["maximumGlibc"], "2.28")

    def test_node_contract_rejects_wrong_architecture_and_new_glibc(self) -> None:
        wrong_machine = bytearray(self.armhf_elf())
        struct.pack_into("<H", wrong_machine, 18, 62)
        with self.assertRaisesRegex(ValueError, "wrong ELF machine"):
            self.prepare.verify_armhf_node(bytes(wrong_machine))
        with self.assertRaisesRegex(ValueError, "newer than OSMC"):
            self.prepare.verify_armhf_node(self.armhf_elf(b"GLIBC_2.32"))

    def test_server_bundle_contract(self) -> None:
        payload = b"x" * (1024 * 1024) + b"EngineFS FFMPEG_BIN FFPROBE_BIN 11470"
        details = self.prepare.verify_server_js(payload)
        self.assertEqual(details["httpPort"], 11470)
        with self.assertRaisesRegex(ValueError, "missing expected markers"):
            self.prepare.verify_server_js(b"x" * (1024 * 1024))

    def test_tar_paths_and_elf_audit_are_strict(self) -> None:
        self.assertTrue(self.prepare.safe_tar_member("node/bin/node"))
        self.assertFalse(self.prepare.safe_tar_member("../node"))
        self.assertFalse(self.prepare.safe_tar_member("/node"))
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "node"
            path.write_bytes(self.armhf_elf())
            details = self.audit.elf_details(path)
            self.assertEqual(details["machine"], "ARM")
            self.assertEqual(details["bits"], 32)


class BootProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.boot = load_script("build_boot_probe")

    def test_probe_command_line_has_no_root_target(self) -> None:
        command_line = self.boot.safe_command_line()
        self.assertEqual(
            command_line,
            "rdinit=/init devtmpfs.mount=0 ro rootflags=noload "
            "stremio_vero.safe_probe=1",
        )
        self.assertNotIn("root=/", command_line)
        self.assertNotIn("PARTUUID", command_line)

    def test_kernel_config_requires_initramfs_and_known_merge_hazard(self) -> None:
        config = "\n".join(
            (
                "CONFIG_BLK_DEV_INITRD=y",
                "CONFIG_RD_GZIP=y",
                "CONFIG_BINFMT_ELF=y",
                "CONFIG_VT_CONSOLE=y",
                "CONFIG_FRAMEBUFFER_CONSOLE=y",
                "CONFIG_AMLOGIC_SERIAL_MESON_CONSOLE=y",
                'CONFIG_INITRAMFS_SOURCE=""',
                'CONFIG_CMDLINE="quiet root=/dev/vero-nand/root console=tty0"',
                "CONFIG_CMDLINE_EXTEND=y",
                "# CONFIG_CMDLINE_FORCE is not set",
            )
        )
        contract = self.boot.verify_kernel_config(config)
        self.assertEqual(contract["merge_order"], "bootloader-then-compiled")
        self.assertIn("root=/dev/vero-nand/root", contract["compiled_command_line"])
        with self.assertRaises(ValueError):
            self.boot.verify_kernel_config(config.replace("CONFIG_RD_GZIP=y", ""))
        with self.assertRaises(ValueError):
            self.boot.verify_kernel_config(config + "\nCONFIG_CMDLINE_FORCE=y")
        with self.assertRaises(ValueError):
            self.boot.verify_kernel_config(
                config.replace('CONFIG_INITRAMFS_SOURCE=""', 'CONFIG_INITRAMFS_SOURCE="payload"')
            )

    def test_safe_multidtb_requires_every_entry_to_disable_emmc(self) -> None:
        dtb = load_script("build_safe_dtb")
        entries = [
            {
                "chipset": "gxl",
                "platform": platform,
                "revision": "2g",
                "dtb": sample_fdt(b"disabled\0"),
            }
            for platform in ("p212", "p231")
        ]
        self.assertEqual(
            self.boot.verify_safe_dtb(dtb, dtb.pack_multidtb(entries)),
            ["p212", "p231"],
        )
        entries[0]["dtb"] = sample_fdt(b"okay\0")
        with self.assertRaises(ValueError):
            self.boot.verify_safe_dtb(dtb, dtb.pack_multidtb(entries))

    def test_boot_component_round_trips_every_guarded_component(self) -> None:
        dtb = load_script("build_safe_dtb")
        inspect = load_script("inspect_boot_image")
        ramdisk = load_script("build_probe_initramfs")
        safe_multidtb = dtb.pack_multidtb(
            [
                {
                    "chipset": "gxl",
                    "platform": platform,
                    "revision": "2g",
                    "dtb": sample_fdt(b"disabled\0"),
                }
                for platform in ("p212", "p231")
            ]
        )
        initramfs = ramdisk.deterministic_gzip(
            ramdisk.build_newc(sample_probe_elf())
        )
        kernel = gzip.compress(b"synthetic-kernel", mtime=0)
        official_ramdisk = gzip.compress(b"synthetic-official-ramdisk", mtime=0)
        page_size = 2048
        header = bytearray(page_size)
        header[:8] = inspect.ANDROID_MAGIC
        struct.pack_into(
            "<10I",
            header,
            8,
            len(kernel),
            0x01080000,
            len(official_ramdisk),
            0x01000000,
            len(safe_multidtb),
            0x01000000,
            0x01000100,
            page_size,
            1,
            0,
        )
        struct.pack_into("<I", header, 1644, 1648)
        pad = lambda value: value + bytes((-len(value)) % page_size)
        official = (
            bytes(header)
            + pad(kernel)
            + pad(official_ramdisk)
            + pad(safe_multidtb)
        )
        candidate, preserved_kernel = self.boot.build_candidate(
            official,
            initramfs,
            safe_multidtb,
            self.boot.safe_command_line(),
            inspect,
        )
        parsed = inspect.parse_boot_image(candidate)
        self.assertEqual(preserved_kernel, kernel)
        self.assertEqual(parsed["kernel"], kernel)
        self.assertEqual(parsed["ramdisk"], initramfs)
        self.assertEqual(parsed["second"], safe_multidtb)


def sample_probe_elf() -> bytes:
    init = load_script("build_probe_init")
    ident = bytearray(16)
    ident[:6] = b"\x7fELF\x02\x01"
    header = init.ELF_HEADER.pack(
        bytes(ident),
        init.ET_EXEC,
        init.EM_AARCH64,
        1,
        0x400000,
        init.ELF_HEADER.size,
        0,
        0,
        init.ELF_HEADER.size,
        init.PROGRAM_HEADER.size,
        2,
        0,
        0,
        0,
    )
    code = struct.pack(
        "<4I",
        init.MOV_X8_WRITE,
        init.SVC_ZERO,
        init.MOV_X8_NANOSLEEP,
        init.SVC_ZERO,
    )
    code_offset = 0x100
    executable = init.PROGRAM_HEADER.pack(
        init.PT_LOAD,
        5,
        code_offset,
        0x400000,
        0x400000,
        len(code),
        len(code),
        0x1000,
    )
    stack = init.PROGRAM_HEADER.pack(
        init.PT_GNU_STACK,
        6,
        0,
        0,
        0,
        0,
        0,
        16,
    )
    prefix = header + executable + stack
    return prefix + bytes(code_offset - len(prefix)) + code + init.MARKER


class ProbeInitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.init = load_script("build_probe_init")

    def test_static_probe_allows_only_two_syscall_sites(self) -> None:
        details = self.init.verify_probe_elf(sample_probe_elf())
        self.assertEqual(details["syscalls"], ["write", "nanosleep"])
        with self.assertRaises(ValueError):
            self.init.verify_probe_elf(
                sample_probe_elf().replace(
                    struct.pack("<I", self.init.MOV_X8_NANOSLEEP),
                    struct.pack("<I", 0xD2800008),
                    1,
                )
            )
        with self.assertRaisesRegex(ValueError, "nonzero immediate"):
            self.init.verify_probe_elf(
                sample_probe_elf().replace(
                    struct.pack("<I", self.init.SVC_ZERO),
                    struct.pack("<I", self.init.SVC_ZERO | (1 << 5)),
                    1,
                )
            )


class ProbeInitramfsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ramdisk = load_script("build_probe_initramfs")
        cls.boot = load_script("inspect_boot_image")

    def test_archive_is_deterministic_and_exactly_allowlisted(self) -> None:
        init = sample_probe_elf()
        first = self.ramdisk.deterministic_gzip(self.ramdisk.build_newc(init))
        second = self.ramdisk.deterministic_gzip(self.ramdisk.build_newc(init))
        self.assertEqual(first, second)
        entries = self.ramdisk.verify_archive(first, init, self.boot)
        self.assertEqual(
            [entry["path"] for entry in entries],
            ["/", "/dev", "/dev/console", "/init"],
        )
        noncanonical = bytearray(first)
        noncanonical[4] = 1
        with self.assertRaisesRegex(ValueError, "canonical"):
            self.ramdisk.verify_archive(bytes(noncanonical), init, self.boot)


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
        with self.assertRaises(ValueError):
            self.dtb.assert_only_emmc_changed(
                original,
                sample_fdt(b"disabled\0", sdio_status=b"disabled\0"),
            )

    def test_every_multidtb_entry_is_patched_and_verified(self) -> None:
        official = [
            {
                "chipset": "gxl",
                "platform": platform,
                "revision": "2g",
                "dtb": sample_fdt(b"okay\0"),
            }
            for platform in ("p212", "p231")
        ]
        patched_indexes: list[int] = []

        def patcher(index: int, _entry: dict[str, object]) -> bytes:
            patched_indexes.append(index)
            return sample_fdt(b"disabled\0")

        patched = self.dtb.patch_all_entries(official, patcher)
        self.assertEqual(patched_indexes, [0, 1])
        self.dtb.assert_all_entries_safely_patched(official, patched)
        self.assertTrue(
            all(
                self.dtb.fdt_snapshot(entry["dtb"])[1][self.dtb.EMMC_STATUS]
                == b"disabled\0"
                for entry in patched
            )
        )

    def test_all_entry_guard_rejects_one_unpatched_entry(self) -> None:
        official = [
            {
                "chipset": "gxl",
                "platform": platform,
                "revision": "2g",
                "dtb": sample_fdt(b"okay\0"),
            }
            for platform in ("p212", "p231")
        ]
        patched = [
            {**official[0], "dtb": sample_fdt(b"disabled\0")},
            dict(official[1]),
        ]
        with self.assertRaisesRegex(ValueError, "unsafe multi-DTB entry 1"):
            self.dtb.assert_all_entries_safely_patched(official, patched)

    def test_all_entry_guard_rejects_changed_index(self) -> None:
        official = [
            {
                "chipset": "gxl",
                "platform": "p212",
                "revision": "2g",
                "dtb": sample_fdt(b"okay\0"),
            }
        ]
        patched = [
            {
                **official[0],
                "platform": "p231",
                "dtb": sample_fdt(b"disabled\0"),
            }
        ]
        with self.assertRaisesRegex(ValueError, "index changed"):
            self.dtb.assert_all_entries_safely_patched(official, patched)


if __name__ == "__main__":
    unittest.main()
