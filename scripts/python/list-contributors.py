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
from collections import defaultdict
from datetime import date, timedelta
from os import environ as env
from urllib.request import Request, urlopen


GITHUB_REPO = env.get("GITHUB_REPO", "kserve/kserve")
GITHUB_API_TOKEN = env.get("GITHUB_API_TOKEN")

repository = "kserve/kserve"
bot = "kserve-oss-bot"
dan = "yuzisun"
six_months_ago = date.today() - timedelta(days=180)

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
        number
        title
        createdAt
      }
    }
  }
}
"""


def get_query_text(repository: str = repository,
                   since_date: date = six_months_ago,
                   num_results: int = 100,
                   cursor: str = None) -> str:

    query_txt = query_template % (
        repository,
        since_date.strftime('%Y-%m-%d'),
        num_results,
        f'after: "{cursor}"' if cursor else ""
    )
    return query_txt


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


def get_contributors() -> dict:
    has_next_page = True
    cursor = None
    nodes = []
    while has_next_page:
        query_text = get_query_text(cursor=cursor)
        query_json={'query': query_text}
        query_json_str=json.dumps(query_json)
        result_str = run_query(query_json_str)
        result_json = json.loads(result_str)
        page_info = result_json["data"]["query"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]
        nodes.extend(result_json["data"]["query"]["nodes"])

        # print(result_json["data"]["query"]["nodes"])

    contributors = defaultdict(lambda: defaultdict(list))

    for node in nodes:
        pr_num = node["number"]
        author = node["author"]["login"]
        reviewers = {r["author"]["login"] for r in node["reviews"]["nodes"]} - {author, bot}
        commenters = {r["author"]["login"] for r in node["comments"]["nodes"]} - {author, bot}

        contributors[author]["authored_prs"].append(pr_num)

        for login in reviewers:
            contributors[login]["reviewed_prs"].append(pr_num)

        for login in commenters:
            contributors[login]["commented_prs"].append(pr_num)

    for login in contributors:
        authored_prs = contributors[login]["authored_prs"]
        reviewed_prs = contributors[login]["reviewed_prs"]
        commented_prs = contributors[login]["commented_prs"]
        participated_prs = list(set(authored_prs + reviewed_prs + commented_prs))

        contributors[login]["authored_prs"] = sorted(authored_prs, reverse=True)
        contributors[login]["reviewed_prs"] = sorted(reviewed_prs, reverse=True)
        contributors[login]["commented_prs"] = sorted(commented_prs, reverse=True)
        contributors[login]["participated_prs"] = sorted(participated_prs, reverse=True)

        contributors[login]["total_prs"] = len(participated_prs)

    # print(json.dumps(contributors, indent=2, sort_keys=True))

    return contributors


if __name__ == '__main__':
    force_ipv4()
    contributors = get_contributors()

    print(f"KServe contributors by number of PRs authored or reviewed since %s:\n" % six_months_ago.strftime('%Y-%m-%d'))

    for login, pr_lists in sorted(contributors.items(),
                                  key=lambda item: item[1]["total_prs"],
                                  reverse=True):

        num_prs = len(pr_lists["participated_prs"])
        prs_str = str(pr_lists["participated_prs"])
        prs_str = (prs_str[:60] + ' ... ]') if len(prs_str) > 60 else prs_str

        print("%3d  %-18s %s" % (num_prs, login, prs_str))
