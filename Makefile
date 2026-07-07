
.PHONY: check-doc-links
## Verify URL links in Markdown files
check-doc-links:
	@python3 scripts/python/verify-doc-links.py && echo "$@: OK"

.PHONY: list-contributors
## List top contributors
list-contributors:
	@python3 scripts/python/list-contributors.py -n 10

.PHONY: list-pr-reviewers
## List top PR reviewers
list-pr-reviewers:
	@python3 scripts/python/list-contributors.py -r reviewer commenter -n 5

.PHONY: list-pr-authors
## List top PR authors
list-pr-authors:
	@python3 scripts/python/list-contributors.py -r author -n 5

.PHONY: promotion-check
## Validate open promotion requests against governance criteria
promotion-check:
	@python3 scripts/python/promotion-check.py --output markdown

.PHONY: promotion-check-user
## Check promotion eligibility for a specific user (USER=username TARGET=reviewer|approver)
promotion-check-user:
	@python3 scripts/python/promotion-check.py --user $(USER) --target $(TARGET) --output markdown

.DEFAULT_GOAL := help
.PHONY: help
## Print Makefile documentation
help:
	@perl -0 -nle 'printf("\033[36m  %-20s\033[0m %s\n", "$$2", "$$1") while m/^##\s*([^\r\n]+)\n^([\w.-]+):[^=]/gm' $(MAKEFILE_LIST) | sort
