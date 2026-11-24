# Frozen analysis cohort

The unit is one implementation PR. `repo_name` and `pr_number` jointly identify it, and `repo_id` is the SpecMine repository identifier. Empty cells mean unavailable or inapplicable. The cohort CSV records all 3,186 units.

| Field(s) | Definition |
|---|---|
| `has_acceptance_criteria`, `has_edge_cases`, `has_requirements` | Binary supplied content features aggregated across the unambiguous active snapshot specifications linked to the PR. |
| `has_testing_requirement` | Binary indicator of an explicit testing directive, extracted using the original rule-based classifier from matched snapshot text. |
| `n_words`, `repo_stars`, `n_changed_source_files` | Aggregated specification word count, repository stars at the dataset snapshot, and changed non-test source file count. Fields prefixed `log_` use log(1 + field). |
| `tool`, `repo_language` | Study tool assignment and repository language. Fields suffixed `_group` pool infrequent values as Other for regression. |
| `test_added` | Original path-based outcome, independent of the final outcome field. |
| `test_added_content_verified`, `resolved` | Content-based outcome (1 verified addition, 0 exhaustive negative, empty unknown) and whether the outcome is observed. |
| `unknown_reason`, `verification_state`, `explanation` | Saved pipeline reason and final offline audit state and explanation. Populated according to source availability. The audit state and explanation are populated for unknowns. |
| `n_eligible_added_files`, `n_files_attempted`, `n_files_inspected` | Counts from the saved verification record for eligible, attempted, and examined added files. |
| `inspection_complete`, `early_exit`, `files_avoided_early_exit` | Complete eligible inspection flag, positive-stop flag, and files skipped after a positive. |
| `pinned_commit_sha`, `commit_sha`, `confirmed_file_path`, `file_content_hash` | PR head SHA and supporting positive file's commit, path and content SHA-256 where recorded. |
| `test_detection_method`, `test_detection_evidence`, `supporting_evidence` | Saved classification method, reference to supporting evidence and recorded evidence details. |
| `processing_mode`, `new_model_requests`, `processed_without_new_grok` | Saved execution mode, count of new requests, and flag for processing without a new Grok request, where recorded. |

In result tables, rates are fractions and fields ending in `_pp` are percentage-point differences. Crude and adjusted confidence limits are pointwise 95% intervals. Holm-corrected p-values label the relevant family. Scenario bounds describe alternative outcomes for the missing PRs without editing the cohort.
