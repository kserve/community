#!/usr/bin/env python3

# Copyright 2023 The KServe Contributors
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

# This script is used to find PR reviewers on the kserve/kserve repo

import json

from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser as ArgParser
from collections import defaultdict
from datetime import date, timedelta
from enum import Enum
from os import environ as env
from typing import Dict, List
from urllib.request import Request, urlopen


class Role(str, Enum):
    AUTHOR = "author"
    REVIEWER = "reviewer"
    COMMENTER = "commenter"


# exclude known frequent actors
ignored_users = {"kserve-oss-bot", "dependabot", "yuzisun"}

args = ArgParser(description="List top PR participants",
                 formatter_class=ArgumentDefaultsHelpFormatter)
args.add_argument('-r',
                  metavar='ROLE',
                  dest='roles', type=str, nargs='+',
                  default=[r.value for r in Role],
                  help="type of PR participation")
args.add_argument('-n',
                  dest='min_num_prs', type=int,
                  default=5,
                  help="minimum number of PRs participated")
args.add_argument('-d',
                  dest='days', type=int,
                  default=180,
                  help="number of days to look back")
args.add_argument('-i',
                  metavar='USER',
                  dest='ignored_users', type=str, nargs='+',
                  default=[u for u in ignored_users],
                  help="users to be ignored")
args.add_argument('-v',
                  dest='debug', action="store_true",
                  help="debug")
args.add_argument('-f',
                  dest='json_file', type=str,
                  default="pulls.json",
                  help="JSON file to write full query results, if debug")
opts = args.parse_args()

# initialize variables from CLI script arguments
roles = sorted(set([Role(r) for r in opts.roles]))
since_date = date.today() - timedelta(days=opts.days)
min_prs_participated = opts.min_num_prs
debug = opts.debug
json_file = opts.json_file
ignored_users = set(opts.ignored_users)

# non-parameterized variables
repo = "kserve/kserve"

# the GitHub API requires an API token:
# https://docs.github.com/en/graphql/guides/forming-calls-with-graphql#authenticating-with-a-personal-access-token
GITHUB_API_TOKEN = env["GITHUB_API_TOKEN"]  # Did you export your GitHub API token?

# query template needs to be completed with repo, date, results per page, etc
query_template = """
{
  query: search(
    type: ISSUE
    query: "repo:%s is:PR comments:>1 created:>%s"
    first: %d
    # after: "$cursor"
    %s
  )
  {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        createdAt
        author {
          login
        }
        reviews(last: 10) {
          nodes {
            author {
              login
            }
            state
            createdAt
          }
        }
        comments(last: 100) {
          nodes {
            author {
              login
            }
            # bodyText
          }
        }
      }
    }
  }
}
"""


def get_query_text(repository: str = repo,
                   since: date = since_date,
                   num_results: int = 100,
                   cursor: str = None) -> str:

    query_txt = query_template % (
        repository,
        since.strftime('%Y-%m-%d'),
        num_results,
        f'after: "{cursor}"' if cursor else ""
    )
    return query_txt


def run_query(query: str) -> str:
    encoded_body = query.encode('utf8')
    url = "https://api.github.com/graphql"
    method = "POST"
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {GITHUB_API_TOKEN}"
    }
    timeout = 10
    resp = None
    resp_content = None

    try:
        req = Request(url, method=method, headers=headers, data=encoded_body)
        resp = urlopen(req, timeout=timeout)
        resp_content = resp.read().decode('utf8')
    except Exception as e:
        print(e)
    finally:
        if resp:
            resp.close()

    return resp_content


def get_paged_query_results() -> []:
    has_next_page = True
    cursor = None
    nodes = []

    while has_next_page:
        query_text = get_query_text(cursor=cursor)
        query_json = {'query': query_text}
        query_json_str = json.dumps(query_json)
        result_str = run_query(query_json_str)
        result_json = json.loads(result_str)
        page_info = result_json["data"]["query"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]
        nodes.extend(result_json["data"]["query"]["nodes"])

    if debug:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(nodes, f, ensure_ascii=False, indent=4)

    return nodes


def get_contributors() -> Dict[str, List]:
    nodes = get_paged_query_results()
    participants_to_pr_by_role = defaultdict(lambda: defaultdict(list))
    contributors_to_pr = dict()

    for node in nodes:
        pr_num = node["number"]
        author = node["author"]["login"]
        reviewers = {r["author"]["login"] for r in node["reviews"]["nodes"]} - {author}
        commenters = {r["author"]["login"] for r in node["comments"]["nodes"]} - {author}

        participants_to_pr_by_role[author][Role.AUTHOR].append(pr_num)

        for login in reviewers:
            participants_to_pr_by_role[login][Role.REVIEWER].append(pr_num)

        for login in commenters:
            participants_to_pr_by_role[login][Role.COMMENTER].append(pr_num)

    if debug:
        print("=================== all PR participants ===================")
        print(json.dumps(participants_to_pr_by_role, indent=2, sort_keys=True)
              .replace("\n      ", "")
              .replace("\n    ]", "]"))
        print("===========================================================\n\n")

    for login in participants_to_pr_by_role:
        prs_participated = set()

        for role in roles:
            prs_participated.update(participants_to_pr_by_role[login][role])

        if login not in ignored_users:
            contributors_to_pr[login] = sorted(prs_participated, reverse=True)

    return contributors_to_pr


def force_ipv4():
    # Monkey-patch socket.getaddrinfo to force IPv4 conections, since some older
    # routers and some internet providers don't support IPv6, in which case Python
    # will first try an IPv6 connection which will hang until timeout and only
    # then attempt a successful IPv4 connection
    import socket

    # get a reference to the original getaddrinfo function
    getaddrinfo_original = socket.getaddrinfo

    # create a patched getaddrinfo function which uses the original function
    # but filters out IPv6 (socket.AF_INET6) entries of host and port address infos
    def getaddrinfo_patched(*args, **kwargs):
        res = getaddrinfo_original(*args, **kwargs)
        return [r for r in res if r[0] == socket.AF_INET]

    # replace the original socket.getaddrinfo function with our patched version
    socket.getaddrinfo = getaddrinfo_patched


if __name__ == '__main__':
    force_ipv4()
    contributors = get_contributors()

    print(f"Contributors to '{repo}'"
          f" (PR {', '.join([r.value+'s' for r in roles])})"
          f" by number of PRs (>{min_prs_participated})"
          f" since {since_date.strftime('%Y-%m-%d')}:\n")

    for login, prs in sorted(contributors.items(),
                             key=lambda item: len(item[1]),
                             reverse=True):
        num_prs = len(prs)
        prs_str = str(prs)
        prs_txt = (prs_str[:60] + ' ... ]') if len(prs_str) > 60 else prs_str

        if num_prs >= min_prs_participated:
            print("%3d  %-18s %s" % (num_prs, login, prs_txt))
