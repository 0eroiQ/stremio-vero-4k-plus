# Architecture decision record

## Decision

The base is the final official OSMC Vero 4K/4K+ image, not Android/AOSP and not
a replacement kernel. We keep the Vero boot chain, Linux kernel, firmware,
AMCodec integration, audio stack, CEC, RF remote, ConnMan and BlueZ.

The official Stremio Web application is the visible product. It already uses
Stremio Core for the real account, add-ons, catalogs, Library, Continue
Watching and progress. A Vero overlay adds only the device-specific settings
and shell integration.

## Runtime layers

1. **OSMC base** — unchanged Vero bootloader, kernel, DTB, firmware and Debian
   armhf userspace.
2. **Stremio kiosk shell** — a fullscreen WebKit/WPE host for the pinned
   official Stremio Web build, with D-pad navigation and no desktop.
3. **Stremio Service** — the official Server JavaScript on a verified ARMv7
   Node.js runtime with matching ARM FFmpeg tools. Its state and cache are
   isolated from the immutable application files. The packaged unit remains
   disabled until its port-11470 network policy is tested.
4. **Settings Bridge** — a localhost-only API. It queues validated settings,
   maps supported values to Kodi JSON-RPC, and later exposes narrow ConnMan,
   BlueZ, CEC and updater operations.
5. **Playback Bridge** — accepts a resolved Stremio stream, suspends the kiosk
   display, starts Kodi directly in playback, synchronizes state and progress,
   stops Kodi when playback finishes, and restores Stremio.
6. **Kodi VideoPlayer** — retained as the Vero hardware playback engine. Kodi
   Home, Estuary and Kodi Settings are not part of the normal user experience.

## Display ownership

Kodi GBM and the kiosk shell cannot be assumed to own the DRM display at the
same time. The first implementation therefore uses an explicit hand-off:

```text
Stremio visible -> suspend kiosk -> start Kodi/player -> stop Kodi -> resume Stremio
```

The Settings Bridge persists choices while Kodi is stopped and applies them
after Kodi JSON-RPC becomes ready, before `Player.Open`.

## Settings ownership

- **Stremio Core:** account, add-ons, interface language, Library and native
  Stremio player preferences.
- **Playback Bridge:** stream hand-off, progress, selected audio/subtitle
  tracks, seek and stop events.
- **Kodi:** refresh-rate switching, AMCodec/HDR mode, audio channel layout,
  passthrough codecs and subtitle renderer values.
- **OSMC Linux:** Ethernet/Wi-Fi, Bluetooth, CEC, system information, update,
  restart and shutdown.

All Kodi IDs in the bridge come from the `settings.xml` contained in the pinned
OSMC 2025.03-1 image. Unsupported settings are reported; they are not silently
invented or written to `guisettings.xml`.

## Image construction

The official compressed installer image is a read-only input. The builder:

1. verifies its SHA-256;
2. reads `filesystem.tar.xz` from the image's FAT32 partition;
3. streams the original tar entries into a new archive;
4. replaces only allowlisted overlay paths;
5. writes a manifest containing input, overlay and output hashes.

The current milestone outputs a transformed rootfs archive, not install media.
Image repacking and physical writing are separate gates.

## Rejected directions

- Android TV/AOSP, because Vero 4K+ has no supported Android HAL/codec stack.
- A custom screenshot clone, because it would not contain real Stremio data.
- Removing Kodi before libmpv/WPE has proven equivalent Vero hardware decode,
  HDR, refresh-rate and HDMI passthrough behavior.
