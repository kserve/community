# KServe Community Scripts

## Governance Check

`governance-check.py` validates open promotion requests in
[kserve/community](https://github.com/kserve/community) against the
[governance criteria](../membership.md) by querying PR activity from
[kserve/kserve](https://github.com/kserve/kserve).

### What it does

- Finds open promotion issues (title matching `REQUEST: Promotion to ...`)
- For each candidate, counts authored (merged) PRs and reviewed PRs
- Filters out noise: bot commands (`/lgtm`, `/approve`, `/retest`, etc.),
  comments under 10 characters, and self-reviews
- For Approver candidates:
  - Finds when they became a reviewer (from OWNERS file git history)
  - Measures activity **only during their reviewer tenure** (not before)
  - Fails automatically if reviewer tenure is less than 3 months
- Detects inactive maintainers (12+ months with no PR activity)
- Supports `--user` mode for checking individual eligibility without opening an issue

### Measurement periods

| Target Role | Period | Rationale |
|-------------|--------|-----------|
| Reviewer | Last 90 days | Recent activity as a member |
| Approver | Since reviewer start date | Only reviewer-period activity counts |

### Quick start

```bash
# Requires a GitHub token (uses gh CLI token if available)
export GITHUB_API_TOKEN=$(gh auth token)

# Validate all open promotion requests
make governance-check

# Check a specific user's eligibility
make governance-check-user USER=someuser TARGET=approver
make governance-check-user USER=someuser TARGET=reviewer
```

### Makefile targets

| Target | Description |
|--------|-------------|
| `make governance-check` | Validate open promotion requests and detect inactive maintainers |
| `make governance-check-user USER=x TARGET=y` | Check a specific user's promotion eligibility |
| `make list-contributors` | List top contributors by total PR participation |
| `make list-pr-reviewers` | List top PR reviewers |
| `make list-pr-authors` | List top PR authors |

### CLI options

```
python3 scripts/python/governance-check.py [OPTIONS]

Options:
  --repo REPO              GitHub repo to query for PR activity
                           (default: kserve/kserve)
  --community-repo REPO    GitHub repo with promotion issues
                           (default: kserve/community)
  --reviewer-days DAYS     Lookback period for reviewer candidates
                           (default: 90)
  --inactive-days DAYS     Days of no activity to flag as inactive
                           (default: 365)
  --user USERNAME          Check a specific user instead of open issues
  --target ROLE            Target role for --user mode (reviewer|approver)
  --output {json,markdown} Output format (default: markdown)
  -v, --debug              Print progress info to stderr
```

### Examples

```bash
export GITHUB_API_TOKEN=$(gh auth token)

# Validate all open promotion requests
python3 scripts/python/governance-check.py --output markdown

# Check your own eligibility before opening a promotion request
python3 scripts/python/governance-check.py --user myname --target reviewer

# JSON output for scripting
python3 scripts/python/governance-check.py --output json | jq '.promotion_validations'

# Custom lookback for reviewer candidates
python3 scripts/python/governance-check.py --reviewer-days 180

# Check a different repo
python3 scripts/python/governance-check.py --repo kserve/modelmesh-serving
```

### How reviews are counted

A PR counts as "reviewed" if the user either:

- Submitted a review with COMMENTED or CHANGES_REQUESTED state, or
- Left a general comment that passes the noise filter (not a bot command, 10+ characters, not on their own PR)

Multiple comments on the same PR count as one review.

## List Contributors

`list-contributors.py` is a simpler script that lists top PR participants
(authors, reviewers, commenters) ranked by number of PRs. See `--help` for options.
