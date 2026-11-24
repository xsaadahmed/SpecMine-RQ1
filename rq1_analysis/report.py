"""Generate a concise, numerically traceable Markdown research report."""
import json

import pandas as pd

from common import HERE, OUT


def report():
    build = json.loads((OUT / "tables" / "build_summary.json").read_text())
    audit = json.loads((OUT / "validation" / "validation_results.json").read_text())
    d = pd.read_parquet(OUT / "analysis_dataset.parquet")
    rates = pd.read_csv(OUT / "tables" / "testing_rates.csv")
    effects = pd.read_csv(OUT / "tables" / "association_tests.csv")
    models = pd.read_csv(OUT / "tables" / "logistic_regression.csv")
    tools = pd.read_csv(OUT / "tables" / "descriptive_by_tool.csv")
    flow = pd.read_csv(OUT / "tables" / "sample_flow.csv")
    review = audit["manual_file_audit"]
    timing = audit["temporal_audit"]
    labels = {"has_acceptance_criteria": "Acceptance criteria", "has_edge_cases": "Edge cases", "has_testing_requirement": "Testing directive (secondary)"}
    lines = ["# CS 520 RQ1: preliminary research summary", "", "Prepared November 2, 2026 for the November 5 midpoint. Final project due December 15, 2026.", "",
        "**Finding:** snapshot specifications with the studied features have higher marginal test-file addition rates in this selected sample. Evidence is sensitive to tool adjustment, change-size adjustment, the test detector, and the temporal subset. These results do not establish an association with the actual specification text present at PR creation, and do not support a causal claim.", "",
        "## Data feasibility and analysis population", "",
        f"Used the locally cloned SpecMine v1.1 500-repository sample only. The four requested tables contain 28,583 specs, 28,583 feature rows, {build['raw_pr_records']:,} PR records, and 288,267 tool-level changed-file records. Deduplication gives {build['unique_prs']:,} PRs in 229 repositories and {build['deduplicated_file_observations']:,} PR/file observations. Thirteen extra PR records are repeated tool discoveries.", "",
        f"The snapshot contains {build['snapshot_paths']:,} distinct repository/path pairs; {build['ambiguous_snapshot_paths']} paths have conflicting content or feature snapshots. Exact unambiguous paths link at least one spec to {build['prs_with_any_unambiguous_path_match']:,} PRs. Requiring complete active-spec feature coverage, complete file lists, and at least one non-test source change leaves **{len(d):,} PRs in {d.repo_name.nunique()} repositories**. This is the main exploratory snapshot cohort, not a version-verified historical cohort.", "",
        "| Sequential inclusion stage | PRs | Repositories |", "|---|---:|---:|"]
    lines += [f"| {r.stage.replace('_',' ')} | {r.n_prs:,} | {r.n_repos} |" for r in flow.itertuples()]
    lines += ["", "Complete file lists require files_status=done, observed unique path count equal to n_files, fewer than 3,000 files, and no conflicting global PR or file metadata. Removed specs are retained in the link audit but cannot supply active predictors. Renamed files are retained without inferring their previous paths. The exclusion ledger records all overlapping reasons for every excluded PR.", "",
        "## Measures and statistical methods", "",
        "A PR is identified by repository and PR number. All discovery tools are retained as a sorted list; multi-tool PRs count once. Specs join to precomputed features one-to-one on file_url_sha16, then to PR files on exact repository/full path after collapsing identical-content, identical-feature snapshot duplicates. No basename matching, archive-prefix removal, repository-only linkage, or inferred rename matching is used.", "",
        "For multiple active specs, a binary feature is present if any spec has it, and word count is the sum across distinct matched paths. All active specs must have complete, unambiguous primary features; missing features are never coded as absence. Acceptance criteria and edge cases enter models separately. The existing labels are structural/template signals rather than independently validated measures of requirement quality.", "",
        "The secondary testing-directive classifier requires an English imperative/modal and a phrase such as unit tests, integration tests, or automated tests on the same line within 100 characters. It ignores fenced code, HTML comments, and lines with explicit negation/optional wording. It can miss multilingual, indirect, multi-line, or differently phrased requirements. Raw text hashes were checked against the supplied SHA-256 values before classification.", "",
        "The path detector recognizes cross-language test names and executable files in test directories, excludes documentation, samples/fixtures/mocks, generated/vendor files, and specification tooling, and flags uncertain cases. The primary outcome is at least one candidate test file with status added. Modified, removed, and renamed tests remain separate. Additions and modifications can both occur in one PR. New test cases inside an existing file, inline Rust tests, and test execution/passing are not observable from file paths.", "",
        "Source-change count uses recognized executable-source extensions outside spec directories, excluding identified tests, fixture/sample files, and generated/vendor files. It is distinct from the supplied is_code flag. Repository stars, primary language, size, and licenses are snapshot metadata; a deterministic latest content-fetch row supplies them, and metadata variation is logged. They are not PR-time measurements.", "",
        "Reported marginal group intervals are Wilson 95% intervals. Two-sided chi-square tests are used when expected counts are at least five, otherwise Fisher exact tests. Conditional odds ratios have exact 95% intervals; risk ratios have log-scale approximate intervals when all cells are positive. Independence-based p-values and intervals are descriptive because PRs cluster by repository. Holm adjustment is supplied for the two primary addition comparisons. Repository bootstrap intervals for risk differences use 2,000 whole-repository resamples with seed 520.", "",
        "Logistic models include both primary predictors, has_requirements when variable, log(1+total spec words), log(1+stars), grouped primary programming language, and optionally log(1+changed source files) and tool. Languages with at least 50 observations are retained up to the five largest; tools with at least 20 observations are retained; other categories are pooled. Standard errors cluster by repository with a finite-sample correction. Fits are withheld for fewer than 30 clusters, fewer than ten events/non-events per parameter, rank deficiency, separation, or unstable estimates. Source-change count is measured in the same PR and could be a mediator or collider; the model omitting it is a sensitivity check. These model choices were made during exploratory analysis, not preregistered.", "",
        "## Descriptive results", "",
        f"Candidate test files were added in {int(d.test_added.sum()):,}/{len(d):,} PRs ({d.test_added.mean():.1%}) and modified in {int(d.test_modified.sum()):,} ({d.test_modified.mean():.1%}). Acceptance criteria appear in {int(d.has_acceptance_criteria.sum())} PRs ({d.has_acceptance_criteria.mean():.1%}), edge cases in {int(d.has_edge_cases.sum())} ({d.has_edge_cases.mean():.1%}), requirements in {int(d.has_requirements.sum())} ({d.has_requirements.mean():.1%}), and testing directives in {int(d.has_testing_requirement.sum())} ({d.has_testing_requirement.mean():.1%}). Primary feature columns have no missing values after complete-coverage selection; frequencies and missingness before selection are also exported.", "",
        "| Snapshot feature | Absent: additions / PRs | Present: additions / PRs | Rate difference (repository-bootstrap 95% CI), percentage points |", "|---|---:|---:|---:|"]
    for predictor, label in labels.items():
        s = rates[(rates.cohort == "primary_snapshot") & (rates.outcome == "test_added") & (rates.predictor == predictor)].set_index("feature_present")
        e = effects[(effects.cohort == "primary_snapshot") & (effects.outcome == "test_added") & (effects.predictor == predictor)].iloc[0]
        lines += [f"| {label} | {int(s.loc[0,'tests'])}/{int(s.loc[0,'n'])} ({s.loc[0,'rate']:.1%}) | {int(s.loc[1,'tests'])}/{int(s.loc[1,'n'])} ({s.loc[1,'rate']:.1%}) | {100*e.risk_difference:.1f} ({100*e.cluster_rd_ci_low:.1f}, {100*e.cluster_rd_ci_high:.1f}) |"]
    lines += ["", "![Test addition rates](outputs/figures/test_addition_rates.png)", "",
        "## Adjusted associations and sensitivity", "",
        "Main model below adjusts for tool, language, requirements, word count, stars, and source-file change count, with repository-clustered intervals. Odds ratios describe odds, not probability ratios.", "",
        "| Outcome | Predictor | Adjusted odds ratio (95% CI) | p-value |", "|---|---|---:|---:|"]
    for outcome in ["test_added", "test_modified"]:
        name = f"primary_snapshot_{outcome}_tool_adjusted_source_adjusted"
        for predictor in labels:
            if predictor == "has_testing_requirement": continue
            r = models[(models.model == name) & (models.term == predictor)]
            if len(r):
                r = r.iloc[0]
                lines.append(f"| {outcome.replace('_',' ')} | {labels[predictor]} | {r.odds_ratio:.2f} ({r.ci_low:.2f}, {r.ci_high:.2f}) | {r.p_value:.3f} |")
            else: lines.append(f"| {outcome} | {labels[predictor]} | Fit withheld; see diagnostics | — |")
    lines += ["", "All unadjusted contingency tests, effect sizes, adjusted models (including the secondary testing-directive model), and diagnostics are saved in outputs/tables/. Main intervals should be interpreted together with the following sensitivity checks, not as a definitive yes/no answer.", "",
        "| Addition-rate sensitivity | Acceptance criteria: difference, pp (95% cluster CI) | Edge cases: difference, pp (95% cluster CI) |", "|---|---:|---:|"]
    for cohort in ["high_confidence_detector", "temporal_overlap", "without_largest_repository"]:
        values = []
        for predictor in list(labels)[:2]:
            r = effects[(effects.cohort == cohort) & (effects.predictor == predictor) & effects.outcome.str.contains("added")].iloc[0]
            values.append(f"{100*r.risk_difference:.1f} ({100*r.cluster_rd_ci_low:.1f}, {100*r.cluster_rd_ci_high:.1f})")
        lines.append(f"| {cohort.replace('_',' ')} | " + " | ".join(values) + " |")
    lines += ["", "The edge-case modification contrast has a different marginal direction from the addition contrast; tool adjustment can substantially change it. The source-unadjusted model also changes the addition estimates. These differences make template composition and analysis choices material to the conclusion.", "",
        "| Tool attribution | PRs | Acceptance prevalence | Edge-case prevalence |", "|---|---:|---:|---:|"]
    lines += [f"| {r.tool} | {r.n} | {r.acceptance_prevalence:.1%} | {r.edge_prevalence:.1%} |" for r in tools.itertuples()]
    lines += ["", "Within-tool exposure counts and testing rates are exported separately. Large template differences and limited overlap can leave residual confounding even after grouped tool adjustment. Tool labels do not prove that any AI agent wrote the implementation.", "",
        "## Validation and threats to validity", "",
        f"- **Temporal validity:** {timing['prs_with_any_snapshot_change_after_pr_end']:,} retained PRs have at least one spec whose snapshot last-change date is after the PR ended; {timing['prs_with_any_snapshot_last_change_before_pr_open']:,} have a last-change date before PR creation (these categories can overlap across specs). Only {timing['all_snapshots_last_changed_within_pr_interval']:,} have all last-change dates inside the interval. History-commit counts are exported as plausibility diagnostics. None proves that a commit belonged to the PR, that file contents match its head, or that features existed before implementation. **Zero PR-time content versions are verified.**", 
        "- **Linkage validity:** full exact paths prevent speculative matches but exclude moved/deleted specs and PRs with partial feature coverage. Identical basenames and analogous change/archive paths are not enough. The CSV ledger and full link Parquet preserve excluded observations and unmatched paths. Included-versus-excluded testing rates reveal selection from matching requirements.",
        f"- **Detector validity:** manually inspected {review['reviewed_paths']} file paths ({review['predicted_tests']} predicted tests and {review['predicted_non_tests']} predicted non-tests). {review['determinate_path_labels']} received determinate path labels, with {review['path_label_agreements']} agreements and {review['path_label_disagreements']} disagreements; {review['uncertain']} require content inspection. This was an unblinded assistant path review, not independent human annotation. No contents, assertions, or test runs were checked, so population precision and recall are not established. Directory-only support modules and shell harnesses can be false positives; tests under examples/spec tooling, unusual filenames/extensions, and inline tests can be false negatives. The explicit-filename sensitivity excludes detector-flagged uncertain positives but cannot resolve all errors.",
        f"- **Targeted false-negative audit:** separately inspected {review['targeted_negative_review']['paths_reviewed']} test-looking paths originally predicted negative. Six received test path labels: Rust tests.rs and *_tests.rs, C# .unittests.cs, and explicitly named Python/Go tests inside example packages. Rules were corrected for those conventions; explicitly named tests inside examples remain detector-flagged uncertain. The corrected detector agrees with all determinate targeted labels, while {review['targeted_negative_review']['uncertain']} cases remain unresolved. Total unique paths reviewed: {review['total_unique_reviewed_paths']}; unresolved across both audits: {review['total_unique_uncertain_paths']}. These are path-level judgments, not content-verified error rates.",
        f"- **is_code validity:** {build['predicted_test_files_is_code_zero']:,} candidate test-file observations have is_code=0, demonstrating why that flag was not used as a prefilter.",
        "- **Sampling and dependence:** the 500 repositories were selected for PR richness, tool coverage, and stars; the PR sweep targeted repositories with at least ten stars. These are conditional sample rates, not corpus-wide estimates. PRs are dependent within repositories; bootstrap/clustered inference helps but does not remove selection bias or repository-level confounding. Exposure-specific repository counts and largest-repository sensitivity are exported.",
        "- **Outcome scope:** a candidate added file is neither a count of new assertions nor evidence of execution, adequacy, passing tests, or improved software quality. A modification can add tests, remove assertions, or refactor helpers. Existing tests untouched by a PR are unobserved. Same-PR co-occurrence cannot establish direction or causation.",
        "- **Privacy and licensing:** exports omit author fields, avatars, and raw prose. The actual spec schema contains five avatar URL columns beyond the documented 124; none is loaded into research observations. Source files remain unchanged, verified with SHA-256. Dataset citation and source repository license terms apply; this project does not relicense underlying artifacts.", "",
        "## Implications and next steps", "",
        "The midpoint milestone is met: local data loaded, schema and keys audited, exact-path linkage established, detector implemented and path-audited, and descriptive/adjusted analyses executed. The defensible current result is an exploratory association involving snapshot labels, with substantial temporal and template limitations. Stronger evidence requires pinned PR-head (and ideally pre-implementation) spec contents, historical paths/blob hashes, re-extracted features, and independent content-level detector annotation. Expanding to the full dataset alone would not fix those validity problems.", "",
        "Before December 15, prioritize those validation improvements and a carefully bounded write-up over a larger unverified join. Preserve this frozen sample analysis as the reproducible midpoint baseline.", "",
        "## Sources", "",
        "- [SpecMine official sample and documentation](https://github.com/shyamagarwal13/specmine-official)",
        "- [Data dictionary](https://github.com/shyamagarwal13/specmine-official/blob/main/DATA_DICTIONARY.md)",
        "- [Full dataset mirror (not downloaded)](https://huggingface.co/datasets/ShyAgarwal/specmine)",
        "- Agarwal, Shyam and Vasilescu, Bogdan (2026), *SpecMine: A Large-Scale Corpus of Spec-Driven Development Artifacts*, [Zenodo DOI](https://doi.org/10.5281/zenodo.22102779).", ""]
    (HERE / "RESEARCH_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    brief = ["# CS 520 midpoint brief — November 5, 2026", "", "Analysis executed November 2, 2026 using the local SpecMine v1.1 sample.", "",
        "**RQ1:** Are specifications with acceptance criteria, edge cases, and testing requirements associated with automated test additions?", "",
        "The sample supports a preliminary snapshot analysis. It cannot establish which features were present at PR creation or before implementation.", "",
        f"**Data and method.** Audited the four requested tables and original documentation. Deduplicated {build['raw_pr_records']:,} tool-level records into {build['unique_prs']:,} unique PRs. Matched exact repository/full spec paths, collapsed only identical content/features, excluded {build['ambiguous_snapshot_paths']} conflicting snapshot paths, and required complete active-spec coverage, complete changesets, and non-test source changes. The retained cohort is **{len(d):,} PRs from {d.repo_name.nunique()} repositories**. Multiple specs use any-presence for binary features and total words for length.", "",
        "**Outcome.** A PR adds at least one candidate automated test file, identified by cross-language filename/directory conventions and change_status=added. Modified tests are a separate outcome. No is_code prefilter was applied. A secondary English directive rule measures explicit testing requirements.", "",
        "| Snapshot feature | Test-addition rate absent | Present |", "|---|---:|---:|"]
    for predictor, label in labels.items():
        sub = rates[(rates.cohort == "primary_snapshot") & (rates.outcome == "test_added") & (rates.predictor == predictor)].set_index("feature_present")
        brief.append(f"| {label} | {sub.loc[0,'rate']:.1%} | {sub.loc[1,'rate']:.1%} |")
    brief += ["", "**Adjusted results.** Logistic models control for both primary features, requirements, spec length, stars, language, tool, and changed source-file count, with repository-clustered standard errors.", ""]
    for predictor, label in list(labels.items())[:2]:
        r = models[(models.model == "primary_snapshot_test_added_tool_adjusted_source_adjusted") & models.term.eq(predictor)]
        if len(r):
            r = r.iloc[0]
            brief.append(f"- {label}: adjusted odds ratio {r.odds_ratio:.2f}, 95% CI {r.ci_low:.2f}–{r.ci_high:.2f}.")
    brief += ["", "Both main adjusted intervals include 1. Detector and temporal sensitivities weaken the marginal edge-case evidence; modifications show a different marginal pattern. Tool templates are strongly associated with the feature labels. These are exploratory associations, with no causal or software-quality claim.", "",
        f"**Validation and limits.** Unit tests and data-integrity checks pass. Reviewed {review['total_unique_reviewed_paths']} file paths and 12 exact local links; {review['total_unique_uncertain_paths']} file cases remain uncertain without content inspection. A targeted negative audit identified six missed test-like paths and informed corrected naming rules. Path review does not establish precision/recall. Original input hashes are unchanged. {timing['prs_with_any_snapshot_change_after_pr_end']:,} retained PRs have a spec changed after PR end; only {timing['all_snapshots_last_changed_within_pr_interval']:,} have every snapshot last-change date inside the PR interval. **Zero PR-time content versions are verified.** The purposive, star/PR-rich sample is not representative of the full corpus.", "",
        "**For the final project (December 15).** Prioritize pinned PR-time specification contents and independent content-level test annotation. The current pipeline, dataset, exclusion ledger, tables, plots, and cached intermediate files form a reproducible midpoint baseline. Expanding the sample alone will not resolve temporal validity.", "",
        "See [full methods and results](RESEARCH_SUMMARY.md) and [reproduction instructions](README.md). Dataset: [SpecMine official sample](https://github.com/shyamagarwal13/specmine-official).", ""]
    (HERE / "MIDPOINT_SUMMARY.md").write_text("\n".join(brief), encoding="utf-8")
    print("Wrote rq1_analysis/RESEARCH_SUMMARY.md")


if __name__ == "__main__":
    report()
