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

## 2026-09-03 — inactive ARM Stremio Service payload

- Stremio Service source commit:
  `1891799734acba88904f9f62cb8ca491873b36fb`
- Stremio Server 4.21.1 SHA-256:
  `405eb494d6708406a30e716c3cfb5abae7a5e9c7a8b79446d64c3f821385930f`
- Node.js 18.12.1 Linux armv7l archive SHA-256:
  `d0131a764c0f44821fdacb3c3ab8b35b52af060a98ac7a150ec49d4c540be3d7`
- FFmpeg 4.4.1 static armhf archive SHA-256:
  `42069b3e7289acf9772ed651f56fe13a53274165db55d005444a1bc1551cdd2f`
- GitHub ARM smoke run:
  `https://github.com/0eroiQ/stremio-vero-4k-plus/actions/runs/33723607014`

The ARM job executed Node.js, FFmpeg and ffprobe under QEMU, started the exact
Stremio Server bundle, and received HTTP 200 from `127.0.0.1:11470`. Casting
discovery was disabled because QEMU user networking does not provide the
multicast socket operation used by the server. No stream or video playback was
claimed by this test.

The verified runtime was then added to a new derived rootfs as an inactive
payload. There is no Stremio Service systemd unit or autostart link yet:

- final derived rootfs SHA-256:
  `1e04bd683f1618691123464e27f33333ad308de59acf9b035addce22d9758396`
- original OSMC entries: 40,574
- byte-and-metadata-identical original entries: 40,574
- declared overlay entries: 117
- undeclared changes: 0
- Kodi autostart override present: no

No Vero, eMMC, SD card or USB drive was accessed by this build.
