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

## Still unproven

- A stable Android boot on the exact Vero 4K+ board.
- A complete distributable graphics/codec/audio HAL stack.
- Hardware video decode usable by the official Stremio TV players.
- HDR metadata, refresh-rate switching, HDMI passthrough, CEC, RF remote,
  Wi-Fi, and Bluetooth in the new runtime.
- An external-root boot path that leaves internal storage unreachable.

