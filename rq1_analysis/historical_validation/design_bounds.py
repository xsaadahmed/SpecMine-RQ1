"""Conservative finite-frame uncertainty under the actual stratified PR draw.

Invert hypergeometric tails for binary domain/exposure counts per stratum.
Bonferroni covers all strata, both exposure groups, and both primary predictors.
Ratio and difference bounds are propagated conservatively without independence
assumptions between PR outcomes or repositories. This targets the retrievable
protocol domain of the finite, curated two-tool frame, not all software PRs.
"""
import numpy as np
import pandas as pd
from scipy.stats import hypergeom

from hv_common import OUT,write_json

PRIMARY=["has_acceptance_criteria","has_edge_cases"]
STRATA=["tool","supplied_snapshot_has_acceptance_criteria","supplied_snapshot_has_edge_cases","test_added"]


def hypergeometric_count_interval(N,n,k,alpha=.05):
    """Equal-tail exact confidence set for a finite-population success count."""
    assert 0<=k<=n<=N and n>0 and 0<alpha<1
    lowest,highest=k,N-n+k
    lo,hi=lowest,highest
    while lo<hi:
        mid=(lo+hi)//2
        if hypergeom.sf(k-1,N,mid,n)>=alpha/2:hi=mid
        else:lo=mid+1
    lower=lo
    lo,hi=lowest,highest
    while lo<hi:
        mid=(lo+hi+1)//2
        if hypergeom.cdf(k,N,mid,n)>=alpha/2:lo=mid
        else:hi=mid-1
    return lower,lo


def ratio_bounds(success_lo,success_hi,failure_lo,failure_hi):
    lower=success_lo/(success_lo+failure_hi) if success_lo+failure_hi else 0.
    upper=success_hi/(success_hi+failure_lo) if success_hi+failure_lo else 1.
    return lower,upper


def design_bounds():
    d=pd.read_csv(OUT/"pilot_observations.csv")
    n_strata=d.groupby(STRATA).ngroups
    family=n_strata*2*len(PRIMARY)
    alpha_cell=.05/family
    cells=[]
    for key,g in d.groupby(STRATA):
        N=int(g.stratum_frame_n.iloc[0]);n=len(g)
        assert n==int(g.stratum_sample_n.iloc[0])
        for feature in PRIMARY:
            for flag in [0,1]:
                # D=0 contributes to neither exposure group: no missing feature
                # is coded as absence. Domain is complete head retrieval +
                # frozen net-diff path/status compatibility under this protocol.
                indicator=g.in_historical_head_cohort & g['historical_head_'+feature].eq(flag)
                k=int(indicator.sum())
                lower,upper=hypergeometric_count_interval(N,n,k,alpha_cell)
                cells.append(dict(zip(STRATA,key),feature=feature,feature_present=flag,N=N,n=n,k=k,population_count_low=lower,population_count_high=upper))
    cells=pd.DataFrame(cells)
    cells.to_csv(OUT/'tables/exact_design_count_bounds.csv',index=False)
    rows=[]
    for tool in ['all','openspec','speckit']:
        for feature in PRIMARY:
            subset=cells[cells.feature.eq(feature)]
            if tool!='all':subset=subset[subset.tool.eq(tool)]
            bounds={}
            for flag in [0,1]:
                g=subset[subset.feature_present.eq(flag)]
                yes=g[g.test_added.eq(1)][['population_count_low','population_count_high']].sum()
                no=g[g.test_added.eq(0)][['population_count_low','population_count_high']].sum()
                bounds[flag]=ratio_bounds(yes.iloc[0],yes.iloc[1],no.iloc[0],no.iloc[1])
            rows.append({'tool':tool,'feature':feature,'unexposed_rate_low':bounds[0][0],'unexposed_rate_high':bounds[0][1],'exposed_rate_low':bounds[1][0],'exposed_rate_high':bounds[1][1],'difference_low':bounds[1][0]-bounds[0][1],'difference_high':bounds[1][1]-bounds[0][0],'simultaneous_confidence':.95,'family_count':family,'target':'retrievable/compatible domain in the frozen two-tool PR frame'})
    result=pd.DataFrame(rows)
    result.to_csv(OUT/'tables/exact_design_rate_bounds.csv',index=False)
    write_json(OUT/'design_bounds_protocol.json',{'method':'Exact hypergeometric tail inversion for each finite-stratum domain/exposure count; Bonferroni simultaneous coverage; conservative propagation to ratios and differences','alpha_family':.05,'binary_count_intervals':family,'alpha_per_count':alpha_cell,'target':'Current-protocol retrievable, unchanged-net-diff domain within the frozen 3070-PR two-tool frame','selection_assumption':'Hash-ranked selection is treated as a reproducible pseudorandom simple random sample within each predeclared stratum; frame/domain state treated as fixed during acquisition','unavailable_pr':'D=0 belongs to neither exposure group. It is not imputed as exposure-absent; this targets a retrieval domain, not all frame PRs.','repository_dependence':'Design-based finite-population inference treats outcomes as fixed and relies on randomized PR sampling, rather than independent repository outcomes.','remaining_limits':'Does not correct curated corpus selection, feature definition error, test-outcome detector error, changing remote state, or lack of genuine pre-implementation precedence. Bounds may be very wide because only 1-3 PRs were drawn per stratum.'})
    import json
    limits_path=OUT/'statistical_limits.json'
    if limits_path.exists():
        limits=json.loads(limits_path.read_text())
        limits['primary_confidence_bounds']='Conservative simultaneous exact finite-frame bounds: see design_bounds_protocol.json and tables/exact_design_rate_bounds.csv. The separate bootstrap intervals are composition diagnostics.'
        write_json(limits_path,limits)
    print(result[['tool','feature','difference_low','difference_high']].to_string(index=False))
    # The final figure displays the sampling-aware bounds rather than visually
    # suggesting precision from weighted bars alone.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rates_path=OUT/'tables/testing_rates_by_version_and_tool.csv'
    if rates_path.exists():
        rates=pd.read_csv(rates_path)
        fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True)
        for ax,feature,title in zip(axes,PRIMARY,['Acceptance criteria','Edge cases']):
            for j,tool in enumerate(['openspec','speckit']):
                s=rates[rates.version.eq('verified_head')&rates.tool.eq(tool)&rates.feature.eq(feature)&rates.outcome.eq('test_added')].sort_values('feature_present')
                b=result[result.tool.eq(tool)&result.feature.eq(feature)].iloc[0]
                y=s.weighted_descriptive_rate.to_numpy(float)*100
                lower=np.array([b.unexposed_rate_low,b.exposed_rate_low])*100
                upper=np.array([b.unexposed_rate_high,b.exposed_rate_high])*100
                x=np.array([0,1])+(-.17 if j==0 else .17)
                ax.bar(x,y,width=.32,color=['#367e91','#d59140'][j],label='OpenSpec' if j==0 else 'Spec Kit',yerr=np.vstack([y-lower,upper-y]),capsize=4,error_kw={'elinewidth':1.2})
                for xi,row in zip(x,s.itertuples()):ax.text(xi,row.weighted_descriptive_rate*100+2,f'n={row.n_prs}',ha='center',fontsize=9)
            ax.set_xticks([0,1],['Absent','Present']);ax.set_title(title);ax.set_ylim(0,105)
            ax.spines[['top','right']].set_visible(False)
        axes[0].set_ylabel('Weighted descriptive test-addition rate (%)')
        axes[1].legend(loc='upper right',fontsize=9)
        fig.suptitle('Pinned PR-head pilot: broad uncertainty within each tool')
        fig.text(.5,.01,'Intervals: conservative simultaneous 95% finite-frame design bounds. Counts: sampled PRs. No causal inference.',ha='center',fontsize=9)
        fig.tight_layout(rect=[0,.04,1,.94])
        fig.savefig(OUT/'figures/historical_pilot_by_tool.png',dpi=180)
        plt.close(fig)


if __name__=='__main__':design_bounds()
