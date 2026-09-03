# Fullscreen kiosk compatibility audit

This audit selects the next **disabled** display prototype. It does not enable
a service, replace Kodi autostart, create installation media or access a Vero.

## Pinned OSMC display stack

The final Vero 4K/4K+ root filesystem contains:

- OSMC `vero3-userland-osmc` `2.0.5`;
- OSMC `vero3-mediacenter-osmc` `21.1.0-9`;
- `/opt/vero3/lib/libMali.so`, `libEGL.so.1` and `libGLESv2.so.2`;
- `/opt/vero3/lib` in the dynamic linker search path;
- `MALI_FBDEV` and `/dev/fb0` markers in the vendor Mali library;
- `CONFIG_FB=y` and `CONFIG_MALI400=m` in the shipped kernel configuration;
- `CONFIG_DRM` explicitly disabled in that kernel configuration;
- Kodi's OSMC-specific GBM session entry and executable.

It does not contain Cog, WPE WebKit, WPEBackend-fdo, a Wayland client runtime,
a Wayland compositor, GBM runtime, Qt WebEngine or the Qt EGLFS plugin.

Run the reproducible archive-only check with:

```sh
make kiosk-audit
```

The machine-readable result is written to `out/kiosk/base-audit.json`.

## Decision

The ordinary Debian Bullseye Cog package is not a drop-in choice. Its packaged
WPEBackend-fdo path depends on Wayland libraries, and a Wayland compositor must
own the display. Adding that entire stack would still leave an unproven bridge
between its GBM/Wayland assumptions and Vero's legacy vendor fbdev EGL driver;
the shipped Vero kernel does not expose the DRM API expected by GBM.

The next prototype is therefore **Qt WebEngine with the EGLFS platform**, kept
disabled and outside the boot path. EGLFS is designed for one fullscreen EGL
application without X11 or Wayland and is the closer match to the evidence in
the Vero library. This is a probe selection, not a compatibility claim.

The rootfs overlay contains the minimal fullscreen QML view, a launcher that
forces the legacy fbdev EGL path and a systemd unit. The Qt runtime is not yet
packaged. The unit is not enabled and also has `RefuseManualStart=yes`, so it
cannot accidentally take the display while the compatibility work is ongoing.

The probe must prove all of the following before it can replace Kodi at boot:

1. Debian Bullseye armhf Qt WebEngine and its complete dependency closure can
   be pinned, checksummed and unpacked without replacing OSMC's vendor EGL or
   Vero packages.
2. `QT_QPA_PLATFORM=eglfs` can create a surface through the existing
   `/opt/vero3/lib` stack.
3. The official local Stremio Web bundle renders correctly at 1080p and accepts
   RF/CEC D-pad, Select and Back input.
4. Idle and navigation memory use fit safely within Vero 4K+ limits.
5. The shell can fully release the display before hidden Kodi starts, and can
   recover it after Kodi exits.

Until those gates pass, the Stremio service and any future kiosk service remain
disabled and normal OSMC/Kodi boot remains unchanged.
