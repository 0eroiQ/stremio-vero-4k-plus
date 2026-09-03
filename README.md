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

Stage 0: upstream provenance and safety scaffolding.

The TV interface in the project reference is the official Stremio Android TV
experience. The open-source Stremio Linux shell is a desktop client and is not
being presented as an equivalent. Before an image is produced, this project
must establish a permitted distribution path for the official TV application
and an exact, reproducible Vero 4K+ boot/runtime base.

## Safety boundary

The first hardware artifact will be external-boot-only. It must contain no
installer, flasher, partitioner, eMMC write service, or automatic migration.
Every build and test gate is documented in [docs/SAFETY.md](docs/SAFETY.md).

## Project status

| Component | Status |
| --- | --- |
| Repository and CI safety checks | In progress |
| Exact Vero 4K+ upstream source lock | Researching |
| Stremio TV runtime/distribution path | Researching |
| Reproducible root filesystem | Not started |
| Bootable external image | Not built |
| Physical Vero boot | Not attempted |
| 4K/HDR/audio/remote validation | Not attempted |

## Development

Run the non-destructive repository checks:

```sh
make check
```

`make image` intentionally refuses to run until the upstream inputs and image
layout are reviewed and locked.

## Upstream projects

This project depends on work by Stremio and OSMC. It is not affiliated with,
endorsed by, or supported by either project. No Stremio APK, OSMC binary,
device firmware, keys, or proprietary blobs are committed here.

