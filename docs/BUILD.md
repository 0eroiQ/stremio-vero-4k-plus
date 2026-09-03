# Build

The current build starts with the final official OSMC Vero 4K/4K+ installer
and changes only a copied root-filesystem archive. Android/AOSP is not part of
this design.

All outputs are regular files beneath the ignored `.cache/` and `out/`
directories. No repository command formats media or accepts a block device as
an output.

## 1. Check the Mac

```sh
make preflight
make check
```

The OSMC path needs Git, Python 3, Node 22 or newer and at least 4 GiB of free
space. It does not need the 180 GiB Android source checkout from the abandoned
AOSP direction.

## 2. Prepare the official Stremio TV UI

```sh
make stremio-web-source
```

This fetches the exact `stremio-web` commit recorded in
`sources/sources.lock.json`, verifies `HEAD`, copies the source beneath
`out/stremio-web-src`, and applies the small Vero Settings overlay. The real
Stremio account, add-on, catalog, Library and progress code remains upstream
Stremio code; no media rows are hardcoded by this project.

To install JavaScript dependencies and produce the production web bundle:

```sh
make stremio-web-build
```

## 3. Prepare and audit the Stremio Service runtime

```sh
make stremio-service-audit
```

This fetches the pinned Stremio Service source only for provenance and
architecture comparison. Its bundled x86-64 executables are rejected. The
builder then combines the exact official Server 4.21.1 JavaScript bundle with
the matching official Node.js 18.12.1 Linux ARMv7 hard-float runtime beneath
`out/stremio-service-armhf/`.

The output includes pinned static ARM builds of FFmpeg 4.4.1 and ffprobe from
the same release family embedded by upstream Stremio Service. It is not added
to any startup target and deliberately reports `imageEligible: false`. CI
executes Node, FFmpeg and ffprobe and starts the server under QEMU; this proves
ARM startup compatibility, not media playback or Vero hardware integration.

## 4. Build the OSMC rootfs overlay

```sh
make osmc-rootfs
```

The steps are deliberately explicit:

1. download the official OSMC `2025.03-1` installer from its published mirror;
2. reject it unless its SHA-256 matches the source lock;
3. parse its FAT32 filesystem directly from the regular image file, without
   attaching or mounting it;
4. extract and validate `filesystem.tar.xz`;
5. stream the official archive into a new archive while adding the local-only
   settings bridge, Stremio Web build and the inactive ARM service payload; and
6. write a JSON build report with the base and output checksums.

The ARM Stremio Service payload is present for offline verification but has no
systemd unit or autostart link yet. The current overlay also does **not**
disable OSMC's Kodi startup. That switch would
leave a black screen until the fullscreen Stremio shell and display hand-off
are packaged and tested, so it remains a later gated change.

## 5. Why `make image` remains blocked

The rootfs overlay is a reviewable development artifact, not a bootable release
image. A derived installer image will be enabled only after:

1. a lightweight fullscreen WPE/WebKit shell is pinned and builds for OSMC
   Bullseye armhf;
2. D-pad/remote navigation works in the official Stremio interface;
3. Stremio-to-Kodi display hand-off works without exposing Kodi Home;
4. settings are applied to Kodi before each playback session;
5. the transformed rootfs and installer layout pass offline inspection; and
6. a recovery plan is reviewed before any removable media is prepared.

The earlier storage-blind boot probe is kept in this repository as safety
evidence. It is not used to construct this OSMC-based runtime.
