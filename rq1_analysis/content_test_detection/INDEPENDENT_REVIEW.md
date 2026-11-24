# Independent source review

The worksheet has 12 pinned files across eight language categories. It includes cases from the original six-file packet, a test-support example, a schema migration, and four files from previously unresolved PRs. This is a targeted challenge set. Treat measured agreement as evidence about these files and the trial protocol.

1. Open `outputs/full_cohort/final_verification_v1/independent_review_v1/source_review.html`. It displays the complete source with line numbers, the pinned commit, the Git blob ID, and the SHA-256 of the original bytes. Inspect each file without opening previous model output or adjudications. The source is text for review only.
2. Copy `labels_blank.csv` in the same folder to `labels_completed.csv`. Keep the identifier and hash columns as supplied. Use one pseudonymous `reviewer_id` on all 12 rows.
3. Fill in `label`. Use `automated_test` for an implemented runnable test, executable test registration or standalone test that checks behavior and signals failure. Use `not_test` for production code, fixtures, setup, helpers, configuration, or templates with no implemented tests. Use `uncertain` whenever the source or context is insufficient.
4. Add a short rationale in `notes`. On decisive rows fill `basis_start` and `basis_end` with the narrowest line range that supports your decision. For tests, include the declaration/registration and implemented check if possible. For non-tests, choose the relevant declaration and body, or the operative configuration or helper definition. For uncertain rows the range can be blank. Save as UTF-8 CSV.
5. From the repo root, import the worksheet offline.

```powershell
& .\rq1_analysis\content_test_detection\.venv\Scripts\python.exe -B .\rq1_analysis\content_test_detection\independent_review.py --import-labels .\rq1_analysis\content_test_detection\outputs\full_cohort\final_verification_v1\independent_review_v1\labels_completed.csv --confirm-independent
```

The gate requires 12 annotations, including at least four clear tests and four clear non-tests spanning at least three language categories. At least six historical controls must have decisive reviews, with no disagreements pending adjudication. Two eligible, still-unresolved trial inputs must receive independent non-test labels with substantive declarations inside the reviewer’s supporting ranges. An uncertain case stays uncertain. Disagreements block dispatch and appear in the report. The importer seals the completed worksheet and results by hash. It reports historical control agreement and errors and unsupported citations among comparable archived model responses. It also reports how often a grammar-checked declaration falls in the reviewer’s supporting range. Inter-reviewer agreement is unavailable with one reviewer. The archived metrics concern archived prompts only.

If the import reports `offline_gate_passed: true`, the following command starts a one-shot Grok 4.3 trial from cached pinned source. Run it only after checking the offline report and setting `XAI_API_KEY` in that PowerShell session.

```powershell
& .\rq1_analysis\content_test_detection\.venv\Scripts\python.exe -B .\rq1_analysis\content_test_detection\independent_review.py --live-trial .\rq1_analysis\content_test_detection\outputs\full_cohort\final_verification_v1\independent_review_v1\labels_completed.csv
```

The trial permits at most two new attempts under the existing $7 and 1,000-attempt cumulative limits. It stops at the first provider error, invalid choice, abstention, or unsupported citation. The model sees complete source and a catalog of parsed declarations. A model choice is compared with a frozen independent label and checked against the exact pinned source and the reviewer’s cited range. The trial evaluates non-test citations for two already reviewed files. It cannot estimate sensitivity, specificity or error rates for the entire cohort. A trial receipt does not publish PR labels or unlock the ordinary paid cohort runner. The old trial’s `--status` option remains available for historical inspection.

## Cohort publication

`cohort_overlay.py` verifies and admits the 47 PRs from `final_verification_v1`. It keeps the prior rolling publication under `runner_integration/` and preserves the seven frozen selections and per-PR checkpoints. `full_cohort.py` joins the admitted labels by repository and PR number before scheduling and when it republishes results. It checks for conflicts and excludes the admitted PRs from work even when a historical per-batch checkpoint is unknown.
