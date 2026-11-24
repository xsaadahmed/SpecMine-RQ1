# Documentation and local-data assessment (before pipeline implementation)

Inspected the root README.md, DATA_DICTIONARY.md, schema.sql, and load.py at
upstream commit `9fbb61541046cb2fb770fa944192a3fc0b64a9b1`. All 13 sample
Parquet tables and both compressed text streams exist locally. No full-data
download is necessary. Initial read-only Python checks found:

| Table | Rows | Actual columns | Relationship |
|---|---:|---:|---|
| spec_files | 28,583 | 129 | unique file_url_sha16; repository/path is NOT unique |
| spec_content_features | 28,583 | 40 | file_url_sha16 to spec_files, one-to-one |
| pull_requests | 5,335 | 25 | tool/repo_name/pr_number unique; 5,322 underlying PRs |
| pr_files | 288,267 | 12 | tool/repo_name/pr_number to PR records; deduplicate paths across tools |

The dictionary labels spec_files as 124 columns, but the actual file has 129;
the pipeline must inspect the actual schema. The dictionary lists three change
statuses, but data also contain `renamed` (28,626 tool-level file rows).
Renamed tests are neither newly added tests nor modified tests in the primary
definitions; they will be retained and reported separately.

There are 3,102 repeated repository/path spec rows. Seventeen paths have multiple
content hashes and sixteen have differing primary feature vectors. Arbitrary
drop_duplicates would choose a version without evidence. Identical content and
feature duplicates can be collapsed; conflicting paths must be flagged.

A preliminary exact-path lookup (before removing ambiguity or requiring complete
PR coverage) finds at least one snapshot spec for 5,316 unique PRs. This is an
upper bound on usable linkage, not a validated analysis count. Historical
OpenSpec change/archive paths are common. No archive-prefix stripping, basename,
branch-name, or repository-only join is justified by these tables.

The PR tables have no head/base commit hashes, changed-file blob hashes, patches,
or previous_filename. The spec history table records commits but not historical
contents. Therefore **no PR-time specification version can be proved from these
four tables**. Snapshot last-commit dates can detect obvious timing mismatches;
they cannot establish blob equality. The main executable analysis will be
explicitly exploratory: exact, unambiguous paths, complete active-spec feature
coverage, visible source changes, complete file lists. A temporal-overlap subset
will be a sensitivity analysis, never described as verified historical content.
Strictly version-verified RQ1 analysis remains infeasible without pinned PR
content. PR creation-time predictors in particular cannot be reconstructed.

The README states this is a purposive sample of PR-rich/high-star repositories,
and the PR sweep itself targets repositories with at least ten stars. Thus its
rates do not estimate prevalence in the full corpus or all software development.
Tool labels are path/discovery attributions, not evidence of AI authorship.

All research files and derived outputs belong under rq1_analysis/. Inputs are
read-only; a SHA-256 manifest will verify that they remain unchanged. Raw
specification prose and author information will not be copied to public outputs.
Follow source-repository license terms for underlying artifacts. No standalone
LICENSE file is shipped in this clone; this project does not grant a new license
to the dataset or redistribute its source text.
