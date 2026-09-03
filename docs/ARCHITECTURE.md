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

## Open decision: TV runtime

The official open-source Linux shell is a desktop client. The reference TV
interface is delivered by Stremio's Android TV application. The project will
not imitate the screenshot with hard-coded data and will not claim that the
desktop shell is the TV client.

The image build remains blocked until one of these routes is validated:

- a permitted official Android TV application/runtime route for this target;
- an upstream-supported Stremio TV web/runtime route; or
- explicit upstream permission and a maintainable integration contract.

## Playback gate

The presence of an Amlogic video driver is not proof that `libmpv` or an
Android player can use it. Hardware decode, zero-copy presentation, HDR
metadata, refresh-rate switching, and HDMI passthrough are separate target
tests.

