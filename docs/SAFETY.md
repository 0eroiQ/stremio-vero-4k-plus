# Safety gates

The Vero 4K+ has already shown that an unverified external image can produce a
black screen and turn recovery into a separate hardware operation. This
project therefore treats a bootable artifact as a gated hardware deliverable,
not as an ordinary software build.

## Prohibited in the external-boot prototype

- Writing to internal eMMC, bootloader environment, partition tables, or BCB.
- Bundling installers, recovery writers, factory reset helpers, or flash tools.
- Referring to removable media by a hard-coded host device path.
- Automatically formatting or writing any removable drive.
- Testing on the Vero before a human reviews the image manifest and checksum.
- Claiming boot, video, audio, HDR, CEC, Wi-Fi, or Bluetooth support without
  observed evidence on the target hardware.

## Gate A: provenance

- Exact model is Vero 4K+ (`vero3` family), not a generic S905D board.
- Every source is pinned to an immutable revision and has a recorded license.
- Binary firmware and applications have an explicit redistribution basis.
- Kernel, device tree, configuration, firmware, and userspace ABI are matched.

## Gate B: offline image inspection

- Build runs in an isolated, pinned environment.
- Output is a regular file beneath `out/`; no block device is accepted.
- Every multi-DTB entry disables eMMC while preserving SD and SDIO.
- The guarded component uses a four-entry initramfs whose PID 1 can only write
  its console marker and sleep. It specifies no root target.
- Partition table and every filesystem are enumerated in a machine-readable
  manifest.
- Root filesystem contains no internal-storage write service or device rule.
- Checksums and a software bill of materials are generated.

## Gate C: recovery readiness

- Exact-model official OSMC recovery media is available and checksum-verified.
- The recovery procedure is documented separately from the prototype.
- No physical test begins while the installed Vero system is unhealthy.
- The deployed bootloader environment is inspected read-only; no recovery,
  autoscript, toothpick, or automatic update path is used for the first probe.
- The pre-kernel path must be proven free of internal writes. Kernel and DTB
  protections do not count as proof for actions that happen before `bootm`.

## Gate D: external boot

- The first test uses only reviewed removable media.
- The internal eMMC is never mounted read-write by the prototype.
- Bring-up order is HDMI, input, network, login, 1080p decode, then 4K/HDR.
- A failed test stops; it does not trigger an automatic fallback write.

Internal installation is outside the current milestone.
