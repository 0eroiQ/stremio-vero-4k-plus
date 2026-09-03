# Verified upstream inputs

## OSMC base

The base input is the final published Vero 4K/4K+ disk image:

- release: `2025.03-1`
- file: `OSMC_TGT_vero3_20250303.img.gz`
- SHA-256: `a7736298e5c14f705223d4c9a2b560fdc62e819533acccbc78dad3954de63187`
- OSMC-published MD5: `dfa49468c45d90754736de081ea10010`

The image contains one FAT32 installer partition with `kernel.img`, `dtb.img`
and `filesystem.tar.xz`. The current builder reads the filesystem archive and
produces a modified copy. It does not edit the downloaded image in place.

OSMC ended Vero 4K/4K+ support after this final image. Therefore an “OSMC
update” control must report that lifecycle state honestly and must never switch
the device to Vero V packages.

## Stremio UI and Core

The visible UI comes from the official `Stremio/stremio-web` repository. It is
a React application using `@stremio/stremio-core-web`, so account, add-ons,
catalogs, Library and watch progress are real Stremio state rather than local
fixtures.

The source is pinned to a full commit in `sources/sources.lock.json`. Our
overlay modifies the existing Settings route and preserves the upstream
copyright notice. The resulting combined work is distributed under GPL-2.0.

The official Linux shell is retained as an architecture reference only. Its
GTK4/libadwaita/WebKitGTK/libmpv desktop shell is not automatically suitable
for a Vero television appliance. The kiosk host remains an explicit build and
hardware-compatibility gate.

## Stremio Service

The official `Stremio/stremio-service` source is pinned separately. The web UI
can compile without it, but a self-contained Vero appliance still needs the
service for torrent and local streaming behavior. Upstream publishes an amd64
Debian package and bundles x86-64 builds of `stremio-runtime`, `ffmpeg` and
`ffprobe`; those files are explicitly rejected for Vero.

The service source identifies its runtime as Node.js 18.12.1. This project pins
the matching official Node.js Linux `armv7l` archive and the exact official
Stremio Server 4.21.1 JavaScript bundle. The prepared Node executable is
verified as 32-bit ARM hard-float and requires at most GLIBC 2.28, which is
within the pinned OSMC Bullseye GLIBC 2.31 baseline. This proves architecture
compatibility only. ARM `ffmpeg` and `ffprobe`, startup under emulation and
physical Vero playback remain explicit gates.

## Kodi settings provenance

The bridge mapping is limited to setting IDs and enum values found in:

`usr/share/kodi/system/settings/settings.xml`

inside the pinned OSMC root filesystem. The initial mapping covers:

- `videoplayer.adjustrefreshrate`
- `videoplayer.usedisplayasclock`
- `videoplayer.useamcodec`
- `videoplayer.amlhdrmodes`
- `audiooutput.channels`
- `audiooutput.passthrough`
- AC3, E-AC3, DTS, TrueHD and DTS-HD passthrough toggles
- preferred audio/subtitle language and basic subtitle rendering

Runtime application uses Kodi JSON-RPC `Settings.GetSettings`,
`Settings.GetSettingValue` and `Settings.SetSettingValue`. The bridge first
discovers available setting IDs and skips unavailable ones with an explicit
status instead of modifying Kodi XML files directly.
