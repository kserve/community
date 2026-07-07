#!/usr/bin/env python3

# Copyright 2026 The KServe Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Validates open promotion requests against governance criteria
# and identifies inactive maintainers.

import base64
import json
import re
import socket
import sys

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from os import environ as env
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# --- Constants ---

MIN_REVIEW_COMMENT_LENGTH = 10

NOISE_PATTERNS = [
    r"^/(lgtm|approve|retest|ok-to-test|test|rerun-failed)",
    r"^/(hold|unhold|assign|unassign|cc|remove-cc)",
    r"^/cherry-pick",
]

IGNORED_USERS = {
    "github-advanced-security",
    "kserve-oss-bot",
    "dependabot",
    "oss-prow-bot",
}

CRITERIA = {
    "reviewer": {"min_authored": 3, "min_reviewed": 5},
    "approver": {"min_authored": 5, "min_reviewed": 10, "min_tenure_months": 3},
}


# --- CLI ---

def parse_args():
    p = ArgumentParser(
        description="Validate promotion requests and detect inactive maintainers",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--repo", default="kserve/kserve",
                    help="GitHub repository to query for PR activity")
    p.add_argument("--community-repo", default="kserve/community",
                    help="GitHub repository with promotion issues")
    p.add_argument("--reviewer-days", type=int, default=90,
                    help="Lookback days for reviewer candidates")
    p.add_argument("--inactive-days", type=int, default=365,
                    help="Days of no activity to flag as inactive")
    p.add_argument("--user", default=None,
                    help="Check a specific user instead of open promotion issues")
    p.add_argument("--target", choices=["reviewer", "approver"], default=None,
                    help="Target role for --user mode")
    p.add_argument("--output", choices=["json", "markdown"], default="markdown",
                    help="Output format")
    p.add_argument("-v", "--debug", action="store_true",
                    help="Print debug info")
    return p.parse_args()


# --- GitHub API ---

GITHUB_API_TOKEN = env.get("GITHUB_API_TOKEN", "")
GRAPHQL_URL = "https://api.github.com/graphql"
REST_URL = "https://api.github.com"


def _request(url, method="GET", data=None, accept=None):
    headers = {
        "Authorization": f"Bearer {GITHUB_API_TOKEN}",
        "Content-Type": "application/json",
    }
    if accept:
        headers["Accept"] = accept

    req = Request(url, method=method, headers=headers,
                  data=data.encode("utf-8") if data else None)
    try:
        resp = urlopen(req, timeout=30)
        return resp.read().decode("utf-8")
    except HTTPError as e:
        if e.code == 401:
            print("Authentication failed: check GITHUB_API_TOKEN", file=sys.stderr)
        elif e.code == 403:
            print(f"Rate limit or permission denied: {e.reason}", file=sys.stderr)
        else:
            print(f"HTTP {e.code}: {e.reason}", file=sys.stderr)
        return None
    except (URLError, socket.timeout) as e:
        print(f"Network error: {e}", file=sys.stderr)
        return None


def graphql(query):
    body = json.dumps({"query": query})
    result = _request(GRAPHQL_URL, method="POST", data=body)
    if not result:
        return None
    parsed = json.loads(result)
    if "errors" in parsed:
        print(f"GraphQL errors: {parsed['errors']}", file=sys.stderr)
    return parsed


# --- Data Fetching ---

PR_QUERY = """
{
  query: search(
    type: ISSUE
    query: "repo:%s is:PR created:>%s"
    first: 100
    %s
  ) {
    pageInfo { hasNextPage endCursor }
    nodes {
      ... on PullRequest {
        number
        title
        createdAt
        mergedAt
        author { login }
        reviews(first: 30) {
          nodes {
            author { login }
            state
            body
          }
        }
        comments(first: 50) {
          nodes {
            author { login }
            body
          }
        }
      }
    }
  }
}
"""


def fetch_all_prs(repo, since_date):
    nodes = []
    has_next = True
    cursor = None

    while has_next:
        after = f'after: "{cursor}"' if cursor else ""
        query = PR_QUERY % (repo, since_date.strftime("%Y-%m-%d"), after)
        result = graphql(query)
        if not result or "data" not in result:
            break
        page = result["data"]["query"]
        has_next = page["pageInfo"]["hasNextPage"]
        cursor = page["pageInfo"]["endCursor"]
        nodes.extend(page["nodes"])

    return nodes


ISSUE_QUERY = """
{
  search(
    type: ISSUE
    query: "repo:%s is:issue is:open Promotion to in:title"
    first: 50
  ) {
    nodes {
      ... on Issue {
        number
        title
        url
        createdAt
      }
    }
  }
}
"""


def fetch_promotion_issues(community_repo):
    result = graphql(ISSUE_QUERY % community_repo)
    if not result or "data" not in result:
        return []

    return [node for node in result["data"]["search"]["nodes"]
            if re.match(r"REQUEST:\s*Promotion to", node.get("title", ""), re.IGNORECASE)]


# Added-line pattern in a unified diff: starts with "+  - username"
_DIFF_ADDED_ENTRY = re.compile(r"^\+\s+-\s+(\S+)")


def fetch_reviewer_since_dates(repo):
    """Find the date each reviewer was added to OWNERS by scanning commit diffs."""
    url = f"{REST_URL}/repos/{repo}/commits?path=OWNERS&per_page=100"
    result = _request(url)
    if not result:
        return {}

    commits = json.loads(result)
    reviewer_dates = {}

    for commit_info in reversed(commits):
        sha = commit_info["sha"]
        commit_date = commit_info["commit"]["author"]["date"][:10]
        detail = _request(f"{REST_URL}/repos/{repo}/commits/{sha}")
        if not detail:
            continue

        for f in json.loads(detail).get("files", []):
            if f["filename"] != "OWNERS":
                continue
            in_reviewers = False
            for line in f.get("patch", "").splitlines():
                if "reviewers:" in line:
                    in_reviewers = True
                elif re.match(r"^[a-z]", line):
                    in_reviewers = False
                elif in_reviewers:
                    m = _DIFF_ADDED_ENTRY.match(line)
                    if m:
                        username = m.group(1).lower()
                        if username not in reviewer_dates:
                            reviewer_dates[username] = commit_date

    return reviewer_dates


def fetch_owners(repo):
    url = f"{REST_URL}/repos/{repo}/contents/OWNERS"
    result = _request(url, accept="application/vnd.github.v3+json")
    if not result:
        return {"leads": [], "approvers": [], "reviewers": []}

    content = base64.b64decode(json.loads(result)["content"]).decode("utf-8")
    return parse_owners(content)


def parse_owners(content):
    owners = {"leads": [], "approvers": [], "reviewers": []}
    current_section = None

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("project-leads:"):
            current_section = "leads"
        elif stripped.startswith("approvers:"):
            current_section = "approvers"
        elif stripped.startswith("reviewers:"):
            current_section = "reviewers"
        elif stripped.startswith("- ") and current_section:
            username = stripped[2:].strip()
            if username:
                owners[current_section].append(username.lower())
        elif stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            current_section = None

    return owners


# --- Noise Filtering ---

def is_valid_review(body, pr_author, reviewer):
    if not body or reviewer == pr_author:
        return False
    text = body.strip()
    if len(text) < MIN_REVIEW_COMMENT_LENGTH:
        return False
    return not any(re.match(p, text, re.IGNORECASE) for p in NOISE_PATTERNS)


def is_formal_review(review_state, pr_author, reviewer):
    if reviewer == pr_author:
        return False
    return review_state in ("COMMENTED", "CHANGES_REQUESTED")


# --- Analysis ---

def build_activity(pr_nodes):
    """Build per-user activity from PR data."""
    activity = defaultdict(lambda: {"authored": [], "reviewed": []})

    for pr in pr_nodes:
        if not pr or not pr.get("author"):
            continue

        pr_author = pr["author"]["login"].lower()
        if pr_author in IGNORED_USERS:
            continue

        pr_info = {"number": pr["number"], "title": pr["title"]}

        if pr.get("mergedAt"):
            activity[pr_author]["authored"].append({
                **pr_info, "merged_at": pr["mergedAt"][:10]})

        reviewers_on_this_pr = set()
        pr_created = pr["createdAt"][:10]

        for review in pr.get("reviews", {}).get("nodes", []):
            if not review or not review.get("author"):
                continue
            reviewer = review["author"]["login"].lower()
            if reviewer in IGNORED_USERS or reviewer == pr_author:
                continue
            if is_formal_review(review.get("state", ""), pr_author, reviewer) or \
               is_valid_review(review.get("body", ""), pr_author, reviewer):
                reviewers_on_this_pr.add(reviewer)

        for comment in pr.get("comments", {}).get("nodes", []):
            if not comment or not comment.get("author"):
                continue
            commenter = comment["author"]["login"].lower()
            if commenter in IGNORED_USERS or commenter == pr_author:
                continue
            if is_valid_review(comment.get("body", ""), pr_author, commenter):
                reviewers_on_this_pr.add(commenter)

        for reviewer in reviewers_on_this_pr:
            activity[reviewer]["reviewed"].append({**pr_info, "date": pr_created})

    return activity


def get_current_role(username, owners):
    u = username.lower()
    if u in owners["leads"]:
        return "lead"
    if u in owners["approvers"]:
        return "approver"
    if u in owners["reviewers"]:
        return "reviewer"
    return "member"


def parse_promotion_title(title):
    m = re.match(r"REQUEST:\s*Promotion to (\w+) for @?(\S+)", title, re.IGNORECASE)
    return (m.group(1).lower(), m.group(2).lower()) if m else (None, None)


def filter_by_date(items, date_key, since):
    cutoff = since.strftime("%Y-%m-%d")
    return [i for i in items if i.get(date_key, "") >= cutoff]


def deduplicate_reviewed(reviewed):
    seen = set()
    unique = []
    for r in reviewed:
        if r["number"] not in seen:
            seen.add(r["number"])
            unique.append(r)
    return unique


def compute_tenure_activity(user_data, reviewer_since_str):
    since = datetime.strptime(reviewer_since_str, "%Y-%m-%d").date()
    authored = filter_by_date(user_data["authored"], "merged_at", since)
    reviewed = deduplicate_reviewed(filter_by_date(user_data["reviewed"], "date", since))
    months = max(1, (date.today() - since).days // 30)

    active_months = set()
    for r in reviewed:
        active_months.add(r.get("date", "")[:7])
    for a in authored:
        active_months.add(a.get("merged_at", "")[:7])

    return {
        "reviewer_since": reviewer_since_str,
        "months_as_reviewer": months,
        "authored_during_tenure": len(authored),
        "reviewed_during_tenure": len(reviewed),
        "avg_reviews_per_month": round(len(reviewed) / months, 1),
        "months_with_activity": len(active_months),
        "months_total": months,
    }


def validate_candidate(username, target_role, activity, owners,
                        reviewer_since_dates=None, reviewer_days=90):
    criteria = CRITERIA.get(target_role)
    if not criteria:
        return None

    user_data = activity.get(username.lower(), {"authored": [], "reviewed": []})
    tenure = None

    if target_role == "approver" and reviewer_since_dates:
        reviewer_since = reviewer_since_dates.get(username.lower())
        if reviewer_since:
            reviewer_start = datetime.strptime(reviewer_since, "%Y-%m-%d").date()
            tenure_months = (date.today() - reviewer_start).days // 30
            tenure = compute_tenure_activity(user_data, reviewer_since)
            min_tenure = criteria.get("min_tenure_months", 3)
            if tenure_months >= min_tenure:
                since_date = date.today() - timedelta(days=reviewer_days)
            else:
                since_date = reviewer_start
        else:
            since_date = date.today() - timedelta(days=reviewer_days)
            tenure = {"reviewer_since": "unknown"}
    else:
        since_date = date.today() - timedelta(days=reviewer_days)

    authored = filter_by_date(user_data["authored"], "merged_at", since_date)
    reviewed = deduplicate_reviewed(
        filter_by_date(user_data["reviewed"], "date", since_date))

    validation = {
        "authored_prs": {
            "required": criteria["min_authored"],
            "actual": len(authored),
            "pass": len(authored) >= criteria["min_authored"],
        },
        "reviewed_prs": {
            "required": criteria["min_reviewed"],
            "actual": len(reviewed),
            "pass": len(reviewed) >= criteria["min_reviewed"],
        },
    }

    if target_role == "approver":
        tenure_months = tenure.get("months_as_reviewer", 0) if tenure else 0
        min_tenure = criteria.get("min_tenure_months", 3)
        validation = {
            "reviewer_tenure": {
                "required": f"{min_tenure} months",
                "actual": f"{tenure_months} months",
                "pass": tenure_months >= min_tenure,
            },
            **validation,
        }

    result = {
        "username": username,
        "current_role": get_current_role(username, owners),
        "target_role": target_role,
        "measurement_since": since_date.strftime("%Y-%m-%d"),
        "validation": validation,
        "authored_pr_links": authored,
        "reviewed_pr_links": reviewed,
        "overall_pass": all(v["pass"] for v in validation.values()),
    }

    if tenure:
        result["reviewer_tenure_detail"] = tenure

    return result


def find_inactive_maintainers(owners, activity, inactive_days):
    cutoff = date.today() - timedelta(days=inactive_days)
    leads = set(owners["leads"])
    inactive = []

    all_maintainers = set()
    for role in ["reviewers", "approvers"]:
        for u in owners[role]:
            all_maintainers.add((u, "approver" if u in owners["approvers"] else "reviewer"))

    for username, role in all_maintainers:
        if username in leads:
            continue

        user_data = activity.get(username, {"authored": [], "reviewed": []})
        all_dates = [a.get("merged_at", "") for a in user_data["authored"]] + \
                    [r.get("date", "") for r in user_data["reviewed"]]
        all_dates = [d for d in all_dates if d]
        last_activity = max(all_dates) if all_dates else "never"

        if last_activity == "never" or last_activity < cutoff.strftime("%Y-%m-%d"):
            days = (date.today() - datetime.strptime(last_activity, "%Y-%m-%d").date()).days \
                if last_activity != "never" else inactive_days
            inactive.append({
                "username": username,
                "current_role": role,
                "last_activity_date": last_activity,
                "days_inactive": days,
            })

    return sorted(inactive, key=lambda x: x["days_inactive"], reverse=True)


# --- Output ---

def output_json(validations, inactive, opts):
    print(json.dumps({
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": opts.repo,
        "criteria": CRITERIA,
        "promotion_validations": validations,
        "inactive_maintainers": inactive,
    }, indent=2))


def _format_validation_header(v):
    icon = "✅" if v["overall_pass"] else "❌"
    status = "PASS" if v["overall_pass"] else "FAIL"
    issue_ref = f" ([#{v['issue_number']}]({v['issue_url']}))" if v.get("issue_number") else ""
    return icon, status, issue_ref


def _summary_row(v):
    icon, status, issue_ref = _format_validation_header(v)
    authored = v["validation"]["authored_prs"]
    reviewed = v["validation"]["reviewed_prs"]
    tenure = v.get("reviewer_tenure_detail", {})

    if tenure.get("reviewer_since") and tenure["reviewer_since"] != "unknown":
        tenure_str = f"{tenure['months_as_reviewer']}mo (since {tenure['reviewer_since']})"
    else:
        tenure_str = f"90d (since {v.get('measurement_since', '—')})"

    return (f"| @{v['username']} | {v['target_role'].capitalize()}{issue_ref} "
            f"| {tenure_str} | {authored['actual']}/{authored['required']} "
            f"| {reviewed['actual']}/{reviewed['required']} | {icon} {status} |")


def _detail_section(v):
    icon, status, issue_ref = _format_validation_header(v)
    lines = [
        f"### {icon} {status}: @{v['username']} → {v['target_role'].capitalize()}{issue_ref}",
        "",
        f"Measurement period: since **{v['measurement_since']}**",
        "",
        "| Criteria | Required | Actual | Status |",
        "|----------|:---:|:---:|:---:|",
    ]
    for name, val in v["validation"].items():
        label = name.replace("_", " ").capitalize()
        s = "✅" if val["pass"] else "❌"
        lines.append(f"| {label} | {val['required']} | {val['actual']} | {s} |")
    lines.append("")

    tenure = v.get("reviewer_tenure_detail")
    if tenure and tenure.get("reviewer_since") != "unknown":
        lines += [
            f"**Reviewer tenure** (since {tenure['reviewer_since']}, "
            f"{tenure['months_as_reviewer']} months):",
            "",
            "| Metric | Value |",
            "|--------|:---:|",
            f"| Authored PRs during tenure | {tenure['authored_during_tenure']} |",
            f"| Reviewed PRs during tenure | {tenure['reviewed_during_tenure']} |",
            f"| Avg reviews/month | {tenure['avg_reviews_per_month']} |",
            f"| Months with activity | {tenure['months_with_activity']}/{tenure['months_total']} |",
            "",
        ]

    lines.append("<details><summary>PR evidence</summary>")
    lines.append("")
    if v["authored_pr_links"]:
        lines.append("**Authored (merged):**")
        lines += [f"- #{pr['number']} — {pr['title']}" for pr in v["authored_pr_links"]]
        lines.append("")
    if v["reviewed_pr_links"]:
        lines.append("**Reviewed:**")
        lines += [f"- #{pr['number']} — {pr['title']}" for pr in v["reviewed_pr_links"]]
        lines.append("")
    lines += ["</details>", ""]

    return lines


def output_markdown(validations, inactive, opts):
    today = date.today().strftime("%Y-%m-%d")
    lines = ["# Quarterly Promotion Review", "", f"Generated: {today} | Repo: {opts.repo}", ""]

    if validations:
        lines += [
            "## Summary", "",
            "| Candidate | Target | Tenure | Authored | Reviewed | Result |",
            "|-----------|--------|:---:|:---:|:---:|:---:|",
        ]
        for v in validations:
            lines.append(_summary_row(v))
        lines.append("")

    if not opts.user and inactive:
        lines += [
            "## Inactive Maintainers", "",
            "| Username | Role | Last Activity | Days Inactive |",
            "|----------|------|:---:|:---:|",
        ]
        for m in inactive:
            lines.append(f"| @{m['username']} | {m['current_role']} "
                         f"| {m['last_activity_date']} | {m['days_inactive']} |")
        lines.append("")

    if validations:
        lines += ["---", "", "## Details", ""]
        for v in validations:
            lines += _detail_section(v)
    else:
        lines += ["## Open Promotion Requests", "", "No open promotion requests found.", ""]
        if not opts.user and not inactive:
            lines += ["## Inactive Maintainers", "", "All maintainers are active.", ""]

    print("\n".join(lines))


# --- Main ---

def force_ipv4():
    original = socket.getaddrinfo
    def patched(*args, **kwargs):
        return [r for r in original(*args, **kwargs) if r[0] == socket.AF_INET]
    socket.getaddrinfo = patched


def main():
    opts = parse_args()

    if not GITHUB_API_TOKEN:
        print("Error: GITHUB_API_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    if opts.user and not opts.target:
        print("Error: --target is required when using --user", file=sys.stderr)
        sys.exit(1)

    for repo_arg in [opts.repo, opts.community_repo]:
        if not re.match(r"^[\w.-]+/[\w.-]+$", repo_arg):
            print(f"Error: invalid repo format: {repo_arg}", file=sys.stderr)
            sys.exit(1)

    force_ipv4()

    if opts.debug:
        print(f"Fetching OWNERS from {opts.repo}...", file=sys.stderr)
    owners = fetch_owners(opts.repo)

    if opts.debug:
        print(f"Fetching reviewer-since dates from {opts.repo} OWNERS history...", file=sys.stderr)
    reviewer_since_dates = fetch_reviewer_since_dates(opts.repo)

    since = date.today() - timedelta(days=max(opts.reviewer_days, opts.inactive_days))
    if opts.debug:
        print(f"Fetching PRs from {opts.repo} since {since}...", file=sys.stderr)
    pr_nodes = fetch_all_prs(opts.repo, since)
    if opts.debug:
        print(f"Fetched {len(pr_nodes)} PRs", file=sys.stderr)

    activity = build_activity(pr_nodes)
    validations = []

    if opts.user:
        result = validate_candidate(opts.user.lower(), opts.target, activity,
                                     owners, reviewer_since_dates, opts.reviewer_days)
        if result:
            validations.append(result)
    else:
        if opts.debug:
            print(f"Fetching open promotion issues from {opts.community_repo}...",
                  file=sys.stderr)
        for issue in fetch_promotion_issues(opts.community_repo):
            target_role, username = parse_promotion_title(issue.get("title", ""))
            if not target_role or not username:
                continue
            result = validate_candidate(username, target_role, activity,
                                         owners, reviewer_since_dates, opts.reviewer_days)
            if result:
                result["issue_number"] = issue["number"]
                result["issue_url"] = issue["url"]
                validations.append(result)

    inactive = find_inactive_maintainers(owners, activity, opts.inactive_days) \
        if not opts.user else []

    if opts.output == "json":
        output_json(validations, inactive, opts)
    else:
        output_markdown(validations, inactive, opts)


if __name__ == "__main__":
    main()
