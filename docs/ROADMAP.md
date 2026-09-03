# Roadmap

## Phase 0 — source and recovery proof

- Create the public project and continuous safety checks.
- Reproduce and inspect an eMMC-disabled Vero 4K+ multi-DTB offline. (Complete;
  physical boot remains untested.)
- Pin exact upstream Vero sources and document their licenses.
- Resolve the official Stremio TV runtime and redistribution path.
- Document exact-model OSMC recovery without running it.

Exit condition: `sources.lock.json` is complete and marked `locked`.

## Phase 1 — offline build

- Build the kernel/runtime in a pinned Linux container.
- Assemble an external-only image as a regular file.
- Generate partition manifest, SBOM, licenses, and SHA-256 checksums.
- Mount and inspect every filesystem offline.

Exit condition: CI and local verification pass with no device-writing code.

## Phase 2 — guarded Vero bring-up

- HDMI signal and stable boot.
- USB/RF remote and HDMI-CEC navigation.
- Ethernet, Wi-Fi, Bluetooth, and Vero Settings.
- Stremio account and catalog synchronization.
- 1080p, then 4K HEVC Main10, HDR, refresh rate, and HDMI passthrough.

Exit condition: recorded acceptance evidence for every feature.

## Phase 3 — user-installable release

- Publish the reviewed external image and checksums.
- Provide a removable-media writer that requires explicit drive selection and
  destructive confirmation.
- Keep internal installation disabled until a separate recovery and rollback
  design is proven.
