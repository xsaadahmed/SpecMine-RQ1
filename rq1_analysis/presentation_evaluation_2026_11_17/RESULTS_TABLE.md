| Snapshot specification feature | Present: positive/negative (N); rate | Absent: positive/negative (N); rate | Difference, pp (95% cluster-bootstrap CI) | Exploratory adjusted OR (95% cluster CI) |
|---|---:|---:|---:|---:|
| Acceptance criteria | 61/31 (92); 66.3% | 962/810 (1772); 54.3% | +12.0 (-0.6, 22.9) | 1.68 (0.94, 2.98) |
| Edge cases | 287/204 (491); 58.5% | 736/637 (1373); 53.6% | +4.8 (-4.6, 14.7) | 1.29 (0.82, 2.04) |
| Testing directive (secondary) | 124/66 (190); 65.3% | 899/775 (1674); 53.7% | +11.6 (3.8, 19.3) | 1.41 (1.02, 1.95) |

Rates use resolved PRs only. Difference CIs resample repositories 3,000 times (seed 520). They address dependence, not verification selection. ORs adjust for tool, language, requirements, log specification words and log stars; directive OR adds the secondary directive to the primary model. None is a causal or full-cohort estimate.
