# Final RQ1 results

The content-verified cohort confirms the stated counts. The one-to-one join by repository and PR number matched all 3,186 PRs from 215 repositories, with zero duplicates and zero unmatched identifiers. All three specification features and all model covariates were observed. The analysis used all 3,114 verified outcomes from 209 repositories (1,723 positive and 1,391 exhaustive negative). The other 72 outcomes remain missing (2.26%). Of these, 21 have a changed cached diff, 11 lack usable pinned PR metadata, and 40 lack conclusive file-level evidence.

## Main associations

Rates are among verified PRs. Intervals are pointwise 95% intervals. Rate differences use 5,000 repository-bootstrap draws. Odds ratios and two-sided Wald p-values use repository-clustered binomial-logit inference.

| Snapshot feature | Present | Absent | Difference in pp (95% CI) | Unadjusted OR (95% CI), p | Adjusted OR (95% CI), p |
|---|---:|---:|---:|---:|---:|
| Acceptance criteria | 83/120 (69.2%) | 1,640/2,994 (54.8%) | +14.4 (0.4, 25.3) | 1.85 (1.07–3.21), .028 | 1.43 (0.76–2.69), .266 |
| Edge cases | 539/870 (62.0%) | 1,184/2,244 (52.8%) | +9.2 (0.8, 17.9) | 1.46 (1.02–2.09), .040 | 1.47 (0.99–2.19), .055 |
| Explicit testing directives, secondary | 215/316 (68.0%) | 1,508/2,798 (53.9%) | +14.1 (5.2, 23.9) | 1.82 (1.17–2.85), .009 | 1.62 (1.03–2.56), .038 |

Neither primary adjusted association passes Holm correction across acceptance criteria and edge cases (p = .266 and .111). The testing-directive result is nominal evidence in the secondary model (p = .038). With all three adjusted tests in one Holm family, its p-value is .114. The unadjusted directive association survives that same three-feature correction for the unadjusted models (p = .026). The primary unadjusted Holm p-values are both .056. The bootstrap rate-difference intervals are descriptive and have no multiplicity correction.

## Earlier outcomes and robustness

- Content inspection changed 71 of 3,114 filename labels (2.3%). It recovered 56 positives from filename negatives and found 15 exhaustive negatives among filename positives. All 1,864 verified outcomes used in the presentation analysis agree with the final labels.
- Raw gaps for acceptance criteria, edge cases, and testing directives were +9.0, +9.1, and +12.7 points in the full filename cohort, +12.0, +4.8, and +11.6 in the earlier verified cohort, and +14.4, +9.2, and +14.1 in the final verified cohort. Using the same 3,114 PRs and the same controls, the edge-case adjusted OR fell from 2.02 with filename labels to 1.47 with content labels. Adjusted ORs in the smaller verified cohort were 1.68, 1.29, and 1.41. See [method and cohort comparisons](outputs/definition_and_cohort_comparison.csv) and [model results](outputs/model_results.csv).
- Assigning all 72 unknowns in the most unfavorable or favorable way for each raw gap gives ranges of **+12.2 to +16.1 pp** for acceptance criteria, **+6.7 to +11.3 pp** for edge cases, and **+11.6 to +16.1 pp** for directives. These are assignment bounds, not confidence intervals. The adverse directive assignment gives adjusted OR 1.44 (95% CI 0.95–2.19). The unfavorable and favorable assignments optimize the raw gap, and their fitted ORs are scenarios rather than sharp bounds for adjusted effects.
- Verification varied little by feature. Present versus absent rates were 98.36% vs 97.72% for acceptance criteria, 97.64% vs 97.78% for edge cases, and 97.83% vs 97.73% for directives. Clustered verification-model p-values were .717, .923, and .934. Coverage differed by repository, with no verified outcomes in six of 215 repositories. It was 97.49% for OpenSpec and 98.10% for Spec Kit, and 98.48% for original filename positives versus 96.89% for filename negatives.
- Dropping any one repository left each raw gap positive. The ranges were +12.0 to +17.4, +7.3 to +11.0, and +12.3 to +18.5 pp respectively. Removing the largest repository (207 verified PRs) gave adjusted ORs of 1.42, 1.45, and 2.05. Adding PR source-file count gave ORs of 1.85, 1.16, and 1.71. The edge-case result is especially sensitive to this control. Acceptance-criteria raw contrasts differed between OpenSpec (+35.7 pp, 16 exposed PRs) and Spec Kit (−6.4 pp, 51 exposed PRs). These are descriptive strata with sparse cells.

## Specification timing

The historical pilot provides 39 pinned PR heads and 11 complete earlier anchors. All 39 and all 11 now have verified test outcomes. With the same extraction rules on snapshots and head contents, two acceptance labels and two edge-case labels changed among the 39 PRs. Testing directives did not change. Earlier-anchor labels match the head labels in the 11 complete pairs. The pilot was stratified on tool, features, and the original outcome. Its rejoined raw rates describe those selected cases, and the original design-based results were very imprecise. No case establishes that the measured text genuinely preceded implementation.

## Strongest defensible answer

Added automated tests were more common for PRs whose matched specification snapshots contained each of the three features. The raw direction persists under every possible assignment of the 72 unknown outcomes. After adjustment and correction for multiple comparisons, the primary associations are inconclusive, and testing directives provide exploratory evidence that is sensitive to missing-outcome assumptions. The results describe associations with snapshot features in the curated cohort.
