#!/usr/bin/env python3
"""Build a non-installing Vero boot component around a storage-blind initramfs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import struct


ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_ROOT = (ROOT / "out").resolve()
REQUIRED_INITRAMFS_FEATURES = (
    "CONFIG_BLK_DEV_INITRD",
    "CONFIG_RD_GZIP",
    "CONFIG_BINFMT_ELF",
    "CONFIG_VT_CONSOLE",
    "CONFIG_FRAMEBUFFER_CONSOLE",
    "CONFIG_AMLOGIC_SERIAL_MESON_CONSOLE",
)
EXPECTED_MULTIDTB_IDENTITIES = {
    ("gxl", "p212", "2g"),
    ("gxl", "p231", "2g"),
}


def load_sibling(name: str):
    path = pathlib.Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"vero_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load helper: {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_output(path: pathlib.Path) -> pathlib.Path:
    resolved_parent = path.parent.resolve()
    if OUT_ROOT != resolved_parent and OUT_ROOT not in resolved_parent.parents:
        raise ValueError("output must be inside the repository out directory")
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise ValueError("existing output is not a regular file")
    return path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_command_line() -> str:
    command_line = " ".join(
        (
            "rdinit=/init",
            "devtmpfs.mount=0",
            "ro",
            "rootflags=noload",
            "stremio_vero.safe_probe=1",
        )
    )
    if len(command_line.encode("ascii")) >= 512:
        raise ValueError("boot command line does not fit the legacy Vero header")
    forbidden = ("root=/", "root=PARTUUID", "install", "recovery")
    if any(value in command_line for value in forbidden):
        raise ValueError("unsafe boot command line")
    return command_line


def kernel_config_values(config: str) -> dict[str, str]:
    return {
        line.split("=", 1)[0]: line.split("=", 1)[1]
        for line in config.splitlines()
        if line.startswith("CONFIG_") and "=" in line
    }


def verify_kernel_config(config: str) -> dict[str, object]:
    values = kernel_config_values(config)
    missing = [key for key in REQUIRED_INITRAMFS_FEATURES if values.get(key) != "y"]
    if missing:
        raise ValueError(f"required initramfs kernel features are missing: {missing}")
    if values.get("CONFIG_INITRAMFS_SOURCE") != '""':
        raise ValueError("kernel has a non-empty built-in initramfs source")
    compiled = values.get("CONFIG_CMDLINE", "")
    if not (compiled.startswith('"') and compiled.endswith('"')):
        raise ValueError("kernel compiled command line is missing or malformed")
    compiled = compiled[1:-1]
    if "root=/dev/vero-nand/root" not in compiled:
        raise ValueError("kernel compiled root contract changed; safety review required")
    if values.get("CONFIG_CMDLINE_EXTEND") != "y":
        raise ValueError("kernel command-line merge mode changed; safety review required")
    if values.get("CONFIG_CMDLINE_FORCE") == "y":
        raise ValueError("kernel unexpectedly forces its compiled command line")
    return {
        "required_features": list(REQUIRED_INITRAMFS_FEATURES),
        "built_in_initramfs": "empty",
        "compiled_command_line": compiled,
        "merge_order": "bootloader-then-compiled",
        "safety_response": "initramfs-/init-prevents-root-namespace-preparation",
    }


def verify_safe_dtb(dtb_helpers, blob: bytes) -> list[str]:
    entries = dtb_helpers.parse_multidtb(blob)
    identities = {
        (str(entry["chipset"]), str(entry["platform"]), str(entry["revision"]))
        for entry in entries
    }
    if identities != EXPECTED_MULTIDTB_IDENTITIES or len(entries) != len(identities):
        raise ValueError(f"unexpected Vero multi-DTB identity set: {sorted(identities)}")
    required = {
        ("/emmc@d0074000", "status"): b"disabled\0",
        ("/sd@d0072000", "status"): b"okay\0",
        ("/sdio@d0070000", "status"): b"okay\0",
    }
    for entry in entries:
        _nodes, properties = dtb_helpers.fdt_snapshot(entry["dtb"])
        for key, expected in required.items():
            if properties.get(key) != expected:
                raise ValueError(
                    f"unsafe device-tree property for {entry['platform']}: {key}"
                )
    return sorted(identity[1] for identity in identities)


def verify_probe_initramfs(compressed: bytes, boot_helpers, ramdisk_helpers) -> dict[str, object]:
    if not compressed.startswith(boot_helpers.GZIP_MAGIC):
        raise ValueError("probe initramfs is not gzip-compressed")
    entries = boot_helpers.parse_newc(gzip.decompress(compressed))
    init_entry = entries.get("init")
    if not isinstance(init_entry, dict) or not isinstance(init_entry.get("data"), bytes):
        raise ValueError("probe initramfs has no /init")
    init = init_entry["data"]
    ramdisk_helpers.verify_archive(compressed, init, boot_helpers)
    init_helpers = load_sibling("build_probe_init")
    init_details = init_helpers.verify_probe_elf(init)
    return {
        "sha256": sha256_bytes(compressed),
        "entry_allowlist": ["/", "/dev", "/dev/console", "/init"],
        "init_sha256": init_details["sha256"],
        "init_syscalls": init_details["syscalls"],
    }


def boot_id(kernel: bytes, ramdisk: bytes, second: bytes) -> bytes:
    digest = hashlib.sha1(usedforsecurity=False)
    for component in (kernel, ramdisk, second):
        digest.update(component)
        digest.update(struct.pack("<I", len(component)))
    digest.update(struct.pack("<I", 0))
    return digest.digest() + bytes(12)


def pad(component: bytes, page_size: int) -> bytes:
    return component + bytes((-len(component)) % page_size)


def build_candidate(
    official: bytes,
    initramfs: bytes,
    safe_dtb: bytes,
    command_line: str,
    boot_helpers,
) -> tuple[bytes, bytes]:
    parsed = boot_helpers.parse_boot_image(official)
    header = parsed["header"]
    kernel = parsed["kernel"]
    if not isinstance(header, dict) or not isinstance(kernel, bytes):
        raise ValueError("invalid parsed official boot image")
    page_size = header["page_size"]
    if not isinstance(page_size, int):
        raise ValueError("invalid official page size")

    header_page = bytearray(official[:page_size])
    struct.pack_into("<I", header_page, 16, len(initramfs))
    struct.pack_into("<I", header_page, 24, len(safe_dtb))
    image_name = b"Stremio Vero 4K+"
    if len(image_name) != 16:
        raise ValueError("probe image name must exactly fill the legacy header field")
    header_page[48:64] = image_name
    header_page[64:576] = bytes(512)
    encoded_command_line = command_line.encode("ascii")
    header_page[64 : 64 + len(encoded_command_line)] = encoded_command_line
    header_page[576:608] = boot_id(kernel, initramfs, safe_dtb)
    header_page[608:1632] = bytes(1024)

    candidate = (
        bytes(header_page)
        + pad(kernel, page_size)
        + pad(initramfs, page_size)
        + pad(safe_dtb, page_size)
    )
    reparsed = boot_helpers.parse_boot_image(candidate)
    if reparsed["kernel"] != kernel:
        raise ValueError("official Vero kernel changed while building the probe")
    if reparsed["ramdisk"] != initramfs:
        raise ValueError("guarded boot probe does not contain the restricted initramfs")
    if reparsed["second"] != safe_dtb:
        raise ValueError("guarded boot probe does not contain the safe multi-DTB")
    if reparsed["header"]["command_line"] != command_line:
        raise ValueError("guarded boot command line did not round-trip")
    if len(candidate) % page_size:
        raise ValueError("guarded boot probe is not page-aligned")
    return candidate, kernel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-deb", type=pathlib.Path, required=True)
    parser.add_argument("--safe-dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    output = safe_output(
        (ROOT / args.output).resolve() if not args.output.is_absolute() else args.output
    )

    dtb_helpers = load_sibling("build_safe_dtb")
    boot_helpers = load_sibling("inspect_boot_image")
    ramdisk_helpers = load_sibling("build_probe_initramfs")
    package = args.kernel_deb.read_bytes()
    data_tar = dtb_helpers.ar_member(package, "data.tar.xz")
    official = dtb_helpers.tar_member_xz(data_tar, "boot/kernel-4.9.269-62-osmc.img")
    config = dtb_helpers.tar_member_xz(
        data_tar, "boot/config-4.9.269-62-osmc"
    ).decode("utf-8")
    kernel_contract = verify_kernel_config(config)
    safe_dtb = args.safe_dtb.read_bytes()
    protected_platforms = verify_safe_dtb(dtb_helpers, safe_dtb)
    initramfs = args.initramfs.read_bytes()
    initramfs_details = verify_probe_initramfs(
        initramfs, boot_helpers, ramdisk_helpers
    )
    command_line = safe_command_line()
    candidate, kernel = build_candidate(
        official, initramfs, safe_dtb, command_line, boot_helpers
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(candidate)
    manifest = {
        "schema": 1,
        "artifact": output.name,
        "sha256": sha256_bytes(candidate),
        "source_package_sha256": sha256_bytes(package),
        "source_kernel_sha256": sha256_bytes(kernel),
        "kernel_contract": kernel_contract,
        "safe_multidtb_sha256": sha256_bytes(safe_dtb),
        "emmc_disabled_platforms": protected_platforms,
        "command_line": command_line,
        "initramfs": initramfs_details,
        "storage_access": "none-by-probe-init",
        "artifact_scope": "boot-component-only-not-a-disk-image",
        "pre_kernel_removable_boot_path_verified": False,
        "physical_boot_tested": False,
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"guarded Vero boot component: PASS ({manifest['sha256']})")
    print("initramfs: STORAGE-BLIND")
    print(f"eMMC-disabled DTB entries: {', '.join(protected_platforms)}")
    print(f"artifact: {output}")
    print("physical boot status: NOT TESTED")


if __name__ == "__main__":
    main()
