# Historical RQ1 validation pilot — November 2, 2026

**Established:** pinned PR-head content is now verified for 39 of 40 selected PRs. This removes the snapshot-content assumption for that separate cohort. It does not establish which text existed at PR creation, before all implementation work, or at the time the original dataset was collected.

**Interpretation:** some snapshot feature labels change at historical head. Tool/template composition, feature definitions, availability, and very uneven pilot weights make the association estimates unstable. This pilot strengthens measurement validity; it does not support a new directional or causal testing claim.

## Baseline preservation

All 103 pre-existing substantive baseline/source-data files still match their recorded SHA-256 hashes. Original code, midpoint results, and existing reviews were not edited or rerun. A separately verified ZIP preserves 83 midpoint project files; original raw datasets were not duplicated. All extension code, content caches, reports, forms, and results are under historical_validation/.

## Sampling and retrieval

Selected 40 PRs from 3,070 closed OpenSpec/Spec Kit PRs in the frozen midpoint cohort, using hash-ranked stratified sampling with a fixed seed. There are 20 PRs per tool, 8 acceptance-positive and 12 acceptance-negative cases per tool, with edge-case and test-addition strata represented. The sample spans 26 repositories. No inaccessible PR was replaced. The sampling CSV records each stratum's frame size, sample size, probability, and inverse probability weight.

| Verification stage | Actual count |
|---|---:|
| PR metadata available | 40/40 |
| Planned active spec-file observations | 72 |
| Spec-file observations verified at pinned PR head | 70 |
| PRs with complete verified head content and unchanged net-diff path/status set | 39 |
| PRs with a validated earlier anchor | 37 |
| Spec-file observations retrieved at that earlier anchor | 23 |
| PRs with every active spec retrieved before first observed executable change | 11 |
| PRs proven to have genuinely pre-implementation text | 0 |

Head metadata is the API-recorded head at acquisition, frozen in the cache; it is not a reconstruction of a force-pushed-away head. Every content request uses a full 40-character commit SHA. Decoded bytes must match the response Git blob SHA and, for head specs, the changed-file API's expected blob SHA. Content SHA-256 and pinned URLs are recorded. Current branches and snapshot prose are never fallbacks for a failed historical read.

The complete live net-diff path/status set is compared with the frozen baseline, so the reused path-classified test outcome refers to the same changeset. Metadata availability is distinct from spec accessibility. Excluded PRs:

- P03: [carverauto/serviceradar #2048](https://github.com/carverauto/serviceradar/pull/2048) — live net diff different or unavailable;historical head spec content incomplete. The API now returns an empty net diff; its two baseline spec paths are unresolved.

All 70 successful head spec observations used exact current API paths; 0 required an API previous_filename mapping. The code supports observed renames and records removed files without inventing head content. This pilot therefore exercises normal paths, but does not empirically validate every rename/deletion scenario. Basename matching and guessed archive rewrites are prohibited.

## Feature version agreement versus rule-definition drift

The release does not ship the upstream acceptance/edge extractor. Versioned English structural rules recognize acceptance-criteria and edge-case headings (ATX, Setext, or standalone bold), ignoring fenced code and HTML comments. A heading can be an unfilled template; these rules do not certify substantive criterion quality. The midpoint testing-directive rule is reused unchanged. Rules are applied to both head and hash-checked snapshot text. This separates historical content changes from differences between our rule and supplied labels.

Of 70 pinned spec observations, 21 (30.0%) have different bytes from the snapshot; the others are byte-identical. File-level and PR-level agreement are both exported. At complete-PR level:

| Feature | Same-rule snapshot → head mismatches | Direction | Supplied snapshot → recalculated snapshot mismatches |
|---|---:|---|---:|
| Acceptance criteria | 2/39 (5.1%) | 0 gained; 2 lost | 1/39 |
| Edge cases | 2/39 (5.1%) | 0 gained; 2 lost | 1/39 |
| Testing directive | 0/39 (0.0%) | 0 gained; 0 lost | 0/39 |

Both acceptance and edge version-label losses occur in OpenSpec in this pilot. Spec Kit has no same-rule head-versus-snapshot label changes observed here. Those are pilot counts, not population mismatch estimates. Definition drift occurs separately in one Spec Kit acceptance case and one OpenSpec edge case; neither is automatically an error in the upstream label. See version_label_change_examples.csv and feature_agreement.csv for the exact cases.

## What earlier content establishes

The earlier anchor is the parent of the first commit changing a recognized executable source/test path, after checking a linear prefix of the complete PR commit list. Earlier prefix commits must contain no detected executable changes; they need not be spec-only commits. Tests and fixture code count as implementation for this timing check. PR base dates, commit messages, and PR creation dates alone are not used as evidence.

Anchor blockers:

- anchor_established: 37 PRs.
- empty_commit_history: 1 PRs.
- prefix_budget_exhausted: 1 PRs.
- nonlinear_history_prefix: 1 PRs.

The prefix scan is capped at 12 commits per PR. Merge/nonlinear prefixes, missing history, and exhausted budgets yield no precedence claim. Of 67 attempted earlier content requests, 23 verified and 44 returned 404. A 404 is recorded as not retrieved, not coded as feature absence. Earlier paths use only the actual path or an API-supplied previous filename; specs archived later in the PR can therefore remain unresolved.

The 11 complete earlier PRs include 5 OpenSpec and 6 Spec Kit PRs. Acceptance, edge-case, and testing-directive labels all agree between earlier/head text within those 11 pairs. This successful subset is selected by earlier availability and cannot establish stability for the rest. The source-extension detector can miss implementation in configuration, unsupported languages, or unobserved work; squashing, force pushes, other branches, and work before the recorded history remain possible. **Genuine temporal precedence over implementation remains unproven.**

## Reanalysis and tool/template differences

The historical head cohort contains 39 PRs and 25 repositories. Outcome- and exposure-stratified sampling makes raw pilot testing rates unsuitable as frame estimates. We report frozen inverse-probability-weighted descriptions, with a separate within-stratum response-calibrated sensitivity. The latter assumes the failed historical case is missing at random within its stratum; this assumption is not established.

Weights are highly unequal (maximum 321.3; Kish weight effective sample size approximately 12.1, before considering clustering). A high-weight feature-definition disagreement can dominate a nominally 39-PR result. We withhold logistic regression and naive chi-square/Fisher p-values.

The primary uncertainty bounds below account for the actual stratified draw. Exact hypergeometric tail inversion bounds each stratum's number of retrievable/compatible PRs in each historical exposure group. Bonferroni correction covers all 64 binary counts across both primary predictors simultaneously; conservative ratio/difference propagation gives 95% simultaneous finite-frame bounds. The failed PR belongs to neither exposure group (retrieval domain D=0); its feature is not imputed as absent. This targets the protocol-retrievable domain of the frozen two-tool frame under a fixed repository state and pseudorandom within-stratum selection. It does not cover feature/classifier errors or generalize beyond this curated frame. Only 1–3 PRs per stratum were sampled, so the bounds are appropriately very wide. Fixed-weight repository-bootstrap composition intervals are provided separately as diagnostics, not as survey-design confidence intervals.

| Tool | Head feature | Sample PRs absent / present | Weighted addition rate absent / present | Weighted difference, pp (95% design bounds) |
|---|---|---:|---:|---:|
| openspec | Acceptance criteria | 13 / 6 | 61.3% / 42.9% | -18.5 (-98.3, 91.9) |
| openspec | Edge cases | 13 / 6 | 61.2% / 72.5% | 11.3 (-97.8, 92.3) |
| speckit | Acceptance criteria | 11 / 9 | 62.4% / 14.1% | -48.4 (-96.6, 90.4) |
| speckit | Edge cases | 10 / 10 | 42.4% / 60.1% | 17.7 (-90.1, 93.3) |

All four primary tool-specific design bounds span zero. The testing-directive predictor occurs in only two head PRs (one per tool); no useful contrast inference is available. Test modifications, earlier-subset comparisons, and response-weight sensitivities are exported separately as descriptions/bootstrap diagnostics.

A useful diagnostic holds the same 39 PRs fixed while changing feature source:

| Feature source on identical PRs | Pooled acceptance difference, pp | Pooled edge difference, pp |
|---|---:|---:|
| supplied snapshot | -6.8 | 1.8 |
| snapshot same rule | -42.2 | 2.0 |
| verified head | -46.5 | 2.1 |
| verified head response calibrated sensitivity | -40.0 | 10.2 |

The large acceptance shift already appears when recalculating snapshot features, before substituting historical content. It must not be attributed entirely to historical contamination. The unavailable high-weight PR and sparse strata add instability. An apparent reversal in these weighted pilot point estimates is not evidence that acceptance criteria reduce test additions.

The full frozen two-tool frame provides separate template context (these remain snapshot labels):

| Tool | Frame PRs | Acceptance prevalence | Edge-case prevalence |
|---|---:|---:|---:|
| openspec | 1915 | 0.8% | 1.1% |
| speckit | 1155 | 4.4% | 74.5% |

Tool and template composition are therefore major plausible explanations for marginal associations. This small pilot cannot establish that templates fully explain the original findings, nor isolate an independent specification effect. The original path-classified outcome also remains unvalidated against independent human contents; adding files does not prove tests ran, passed, or improved quality.

![Historical pilot by tool](outputs/figures/historical_pilot_by_tool.png)

## Independent test-content review readiness

A separate frozen file sample contains 56 likely test/non-test paths, stratified by tool, detector prediction, and uncertainty. All 56 have verified pinned content references. Removed-file contents use an explicitly labeled PR-base commit, not an inferred pre-implementation anchor. The human CSV is blinded to detector predictions; labels, reviewer identity, provenance, and adjudication fields are blank. Existing assistant reviews were neither overwritten nor promoted to human truth.

**Precision and recall are not evaluated.** HUMAN_REVIEW_PROTOCOL.md defines the task. The evaluator refuses unproven/assistant references and requires explicit human provenance attestation and complete adjudicated labels. Independence ultimately requires a real annotation process, not just filled fields.

## Reproducibility, checks, and remaining blockers

The offline replay passed 22 extension unit tests plus cohort/blob/ancestry/blank-form invariants. It verified all 103 baseline hashes and the independent archive. Acquisition used cached, bounded GitHub connector requests (two at a time with pauses); API failures were retained. Downloaded code is never executed. Content caches are local and ignored by Git; reports omit raw prose and author/contact metadata. No full SpecMine corpus was downloaded.

Remaining blockers are the changed/empty net diff for one sampled PR, incomplete/nonlinear or budget-limited earlier history, unavailable earlier paths, feature-definition calibration, independent human annotation, and insufficient pilot size for adjusted inference. A larger historical follow-up should sample more independent repositories with adequate within-tool exposure overlap and retain a formal sampling/nonresponse analysis. Expanding to full snapshot data would not fix these issues.

See README.md for exact replay/acquisition commands and output dictionaries. The November 5 baseline is preserved unchanged.

Sources: [GitHub contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content), [PR files/commits API](https://docs.github.com/en/rest/pulls/pulls), [SpecMine sample](https://github.com/shyamagarwal13/specmine-official).
