# Vero removable-boot contract

## What the official media does

Official Vero 4K/4K+ recovery media is an installer, not a live operating
system. Its removable FAT partition is labelled `OSMCInstall` and carries an
Android-format `kernel.img`, a multi-device-tree `dtb.img`, and a root
filesystem archive. Once booted, its installer writes to internal storage.

It must not be used as a safety test for this project.

## Offline kernel-entry probe

The factory bootloader demonstrably loads the removable Android boot-image
contract. The first project artifact preserves the container format but stops
inside a new storage-blind initramfs. It does not mount or discover any root
filesystem.

Before a physical test, the prototype must meet all of these conditions:

1. Every device tree in the multi-DTB disables the internal eMMC controller.
2. The initramfs contains only `/`, `/dev`, `/dev/console`, and `/init`.
3. `/init` is a static AArch64 program with only `write` and `nanosleep`
   syscall sites; it cannot open, mount, inspect, or modify storage.
4. The kernel command line specifies `rdinit=/init` and no root target.
5. The image writer, partition table, filesystem, installer, and update script
   are absent.
6. The pre-kernel bootloader path is proven read-only before any removable
   medium is prepared.

This external-root path is an engineering hypothesis, not an OSMC-supported
feature. A successful build will not be described as bootable until observed
on the exact Vero 4K+ hardware.

## Required boot artifacts

- 64-bit ARM kernel matching OSMC's Vero 4K+ downstream patches.
- The official two-entry multi-DTB, with the eMMC controller disabled in both
  the `p212` and `p231` entries so a wrong selection also fails closed.
- Android boot-image wrapper expected by the factory bootloader.
- Deterministic gzip/newc initramfs containing only the storage-blind PID 1 and
  its console device.
- No root/data partitions at this stage.

## First completed component

`make safe-dtb` now reproduces the official two-entry Amlogic multi-DTB and
changes only the eMMC controller status from `okay` to `disabled` in both
`gxl/p212/2g` and `gxl/p231/2g`. SD and SDIO remain `okay`, and a semantic
before/after comparison rejects any additional node, property, index, order,
or identity change.

This is offline structural evidence only. It does not prove that the factory
bootloader will select or boot the modified tree, and it is not permission to
prepare removable media.

`make boot-probe` cross-assembles the tiny PID 1 twice with the same recorded
toolchain, requires identical bytes, validates its ELF headers and exact syscall sites, executes it under
QEMU, packs the four-entry initramfs deterministically, and combines it with
the unchanged official compressed kernel and protected multi-DTB. The builder
then parses its own output and rejects any component or command-line mismatch.

The pinned official kernel appends a compiled internal-root parameter after
bootloader parameters. A direct external-root command line is therefore not a
safe or functional design. The probe instead supplies `/init` inside the
initramfs; the audited kernel runs that early userspace before preparing any
root namespace, and the program never returns.

## Official boot-image inspection

`make inspect-boot` verifies that the current official Vero kernel package uses
an Android boot header v1 with 2048-byte pages, a gzip-compressed kernel and
ramdisk, and the Amlogic multi-DTB as its second component. It records the exact
addresses, sizes, and hashes without executing or extracting them to the host
filesystem.

The inspection deliberately rejects the bundled OSMC ramdisk for this project:
its normal job includes selecting internal MMC by default, filesystem repair,
a writable root mount, and a rescue shell. The guarded probe replaces it with
the four-entry storage-blind initramfs described above.

## Unresolved pre-kernel blocker

The pinned public U-Boot recovery source contains a path that can clear part of
internal `instaboot` before `bootm`. That path looks for `recovery.img`, not the
offline component built here. However, OSMC later shipped an encrypted,
binary-only bootloader update specifically mentioning that problem, and the
deployed removable-boot behavior cannot be reconstructed from readable source.

Therefore this repository does not create recovery media, an autoscript, a FAT
image, or a media writer. A physical test remains blocked until the exact
deployed boot environment is inspected read-only and a kernel-loading path is
shown not to execute any pre-kernel write.
