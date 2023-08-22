
.PHONY: check-doc-links
## Verify URL links in Markdown files
check-doc-links:
	@python3 scripts/python/verify-doc-links.py && echo "$@: OK"

.PHONY: list-contributors
## List top contributors
list-contributors:
	@python3 scripts/python/list-contributors.py

.PHONY: list-pr-reviewers
## List top PR reviewers
list-pr-reviewers:
	@python3 scripts/python/list-contributors.py -r reviewer commenter

.PHONY: list-pr-authors
## List top PR authors
list-pr-authors:
	@python3 scripts/python/list-contributors.py -r author

.DEFAULT_GOAL := help
.PHONY: help
## Print Makefile documentation
help:
	@perl -0 -nle 'printf("\033[36m  %-20s\033[0m %s\n", "$$2", "$$1") while m/^##\s*([^\r\n]+)\n^([\w.-]+):[^=]/gm' $(MAKEFILE_LIST) | sort
