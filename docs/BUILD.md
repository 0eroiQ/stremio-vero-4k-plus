# Build prerequisites

The project currently prepares two different build classes:

- **Kernel/boot probe:** exact Vero kernel, eMMC-disabled device tree, minimal
  initramfs, and external-root image assembly. Reserve at least 20 GiB.
- **Android TV runtime:** AOSP/LineageOS source, Vero device definition, and
  userspace integration. Reserve at least 180 GiB before sources are fetched.

Check the host without installing anything:

```sh
python3 scripts/preflight.py --profile kernel
python3 scripts/preflight.py --profile aosp
```

Fetch only the checksummed official binary inputs into the ignored local cache:

```sh
make fetch-inputs
```

The fetcher accepts only `https://apt.osmc.tv` and `https://dl.strem.io` and
refuses an input whose SHA-256 differs from `sources/sources.lock.json`.

## Why `make image` is still blocked

The exact television UI requires Android, but OSMC does not publish an Android
board support package for Vero 4K+. Producing a black-screen image before its
graphics, input, and boot contracts are defined would not be useful evidence.

The image target will be enabled only after:

1. the eMMC-disabled Vero DTB is built and inspected;
2. the non-installer initramfs is tested structurally;
3. the removable root layout has deterministic identifiers; and
4. the Android board/runtime source set is pinned.

