# Build prerequisites

The project currently prepares two different build classes:

- **Kernel/boot probe:** exact Vero kernel, eMMC-disabled device tree, minimal
  initramfs, and offline boot-component assembly. The current CI job needs only
  a small workspace; a later full kernel rebuild should reserve at least 20 GiB.
- **Android TV runtime:** AOSP/LineageOS source, Vero device definition, and
  userspace integration. Reserve at least 180 GiB before sources are fetched.

Check the host without installing anything:

```sh
python3 scripts/preflight.py --profile kernel
python3 scripts/preflight.py --profile aosp
```

Fetch only the checksummed official binary inputs into the ignored local cache:

```sh
make fetch-inputs
```

The fetcher accepts only `https://apt.osmc.tv` and `https://dl.strem.io` and
refuses an input whose SHA-256 differs from `sources/sources.lock.json`.

Inspect the official Android boot-image container without extracting or
executing its contents:

```sh
make inspect-boot
```

The generated JSON records the boot header and component hashes. It must also
reject reuse of the original OSMC ramdisk because that ramdisk defaults to an
internal MMC device, includes filesystem-repair programs, prepares a writable
root, and exposes a rescue shell. Those are valid OSMC behaviors but violate
this project's external-only first-boot boundary.

## eMMC-disabled device tree

Install `dtc`, `fdtget`, and `fdtput` from the Device Tree Compiler package,
then run:

```sh
make safe-dtb
```

This does not create or write removable media. It creates a regular Amlogic
multi-DTB file and JSON manifest only beneath `out/boot-probe/`. The builder
disables eMMC independently in the included `p212` and `p231` trees, confirms
that SD and SDIO remain enabled, and compares every node and property to prove
that no other semantic device-tree value changed.

## Storage-blind initramfs

The CI runner installs GNU AArch64 binutils and QEMU user emulation. It records
their versions, builds `probe/init.S` twice in clean temporary directories, and
rejects different bytes from that same toolchain. This proves same-run
determinism; cross-toolchain reproducibility remains a later gate. The resulting
static ELF is rejected if it has a loader, dynamic
segment, writable-executable segment, executable stack, unexpected marker, or
anything except the two allowed syscall sites. QEMU must print the exact probe
marker and observe only `write` and `nanosleep`.

The deterministic newc archive has exactly four entries: `/`, `/dev`, the
console character device, and `/init`. It has no shell, utility suite, modules,
firmware, network stack, service manager, or storage tool.

## Guarded Vero boot component

Build the Android-format boot component:

```sh
make boot-probe
```

The result stays beneath `out/boot-probe/`. It reuses the checksummed official
compressed kernel unchanged, replaces the original OSMC ramdisk with the
storage-blind initramfs, embeds the all-entry eMMC-disabled multi-DTB, and adds
no root target. The result is not a disk image and cannot be written by any
repository command.

## Why `make image` is still blocked

The exact television UI requires Android, but OSMC does not publish an Android
board support package for Vero 4K+. Producing a black-screen image before its
graphics, input, and boot contracts are defined would not be useful evidence.

The image target will be enabled only after:

1. the all-entry eMMC-disabled DTB and storage-blind component pass CI;
2. the deployed Vero bootloader's exact removable path is proven not to write
   before Linux starts;
3. a minimal read-only external Android root is designed and inspected; and
4. the Android board/runtime source set is pinned.
