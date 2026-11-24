"""Freeze and analyze the final RQ1 cohort using local artifacts."""
from hashlib import sha256
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
MID = BASE / 'presentation_evaluation_2026_11_17'
sys.path.insert(0, str(MID))
from evaluate import bootstrap

OUT = HERE / 'outputs'
SOURCE = BASE / 'content_test_detection/outputs/full_cohort/final_verification_v1/ai-assisted-source-v1'
KEY = ['repo_name', 'pr_number']
F = ['has_acceptance_criteria', 'has_edge_cases', 'has_testing_requirement']
NAMES = ['Acceptance criteria', 'Edge cases', 'Testing directives']
Y = 'test_added_content_verified'
LOG = ['n_words', 'repo_stars', 'n_changed_source_files']
PRIMARY = ' + '.join(F[:2] + ['has_requirements', 'log_n_words', 'log_repo_stars',
                              'C(tool_group)', 'C(repo_language_group)'])
SECONDARY = PRIMARY + ' + ' + F[2]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def save(frame, name):
    frame.to_csv(OUT / f'{name}.csv', index=False)


def prepare(data):
    result = data.copy()
    for col in LOG:
        assert result[col].dropna().ge(0).all()
        result['log_' + col] = np.log1p(result[col])
    for col, minimum in [('tool', 30), ('repo_language', 50)]:
        freq = result.loc[result.resolved, col].value_counts()
        result[col + '_group'] = result[col].where(result[col].isin(freq[freq >= minimum].index), 'Other')
    return result


def fit(frame, outcome, rhs, terms, model):
    glm = smf.glm(f'{outcome} ~ {rhs}', data=frame, family=sm.families.Binomial())
    used = frame.loc[glm.data.row_labels]
    result = glm.fit(cov_type='cluster', cov_kwds={'groups': used.repo_name, 'use_correction': True},
                     maxiter=200)
    rank = np.linalg.matrix_rank(glm.exog)
    stable = (result.converged and rank == glm.exog.shape[1] and np.isfinite(result.bse).all()
              and result.params.abs().max() < 20)
    ci = result.conf_int()
    return [dict(model=model, outcome=outcome, term=term, n=len(used),
                 repositories=used.repo_name.nunique(), coefficients=glm.exog.shape[1],
                 rank=rank, converged=result.converged, stable=stable, formula=rhs,
                 odds_ratio=np.exp(result.params[term]) if stable else np.nan,
                 ci_low=np.exp(ci.loc[term, 0]) if stable else np.nan,
                 ci_high=np.exp(ci.loc[term, 1]) if stable else np.nan,
                 p_value=result.pvalues[term] if stable else np.nan)
            for term in terms]


def rates(frame, feature, outcome):
    summary = {}
    for value, name in [(0, 'absent'), (1, 'present')]:
        col = frame.loc[frame[feature].eq(value), outcome]
        n = int(col.notna().sum())
        pos = int(col.sum())
        summary.update({f'{name}_total': len(col), f'{name}_observed': n,
                        f'{name}_positive': pos, f'{name}_negative': n - pos,
                        f'{name}_missing': len(col) - n, f'{name}_rate': pos/n if n else np.nan})
    return dict(difference_pp=100*(summary['present_rate']-summary['absent_rate']), **summary)


def plot(main):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), layout='constrained')
    for ax, estimate, low, high, null, title in [
        (axes[0], 'difference_pp', 'difference_ci_low', 'difference_ci_high', 0, 'Unadjusted rate difference (pp)'),
        (axes[1], 'adjusted_or', 'adjusted_ci_low', 'adjusted_ci_high', 1, 'Adjusted odds ratio')]:
        y = np.arange(len(main))
        middle = main[estimate]
        ax.errorbar(middle, y, xerr=[middle-main[low], main[high]-middle], fmt='o',
                    color='#205780', capsize=4)
        ax.axvline(null, color='#667788', ls='--', lw=1)
        ax.set_yticks(y, NAMES if ax is axes[0] else [])
        ax.tick_params(axis='y', length=0)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.spines[['top','right','left']].set_visible(False)
        if null == 1:
            ax.set_xscale('log')
            ax.set_xticks([0.75, 1, 1.5, 2, 2.5], ['0.75', '1', '1.5', '2', '2.5'])
            ax.minorticks_off()
    axes[0].set_xlabel('Point estimates and 95% intervals')
    axes[1].set_xlabel('Point estimates and 95% intervals')
    fig.suptitle('Specification features and content-verified test additions')
    for extension in ['pdf', 'svg', 'png']:
        fig.savefig(OUT / f'associations.{extension}', dpi=300)
    plt.close(fig)


def plot_missing(main, scenarios):
    bounds = scenarios.pivot(index='feature',columns='scenario',values='difference_pp').loc[F]
    center = main['difference_pp'].to_numpy()
    fig, ax = plt.subplots(figsize=(7.6,3.5),layout='constrained')
    ax.errorbar(center, np.arange(len(F)),
                xerr=[center-bounds.lower_difference, bounds.upper_difference-center],
                fmt='o', color='#205780', capsize=5)
    ax.axvline(0,color='#667788',ls='--',lw=1)
    ax.set_yticks(range(len(F)),NAMES)
    ax.invert_yaxis()
    ax.set_xlabel('Test-addition gap (percentage points)\nDots show observed gaps. Bars show extreme assignment bounds.')
    ax.set_title('How the 72 unknown outcomes could shift the raw differences')
    ax.spines[['top','right','left']].set_visible(False)
    for extension in ['pdf','svg','png']:
        fig.savefig(OUT/f'missing_outcome_bounds.{extension}',dpi=300)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    paths = {
        'features': BASE / 'outputs/analysis_dataset.parquet',
        'outcomes': SOURCE / 'verified_cohort.csv',
        'unknown_audit': SOURCE / 'codex_source_review_v16/all_85_review.csv',
        'earlier': MID / 'outputs/analysis_dataset.csv',
        'head': BASE / 'historical_validation/outputs/historical_head_analysis_cohort.csv',
        'earlier_anchor': BASE / 'historical_validation/outputs/earlier_complete_analysis_cohort.csv',
    }
    hashes = {k: digest(v) for k,v in paths.items()}
    s = pd.read_parquet(paths['features'])
    o = pd.read_csv(paths['outcomes'])
    audit = pd.read_csv(paths['unknown_audit']).query("outcome == 'unknown'")
    cols = F + ['repo_id','tool','repo_language','has_requirements','test_added'] + LOG
    checks = KEY + ['tool','test_added']
    same = s[checks].merge(o[checks], on=KEY, how='outer', indicator=True,
                           validate='one_to_one', suffixes=('_spec','_content'))
    assert same._merge.eq('both').all()
    for col in ['tool','test_added']:
        assert same[f'{col}_spec'].eq(same[f'{col}_content']).all()
    overlap = [c for c in o if c not in cols + KEY]
    d = s[KEY+cols].merge(o[KEY+overlap], on=KEY, validate='one_to_one')
    d = d.merge(audit[KEY+['verification_state','explanation']], on=KEY, how='left', validate='one_to_one')
    d['resolved'] = d[Y].notna()
    assert d.explanation.notna().eq(~d.resolved).all()
    assert d[F+['has_requirements','test_added']].isin([0,1]).all().all()
    assert d.loc[d.resolved,Y].isin([0,1]).all()
    assert d.loc[d[Y].eq(0),'inspection_complete'].astype(str).str.lower().eq('true').all()
    assert d.loc[d.resolved,'pinned_commit_sha'].str.fullmatch('[a-f0-9]{40}').all()
    d = prepare(d)
    s0 = d[d.resolved].copy()
    freeze = OUT / 'frozen_analysis_cohort.csv'
    payload = d.to_csv(index=False, lineterminator='\n').encode()
    if freeze.exists():
        assert freeze.read_bytes() == payload, 'Frozen cohort differs. Create a new version.'
    else:
        freeze.write_bytes(payload)
    counts = dict(total=len(d), repositories=d.repo_name.nunique(), resolved=len(s0),
                  resolved_repositories=s0.repo_name.nunique(), positive=int(s0[Y].sum()),
                  negative=int(s0[Y].eq(0).sum()), unknown=int((~d.resolved).sum()),
                  diff_or_metadata=int(d.verification_state.eq('missing_or_changed_github_data').sum()),
                  unresolved_file_evidence=int((~d.resolved & d.verification_state.ne('missing_or_changed_github_data')).sum()))
    assert counts['total'] == counts['resolved'] + counts['unknown']
    (OUT/'reconciliation.json').write_text(json.dumps({
        **counts, 'verification_percent':100*len(s0)/len(d), 'unmatched':0, 'duplicate_PRs':0,
        'missing_by_input':d[cols].isna().sum().to_dict(),
        'input_hashes':{str(paths[k].relative_to(BASE)):v for k,v in hashes.items()},
        'frozen_cohort_sha256':digest(freeze)}, indent=2),encoding='utf-8')

    main_rows, model_rows, scenarios, loo, comparisons, coverage, within = [], [], [], [], [], [], []
    old = pd.read_csv(paths['earlier'])
    matching_old = old.loc[old[Y].notna(),KEY+[Y]].merge(d[KEY+[Y]],on=KEY,validate='one_to_one',suffixes=('_old','_final'))
    assert len(matching_old) == old[Y].notna().sum()
    save(matching_old[matching_old[Y+'_old'].ne(matching_old[Y+'_final'])], 'earlier_outcome_revisions')
    for col in F + ['repo_name','tool','repo_language','test_added']:
        for value, group in d.groupby(col, dropna=False):
            coverage.append(dict(characteristic=col, group=value, n=len(group),
                                 observed=int(group.resolved.sum()), unknown=int((~group.resolved).sum()),
                                 verification_rate=group.resolved.mean()))
    d['verified_indicator'] = d.resolved.astype(int)
    largest = s0.repo_name.value_counts().index[0]
    for feature, name in zip(F, NAMES):
        rhs = SECONDARY if feature == F[2] else PRIMARY
        crude = fit(s0,Y,feature,[feature],'unadjusted')[0]
        adj = fit(s0,Y,rhs,[feature],'adjusted')[0]
        assert adj['stable'] and adj['n'] == len(s0)
        model_rows += [crude,adj]
        ci = bootstrap(s0,feature,reps=5000)
        row = dict(feature=name, column=feature, **rates(d,feature,Y))
        row.update(difference_ci_low=ci['difference_ci'][0],difference_ci_high=ci['difference_ci'][1],
                   bootstrap_replicates=ci['valid_replicates'])
        for prefix, model in [('unadjusted',crude),('adjusted',adj)]:
            row.update({prefix+'_'+k:model[v] for k,v in
                        [('or','odds_ratio'),('ci_low','ci_low'),('ci_high','ci_high'),('p','p_value')]})
        main_rows.append(row)
        for frame, outcome, name in [(d,'test_added','filename_full'),(s0,'test_added','filename_same_subset'),
                                     (old,Y,'earlier_verified'),(s0,Y,'final_verified')]:
            comparisons.append(dict(method=name,feature=feature,**rates(frame,feature,outcome)))
        for group, frame in s0.groupby('tool'):
            within.append(dict(tool=group,feature=feature,**rates(frame,feature,Y)))
        for repo in s0.repo_name.unique():
            loo.append(dict(removed_repository=repo, feature=feature, **rates(s0[s0.repo_name.ne(repo)],feature,Y)))
        for frame, outcome, formula, name in [
            (d,'verified_indicator',feature,'verification_unadjusted'),
            (s0,Y,rhs+' + log_n_changed_source_files','additional_PR_size_control'),
            (s0[s0.repo_name.ne(largest)],Y,rhs,'without_largest_repository'),
            (d,'test_added',rhs,'filename_full'),
            (s0,'test_added',rhs,'filename_same_subset'),
            (prepare(old.assign(resolved=old[Y].notna())).query('resolved'),Y,rhs,'earlier_verified')]:
            model_rows.extend(fit(frame,outcome,formula,[feature],name))
        for scenario, fill in [('lower_difference',1-d[feature]),('upper_difference',d[feature]),
                               ('all_missing_negative',0),('all_missing_positive',1),('filename_for_missing',d.test_added)]:
            frame = d.assign(sensitivity_outcome=d[Y].fillna(fill))
            scenarios.append(dict(scenario=scenario,feature=feature,**rates(frame,feature,'sensitivity_outcome')))
            model_rows.extend(fit(frame,'sensitivity_outcome',rhs,[feature],scenario))

    main_table = pd.DataFrame(main_rows)
    for kind in ['adjusted','unadjusted']:
        main_table[kind+'_holm_p_primary'] = np.nan
        main_table.loc[:1,kind+'_holm_p_primary'] = multipletests(main_table.loc[:1,kind+'_p'],method='holm')[1]
        main_table[kind+'_holm_p_all_three_sensitivity'] = multipletests(main_table[kind+'_p'],method='holm')[1]
    save(main_table,'main_associations')
    save(pd.DataFrame(coverage),'verification_coverage')
    save(pd.DataFrame(loo),'leave_one_repository_out')
    scenario_table = pd.DataFrame(scenarios)
    save(scenario_table,'missing_outcome_sensitivity')
    save(pd.DataFrame(comparisons),'definition_and_cohort_comparison')
    save(pd.DataFrame(within),'within_tool_rates')
    save(pd.DataFrame(model_rows),'model_results')
    save(s0[s0[Y].ne(s0.test_added)][KEY+['tool','test_added',Y,'confirmed_file_path']],'changed_filename_labels')
    save(d[~d.resolved][KEY+F+['tool','repo_language','verification_state','explanation']],'unknown_prs')
    save(main_table[['feature']+[c for c in main_table if c.startswith(('absent_','present_'))]],'descriptive_statistics')
    historical = []
    for name in ['head','earlier_anchor']:
        h = pd.read_csv(paths[name]).merge(d[KEY+[Y]],on=KEY,how='left',validate='one_to_one',indicator=True)
        assert h._merge.eq('both').all()
        for feature in F:
            head, snapshot, anchor = [prefix+feature for prefix in
                                     ['historical_head_','same_rule_snapshot_','earlier_']]
            for col in [snapshot,head]+([anchor] if name=='earlier_anchor' else []):
                hpair = h.dropna(subset=[col,head])
                historical.append(dict(pilot_cohort=name,feature=feature,feature_version=col,
                                       n=len(h), observed=h[Y].notna().sum(),
                                       mismatch_vs_head=hpair[col].ne(hpair[head]).sum(),
                                       **rates(h,col,Y)))
    save(pd.DataFrame(historical),'historical_descriptive_only')
    plot(main_table)
    plot_missing(main_table,scenario_table)
    assert all(digest(paths[k])==value for k,value in hashes.items())
    print(counts)
    print(main_table.to_string(index=False))


if __name__ == '__main__':
    main()
