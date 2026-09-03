# OSMC overlay build evidence

This file records offline development evidence. It is not a Vero boot result
and it is not permission to create or use installation media.

## 2026-09-03 — official Stremio Web plus Vero Settings

- Host: macOS arm64
- OSMC base: `2025.03-1`, Vero 4K/4K+
- Compressed installer SHA-256:
  `a7736298e5c14f705223d4c9a2b560fdc62e819533acccbc78dad3954de63187`
- Extracted official rootfs SHA-256:
  `3fdbc5a848a263a76bb2939c42f6e54a4cd663bd37fe7313eadb193766e2b80b`
- Stremio Web commit:
  `6303c9947967afff70faaa1071171bfd9b4b30d8`
- Final derived rootfs SHA-256:
  `99a4639feee6a784cc28a52a994aff82f26171d1e4ec1e5d007c4e42447b4128`
- Official Stremio production build: pass, with two upstream bundle-size
  warnings and no compile error
- Python and safety suite: 23 tests passed
- Stremio source lint: pass

The rootfs verifier compared every original archive entry:

- original OSMC entries: 40,574
- byte-and-metadata-identical original entries: 40,574
- declared overlay entries: 107
- undeclared changes: 0
- Kodi autostart override present: no

No Vero, eMMC, SD card or USB drive was accessed by this build.
