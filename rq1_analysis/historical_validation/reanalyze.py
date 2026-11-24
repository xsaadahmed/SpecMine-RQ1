"""Paired version checks and cautious weighted pilot descriptions, without regression."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from hv_common import BASELINE, FEATURES, OUT, write_json

STRATA=["tool","supplied_snapshot_has_acceptance_criteria","supplied_snapshot_has_edge_cases","test_added"]
LABELS={"has_acceptance_criteria":"Acceptance criteria","has_edge_cases":"Edge cases","has_testing_requirement":"Testing directive"}


def weighted_contrast(d, column, outcome, weight="design_weight", repetitions=5000):
    """Fixed-IPW descriptive contrast with approximate repository composition intervals.

    This bootstrap does not reproduce quota sampling; intervals are NOT survey-
    design confidence intervals or a basis for population significance claims.
    """
    d=d[d[column].notna()].copy()
    for flag in [0,1]:
        d[f"n{flag}"]=d[weight]*d[column].eq(flag)
        d[f"y{flag}"]=d[f"n{flag}"]*d[outcome]
    totals=d.groupby("repo_name")[["n0","y0","n1","y1"]].sum().to_numpy(float)
    summed=totals.sum(axis=0)
    rates=[summed[1]/summed[0] if summed[0] else np.nan,summed[3]/summed[2] if summed[2] else np.nan]
    intervals=[(np.nan,np.nan),(np.nan,np.nan)]
    diff_ci=(np.nan,np.nan)
    group_repos=[d.loc[d[column].eq(flag),"repo_name"].nunique() for flag in [0,1]]
    valid=0
    if len(totals)>=5:
        rng=np.random.default_rng(20261102)
        draws=totals[rng.integers(0,len(totals),size=(repetitions,len(totals)))].sum(axis=1)
        rr=[]
        for i,flag in enumerate([0,1]):
            with np.errstate(divide="ignore",invalid="ignore"):
                values=draws[:,2*i+1]/draws[:,2*i]
            rr.append(values)
            good=values[np.isfinite(values)]
            if len(good)>=.95*repetitions and group_repos[flag]>=3:
                intervals[flag]=tuple(np.quantile(good,[.025,.975]))
        differences=rr[1]-rr[0]
        good=differences[np.isfinite(differences)]
        valid=len(good)
        if len(good)>=.95*repetitions and min(group_repos)>=3:
            diff_ci=tuple(np.quantile(good,[.025,.975]))
    return rates,intervals,rates[1]-rates[0],diff_ci,group_repos,valid


def agreement_tables(d,files):
    rows=[]
    head=d[d.in_historical_head_cohort].copy()
    files=files[files.retrieval_status.eq("verified")].merge(d[["pilot_id","tool"]],on="pilot_id",validate="many_to_one")
    for level,frame in [("file_observation",files),("PR_complete_head",head)]:
        for tool in ["all","openspec","speckit"]:
            sub=frame if tool=="all" else frame[frame.tool.eq(tool)]
            historical="head_" if level=="file_observation" else "historical_head_"
            for feature in FEATURES:
                for comparison,a,b in [("version_change_same_rule","same_rule_snapshot_"+feature,historical+feature),("snapshot_definition_drift","supplied_snapshot_"+feature,"same_rule_snapshot_"+feature)]:
                    pairs=sub[[a,b]].dropna()
                    mismatch=pairs[a].ne(pairs[b])
                    rows.append({"level":level,"tool":tool,"comparison":comparison,"feature":feature,"paired_n":len(pairs),"agreements":int((~mismatch).sum()),"mismatches":int(mismatch.sum()),"mismatch_rate":float(mismatch.mean()) if len(pairs) else np.nan,"absent_to_present":int((pairs[a].eq(0)&pairs[b].eq(1)).sum()),"present_to_absent":int((pairs[a].eq(1)&pairs[b].eq(0)).sum())})
    table=pd.DataFrame(rows)
    table.to_csv(OUT / "tables/feature_agreement.csv",index=False)
    changed=files[files[["version_label_mismatch_"+f for f in FEATURES]].eq(True).any(axis=1)]
    changed[["pilot_id","repo_name","pr_number","baseline_path","resolved_path","head_sha","blob_sha","content_reference"]+["same_rule_snapshot_"+f for f in FEATURES]+["head_"+f for f in FEATURES]].to_csv(OUT / "tables/version_label_change_examples.csv",index=False)
    files.groupby("tool").agg(n_verified_specs=("baseline_path","size"),identical_bytes=("content_identical_to_snapshot","sum")).reset_index().to_csv(OUT / "tables/content_identity.csv",index=False)
    return table


def reanalyze():
    d=pd.read_csv(OUT / "pilot_observations.csv")
    files=pd.read_csv(OUT / "historical_spec_files.csv")
    agreement=agreement_tables(d,files)
    head=d[d.in_historical_head_cohort].copy()
    # Preserve original design weights; show response recalibration only as a
    # named sensitivity requiring an untestable within-stratum MAR assumption.
    responders=head.groupby(STRATA).pilot_id.transform("size")
    head["response_calibrated_weight"]=head.stratum_frame_n/responders
    head[["pilot_id","design_weight","response_calibrated_weight"]].to_csv(OUT / "tables/weight_sensitivity.csv",index=False)
    rates,contrasts=[],[]
    versions=[("supplied_snapshot","supplied_snapshot_",head,"design_weight"),
              ("supplied_snapshot_response_calibrated_sensitivity","supplied_snapshot_",head,"response_calibrated_weight"),
              ("snapshot_same_rule","same_rule_snapshot_",head,"design_weight"),
              ("snapshot_same_rule_response_calibrated_sensitivity","same_rule_snapshot_",head,"response_calibrated_weight"),
              ("verified_head","historical_head_",head,"design_weight"),
              ("verified_head_response_calibrated_sensitivity","historical_head_",head,"response_calibrated_weight"),
              ("earlier_complete_subset","earlier_",head[head.in_earlier_complete_cohort],"design_weight"),
              ("head_on_earlier_complete_subset","historical_head_",head[head.in_earlier_complete_cohort],"design_weight")]
    for version,prefix,frame,weight in versions:
        for tool in ["all","openspec","speckit"]:
            sub=frame if tool=="all" else frame[frame.tool.eq(tool)]
            for feature in FEATURES:
                col=prefix+feature
                for outcome in ["test_added","test_modified"]:
                    means,intervals,difference,ci,repos,valid=weighted_contrast(sub,col,outcome,weight)
                    for flag in [0,1]:
                        group=sub[sub[col].eq(flag)]
                        rates.append({"version":version,"tool":tool,"feature":feature,"outcome":outcome,"feature_present":flag,"n_prs":len(group),"n_repositories":repos[flag],"outcome_prs":int(group[outcome].sum()),"unweighted_pilot_rate_not_a_frame_estimate":float(group[outcome].mean()) if len(group) else np.nan,"weighted_descriptive_rate":means[flag],"repository_bootstrap_low":intervals[flag][0],"repository_bootstrap_high":intervals[flag][1],"weight_method":weight,"interval_scope":"approximate fixed-weight repository-composition interval, not survey-design population inference"})
                    contrasts.append({"version":version,"tool":tool,"feature":feature,"outcome":outcome,"n_exposed":int(sub[col].eq(1).sum()),"n_unexposed":int(sub[col].eq(0).sum()),"weighted_rate_difference":difference,"repository_bootstrap_low":ci[0],"repository_bootstrap_high":ci[1],"bootstrap_valid":valid,"interval_withheld_for_sparse_repositories":min(repos)<3})
    rates=pd.DataFrame(rates);contrasts=pd.DataFrame(contrasts)
    rates.to_csv(OUT / "tables/testing_rates_by_version_and_tool.csv",index=False)
    contrasts.to_csv(OUT / "tables/weighted_pilot_contrasts.csv",index=False)
    # Earlier/head feature changes use only PRs with complete independent retrieval.
    early=head[head.in_earlier_complete_cohort]
    earlier=[]
    for tool in ["all","openspec","speckit"]:
        sub=early if tool=="all" else early[early.tool.eq(tool)]
        for feature in FEATURES:
            a,b=sub["earlier_"+feature],sub["historical_head_"+feature]
            earlier.append({"tool":tool,"feature":feature,"paired_n":len(sub),"earlier_present":int(a.sum()),"head_present":int(b.sum()),"label_mismatches":int(a.ne(b).sum())})
    pd.DataFrame(earlier).to_csv(OUT / "tables/earlier_vs_head_features.csv",index=False)
    # Full frozen frame provides template context, never historical replacement.
    baseline=pd.read_parquet(BASELINE / "outputs/analysis_dataset.parquet")
    frame=baseline[baseline.tool.isin(["openspec","speckit"]) & baseline.closed_at.notna()]
    context=[]
    for tool,g in frame.groupby("tool"):
        for feature in FEATURES:
            for flag in [0,1]:
                s=g[g[feature].eq(flag)]
                context.append({"tool":tool,"feature":feature,"feature_present":flag,"n_baseline_prs":len(s),"baseline_test_added_rate":float(s.test_added.mean()) if len(s) else np.nan,"historical_version_verified":False})
    pd.DataFrame(context).to_csv(OUT / "tables/frozen_frame_template_context.csv",index=False)
    write_json(OUT / "statistical_limits.json",{"historical_n":len(head),"repository_clusters":int(head.repo_name.nunique()),"kish_weight_effective_n":float(head.design_weight.sum()**2/(head.design_weight**2).sum()),"max_design_weight":float(head.design_weight.max()),"regression":"withheld","reason":"Small pilot, fewer than 30 repositories, sparse exposures and outcome-stratified selection; adjusted logistic inference would be unstable/misleading.","p_values":"not computed: naive chi-square/Fisher tests ignore deliberate outcome-stratified selection","weights":"original N_h/n_h for each frozen tool/AC/edge/outcome stratum","nonresponse":"One unavailable historical PR is excluded transparently; response-calibrated sensitivity assumes missing-at-random within the original stratum, without claiming that assumption holds.","intervals":"5000 fixed-weight whole-repository bootstrap resamples, seed 20261102. Approximate composition uncertainty only; not a design-correct confidence interval for the 3070-PR frame. Withheld if either exposure appears in fewer than 3 repositories or fewer than 95% of replicates are finite.","population_claims":"none; estimates conditional on pilot selection, content accessibility, structural rules, and the unvalidated path outcome classifier"})
    # Two primary features, separate tools; no pooled bar disguising template mix.
    fig,axes=plt.subplots(1,2,figsize=(11,4.7),sharey=True)
    for ax,feature in zip(axes,FEATURES[:2]):
        for j,tool in enumerate(["openspec","speckit"]):
            s=rates[(rates.version=="verified_head") & rates.tool.eq(tool) & rates.feature.eq(feature) & rates.outcome.eq("test_added")].sort_values("feature_present")
            y=s.weighted_descriptive_rate.to_numpy(float)*100
            x=np.array([0,1])+(-.17 if j==0 else .17)
            ax.bar(x,y,width=.32,label="OpenSpec" if j==0 else "Spec Kit",color=["#367e91","#d59140"][j])
            for xi,row in zip(x,s.itertuples()):
                if np.isfinite(row.weighted_descriptive_rate):
                    ax.text(xi,row.weighted_descriptive_rate*100+2,f"n={row.n_prs}",ha="center",fontsize=9)
        ax.set_xticks([0,1],["Absent","Present"])
        ax.set_title(LABELS[feature]);ax.set_ylim(0,105)
        ax.spines[["top","right"]].set_visible(False)
    axes[0].set_ylabel("IPW descriptive test-addition rate (%)")
    axes[1].legend(loc="upper left")
    fig.suptitle("Pinned PR-head pilot: tool-specific descriptions")
    fig.text(.5,.01,"Outcome-stratified pilot; counts are sampled PRs. No population significance inference. Intervals are in the tables.",ha="center",fontsize=9)
    fig.tight_layout(rect=[0,.04,1,.94])
    fig.savefig(OUT / "figures/historical_pilot_by_tool.png",dpi=180)
    plt.close(fig)
    print(agreement[(agreement.level=="PR_complete_head") & agreement.tool.eq("all")].to_string(index=False))
    print(contrasts[contrasts.version.eq("verified_head") & contrasts.outcome.eq("test_added")].to_string(index=False))


if __name__=="__main__":reanalyze()
