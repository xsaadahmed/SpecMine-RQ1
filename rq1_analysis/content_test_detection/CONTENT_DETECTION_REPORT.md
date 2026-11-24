# Content-based test detection: executed findings

Updated November 16, 2026. Original data, midpoint baseline, historical pilot, caches, and human-review forms are preserved.

**Implemented and executed:** a static-content detector, prioritized added-file PR search with early exit, pinned GitHub retrieval/cache reuse, a resumable main-cohort queue, guarded Grok 4.3 integration, and coverage-aware RQ1 descriptions. All 684 prior files remain hash-identical.

**Grok execution:** 10 actual xAI request attempts; 31774 input tokens; 1289 output tokens; provider-reported cost **$0.04**. XAI_API_KEY was unavailable. No paid request was made. Live schema/model/account integration remains unvalidated; local SDK-parameter, schema, evidence, retry, and budget tests passed. Configure the key securely and run the at-most-ten-call smoke batch described in README.md.

## Actual outcomes

| Scope | PRs | Confirmed added test | Exhaustive negative | Unknown |
|---|---:|---:|---:|---:|
| Historical pilot | 40 | 21 | 16 | 3 |
| Entire main-cohort output queue | 3,186 | 34 | 26 | 3,126 |

The main output includes the historical pilot plus a reproducible additional 24-PR acquisition subset, for 64 active PRs total. It does not represent a completed content sweep of 3,186 PRs. All 34 positive PR outcomes were confirmed by deterministic source analysis; Grok contributed zero classifications. Verification means pinned, hash-checked code plus classifier evidence, not independent human annotation, test execution, passing tests, or improved software quality.

The 56 cached-file evaluation produced **21 automated_test, 4 test_support, 24 not_test, and 7 uncertain** results. It reused all existing content references without downloads. There were 3 resolved file-level disagreements with the filename detector: two Rust files with embedded tests missed by path rules and one Rust module file counted as a test by path rules despite declaring no cases itself. These are evidence-backed detector disagreements, not human-reference false-positive/false-negative rates. The 56 cases include modified/removed files and are not the added-file PR outcome sample.

## Search efficiency and evidence

- Pilot: 93 unique PR/file contents examined; mean 2.325 and median 1.0 files per PR; 281 eligible added-source files; 188 examinations avoided after positive early exits.
- Main: 114 unique PR/file contents examined, including the pilot; 274 avoided after positive exits. Across the 64 active PRs, mean 1.781, median 1.0. Across all 3,186 queued PRs, the mean 0.0358 and median 0 reflect mostly uninspected PRs, not efficient negative verification.
- New GitHub reads: 172, with request kinds {'content': 122, 'files': 26, 'metadata': 24}, below the configured 200-request total ceiling. Existing historical responses/content were reused. No full SpecMine download or repository clone sweep occurred.
- Every positive records repository/PR, added-file path, full head SHA, Git blob SHA, SHA-256, evidence symbol/line, method, and inspected/eligible counts. Negatives require complete compatible file lists and a resolved negative/support decision for every eligible added file. Missing, truncated, unsupported, or ambiguous content remains unknown.

Only added files are eligible for the primary outcome. Modified/removed examples remain in the separate file evaluation. Test directories are searched before test-like filenames, then other executable sources, including embedded tests. Existing repository files outside the net diff are never searched. Unknown cases do not prevent a later verified positive, and one positive cancels further retrieval for that PR.

## What changed relative to the original detector

- dallay/agentsync #247: path result 0 → content result 1, supported by src/update_check.rs.
- dallay/agentsync #262: path result 0 → content result 1, supported by src/skills_layout.rs.

Among the 60 currently resolved main-cohort PRs, 2 disagree (3.3%); both corrections are Rust and both negative-to-positive. The historical-head cohort has 37 resolved outcomes among its 39 PRs, with two disagreements. Neither comparison is an accuracy estimate. Remaining unknowns are exported by tool, repository, and language.

## RQ1 reanalysis

Recalculated rates are in outputs/tables/rq1_testing_rates.csv. Historical rows use independently retrieved historical-head feature labels; main-cohort rows use the original snapshot labels and are explicitly labeled as such. Paired path/content comparisons use the same resolved subset. The table reports unknown counts, Wilson reference intervals conditional on that selected subset, and conservative missingness identification bounds that permit every unknown to be either 0 or 1. The Wilson intervals do not correct sampling, verification selection, or repository clustering and are not population evidence.

Historical-head descriptive rates (selected verified subset):

| Feature | Absent: positives / verified | Present: positives / verified | Unknown absent / present |
|---|---:|---:|---:|
| Acceptance criteria | 14/24 | 7/13 | 0 / 2 |
| Edge cases | 11/22 | 10/15 | 1 / 1 |

Only 60/3,186 main outcomes (1.9%) are resolved. Regression was withheld: fewer_than_200_verified_PRs, less_than_80_percent_outcome_coverage. The historical pilot is small and was sampled on the old outcome; raw subset associations cannot be generalized. OpenSpec/Spec Kit exposure rates and missingness are exported separately. **The original RQ1 association conclusions cannot yet be replaced.** This extension establishes concrete measurement corrections, not a new positive/negative specification effect or a causal claim.

![Verification coverage](outputs/figures/content_verification_coverage.png)

## Remaining blockers and next steps before December 15

The live Grok smoke batch requires XAI_API_KEY. Shell/PowerShell, parser-error, and other semantic cases remain queued; privacy-sensitive files may stay unresolved even with a key. One historical PR's live net diff differs from the frozen study and remains unknown. Most main-cohort PRs are unacquired; activate reproducible batches and use the request/cost estimates before larger acquisition. All unprocessed outcomes remain unknown.

Run at most ten Grok attempts first, inspect the technical validation/accounting report, validate the smoke gate, then resume within the cumulative $3 cap. Broader execution needs enough repository/language/tool coverage to assess verification bias before fitting models. Independent human annotation of a separate stratified validation sample is still needed for accuracy, precision, or recall. It is not required to manually label every file to run the automated pipeline.

**Validation:** 46 extension unit tests pass; evidence/completeness/budget checks pass; prior-work hashes pass. Retrieved source is never executed. SDK integration was exercised with test doubles only; those are not counted as xAI calls. Reproduction, secure key setup, all outputs, and limitations are documented in README.md.
