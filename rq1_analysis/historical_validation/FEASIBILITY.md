# Historical validation feasibility, November 2, 2026

The existing midpoint reports, source implementation, dataset, and reviews were
read before extension work. Their 103 existing substantive files are fingerprinted
in baseline_manifest.json. No baseline script is run or edited by this extension.

The GitHub connector successfully returned Chorus-AIDLC/Chorus PR 272's exact
head SHA and base SHA, the PR commit list, and a specification at its pinned head
SHA. The contents response includes a Git blob SHA and base64 bytes. Thus pinned
PR-head verification is feasible, subject to repository/commit/file accessibility.
This probe is a feasibility example, not a member selected into the pilot by hand.

API documentation permits a commit SHA as the contents `ref`. Changed-file
responses expose current/previous paths and statuses. Pagination and API caps
must be checked; the PR commit endpoint caps at 250 commits, and PR file lists
at 3,000 files. No truncated list is treated as complete.

The pilot will freeze 40 PRs from the midpoint's closed OpenSpec/Spec Kit PRs:
20 per tool, with 8 acceptance-positive and 12 acceptance-negative PRs per tool.
Allocation balances edge-case flags and test-addition outcomes within those
groups, subject to available cells. Hash ordering with a fixed seed makes draws
reproducible; every stratum's frame size, draw size, and inclusion probability
will be recorded. Sampling depends on both snapshot exposures and outcomes, so
unweighted pilot testing rates cannot estimate the midpoint frame's association.
Any weighted pilot estimates will be exploratory and clearly labeled.

Use PR-head content only when Git blob verification succeeds and the complete
set of active spec paths can be resolved. Resolve renamed paths only using the
API's previous_filename, never guessed archive rewrites. Deleted specs have no
head content; earlier contents, if retrieved, are separately labeled.

For earlier content, inspect the PR's actual commit sequence and changed-file
lists. Only a verified linear prefix with no preceding executable source/test
changes can support an anchor at the parent of the first observed implementation
commit. Retrieve specs at that anchor independently. This establishes presence
before recorded implementation within that history, not proof of genuinely
pre-implementation text: squashing, force pushes, work before the PR, other
branches, and unobserved work remain possible. A PR's present-day base SHA or
creation timestamp alone does not establish precedence.

The original acceptance/edge feature extraction code is not shipped in the
sample repository. New documented structural rules must therefore be applied to
both pinned historical content and the same snapshot content. Compare those
same-rule labels to isolate content-version differences. Separately compare
new snapshot-rule labels to supplied snapshot labels to expose definition drift.
Do not conflate the two mismatch rates.

Independent test validation will produce blank human-label fields and pinned
content references. Existing assistant labels will not be promoted to ground
truth. Precision and recall remain unavailable until trustworthy annotation
and adjudication exist.

Sources: [contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content),
[PR files API](https://docs.github.com/en/rest/pulls/pulls#list-pull-requests-files),
[PR commits API](https://docs.github.com/en/rest/pulls/pulls#list-commits-on-a-pull-request).
