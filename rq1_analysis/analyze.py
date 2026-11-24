"""Descriptives, association tests, repository bootstrap, and guarded logistic models."""
import json
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import patsy
from scipy.stats import chi2_contingency, fisher_exact
from scipy.stats.contingency import odds_ratio
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

from common import FEATURES, OUT, save, write_json

PREDICTORS = ["has_acceptance_criteria", "has_edge_cases", "has_testing_requirement"]
LABELS = {"has_acceptance_criteria": "Acceptance criteria", "has_edge_cases": "Edge cases", "has_testing_requirement": "Testing directive (secondary)"}


def cluster_risk_difference(data, predictor, outcome, repetitions=2000):
    """Resample repositories, preserving every PR in each selected cluster."""
    grouped = data.groupby(["repo_name", predictor])[outcome].agg(["sum", "count"]).unstack(predictor, fill_value=0)
    if 0 not in grouped["count"] or 1 not in grouped["count"] or len(grouped) < 2:
        return np.nan, np.nan, 0
    totals = grouped.loc[:, [("sum", 0), ("count", 0), ("sum", 1), ("count", 1)]].to_numpy(float)
    rng = np.random.default_rng(520)
    values = []
    for _ in range(repetitions):
        sampled = totals[rng.integers(0, len(totals), len(totals))].sum(axis=0)
        if sampled[1] and sampled[3]:
            values.append(sampled[2] / sampled[3] - sampled[0] / sampled[1])
    if len(values) < repetitions * .95:
        return np.nan, np.nan, len(values)
    lo, hi = np.quantile(values, [.025, .975])
    return float(lo), float(hi), len(values)


def compare(data, predictor, outcome, cohort):
    d = data[["repo_name", predictor, outcome]].dropna().copy()
    d[predictor], d[outcome] = d[predictor].astype(int), d[outcome].astype(int)
    tab = pd.crosstab(d[predictor], d[outcome]).reindex(index=[0, 1], columns=[0, 1], fill_value=0)
    a, b = int(tab.loc[1, 1]), int(tab.loc[1, 0])
    c, e = int(tab.loc[0, 1]), int(tab.loc[0, 0])
    rates = []
    for flag, positives, total in [(0, c, c+e), (1, a, a+b)]:
        lo, hi = proportion_confint(positives, total, method="wilson") if total else (np.nan, np.nan)
        rates.append({"cohort": cohort, "predictor": predictor, "outcome": outcome, "feature_present": flag, "n": total, "tests": positives, "rate": positives/total if total else np.nan, "wilson_low": lo, "wilson_high": hi})
    overlap = d.groupby("repo_name")[predictor].nunique()
    result = {"cohort": cohort, "predictor": predictor, "outcome": outcome, "n": len(d), "n_repositories": d.repo_name.nunique(), "n_exposed_repositories": d.loc[d[predictor].eq(1), "repo_name"].nunique(), "n_repositories_with_both_exposures": int(overlap.eq(2).sum()), "a_exposed_test": a, "b_exposed_no_test": b, "c_unexposed_test": c, "d_unexposed_no_test": e}
    if min(a+b, c+e, a+c, b+e) == 0:
        result["status"] = "insufficient predictor or outcome variation"
        return rates, result
    # Exposed vs unexposed table; conditional exact OR and CI also with zero cells.
    table = np.array([[a, b], [c, e]])
    chi, pchi, _, expected = chi2_contingency(table, correction=False)
    use_fisher = (expected < 5).any()
    result.update(test="Fisher exact" if use_fisher else "Chi-square", p_value=float(fisher_exact(table).pvalue if use_fisher else pchi), chi_square=float(chi), min_expected=float(expected.min()))
    effect = odds_ratio(table, kind="conditional")
    ci = effect.confidence_interval()
    result.update(odds_ratio=float(effect.statistic), or_ci_low=float(ci.low), or_ci_high=float(ci.high))
    rate1, rate0 = a/(a+b), c/(c+e)
    result["risk_difference"] = rate1 - rate0
    if min(a, b, c, e) > 0:
        rr = rate1/rate0
        se = np.sqrt(1/a - 1/(a+b) + 1/c - 1/(c+e))
        result.update(risk_ratio=rr, rr_ci_low=np.exp(np.log(rr)-1.96*se), rr_ci_high=np.exp(np.log(rr)+1.96*se))
    else:
        result.update(risk_ratio=rate1/rate0 if rate0 else np.inf, rr_ci_low=np.nan, rr_ci_high=np.nan)
    lo, hi, valid = cluster_risk_difference(d, predictor, outcome)
    result.update(cluster_rd_ci_low=lo, cluster_rd_ci_high=hi, bootstrap_valid=valid, status="estimated")
    return rates, result


def logistic(data, outcome, cohort, include_tool=True, include_source=True, secondary_testing=False):
    cols = ["repo_name", "has_acceptance_criteria", "has_edge_cases", "has_requirements", "n_words", "repo_stars", "n_changed_source_files", "repo_language", "tool", outcome]
    if secondary_testing: cols.append("has_testing_requirement")
    d = data[cols].copy()
    d["repo_language"] = d.repo_language.fillna("Unknown")
    d = d.dropna()
    for c in [outcome, "has_acceptance_criteria", "has_edge_cases", "has_requirements"]:
        d[c] = d[c].astype(float)
    for old, new in [("n_words", "log_words"), ("repo_stars", "log_stars"), ("n_changed_source_files", "log_source")]:
        d[new] = np.log1p(d[old].astype(float))
    # Pool infrequent categories before fitting; do not select by significance.
    for old, new in [("repo_language", "language_group"), ("tool", "tool_group")]:
        counts = d[old].value_counts()
        keep = counts[counts >= 50].index[:5] if old == "repo_language" else counts[counts >= 20].index
        d[new] = d[old].where(d[old].isin(keep), "Other")
    terms = ["has_acceptance_criteria", "has_edge_cases", "log_words", "log_stars", "C(language_group)"]
    if d.has_requirements.nunique() > 1: terms.append("has_requirements")
    if include_tool and d.tool_group.nunique() > 1: terms.append("C(tool_group)")
    if include_source: terms.append("log_source")
    if secondary_testing: terms.append("has_testing_requirement")
    formula = outcome + " ~ " + " + ".join(terms)
    name = f"{cohort}_{outcome}_{'tool_adjusted' if include_tool else 'no_tool'}_{'source_adjusted' if include_source else 'no_source'}"
    if secondary_testing: name += "_testing_secondary"
    diagnostic = {"model": name, "formula": formula, "n": len(d), "repositories": d.repo_name.nunique(), "events": int(d[outcome].sum()), "warnings": []}
    try:
        y, design = patsy.dmatrices(formula, d, return_type="dataframe")
        rank, k = np.linalg.matrix_rank(design), design.shape[1]
        diagnostic.update(parameters=k, rank=int(rank), condition_number=float(np.linalg.cond(design)))
        if d.repo_name.nunique() < 30:
            raise ValueError("Fewer than 30 repository clusters; cluster-robust regression withheld")
        if min(d[outcome].sum(), len(d)-d[outcome].sum()) < 10*k:
            raise ValueError("Fewer than ten events or non-events per parameter")
        if rank < k or diagnostic["condition_number"] > 1e8:
            raise ValueError("Rank-deficient or ill-conditioned design (tool/template confounding)")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fit = smf.glm(formula, data=d, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": d.repo_name, "use_correction": True})
        diagnostic["warnings"] = [str(w.message) for w in caught]
        if not fit.converged or not np.isfinite(fit.bse).all() or (fit.params.abs() > 20).any() or (fit.bse > 10).any() or any("separation" in str(w.message).lower() for w in caught):
            raise ValueError("Nonconvergence, separation, or unstable coefficients; inference withheld")
        ci = fit.conf_int()
        result = pd.DataFrame({"term": fit.params.index, "log_odds": fit.params.values, "cluster_se": fit.bse.values, "odds_ratio": np.exp(fit.params.values), "ci_low": np.exp(ci[0].values), "ci_high": np.exp(ci[1].values), "p_value": fit.pvalues.values})
        result.insert(0, "model", name)
        (OUT / "tables" / f"{name}.txt").write_text(fit.summary().as_text(), encoding="utf-8")
        diagnostic["status"] = "estimated_cluster_robust"
        return result, diagnostic
    except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as error:
        diagnostic.update(status="withheld", reason=str(error))
        return pd.DataFrame(), diagnostic


def analyze():
    d = pd.read_parquet(OUT / "analysis_dataset.parquet")
    allprs = pd.read_parquet(OUT / "intermediate" / "all_pr_observations.parquet")
    frequency = []
    for cohort, frame in [("all_unique_prs", allprs), ("primary_snapshot", d)]:
        for col in FEATURES + ["has_testing_requirement", "repo_language", "repo_stars", "repo_size_kb", "n_changed_source_files", "test_added", "test_modified"]:
            frequency.append({"cohort": cohort, "feature": col, "n": len(frame), "nonmissing": int(frame[col].notna().sum()), "missing": int(frame[col].isna().sum()), "positive": int(frame[col].eq(1).sum()) if col.startswith("has_") or col.startswith("test_") else np.nan, "mean": float(frame[col].mean()) if pd.api.types.is_numeric_dtype(frame[col]) else np.nan, "median": float(frame[col].median()) if pd.api.types.is_numeric_dtype(frame[col]) else np.nan})
    save(pd.DataFrame(frequency), "feature_frequencies_and_missingness")
    for col in ["tool", "repo_language", "repo_name", "repo_license_spdx_id"]:
        table = d.groupby(col, dropna=False).agg(n=("pr_number", "size"), test_additions=("test_added", "sum"), addition_rate=("test_added", "mean"), modification_rate=("test_modified", "mean"), acceptance_prevalence=("has_acceptance_criteria", "mean"), edge_prevalence=("has_edge_cases", "mean"))
        save(table.reset_index().sort_values("n", ascending=False), f"descriptive_by_{col}")
    save(d[["n_words", "repo_stars", "repo_size_kb", "n_changed_source_files", "n_active_spec_files"]].describe().T.reset_index(names="variable"), "continuous_descriptives")
    # Exclusion bias: testing can be measured even where specs cannot be linked.
    save(allprs.groupby("in_primary_snapshot_analysis").agg(n=("pr_number", "size"), repos=("repo_name", "nunique"), addition_rate=("test_added", "mean"), modification_rate=("test_modified", "mean")).reset_index(), "included_vs_excluded")
    rates, effects = [], []
    largest = d.repo_name.value_counts().index[0] if len(d) else ""
    analyses = [("primary_snapshot", d, "test_added"), ("primary_snapshot", d, "test_modified"), ("high_confidence_detector", d, "test_added_strict"), ("high_confidence_detector", d, "test_modified_strict"), ("temporal_overlap", d[d.in_temporal_sensitivity], "test_added"), ("without_largest_repository", d[d.repo_name.ne(largest)], "test_added")]
    for cohort, frame, outcome in analyses:
        for predictor in PREDICTORS:
            r, e = compare(frame, predictor, outcome, cohort)
            rates.extend(r); effects.append(e)
    rates, effects = pd.DataFrame(rates), pd.DataFrame(effects)
    primary_mask = effects.cohort.eq("primary_snapshot") & effects.outcome.eq("test_added") & effects.predictor.isin(PREDICTORS[:2]) & effects.p_value.notna()
    if primary_mask.any():
        effects.loc[primary_mask, "primary_holm_p"] = multipletests(effects.loc[primary_mask, "p_value"], method="holm")[1]
    save(rates, "testing_rates")
    save(effects, "association_tests")
    # Show within-tool overlap; a tool with only one exposure cannot identify its effect.
    strata = []
    for tool, frame in d.groupby("tool"):
        for predictor in PREDICTORS[:2]:
            for flag in [0, 1]:
                s = frame[frame[predictor].eq(flag)]
                strata.append({"tool": tool, "predictor": predictor, "feature_present": flag, "n": len(s), "n_repositories": s.repo_name.nunique(), "tests_added": int(s.test_added.sum()), "rate": float(s.test_added.mean()) if len(s) else np.nan})
    save(pd.DataFrame(strata), "within_tool_testing_rates")
    regression, diagnostics = [], []
    for outcome in ["test_added", "test_modified"]:
        for tool, source in [(False, True), (True, True), (True, False)]:
            result, diagnostic = logistic(d, outcome, "primary_snapshot", tool, source)
            regression.append(result); diagnostics.append(diagnostic)
        result, diagnostic = logistic(d, outcome, "primary_snapshot", True, True, secondary_testing=True)
        regression.append(result); diagnostics.append(diagnostic)
    save(pd.concat(regression, ignore_index=True), "logistic_regression")
    write_json(OUT / "tables" / "regression_diagnostics.json", diagnostics)
    # Marginal rates: Wilson bars are independent-binomial reference intervals;
    # repository-bootstrap intervals for contrasts appear in association_tests.csv.
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, predictor in zip(axes, PREDICTORS[:2]):
        subset = rates[(rates.cohort == "primary_snapshot") & (rates.outcome == "test_added") & (rates.predictor == predictor)].sort_values("feature_present")
        y = subset.rate.to_numpy(float)*100
        error = np.vstack([y-subset.wilson_low.to_numpy(float)*100, subset.wilson_high.to_numpy(float)*100-y])
        ax.bar([0, 1], y, yerr=error, color=["#5a7994", "#248a79"], capsize=5, width=.55)
        ax.set_xticks([0, 1], ["Absent", "Present"])
        ax.set_title(LABELS[predictor])
        for i, row in enumerate(subset.itertuples()):
            if np.isfinite(row.rate): ax.text(i, row.wilson_high*100+2, f"{row.rate:.1%}\nn={row.n:,}", ha="center", fontsize=10)
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("PRs adding a candidate test file (%)")
    fig.suptitle("Exact-path snapshot cohort: exploratory associations", fontsize=13)
    fig.text(.5, .01, "Bars: marginal rates; intervals: Wilson 95%. PR-time specification versions are unverified.", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, .05, 1, .93])
    fig.savefig(OUT / "figures" / "test_addition_rates.png", dpi=180)
    fig.savefig(OUT / "figures" / "test_addition_rates.pdf")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7), sharey=True)
    for ax, outcome in zip(axes, ["test_added", "test_modified"]):
        sub = effects[effects.cohort.eq("primary_snapshot") & effects.outcome.eq(outcome)]
        for i, predictor in enumerate(PREDICTORS):
            r = sub[sub.predictor.eq(predictor)].iloc[0]
            ax.plot([r.cluster_rd_ci_low*100, r.cluster_rd_ci_high*100], [i, i], color="#246b87", lw=3)
            ax.scatter([r.risk_difference*100], [i], color="#172f42", zorder=3)
        ax.axvline(0, color="#999999", ls="--")
        ax.set_title("Test file " + ("additions" if outcome == "test_added" else "modifications"))
        ax.set_xlabel("Rate difference (percentage points)")
        ax.set_yticks(range(3), [LABELS[x] for x in PREDICTORS])
    fig.suptitle("Repository bootstrap: 95% intervals for marginal differences", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "figures" / "clustered_rate_differences.png", dpi=180)
    plt.close(fig)
    print(effects.loc[effects.cohort.eq("primary_snapshot"), ["predictor", "outcome", "risk_difference", "cluster_rd_ci_low", "cluster_rd_ci_high", "p_value"]].to_string(index=False))
    print(pd.DataFrame(diagnostics)[["model", "status"]].to_string(index=False))


if __name__ == "__main__":
    analyze()
