.PHONY: check safety sources test preflight fetch-inputs inspect-boot safe-dtb image

check: safety sources test

safety:
	@python3 scripts/safety_lint.py

sources:
	@python3 scripts/validate_sources.py sources/sources.lock.json

test:
	@python3 -m unittest discover -s tests -v

preflight:
	@python3 scripts/preflight.py --profile aosp

fetch-inputs:
	@python3 scripts/fetch_verified.py sources/sources.lock.json

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
	  --output out/boot-probe/dtb-external-only.img

image:
	@printf '%s\n' \
	  'IMAGE BUILD BLOCKED: upstream boot/runtime inputs are not locked yet.' \
	  'No disk image was created and no block device was touched.' >&2
	@exit 2
