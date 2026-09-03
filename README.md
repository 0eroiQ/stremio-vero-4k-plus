# Stremio for Vero 4K+

An independent, experimental effort to run a television-first Stremio
experience on the OSMC Vero 4K+ hardware.

> [!WARNING]
> There is no boot-validated image yet. Do not write anything from this
> repository to a Vero, microSD card, USB drive, or internal eMMC.

## Goal

- Boot directly into the television interface controlled with a D-pad remote.
- Use the user's real Stremio account, add-ons, library, and watch progress.
- Preserve Vero hardware video decoding, HDMI audio, HDR, CEC, networking, and
  Bluetooth where the hardware and upstream drivers support them.
- Provide a remote-friendly **Vero Settings** screen to replace the day-to-day
  device-management functions normally exposed by My OSMC.
- Keep Kodi and a desktop environment out of the final appliance interface.

## Current stage

Stage 0: upstream provenance and safety scaffolding. The public repository and
CI checks are active. The project now builds an offline-only Vero boot component
from the unchanged official kernel, a storage-blind four-entry initramfs, and a
multi-DTB in which eMMC is disabled for both possible Vero entries. It is not a
disk image, is not a Stremio runtime, and has not been tested on hardware.

Physical media remains blocked. The readable upstream U-Boot recovery path can
modify an internal `instaboot` area before Linux starts, while the currently
distributed Vero bootloader contains a binary-only OSMC fix whose exact boot
flow cannot be verified from public source. A DTB or initramfs cannot guard an
action that happens before the kernel starts.

The TV interface in the project reference is the official Stremio Android TV
experience. The open-source Stremio Linux shell is a desktop client and is not
being presented as an equivalent. The selected direction is a Vero-specific
Android TV/AOSP runtime that installs an unmodified official Stremio TV APK
from Stremio's own download server on first run. The APK will not be committed,
mirrored, modified, or re-signed by this project.

## Safety boundary

The first hardware artifact will be external-boot-only. It must contain no
installer, flasher, partitioner, eMMC write service, or automatic migration.
Every build and test gate is documented in [docs/SAFETY.md](docs/SAFETY.md).
Recorded CI hashes and their exact scope are in
[docs/OFFLINE-EVIDENCE.md](docs/OFFLINE-EVIDENCE.md).

## Project status

| Component | Status |
| --- | --- |
| Repository and CI safety checks | Passing |
| Official Vero boot-container analysis | Passing; original writable ramdisk rejected |
| All-entry eMMC-disabled Vero multi-DTB | Reproducible offline; hardware not tested |
| Storage-blind initramfs | Four entries; `/init` permits only `write` and `nanosleep` |
| Guarded Vero boot component | Offline CI build only; hardware not tested |
| Pre-kernel removable boot path | Blocked; deployed bootloader flow is not publicly auditable |
| Exact Vero 4K+ upstream source lock | Researching |
| Stremio TV runtime/distribution path | Android TV route selected; licensing gate open |
| Reproducible root filesystem | Not started |
| Bootable external image | Not built |
| Physical Vero boot | Not attempted |
| 4K/HDR/audio/remote validation | Not attempted |

## Development

Run the non-destructive repository checks:

```sh
make check
```

After installing the Device Tree Compiler tools, reproduce the first guarded
boot component beneath the ignored `out/` directory:

```sh
make safe-dtb
```

The builder reads the checksummed official kernel package, changes only the
eMMC `status` property in both included device trees, verifies that SD and SDIO
remain enabled, and writes a checksum manifest marked
`physical_boot_tested: false`.

Inspect the official Vero Android boot wrapper and confirm that its original
OSMC ramdisk is unsuitable for this external-only prototype:

```sh
make inspect-boot
```

On a Linux builder with the documented cross tools, build the storage-blind
initramfs and guarded Android-format Vero component as regular files beneath
`out/`:

```sh
make boot-probe
```

This target does not create a partition table, disk image, or write to any
device. Its manifest records `artifact_scope` as
`boot-component-only-not-a-disk-image`.

Do not rename or copy this component to removable media. Its only current
purpose is offline structural verification.

`make image` intentionally refuses to run until the upstream inputs and image
layout are reviewed and locked.

## Upstream projects

This project depends on work by Stremio and OSMC. It is not affiliated with,
endorsed by, or supported by either project. No Stremio APK, OSMC binary,
device firmware, keys, or proprietary blobs are committed here. “Stremio” and
“OSMC” remain the property of their respective owners.
