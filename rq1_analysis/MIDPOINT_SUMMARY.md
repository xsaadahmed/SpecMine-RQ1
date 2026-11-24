# CS 520 midpoint brief — November 5, 2026

Analysis executed November 2, 2026 using the local SpecMine v1.1 sample.

**RQ1:** Are specifications with acceptance criteria, edge cases, and testing requirements associated with automated test additions?

The sample supports a preliminary snapshot analysis. It cannot establish which features were present at PR creation or before implementation.

**Data and method.** Audited the four requested tables and original documentation. Deduplicated 5,335 tool-level records into 5,322 unique PRs. Matched exact repository/full spec paths, collapsed only identical content/features, excluded 17 conflicting snapshot paths, and required complete active-spec coverage, complete changesets, and non-test source changes. The retained cohort is **3,186 PRs from 215 repositories**. Multiple specs use any-presence for binary features and total words for length.

**Outcome.** A PR adds at least one candidate automated test file, identified by cross-language filename/directory conventions and change_status=added. Modified tests are a separate outcome. No is_code prefilter was applied. A secondary English directive rule measures explicit testing requirements.

| Snapshot feature | Test-addition rate absent | Present |
|---|---:|---:|
| Acceptance criteria | 53.3% | 62.3% |
| Edge cases | 51.1% | 60.2% |
| Testing directive (secondary) | 52.3% | 65.0% |

**Adjusted results.** Logistic models control for both primary features, requirements, spec length, stars, language, tool, and changed source-file count, with repository-clustered standard errors.

- Acceptance criteria: adjusted odds ratio 1.55, 95% CI 0.74–3.24.
- Edge cases: adjusted odds ratio 1.57, 95% CI 0.98–2.50.

Both main adjusted intervals include 1. Detector and temporal sensitivities weaken the marginal edge-case evidence; modifications show a different marginal pattern. Tool templates are strongly associated with the feature labels. These are exploratory associations, with no causal or software-quality claim.

**Validation and limits.** Unit tests and data-integrity checks pass. Reviewed 85 file paths and 12 exact local links; 19 file cases remain uncertain without content inspection. A targeted negative audit identified six missed test-like paths and informed corrected naming rules. Path review does not establish precision/recall. Original input hashes are unchanged. 1,085 retained PRs have a spec changed after PR end; only 1,521 have every snapshot last-change date inside the PR interval. **Zero PR-time content versions are verified.** The purposive, star/PR-rich sample is not representative of the full corpus.

**For the final project (December 15).** Prioritize pinned PR-time specification contents and independent content-level test annotation. The current pipeline, dataset, exclusion ledger, tables, plots, and cached intermediate files form a reproducible midpoint baseline. Expanding the sample alone will not resolve temporal validity.

See [full methods and results](RESEARCH_SUMMARY.md) and [reproduction instructions](README.md). Dataset: [SpecMine official sample](https://github.com/shyamagarwal13/specmine-official).
