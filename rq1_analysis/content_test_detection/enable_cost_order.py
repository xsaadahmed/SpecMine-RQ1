from pathlib import Path
p=Path('rq1_analysis/content_test_detection/full_cohort.py');s=p.read_text();s=s.replace("import argparse,json,os,math", "import argparse,json,os,math,time")
s=s.replace("p.add_argument('--batch-number',type=int,default=1);args=p.parse_args()", "p.add_argument('--batch-number',type=int,default=1);p.add_argument('--prioritize-low-cost',action='store_true');args=p.parse_args()")
s=s.replace("    stop=None\n", "    work_sample=prioritize_remaining(sample,states) if args.prioritize_low_cost else sample\n    if args.prioritize_low_cost:\n        plans=B/'execution_plans';plans.mkdir(exist_ok=True)\n        work_sample[KEY+['execution_rank']].to_csv(plans/(str(time.time_ns())+'.csv'),index=False)\n    stop=None\n")
s=s.replace("for row in sample.to_dict('records'):\n            ident=", "for row in work_sample.to_dict('records'):\n            ident=")
p.write_text(s)
