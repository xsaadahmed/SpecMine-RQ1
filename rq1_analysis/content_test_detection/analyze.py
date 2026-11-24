"""Keep content outcomes, snapshot predictors, and historical predictors distinct."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

from common import BASE,HIST,KEY,OUT,write_json

FEATURES=['has_acceptance_criteria','has_edge_cases']


def wilson(k,n):
    if not n:return np.nan,np.nan
    z=norm.ppf(.975);p=k/n;denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    radius=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return max(0,center-radius),min(1,center+radius)


def rate_tables(d,prefix,label):
    rows=[]
    for tool in ['all','openspec','speckit']:
        sub=d if tool=='all' else d[d.tool.eq(tool)]
        for feature in FEATURES:
            for flag in [0,1]:
                g=sub[sub[prefix+feature].eq(flag)]
                verified=g[g.test_added_content_verified.notna()]
                positives=int(verified.test_added_content_verified.sum())
                unknown=len(g)-len(verified)
                lo,hi=wilson(positives,len(verified))
                rows.append({'cohort':label,'tool':tool,'feature':feature,'feature_present':flag,'n_total':len(g),'n_verified':len(verified),'n_unknown':unknown,'n_verified_repositories':verified.repo_name.nunique(),'test_added_content_positive':positives,'original_path_rate_all':float(g.test_added.mean()) if len(g) else np.nan,'original_path_rate_same_verified_subset':float(verified.test_added.mean()) if len(verified) else np.nan,'content_rate_among_verified':positives/len(verified) if len(verified) else np.nan,'wilson_reference_low':lo,'wilson_reference_high':hi,'missingness_identification_lower':positives/len(g) if len(g) else np.nan,'missingness_identification_upper':(positives+unknown)/len(g) if len(g) else np.nan,'interval_scope':'Wilson reference only: selected verified observations; ignores sampling/cluster dependence. Identification bounds allow every unknown outcome to be either 0 or 1.'})
    return rows


def analyze():
    main=pd.read_csv(OUT/'main_pr_outcomes.csv')
    pilot=pd.read_csv(OUT/'pilot_pr_outcomes.csv')
    snapshot=pd.read_parquet(BASE/'outputs/analysis_dataset.parquet')
    main=main.merge(snapshot[KEY+FEATURES+['repo_stars','n_words','n_changed_source_files']],on=KEY,validate='one_to_one')
    historic=pd.read_csv(HIST/'outputs/historical_head_analysis_cohort.csv')
    historical=historic.merge(pilot[KEY+['test_added_content_verified','n_files_inspected','n_eligible_added_files']],on=KEY,validate='one_to_one',suffixes=('','_new'))
    tables=rate_tables(main,'','snapshot_specifications_content_outcomes')+rate_tables(historical,'historical_head_','verified_head_specifications_content_outcomes')
    rates=pd.DataFrame(tables);rates.to_csv(OUT/'tables/rq1_testing_rates.csv',index=False)
    comparisons=[]
    for cohort,d in [('main',main),('historical_head',historical)]:
        known=d[d.test_added_content_verified.notna()]
        agree=known.test_added.astype(int).eq(known.test_added_content_verified.astype(int))
        comparisons.append({'cohort':cohort,'n':len(d),'verified':len(known),'unknown':int(d.test_added_content_verified.isna().sum()),'agreement':int(agree.sum()),'disagreement':int((~agree).sum()),'disagreement_rate_among_verified':float((~agree).mean()) if len(known) else None,'interpretation':'Detector disagreement, not precision/recall or human-reference accuracy'})
        for col in ['tool','repo_language','repo_name']:
            records=[]
            for value,g in d.groupby(col,dropna=False):
                k=g[g.test_added_content_verified.notna()]
                mismatch=k.test_added.astype(int).ne(k.test_added_content_verified.astype(int))
                records.append({'group':value,'n_prs':len(g),'n_verified':len(k),'n_unknown':len(g)-len(k),'disagreements':int(mismatch.sum()),'disagreement_rate_among_verified':float(mismatch.mean()) if len(k) else np.nan,'content_positives':int(k.test_added_content_verified.sum())})
            pd.DataFrame(records).to_csv(OUT/f'tables/{cohort}_coverage_by_{col}.csv',index=False)
    pd.DataFrame(comparisons).to_csv(OUT/'tables/pr_detector_agreement.csv',index=False)
    # Descriptive pair changes are deliberately confined to the verified subset.
    known=main[main.test_added_content_verified.notna()]
    disagreements=known[known.test_added.astype(int).ne(known.test_added_content_verified.astype(int))]
    disagreements.to_csv(OUT/'tables/pr_detector_disagreements.csv',index=False)
    coverage=len(known)/len(main)
    reasons=[]
    if len(known)<200:reasons.append('fewer_than_200_verified_PRs')
    if known.repo_name.nunique()<30:reasons.append('fewer_than_30_repository_clusters')
    if coverage<.8:reasons.append('less_than_80_percent_outcome_coverage')
    if known.test_added_content_verified.nunique()<2:reasons.append('insufficient_outcome_variation')
    # A future full-cohort run can fit the same baseline model with the new Y;
    # a sparse convenience/stratified subset is not used for adjusted inference.
    model_status={'status':'withheld','verified_n':len(known),'verified_repositories':int(known.repo_name.nunique()),'main_coverage':coverage,'reasons':reasons,'historical_pilot':'Adjusted regression withheld for sparse, outcome-stratified historical pilot; no snapshot substitution.','intervals':'Wilson intervals are conditional descriptive reference intervals only. Missing-outcome bounds are primary for coverage interpretation.','accuracy':None,'precision':None,'recall':None}
    if not reasons:
        try:
            import statsmodels.api as sm
            import statsmodels.formula.api as smf
            fitdata=known.dropna(subset=FEATURES+['repo_stars','n_words','n_changed_source_files']).copy()
            fitdata['content_y']=fitdata.test_added_content_verified.astype(int)
            for col in ['n_words','repo_stars','n_changed_source_files']:fitdata['log_'+col]=np.log1p(fitdata[col])
            counts=fitdata.tool.value_counts();fitdata['tool_group']=fitdata.tool.where(fitdata.tool.isin(counts[counts.ge(50)].index),'Other')
            formula='content_y ~ has_acceptance_criteria + has_edge_cases + log_n_words + log_repo_stars + log_n_changed_source_files + C(tool_group)'
            k=6+fitdata.tool_group.nunique()
            if min(fitdata.content_y.sum(),len(fitdata)-fitdata.content_y.sum())<10*k:raise ValueError('insufficient_events_per_parameter')
            fit=smf.glm(formula,data=fitdata,family=sm.families.Binomial()).fit(cov_type='cluster',cov_kwds={'groups':fitdata.repo_name,'use_correction':True})
            if not fit.converged or not np.isfinite(fit.bse).all() or (fit.params.abs()>20).any():raise ValueError('unstable_model')
            ci=fit.conf_int()
            pd.DataFrame({'term':fit.params.index,'odds_ratio':np.exp(fit.params.values),'low':np.exp(ci[0].values),'high':np.exp(ci[1].values),'p_value':fit.pvalues.values}).to_csv(OUT/'tables/content_outcome_regression.csv',index=False)
            model_status.update(status='estimated_snapshot_predictors_only',formula=formula)
        except Exception as e:model_status['reasons'].append(type(e).__name__+':'+str(e)[:150])
    write_json(OUT/'statistical_analysis_status.json',model_status)
    write_json(OUT/'comparison_summary.json',{'comparisons':comparisons,'verified_main_negative_to_positive':int((disagreements.test_added.eq(0)&disagreements.test_added_content_verified.eq(1)).sum()),'verified_main_positive_to_negative':int((disagreements.test_added.eq(1)&disagreements.test_added_content_verified.eq(0)).sum()),'original_RQ1_inference_replaced':False,'reason':'Content-corrected subset descriptions are available, but verification coverage and historical sample size do not support replacing original association estimates.'})
    # Coverage is visible; unknowns are never plotted as negatives.
    fig,ax=plt.subplots(figsize=(9,3.6))
    for i,(label,d) in enumerate([('Historical pilot (40 PRs)',pilot),('Main cohort (3,186 PRs)',main)]):
        values=[int(d.test_added_content_verified.eq(1).sum()),int(d.test_added_content_verified.eq(0).sum()),int(d.test_added_content_verified.isna().sum())]
        left=0
        for n,color,name in zip(values,['#237b74','#607f9f','#dddddd'],['Confirmed added test','Exhaustive negative','Unknown']):
            ax.barh(i,n/len(d),left=left,color=color,label=name if i==0 else None)
            if n/len(d)>.08:ax.text(left+n/len(d)/2,i,str(n),ha='center',va='center')
            left+=n/len(d)
    ax.set_yticks([0,1],['Historical pilot','Main cohort']);ax.set_xlim(0,1);ax.set_xlabel('Fraction of PRs');ax.legend(loc='upper center',bbox_to_anchor=(.5,1.28),ncol=3,frameon=False)
    ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'figures/content_verification_coverage.png',dpi=180);plt.close(fig)
    return comparisons
