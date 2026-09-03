.PHONY: check safety sources test preflight fetch-inputs image

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

image:
	@printf '%s\n' \
	  'IMAGE BUILD BLOCKED: upstream boot/runtime inputs are not locked yet.' \
	  'No disk image was created and no block device was touched.' >&2
	@exit 2
