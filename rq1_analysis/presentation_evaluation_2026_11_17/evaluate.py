"""Offline evaluation of a frozen content-outcome snapshot; no acquisition imports."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
import pandas as pd
from scipy.stats import norm
import statsmodels.api as sm
import statsmodels.formula.api as smf

HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=BASE/'content_test_detection/outputs/full_cohort';KEY=['repo_name','pr_number']
F=['has_acceptance_criteria','has_edge_cases','has_testing_requirement'];NAMES=['Acceptance criteria','Edge cases','Testing directive (secondary)']
OUT=HERE/'outputs';OUT.mkdir(exist_ok=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save_json(name,value):(OUT/name).write_text(json.dumps(value,indent=2,default=str),encoding='utf-8')

def bootstrap(frame,feature,y='test_added_content_verified',reps=3000):
    g=frame.groupby(['repo_name',feature])[y].agg(['sum','count']).unstack(feature,fill_value=0)
    a=np.column_stack([g[('sum',0)],g[('count',0)],g[('sum',1)],g[('count',1)]])
    rng=np.random.default_rng(520);draw=a[rng.integers(0,len(a),(reps,len(a)))].sum(axis=1)
    good=(draw[:,1]>0)&(draw[:,3]>0);draw=draw[good]
    absent=draw[:,0]/draw[:,1];present=draw[:,2]/draw[:,3]
    return {'absent_ci':np.quantile(absent,[.025,.975]).tolist(),'present_ci':np.quantile(present,[.025,.975]).tolist(),'difference_ci':(100*np.quantile(present-absent,[.025,.975])).tolist(),'valid_replicates':int(good.sum())}

def main():
    source=ROOT/'current_main_outcomes.csv';spec=BASE/'outputs/analysis_dataset.parquet'
    protected=[source,spec]+list(ROOT.glob('batch_*/sample.csv'))+list(ROOT.glob('batch_*/selection_protocol.json'))
    hashes={str(p):digest(p) for p in protected}
    # Freeze exactly the outcomes used, separately from continuously updated reports.
    (HERE/'frozen_content_outcomes.csv').write_bytes(source.read_bytes())
    o=pd.read_csv(HERE/'frozen_content_outcomes.csv');s=pd.read_parquet(spec)
    assert not o.duplicated(KEY).any() and not s.duplicated(KEY).any()
    assert o.test_added_content_verified.dropna().isin([0,1]).all()
    cross=s[KEY+['tool','test_added']].merge(o[KEY+['tool','test_added']],on=KEY,validate='one_to_one',suffixes=('_snapshot','_outcome'))
    assert cross.tool_snapshot.eq(cross.tool_outcome).all() and cross.test_added_snapshot.eq(cross.test_added_outcome).all(),'Saved identity metadata conflicts'
    check=s[KEY].merge(o[KEY],on=KEY,how='outer',indicator=True,validate='one_to_one')
    o[~o[KEY].apply(tuple,axis=1).isin(set(map(tuple,s[KEY].to_numpy())))].to_csv(OUT/'unmatched_outcomes.csv',index=False)
    wanted=KEY+F+['has_requirements','n_words','repo_stars','repo_language','tool','test_added','n_changed_source_files','repo_id']
    d=s[wanted].merge(o[KEY+['test_added_content_verified','n_files_inspected','n_eligible_added_files','test_detection_method','inspection_complete','pinned_commit_sha']],on=KEY,how='left',validate='one_to_one')
    d['resolved']=d.test_added_content_verified.notna()
    # Persist draw identities separately; do not interpret completion as inclusion.
    assignments=[]
    for p in sorted(ROOT.glob('batch_*/sample.csv')):
        b=pd.read_csv(p);cols=KEY+[c for c in ['stratum','eligible_stratum_n','allocated_batch_n','batch_inclusion_fraction','selection_hash','execution_rank'] if c in b]
        b=b[cols].copy();b['selection_batch']=p.parent.name;assignments.append(b)
    assignment=pd.concat(assignments,ignore_index=True);assert not assignment.duplicated(KEY).any();assignment.to_csv(OUT/'selection_assignments.csv',index=False)
    d=d.merge(assignment[KEY+['selection_batch']],on=KEY,how='left',validate='one_to_one');d['selection_batch']=d.selection_batch.fillna('outside_scaling_batches')
    d.to_csv(OUT/'analysis_dataset.csv',index=False);known=d[d.resolved].copy()
    rows=[]
    for feature,name in zip(F,NAMES):
        ci=bootstrap(known,feature);row={'feature':name,'column':feature}
        for flag,tag in [(0,'absent'),(1,'present')]:
            g=d[d[feature].eq(flag)];k=g[g.resolved];pos=int(k.test_added_content_verified.sum());n=len(k)
            row.update({tag+'_resolved':n,tag+'_positive':pos,tag+'_negative':n-pos,tag+'_unknown':len(g)-n,tag+'_repositories':k.repo_name.nunique(),tag+'_rate':pos/n,tag+'_rate_ci_low':ci[tag+'_ci'][0],tag+'_rate_ci_high':ci[tag+'_ci'][1],tag+'_path_rate_same_subset':k.test_added.mean(),tag+'_original_full_path_rate':g.test_added.mean(),tag+'_bound_low':pos/len(g),tag+'_bound_high':(pos+len(g)-n)/len(g),tag+'_verification_rate':n/len(g)})
        row.update(difference_pp=100*(row['present_rate']-row['absent_rate']),difference_ci_low=ci['difference_ci'][0],difference_ci_high=ci['difference_ci'][1],missing_outcome_RD_low=100*(row['present_bound_low']-row['absent_bound_high']),missing_outcome_RD_high=100*(row['present_bound_high']-row['absent_bound_low']),bootstrap_replicates=ci['valid_replicates'])
        rows.append(row)
    rates=pd.DataFrame(rows);rates.to_csv(OUT/'results.csv',index=False)
    # Comparable path and content comparisons on exactly the same selected PRs.
    diffs=known[known.test_added.ne(known.test_added_content_verified)]
    diffs.to_csv(OUT/'changed_labels.csv',index=False)
    missing=[]
    for col in F+['tool','repo_language','selection_batch','repo_name']:
        for value,g in d.groupby(col,dropna=False):
            k=g[g.resolved];missing.append({'characteristic':col,'group':value,'n':len(g),'resolved':len(k),'unknown':len(g)-len(k),'verification_rate':len(k)/len(g),'content_positive':int(k.test_added_content_verified.sum()),'content_rate':k.test_added_content_verified.mean(),'path_rate_resolved':k.test_added.mean(),'path_rate_unresolved':g.loc[~g.resolved,'test_added'].mean()})
    pd.DataFrame(missing).to_csv(OUT/'verification_coverage.csv',index=False)
    tool_rates=[]
    for tool in ['openspec','speckit']:
        for feature in F:
            for flag,g in known[known.tool.eq(tool)].groupby(feature):
                tool_rates.append({'tool':tool,'feature':feature,'present':flag,'n':len(g),'positive':int(g.test_added_content_verified.sum()),'rate':g.test_added_content_verified.mean()})
    pd.DataFrame(tool_rates).to_csv(OUT/'within_tool_rates.csv',index=False)
    diagnostics=[];models=[]
    fitdata=known.copy();fitdata['y']=fitdata.test_added_content_verified.astype(int)
    for c in ['n_words','repo_stars','n_changed_source_files']:fitdata['log_'+c]=np.log1p(fitdata[c])
    for c,threshold in [('tool',30),('repo_language',50)]:
        counts=fitdata[c].value_counts();fitdata[c+'_group']=fitdata[c].where(fitdata[c].isin(counts[counts.ge(threshold)].index),'Other')
    primary='has_acceptance_criteria + has_edge_cases + has_requirements + log_n_words + log_repo_stars + C(tool_group) + C(repo_language_group)'
    for model,rhs in [('primary_selected_subset',primary),('testing_directive_secondary',primary+' + has_testing_requirement'),('PR_size_sensitivity',primary+' + log_n_changed_source_files')]:
        for outcome in ['content','path_same_subset'] if model=='primary_selected_subset' else ['content']:
            fitdata['y']=fitdata.test_added_content_verified.astype(int) if outcome=='content' else fitdata.test_added.astype(int)
            try:
                fit=smf.glm('y ~ '+rhs,data=fitdata,family=sm.families.Binomial()).fit(cov_type='cluster',cov_kwds={'groups':fitdata.repo_name,'use_correction':True},maxiter=200)
                rank=np.linalg.matrix_rank(fit.model.exog);stable=bool(fit.converged and rank==fit.model.exog.shape[1] and np.isfinite(fit.bse).all() and fit.params.abs().max()<20)
                diagnostics.append({'model':model,'outcome':outcome,'n':int(fit.nobs),'repositories':fitdata.repo_name.nunique(),'parameters':len(fit.params),'rank':int(rank),'converged':bool(fit.converged),'stable':stable,'condition_number':float(np.linalg.cond(fit.model.exog)),'formula':rhs,'selection_scope':'Resolved subset only; not population inference; no missingness correction'})
                if stable:
                    ci=fit.conf_int()
                    for term in F:
                        if term in fit.params:models.append({'model':model,'outcome':outcome,'term':term,'OR':float(np.exp(fit.params[term])),'CI_low':float(np.exp(ci.loc[term,0])),'CI_high':float(np.exp(ci.loc[term,1])),'p_value_reference_only':float(fit.pvalues[term])})
            except Exception as error:diagnostics.append({'model':model,'outcome':outcome,'status':'failed','error':type(error).__name__+':'+str(error)})
    pd.DataFrame(models).to_csv(OUT/'exploratory_models.csv',index=False);save_json('model_diagnostics.json',diagnostics)
    # Historical-head sensitivity: separate tiny/outcome-stratified pilot.
    historical=pd.read_csv(BASE/'historical_validation/outputs/historical_head_analysis_cohort.csv')
    h=historical.merge(o[KEY+['test_added_content_verified']],on=KEY,validate='one_to_one');h.to_csv(OUT/'historical_head_sensitivity.csv',index=False)
    integrity={'n_outcomes':len(o),'n_features':len(s),'join':check['_merge'].value_counts().to_dict(),'unmatched_outcomes':int(check['_merge'].eq('right_only').sum()),'unmatched_feature_rows':int(check['_merge'].eq('left_only').sum()),'feature_missingness':d[F].isna().sum().to_dict(),'repositories_total':d.repo_name.nunique(),'resolved':len(known),'positive':int(known.test_added_content_verified.sum()),'negative':int(known.test_added_content_verified.eq(0).sum()),'unknown':int((~d.resolved).sum()),'resolved_repositories':known.repo_name.nunique(),'negative_to_positive':int((diffs.test_added.eq(0)&diffs.test_added_content_verified.eq(1)).sum()),'positive_to_negative':int((diffs.test_added.eq(1)&diffs.test_added_content_verified.eq(0)).sum()),'disagreements':len(diffs),'historical_head_prs':len(h),'historical_head_outcomes_resolved':int(h.test_added_content_verified.notna().sum()),'negative_inspection_complete_violations':int((known.test_added_content_verified.eq(0)&~known.inspection_complete.fillna(False).astype(bool)).sum()),'missing_pin_resolved':int(known.pinned_commit_sha.isna().sum()),'source_hashes':hashes}
    negative_flags=known.loc[known.test_added_content_verified.eq(0),'inspection_complete'].map(lambda x:str(x).lower()=='true')
    assert negative_flags.all(),'Negative outcome without explicit complete-inspection flag'
    assert known.pinned_commit_sha.astype(str).str.fullmatch('[0-9a-f]{40}').all(),'Invalid pinned commit'
    assert integrity['negative_inspection_complete_violations']==0 and integrity['missing_pin_resolved']==0
    assert all(digest(Path(p))==hash for p,hash in hashes.items()),'Input changed during analysis'
    save_json('validation.json',integrity);print(rates[['feature','absent_resolved','absent_positive','absent_rate','present_resolved','present_positive','present_rate','difference_pp','difference_ci_low','difference_ci_high']].to_string(index=False));print(json.dumps(integrity,default=str));print(pd.DataFrame(models).to_string(index=False))
if __name__=='__main__':main()
