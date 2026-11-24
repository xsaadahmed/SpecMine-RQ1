# Offline RQ1 evaluation for the progress presentation

All analysis is separate from prior outputs. No GitHub requests, Grok calls, scaling, package downloads or old pipeline reruns occurred. Six evaluation checks passed. Input hashes in outputs/validation.json confirm the original outcome table, snapshot dataset and sampled selections were unchanged during analysis. frozen_content_outcomes.csv preserves the exact 3,186-row outcome snapshot used.

Start with RESULTS_TABLE.md, SLIDES.md and SPEAKER_NOTES.md. outputs/rates.png/PDF provides an optional figure, not an additional required slide.

## Join and outcome validation

Join key is exact repo_name + integer PR number, with duplicate identities rejected on both sides. Both inputs have 3,186 rows; all 3,186 match one-to-one, with zero unmatched rows and no missing acceptance/edge/directive values. Unknown outcomes remain null. The estimation subset has 1,864 resolved PRs from 192 repositories: 1,023 positive and 841 negative. All negative rows have complete-inspection flags and every resolved row has a pinned commit recorded. This is an audit of saved provenance flags, not a fresh source reclassification or independent detector validation.

Exposure features are inherited from the frozen snapshot dataset. Acceptance and edge cases are supplied SpecMine labels. Testing directives use the existing secondary English prose-line rule requiring a directive plus a testing phrase, ignoring fenced code, HTML comments and explicit negations. At PR level any active exact-matched specification can supply a binary feature; word counts sum distinct active files. Complete specification coverage was required by the original cohort builder. We did not reinterpret or relabel specifications here.

## Results and measurement comparison

The concise table lists all present/absent positive and negative counts, rates, percentage-point differences and exploratory adjusted ORs. Repository bootstrap intervals use 3,000 resamples with replacement of whole repository clusters, seed 520. They preserve within-repository PR dependence but condition on the observed verified subset. They do not reflect uncertainty about unknown outcomes or eliminate verification selection.

Original full-cohort filename results:

- Acceptance: 62.3% present vs 53.3% absent, +9.0 pp.
- Edge cases: 60.2% vs 51.1%, +9.1 pp.
- Testing directive: 65.0% vs 52.3%, +12.7 pp.

Content results use only resolved outcomes and therefore are not directly paired with those full-cohort percentages. For a fair measurement comparison, original filename results on the SAME 1,864 resolved PRs are:

- Acceptance: 58.7% vs 53.4%, approximately +5.3 pp; content: 66.3% vs 54.3%, +12.0 pp.
- Edge cases: 58.9% vs 51.9%, approximately +7.0 pp; content: 58.5% vs 53.6%, +4.8 pp.
- Testing directive: 63.7% vs 52.6%, approximately +11.1 pp; content: 65.3% vs 53.7%, +11.6 pp.

There are 44 disagreements among 1,864 paired outcomes (2.36%): 33 filename negatives become content positives, 11 filename positives become content negatives. Net positive-count change is +22. These are detector disagreements, not independently measured error rates. The full disagreement ledger is outputs/changed_labels.csv.

## Exploratory adjusted analysis

The selected-sample comparison is estimable: 1,864 observations, 192 repository clusters, 14 parameters, full-rank design, converged binomial-logit fits, finite clustered SEs and condition number 136.8. Python statsmodels 0.15.0 was already installed in rq1_analysis/.venv and used without installing anything. Primary model:

content outcome ~ acceptance + edge cases + requirements + log(1 + spec words) + log(1 + stars) + grouped tool + grouped repository language.

Tool levels with <30 resolved PRs and languages with <50 are pooled into Other. No missing-control exclusions were necessary. Cluster-sandwich covariance uses repository clusters with finite-sample correction and normal-reference 95% intervals. Primary content ORs: acceptance 1.68 [0.94, 2.98]; edge cases 1.29 [0.82, 2.04]. Both include one. These models are conditional exploratory descriptions; they are not a representative-population adjusted effect or a causal estimate. Cluster covariance does not control unmeasured repository confounding as fixed effects would.

The same primary formula/sample with filename outcomes gives acceptance OR 1.32 [0.69, 2.53], edge OR 1.91 [1.06, 3.44]. Comparing this with original whole-cohort models additionally mixes sample/control changes; the original reported ORs around 1.55 and 1.57 are retained historical results, not rerun estimates.

Adding the secondary testing directive gives directive OR 1.41 [1.02, 1.95], nominal p=0.036. A Holm correction across all three feature terms in that secondary model gives p=0.108 for the directive. It must not be presented as a confirmed significant effect. outputs/secondary_multiplicity.csv records all adjusted values.

Adding log changed-source-file count as a sensitivity gives acceptance OR 1.76 [0.94, 3.30] and edge OR 0.94 [0.60, 1.48]. That control is itself measured during implementation and can be related to adding tests; it is a sensitivity, not a causal adjustment. The edge result's model dependence reinforces uncertainty. No model can correct post-PR snapshot timing or the absent outcomes just by having a larger N.

## Selection and incomplete verification

Four fixed scaling draws assign 2,000 unique PRs. Of these, 1,709 are resolved and 291 unknown. Outside those draws, 155 are resolved from earlier work and 1,031 remain unknown. The early work mixes pilot/validation selection mechanisms, including original-outcome stratification. Scaling assignment is stratified and reproducible, but completion is resource- and outcome-dependent. Inclusion fractions in outputs/selection_assignments.csv refer to assignment within successive conditional frames, not probability of source verification. We applied NO inverse-probability weights, since no defensible verification probability or missing-at-random assumption is established. An unweighted selected-subset model is explicitly labeled as such.

Verification differs materially:

- Acceptance present 75.4% resolved; absent 57.8%.
- Edge present 55.1%; absent 59.8%.
- Directive present 58.8%; absent 58.5%.
- OpenSpec 59.2%; Spec Kit 56.9%.
- Rust 64.5%; TypeScript 61.8%; C++ 32.8%; Swift 19.0%.
- Repository coverage ranges 0–100%; 192/215 repositories contribute resolved PRs.
- Median changed-source files: resolved 6 vs unresolved 7; median spec words 1,750 vs 1,866. Median stars is 118 in both groups. Similar medians do not establish exchangeability.

Tool-specific acceptance rates also disagree in direction: OpenSpec 13/15 (86.7%) with acceptance vs 591/1,118 (52.9%) without; Spec Kit 21/41 (51.2%) vs 345/616 (56.0%). These small exposed groups and template differences cannot be explained away by a pooled positive association. Edge exposure is scarce in OpenSpec (22 resolved positives for the feature) and common in Spec Kit (464), limiting covariate overlap. outputs/within_tool_rates.csv contains denominators.

Without assumptions about unknown outcomes, full-cohort risk-difference bounds permit either direction: acceptance -23.6 to +43.2 pp; edge -40.0 to +45.0 pp; directive -34.5 to +48.2 pp. These are worst-case identification bounds, not confidence intervals. Therefore a full-cohort directional claim is not identified by the observed outcomes alone.

## Three limitations to acknowledge

1. **Incomplete, selective verification:** 41.5% unknown, with differences by feature, language, repository and execution order. Easy positives finish sooner than exhaustive negatives.
2. **Temporal uncertainty:** main predictors remain snapshots; 39 pilot PR-head checks do not prove pre-implementation content. Historical-head sensitivity stays separate (38 of 39 have resolved outcomes).
3. **Measurement and template confounding:** source-grounded automation still needs independent reference annotations; tool templates correlate with exposure; English testing directives are secondary. Test-file presence does not prove execution, passing tests or improved quality.

## Do not present as conclusive

Do not claim significance for either primary feature, that the secondary nominal finding is confirmatory, that full-cohort effects are established, that unknowns are negative, that the resolved subset is representative, that Grok is human ground truth, that main features are historically verified, that AI agents wrote the code, or that specifications cause tests/quality improvements. An interval including the null is uncertainty, not proof of no association.

## Reproduction

From repository root, offline:

```powershell
rq1_analysis/.venv/Scripts/python -B rq1_analysis/presentation_evaluation_2026_11_17/evaluate.py
rq1_analysis/.venv/Scripts/python -B rq1_analysis/presentation_evaluation_2026_11_17/make_table.py
rq1_analysis/.venv/Scripts/python -B -m pytest rq1_analysis/presentation_evaluation_2026_11_17/test_evaluation.py -q -o cache_dir=rq1_analysis/presentation_evaluation_2026_11_17/.pytest_cache
```

The first command intentionally refreshes only THIS new evaluation snapshot/outputs from the latest saved cohort. For the exact presentation snapshot, retain frozen_content_outcomes.csv and the recorded input hashes. Original midpoint and historical analyses are not rerun or overwritten.
