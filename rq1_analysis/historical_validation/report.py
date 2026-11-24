"""Generate pilot findings from executed records, with separate uncertainty claims."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pandas as pd

from hv_common import FEATURES, HERE, OUT


def report():
    build=json.loads((OUT / "historical_build_summary.json").read_text())
    checks=json.loads((OUT / "validation_results.json").read_text())
    limits=json.loads((OUT / "statistical_limits.json").read_text())
    sampling=json.loads((OUT / "sampling_protocol.json").read_text())
    p=pd.read_csv(OUT / "pilot_observations.csv")
    f=pd.read_csv(OUT / "historical_spec_files.csv")
    agreement=pd.read_csv(OUT / "tables/feature_agreement.csv")
    identity=pd.read_csv(OUT / "tables/content_identity.csv")
    rates=pd.read_csv(OUT / "tables/testing_rates_by_version_and_tool.csv")
    effects=pd.read_csv(OUT / "tables/weighted_pilot_contrasts.csv")
    design=pd.read_csv(OUT / "tables/exact_design_rate_bounds.csv")
    earlier=pd.read_csv(OUT / "tables/earlier_vs_head_features.csv")
    context=pd.read_csv(OUT / "tables/frozen_frame_template_context.csv")
    anchors=json.loads((OUT / "anchor_audit.json").read_text())
    tests=ET.parse(OUT / "unit_tests.xml").getroot()
    n_tests=sum(int(x.attrib.get("tests",0)) for x in tests.iter("testsuite"))
    labels={"has_acceptance_criteria":"Acceptance criteria","has_edge_cases":"Edge cases","has_testing_requirement":"Testing directive"}
    contents_changed=int(identity.n_verified_specs.sum()-identity.identical_bytes.sum())
    lines=["# Historical RQ1 validation pilot — November 2, 2026", "",
        "**Established:** pinned PR-head content is now verified for 39 of 40 selected PRs. This removes the snapshot-content assumption for that separate cohort. It does not establish which text existed at PR creation, before all implementation work, or at the time the original dataset was collected.", "",
        "**Interpretation:** some snapshot feature labels change at historical head. Tool/template composition, feature definitions, availability, and very uneven pilot weights make the association estimates unstable. This pilot strengthens measurement validity; it does not support a new directional or causal testing claim.", "",
        "## Baseline preservation", "",
        f"All {checks['baseline_files_unchanged']} pre-existing substantive baseline/source-data files still match their recorded SHA-256 hashes. Original code, midpoint results, and existing reviews were not edited or rerun. A separately verified ZIP preserves {checks['archive']['files']} midpoint project files; original raw datasets were not duplicated. All extension code, content caches, reports, forms, and results are under historical_validation/.", "",
        "## Sampling and retrieval", "",
        f"Selected {sampling['pilot_n']} PRs from {sampling['frame_n']:,} closed OpenSpec/Spec Kit PRs in the frozen midpoint cohort, using hash-ranked stratified sampling with a fixed seed. There are 20 PRs per tool, 8 acceptance-positive and 12 acceptance-negative cases per tool, with edge-case and test-addition strata represented. The sample spans {sampling['pilot_repositories']} repositories. No inaccessible PR was replaced. The sampling CSV records each stratum's frame size, sample size, probability, and inverse probability weight.", "",
        "| Verification stage | Actual count |", "|---|---:|",
        f"| PR metadata available | {int(p.metadata_available.sum())}/{len(p)} |",
        f"| Planned active spec-file observations | {build['planned_active_spec_observations']} |",
        f"| Spec-file observations verified at pinned PR head | {build['verified_head_spec_observations']} |",
        f"| PRs with complete verified head content and unchanged net-diff path/status set | {build['historical_head_analysis_prs']} |",
        f"| PRs with a validated earlier anchor | {build['anchors_established']} |",
        f"| Spec-file observations retrieved at that earlier anchor | {build['verified_earlier_spec_observations']} |",
        f"| PRs with every active spec retrieved before first observed executable change | {build['complete_earlier_prs']} |",
        "| PRs proven to have genuinely pre-implementation text | 0 |", "",
        "Head metadata is the API-recorded head at acquisition, frozen in the cache; it is not a reconstruction of a force-pushed-away head. Every content request uses a full 40-character commit SHA. Decoded bytes must match the response Git blob SHA and, for head specs, the changed-file API's expected blob SHA. Content SHA-256 and pinned URLs are recorded. Current branches and snapshot prose are never fallbacks for a failed historical read.", "",
        "The complete live net-diff path/status set is compared with the frozen baseline, so the reused path-classified test outcome refers to the same changeset. Metadata availability is distinct from spec accessibility. Excluded PRs:", ""]
    for r in p[~p.in_historical_head_cohort].itertuples():
        lines.append(f"- {r.pilot_id}: [{r.repo_name} #{r.pr_number}](https://github.com/{r.repo_name}/pull/{r.pr_number}) — {r.historical_exclusion_reasons.replace('_',' ')}. The API now returns an empty net diff; its two baseline spec paths are unresolved.")
    renamed=f[f.resolution_status.eq("api_previous_filename")]
    lines += ["",f"All {build['verified_head_spec_observations']} successful head spec observations used exact current API paths; {len(renamed)} required an API previous_filename mapping. The code supports observed renames and records removed files without inventing head content. This pilot therefore exercises normal paths, but does not empirically validate every rename/deletion scenario. Basename matching and guessed archive rewrites are prohibited.", "",
        "## Feature version agreement versus rule-definition drift", "",
        "The release does not ship the upstream acceptance/edge extractor. Versioned English structural rules recognize acceptance-criteria and edge-case headings (ATX, Setext, or standalone bold), ignoring fenced code and HTML comments. A heading can be an unfilled template; these rules do not certify substantive criterion quality. The midpoint testing-directive rule is reused unchanged. Rules are applied to both head and hash-checked snapshot text. This separates historical content changes from differences between our rule and supplied labels.", "",
        f"Of {build['verified_head_spec_observations']} pinned spec observations, {contents_changed} ({contents_changed/build['verified_head_spec_observations']:.1%}) have different bytes from the snapshot; the others are byte-identical. File-level and PR-level agreement are both exported. At complete-PR level:", "",
        "| Feature | Same-rule snapshot → head mismatches | Direction | Supplied snapshot → recalculated snapshot mismatches |", "|---|---:|---|---:|"]
    for feature,label in labels.items():
        a=agreement[(agreement.level=="PR_complete_head") & agreement.tool.eq("all") & agreement.comparison.eq("version_change_same_rule") & agreement.feature.eq(feature)].iloc[0]
        b=agreement[(agreement.level=="PR_complete_head") & agreement.tool.eq("all") & agreement.comparison.eq("snapshot_definition_drift") & agreement.feature.eq(feature)].iloc[0]
        lines.append(f"| {label} | {a.mismatches}/{a.paired_n} ({a.mismatch_rate:.1%}) | {a.absent_to_present} gained; {a.present_to_absent} lost | {b.mismatches}/{b.paired_n} |")
    lines += ["", "Both acceptance and edge version-label losses occur in OpenSpec in this pilot. Spec Kit has no same-rule head-versus-snapshot label changes observed here. Those are pilot counts, not population mismatch estimates. Definition drift occurs separately in one Spec Kit acceptance case and one OpenSpec edge case; neither is automatically an error in the upstream label. See version_label_change_examples.csv and feature_agreement.csv for the exact cases.", "",
        "## What earlier content establishes", "",
        "The earlier anchor is the parent of the first commit changing a recognized executable source/test path, after checking a linear prefix of the complete PR commit list. Earlier prefix commits must contain no detected executable changes; they need not be spec-only commits. Tests and fixture code count as implementation for this timing check. PR base dates, commit messages, and PR creation dates alone are not used as evidence.", "",
        "Anchor blockers:", ""]
    for status,count in p.earlier_anchor_status.value_counts().items():lines.append(f"- {status}: {count} PRs.")
    lines += ["", "The prefix scan is capped at 12 commits per PR. Merge/nonlinear prefixes, missing history, and exhausted budgets yield no precedence claim. Of 67 attempted earlier content requests, 23 verified and 44 returned 404. A 404 is recorded as not retrieved, not coded as feature absence. Earlier paths use only the actual path or an API-supplied previous filename; specs archived later in the PR can therefore remain unresolved.", "",
        "The 11 complete earlier PRs include 5 OpenSpec and 6 Spec Kit PRs. Acceptance, edge-case, and testing-directive labels all agree between earlier/head text within those 11 pairs. This successful subset is selected by earlier availability and cannot establish stability for the rest. The source-extension detector can miss implementation in configuration, unsupported languages, or unobserved work; squashing, force pushes, other branches, and work before the recorded history remain possible. **Genuine temporal precedence over implementation remains unproven.**", "",
        "## Reanalysis and tool/template differences", "",
        f"The historical head cohort contains {len(p[p.in_historical_head_cohort])} PRs and {limits['repository_clusters']} repositories. Outcome- and exposure-stratified sampling makes raw pilot testing rates unsuitable as frame estimates. We report frozen inverse-probability-weighted descriptions, with a separate within-stratum response-calibrated sensitivity. The latter assumes the failed historical case is missing at random within its stratum; this assumption is not established.", "",
        f"Weights are highly unequal (maximum {limits['max_design_weight']:.1f}; Kish weight effective sample size approximately {limits['kish_weight_effective_n']:.1f}, before considering clustering). A high-weight feature-definition disagreement can dominate a nominally 39-PR result. We withhold logistic regression and naive chi-square/Fisher p-values.", "",
        "The primary uncertainty bounds below account for the actual stratified draw. Exact hypergeometric tail inversion bounds each stratum's number of retrievable/compatible PRs in each historical exposure group. Bonferroni correction covers all 64 binary counts across both primary predictors simultaneously; conservative ratio/difference propagation gives 95% simultaneous finite-frame bounds. The failed PR belongs to neither exposure group (retrieval domain D=0); its feature is not imputed as absent. This targets the protocol-retrievable domain of the frozen two-tool frame under a fixed repository state and pseudorandom within-stratum selection. It does not cover feature/classifier errors or generalize beyond this curated frame. Only 1–3 PRs per stratum were sampled, so the bounds are appropriately very wide. Fixed-weight repository-bootstrap composition intervals are provided separately as diagnostics, not as survey-design confidence intervals.", "",
        "| Tool | Head feature | Sample PRs absent / present | Weighted addition rate absent / present | Weighted difference, pp (95% design bounds) |", "|---|---|---:|---:|---:|"]
    for tool in ["openspec","speckit"]:
        for feature in FEATURES[:2]:
            r=rates[(rates.version=="verified_head") & rates.tool.eq(tool) & rates.feature.eq(feature) & rates.outcome.eq("test_added")].set_index("feature_present")
            c=effects[(effects.version=="verified_head") & effects.tool.eq(tool) & effects.feature.eq(feature) & effects.outcome.eq("test_added")].iloc[0]
            bound=design[design.tool.eq(tool)&design.feature.eq(feature)].iloc[0]
            lines.append(f"| {tool} | {labels[feature]} | {int(r.loc[0,'n_prs'])} / {int(r.loc[1,'n_prs'])} | {r.loc[0,'weighted_descriptive_rate']:.1%} / {r.loc[1,'weighted_descriptive_rate']:.1%} | {c.weighted_rate_difference*100:.1f} ({bound.difference_low*100:.1f}, {bound.difference_high*100:.1f}) |")
    lines += ["", "All four primary tool-specific design bounds span zero. The testing-directive predictor occurs in only two head PRs (one per tool); no useful contrast inference is available. Test modifications, earlier-subset comparisons, and response-weight sensitivities are exported separately as descriptions/bootstrap diagnostics.", "",
        "A useful diagnostic holds the same 39 PRs fixed while changing feature source:", "",
        "| Feature source on identical PRs | Pooled acceptance difference, pp | Pooled edge difference, pp |", "|---|---:|---:|"]
    for version in ["supplied_snapshot","snapshot_same_rule","verified_head","verified_head_response_calibrated_sensitivity"]:
        values=[]
        for feature in FEATURES[:2]:
            r=effects[(effects.version==version)&effects.tool.eq("all")&effects.feature.eq(feature)&effects.outcome.eq("test_added")].iloc[0]
            values.append(f"{r.weighted_rate_difference*100:.1f}")
        lines.append(f"| {version.replace('_',' ')} | "+" | ".join(values)+" |")
    lines += ["", "The large acceptance shift already appears when recalculating snapshot features, before substituting historical content. It must not be attributed entirely to historical contamination. The unavailable high-weight PR and sparse strata add instability. An apparent reversal in these weighted pilot point estimates is not evidence that acceptance criteria reduce test additions.", "",
        "The full frozen two-tool frame provides separate template context (these remain snapshot labels):", "",
        "| Tool | Frame PRs | Acceptance prevalence | Edge-case prevalence |", "|---|---:|---:|---:|"]
    for tool in ["openspec","speckit"]:
        vals=[]
        for feature in FEATURES[:2]:
            sub=context[context.tool.eq(tool)&context.feature.eq(feature)]
            total=sub.n_baseline_prs.sum()
            vals.append(sub.loc[sub.feature_present.eq(1),"n_baseline_prs"].iloc[0]/total)
        lines.append(f"| {tool} | {int(total)} | {vals[0]:.1%} | {vals[1]:.1%} |")
    lines += ["", "Tool and template composition are therefore major plausible explanations for marginal associations. This small pilot cannot establish that templates fully explain the original findings, nor isolate an independent specification effect. The original path-classified outcome also remains unvalidated against independent human contents; adding files does not prove tests ran, passed, or improved quality.", "",
        "![Historical pilot by tool](outputs/figures/historical_pilot_by_tool.png)", "",
        "## Independent test-content review readiness", "",
        f"A separate frozen file sample contains {checks['human_form_candidates']} likely test/non-test paths, stratified by tool, detector prediction, and uncertainty. All {checks['human_form_verified_contents']} have verified pinned content references. Removed-file contents use an explicitly labeled PR-base commit, not an inferred pre-implementation anchor. The human CSV is blinded to detector predictions; labels, reviewer identity, provenance, and adjudication fields are blank. Existing assistant reviews were neither overwritten nor promoted to human truth.", "",
        "**Precision and recall are not evaluated.** HUMAN_REVIEW_PROTOCOL.md defines the task. The evaluator refuses unproven/assistant references and requires explicit human provenance attestation and complete adjudicated labels. Independence ultimately requires a real annotation process, not just filled fields.", "",
        "## Reproducibility, checks, and remaining blockers", "",
        f"The offline replay passed {n_tests} extension unit tests plus cohort/blob/ancestry/blank-form invariants. It verified all {checks['baseline_files_unchanged']} baseline hashes and the independent archive. Acquisition used cached, bounded GitHub connector requests (two at a time with pauses); API failures were retained. Downloaded code is never executed. Content caches are local and ignored by Git; reports omit raw prose and author/contact metadata. No full SpecMine corpus was downloaded.", "",
        "Remaining blockers are the changed/empty net diff for one sampled PR, incomplete/nonlinear or budget-limited earlier history, unavailable earlier paths, feature-definition calibration, independent human annotation, and insufficient pilot size for adjusted inference. A larger historical follow-up should sample more independent repositories with adequate within-tool exposure overlap and retain a formal sampling/nonresponse analysis. Expanding to full snapshot data would not fix these issues.", "",
        "See README.md for exact replay/acquisition commands and output dictionaries. The November 5 baseline is preserved unchanged.", "",
        "Sources: [GitHub contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content), [PR files/commits API](https://docs.github.com/en/rest/pulls/pulls), [SpecMine sample](https://github.com/shyamagarwal13/specmine-official).", ""]
    (HERE / "PILOT_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    brief=["# Historical validation pilot: concise findings", "", "Executed November 2, 2026. Original November 5 midpoint baseline preserved unchanged.", "",
        f"- Frozen sample: 40 PRs, 20 per tool (OpenSpec/Spec Kit), with 16 acceptance-positive cases and both edge/outcome classes represented.",
        f"- Verified **{build['verified_head_spec_observations']} pinned head spec-file observations across {build['historical_head_analysis_prs']} complete PRs**. One PR now has an empty net diff; no snapshot fallback or replacement was used.",
        f"- {contents_changed}/70 spec observations differ in bytes from their snapshots. With the same new rules applied to both versions, acceptance labels change in 2/39 PRs and edge labels in 2/39; testing-directive labels change in 0/39. Definition drift is separately identified in one snapshot acceptance label and one edge label.",
        f"- Earlier pinned content is complete for **{build['complete_earlier_prs']} PRs** before the first observed executable-code change in a verified history prefix. These are 5 OpenSpec and 6 Spec Kit PRs. Their measured labels agree with head labels. **Genuine precedence over all implementation work remains unproven.**",
        f"- Prepared **{checks['human_form_candidates']} pinned content-review cases**, all with content hashes and blank human labels. Precision/recall remain unavailable pending independent annotations.",
        "- Reanalysis reports exposure counts and separate tool results. Conservative simultaneous 95% finite-frame design bounds all span zero and are very wide. Unequal weights, a high-weight feature-definition disagreement, and one unresolved PR make the point estimates unstable; naive tests and regression are withheld. This pilot does not establish a positive or negative specification effect or show that templates fully explain the original association.",
        f"- {n_tests} extension tests and evidence/integrity checks pass; all {checks['baseline_files_unchanged']} baseline files remain hash-identical. No full-corpus download.", "",
        "[Detailed report](PILOT_REPORT.md) · [Reproduce](README.md) · [Blank human-review CSV](outputs/human_review.csv) · [Historical cohort](outputs/historical_head_analysis_cohort.csv)", ""]
    (HERE / "PILOT_SUMMARY.md").write_text("\n".join(brief),encoding="utf-8")
    print("Generated PILOT_REPORT.md and PILOT_SUMMARY.md")


if __name__=="__main__":report()
