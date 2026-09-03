# Offline build evidence

This file records structural build evidence only. It is not evidence of a Vero
boot and it is not authorization to prepare removable media.

## 2026-09-03 — storage-blind boot component

- Source commit: `1efe42d24f202ff20fa9b2fe28bf7e10db7cee0e`
- GitHub Actions run:
  <https://github.com/0eroiQ/stremio-vero-4k-plus/actions/runs/33712727615>
- Result: success
- Local unit/safety checks: 15 passed
- Official OSMC ramdisk reuse: rejected

CI-generated, ephemeral component hashes:

| Component | SHA-256 |
| --- | --- |
| All-entry eMMC-disabled multi-DTB | `972b4d4f7c1777d4bd96b19f1358e6712715043d1a480d1c7e1617bd1f400abe` |
| Static storage-blind AArch64 `/init` | `110422cd3eb4cbdb8b03511ecdc76de90422476004c7afba4bd2b0c1be2ed20b` |
| Four-entry deterministic initramfs | `c1a6ab8913f467d728eb7d478c9d3b112aac859f4e88c09fb5de1f8a4065e2c4` |
| Guarded Android-format boot component | `12b74bcf8dbd748b5d93757eb1b035e44970e004278a825e14f4b4cd30cfaf9c` |

The CI output was not uploaded as a release or retained as an artifact. No FAT
filesystem, partition table, recovery component, SD/USB writer, or Android
runtime was created. Physical boot status remains **not tested**.
