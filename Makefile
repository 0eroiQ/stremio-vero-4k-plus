.PHONY: check safety sources test preflight fetch-inputs stremio-web-source stremio-web-build stremio-service-source stremio-service-runtime stremio-service-audit stremio-service-smoke osmc-base-rootfs osmc-rootfs verify-osmc-rootfs inspect-boot safe-dtb probe-init probe-initramfs boot-probe image

OSMC_IMAGE := .cache/downloads/OSMC_TGT_vero3_20250303.img.gz
OSMC_ROOTFS := .cache/downloads/OSMC_TGT_vero3_20250303-rootfs.tar.xz
OSMC_SHA256 := a7736298e5c14f705223d4c9a2b560fdc62e819533acccbc78dad3954de63187
STREMIO_WEB_COMMIT := 6303c9947967afff70faaa1071171bfd9b4b30d8
STREMIO_SERVER_SHA256 := 405eb494d6708406a30e716c3cfb5abae7a5e9c7a8b79446d64c3f821385930f
NODE_ARMHF_SHA256 := d0131a764c0f44821fdacb3c3ab8b35b52af060a98ac7a150ec49d4c540be3d7
QEMU_ARM ?= /usr/bin/qemu-arm-static
ARM_SYSROOT ?= /usr/arm-linux-gnueabihf

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

stremio-service-source:
	@python3 scripts/fetch_git_source.py sources/sources.lock.json \
	  --name "Stremio Service" --directory stremio-service

stremio-service-runtime:
	@python3 scripts/fetch_verified.py sources/sources.lock.json \
	  --name "Stremio Server 4.21.1 JavaScript bundle"
	@python3 scripts/fetch_verified.py sources/sources.lock.json \
	  --name "Node.js 18.12.1 Linux armv7l runtime"
	@python3 scripts/prepare_stremio_service.py \
	  --node-archive .cache/downloads/node-v18.12.1-linux-armv7l.tar.xz \
	  --server-js .cache/downloads/server.js \
	  --output out/stremio-service-armhf \
	  --expected-node-sha256 $(NODE_ARMHF_SHA256) \
	  --expected-server-sha256 $(STREMIO_SERVER_SHA256)

stremio-service-audit: stremio-service-source stremio-service-runtime
	@python3 scripts/audit_stremio_service.py \
	  --upstream .cache/upstream/stremio-service/resources/bin/linux \
	  --prepared out/stremio-service-armhf

stremio-service-smoke: stremio-service-runtime
	@python3 scripts/smoke_stremio_service.py \
	  --runtime out/stremio-service-armhf/stremio-runtime \
	  --server out/stremio-service-armhf/server.js \
	  --emulator $(QEMU_ARM) \
	  --sysroot $(ARM_SYSROOT)

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
