# Architecture decision record

## Required experience

The product must present a television-first Stremio interface with directional
remote navigation, a left icon rail, focused-title metadata, and horizontal
content rows. A conventional Linux desktop window is not acceptable.

## Layers

1. **Vero hardware layer** — exact Vero 4K+ boot chain, kernel, device tree,
   firmware, remote/CEC, HDMI, audio, networking, and video decoder support.
2. **Appliance runtime** — minimal read-only userspace with no general-purpose
   desktop and no internal-storage installer.
3. **Stremio runtime** — official account, catalog, add-on, library, progress,
   and streaming behavior.
4. **TV presentation** — the official TV experience when a permitted and
   technically compatible distribution route is established.
5. **Vero Settings** — a small D-pad interface for network, Bluetooth, remote,
   display, audio, updates, diagnostics, restart, and shutdown.

## Decision: TV runtime

The official open-source Linux shell is a desktop client. The reference TV
interface is delivered by Stremio's native Android TV application. The project
will not imitate the screenshot with hard-coded data and will not claim that
the desktop shell is the TV client.

The selected technical direction is a minimal Vero-specific Android TV/AOSP
runtime. On first setup it will download the unmodified ARMv7 APK from the
official Stremio download host, verify a reviewed SHA-256 value, and install it
as a normal data application. The image will not bundle or re-sign the APK.

This decision gives the requested TV UI, but it introduces a hard platform
gate: Vero 4K+ has no official Android image. Its Android board definition,
graphics composer, codec HAL, audio, CEC, input, networking, SELinux policy,
and update path must be built and validated for this exact hardware.

## Playback gate

The presence of an Amlogic video driver is not proof that Android MediaCodec
or Stremio's bundled players can use it. Hardware decode, zero-copy presentation, HDR
metadata, refresh-rate switching, and HDMI passthrough are separate target
tests.

## Rejected as the primary product

- **Stremio Linux shell:** real Stremio, but desktop GTK/WebKit UI rather than
  the requested television application.
- **Styled screenshot clone:** would repeat the earlier hard-coded UI problem
  and would not be the official Stremio application.
- **Raspberry Pi Stremio OS image:** uses a Pi-specific LineageOS build and
  cannot be repackaged for the Amlogic Vero hardware.
- **Stock OSMC removable image:** it is an installer that repartitions internal
  storage, not a live SD operating system.
