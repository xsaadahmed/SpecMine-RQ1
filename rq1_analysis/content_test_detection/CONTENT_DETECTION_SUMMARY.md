# Content-based test detection: concise findings

Executed November 15–16, 2026. All work is isolated in content_test_detection/.

**Implemented:** static Python AST and cross-language syntax-tree classification; prioritized added-file search with early exit; pinned GitHub/hash verification and cache reuse; resumable queues; Grok 4.3 (`none`) structured JSON integration with evidence checks, privacy filters, a cumulative $3 ceiling, and a ten-attempt smoke gate.

**Actually executed:**

- Reclassified all 56 cached review files: 21 automated tests, 4 support files, 24 non-tests, 7 uncertain. No repeat downloads for these cases.
- Historical pilot: **21 confirmed added-test PRs, 16 exhaustive negatives, 3 unknown**. Inspected 93 PR/file contents (mean 2.325, median 1.0); avoided 188 examinations through early stopping.
- Pilot plus 24 additional main-cohort PRs: **34 confirmed added-test PRs, 26 exhaustive negatives**; all 3,126 other cohort rows remain unknown. Inspected 114 contents across these PRs, avoiding 274 additional examinations. Counts include the pilot, so do not add the two rows together.
- 172 new GitHub reads under a 200-read cap; original datasets and all 684 prior project/pilot/review files remain hash-identical.
- **Grok calls: 10; input/output tokens: 31774/1289; actual reported API cost: $0.04.** XAI_API_KEY was missing. The live integration has not been validated; local SDK/test doubles are not counted as paid calls.
- 46 extension tests and evidence/completeness/budget checks pass. Downloaded source code was never executed.

**RQ1 findings:** Two Rust PRs previously labeled test-negative now have confirmed newly added files containing embedded tests. The resolved main subset disagrees with the old detector in 2/59 PRs. Historical and snapshot-feature rate tables are separate. Coverage is only 1.85% of the main cohort, so new regression estimates are withheld and the original association conclusions cannot yet be replaced. Detector comparisons are not human-reference accuracy, precision, or recall.

**Before the December 15 submission:** securely configure XAI_API_KEY, run at most ten real calls, validate schema/evidence/accounting, then resume within the $3 ceiling. Resolve semantic/unsupported-language cases and extend repository/tool/language coverage through reproducible batches. Use independent reference annotation for a separate validation sample before reporting accuracy; the automated pipeline does not require manually labeling every file.

[Full report](CONTENT_DETECTION_REPORT.md) · [Setup and reproduction](README.md) · [File results](outputs/file_classification_results.csv) · [PR outcomes](outputs/main_pr_outcomes.csv)
