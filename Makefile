
.PHONY: check-doc-links
## Verify URL links in Markdown files
check-doc-links:
	@python3 scripts/python/verify-doc-links.py && echo "$@: OK"

.PHONY: list-contributors
## Verify URL links in Markdown files
list-contributors:
	@python3 scripts/python/list-contributors.py


.DEFAULT_GOAL := help
.PHONY: help
## Print Makefile documentation
help:
	@perl -0 -nle 'printf("\033[36m  %-20s\033[0m %s\n", "$$2", "$$1") while m/^##\s*([^\r\n]+)\n^([\w.-]+):[^=]/gm' $(MAKEFILE_LIST) | sort
