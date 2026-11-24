# CS 520: specification features and automated test-file additions

This executable project analyzes the **local SpecMine v1.1 500-repository sample**.
Start with the concise [midpoint brief](MIDPOINT_SUMMARY.md).
Read [FEASIBILITY.md](FEASIBILITY.md) before interpreting results and
[RESEARCH_SUMMARY.md](RESEARCH_SUMMARY.md) for the generated findings. The main
cohort links exact snapshot paths; **PR-time content versions are unverified**.
The project studies associations and does not establish causation or AI authorship.

## Reproduce

Run from the cloned repository root. Python 3.14.2 was used; exact executed
package versions are in requirements.txt and outputs/inspection/environment.json.
The existing data/ Parquet files, specs.jsonl.gz, kiro_specs.jsonl.gz,
sample_repos.txt, and upstream documentation must remain in their original places.
No full dataset or external API is required.

```powershell
python -m venv rq1_analysis/.venv
rq1_analysis/.venv/Scripts/python -m pip install -r rq1_analysis/requirements.txt
rq1_analysis/.venv/Scripts/python rq1_analysis/run.py
```

On Linux/macOS, replace `rq1_analysis/.venv/Scripts/python` with
`rq1_analysis/.venv/bin/python`. The delivered environment used
`--system-site-packages` to reuse installed scientific packages; the commands
above make an isolated environment. Installation into a fresh isolated environment
has not been separately tested. Network access is needed only for package installation.

The run command verifies input hashes, inspects data, constructs the cleaned
dataset, runs statistics, executes unit tests, validates outputs, and regenerates
the research summary. It stops on failed tests or violated data invariants.
Content-based caches skip unchanged build/statistical stages. Rebuild with:

```powershell
rq1_analysis/.venv/Scripts/python rq1_analysis/run.py --force
```

Stages can be run separately after their prerequisites exist:

```powershell
rq1_analysis/.venv/Scripts/python rq1_analysis/run.py --stage inspect
rq1_analysis/.venv/Scripts/python rq1_analysis/run.py --stage build
rq1_analysis/.venv/Scripts/python rq1_analysis/run.py --stage analyze
rq1_analysis/.venv/Scripts/python rq1_analysis/run.py --stage validate
rq1_analysis/.venv/Scripts/python rq1_analysis/run.py --stage report
```

All source files and outputs are under rq1_analysis/. The scripts derive paths
from their own location, so running from another working directory is supported.
DuckDB computes null summaries directly from Parquet; pandas selectively loads
spec columns and the modest PR tables. Raw prose is streamed one record at a time.
Runtime depends on hardware. The statistical stage uses 2,000 bootstrap resamples
for each contrast. Random seeds are fixed at 520, except the recorded link audit
sample (2026). No input file is overwritten.

## Source code

- `inspect_data.py`: local inventory, actual schemas, nulls, key uniqueness,
  schema.sql discrepancies, original-input SHA-256 baseline, runtime provenance.
- `classifiers.py`: cross-language test path rules, uncertainty flags, status
  handling, and secondary English testing-directive classifier.
- `matching.py`: identical-snapshot collapse, conflicting-version detection,
  PR/tool deduplication, complete-coverage feature aggregation.
- `build_dataset.py`: raw-text hash checks, file outcomes, exact spec/PR linkage,
  temporal/history diagnostics, repository metadata, cohort/exclusion decisions.
- `analyze.py`: descriptives, contingency tests, effect sizes, confidence
  intervals, repository bootstrap, guarded cluster-robust logistic regression,
  tool/temporal/detector/influence sensitivities, PNG/PDF plots.
- `validate.py`: input integrity, uniqueness and aggregation invariants,
  independent reconstruction of outcomes, preserved manual review checks.
- `report.py`: summary generated directly from executed outputs.
- `run.py`: staged execution, caching, test logs, and failure propagation.
- `tests/`: unit tests for path normalization, multilingual code-file
  conventions, fixture exclusions, testing directives, statuses, duplicate
  snapshots/tools, archive identity, and missing-feature handling.

## Outputs

- `outputs/analysis_dataset.csv` and `.parquet`: one row per included unique PR.
- `outputs/intermediate/`: reusable text-feature, snapshot, classified-file,
  complete spec/PR link, and all-PR observation tables.
- `outputs/inspection/`: local inventory, column schemas/missingness, uniqueness,
  schema discrepancies, environment, and immutable original-input manifest.
- `outputs/tables/`: sample waterfall, exclusion combinations, feature frequencies,
  included/excluded comparisons, tool/language/repository/license descriptives,
  testing rates, association tests and effect intervals, regression coefficients,
  diagnostics, and readable model summaries.
- `outputs/figures/`: addition rates (PNG/PDF) and clustered rate differences (PNG).
- `outputs/validation/`: exclusion ledger, duplicate/ambiguous snapshot paths,
  unmatched snapshot specs, temporal audit, manual file/link reviews, uncertain
  cases, unit-test logs/JUnit XML, and validation results.
- `reviews/`: preserved, manually written audit labels/notes for 60 initial file
  paths, 25 targeted negative paths, and 12 actual local spec/PR matches. The
  targeted audit informed Rust/C# naming improvements and explicit test names
  inside example packages (flagged uncertain). These are unblinded assistant path reviews,
  not independent human content-level validation; unresolved cases are explicit.

## Analysis dataset dictionary

| Fields | Meaning |
|---|---|
| repo_name, repo_id, pr_number | PR identity; owner/repository slug and snapshot numeric ID |
| tools, tool, n_tool_records | All tool discoveries; single tool or multiple; original row count |
| has_acceptance_criteria, has_edge_cases, has_requirements | Any active exact-matched spec has the supplied feature; complete coverage required |
| has_testing_requirement | Any active matched spec has a directive matched by the secondary text rule; missing if not measurable |
| n_words | Sum of snapshot word counts over distinct active spec paths |
| n_active_spec_files, n_exact_matched_specs | Active spec-file count and reliable exact-path matches |
| repo_language, repo_stars, repo_size_kb, repo_license_spdx_id | Latest available broad-census snapshot metadata |
| test_added, test_modified, test_removed, test_renamed | At least one classified test with the corresponding status (0/1) |
| test_added_strict, test_modified_strict | Same outcome excluding detector-flagged uncertain test positives |
| n_changed_source_files | Non-test executable source files outside specification directories; all change statuses |
| n_dataset_code_files | Unique paths flagged is_code in any tool discovery, for comparison |
| n_observed_files, n_files, file_list_complete | Observed union, reported changeset size, and completeness check |
| complete_spec_coverage | Every active visible spec has unambiguous complete primary features |
| in_primary_snapshot_analysis | All inclusion conditions met |
| in_temporal_sensitivity, all_specs_temporally_overlap | All matched snapshot last-change times fall in PR creation-to-end interval |
| version_verified | Always false: local tables do not establish PR-time blob equality |
| exclusion_reasons | Semicolon-separated overlapping reasons; empty for included observations |

All other PR metadata fields retain their upstream meanings. Tool-specific
supplied rollups (n_spec_files, n_code_files, etc.) come from a deterministic
representative tool record; use the recomputed unique-file counts for research.
Repository size is available descriptively but is not fitted alongside stars in
the default model. Missing programming language is a separate Unknown category.

## Interpretation and review

The main analysis requires active visible specifications and non-test source
changes, complete net-diff file lists below GitHub's 3,000-file cap, and complete
exact-path feature coverage. Specs removed from the net diff do not supply
predictors. Missing or ambiguous features are not coded as zero. Multiple specs
use any-presence for binary features and total words for length. Model/control
choices and sensitivity definitions are documented in the research summary.

Naive contingency-test p-values assume independent PRs; use clustered intervals
and adjusted models to understand dependence, while recognizing their limits.
Template confounding, snapshot timing, curated sampling, and path-classification
error prevent strong claims about how specification practices affect testing.
Adding a file does not establish added assertions, execution, passing tests,
software quality, or a causal relationship with specification text.

For stronger annotation, independently inspect contents at pinned PR commits and
replace/supplement the preserved reviews with a documented sampling protocol.
The original 60-path sample is frozen after its initial selection so rule
improvements can be compared on the same cases. If rules change predictions on
reviewed paths, re-audit them: validation deliberately fails when saved reviews
no longer correspond to current paths/predictions.

## Citation, license, privacy

Source: [SpecMine sample](https://github.com/shyamagarwal13/specmine-official),
[data dictionary](https://github.com/shyamagarwal13/specmine-official/blob/main/DATA_DICTIONARY.md),
[full mirror](https://huggingface.co/datasets/ShyAgarwal/specmine) (not downloaded).
Cite Agarwal and Vasilescu (2026), *SpecMine: A Large-Scale Corpus of Spec-Driven
Development Artifacts*, DOI [10.5281/zenodo.22102779](https://doi.org/10.5281/zenodo.22102779).

The source README requires respecting individual repository licenses; no
standalone LICENSE is shipped in this clone. This analysis does not grant rights
to source artifacts. Avoid publishing raw source/spec prose or personal data.
Only paths, repository/PR identifiers, features, and aggregate results are
exported; author and avatar fields are excluded. The manifest verifies original
files remain byte-for-byte unchanged.
