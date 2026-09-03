.PHONY: check safety sources test preflight fetch-inputs stremio-web-source stremio-web-build osmc-base-rootfs osmc-rootfs verify-osmc-rootfs inspect-boot safe-dtb probe-init probe-initramfs boot-probe image

OSMC_IMAGE := .cache/downloads/OSMC_TGT_vero3_20250303.img.gz
OSMC_ROOTFS := .cache/downloads/OSMC_TGT_vero3_20250303-rootfs.tar.xz
OSMC_SHA256 := a7736298e5c14f705223d4c9a2b560fdc62e819533acccbc78dad3954de63187
STREMIO_WEB_COMMIT := 6303c9947967afff70faaa1071171bfd9b4b30d8

check: safety sources test

safety:
	@python3 scripts/safety_lint.py

sources:
	@python3 scripts/validate_sources.py sources/sources.lock.json

test:
	@python3 -m unittest discover -s tests -v

preflight:
	@python3 scripts/preflight.py --profile osmc

fetch-inputs:
	@python3 scripts/fetch_verified.py sources/sources.lock.json

stremio-web-source:
	@python3 scripts/fetch_git_source.py sources/sources.lock.json \
	  --name "Stremio Web" --directory stremio-web
	@python3 scripts/prepare_stremio_web.py \
	  --source .cache/upstream/stremio-web \
	  --overlay web-overlay \
	  --output out/stremio-web-src \
	  --expected-commit $(STREMIO_WEB_COMMIT)

stremio-web-build: stremio-web-source
	@cd out/stremio-web-src && corepack pnpm install --frozen-lockfile
	@cd out/stremio-web-src && corepack pnpm run build

osmc-base-rootfs: fetch-inputs
	@python3 scripts/extract_osmc_installer.py \
	  --image-gz $(OSMC_IMAGE) \
	  --output $(OSMC_ROOTFS) \
	  --expected-sha256 $(OSMC_SHA256)

osmc-rootfs: osmc-base-rootfs stremio-web-build
	@python3 scripts/build_osmc_rootfs.py \
	  --base $(OSMC_ROOTFS) \
	  --manifest rootfs-overlay/manifest.json \
	  --output out/rootfs/filesystem.tar.xz

verify-osmc-rootfs:
	@python3 scripts/verify_osmc_rootfs.py \
	  --base $(OSMC_ROOTFS) \
	  --derived out/rootfs/filesystem.tar.xz \
	  --manifest rootfs-overlay/manifest.json

inspect-boot:
	@python3 scripts/fetch_verified.py sources/sources.lock.json \
	  --name "OSMC Vero 4K+ kernel package 4.9.269-62"
	@python3 scripts/inspect_boot_image.py \
	  --kernel-deb .cache/downloads/vero364-image-4.9.269-62-osmc_4.9.269-62-osmc_arm64.deb \
	  --output out/boot-probe/official-boot-analysis.json

safe-dtb:
	@python3 scripts/fetch_verified.py sources/sources.lock.json \
	  --name "OSMC Vero 4K+ kernel package 4.9.269-62"
	@python3 scripts/build_safe_dtb.py \
	  --kernel-deb .cache/downloads/vero364-image-4.9.269-62-osmc_4.9.269-62-osmc_arm64.deb \
	  --output out/boot-probe/dtb-emmc-disabled.img

probe-init:
	@python3 scripts/build_probe_init.py \
	  --source probe/init.S \
	  --output out/boot-probe/init-storage-blind \
	  --qemu qemu-aarch64-static

probe-initramfs: probe-init
	@python3 scripts/build_probe_initramfs.py \
	  --init out/boot-probe/init-storage-blind \
	  --output out/boot-probe/initramfs-storage-blind.cpio.gz

boot-probe: safe-dtb probe-initramfs
	@python3 scripts/build_boot_probe.py \
	  --kernel-deb .cache/downloads/vero364-image-4.9.269-62-osmc_4.9.269-62-osmc_arm64.deb \
	  --safe-dtb out/boot-probe/dtb-emmc-disabled.img \
	  --initramfs out/boot-probe/initramfs-storage-blind.cpio.gz \
	  --output out/boot-probe/kernel-safe-probe.img

image:
	@printf '%s\n' \
	  'IMAGE BUILD BLOCKED: fullscreen shell and playback hand-off are not proven yet.' \
	  'No disk image was created and no block device was touched.' >&2
	@exit 2
