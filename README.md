# Stremio for Vero 4K+

An independent, experimental television appliance built from the final
official OSMC image for Vero 4K+ and the official open-source Stremio Web UI.

> [!WARNING]
> There is no hardware-tested install image yet. Current build commands create
> regular files only. They do not write a microSD card, USB drive, bootloader,
> partition table, or Vero eMMC.

## Product contract

```text
Vero hardware
  -> OSMC Linux, kernel, firmware and hardware drivers
  -> fullscreen official Stremio Web UI
  -> local Playback Bridge
  -> hidden Kodi VideoPlayer while a title is playing
```

The user sees Stremio, not a Kodi home screen, Estuary, or a Linux desktop.
Stremio remains responsible for the account, add-ons, catalogs, Library and
watch progress. Kodi is retained only because OSMC's Vero-specific player path
already provides the proven AMCodec, refresh-rate, HDR and HDMI-audio support.

## What is implemented

- The official OSMC `2025.03-1` Vero 4K/4K+ installer image is pinned by
  SHA-256 and used as a build input; it is not committed or mirrored here.
- The official `stremio-web` source is pinned to an exact commit.
- A Vero Settings overlay adds remote-friendly Picture, HDMI Audio, subtitle
  renderer and Device sections to the real Stremio Settings route.
- A localhost-only settings service validates and persists the choices and
  translates them to the exact Kodi 21 setting IDs shipped in the OSMC image.
- A loopback-only web service serves the production Stremio bundle locally.
- An allowlisted root-filesystem transformer applies the project overlay to
  OSMC's `filesystem.tar.xz` without mounting or modifying the source image.
- Safety checks reject block-device writers and direct eMMC modification code.

## Still required before hardware testing

- Build and package the official Stremio Service and its runtime for OSMC's
  armhf userspace so torrent and local streaming work without a desktop.
- Select and package a lightweight fullscreen WebKit/WPE shell that can use
  Vero's display stack and D-pad input.
- Complete the display hand-off: stop the Stremio shell, start hidden Kodi with
  the selected URL, then restore Stremio when playback ends.
- Connect Vero Settings to ConnMan, BlueZ, CEC and the OSMC updater through
  narrowly scoped helpers.
- Repack the transformed root filesystem into a derived installer image and
  inspect every file offline.
- Test only after a separate recovery and rollback checklist is accepted.

## Development

Run the local, non-destructive checks:

```sh
make check
```

Prepare a patched Stremio Web source tree beneath the ignored `out/` folder:

```sh
make stremio-web-source
```

Build the transformed OSMC root filesystem as a regular file:

```sh
make osmc-rootfs
```

No command in this repository accepts a block device as an output. See
[Architecture](docs/ARCHITECTURE.md), [Build](docs/BUILD.md), and
[Safety](docs/SAFETY.md). The latest verified local build is recorded in
[OSMC overlay evidence](docs/OSMC-OVERLAY-EVIDENCE.md).

## Upstream and licensing

This project is not affiliated with, endorsed by, or supported by Stremio or
OSMC. The Stremio Web modifications are distributed under GPL-2.0, matching
upstream. OSMC images and packages are downloaded from OSMC's published mirror
and remain subject to their component licenses and trademarks.
