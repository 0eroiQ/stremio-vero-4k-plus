.PHONY: check safety sources image

check: safety sources

safety:
	@python3 scripts/safety_lint.py

sources:
	@python3 scripts/validate_sources.py sources/sources.lock.json

image:
	@printf '%s\n' \
	  'IMAGE BUILD BLOCKED: upstream boot/runtime inputs are not locked yet.' \
	  'No disk image was created and no block device was touched.' >&2
	@exit 2

