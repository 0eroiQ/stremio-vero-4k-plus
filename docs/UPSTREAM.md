# Verified upstream facts

This record separates verified upstream behavior from project assumptions.

## Stremio

- The requested 10-foot UI is the native Android TV application
  `com.stremio.one`, whose television entry point is
  `com.stremio.tv.MainActivity`.
- The official ARM APK is `armeabi-v7a`, requires Android API 24 or newer, and
  depends on Android Framework, bionic, SurfaceFlinger, and MediaCodec.
- It cannot run directly in Debian/OSMC armhf Linux.
- Stremio's open Linux shell is a desktop GTK4/libadwaita/WebKitGTK/libmpv
  application. It does not provide the same TV interface.
- Stremio OS for Raspberry Pi is based on LineageOS 21 / Android TV 14 for Pi
  hardware; it is an architectural reference, not a Vero base image.

## Vero 4K+

- SoC family: Amlogic Meson GXL S905D, ARMv8/AArch64.
- OSMC uses a 64-bit kernel with a 32-bit Debian armhf userspace.
- Current published downstream kernel package is in the 4.9.269 OSMC series.
- Exact board device tree: `vero3plus_2g_16g` (`gxl_p231_2g`).
- OSMC does not publish or support an Android/Android TV image for Vero 4K+.
- The official removable image is destructive installation media, not a live
  SD system.

## Verified boot hazards

- The pinned official kernel package has `CONFIG_CMDLINE_EXTEND=y` and a
  compiled internal-root argument. The kernel source appends that text after
  incoming boot arguments, so a direct external `root=` argument would not be
  the final root selection.
- A present initramfs `/init` is executed before the audited kernel prepares a
  root namespace. The offline probe uses that route and never returns from its
  storage-blind PID 1.
- The pinned readable U-Boot recovery source loads a specifically named
  recovery component and then may clear 4096 bytes of internal `instaboot`
  before starting Linux.
- OSMC published a 2024 binary-only bootloader update whose commit message says
  it fixes that toothpick/`instaboot` problem. The exact currently deployed
  removable-media path cannot be matched to readable source, so no automatic
  boot or recovery-media test is authorized.

## Still unproven

- A stable Android boot on the exact Vero 4K+ board.
- A complete distributable graphics/codec/audio HAL stack.
- Hardware video decode usable by the official Stremio TV players.
- HDR metadata, refresh-rate switching, HDMI passthrough, CEC, RF remote,
  Wi-Fi, and Bluetooth in the new runtime.
- An external-root boot path that leaves internal storage unreachable.
- A read-only audit of the exact deployed bootloader environment and a
  pre-kernel path proven not to write internal storage.
