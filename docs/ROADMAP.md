# Roadmap

## Phase 0 — reproducible OSMC overlay

- [x] Pin and verify OSMC 2025.03-1 and official Stremio Web source.
- [x] Add Vero Settings to the real Stremio Settings route.
- [x] Build and unit-test the localhost Settings Bridge and Kodi mapping.
- [x] Build and serve the production Stremio Web bundle on loopback.
- [x] Transform `filesystem.tar.xz` as a regular file and publish a manifest.
- [x] Keep all device-writing commands prohibited.
- [ ] Reproduce the final archive checksum in a clean build environment.

Exit condition: the patched Stremio source and transformed OSMC rootfs build
twice with identical content and all offline checks pass.

## Phase 1 — kiosk and playback hand-off

- Build and prove the official Stremio Service on OSMC Bullseye armhf.
- Select the smallest compatible WPE/WebKit shell for OSMC Bullseye armhf.
- Prove fullscreen rendering and RF/CEC D-pad input on a non-Vero test target.
- Implement the Stremio-to-Kodi playback request and DRM display hand-off.
- Apply queued settings through Kodi JSON-RPC before playback.
- Return progress, pause, seek, stop and completion to Stremio Core.

Exit condition: a desktop/Linux integration test plays a URL through Kodi and
returns to Stremio without showing Kodi Home.

## Phase 2 — derived installer image

- Repack the modified rootfs into a copy of the official OSMC installer image.
- Add SBOM, license notices, file manifest and full checksums.
- Mount and inspect every filesystem offline.
- Confirm the bootloader, kernel and DTB are byte-identical to official OSMC.
- Prepare official recovery media and rollback instructions.

Exit condition: reviewed image exists as a file, with no physical write.

## Phase 3 — guarded Vero acceptance

- First boot, HDMI and stable Stremio navigation.
- RF remote and HDMI-CEC.
- Ethernet, Wi-Fi and Bluetooth through Vero Settings.
- 1080p before 4K HEVC Main10, HDR and refresh-rate switching.
- Stereo before passthrough codec tests.
- Cold boot, reboot, power loss and recovery acceptance.

Exit condition: recorded evidence for every feature and a normal cold boot.
