# Final RQ1 analysis v1

From the repository root in PowerShell:

```powershell
& .\rq1_analysis\.venv\Scripts\python.exe -B .\rq1_analysis\final_analysis_v1\analyze_final.py
& .\rq1_analysis\.venv\Scripts\python.exe -B -m pytest rq1_analysis/final_analysis_v1 -q -p no:cacheprovider
```

The existing statistics environment has pandas 3.0.5, statsmodels 0.15.0, SciPy 1.18.0, NumPy 2.4.3, Matplotlib 3.11.2, and PyArrow 26.0.0. The offline script hashes saved inputs, checks the one-to-one join and freezes the full cohort. A different cohort requires a new version. All new outputs are under this directory.

The primary specification follows the presentation evaluation with acceptance criteria, edge cases, a general requirements indicator, log1p word count, log1p repository stars, and tool and repository language groups. It adds testing directives in the secondary model. Tool groups below 30 resolved PRs and language groups below 50 are pooled for the final cohort. Grouping is held fixed across final-cohort sensitivities and derived separately for the reproduction of the smaller presentation cohort. The original midpoint also reported source-count alternatives. Here source count is a sensitivity because it reflects implementation scope and may occur downstream of the specification. All headline models use the same 3,114 observed outcomes and 209 repository clusters.

The main association table includes observed rates, rate differences, odds ratios, and multiplicity results. The separate figures show pointwise association intervals and unknown-outcome assignment bounds. Exact rates by tool, output-model diagnostics, filename disagreements, coverage by repository and feature, leave-one-repository-out checks, and historical pilot contrasts are in `outputs/`. See [results](RESULTS.md), [limitations](LIMITATIONS.md), and the [data dictionary](DATA_DICTIONARY.md).

The older presentation suite's hash assertion reads the rolling `current_main_outcomes.csv`, which has advanced since the presentation. Its separate `frozen_content_outcomes.csv` still matches the hash recorded by the presentation. The final analysis uses the later versioned cohort.
