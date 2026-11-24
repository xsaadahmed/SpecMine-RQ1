"""Reconcile the published tables against the frozen cohort and fitted outputs."""

import json
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests

from analyze_final import BASE, F, KEY, OUT, Y, digest


def load(name):
    return pd.read_csv(OUT/f'{name}.csv')


def test_cohort_join_counts_and_input_hashes():
    d = load('frozen_analysis_cohort')
    audit = json.loads((OUT/'reconciliation.json').read_text())
    assert len(d)==3186 and not d.duplicated(KEY).any() and d.repo_name.nunique()==215
    assert d[Y].value_counts(dropna=False).to_dict()[1]==1723
    assert d[Y].eq(0).sum()==1391 and d[Y].isna().sum()==72
    assert audit['diff_or_metadata']==32 and audit['unresolved_file_evidence']==40
    assert audit['verification_percent']==100*3114/3186
    assert digest(OUT/'frozen_analysis_cohort.csv')==audit['frozen_cohort_sha256']
    assert all(digest(BASE/path)==value for path,value in audit['input_hashes'].items())
    revised = load('changed_filename_labels')
    assert len(revised)==71 and revised[Y].sum()==56
    assert load('earlier_outcome_revisions').empty


def test_counts_model_estimates_and_worst_case_bounds():
    d = load('frozen_analysis_cohort')
    st = load('main_associations').set_index('column')
    fits = load('model_results')
    bounds = load('missing_outcome_sensitivity').set_index(['feature','scenario'])
    for feature in F:
        row = st.loc[feature]
        for flag,tag in [(0,'absent'),(1,'present')]:
            group = d.loc[d[feature].eq(flag),Y]
            assert row[f'{tag}_total']==len(group)
            assert row[f'{tag}_positive']==group.eq(1).sum()
            assert row[f'{tag}_negative']==group.eq(0).sum()
            assert row[f'{tag}_missing']==group.isna().sum()
            assert np.isclose(row[f'{tag}_rate'],group.mean())
        rd = 100*(row.present_rate-row.absent_rate)
        assert np.isclose(row.difference_pp,rd)
        assert row.difference_ci_low < rd < row.difference_ci_high
        assert np.isclose(row.unadjusted_or,(row.present_positive*row.absent_negative)/
                          (row.present_negative*row.absent_positive))
        for kind in ['unadjusted','adjusted']:
            result = fits[(fits.term==feature)&(fits.model==kind)].iloc[0]
            assert result.stable and result.n==3114 and result.repositories==209
            estimate = np.log(result.odds_ratio)
            se = (np.log(result.ci_high)-np.log(result.ci_low))/(2*norm.ppf(.975))
            assert np.isclose(result.p_value,2*norm.sf(abs(estimate)/se))
            assert np.isclose(row[f'{kind}_or'],result.odds_ratio)
            assert np.isclose(row[f'{kind}_p'],result.p_value)
            assert np.isclose(row[f'{kind}_ci_low'],result.ci_low)
            assert np.isclose(row[f'{kind}_ci_high'],result.ci_high)
        for label,lower in [('lower_difference',True),('upper_difference',False)]:
            assigned = d[Y].fillna(1-d[feature] if lower else d[feature])
            gap = 100*(assigned[d[feature].eq(1)].mean()-assigned[d[feature].eq(0)].mean())
            assert np.isclose(bounds.loc[(feature,label),'difference_pp'],gap)
    for kind in ['adjusted','unadjusted']:
        assert np.allclose(st.loc[F[:2],f'{kind}_holm_p_primary'],
                           multipletests(st.loc[F[:2],f'{kind}_p'],method='holm')[1])


def test_historical_pilot_remains_separate():
    h = load('historical_descriptive_only')
    assert h[h.pilot_cohort.eq('head')].n.eq(39).all()
    assert h[h.pilot_cohort.eq('earlier_anchor')].n.eq(11).all()
    assert h.n.eq(h.observed).all()
    snap = h[(h.pilot_cohort=='head') & h.feature_version.str.startswith('same_rule_snapshot')]
    assert snap.mismatch_vs_head.tolist()==[2,2,0]
