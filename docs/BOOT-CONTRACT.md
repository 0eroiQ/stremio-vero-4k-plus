# Vero removable-boot contract

## What the official media does

Official Vero 4K/4K+ recovery media is an installer, not a live operating
system. Its removable FAT partition is labelled `OSMCInstall` and carries an
Android-format `kernel.img`, a multi-device-tree `dtb.img`, and a root
filesystem archive. Once booted, its installer writes to internal storage.

It must not be used as a safety test for this project.

## Experimental external-root hypothesis

The factory bootloader demonstrably loads the removable kernel contract. The
first project prototype will preserve only that loading contract while using a
new, non-installer initramfs that switches to a root filesystem on the same
removable medium.

Before a physical test, the prototype must meet all of these conditions:

1. The Vero 4K+ device tree disables the internal eMMC controller.
2. The initramfs contains no OSMC target installer or storage-management tool.
3. The kernel command line names the removable root by unique filesystem UUID,
   never by probe-order device name.
4. The root filesystem is immutable for the first boot; logs use RAM.
5. Offline inspection proves that internal storage cannot be enumerated from
   the prototype userspace.
6. The image writer is not part of the first release; a human reviews the raw
   image and checksum before any removable media is prepared.

This external-root path is an engineering hypothesis, not an OSMC-supported
feature. A successful build will not be described as bootable until observed
on the exact Vero 4K+ hardware.

## Required boot artifacts

- 64-bit ARM kernel matching OSMC's Vero 4K+ downstream patches.
- Multi-DTB containing the exact `vero3plus_2g_16g` board description, with an
  external-boot safety patch that disables eMMC.
- Android boot-image wrapper expected by the factory bootloader.
- Minimal non-installer initramfs.
- Separate removable root/data partitions with deterministic UUIDs.

