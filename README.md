# SpecMine RQ1

CS 520 research project at UMass Amherst. We study whether acceptance criteria, edge cases, and explicit testing directives in specification snapshots are associated with automated test additions in implementation pull requests.

The curated study includes 3,186 pull requests. Source verification established 3,114 outcomes, with 72 unknown. The adjusted primary associations are inconclusive. Testing directives show exploratory evidence of a positive association.

- [Final results](rq1_analysis/final_analysis_v1/RESULTS.md)
- [Limitations](rq1_analysis/final_analysis_v1/LIMITATIONS.md)
- [Final tables and figures](rq1_analysis/final_analysis_v1/outputs/)
- [Public analysis cohort](rq1_analysis/final_analysis_v1/outputs/public_analysis_cohort.csv)
- [Analysis and reproduction notes](rq1_analysis/final_analysis_v1/README.md)
- [Midpoint analysis](rq1_analysis/README.md)
- [Historical pilot](rq1_analysis/historical_validation/PILOT_REPORT.md)

The public cohort retains every PR, feature, covariate, and outcome. It omits two internal evidence fields. The release includes project scripts and selected derived results. Some full-pipeline scripts and tests require the original local acquisition artifacts. Obtain the dataset from the [official SpecMine repository](https://github.com/shyamagarwal13/specmine-official) and follow its source license guidance. The official dataset, caches, raw source and specification text, source viewers, and API logs are excluded from this release.
