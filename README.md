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
CI checks are active; no bootable artifact has been published.

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

## Project status

| Component | Status |
| --- | --- |
| Repository and CI safety checks | Passing |
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

`make image` intentionally refuses to run until the upstream inputs and image
layout are reviewed and locked.

## Upstream projects

This project depends on work by Stremio and OSMC. It is not affiliated with,
endorsed by, or supported by either project. No Stremio APK, OSMC binary,
device firmware, keys, or proprietary blobs are committed here. “Stremio” and
“OSMC” remain the property of their respective owners.
