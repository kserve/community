# Contributing to KServe

So, you want to hack on KServe? Yay!

The following sections outline the process all changes to the KServe
repositories go through.  All changes, regardless of whether they are from
newcomers to the community or from the core team follow the
same process and are given the same level of review.

- [Working groups](#working-groups)
- [Code of conduct](#code-of-conduct)
- [Design documents](#design-documents)
- [Contributing a feature](#contributing-a-feature)
- [Setting up to contribute to KServe](#setting-up-to-contribute-to-kserve)
- [Pull requests](#pull-requests)
- [Issues](#issues)
- [Promote your company on kserve.io](#promote-your-company-on-kserveio)
- [Tell the world you're using KServe](#tell-the-world-youre-using-kserve)


## Working groups

Any feature contribution to KServe should be started by first engaging with the
KServe working group.

## Code of conduct

All members of the KServe community must abide by the [Code of Conduct](https://github.com/lfai/foundation/blob/main/codeofconduct.md).

## Design documents

Any substantial design deserves a design document. Design documents are written with Google Docs and
should be shared with the community by adding the doc to our shared Drive
and sending a note to the working group to let people know the doc is there.

When documenting a new design, we recommend a 2-step approach:

1. Use the short-form
[RFC template]()
to outline your ideas and get early feedback.
1. Once you have received sufficient feedback and consensus, you may use the longer-form
[design doc template]()
to specify and discuss your design in more details.

To use either template, open the template and select "Use Template" in order to bootstrap your document.

## Contributing a feature

In order to contribute a feature to KServe you'll need to go through the following steps:

- Discuss your idea with the working group on slack or discussion thread.

- Once there is general agreement that the feature is useful, create a GitHub issue to track the discussion. The issue should include information
about the requirements and use cases that it is trying to address. Include a discussion of the proposed design and technical details of the
implementation in the issue.

- If the feature is substantial enough:

  - Working group leads will ask for a design document as outlined in the previous section.
  Create the design document and add a link to it in the GitHub issue. Don't forget to send a note to the
  working group to let everyone know your document is ready for review.

  - Depending of the breath of the design and how contentious it is, the working group leads may decide
  the feature needs to be discussed in one or more working group meetings before being approved.

  - Once the major technical issues are resolved and agreed upon, post a note to the working group's mailing
  list with the design decision and the general execution plan.

- Submit PRs to [kserve/kserve](https://github.com/kserve/kserve) with your code changes.

- Submit PRs to [kserve/website](https://github.com/kserve/website) with
documentation for your feature, including usage examples when possible. See [here](https://github.com/kserve/website/blob/main/docs/help/contributor/mkdocs-contributor-guide.md)
to learn how to write docs for kserve.io.

> Note that we prefer bite-sized PRs instead of giant monster PRs. It's therefore preferable if you
can introduce large features in smaller reviewable changes that build on top of one another.

If you would like to skip the process of submitting an issue and
instead would prefer to just submit a pull request with your desired
code changes then that's fine. But keep in mind that there is no guarantee
of it being accepted and so it is usually best to get agreement on the
idea/design before time is spent coding it. However, sometimes seeing the
exact code change can help focus discussions, so the choice is up to you.

## Setting up to contribute to KServe

Check out this [README](https://github.com/kserve/kserve/blob/master/README.md) to learn about
the KServe source base and setting up your [development environment](https://kserve.github.io/website/master/developer/developer/).

## Pull requests

If you're working on an existing issue, simply respond to the issue and express
interest in working on it. This helps other people know that the issue is
active, and hopefully prevents duplicated efforts.

To submit a proposed change:

- Fork the affected repository.

- Create a new branch for your changes.

- Develop the code/fix.

- Add new test cases. In the case of a bug fix, the tests should fail
  without your code changes. For new features try to cover as many
  variants as reasonably possible.

- Modify the documentation as necessary.

- Verify the entire CI process (building and testing) works.

While there may be exceptions, the general rule is that all PRs should
be 100% complete - meaning they should include all test cases and documentation
changes related to the change.

When ready, if you have not already done so, [sign off the commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits) and submit
the PR.

See [Writing Good Pull Requests](https://github.com/istio/istio/wiki/Writing-Good-Pull-Requests) for guidance on creating
pull requests, and [Reviewing Pull Requests]() for the PR review
we use.

## Issues

[GitHub issues](https://github.com/kserve/kserve/issues/new/choose) can be used to report bugs or submit feature requests.

When reporting a bug please include the following key pieces of information:

- The version of the project you were using (e.g. version number,
  or git commit)

- Setup environment you are using.

- The exact, minimal, steps needed to reproduce the issue.
  Submitting a 5 line script will get a much faster response from the team
  than one that's hundreds of lines long.

## Promote your company on kserve.io

If your company supports KServe or uses in on production, you can list it on our [adopters page](https://kserve.github.io/website/master/community/adopters).
We have categories for *providers* (who offer hosted or managed KServe services
to their customers), *end user* (who use and consume KServe) and *integrations* (commercial or open source products
that work with KServe).

Please add your company logo, preferably in SVG format, to [here](https://github.com/kserve/website/tree/main/docs/images).
