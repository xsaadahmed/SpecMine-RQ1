# Historical validation pilot: concise findings

Executed November 2, 2026. Original November 5 midpoint baseline preserved unchanged.

- Frozen sample: 40 PRs, 20 per tool (OpenSpec/Spec Kit), with 16 acceptance-positive cases and both edge/outcome classes represented.
- Verified **70 pinned head spec-file observations across 39 complete PRs**. One PR now has an empty net diff; no snapshot fallback or replacement was used.
- 21/70 spec observations differ in bytes from their snapshots. With the same new rules applied to both versions, acceptance labels change in 2/39 PRs and edge labels in 2/39; testing-directive labels change in 0/39. Definition drift is separately identified in one snapshot acceptance label and one edge label.
- Earlier pinned content is complete for **11 PRs** before the first observed executable-code change in a verified history prefix. These are 5 OpenSpec and 6 Spec Kit PRs. Their measured labels agree with head labels. **Genuine precedence over all implementation work remains unproven.**
- Prepared **56 pinned content-review cases**, all with content hashes and blank human labels. Precision/recall remain unavailable pending independent annotations.
- Reanalysis reports exposure counts and separate tool results. Conservative simultaneous 95% finite-frame design bounds all span zero and are very wide. Unequal weights, a high-weight feature-definition disagreement, and one unresolved PR make the point estimates unstable; naive tests and regression are withheld. This pilot does not establish a positive or negative specification effect or show that templates fully explain the original association.
- 22 extension tests and evidence/integrity checks pass; all 103 baseline files remain hash-identical. No full-corpus download.

[Detailed report](PILOT_REPORT.md) · [Reproduce](README.md) · [Blank human-review CSV](outputs/human_review.csv) · [Historical cohort](outputs/historical_head_analysis_cohort.csv)
