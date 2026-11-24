from pathlib import Path
import json
import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).parent;O=P/'outputs';r=pd.read_csv(O/'results.csv');m=pd.read_csv(O/'exploratory_models.csv');v=json.loads((O/'validation.json').read_text())
secondary=m[(m.model=='testing_directive_secondary')&m.outcome.eq('content')].copy();secondary['holm_p']=multipletests(secondary.p_value_reference_only,method='holm')[1];secondary.to_csv(O/'secondary_multiplicity.csv',index=False)
rows=[]
for x in r.to_dict('records'):
 a=m[(m.term==x['column'])&m.outcome.eq('content')&m.model.eq('testing_directive_secondary' if x['column']=='has_testing_requirement' else 'primary_selected_subset')].iloc[0]
 rows.append(f"| {x['feature']} | {x['present_positive']}/{x['present_negative']} ({x['present_resolved']}); {100*x['present_rate']:.1f}% | {x['absent_positive']}/{x['absent_negative']} ({x['absent_resolved']}); {100*x['absent_rate']:.1f}% | {x['difference_pp']:+.1f} ({x['difference_ci_low']:.1f}, {x['difference_ci_high']:.1f}) | {a.OR:.2f} ({a.CI_low:.2f}, {a.CI_high:.2f}) |")
table='''| Snapshot specification feature | Present: positive/negative (N); rate | Absent: positive/negative (N); rate | Difference, pp (95% cluster-bootstrap CI) | Exploratory adjusted OR (95% cluster CI) |
|---|---:|---:|---:|---:|
'''+ '\n'.join(rows)
(P/'RESULTS_TABLE.md').write_text(table+'\n\nRates use resolved PRs only. Difference CIs resample repositories 3,000 times (seed 520). They address dependence, not verification selection. ORs adjust for tool, language, requirements, log specification words and log stars; directive OR adds the secondary directive to the primary model. None is a causal or full-cohort estimate.\n',encoding='utf-8')
fig,ax=plt.subplots(figsize=(8.4,4))
y=np.arange(3)
for prefix,offset,color,label in [('absent',-.15,'#64748b','Feature absent'),('present',.15,'#0f766e','Feature present')]:
 values=r[prefix+'_rate'].to_numpy()*100
 err=np.vstack([values-r[prefix+'_rate_ci_low'].to_numpy()*100,r[prefix+'_rate_ci_high'].to_numpy()*100-values])
 ax.errorbar(values,y+offset,xerr=err,fmt='o',color=color,label=label,capsize=4,markersize=7)
ax.set_yticks(y,['Acceptance criteria','Edge cases','Testing directive (secondary)']);ax.set_xlim(35,85);ax.set_xlabel('PRs adding a test file (%)');ax.invert_yaxis();ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,-.22),ncol=2);ax.set_title('Content outcomes among 1,864 resolved PRs');ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(O/'rates.png',dpi=180);fig.savefig(O/'rates.pdf');plt.close(fig)
print(table)

